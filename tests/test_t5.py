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

    def test_wrong_investigation_envelope_gets_actionable_replacement_request(self):
        with self.assertRaises(ValueError) as caught:
            validate_plan({'bugs':[], 'bugs_found':0})
        message=str(caught.exception)
        self.assertIn('exactly hypotheses and experiment',message)
        self.assertIn("['bugs', 'bugs_found']",message)
        self.assertIn('replacement investigation JSON',message)

    def test_feedback_requires_literal_completion(self):
        for value in (False, None, 0, 1, 'true', 'false', {}, []):
            with self.subTest(value=value):
                self.assertFalse(feedback({'complete':value,'cases':[]})['complete'])
        self.assertTrue(feedback({'complete':True,'cases':[]})['complete'])

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

class ExperimentCompletenessTests(unittest.TestCase):
    conditions=['same_key_sequential','same_key_restart','same_key_concurrent','different_keys']

    def result(self):
        return {'complete':True,'observations':[
            {'condition':name,'committed_charge_count':count}
            for name,count in zip(self.conditions,[1,1,1,2])]}

    def test_unique_complete_measurements_accept_any_order(self):
        from incidentforge.grounding import experiment_facts
        result=self.result();result['observations'].reverse()
        measured=experiment_facts(result,self.conditions)
        self.assertEqual(set(self.conditions),set(measured))
        self.assertEqual(2,measured['different_keys']['committed_charge_count'])

    def test_duplicate_missing_and_unexpected_conditions_fail_closed(self):
        from incidentforge.grounding import experiment_facts
        for mode in ('duplicate','missing','unexpected'):
            result=self.result()
            if mode=='duplicate': result['observations'][-1]=dict(result['observations'][0])
            elif mode=='missing': result['observations'].pop()
            else: result['observations'][-1]['condition']='invented'
            with self.subTest(mode=mode),self.assertRaisesRegex(ValueError,'exactly once'):
                experiment_facts(result,self.conditions)

    def test_incomplete_malformed_and_unmeasured_results_rejected(self):
        from incidentforge.grounding import experiment_facts
        for complete in (False,1,'true',None):
            result=self.result();result['complete']=complete
            with self.subTest(complete=complete),self.assertRaises(ValueError):
                experiment_facts(result,self.conditions)
        for observations in ({},[None],[{'condition':[]}],
                             [{'condition':name} for name in self.conditions]):
            with self.subTest(observations=observations),self.assertRaises(ValueError):
                experiment_facts({'complete':True,'observations':observations},self.conditions)

    def test_investigator_does_not_publish_duplicate_experiment_as_complete(self):
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace
        from incidentforge.investigation import investigate
        plan=SourceEvidenceTests().plan()
        plan['experiment']['predictions']={name:{'H1':'one','H2':'two'} for name in self.conditions}
        bad=self.result();bad['observations'][-1]=dict(bad['observations'][0])
        emitted=[]
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'service.py';file.write_text('def step():\n    return\n')
            workspace=SimpleNamespace(root=Path(tmp),read=lambda name:file.read_text() if name=='fixture/app/service.py' else '{}',
                                      path=lambda name:file,revision=lambda:'baseline')
            controller=SimpleNamespace(workspace=workspace,model=SimpleNamespace(call=lambda messages:json.dumps(plan)),
                backend=SimpleNamespace(run=lambda root,mode:bad,count=1,name='test'),
                emit=lambda kind,data:emitted.append(kind))
            with self.assertRaisesRegex(ValueError,'exactly once'): investigate(controller,{'observations':[]})
        self.assertEqual(['Hypothesis','Hypothesis','ExperimentSpec'],emitted)

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
