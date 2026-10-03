"""Private local development schedules and harmful-control acceptance."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from fixture.app.common import http
from fixture.harness.t2 import World,ROOT,PORTS,UIDS,read_rows
from evaluation.verifier import evaluate
from fixture.harness.persistence.v2 import Session

LINUX=sys.platform=='linux' and os.geteuid()==0
RESULTS=[]


@unittest.skipUnless(LINUX,'requires isolated Linux root launcher')
class ContractTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='if-t2-')
        Path(self.temp.name).chmod(0o755)
        self.addCleanup(self.temp.cleanup)
        self.worlds=[]
        self.addCleanup(lambda:[w.close() for w in self.worlds])

    def world(self,**kwargs):
        w=World(Path(self.temp.name)/str(len(self.worlds)),**kwargs)
        self.worlds.append(w)
        return w.start()

    def boundary(self,w):
        probe='''
import json,os,socket
from pathlib import Path
from fixture.app.common import DB
paths=json.loads(__import__('sys').argv[1])
checks={}
for path in paths:
    try: Path(path).read_bytes()
    except PermissionError: checks[path]=True
    else: raise AssertionError('private read allowed: '+path)
try:
    with open('fixture/app/service.py','ab') as f: f.write(b'tamper')
except PermissionError: checks['bundle_write']=True
else: raise AssertionError('source writable')
try: DB(__import__('sys').argv[2])
except PermissionError: checks['other_socket']=True
else: raise AssertionError('other broker reachable')
try: os.setuid(0)
except PermissionError: checks['root']=True
else: raise AssertionError('root available')
s=socket.socket();s.settimeout(.2)
try: s.connect(('192.0.2.1',443))
except OSError: checks['egress']=True
else: raise AssertionError('egress allowed')
status=Path('/proc/self/status').read_text()
for name in ('CapEff','CapPrm','CapBnd','CapAmb','CapInh'):
    assert int(next(x.split()[1] for x in status.splitlines() if x.startswith(name+':')),16)==0
assert 'NoNewPrivs:\\t1' in status
checks['capabilities']=True
print(json.dumps(checks))
'''
        paths=[str(ROOT/'evaluation/controls.py'),str(ROOT/'evaluation/verifier.py'),
               str(w.db('order')),str(w.db('inventory')),str(w.db('payment')),str(w.event_file),
               '/proc/1/mem']
        proc=subprocess.run([sys.executable,str(ROOT/'fixture/harness/launch.py'),str(UIDS['order']),
                             str(w.bundle),'-c',probe,json.dumps(paths),str(w.sock('payment'))],
                            capture_output=True,text=True,timeout=5)
        self.assertEqual(0,proc.returncode,proc.stderr)
        receipt=json.loads(proc.stdout)
        self.assertEqual(set(w.bundle_hashes),{str(p.relative_to(w.bundle)) for p in w.bundle.rglob('*') if p.is_file()})
        for name,sha in w.bundle_hashes.items(): self.assertEqual(sha,hashlib.sha256((w.bundle/name).read_bytes()).hexdigest())
        receipt['bundle_allowlist']=True
        return receipt

    def verdict(self,w,name,decision='accept_for_review',required=()):
        receipt=self.boundary(w)
        output=Path(os.environ.get('T2_OUTPUT',self.temp.name))/name
        w.export(output)
        sha=hashlib.sha256((output/'manifest.json').read_bytes()).hexdigest()
        report=evaluate(output,sha,receipt)
        report['case']=name
        report['boundary']=receipt
        report['manifest_sha256']=sha
        (output/'validation.json').write_text(json.dumps(report,indent=2))
        RESULTS.append(report)
        self.assertEqual(decision,report['decision'],report)
        for prop in required: self.assertEqual('fail',report['properties'][prop]['status'],report)
        return output,sha,receipt

    def test_reference_clean_canonical_replay_decline_stock_and_cancel_conflict(self):
        w=self.world()
        original=[{'sku':'B','qty':1},{'sku':'A','qty':1},{'sku':'A','qty':1}]
        self.assertEqual(202,w.submit(items=original)[0])
        self.assertEqual('CONFIRMED',w.observe()['status'])
        replay=w.submit(items=[{'sku':'A','qty':2},{'sku':'B','qty':1}])
        self.assertEqual(200,replay[0])
        self.assertEqual(409,w.submit(amount_cents=999)[0])
        self.assertEqual(409,w.cancel()[0])
        w.submit('decline',expect='decline',customer_id='CUST-DECLINE')
        self.assertEqual('CANCELLED_DECLINED',w.observe('decline')['status'])
        w.restart('inventory')
        reservation={'order_id':'decline','operation_key':'rsv:decline','items':[{'sku':'A','qty':1}]}
        self.assertEqual((200,{'reservation_id':'rsv:decline','status':'RELEASED'}),
                         http(PORTS['inventory'],'POST','/reservations',reservation))
        self.assertEqual(409,http(PORTS['inventory'],'POST','/reservations',
                                  {**reservation,'items':[{'sku':'A','qty':2}]})[0])
        for _ in range(2):
            self.assertEqual(200,http(PORTS['inventory'],'POST','/reservations/rsv:decline/release',
                                     {'operation_key':'rel:decline'})[0])
        w.submit('stock',expect='stock_reject',items=[{'sku':'A','qty':100}])
        self.assertEqual('REJECTED_STOCK',w.observe('stock')['status'])
        w.protocol_checks.append({'name':'canonical replay and conflicts','passed':True})
        self.verdict(w,'reference-clean')

    def test_reference_lost_response_payment_restart(self):
        w=self.world(fault=True,pause=True)
        w.submit()
        self.assertTrue(w.dropped.wait(4))
        w.restart('payment')
        w.release.set()
        self.assertEqual('CONFIRMED',w.observe()['status'])
        self.verdict(w,'reference-response-loss-restart')

    def test_cancellation_reconciles_lost_charge_and_survives_order_restart(self):
        w=self.world(fault=True,pause=True)
        w.submit()
        self.assertTrue(w.dropped.wait(4))
        self.assertEqual(202,w.cancel()[0])
        self.assertEqual(200,w.cancel()[0])
        w.restart('order')
        w.release.set()
        self.assertEqual('CANCELLED_BY_CLIENT',w.observe()['status'])
        self.verdict(w,'reference-cancel-uncertain-payment')

    def test_reference_concurrent_orders_and_stock_contention(self):
        w=self.world(stock={'A':2,'B':2})
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda n:w.submit('o'+str(n),expect='contention'),range(4)))
        self.assertTrue(all(r[0]==202 for r in results))
        statuses=[w.observe('o'+str(n))['status'] for n in range(4)]
        self.assertEqual(2,statuses.count('CONFIRMED'))
        self.assertEqual(2,statuses.count('REJECTED_STOCK'))
        self.verdict(w,'reference-stock-contention')

    def payment_case(self,w,concurrent=False):
        body={'order_id':'direct','payment_intent_id':'direct','operation_key':'same-key',
              'customer_id':'CUST-OK','amount_cents':100,'currency':'USD'}
        w.registry['direct']={'expect':'payment_only','payload':{'amount_cents':100,'currency':'USD','customer_id':'CUST-OK'}}
        if concurrent:
            with ThreadPoolExecutor(max_workers=2) as pool:
                results=list(pool.map(lambda _:http(PORTS['payment'],'POST','/charges',body),range(2)))
        else:
            results=[http(PORTS['payment'],'POST','/charges',body)]
            # Same process first, then a real Payment restart.
            replay=http(PORTS['payment'],'POST','/charges',body)
            self.assertEqual(results[0][1],replay[1])
            w.restart('payment')
            results.append(http(PORTS['payment'],'POST','/charges',body))
        self.assertTrue(all(r[0] in (200,201) for r in results),results)
        w.protocol_checks.append({'name':'charge effect identity across concurrency/restart',
                                  'passed':results[0][1]==results[1][1]})
        return body,results

    def test_reference_payment_concurrency_restart_conflict_and_refund(self):
        w=self.world()
        body,results=self.payment_case(w,concurrent=True)
        self.assertEqual(results[0][1],results[1][1])
        w.restart('payment')
        self.assertEqual(results[0][1],http(PORTS['payment'],'POST','/charges',body)[1])
        self.assertEqual(409,http(PORTS['payment'],'POST','/charges',{**body,'currency':'EUR'})[0])
        refund={'operation_key':'refund-direct','charge_id':results[0][1]['charge_id'],'amount_cents':100,'currency':'USD'}
        code,first=http(PORTS['payment'],'POST','/refunds',refund)
        self.assertEqual(201,code)
        w.restart('payment')
        self.assertEqual((200,first),http(PORTS['payment'],'POST','/refunds',refund))
        self.assertEqual(409,http(PORTS['payment'],'POST','/refunds',{**refund,'amount_cents':99})[0])
        self.verdict(w,'reference-payment-protocol')

    def test_all_five_harmful_controls_and_unpatched_incident(self):
        cases=[('fresh_key',True,('P1',)),('no_recovery',True,('P3',)),
               ('always_success',False,('P2',)),('cancel_all',False,('P3',))]
        for control,fault,required in cases:
            with self.subTest(control=control):
                w=self.world(control=control,fault=fault)
                w.submit()
                w.observe(timeout=1.5 if control=='no_recovery' else 4)
                self.verdict(w,'negative-'+control,'reject_behavior',required)
        for control,concurrent in [('memory_dedup',False),('race_claim',True)]:
            with self.subTest(control=control):
                w=self.world(control=control)
                self.payment_case(w,concurrent)
                self.verdict(w,'negative-'+control,'reject_behavior',('P1','P6'))

    def test_always_success_also_rejected_on_decline(self):
        w=self.world(control='always_success')
        w.submit('decline',expect='decline',customer_id='CUST-DECLINE')
        w.observe('decline')
        self.verdict(w,'negative-success-decline','reject_behavior',('P2','P4'))

    def test_delete_attempt_denied_logged_and_not_accepted(self):
        w=self.world(control='delete_effect')
        w.submit()
        w.observe(timeout=.6)
        self.verdict(w,'negative-delete-effect','reject_behavior',('P7','P3'))

    def test_incomplete_or_tampered_evidence_never_passes(self):
        w=self.world()
        w.submit();w.observe()
        output,sha,receipt=self.verdict(w,'evidence-integrity')
        self.assertEqual('invalid_evaluation',evaluate(output,sha,{})['decision'])
        self.assertEqual('invalid_evaluation',evaluate(output,'0'*64,receipt)['decision'])
        original=(output/'payment.db').read_bytes()
        try:
            with (output/'payment.db').open('ab') as f: f.write(b'corruption')
            self.assertEqual('invalid_evaluation',evaluate(output,sha,receipt)['decision'])
        finally: (output/'payment.db').write_bytes(original)

    def test_transient_inventory_violation_cannot_be_hidden_by_final_snapshot(self):
        w=self.world()
        w.submit();w.observe()
        s=Session(w.db('inventory'),'inventory')
        try:
            for available in (-1,9):
                s.request({'op':'begin'})
                value={'A':{'initial':10,'held':1,'available':available},'B':{'initial':10,'held':0,'available':10}}
                s.request({'op':'execute','sql':"UPDATE app_state SET value=? WHERE key='stock'",'params':[json.dumps(value)]})
                s.request({'op':'commit'})
        finally: s.close()
        self.verdict(w,'negative-transient-inventory','reject_behavior',('P5',))

    def test_malformed_candidate_state_is_rejected_without_crashing_verifier(self):
        w=self.world()
        w.submit();w.observe()
        s=Session(w.db('inventory'),'inventory')
        try:
            s.request({'op':'begin'})
            s.request({'op':'execute','sql':"UPDATE app_state SET value=? WHERE key='stock'",'params':['not-json']})
            s.request({'op':'commit'})
        finally: s.close()
        self.verdict(w,'negative-malformed-state','reject_behavior',('P2',))

    def test_decline_compensation_recovers_after_crash_before_release(self):
        w=self.world()
        # Stop Payment before accepting a decline; reservation can complete.
        w.services['payment'].send_signal(signal.SIGSTOP)
        w.submit('decline',expect='decline',customer_id='CUST-DECLINE')
        end=time.monotonic()+4
        while time.monotonic()<end:
            rows=read_rows(w.db('order'),"SELECT value FROM app_state WHERE key='order:decline'")
            if rows and json.loads(rows[0]['value'])['status']=='CHARGING': break
            time.sleep(.005)
        else: self.fail('charging barrier not reached')
        w.services['inventory'].send_signal(signal.SIGSTOP)
        w.services['payment'].send_signal(signal.SIGCONT)
        end=time.monotonic()+4
        while time.monotonic()<end:
            rows=read_rows(w.db('order'),"SELECT value FROM app_state WHERE key='order:decline'")
            if rows and json.loads(rows[0]['value'])['status']=='COMPENSATING': break
            time.sleep(.005)
        else: self.fail('compensation barrier not reached')
        w.log({'event':'durable_compensation_barrier','order_id':'decline'})
        w.restart('order')
        w.services['inventory'].send_signal(signal.SIGCONT)
        self.assertEqual('CANCELLED_DECLINED',w.observe('decline')['status'])
        self.verdict(w,'reference-compensation-restart')
