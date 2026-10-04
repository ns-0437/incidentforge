import json
import unittest
from unittest.mock import patch
from tests import test_t4
from incidentforge.investigation import feedback,validate_plan
from incidentforge.records import action
from incidentforge.controller import Controller
from incidentforge.budget import Budget
from incidentforge.evidence import Evidence

class T5Tests(unittest.TestCase):
    def test_feedback_excludes_private_details(self):
        result=feedback({'complete':True,'decision':'reject_behavior','secret':'hidden',
            'cases':[{'case':'private schedule','properties':{'P1':{'status':'fail','reason':'secret'},
            'P2':{'status':'pass'}},'path':'private'}]})
        self.assertEqual(['P1'],result['failed_properties'])
        self.assertNotIn('secret',json.dumps(result))
        self.assertNotIn('private',json.dumps(result))

    def test_interpretation_requires_nonempty_fields(self):
        with self.assertRaises(ValueError): action(json.dumps({'action':'interpret','conclusion':'',
            'supported':'a','weakened':'b','uncertainty':'c'}))
        with self.assertRaises(ValueError): validate_plan({'hypotheses':[],'experiment':{}})

class SourceEvidenceTests(unittest.TestCase):
    def plan(self):
        h={'mechanism':'cause','symbols':['step'],'supporting_refs':['L1'],
           'counterevidence':[],'alternatives':[],'predicted_signatures':[],
           'distinguishing_experiment':'identity_probe','confidence_basis':'limited'}
        return {'hypotheses':[dict(h),dict(h)],'experiment':{
            'question':'q','baseline':'b','reset':'fresh','intervention':'identity_probe',
            'controlled_variables':[],'workload':'w','predictions':{'one':{'H1':'yes','H2':'no'}},
            'repetitions':1,'reason':'r','limits':{'seconds':100}}}

    def test_empty_source_quotes_cannot_ground_a_hypothesis(self):
        for quote in ('', ' ', '\t', '\n'):
            with self.subTest(quote=quote):
                plan=self.plan();plan['hypotheses'][0]['supporting_refs']=[quote]
                with self.assertRaisesRegex(ValueError,'non-whitespace'):
                    validate_plan(plan,conditions={'one'},source='def step():\n    return\n')

    def test_hypotheses_must_refer_to_the_experiment_actually_selected(self):
        plan=self.plan();plan['hypotheses'][1]['distinguishing_experiment']='compensation_probe'
        with self.assertRaisesRegex(ValueError,'selected distinguishing experiment'):
            validate_plan(plan,conditions={'one'},source='def step():\n    return\n')

    def test_valid_source_line_and_quote_remain_accepted(self):
        plan=self.plan();plan['hypotheses'][1]['supporting_refs']=['    return']
        result=validate_plan(plan,conditions={'one'},source='def step():\n    return\n')
        self.assertEqual(['L1: def step():'],result['hypotheses'][0]['supporting_refs'])
        self.assertEqual(['    return'],result['hypotheses'][1]['supporting_refs'])

class GateTests(unittest.TestCase):
    setUp=test_t4.T4Tests.setUp
    def test_b2_refuses_patch_before_interpretation(self):
        app=self.root/'candidate/fixture/app';app.mkdir(parents=True)
        for name in ('service.py','common.py','contract.py'): (app/name).write_text('x=1\n')
        (self.root/'candidate/CONTRACT.md').write_text('contract')
        (self.root/'candidate/INCIDENT.json').write_text('{}')
        class Backend:
            image='test';name='test-double';count=0
            def run(self,path,mode):
                self.count+=1
                return {'complete':True}
        class Model:
            def call(self,messages):
                return json.dumps({'action':'replace','path':'fixture/app/service.py',
                    'old':'x=1','new':'x=2','reason':'unsupported guess'})
        e=Evidence(self.root/'e','r')
        with patch('incidentforge.investigation.investigate',return_value={'measured_result':'test'}):
            result=Controller('r',self.root/'candidate',e,Backend(),Model(),
                Budget(self.root/'b.db',200000),variant='B2').run()
        self.assertEqual('unresolved',result['decision'])
        self.assertEqual(0,result['edits'])
        self.assertEqual('x=1\n',(app/'service.py').read_text())

if __name__=='__main__': unittest.main()
