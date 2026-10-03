"""Business services. No private schedules, evaluator or repair controls."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time
import uuid
from .common import canonical, http, transaction
from .contract import identity, items, money, order_payload

TERMINAL={'CONFIRMED','REJECTED_STOCK','CANCELLED_DECLINED','CANCELLED_BY_CLIENT'}


class App:
    def __init__(self,args):
        self.args=args
        self.lock=threading.RLock()

    def dispatch(self,method,path,body):
        with self.lock:
            if method=='GET' and path=='/healthz':
                return 200,{'ready':True,'service':self.args.service}
            return getattr(self,self.args.service)(method,path,body)

    def payment(self,method,path,body):
        if method!='POST' or path not in {'/charges','/refunds'}:
            return 404,{'error':'not_found'}
        key=identity(body['operation_key'])
        kind='charge' if path=='/charges' else 'refund'
        payload=({'order_id':identity(body['order_id']),
                  'payment_intent_id':identity(body['payment_intent_id']),
                  'customer_id':identity(body['customer_id']), **money(body)} if kind=='charge' else
                 {'charge_id':identity(body['charge_id']), **money(body)})
        with transaction(self.args.socket) as db:
            previous=db.get(kind+':'+key)
            if previous:
                if previous['payload']!=payload:
                    return 409,{'error':'IDEMPOTENCY_KEY_CONFLICT'}
                return (402 if previous['status']==402 else 200),previous['result']
            if kind=='charge':
                if payload['order_id']!=payload['payment_intent_id']:
                    return 400,{'error':'intent_mismatch'}
                intent,customer,charge_id=payload['payment_intent_id'],payload['customer_id'],''
                if customer=='CUST-DECLINE':
                    result={'status':'DECLINED'}
                    db.put(kind+':'+key,{'payload':payload,'status':402,'result':result})
                    return 402,result
            else:
                rows=db.sql("SELECT intent_id,customer_id,amount_cents,currency FROM payment_effects WHERE effect_id=? AND kind='charge'",payload['charge_id'])
                if not rows:
                    return 404,{'error':'charge_not_found'}
                intent,customer,amount,currency=rows[0]
                if amount!=payload['amount_cents'] or currency!=payload['currency']:
                    return 409,{'error':'full_refund_required'}
                charge_id=payload['charge_id']
                refunded=db.sql("SELECT effect_id FROM payment_effects WHERE charge_id=? AND kind='refund'",charge_id)
                if refunded:
                    return 409,{'error':'already_refunded'}
            effect=str(uuid.uuid4())
            db.sql('INSERT INTO payment_effects VALUES(?,?,?,?,?,?,?,?)',effect,kind,intent,key,
                   payload['amount_cents'],payload['currency'],customer,charge_id)
            result={'status':'COMMITTED',kind+'_id':effect}
            db.put(kind+':'+key,{'payload':payload,'status':201,'result':result})
        return 201,result

    def inventory(self,method,path,body):
        with transaction(self.args.socket) as db:
            stock=db.get('stock')
            if method=='GET' and path=='/stock':
                return 200,stock
            if method=='POST' and path=='/reservations':
                key=identity(body['operation_key'])
                payload={'order_id':identity(body['order_id']),'items':items(body['items'])}
                previous=db.get('reservation:'+key)
                if previous:
                    if previous['payload']!=payload:
                        return 409,{'error':'IDEMPOTENCY_KEY_CONFLICT'}
                    return previous['status'] if previous['status']==409 else 200,previous['result']
                enough=all(stock.get(i['sku'],{}).get('available',0)>=i['qty'] for i in payload['items'])
                result=({'reservation_id':key,'status':'HELD'} if enough else {'error':'INSUFFICIENT_STOCK'})
                if enough:
                    for i in payload['items']:
                        stock[i['sku']]['available']-=i['qty']
                        stock[i['sku']]['held']+=i['qty']
                    db.put('stock',stock)
                db.put('reservation:'+key,{'payload':payload,'status':201 if enough else 409,'result':result})
                return (201 if enough else 409),result
            if method=='POST' and path.startswith('/reservations/') and path.endswith('/release'):
                reservation=identity(path.split('/')[2])
                key=identity(body['operation_key'])
                payload={'reservation_id':reservation}
                previous=db.get('release:'+key)
                if previous:
                    if previous['payload']!=payload:
                        return 409,{'error':'IDEMPOTENCY_KEY_CONFLICT'}
                    return 200,previous['result']
                record=db.get('reservation:'+reservation)
                if not record or record['status']==409:
                    return 404,{'error':'not_found'}
                if record['result']['status']=='HELD':
                    for i in record['payload']['items']:
                        stock[i['sku']]['available']+=i['qty']
                        stock[i['sku']]['held']-=i['qty']
                    record['result']['status']='RELEASED'
                    db.put('stock',stock)
                    db.put('reservation:'+reservation,record)
                db.put('release:'+key,{'payload':payload,'result':record['result']})
                return 200,record['result']
        return 404,{'error':'not_found'}

    def order(self,method,path,body):
        if method=='POST' and path=='/orders':
            payload=order_payload(body)
            oid=payload['client_request_id']
            with transaction(self.args.socket) as db:
                prior=db.get('order:'+oid)
                if prior:
                    return (200,prior) if prior['payload']==payload else (409,{'error':'CLIENT_REQUEST_ID_CONFLICT'})
                result={'order_id':oid,'payload':payload,'status':'RECEIVED','attempts':0,
                        'payment_key':'chg:'+oid,'reservation_key':'rsv:'+oid}
                db.put('order:'+oid,result)
                return 202,result
        if path.startswith('/orders/'):
            oid=identity(path.split('/')[2])
            with transaction(self.args.socket) as db:
                order=db.get('order:'+oid)
                if not order:
                    return 404,{'error':'not_found'}
                if method=='GET' and len(path.split('/'))==3:
                    return 200,order
                if method=='POST' and path.endswith('/cancel'):
                    cancel_id=identity(body['cancel_request_id'])
                    prior=db.get('cancel:'+cancel_id)
                    if prior:
                        return (200,prior) if prior['order_id']==oid else (409,{'error':'CANCEL_ID_CONFLICT'})
                    if order['status'] in TERMINAL:
                        return 409,{'error':'ALREADY_TERMINAL'}
                    if order['status']!='CANCEL_REQUESTED':
                        order['cancel_from']=order['status']
                        order['status']='CANCEL_REQUESTED'
                        order['next_retry']=0
                    result={'order_id':oid,'cancel_request_id':cancel_id,'accepted':True}
                    db.put('cancel:'+cancel_id,result)
                    db.put('order:'+oid,order)
                    return 202,result
        return 404,{'error':'not_found'}

    def update(self,order):
        with transaction(self.args.socket) as db:
            db.put('order:'+order['order_id'],order)

    def reserve(self,o):
        return http(self.args.inventory_port,'POST','/reservations',
                    {'order_id':o['order_id'],'operation_key':o['reservation_key'],'items':o['payload']['items']})

    def charge(self,o):
        p=o['payload']
        return http(self.args.payment_port,'POST','/charges',{'order_id':o['order_id'],
            'payment_intent_id':o['order_id'],'operation_key':o['payment_key'],
            'customer_id':p['customer_id'],'amount_cents':p['amount_cents'],'currency':p['currency']},timeout=.35)

    def step(self,o):
        phase=o['status']
        if phase in TERMINAL or o.get('next_retry',0)>time.time():
            return
        if phase in {'RECEIVED','RESERVING'}:
            o['status']='RESERVING'
            self.update(o)
            code,res=self.reserve(o)
            if code in (200,201):
                o.update(status='RESERVED',reservation_id=res['reservation_id'])
            elif res.get('error')=='INSUFFICIENT_STOCK':
                o['status']='REJECTED_STOCK'
            else:
                raise RuntimeError('reserve')
        elif phase in {'RESERVED','CHARGING'}:
            o['status']='CHARGING'
            o['attempts']+=1
            self.update(o)
            code,res=self.charge(o)
            if code in (200,201):
                o.update(status='CHARGED',charge_id=res['charge_id'])
            elif code==402:
                o['status']='COMPENSATING'
            else:
                raise RuntimeError('charge')
        elif phase=='CHARGED':
            o['status']='CONFIRMED'
        elif phase in {'CANCEL_REQUESTED','COMPENSATING'}:
            # Replay uncertain operations with their original durable identities.
            # This resolves a commit whose response was lost before compensation.
            origin=o.get('cancel_from')
            if origin=='RESERVING' and not o.get('reservation_id'):
                code,res=self.reserve(o)
                if code in (200,201):
                    o['reservation_id']=res['reservation_id']
                elif res.get('error')!='INSUFFICIENT_STOCK':
                    raise RuntimeError('reconcile reservation')
            if origin=='CHARGING' and not o.get('charge_id'):
                code,res=self.charge(o)
                if code in (200,201):
                    o['charge_id']=res['charge_id']
                elif code!=402:
                    raise RuntimeError('reconcile charge')
            self.update(o)
            if o.get('charge_id'):
                p=o['payload']
                code,res=http(self.args.payment_port,'POST','/refunds',{'charge_id':o['charge_id'],
                    'operation_key':'ref:'+o['order_id'],'amount_cents':p['amount_cents'],'currency':p['currency']})
                if code not in (200,201):
                    raise RuntimeError('refund')
                o['refund_id']=res['refund_id']
                self.update(o)
            if o.get('reservation_id'):
                code,res=http(self.args.inventory_port,'POST','/reservations/'+o['reservation_id']+'/release',
                              {'operation_key':'rel:'+o['order_id']})
                if code!=200 or res['status']!='RELEASED':
                    raise RuntimeError('release')
            o['status']='CANCELLED_BY_CLIENT' if origin else 'CANCELLED_DECLINED'
        o['failures']=0
        o['next_retry']=0
        self.update(o)

    def worker(self):
        while True:
            try:
                with self.lock:
                    with transaction(self.args.socket) as db:
                        rows=db.sql("SELECT value FROM app_state WHERE key LIKE 'order:%'")
                    for row in rows:
                        o=json.loads(row[0])
                        try:
                            self.step(o)
                        except Exception as exc:
                            o['failures']=min(o.get('failures',0)+1,10)
                            o['next_retry']=time.time()+min(.05*2**o['failures'],.4)
                            self.update(o)
                            print(canonical({'event':'retry_pending','order_id':o['order_id'],
                                             'error':type(exc).__name__}),flush=True)
            except Exception as exc:
                print(canonical({'event':'worker_error','error':type(exc).__name__}),flush=True)
            time.sleep(.03)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--service',choices=['order','inventory','payment'],required=True)
    parser.add_argument('--socket',required=True)
    parser.add_argument('--port',type=int,required=True)
    parser.add_argument('--payment-port',type=int,default=8084)
    parser.add_argument('--inventory-port',type=int,default=8082)
    args=parser.parse_args()
    app=App(args)
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self): self.handle_request()
        def do_POST(self): self.handle_request()
        def handle_request(self):
            self.connection.settimeout(2)
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<=size<=8192: raise ValueError('size')
                body=json.loads(self.rfile.read(size)) if size else {}
                code,result=app.dispatch(self.command,self.path,body)
            except (ValueError,KeyError,TypeError,IndexError):
                code,result=400,{'error':'invalid_request'}
            except Exception:
                code,result=503,{'error':'temporarily_unavailable'}
            raw=canonical(result).encode()
            try:
                self.send_response(code)
                self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            except OSError: pass
        def log_message(self,*_): pass
    if args.service=='order':
        threading.Thread(target=app.worker,daemon=True).start()
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()


if __name__=='__main__': main()
