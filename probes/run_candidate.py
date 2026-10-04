"""Trusted candidate execution. Private results are never fed back to B0."""
import argparse
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from fixture.harness.t2 import World
from fixture.harness.t2 import PORTS,read_rows
from fixture.app.common import http
from concurrent.futures import ThreadPoolExecutor

def payment_observation(w,accepted_http,order):
    """Summarize public proxy exchanges; these are not committed-effect counts."""
    with w.event_lock:
        responses=[e for e in w.events if e['event']=='payment_response']
    charges=[e for e in responses if e['path']=='/charges']
    keys={e['body'].get('operation_key') for e in charges}
    return {'fault':'payment response loss' if w.fault else 'none',
            'accepted_http':accepted_http,'order':order,'payment_responses':responses,
            'payment_requests':{'charge_requests_observed':len(charges),
                                'distinct_charge_operation_keys':len(keys)}}


def public_stock():
    code,stock=http(PORTS['inventory'],'GET','/stock')
    if code!=200 or not isinstance(stock,dict): raise RuntimeError('public stock observation unavailable')
    return stock


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['developer','protected','identity_probe','compensation_probe','calibration','final_holdout'],required=True)
    parser.add_argument('--incident',choices=['IF-001','IF-002'],default='IF-001')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True);args.output.chmod(0o700)
    if args.mode=='final_holdout':
        from evaluation.holdout import run
        result=run(args.output,args.incident)
    elif args.mode=='calibration':
        from probes.calibrate_recovery import main as calibrate
        result=calibrate()
    elif args.mode=='compensation_probe' or (args.mode=='developer' and args.incident=='IF-002'):
        from fixture.harness.compensation import decline_restart,state
        observations=[]
        conditions=['no_restart','order_restart']
        if args.mode=='compensation_probe': conditions+=['release_replay','release_replay_inventory_restart']
        for condition in conditions:
            with tempfile.TemporaryDirectory(prefix='if-comp-') as temp:
                Path(temp).chmod(0o755);w=World(Path(temp)/'world',trace=True)
                try:
                    w.start()
                    if condition=='order_restart':
                        measured=decline_restart(w)
                        observation={'condition':condition,'order':measured['order'],
                                     'elapsed_seconds':measured['elapsed_seconds'],'deadline_seconds':measured['deadline_seconds']}
                    elif condition=='no_restart':
                        w.submit('decline',expect='decline',customer_id='CUST-DECLINE')
                        observation={'condition':condition,'order':w.observe('decline',timeout=2)}
                    else:
                        body={'order_id':'probe','operation_key':'rsv:probe','items':[{'sku':'A','qty':1}]}
                        http(PORTS['inventory'],'POST','/reservations',body)
                        first=http(PORTS['inventory'],'POST','/reservations/rsv:probe/release',{'operation_key':'rel:probe'})
                        if condition.endswith('inventory_restart'): w.restart('inventory')
                        second=http(PORTS['inventory'],'POST','/reservations/rsv:probe/release',{'operation_key':'rel:probe'})
                        observation={'condition':condition,'responses':[first,second],
                                     'stock':http(PORTS['inventory'],'GET','/stock')[1]}
                    if condition in ('no_restart','order_restart'): observation['stock']=public_stock()
                    from fixture.harness.trace_observation import observation as trace_observation
                    observation['execution_trace']=trace_observation(w)
                    observations.append(observation)
                finally: w.close()
        result={'mode':args.mode,'complete':True,'observations':observations,
                'limitations':['Development only; fixed two-second recovery observation, not calibrated holdout.',
                'Restart condition discards in-flight requests by restarting Inventory with its durable store retained.']}
    elif args.mode=='developer':
        observations=[]
        for fault in (False,True):
            with tempfile.TemporaryDirectory(prefix='if-dev-') as temp:
                Path(temp).chmod(0o755)
                w=World(Path(temp)/'world',fault=fault)
                try:
                    w.start();code,_=w.submit();order=w.observe()
                    # Developer observations only, not hidden evaluator feedback.
                    # Replaying public HTTP responses is not an effect-safety verdict.
                    observations.append(payment_observation(w,code,order))
                finally: w.close()
        result={'mode':'developer','observations':observations,'complete':True,
                'note':'HTTP observations, request identity counts and order state only; no committed-effect count or protected verdict.'}
    elif args.mode=='identity_probe':
        observations=[]
        for condition in ('same_key_sequential','same_key_restart','same_key_concurrent','different_keys'):
            with tempfile.TemporaryDirectory(prefix='if-probe-') as temp:
                Path(temp).chmod(0o755)
                w=World(Path(temp)/'world')
                try:
                    w.start()
                    body={'order_id':'probe','payment_intent_id':'probe','customer_id':'CUST-OK',
                          'amount_cents':100,'currency':'USD','operation_key':'probe-key'}
                    def send(payload): return http(PORTS['payment'],'POST','/charges',payload)
                    if condition=='same_key_concurrent':
                        with ThreadPoolExecutor(2) as pool: responses=list(pool.map(send,[body,body]))
                    else:
                        responses=[send(body)]
                        if condition=='same_key_restart': w.restart('payment')
                        responses.append(send({**body,'operation_key':'second-key'} if condition=='different_keys' else body))
                    effects=read_rows(w.db('payment'),'SELECT * FROM _payment_audit')
                    observations.append({'condition':condition,'http_statuses':[r[0] for r in responses],
                        'response_effect_ids':[r[1].get('charge_id') for r in responses],
                        'committed_charge_count':sum(r['kind']=='charge' for r in effects),
                        'operation_keys':[r['operation_key'] for r in effects]})
                finally: w.close()
        result={'mode':'identity_probe','complete':True,'reset':'fresh stores per condition',
                'observations':observations,'limitations':['One repetition per condition; absence of a race is not proof of absence.',
                  'Declared development experiment; no private schedules or source exposed.']}
    else:
        os.environ['T2_OUTPUT']=str(args.output)
        names=['reference_clean_canonical_replay_decline_stock_and_cancel_conflict',
               'reference_lost_response_payment_restart',
               'cancellation_reconciles_lost_charge_and_survives_order_restart',
               'reference_concurrent_orders_and_stock_contention',
               'reference_payment_concurrency_restart_conflict_and_refund',
               'decline_compensation_recovers_after_crash_before_release']
        names=['tests.test_t2.ContractTests.test_'+n for n in names]
        if args.incident=='IF-002':
            names+=['tests.test_t6.CompensationTests.test_if002_reference_restart',
                    'tests.test_t6.CompensationTests.test_if002_release_replay_across_inventory_restart']
        suite=unittest.defaultTestLoader.loadTestsFromNames(names)
        buf=io.StringIO();out=unittest.TextTestRunner(stream=buf,verbosity=2).run(suite)
        from tests.test_t2 import RESULTS
        (args.output/'tests.log').write_text(buf.getvalue())
        complete=out.testsRun==len(names) and not out.skipped
        accept=complete and out.wasSuccessful() and len(RESULTS)==len(names) and all(r['decision']=='accept_for_review' for r in RESULTS)
        result={'mode':'protected','decision':'accept_for_review' if accept else 'reject_behavior',
                'tests_run':out.testsRun,'failures':len(out.failures),'errors':len(out.errors),
                'skipped':len(out.skipped),'complete':complete,'cases':RESULTS,
                'limitations':['Fixed development schedules, not final holdout or universal correctness.']}
    if args.mode=='developer':
        from fixture.harness.developer_tests import execute
        candidate=os.environ.get('IF_CANDIDATE_ROOT')
        if candidate: result['developer_tests']=execute(Path(candidate)/'developer-tests.json',result)
    (args.output/'result.json').write_text(json.dumps(result,indent=2))
    return 0

if __name__=='__main__': raise SystemExit(main())
