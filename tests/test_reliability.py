"""Post-T8 regressions; scripted doubles make no efficacy claims about live models."""
import json
from unittest.mock import patch,Mock
from tests import test_t4
import unittest
from incidentforge.controller import Controller
from incidentforge.records import action
from incidentforge.grounding import check_interpretation,factual_conclusion
from incidentforge.evidence import Evidence,verify
from incidentforge.budget import Budget
from incidentforge.workspace import Workspace
from incidentforge.llm import Nebius,REQUEST_SECONDS

class ReliabilityTests(unittest.TestCase):
    setUp=test_t4.T4Tests.setUp

    def run_actions(self,commands,variant='B0',measured=None,protected=None):
        root=self.root/'candidate';app=root/'fixture/app';app.mkdir(parents=True)
        for name in ('service.py','common.py','contract.py'): (app/name).write_text('x=1\n')
        (root/'CONTRACT.md').write_text('contract');(root/'INCIDENT.json').write_text('{}')
        class Backend:
            image='test';name='test-double';count=0
            def run(self,path,mode):
                self.count+=1
                if mode=='protected' and protected is not None: return protected
                return {'complete':True,'decision':'accept_for_review','cases':[],
                        'observations':[{'condition':'clean','order':{'status':'CONFIRMED'}}]}
        class Model:
            history=[]
            def call(self,messages):
                self.history.append(json.loads(json.dumps(messages)))
                command=next(commands)
                return command(messages) if callable(command) else json.dumps(command)
        model=Model();e=Evidence(self.root/'e','r');backend=Backend()
        with patch('incidentforge.investigation.investigate',return_value={'measured_facts':measured or {}}):
            report=Controller('r',root,e,backend,model,Budget(self.root/'b.db',200000),variant=variant).run()
        verify(e.root)
        return report,model,backend

    def test_native_objects_keep_exact_factual_gate(self):
        expected={'restart':{'order_status':'COMPENSATING','compensation_complete':False}}
        cmd={'action':'interpret','conclusion':factual_conclusion(expected),'observed_facts':expected,
             'supported':'unverified','weakened':'alternative','uncertainty':'cause unknown'}
        self.assertTrue(check_interpretation(action(json.dumps(cmd)),expected)['facts_verified'])
        cmd['observed_facts']['restart']['compensation_complete']=0
        with self.assertRaises(ValueError):check_interpretation(action(json.dumps(cmd)),{'restart':{'order_status':'COMPENSATING','compensation_complete':False}})

    def test_charge_conclusion_needs_no_nested_json_escaping(self):
        measured={'same_key_restart':{'committed_charge_count':1},'different_keys':{'committed_charge_count':2}}
        conclusion=factual_conclusion(measured)
        self.assertEqual('Measured committed charges: different_keys=2; same_key_restart=1. Causality remains unverified.',conclusion)
        self.assertNotIn('"',conclusion)
        with self.assertRaises(ValueError):check_interpretation({'observed_facts':measured,'conclusion':conclusion.replace('different_keys=2','different_keys=1')},measured)

    def test_bad_action_type_is_recoverable(self):
        with self.assertRaises(ValueError):action('{"action":[]}')
        with self.assertRaises(ValueError):action('{"action":"test","extra":true}')

    def test_no_change_finish_cannot_claim_repair(self):
        report,model,backend=self.run_actions(iter([{'action':'finish','summary':'fixed'}]*3))
        self.assertIsNone(report['candidate_revision']);self.assertEqual('unresolved',report['decision'])
        self.assertEqual([],report['verified_work']['changed_source_paths']);self.assertEqual(1,backend.count)
        self.assertIn('No net source change',json.loads(model.history[1][-1]['content'])['error'])

    def test_reverted_edit_does_not_freeze(self):
        def edit(old,new):return {'action':'replace','path':'fixture/app/service.py','old':old,'new':new,'reason':'test'}
        report,_,_=self.run_actions(iter([edit('x=1','x=2'),edit('x=2','x=1')]+[{'action':'finish','summary':'fixed'}]*3))
        self.assertIsNone(report['candidate_revision']);self.assertEqual(2,report['edits'])

    def test_correction_supplies_exact_interpretation_then_allows_real_edit(self):
        expected={'same_key_sequential':{'committed_charge_count':1}}
        def correct(messages):
            correction=json.loads(messages[-1]['content']);self.assertIn('interpret',correction['action_contract']['allowed_actions'])
            cmd=correction['action_contract']['interpret_fields'];self.assertEqual(expected,cmd['observed_facts'])
            return json.dumps(cmd)
        report,_,_=self.run_actions(iter([
            {'action':'test'},correct,
            {'action':'replace','path':'fixture/app/service.py','old':'x=1','new':'x=2','reason':'repair'},
            {'action':'finish','summary':'one edit; no tests requested'}]),'B1',expected)
        self.assertEqual('accept_for_review',report['decision'])
        self.assertEqual(['fixture/app/service.py'],report['verified_work']['changed_source_paths'])

    def test_unsupported_assertion_operator_rejected_without_writing(self):
        bad={'action':'developer_test','spec':{'assertions':[{'name':'a','condition':'x','path':'order.status','not_equal':''}]},'reason':'test'}
        report,model,_=self.run_actions(iter([bad]*3))
        self.assertFalse(report['verified_work']['developer_test_file_present'])
        self.assertIn('Only equals',json.loads(model.history[1][-1]['content'])['action_contract']['test_operators'])

    def test_noop_replacement_is_not_counted(self):
        cmd={'action':'replace','path':'fixture/app/service.py','old':'x=1','new':'x=1','reason':'claim'}
        report,_,_=self.run_actions(iter([cmd]*3));self.assertEqual(0,report['edits'])

    def test_authored_tests_must_execute_before_finish(self):
        edit={'action':'replace','path':'fixture/app/service.py','old':'x=1','new':'x=2','reason':'repair'}
        authored={'action':'developer_test','spec':{'assertions':[{'name':'a','condition':'clean','path':'order.status','equals':'CONFIRMED'}]},'reason':'regression'}
        def after_refusal(messages):
            self.assertIn('have not run',json.loads(messages[-1]['content'])['error'])
            return '{"action":"test"}'
        report,_,_=self.run_actions(iter([edit,authored,{'action':'finish','summary':'done'},after_refusal,{'action':'finish','summary':'test executed'}]))
        self.assertEqual('accept_for_review',report['decision'])
        self.assertTrue(report['verified_work']['developer_tests_executed_on_current_revision'])

    def test_old_test_run_does_not_cover_new_authored_spec(self):
        commands=[{'action':'test'},
            {'action':'replace','path':'fixture/app/service.py','old':'x=1','new':'x=2','reason':'repair'},
            {'action':'developer_test','spec':{'assertions':[{'name':'a','condition':'clean','path':'order.status','equals':'CONFIRMED'}]},'reason':'test'}]
        report,_,_=self.run_actions(iter(commands+[{'action':'finish','summary':'done'}]*3))
        self.assertIsNone(report['candidate_revision'])
        self.assertFalse(report['verified_work']['developer_tests_executed_on_current_revision'])

    def test_longer_request_still_respects_run_deadline(self):
        b=Budget(self.root/'b.db',200000);e=Evidence(self.root/'e','r');m=Nebius(b,'r',e)
        with patch('incidentforge.llm.time.monotonic',return_value=100),patch('incidentforge.llm.request_once') as request:
            m.deadline=100+REQUEST_SECONDS
            with self.assertRaises(TimeoutError):m.call([])
            request.assert_not_called()
        self.assertEqual(0,b.totals('r')['calls'])

    def test_placeholder_assertion_cannot_be_saved(self):
        bad={'action':'developer_test','spec':{'assertions':[{'name':'description','condition':'observed condition or fault label','path':'observed.field','equals':'expected scalar'}]},'reason':'regression purpose'}
        report,_,_=self.run_actions(iter([bad]*3))
        self.assertFalse(report['verified_work']['developer_test_file_present'])
        self.assertEqual(0,report['edits'])

    def test_failed_feedback_persists_without_private_case_details(self):
        measured={'condition':{'committed_charge_count':1}}
        def interpret(messages):return json.dumps(json.loads(messages[-1]['content'])['action_contract']['interpret_fields'])
        def review(messages):
            guidance=json.loads(messages[-1]['content'])['action_contract']
            self.assertEqual(['P1'],guidance['protected_feedback']['failed_properties'])
            self.assertTrue(guidance['protected_feedback']['candidate_unchanged_since_feedback'])
            self.assertNotIn('secret-case',json.dumps(guidance))
            return json.dumps({'action':'replace','path':'fixture/app/service.py','old':'x=2','new':'x=3','reason':'revise'})
        def finish(messages):
            guidance=json.loads(messages[-1]['content'])['action_contract']
            self.assertFalse(guidance['protected_feedback']['candidate_unchanged_since_feedback'])
            return '{"action":"finish","summary":"revision still needs verification"}'
        rejected={'complete':True,'decision':'reject_behavior','cases':[{'case':'secret-case','properties':{'P1':{'status':'fail','reason':'secret'}}}]}
        report,_,_=self.run_actions(iter([interpret,{'action':'replace','path':'fixture/app/service.py','old':'x=1','new':'x=2','reason':'initial'},
            {'action':'validate'},review,finish]),'B2',measured,rejected)
        self.assertEqual('reject_behavior',report['decision'])
        self.assertFalse(report['protected_feedback']['candidate_unchanged_since_feedback'])

    def test_assertion_target_checks_do_not_require_expected_value_to_pass(self):
        from fixture.harness.developer_tests import validate_targets
        spec={'assertions':[{'name':'recover','condition':'fault','path':'order.status','equals':'CONFIRMED'}]}
        validate_targets(spec,[{'fault':'fault','order':{'status':'PENDING'}}])
        spec['assertions'][0]['path']='order.invented'
        with self.assertRaises(ValueError):validate_targets(spec,[{'fault':'fault','order':{'status':'PENDING'}}])

if __name__=='__main__':unittest.main()
