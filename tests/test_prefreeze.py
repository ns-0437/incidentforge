"""Regression checks for failures observed in development pilots."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
from unittest.mock import patch,Mock
from tests import test_t4
from incidentforge.grounding import facts,check_interpretation,factual_conclusion
from incidentforge.investigation import validate_plan
from fixture.harness.developer_tests import execute,validate

class PrefreezeTests(unittest.TestCase):
    def test_failed_edit_returns_actual_source_without_modifying_it(self):
        from incidentforge.workspace import Workspace,EditMismatch
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);p=root/'fixture/app/service.py';p.parent.mkdir(parents=True)
            source='def step():\n    if ready:\n        return 1\n    return 0\n'
            p.write_text(source)
            with self.assertRaises(EditMismatch) as caught:
                Workspace(root).replace('fixture/app/service.py','if ready: return 1','return 2')
            self.assertEqual(source,p.read_text())
            self.assertIn('    if ready:\n',caught.exception.context['source_excerpt'])
            self.assertEqual(0,caught.exception.context['exact_match_count'])
            Workspace(root).replace('fixture/app/service.py','return 1','return 2')
            self.assertIn('return 2',p.read_text())

    def test_inference_timeout_kills_worker_without_retry(self):
        from incidentforge.llm import request_once
        child=Mock();child.communicate.side_effect=[subprocess.TimeoutExpired('worker',60),(b'',b'')]
        with patch('incidentforge.llm.subprocess.Popen',return_value=child) as start:
            with self.assertRaises(TimeoutError): request_once({'messages':[]})
        self.assertEqual(1,start.call_count);child.kill.assert_called_once()

    def test_expired_remote_deadline_prevents_dispatch(self):
        from incidentforge.remote_backend import ContreeBackend
        b=object.__new__(ContreeBackend);b.deadline=0
        with self.assertRaises(TimeoutError): b.run(Path('.'),'protected')

    def test_reversed_compensation_facts_rejected(self):
        expected=facts({'observations':[{'condition':'restart','order':{'status':'COMPENSATING'}}]})
        wrong={'restart':{'order_status':'CANCELLED_DECLINED','compensation_complete':True}}
        with self.assertRaises(ValueError): check_interpretation({'observed_facts':json.dumps(wrong)},expected)
        good=check_interpretation({'observed_facts':json.dumps(expected),'conclusion':factual_conclusion(expected)},expected)
        self.assertTrue(good['facts_verified']);self.assertFalse(good['causal_prose_verified'])
        wrong=copy.deepcopy(expected);wrong['restart']['compensation_complete']=0
        with self.assertRaises(ValueError): check_interpretation({'observed_facts':json.dumps(wrong)},expected)

    def test_correct_facts_cannot_accompany_reversed_conclusion(self):
        measured={'no_restart':{'order_status':'CANCELLED_DECLINED','compensation_complete':True},
                  'order_restart':{'order_status':'COMPENSATING','compensation_complete':False}}
        command={'observed_facts':json.dumps(measured),'conclusion':'compensation requires a restart to complete'}
        with self.assertRaises(ValueError): check_interpretation(command,measured)
        command['conclusion']=factual_conclusion(measured)
        self.assertTrue(check_interpretation(command,measured)['facts_verified'])

    def test_plan_references_and_distinction(self):
        h={'mechanism':'retry','symbols':['step'],'supporting_refs':['return 1'],
           'counterevidence':[],'alternatives':['other'],'predicted_signatures':['one'],
           'distinguishing_experiment':'identity_probe','confidence_basis':'unverified'}
        plan={'hypotheses':[h,copy.deepcopy(h)],'experiment':{'question':'which','baseline':'x','reset':'fresh',
          'intervention':'identity_probe','controlled_variables':['key'],'workload':'requests',
          'predictions':{'probe':{'H1':'one','H2':'two'}},'repetitions':1,'reason':'distinguish','limits':{'seconds':100}}}
        def check(p): return validate_plan(p,conditions=['probe'],source='def step():\n    return 1\n')
        check(plan)
        numbered=copy.deepcopy(plan);numbered['hypotheses'][0]['supporting_refs']=['L2']
        self.assertEqual(['L2:     return 1'],check(numbered)['hypotheses'][0]['supporting_refs'])
        numbered=copy.deepcopy(plan);numbered['hypotheses'][0]['supporting_refs']=['L999']
        with self.assertRaises(ValueError): check(numbered)
        for field,value in [('symbols',['invented']),('supporting_refs',['return 2']),('confidence_basis',[])]:
            bad=copy.deepcopy(plan);bad['hypotheses'][0][field]=value
            with self.assertRaises(ValueError): check(bad)
        bad=copy.deepcopy(plan);bad['experiment']['predictions']['probe']['H2']='one'
        with self.assertRaises(ValueError): check(bad)
        bad=copy.deepcopy(plan);bad['hypotheses'].append(h)
        with self.assertRaises(ValueError): check(bad)

    def test_developer_assertions_are_independent_and_strict(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'tests.json'
            spec={'assertions':[{'name':'completed','condition':'restart','path':'order.status','equals':'CANCELLED_DECLINED'}]}
            p.write_text(json.dumps(spec))
            observed={'observations':[{'condition':'restart','order':{'status':'COMPENSATING'}}]}
            self.assertFalse(execute(p,observed)['passed'])
            observed['observations'][0]['order']['status']='CANCELLED_DECLINED'
            self.assertTrue(execute(p,observed)['passed'])
            spec['assertions'][0].update(path='order.missing',equals=None);p.write_text(json.dumps(spec))
            self.assertFalse(execute(p,observed)['passed'])
            spec['assertions'][0]['path']='__import__(os)'
            with self.assertRaises(ValueError): validate(spec)

if __name__=='__main__': unittest.main()
