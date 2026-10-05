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

def accepted_receipt():
    return {'complete':True,'decision':'accept_for_review','tests_run':1,
            'errors':0,'failures':0,'skipped':0,'cases':[{
                'case':'scripted-case','decision':'accept_for_review',
                'boundary':{'scripted-isolation-check':True},
                'properties':{f'P{i}':{'status':'pass'} for i in range(1,8)}}]}

class RemoteFailureArchiveTests(unittest.TestCase):
    setUp=test_t4.T4Tests.setUp

    def test_failed_runner_archive_is_retained_without_claiming_success(self):
        import importlib.util,io,tarfile,hashlib,types,sys
        from pathlib import Path
        payload=b'diagnostic archive bytes';digest=hashlib.sha256(payload).hexdigest()
        tar=io.BytesIO()
        with tarfile.open(fileobj=tar,mode='w') as archive:
            info=tarfile.TarInfo('evidence.zip');info.size=len(payload);archive.addfile(info,io.BytesIO(payload))
        state={'status':'SUCCESS','result_image_uuid':'snapshot','metadata':{'result':{
            'state':{'exit_code':1},'stdout':{'truncated':False,'value':json.dumps({'exit_code':1,'bytes':len(payload),'sha256':digest})}}}}
        class Client:
            def get_operation_status(self,*args,**kwargs): return types.SimpleNamespace(to_dict=lambda:state)
            def inspect_image_archive(self,*args,**kwargs): return [tar.getvalue()]
        modules={name:types.ModuleType(name) for name in ('contree_client','contree_client.sync','contree_client.runtime','contree_client.models')}
        modules['contree_client.sync'].ContreeClient=types.SimpleNamespace(from_profile=lambda **kwargs:Client())
        modules['contree_client.runtime'].RetryPolicy=lambda **kwargs:None
        modules['contree_client.models'].FileSpec=object;modules['contree_client.models'].InstanceNetworking=object
        script=Path(__file__).resolve().parents[1]/'scripts/contree-execute.py'
        request=self.root/'request.json';guard=self.root/'guard.json'
        request.write_text(json.dumps({'output':str(self.root),'guard':str(guard),'cancel':str(self.root/'CANCEL')}))
        guard.write_text(json.dumps({'output':str(self.root)}));(self.root/'launch.json').write_text('{"uuid":"operation"}')
        with patch.dict(sys.modules,modules),patch('sys.argv',[str(script),str(request),'--recover']):
            spec=importlib.util.spec_from_file_location('failed_export',script)
            runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
            self.assertEqual(1,runner.main())
        self.assertEqual(payload,(self.root/'evidence.zip').read_bytes())
        self.assertEqual(1,json.loads((self.root/'receipt.json').read_text())['runner_exit_code'])
        self.assertTrue(json.loads((self.root/'error.json').read_text())['terminal_confirmed'])
        self.assertFalse(guard.exists())

class EditCompileTests(unittest.TestCase):
    setUp=test_t4.T4Tests.setUp

    def test_ast_parseable_but_uncompilable_edit_is_rejected_without_writing(self):
        from incidentforge.workspace import EditSyntaxError
        import ast
        root=self.root/'candidate';folder=root/'fixture/app';folder.mkdir(parents=True)
        source='def step():\n    raise RuntimeError("release")\n'
        file=folder/'service.py';file.write_text(source)
        proposed='def step():\n    break\n'
        ast.parse(proposed)
        with self.assertRaises(EditSyntaxError) as caught:
            Workspace(root).replace('fixture/app/service.py','raise RuntimeError("release")','break')
        self.assertIn('outside loop',str(caught.exception))
        self.assertFalse(caught.exception.context['applied'])
        self.assertEqual(source,file.read_text())

class RegressionQualityTests(unittest.TestCase):
    def test_baseline_assessment_distinguishes_weak_and_discriminating_tests(self):
        from fixture.harness.developer_tests import assess
        baseline={'observations':[{'condition':'restart','order':{'status':'COMPENSATING','attempts':2}}]}
        weak={'assertions':[{'name':'retries','condition':'restart','path':'order.attempts','equals':2}]}
        strong={'assertions':[{'name':'recovers','condition':'restart','path':'order.status','equals':'CANCELLED_DECLINED'}]}
        self.assertTrue(assess(weak,baseline)['passed'])
        self.assertFalse(assess(strong,baseline)['passed'])
        repaired={'observations':[{'condition':'restart','order':{'status':'CANCELLED_DECLINED','attempts':2}}]}
        self.assertTrue(assess(strong,repaired)['passed'])
        self.assertEqual('COMPENSATING',baseline['observations'][0]['order']['status'])

class ActionSchemaTests(unittest.TestCase):
    def test_assertion_pairs_use_only_actual_developer_targets(self):
        from incidentforge.action_schema import action_format
        fmt=action_format(['read','developer_test','finish'],[
            {'condition':'clean','fields':[{'path':'order.status'}]},
            {'condition':'response_loss','fields':[{'path':'order.status'},{'path':'stock.A'}]}],{})
        variants=fmt['json_schema']['schema']['anyOf']
        test=next(v for v in variants if v['properties']['action']['enum']==['developer_test'])
        spec=test['properties']['spec']
        self.assertEqual(['assertions'],spec['required'])
        pairs=spec['properties']['assertions']['items']['anyOf']
        self.assertEqual(['clean'],pairs[0]['properties']['condition']['enum'])
        self.assertEqual(['order.status'],pairs[0]['properties']['path']['enum'])
        self.assertNotIn('same_key_restart',json.dumps(fmt))
        self.assertFalse(spec['additionalProperties'])

    def test_unavailable_actions_and_missing_targets_are_not_offered(self):
        from incidentforge.action_schema import action_format
        fmt=action_format(['read','developer_test'],[],{})
        variants=fmt['json_schema']['schema']['anyOf']
        self.assertEqual([['read']],[v['properties']['action']['enum'] for v in variants])

class StartupReportTests(unittest.TestCase):
    setUp=test_t4.T4Tests.setUp

    def test_backend_failure_is_visible_and_spends_nothing(self):
        import importlib.util,shutil,contextlib,io
        from pathlib import Path
        project=Path(__file__).resolve().parents[1]
        spec=importlib.util.spec_from_file_location('run_t4_startup',project/'scripts/run-t4.py')
        runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
        for folder in ('fixture/app','contracts/public'):
            shutil.copytree(project/folder,self.root/folder)
        runner.ROOT=self.root
        with patch('sys.argv',['run-t4.py','--live','--backend','contree']),patch('incidentforge.remote_backend.ContreeBackend',side_effect=RuntimeError('SECRET_ERROR')),patch.object(runner,'Nebius') as model,contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(1,runner.main())
        model.assert_not_called()
        report=json.loads(next((self.root/'runs').glob('*/report.json')).read_text())
        self.assertEqual('backend_startup',report['failure_stage'])
        self.assertEqual(0,report['accounting']['calls'])
        self.assertNotIn('SECRET_ERROR',output.getvalue())
        run=self.root/'runs'/report['run_id']
        self.assertEqual(3,verify(run))
        from incidentforge.ui import details
        self.assertEqual('verified',details(self.root,report['run_id'])['integrity'])

class SetupPreflightTests(unittest.TestCase):
    setUp=test_t4.T4Tests.setUp

    def test_pending_ledger_blocks_without_changing_accounting(self):
        from incidentforge.preflight import inspect
        (self.root/'runs').mkdir()
        budget=Budget(self.root/'runs/t4-budget.sqlite',200000)
        budget.reserve('pending',17695,200000,10)
        before=budget.totals('pending')
        with patch('incidentforge.preflight.reader_preflight',return_value='image'),patch('incidentforge.preflight.credential',return_value='SECRET_TEST_VALUE'):
            result=inspect(self.root,'docker')
        self.assertFalse(result['ready_for_preflighted_launch'])
        self.assertNotIn('SECRET_TEST_VALUE',json.dumps(result))
        self.assertEqual(before,budget.totals('pending'))

    def test_unconfigured_checkout_stays_unmodified_and_reports_missing_access(self):
        from incidentforge.preflight import inspect
        with patch('incidentforge.preflight.reader_preflight',side_effect=RuntimeError('Start Docker')),patch('incidentforge.preflight.credential',side_effect=RuntimeError('SECRET_TEST_VALUE')):
            result=inspect(self.root,'docker')
        self.assertFalse(result['ready_for_preflighted_launch'])
        self.assertFalse((self.root/'runs').exists())
        self.assertNotIn('SECRET_TEST_VALUE',json.dumps(result))
        checks={c['check']:c for c in result['checks']}
        self.assertFalse(checks['inference_credential']['ready'])
        self.assertFalse(checks['allocation']['detail']['ledger_exists'])

class StructuredInvestigationTests(unittest.TestCase):
    setUp=test_t4.T4Tests.setUp

    def test_format_reaches_provider_and_is_retained_in_evidence(self):
        from incidentforge.investigation import investigation_format
        fmt=investigation_format('compensation_probe',['no_restart','order_restart'],['step'],'def step():\n    return\n')
        budget=Budget(self.root/'b.db',200000);evidence=Evidence(self.root/'e','r')
        model=Nebius(budget,'r',evidence)
        response={'usage':{'prompt_tokens':10,'completion_tokens':10},
                  'choices':[{'message':{'content':'{}'},'finish_reason':'stop'}]}
        with patch('incidentforge.llm.request_once',return_value=json.dumps(response).encode()) as request:
            self.assertEqual('{}',model.call([],response_format=fmt))
        self.assertEqual(fmt,request.call_args.args[0]['response_format'])
        event=json.loads((evidence.root/'events.jsonl').read_text().splitlines()[0])
        ref=event['payload']['response_format']
        self.assertEqual(fmt,json.loads((evidence.root/'artifacts'/ref['sha256']).read_text()))
        self.assertEqual(2,verify(evidence.root))
        self.assertEqual(1,budget.totals('r')['calls'])

    def test_provider_citations_exclude_blank_and_nonexistent_lines(self):
        from incidentforge.investigation import investigation_format
        fmt=investigation_format('identity_probe',['one'],['step'],'\ndef step():\n    \n    return\n')
        allowed=fmt['json_schema']['schema']['properties']['hypotheses']['items']['properties']['supporting_refs']['items']['enum']
        self.assertEqual(['L2','L4'],allowed)

    def test_oversized_schema_is_rejected_before_reservation(self):
        budget=Budget(self.root/'b.db',200000);evidence=Evidence(self.root/'e','r')
        with patch('incidentforge.llm.request_once') as request:
            with self.assertRaisesRegex(ValueError,'payload byte bound'):
                Nebius(budget,'r',evidence).call([],response_format={'description':'x'*110000})
            request.assert_not_called()
        self.assertEqual(0,budget.totals('r')['calls'])

class PromptGuidanceTests(unittest.TestCase):
    def test_only_latest_contract_retained_without_losing_evidence(self):
        from incidentforge.controller import latest_action_contract
        original=[{'role':'system','content':'rules'},
            {'role':'user','content':json.dumps({'tool_result':{'observation':'failed'},'action_contract':{'remaining_edits':3}})},
            {'role':'assistant','content':'exact proposed edit'},
            {'role':'user','content':json.dumps({'error':'no match','current_source':'verbatim source','action_contract':{'remaining_edits':2}})}]
        before=json.dumps(original);result=latest_action_contract(original)
        self.assertEqual(before,json.dumps(original))
        old=json.loads(result[1]['content']);self.assertNotIn('action_contract',old)
        self.assertEqual({'observation':'failed'},old['tool_result'])
        self.assertEqual(original[0],result[0]);self.assertEqual(original[2:],result[2:])
        self.assertEqual(result,latest_action_contract(result))

    def test_repeated_large_guidance_no_longer_accumulates(self):
        from incidentforge.controller import latest_action_contract
        from incidentforge.records import encoded
        messages=[{'role':'user','content':json.dumps({'tool_result':i,'action_contract':{'context':'x'*7000}})} for i in range(10)]
        result=latest_action_contract(messages)
        self.assertLess(len(encoded(result)),10000)
        self.assertEqual(list(range(10)),[json.loads(m['content'])['tool_result'] for m in result])
        self.assertEqual(1,sum('action_contract' in json.loads(m['content']) for m in result))

class FinalReceiptTests(unittest.TestCase):
    def test_valid_acceptance_and_applicable_exemptions(self):
        from incidentforge.grounding import final_decision
        result=accepted_receipt()
        for prop in ('P2','P6'): result['cases'][0]['properties'][prop]['status']='not_applicable'
        self.assertEqual('accept_for_review',final_decision(result))

    def test_empty_duplicate_mismatched_and_failed_cases_rejected(self):
        from incidentforge.grounding import final_decision
        for mode in ('empty','duplicate','count','case-failure','property-failure','boundary','missing-property','errors'):
            result=accepted_receipt()
            if mode=='empty': result['cases']=[]
            elif mode=='duplicate': result['cases']*=2;result['tests_run']=2
            elif mode=='count': result['tests_run']=2
            elif mode=='case-failure': result['cases'][0]['decision']='reject_behavior'
            elif mode=='property-failure': result['cases'][0]['properties']['P4']['status']='fail'
            elif mode=='boundary': result['cases'][0]['boundary']={'check':1}
            elif mode=='missing-property': del result['cases'][0]['properties']['P7']
            else: result['errors']=1
            with self.subTest(mode=mode):self.assertEqual('invalid_evaluation',final_decision(result))

    def test_incomplete_and_unknown_verdicts_cannot_accept(self):
        from incidentforge.grounding import final_decision
        for complete in (False,1,'true',None):
            result=accepted_receipt();result['complete']=complete
            self.assertEqual('invalid_evaluation',final_decision(result))
        self.assertEqual('invalid_evaluation',final_decision({'complete':True,'decision':'invented'}))
        self.assertEqual('reject_behavior',final_decision({'complete':True,'decision':'reject_behavior'}))

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
                result={**accepted_receipt(),
                        'observations':[{'condition':'clean','order':{'status':'CONFIRMED'}}]}
                if mode=='developer':
                    from fixture.harness.developer_tests import execute
                    result['developer_tests']=execute(path/'developer-tests.json',result)
                return result
        class Model:
            history=[]
            def call(self,messages,**kwargs):
                self.history.append(json.loads(json.dumps(messages)))
                command=next(commands)
                return command(messages) if callable(command) else json.dumps(command)
        model=Model();e=Evidence(self.root/'e','r');backend=Backend()
        with patch('incidentforge.investigation.investigate',return_value={'measured_facts':measured or {}}):
            report=Controller('r',root,e,backend,model,Budget(self.root/'b.db',200000),variant=variant).run()
        verify(e.root)
        return report,model,backend

    def test_investigator_sees_import_records_and_measured_dependencies(self):
        """The index reaches the model, and the bundle records measured provenance."""
        report,model,_=self.run_actions(iter([{'action':'finish','summary':'stop'}]*3))
        index=None
        for turn in model.history:
            for message in turn:
                if message['role']=='user' and 'source_index' in message['content']:
                    index=json.loads(message['content'])['source_index'];break
            if index: break
        self.assertIsNotNone(index,'the repository index never reached the model')
        for path,entry in index.items():
            self.assertIn('symbols',entry,path)
            self.assertIn('imports',entry,'import records were not exposed for '+path)
            self.assertIsInstance(entry['imports'],list)
        records=json.loads((self.root/'e'/'records.json').read_text())
        bundle=next(r['data'] for r in records if r['kind']=='IncidentBundle')
        provenance=bundle['config']['dependency_provenance']
        self.assertEqual([],provenance['external_modules'])
        self.assertIn('not measured',provenance['runtime_interpreter'])
        self.assertNotIn('3.12',json.dumps(provenance))
        # lock_hash is now derived from that provenance, not a hardcoded literal.
        from incidentforge.records import digest
        self.assertEqual(digest(provenance),bundle['lock_hash'])

    def test_contradictory_final_acceptance_remains_invalid(self):
        report,_,_=self.run_actions(iter([
            {'action':'replace','path':'fixture/app/service.py','old':'x=1','new':'x=2','reason':'repair'},
            {'action':'developer_test','spec':{'assertions':[{'name':'regression','condition':'clean','path':'order.status','equals':'CONFIRMED'}]},'reason':'cover outcome'},{'action':'test'},
            {'action':'finish','summary':'candidate for review'}]),protected={
                'complete':True,'decision':'accept_for_review','cases':[]})
        self.assertEqual('invalid_evaluation',report['decision'])
        self.assertIsNotNone(report['candidate_revision'])
        self.assertIn('inconsistent',report['reason'])

    def test_syntax_rejection_supplies_proposed_context_without_applying_edit(self):
        def check(messages):
            correction=json.loads(messages[-1]['content'])
            rejected=correction['rejected_proposal']
            self.assertFalse(rejected['applied'])
            self.assertIn('    pass',rejected['proposed_source_excerpt'])
            self.assertEqual(0,correction['action_contract']['applied_edits'])
            self.assertEqual('x=1\n',(self.root/'candidate/fixture/app/service.py').read_text())
            self.assertEqual(['read'],correction['action_contract']['allowed_actions'])
            return json.dumps({'action':'read','path':'fixture/app/service.py'})
        report,_,_=self.run_actions(iter([
            {'action':'replace','path':'fixture/app/service.py','old':'x=1','new':'# removed block\n    pass','reason':'invalid indentation'},
            check,{'action':'replace','path':'fixture/app/service.py','old':'x=1','new':'x=2','reason':'valid correction'},
            {'action':'developer_test','spec':{'assertions':[{'name':'regression','condition':'clean','path':'order.status','equals':'CONFIRMED'}]},'reason':'cover outcome'},{'action':'test'},{'action':'finish','summary':'corrected syntax'}]))
        self.assertEqual(2,report['edits'])
        self.assertEqual('accept_for_review',report['decision'])

    def test_rejected_edit_requires_read_of_affected_file(self):
        report,model,_=self.run_actions(iter([
            {'action':'replace','path':'fixture/app/service.py','old':'not present','new':'x=2','reason':'bad match'},
            {'action':'read','path':'fixture/app/common.py'},
            {'action':'replace','path':'fixture/app/service.py','old':'x=1','new':'x=2','reason':'skip required read'}]))
        self.assertEqual(0,report['edits'])
        self.assertEqual('unresolved',report['decision'])
        self.assertIn('Read fixture/app/service.py after the rejected edit',json.dumps(model.history))
        self.assertEqual('x=1\n',(self.root/'candidate/fixture/app/service.py').read_text())

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

    def test_source_edit_without_authored_regression_cannot_freeze(self):
        report,model,_=self.run_actions(iter([
            {'action':'replace','path':'fixture/app/service.py','old':'x=1','new':'x=2','reason':'repair'},
            *[{'action':'finish','summary':'skip tests'}]*3]))
        self.assertIsNone(report['candidate_revision'])
        self.assertEqual('unresolved',report['decision'])
        self.assertIn('Author developer regression tests',json.dumps(model.history))

    def test_failing_authored_assertions_cannot_freeze(self):
        report,_,_=self.run_actions(iter([
            {'action':'replace','path':'fixture/app/service.py','old':'x=1','new':'x=2','reason':'repair'},
            {'action':'developer_test','spec':{'assertions':[{'name':'wrong','condition':'clean','path':'order.status','equals':'PENDING'}]},'reason':'test'},
            {'action':'test'},*[{'action':'finish','summary':'ignore failed assertion'}]*3]))
        self.assertIsNone(report['candidate_revision'])
        self.assertTrue(report['verified_work']['developer_tests_executed_on_current_revision'])
        self.assertFalse(report['verified_work']['developer_tests_passed_on_current_revision'])

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
            {'action':'developer_test','spec':{'assertions':[{'name':'regression','condition':'clean','path':'order.status','equals':'CONFIRMED'}]},'reason':'cover outcome'},{'action':'test'},{'action':'finish','summary':'edited and tested'}]),'B1',expected)
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

    def test_incomplete_protected_feedback_stops_without_more_calls_or_freeze(self):
        measured={'condition':{'committed_charge_count':1}}
        def interpret(messages):
            return json.dumps(json.loads(messages[-1]['content'])['action_contract']['interpret_fields'])
        commands=iter([interpret,
            {'action':'replace','path':'fixture/app/service.py','old':'x=1','new':'x=2','reason':'repair'},
            {'action':'validate'}, {'action':'finish','summary':'must not be requested'}])
        report,model,backend=self.run_actions(commands,'B2',measured,
            {'complete':False,'decision':'invalid_evaluation','cases':[], 'secret':'private schedule'})
        self.assertEqual('unresolved',report['decision'])
        self.assertIn('Protected feedback incomplete',report['reason'])
        self.assertEqual(1,report['protected_feedback_requests'])
        self.assertFalse(report['protected_feedback']['complete'])
        self.assertNotIn('private schedule',json.dumps(report))
        self.assertIsNone(report['candidate_revision'])
        self.assertEqual(3,len(model.history))
        self.assertEqual(2,backend.count)
        self.assertEqual('finish',next(commands)['action'])

    def test_b2_cannot_exceed_the_single_allowed_feedback_request(self):
        measured={'condition':{'committed_charge_count':1}}
        def interpret(messages):
            return json.dumps(json.loads(messages[-1]['content'])['action_contract']['interpret_fields'])
        def refused(messages):
            self.assertIn('protected feedback limit',json.loads(messages[-1]['content'])['error'])
            return json.dumps({'action':'finish','summary':'second feedback refused'})
        commands=iter([interpret,
            {'action':'replace','path':'fixture/app/service.py','old':'x=1','new':'x=2','reason':'repair'},
            {'action':'validate'},{'action':'validate'},refused,
            {'action':'finish','summary':'done'}])
        report,model,backend=self.run_actions(commands,'B2',measured,
            {'complete':True,'decision':'accept_for_review','cases':[]})
        self.assertEqual(1,report['protected_feedback_requests'])
        self.assertIsNone(report['candidate_revision'])

    def test_source_change_after_passing_tests_invalidates_their_applicability(self):
        authored={'action':'developer_test','spec':{'assertions':[{'name':'a','condition':'clean',
            'path':'order.status','equals':'CONFIRMED'}]},'reason':'regression'}
        commands=iter([
            {'action':'replace','path':'fixture/app/service.py','old':'x=1','new':'x=2','reason':'repair'},
            authored,{'action':'test'},
            {'action':'replace','path':'fixture/app/service.py','old':'x=2','new':'x=3','reason':'second edit'},
            {'action':'finish','summary':'tests passed earlier'},
            {'action':'finish','summary':'still stale'}])
        report,_,_=self.run_actions(commands)
        self.assertIsNone(report['candidate_revision'])
        self.assertFalse(report['verified_work']['developer_tests_executed_on_current_revision'])

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
            self.assertIn('Review the failed properties',guidance['completion_instruction'])
            return '{"action":"finish","summary":"revision still needs verification"}'
        rejected={'complete':True,'decision':'reject_behavior','cases':[{'case':'secret-case','properties':{'P1':{'status':'fail','reason':'secret'}}}]}
        report,_,_=self.run_actions(iter([interpret,{'action':'replace','path':'fixture/app/service.py','old':'x=1','new':'x=2','reason':'initial'},
            {'action':'validate'},review,
            {'action':'developer_test','spec':{'assertions':[{'name':'regression','condition':'clean','path':'order.status','equals':'CONFIRMED'}]},'reason':'test'},
            {'action':'test'},finish]),'B2',measured,rejected)
        self.assertEqual('reject_behavior',report['decision'])
        self.assertFalse(report['protected_feedback']['candidate_unchanged_since_feedback'])

    def test_assertion_target_checks_do_not_require_expected_value_to_pass(self):
        from fixture.harness.developer_tests import validate_targets
        spec={'assertions':[{'name':'recover','condition':'fault','path':'order.status','equals':'CONFIRMED'}]}
        validate_targets(spec,[{'fault':'fault','order':{'status':'PENDING'}}])
        spec['assertions'][0]['path']='order.invented'
        with self.assertRaises(ValueError):validate_targets(spec,[{'fault':'fault','order':{'status':'PENDING'}}])

    def test_target_catalog_excludes_ambiguous_conditions_and_experiment_fields(self):
        from fixture.harness.developer_tests import target_catalog
        result=target_catalog([{'fault':'none','order':{'status':'PENDING'},'count':1},
            {'condition':'duplicate','x':1},{'condition':'duplicate','x':2}])
        self.assertEqual([{'condition':'none','fields':[{'path':'count','observed_type':'int'},
            {'path':'fault','observed_type':'str'},{'path':'order.status','observed_type':'str'}]}],result)
        self.assertNotIn('committed_charge_count',json.dumps(result))

    def test_target_catalog_is_bounded(self):
        from fixture.harness.developer_tests import target_catalog
        result=target_catalog([{'condition':str(i),**{str(j):j for j in range(100)}} for i in range(30)])
        self.assertEqual(12,len(result));self.assertTrue(all(len(c['fields'])<=64 for c in result))

    def test_post_feedback_flow_preserves_identical_test_execution(self):
        measured={'condition':{'committed_charge_count':1}}
        spec={'assertions':[{'name':'a','condition':'clean','path':'order.status','equals':'CONFIRMED'}]}
        authored={'action':'developer_test','spec':spec,'reason':'regression'}
        def interpret(messages):return json.dumps(json.loads(messages[-1]['content'])['action_contract']['interpret_fields'])
        def run_test(messages):
            g=json.loads(messages[-1]['content'])['action_contract']
            self.assertEqual(0,g['remaining_protected_feedback_requests'])
            self.assertNotIn('validate',g['allowed_actions']);self.assertNotIn('finish',g['allowed_actions'])
            self.assertFalse(g['finish_ready'])
            return '{"action":"test"}'
        def repeat(messages):
            g=json.loads(messages[-1]['content'])['action_contract']
            self.assertTrue(g['finish_ready']);self.assertIn('finish',g['allowed_actions'])
            return json.dumps({**authored,'spec':json.dumps(spec,sort_keys=True,indent=2)})
        def finish(messages):
            data=json.loads(messages[-1]['content'])
            self.assertTrue(data['tool_result']['unchanged']);self.assertFalse(data['tool_result']['edit_consumed'])
            self.assertTrue(data['action_contract']['tests_executed_on_current_revision'])
            return '{"action":"finish","summary":"edited and tested; awaiting independent verification"}'
        report,_,backend=self.run_actions(iter([interpret,{'action':'replace','path':'fixture/app/service.py','old':'x=1','new':'x=2','reason':'repair'},
            authored,{'action':'validate'},run_test,repeat,finish]),'B2',measured)
        self.assertEqual('accept_for_review',report['decision']);self.assertEqual(2,report['edits'])
        self.assertEqual(4,backend.count)  # reproduction, feedback, test, final verification

    def test_changed_expected_type_invalidates_test_revision(self):
        spec={'assertions':[{'name':'a','condition':'clean','path':'order.status','equals':1}]}
        changed={'assertions':[{'name':'a','condition':'clean','path':'order.status','equals':True}]}
        report,_,_=self.run_actions(iter([
            {'action':'replace','path':'fixture/app/service.py','old':'x=1','new':'x=2','reason':'repair'},
            {'action':'developer_test','spec':spec,'reason':'test'},{'action':'test'},
            {'action':'developer_test','spec':changed,'reason':'different assertion'},
            *[{'action':'finish','summary':'done'}]*3]))
        self.assertIsNone(report['candidate_revision']);self.assertEqual(3,report['edits'])
        self.assertFalse(report['verified_work']['developer_tests_executed_on_current_revision'])

if __name__=='__main__':unittest.main()

class AllocationTests(unittest.TestCase):
    def test_existing_allocation_keeps_ledger_and_hard_ceiling(self):
        import tempfile,sqlite3
        from pathlib import Path
        from incidentforge.budget import BudgetExceeded
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'budget.sqlite'
            b=Budget.existing(path)
            token=b.reserve('old',100,200000,10);b.settle(token,80)
            with sqlite3.connect(path) as db: db.execute('UPDATE settings SET cap=400000')
            db.close()
            b=Budget.existing(path)
            self.assertEqual(b.totals('old')['reserved_or_spent_microusd'],80)
            token=b.reserve('new',399920,400000,10);b.settle(token,399920)
            with self.assertRaises(BudgetExceeded): b.reserve('next',1,400000,10)
            with sqlite3.connect(path) as db: db.execute('UPDATE settings SET cap=400001')
            db.close()
            with self.assertRaises(ValueError): Budget.existing(path)

class TraceTests(unittest.TestCase):
    def test_only_executed_lines_without_local_values(self):
        import sys,tempfile
        from pathlib import Path
        from fixture.harness.trace_runtime import Recorder
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'candidate.py'
            source="def step(flag):\n    secret='DO_NOT_CAPTURE'\n    if flag:\n        return\n    return 7\n"
            scope={};exec(compile(source,str(target),'exec'),scope)
            rows=[];recorder=Recorder(target,rows.append)
            previous=sys.gettrace()
            try:
                sys.settrace(recorder.trace)
                for _ in range(4): scope['step'](True)
            finally: sys.settrace(previous)
            self.assertTrue(any(r['event']=='return' and r['line']==4 for r in rows))
            self.assertFalse(any(r['line']==5 for r in rows))
            self.assertEqual(len(rows),len({(r['event'],r['line']) for r in rows}))
            self.assertNotIn('DO_NOT_CAPTURE',json.dumps(rows))

    def test_trace_reader_rejects_malformed_and_wrong_process_rows(self):
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace
        from fixture.harness.trace_observation import observation
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);app=root/'public/fixture/app';app.mkdir(parents=True)
            (app/'service.py').write_text('def step():\n    return\n')
            rows=['broken','[]','{"pid":9,"line":2,"event":"return"}',
                  '{"pid":1,"line":true,"event":"line"}','{"pid":1,"line":99,"event":"line"}',
                  '{"pid":1,"line":2,"event":"return"}']
            (root/'order-service.log').write_text(''.join('IF_TRACE_V1 '+r+'\n' for r in rows))
            result=observation(SimpleNamespace(root=root,bundle=root/'public',started_ids=[{'service':'order','pid':1}]))
            self.assertEqual([{'event':'return','line':2,'source':'    return'}],result['processes'][0]['events'])
            self.assertIn('spoofed',result['trust'])

class SymbolFeedbackTests(unittest.TestCase):
    def test_symbol_catalog_excludes_data_keys_and_operation_strings(self):
        from incidentforge.investigation import source_symbols
        source="class App:\n    def step(self, order):\n        self.pending.add(order['reservation_id'])\n        return 'release'\n"
        symbols=source_symbols(source)
        self.assertEqual(['App','add','order','pending','self','step'],symbols)
        self.assertNotIn('reservation_id',symbols)
        self.assertNotIn('release',symbols)

    def test_first_investigation_prompt_supplies_exact_validator_vocabulary(self):
        import tempfile,json
        from pathlib import Path
        from types import SimpleNamespace
        from incidentforge.investigation import investigate,source_symbols
        source="def step(order):\n    return order['reservation_id']\n"
        class Captured(Exception): pass
        class Model:
            def call(inner,messages,**kwargs):
                fmt=kwargs['response_format']
                self.assertEqual('json_schema',fmt['type'])
                schema=fmt['json_schema']['schema']
                self.assertEqual(['hypotheses','experiment'],schema['required'])
                references=schema['properties']['hypotheses']['items']['properties']['supporting_refs']['items']['enum']
                self.assertEqual(['L1','L2'],references)
                prediction=schema['properties']['experiment']['properties']['predictions']
                self.assertEqual({'no_restart','order_restart','release_replay','release_replay_inventory_restart'},set(prediction['required']))
                payload=json.loads(messages[-1]['content'])
                self.assertEqual(source_symbols(source),payload['allowed_source_symbols'])
                self.assertIn('selected verbatim from allowed_source_symbols',messages[0]['content'])
                raise Captured()
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'service.py';file.write_text(source)
            workspace=SimpleNamespace(read=lambda name: source if name=='fixture/app/service.py' else '{}',
                                      revision=lambda:'baseline',path=lambda name:file)
            controller=SimpleNamespace(workspace=workspace,backend=SimpleNamespace(incident='IF-002'),model=Model())
            with self.assertRaises(Captured): investigate(controller,{'observations':[]})

    def test_invalid_identifiers_report_exact_choices_without_accepting_them(self):
        from incidentforge.investigation import validate_plan
        h={'mechanism':'cause','symbols':['invented'],'supporting_refs':['L1'],
           'counterevidence':[],'alternatives':[],'predicted_signatures':[],
           'distinguishing_experiment':'identity_probe','confidence_basis':'limited'}
        experiment={'question':'q','baseline':'b','reset':'fresh','intervention':'identity_probe',
                    'controlled_variables':[],'workload':'w','predictions':{'one':{'H1':'yes','H2':'no'}},
                    'repetitions':1,'reason':'r','limits':{'seconds':100}}
        with self.assertRaises(ValueError) as caught:
            validate_plan({'hypotheses':[dict(h),dict(h)],'experiment':experiment},
                          conditions={'one'},source='def step(order):\n    return order\n')
        self.assertIn("Invalid: ['invented']",str(caught.exception))
        self.assertIn('Choose only from: order, step',str(caught.exception))

class TraceFocusTests(unittest.TestCase):
    def sample(self):
        import hashlib
        source=b"def step(order):\n    phase=order['status']\n    if phase=='PENDING':\n        return\n    finish()\n"
        observations=[{'condition':'restart','execution_trace':{
            'source_sha256':hashlib.sha256(source).hexdigest(),'processes':[
            {'generation':0,'events':[{'event':'return','line':5}]},
            {'generation':1,'events':[{'event':'return','line':4,'source':'FORGED SOURCE'},
                                    {'event':'return','line':4},{'event':'line','line':5}]}]}}]
        return source,observations
    def test_focus_separates_generations_and_uses_actual_source(self):
        from incidentforge.trace_focus import focus
        source,obs=self.sample();value=focus(obs,source)
        processes=value['conditions'][0]['processes']
        self.assertEqual([0,1],[p['generation'] for p in processes])
        returns=processes[1]['observed_returns']
        self.assertEqual(1,len(returns));self.assertEqual(4,returns[0]['line'])
        self.assertNotIn('FORGED SOURCE',json.dumps(value))
        self.assertIn("if phase=='PENDING':",json.dumps(value))
        self.assertIn('Untrusted',value['trust'])
    def test_source_change_hides_stale_trace_locations(self):
        from incidentforge.trace_focus import focus
        source,obs=self.sample();row=focus(obs,source+b'# edited\n')['conditions'][0]
        self.assertFalse(row['source_matches']);self.assertEqual([],row['processes'])
    def test_trace_focus_bounds_and_marks_incomplete_input(self):
        from incidentforge.trace_focus import focus
        source,obs=self.sample();trace=obs[0]['execution_trace'];trace['log_truncated']=True
        trace['processes'][1]['event_limit_reached']=True
        trace['processes'][1]['events'] += [{'event':'return','line':True},{'event':'return','line':9999}]
        row=focus(obs,source)['conditions'][0]
        self.assertTrue(row['log_truncated']);self.assertTrue(row['processes'][1]['event_limit_reached'])
        self.assertEqual(1,len(row['processes'][1]['observed_returns']))

class ReconciliationTests(unittest.TestCase):
    setUp=test_t4.T4Tests.setUp
    def sample(self,terminal=True):
        from incidentforge.evidence import Evidence
        path=self.root/'runs';path.mkdir(exist_ok=True)
        b=Budget(path/'t4-budget.sqlite',400000);token=b.reserve('timeout',17695,200000,10)
        e=Evidence(path/'timeout','timeout')
        e.event('model_reserved',{'reservation':token,'maximum_microusd':17695})
        reason='TimeoutError: Inference wall-time cap; usage unknown, no retry'
        if terminal:
            e.event('stopped',{'reason':reason})
            e.event('report',{'run_id':'timeout','decision':'unresolved','reason':reason})
        return b,token,e
    def test_preview_then_atomic_reconciliation_preserves_unknown_cost(self):
        from incidentforge.reconciliation import reconcile
        from contextlib import closing
        import sqlite3
        b,token,e=self.sample();before=b.path.read_bytes()
        preview=reconcile(self.root,'timeout')
        self.assertFalse(preview['applied']);self.assertEqual(before,b.path.read_bytes())
        with self.assertRaises(ValueError): reconcile(self.root,'timeout',apply=True)
        receipt=reconcile(self.root,'timeout',apply=True,authority='test authorization')
        self.assertEqual(17695,receipt['exposure_microusd'])
        with closing(sqlite3.connect(b.path)) as db:
            self.assertEqual((None,'conservative_unknown'),db.execute('SELECT actual,status FROM calls WHERE id=?',(token,)).fetchone())
            self.assertEqual(1,db.execute('SELECT COUNT(*) FROM timeout_reconciliations').fetchone()[0])
            self.assertEqual(400000,db.execute('SELECT cap FROM settings').fetchone()[0])
        with self.assertRaises(ValueError): reconcile(self.root,'timeout',apply=True,authority='duplicate')
        self.assertEqual(17695,b.totals('timeout')['reserved_or_spent_microusd'])
        from incidentforge.ui import budget_status
        status=budget_status(self.root)
        self.assertEqual(.017695,status['reserved_usd'])
        self.assertEqual(.017695,status['unknown_usd'])
        self.assertEqual(0,status['estimated_usd'])
        self.assertEqual(0,status['pending'])
        self.assertEqual(1,status['unknown_calls'])
    def test_nonterminal_and_tampered_evidence_cannot_clear_pending(self):
        from incidentforge.reconciliation import reconcile
        b,token,e=self.sample(terminal=False)
        with self.assertRaises(ValueError): reconcile(self.root,'timeout',apply=True,authority='test')
        self.assertEqual(1,b.totals('timeout')['unknown_or_pending'])
        (e.root/'events.jsonl').write_text('{}\n')
        with self.assertRaises((ValueError,KeyError)): reconcile(self.root,'timeout',apply=True,authority='test')
        self.assertEqual(1,b.totals('timeout')['unknown_or_pending'])
    def test_settled_call_cannot_be_reclassified_unknown(self):
        from incidentforge.reconciliation import reconcile
        b,token,e=self.sample();b.settle(token,100)
        with self.assertRaises(ValueError): reconcile(self.root,'timeout',apply=True,authority='test')
        self.assertEqual(100,b.totals('timeout')['reserved_or_spent_microusd'])

class VerifierPreflightTests(unittest.TestCase):
    def test_missing_daemon_stops_before_remote_work(self):
        import subprocess,sys,tempfile
        from pathlib import Path
        from incidentforge.remote_backend import ContreeBackend
        with tempfile.TemporaryDirectory() as temp:
            evidence=Mock();evidence.root=Path(temp)
            with patch.dict('os.environ',{'CONTREE_PYTHON':sys.executable}), patch(
                    'incidentforge.remote_backend.subprocess.run',side_effect=subprocess.CalledProcessError(1,['docker'])) as run:
                with self.assertRaisesRegex(RuntimeError,'Start Docker Desktop'):
                    ContreeBackend(Path(temp),evidence)
                self.assertEqual(1,run.call_count)
                evidence.event.assert_not_called()
    def test_linux_image_is_pinned_at_startup(self):
        import sys,tempfile
        from pathlib import Path
        from incidentforge.remote_backend import ContreeBackend
        with tempfile.TemporaryDirectory() as temp:
            evidence=Mock();evidence.root=Path(temp);image='sha256:'+'a'*64
            with patch.dict('os.environ',{'CONTREE_PYTHON':sys.executable}), patch(
                    'incidentforge.remote_backend.subprocess.run',side_effect=[Mock(stdout='linux'),Mock(stdout=image)]):
                backend=ContreeBackend(Path(temp),evidence)
            self.assertEqual(image,backend.reader_image);self.assertEqual(0,backend.count)
            self.assertEqual('verifier_preflight',evidence.event.call_args.args[0])
    def test_wrong_os_or_invalid_image_fails_closed(self):
        from incidentforge.remote_backend import reader_preflight
        for outputs in ([Mock(stdout='windows')],[Mock(stdout='linux'),Mock(stdout='sha256:bad')]):
            with patch('incidentforge.remote_backend.subprocess.run',side_effect=outputs):
                with self.assertRaises(RuntimeError): reader_preflight()

class GuardReferenceTests(unittest.TestCase):
    def test_return_guard_links_initialization_and_updates_without_known_bug_names(self):
        import hashlib
        from incidentforge.trace_focus import focus
        source=b"class Worker:\n    def __init__(self):\n        self.queue=set()\n    def enqueue(self,key):\n        self.queue.add(key)\n    def step(self,key):\n        if key not in self.queue:\n            return\n        send(key)\n"
        obs=[{'condition':'restart','execution_trace':{'source_sha256':hashlib.sha256(source).hexdigest(),
             'processes':[{'generation':1,'events':[{'event':'return','line':8}]}]}}]
        value=focus(obs,source);guard=value['conditions'][0]['processes'][0]['observed_returns'][0]['enclosing_guards'][0]
        self.assertEqual(7,guard['guard_line'])
        refs=guard['attribute_references'][0]
        self.assertEqual('self.queue',refs['attribute'])
        self.assertEqual([3,5,7],[r['line'] for r in refs['source_references']])
        self.assertIn('not proof',value['static_scope'])
    def test_ordinary_function_return_does_not_invent_guard(self):
        import hashlib
        from incidentforge.trace_focus import focus
        source=b'def step():\n    return 7\n'
        obs=[{'execution_trace':{'source_sha256':hashlib.sha256(source).hexdigest(),
             'processes':[{'events':[{'event':'return','line':2}]}]}}]
        self.assertEqual([],focus(obs,source)['conditions'][0]['processes'][0]['observed_returns'][0]['enclosing_guards'])
