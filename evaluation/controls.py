"""Private authored controls, applied separately to a known-good source."""

def mutate(source,control):
    if control=='reference': return source
    def replace(old,new):
        nonlocal source
        if source.count(old)!=1: raise ValueError('control target changed: '+control)
        source=source.replace(old,new)
    if control=='fresh_key':
        replace("o['attempts']+=1", "o['attempts']+=1\n            o['payment_key']=str(uuid.uuid4())")
    elif control=='lost_compensation':
        replace('self.lock=threading.RLock()', 'self.lock=threading.RLock()\n        self.pending_compensations=set()')
        replace("o['status']='COMPENSATING'", "o['status']='COMPENSATING'\n                self.pending_compensations.add(o['order_id'])")
        replace("phase=o['status']", "phase=o['status']\n        if phase=='COMPENSATING' and o['order_id'] not in self.pending_compensations:\n            return")
    elif control=='terminal_without_release':
        replace("if o.get('reservation_id'):", "if False and o.get('reservation_id'):")
    elif control=='double_release':
        replace("stock[i['sku']]['available']+=i['qty']", "stock[i['sku']]['available']+=2*i['qty']")
    elif control=='no_recovery':
        replace("if phase in TERMINAL or o.get('next_retry',0)>time.time():",
                "if phase=='CHARGING' or phase in TERMINAL or o.get('next_retry',0)>time.time():")
    elif control=='always_success':
        replace("self.update(o)\n            code,res=self.charge(o)","self.update(o)\n            code,res=200,{'charge_id':'fabricated'}")
    elif control=='cancel_all':
        replace("phase=o['status']", "phase=o['status']\n        if phase=='RECEIVED':\n            o['status']='CANCELLED_BY_CLIENT'\n            self.update(o)\n            return")
    elif control=='memory_dedup':
        replace('self.lock=threading.RLock()', 'self.lock=threading.RLock()\n        self.memo={}')
        replace("previous=db.get(kind+':'+key)","previous=self.memo.get(kind+':'+key)")
        replace("db.put(kind+':'+key,{'payload':payload,'status':201,'result':result})",
                "db.put(kind+':'+key,{'payload':payload,'status':201,'result':result})\n            self.memo[kind+':'+key]={'payload':payload,'status':201,'result':result}")
    elif control=='race_claim':
        replace('import argparse','import argparse\nfrom contextlib import nullcontext')
        replace('self.lock=threading.RLock()', 'self.lock=threading.RLock()\n        self.barrier=threading.Barrier(2)')
        replace('with self.lock:\n            if method',"with (nullcontext() if self.args.service=='payment' else self.lock):\n            if method")
        replace("kind='charge' if path=='/charges' else 'refund'",
                "kind='charge' if path=='/charges' else 'refund'\n        with transaction(self.args.socket) as check:\n            claimed=check.get(kind+':'+key)\n        self.barrier.wait(timeout=3)")
        replace("previous=db.get(kind+':'+key)","previous=claimed")
    elif control=='delete_effect':
        replace("result={'status':'COMMITTED',kind+'_id':effect}",
                "db.sql('DELETE FROM payment_effects WHERE effect_id=?',effect)\n            result={'status':'COMMITTED',kind+'_id':effect}")
    else: raise ValueError(control)
    return source
