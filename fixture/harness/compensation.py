"""Trusted development schedule: committed intent before a crash, no release commit."""
import json
import signal
import time
from .t2 import read_rows

def state(w,service,key):
    rows=read_rows(w.db(service),'SELECT value FROM app_state WHERE key='+"'"+key+"'")
    return json.loads(rows[0]['value']) if rows else None

def wait_phase(w,oid,phase,seconds=4):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        value=state(w,'order','order:'+oid)
        if value and value['status']==phase: return value
        time.sleep(.005)
    raise RuntimeError('durable phase barrier not reached: '+phase)

def decline_restart(w,oid='decline',timeout=2):
    w.services['payment'].send_signal(signal.SIGSTOP)
    code,_=w.submit(oid,expect='decline',customer_id='CUST-DECLINE')
    if code!=202: raise RuntimeError('decline not accepted')
    wait_phase(w,oid,'CHARGING')
    w.services['inventory'].send_signal(signal.SIGSTOP)
    w.services['payment'].send_signal(signal.SIGCONT)
    order=wait_phase(w,oid,'COMPENSATING')
    reservation=state(w,'inventory','reservation:'+order['reservation_key'])
    if not reservation or reservation['result']['status']!='HELD':
        raise RuntimeError('pre-release hold barrier absent')
    audit=read_rows(w.db('order'),"SELECT seq,tx,value FROM _state_audit WHERE key='order:"+oid+"' ORDER BY seq")
    committed=[r for r in audit if r['value'] and json.loads(r['value']).get('status')=='COMPENSATING']
    if not committed: raise RuntimeError('committed compensation intent not audited')
    w.log({'event':'durable_compensation_barrier','order_id':oid,'audit_seq':committed[-1]['seq'],
           'transaction':committed[-1]['tx'],'reservation_status':'HELD'})
    old=w.services['order'];old.kill();old.wait(timeout=3)
    # Drop queued requests from the dead Order process. SIGCONT alone could let
    # an old release complete and hide the missing recovery defect.
    w.restart('inventory')
    start=time.monotonic()
    w.start_service('order')
    startup=time.monotonic()-start
    w.log({'event':'compensation_recovery_start','order_id':oid,'deadline_seconds':timeout,
           'old_order_pid':old.pid,'new_order_pid':w.services['order'].pid,
           'inventory_restart_reason':'discard in-flight pre-crash requests; durable store retained'})
    observed=w.observe(oid,timeout=max(.001,timeout-startup))
    elapsed=time.monotonic()-start
    w.log({'event':'compensation_recovery_observed','elapsed_seconds':elapsed,'order_id':oid,
           'status':observed.get('status') if observed else None})
    return {'order':observed,'reservation':state(w,'inventory','reservation:'+order['reservation_key']),
            'elapsed_seconds':elapsed,'startup_seconds':startup,
            'clock_origin':'before Order process launch; includes readiness',
            'deadline_seconds':timeout,'durable_barrier':True}
