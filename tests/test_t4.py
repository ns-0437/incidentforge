"""Controller safety/accounting tests. Scripted worker is explicitly not a live agent."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from incidentforge.budget import Budget,BudgetExceeded
from incidentforge.evidence import Evidence,verify
from incidentforge.records import action,record,FIELDS
from incidentforge.workspace import Workspace
from incidentforge.llm import Nebius,CALL_RESERVATION,cost
from incidentforge.controller import Controller

class T4Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def test_reservations_survive_crash_and_block_redispatch(self):
        b=Budget(self.root/'b.db',200000)
        token=b.reserve('r',CALL_RESERVATION,200000,10)
        again=Budget(self.root/'b.db',200000)
        with self.assertRaises(BudgetExceeded): again.reserve('another',1,200000,10)
        self.assertEqual(CALL_RESERVATION,again.totals('r')['reserved_or_spent_microusd'])
        again.settle(token,200)
        self.assertEqual(200,again.totals('r')['estimated_usage_microusd'])
        with self.assertRaises(ValueError): again.settle(token,0)

    def test_concurrent_reservation_does_not_overspend(self):
        b=Budget(self.root/'b.db',100)
        def reserve(_):
            try: return b.reserve('r',70,100,2)
            except BudgetExceeded: return None
        with ThreadPoolExecutor(2) as pool: tokens=list(pool.map(reserve,range(2)))
        self.assertEqual(1,sum(t is not None for t in tokens))

    def test_limits_cannot_be_raised_and_overrun_stops(self):
        b=Budget(self.root/'b.db',100)
        with self.assertRaises(ValueError): Budget(self.root/'b.db',200)
        with self.assertRaises(BudgetExceeded): b.reserve('r',101,100,10)
        t=b.reserve('r',90,100,1)
        with self.assertRaises(BudgetExceeded): b.settle(t,91)
        self.assertEqual(1,b.totals('r')['unknown_or_pending'])

    def test_evidence_tampering_is_detected(self):
        e=Evidence(self.root/'events','r');ref=e.artifact(b'original')
        e.event('test',{'ref':ref});self.assertEqual(1,verify(e.root))
        (e.root/'artifacts'/ref['sha256']).write_bytes(b'changed')
        with self.assertRaises(ValueError): verify(e.root)

    def test_event_order_tampering_is_detected(self):
        e=Evidence(self.root/'events','r');e.event('a',{});e.event('b',{})
        path=e.root/'events.jsonl';lines=path.read_text().splitlines();path.write_text('\n'.join(reversed(lines)))
        with self.assertRaises(ValueError): verify(e.root)

    def test_action_validation_rejects_shell_and_extra_fields(self):
        for obj in ({'action':'shell','command':'dir'},{'action':'test','command':'dir'},
                    {'action':'replace','path':'x','old':'','new':'x','reason':'r'}):
            with self.assertRaises(ValueError): action(json.dumps(obj))
        self.assertEqual({'action':'test'},action('{"action":"test"}'))

    def test_workspace_traversal_and_ambiguous_edits_denied(self):
        app=self.root/'fixture/app';app.mkdir(parents=True)
        (app/'service.py').write_text('x=1\nx=1\n')
        w=Workspace(self.root)
        for path in ('../secret','fixture/harness/t2.py','/etc/passwd'):
            with self.assertRaises(ValueError): w.read(path)
        with self.assertRaises(ValueError): w.replace('fixture/app/service.py','x=1','x=2')
        with self.assertRaises(SyntaxError): w.replace('fixture/app/service.py','x=1\nx=1','!')
        self.assertEqual('x=1\nx=1\n',w.read('fixture/app/service.py'))

    def test_all_record_types_require_complete_fields(self):
        for name in FIELDS:
            with self.assertRaises(ValueError): record(name,'r',{})
        with self.assertRaises(ValueError): record('Invented','r',{})

    def test_usage_pricing_and_reservation_cover_max_output(self):
        self.assertEqual(1,cost(1,1))
        self.assertEqual(300000,cost(1000000,1000000))
        self.assertGreaterEqual(CALL_RESERVATION,cost(262144,8192))

    def test_transport_failure_retains_budget_and_no_retry(self):
        b=Budget(self.root/'b.db',200000);e=Evidence(self.root/'e','r')
        model=Nebius(b,'r',e)
        with patch('incidentforge.llm.request_once',side_effect=TimeoutError) as request:
            with self.assertRaises(TimeoutError): model.call([{'role':'user','content':'test'}])
            self.assertEqual(1,request.call_count)
        self.assertEqual(1,b.totals('r')['unknown_or_pending'])

    def test_controller_never_claims_success_without_validation(self):
        app=self.root/'candidate/fixture/app';app.mkdir(parents=True)
        for name in ('service.py','common.py','contract.py'): (app/name).write_text('x=1\n')
        (self.root/'candidate/CONTRACT.md').write_text('test')
        (self.root/'candidate/INCIDENT.json').write_text('{}')
        class Backend:
            name='test-double';image='test';count=0
            def run(self,path,mode):
                self.count+=1
                if mode=='developer':
                    from fixture.harness.developer_tests import execute
                    result={'complete':True,'observations':[{'condition':'clean','order':{'status':'CONFIRMED'}}]}
                    result['developer_tests']=execute(path/'developer-tests.json',result)
                    return result
                return {'decision':'accept_for_review','complete':False,'cases':[]}
        class Model:
            calls=0
            def call(self,messages,**kwargs):
                self.calls+=1
                if self.calls==1: return json.dumps({'action':'replace','path':'fixture/app/service.py','old':'x=1','new':'x=2','reason':'test change'})
                if self.calls==2: return json.dumps({'action':'developer_test','spec':{'assertions':[{'name':'r','condition':'clean','path':'order.status','equals':'CONFIRMED'}]},'reason':'regression'})
                if self.calls==3: return '{"action":"test"}'
                return '{"action":"finish","summary":"claimed fixed"}'
        b=Budget(self.root/'b.db',200000);e=Evidence(self.root/'e','r')
        report=Controller('r',self.root/'candidate',e,Backend(),Model(),b).run()
        self.assertEqual('invalid_evaluation',report['decision'])
        self.assertGreater(verify(e.root),0)

if __name__=='__main__': unittest.main()
