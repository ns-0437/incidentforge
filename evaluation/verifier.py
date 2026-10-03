"""Protected development evaluator. Read only trusted, bounded quiesced backups."""
from collections import defaultdict
from contextlib import closing
import hashlib
import json
import sqlite3
import time

PROPERTIES=['P1','P2','P3','P4','P5','P6','P7']


def evaluate(directory,manifest_sha256,boundary_receipt):
    evidence_loaded=False
    failures={p:[] for p in PROPERTIES}
    def fail(prop,reason): failures[prop].append(reason)
    def invalid(reason):
        return {'schema_version':1,'decision':'invalid_evaluation',
                'properties':{p:{'status':'fail' if p=='P7' else 'unknown','reasons':[reason] if p=='P7' else []}
                              for p in PROPERTIES}}
    try:
        raw=(directory/'manifest.json').read_bytes()
        if len(raw)>1_000_000 or hashlib.sha256(raw).hexdigest()!=manifest_sha256:
            return invalid('manifest origin/hash mismatch')
        m=json.loads(raw)
        if not m.get('registry'): return invalid('empty workload registry')
        if not boundary_receipt or not all(boundary_receipt.values()) or not m['quiesced']:
            return invalid('boundary or quiescence incomplete')
        stores={}
        for service in ('order','inventory','payment'):
            path=directory/(service+'.db')
            if path.is_symlink() or not 0<path.stat().st_size<=4_000_000:
                return invalid('invalid backup size/path')
            if hashlib.sha256(path.read_bytes()).hexdigest()!=m['snapshots'][service]['sha256']:
                return invalid('backup hash mismatch')
            with closing(sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1',uri=True)) as db:
                deadline=time.monotonic()+2
                db.set_progress_handler(lambda: int(time.monotonic()>deadline),1000)
                if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
                    return invalid('backup integrity')
                db.row_factory=sqlite3.Row
                data={name:[dict(r) for r in db.execute('SELECT * FROM '+name)] for name in
                      ('app_state','_state_audit','_policy_audit')}
                if service=='payment':
                    for name in ('payment_effects','_payment_audit','_effect_audit'):
                        data[name]=[dict(r) for r in db.execute('SELECT * FROM '+name)]
                stores[service]=data
        if m['fault_requested'] and not any(e['event']=='response_lost_after_commit' for e in m['events']):
            return invalid('requested post-commit fault not witnessed')
        payment=stores['payment']
        effects=payment['_payment_audit']
        if [{k:v for k,v in r.items() if k!='seq'} for r in effects]!=payment['payment_effects']:
            return invalid('effect/audit mismatch')
        if payment['_effect_audit']: fail('P1','unexpected legacy payment effects')
        for service,data in stores.items():
            if data['_policy_audit']: fail('P7',service+': broker recorded rejected operations')
        evidence_loaded=True
        state={s:{r['key']:json.loads(r['value']) for r in d['app_state']} for s,d in stores.items()}
        # Replay complete mutation history, grouping atomic transactions before checking business invariants.
        for service,data in stores.items():
            replay={}
            transactions=[]
            for r in data['_state_audit']:
                if not transactions or transactions[-1][0]!=r['tx']: transactions.append((r['tx'],[]))
                transactions[-1][1].append(r)
            if len({t for t,_ in transactions})!=len(transactions): return invalid('noncontiguous transaction history')
            for tx,rows in transactions:
                before=dict(replay)
                for r in rows:
                    if r['kind']=='delete': replay.pop(r['key'],None)
                    else: replay[r['key']]=json.loads(r['value'])
                if service=='inventory':
                    held=defaultdict(int)
                    for key,res in replay.items():
                        if key.startswith('reservation:'):
                            registered=m['registry'].get(res['payload']['order_id'])
                            if registered is None or res['payload']['items']!=registered['payload'].get('items'):
                                fail('P5','reservation payload disagrees with workload')
                            prior=before.get(key)
                            if prior and (prior['payload']!=res['payload'] or
                                (prior['result'].get('status')=='RELEASED' and res!=prior)):
                                fail('P5','reservation identity/release history changed')
                            if key not in before and res['status']==409:
                                if all(replay.get('stock',{}).get(i['sku'],{}).get('available',0)>=i['qty'] for i in res['payload']['items']):
                                    fail('P4','stock rejection despite sufficient inventory')
                        if key.startswith('reservation:') and res['result'].get('status')=='HELD':
                            for item in res['payload']['items']: held[item['sku']]+=item['qty']
                    stock=replay.get('stock',{})
                    if any(k.startswith('reservation:') and k not in replay for k in before):
                        fail('P5','reservation history deleted')
                    if set(stock)!=set(m['initial']): fail('P5','stock catalog changed')
                    for sku,initial in m['initial'].items():
                        cell=stock.get(sku,{})
                        if cell!={'initial':initial,'held':held[sku],'available':initial-held[sku]} or held[sku]>initial or held[sku]<0:
                            fail('P5','inventory mismatch at transaction '+tx)
            if replay!=state[service]: return invalid(service+': state history incomplete')
        charges=defaultdict(list)
        refunds=defaultdict(list)
        key_effects=defaultdict(list)
        for r in effects:
            intent=r['intent_id']
            expected=m['registry'].get(intent)
            if expected is None:
                fail('P1','unregistered payment intent '+intent)
            else:
                p=expected['payload']
                if (r['amount_cents'],r['currency'],r['customer_id'])!=(p['amount_cents'],p['currency'],p['customer_id']):
                    fail('P1','misattributed amount/currency/customer '+intent)
            key_effects[(r['kind'],r['operation_key'])].append(r)
            if r['kind']=='charge': charges[intent].append(r)
            elif r['kind']=='refund': refunds[r['charge_id']].append(r)
            else: fail('P1','unknown payment effect kind')
        for intent,rows in charges.items():
            if len(rows)>1: fail('P1','multiple committed charges for '+intent)
        for key,rows in key_effects.items():
            if len(rows)>1: fail('P6','same operation key produced multiple effects: '+str(key))
        charge_by_id={r['effect_id']:r for rows in charges.values() for r in rows}
        for cid,rows in refunds.items():
            if len(rows)!=1 or cid not in charge_by_id:
                fail('P4','invalid/duplicate refund '+cid)
            elif any(rows[0][k]!=charge_by_id[cid][k] for k in ('intent_id','amount_cents','currency','customer_id')):
                fail('P4','refund does not match original charge')
        reservations=[v for k,v in state['inventory'].items() if k.startswith('reservation:')]
        for res in reservations:
            oid=res['payload']['order_id']
            if oid not in m['registry']:
                fail('P5','reservation for unknown order')
        for oid,registered in m['registry'].items():
            expect=registered['expect']
            if expect=='payment_only':
                if registered['payload']['customer_id']!='CUST-DECLINE' and len(charges[oid])!=1:
                    fail('P3','direct eligible payment did not produce exactly one charge')
                continue
            order=state['order'].get('order:'+oid,{})
            response=m['responses'].get(oid,{})
            if any(response.get(k)!=order.get(k) for k in ('status','charge_id','refund_id','payload')):
                fail('P2','response/durable state disagree '+oid)
            phase=order.get('status')
            if order.get('payload')!=registered['payload']: fail('P2','durable order payload mismatch '+oid)
            cs=charges[oid]
            holds=[r for r in reservations if r['payload']['order_id']==oid and r['result'].get('status')=='HELD']
            if phase=='CONFIRMED':
                if len(cs)!=1 or refunds.get(cs[0]['effect_id']) or order.get('charge_id')!=cs[0]['effect_id']:
                    fail('P2','confirmation without exactly one matching unrefunded charge '+oid)
                if len(holds)!=1 or holds[0]['payload']['items']!=registered['payload']['items']:
                    fail('P2','confirmation without matching hold '+oid)
            if oid in m['cancellations']:
                if phase!='CANCELLED_BY_CLIENT' or holds or any(len(refunds[c['effect_id']])!=1 for c in cs):
                    fail('P4','cancellation incomplete '+oid)
            elif expect=='eligible':
                if phase!='CONFIRMED': fail('P3','eligible order not confirmed by deadline '+oid)
            elif expect in {'decline','stock_reject'}:
                target='CANCELLED_DECLINED' if expect=='decline' else 'REJECTED_STOCK'
                if phase!=target or holds or cs: fail('P4','rejection/compensation incorrect '+oid)
            elif expect=='contention':
                if phase not in {'CONFIRMED','REJECTED_STOCK'}: fail('P3','contention did not settle '+oid)
                if phase=='REJECTED_STOCK' and (holds or cs): fail('P4','stock loser leaked effects '+oid)
                if phase=='REJECTED_STOCK' and not any(r['payload']['order_id']==oid and r['status']==409 for r in reservations):
                    fail('P4','stock rejection without inventory decision '+oid)
            else: return invalid('unknown expected outcome')
        for check in m.get('protocol_checks',[]):
            if not check['passed']: fail('P6',check['name'])
        properties={p:{'status':'fail' if failures[p] else 'pass','reasons':failures[p]} for p in PROPERTIES}
        if not m.get('protocol_checks') and not failures['P6']:
            properties['P6']['status']='not_applicable'
        if all(r['expect']=='payment_only' for r in m['registry'].values()) and not failures['P2']:
            properties['P2']['status']='not_applicable'
        return {'schema_version':1,'decision':'reject_behavior' if any(failures.values()) else 'accept_for_review',
                'properties':properties,'counts':{'charges':sum(map(len,charges.values())),
                'refunds':sum(map(len,refunds.values()))},'conditions':'local T2 development workloads; not a final holdout'}
    except (OSError,sqlite3.Error) as exc:
        return invalid('evidence parsing failed: '+type(exc).__name__)
    except (ValueError,KeyError,TypeError,AttributeError,IndexError) as exc:
        if not evidence_loaded: return invalid('evidence metadata malformed: '+type(exc).__name__)
        return {'schema_version':1,'decision':'reject_behavior','properties':{
            p:{'status':'fail' if p=='P2' else 'pass' if p=='P7' else 'unknown',
               'reasons':['malformed candidate durable state: '+type(exc).__name__] if p=='P2' else []}
            for p in PROPERTIES}}
