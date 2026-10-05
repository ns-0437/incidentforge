"""HTTP, launch/cancel, export and rendering-data boundaries. No paid calls."""
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from incidentforge.ui import Manager,make_server,details,export_run,run_path
from incidentforge.evidence import Evidence
from incidentforge.records import record
from incidentforge.budget import Budget

class UITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.terminal=threading.Event();self.spawned=[]
        owner=self
        class Process:
            def wait(self): owner.terminal.wait(5);return 0
        def spawn(run_id,incident,variant,backend,log):
            self.spawned.append(run_id);(self.root/'runs'/run_id).mkdir();return Process()
        self.manager=Manager(self.root,spawn)
        self.server=make_server(self.root,0,self.manager)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url='http://127.0.0.1:'+str(self.server.server_port)
        self.addCleanup(self.stop)
    def stop(self):
        self.terminal.set();self.server.shutdown();self.server.server_close();self.thread.join()
        end=time.time()+2
        while self.manager.guard.exists() and time.time()<end: time.sleep(.01)
    def request(self,path,body=None,token=None,origin=None):
        headers={}
        if token: headers['X-IncidentForge-Token']=token
        if origin: headers['Origin']=origin
        request=urllib.request.Request(self.url+path,data=json.dumps(body).encode() if body else None,headers=headers)
        with urllib.request.urlopen(request) as response: return response.status,response.read(),response.headers
    def token(self): return json.loads(self.request('/api/state')[1])['token']
    def evidence(self):
        e=Evidence(self.root/'runs'/'sample','sample')
        e.event('transition',{'from':'VERIFY','to':'REPORT'})
        e.event('model_interpretation',{'conclusion':'<script>alert(1)</script> → raw data'})
        data={'candidate_hash':'abc','evaluator_version':'dev','conditions':'development','properties':[{'PRIVATE_CASE':{'P4':{'status':'fail','reasons':['PRIVATE_SCHEDULE']}}}],
              'boundary_status':'pass','costs':{},'decision':'reject_behavior','limitations':[]}
        e.event('record',{'record':e.artifact(record('ValidationReport','sample',data))})
        report={'run_id':'sample','variant':'B1','decision':'reject_behavior','reason':'independent failure','model_claim_unverified':'claim','accounting':{'calls':1}}
        e.event('report',report)
        (e.root/'report.json').write_text(json.dumps(report))
        (e.root/'secret.env').write_text('NEVER_EXPORT')
        return e
    def test_host_origin_and_token_boundaries(self):
        for token,origin in [(None,None),(self.token(),'https://untrusted.invalid')]:
            with self.assertRaises(urllib.error.HTTPError) as cm:
                self.request('/api/launch',{'incident':'IF-001','variant':'B0'},token,origin)
            self.assertEqual(403,cm.exception.code)
        self.assertEqual([],self.spawned)
    def test_launch_double_launch_cancel_and_terminal(self):
        token=self.token();status,raw,_=self.request('/api/launch',{'incident':'IF-002','variant':'B2'},token,self.url)
        self.assertEqual(202,status);run_id=json.loads(raw)['run_id']
        with self.assertRaises(urllib.error.HTTPError): self.request('/api/launch',{'incident':'IF-001','variant':'B0'},token)
        result=json.loads(self.request('/api/cancel',{'run_id':run_id},token)[1])
        self.assertFalse(result['terminal_confirmed']);self.assertTrue((self.root/'runs'/run_id/'CANCEL').exists())
        self.terminal.set()
        end=time.time()+2
        while self.manager.active() and time.time()<end: time.sleep(.01)
        self.assertIsNone(self.manager.active());self.assertEqual(1,len(self.spawned))
    def test_active_guard_removed_during_read(self):
        from unittest.mock import patch
        from incidentforge.ui import read_json
        self.manager.guard.write_text('{"run_id":"finished"}')
        def removed(path):
            path.unlink()
            return read_json(path)
        with patch('incidentforge.ui.read_json',side_effect=removed):
            self.assertIsNone(self.manager.active())
        self.manager.guard.write_text('invalid')
        with self.assertRaises(json.JSONDecodeError): self.manager.active()
        self.manager.guard.unlink()

    def test_guard_release_survives_a_concurrent_reader_holding_the_file(self):
        # /api/state reads the guard while the watcher removes it. On Windows an
        # open handle makes unlink raise, which previously killed the watcher
        # thread and stranded the guard, refusing every later launch.
        from unittest.mock import patch
        self.manager.guard.write_text('{"run_id":"stuck"}')
        real=Path.unlink
        attempts={'n':0}
        def flaky(path,*args,**kwargs):
            attempts['n']+=1
            if attempts['n']<3:
                raise PermissionError(32,'The process cannot access the file because it is being used by another process')
            return real(path,*args,**kwargs)
        with patch.object(Path,'unlink',flaky):
            self.assertTrue(self.manager.release_guard(timeout=5))
        self.assertFalse(self.manager.guard.exists())
        self.assertGreaterEqual(attempts['n'],3,'the transient sharing violation was not retried')

    def failing_manager(self,error):
        """A Manager whose spawn fails, capturing the log handle it was given."""
        from incidentforge.ui import Manager
        captured={}
        def spawn(run_id,incident,variant,backend,log):
            captured['log']=log;captured['run_id']=run_id
            raise error
        return Manager(self.root/'failing',spawn),captured

    def test_spawn_failure_cleans_up_through_a_transient_sharing_violation(self):
        from unittest.mock import patch
        original=ValueError('Set CONTREE_PYTHON to the installed ConTree SDK Python')
        manager,captured=self.failing_manager(original)
        real=Path.unlink;hits={'n':0}
        def flaky(path,*args,**kwargs):
            if path.name=='active.json' and hits['n']<1:
                hits['n']+=1;raise PermissionError(32,'in use by another process')
            return real(path,*args,**kwargs)
        with patch.object(Path,'unlink',flaky):
            with self.assertRaises(ValueError) as caught:
                manager.launch('IF-002','B2')
        # The operator still sees the actionable spawn failure, not a file error.
        self.assertIn('CONTREE_PYTHON',str(caught.exception))
        self.assertEqual(1,hits['n'],'the sharing violation was never exercised')
        self.assertTrue(captured['log'].closed,'the worker log was left open')
        self.assertFalse(manager.guard.exists(),'the guard was stranded by a transient error')
        self.assertIsNone(manager.current);self.assertIsNone(manager.process)
        # Cleanup succeeded, so the operator may try again.
        manager.spawn=lambda *a,**k:None
        self.assertEqual('IF-002',manager.launch('IF-002','B2')['incident'])

    def test_persistent_cleanup_failure_is_explicit_and_blocks_relaunch(self):
        from unittest.mock import patch
        manager,captured=self.failing_manager(ValueError('preflight refused the launch'))
        def always(path,*args,**kwargs):
            if path.name=='active.json': raise PermissionError(32,'in use by another process')
            return None
        with patch.object(Path,'unlink',always):
            with self.assertRaises(RuntimeError) as caught:
                manager.launch('IF-002','B2')
        message=str(caught.exception)
        self.assertIn('preflight refused the launch',message,'original failure was lost')
        self.assertIn('active.json',message,'residual guard was not named')
        self.assertIsInstance(caught.exception.__cause__,ValueError)
        self.assertTrue(captured['log'].closed)
        self.assertTrue(manager.guard.exists(),'a stuck guard must remain, conservatively')
        with self.assertRaises(ValueError): manager.launch('IF-002','B2')

    def test_active_survives_a_guard_read_blocked_by_a_concurrent_delete(self):
        # Windows raises PermissionError, not FileNotFoundError, for a file that
        # is open elsewhere or pending deletion. active() caught only the latter,
        # so a console poll during guard removal returned 400 instead of state.
        from unittest.mock import patch
        import incidentforge.ui as ui
        self.manager.guard.write_text('{"run_id":"live-run"}')
        real=ui.read_json;hits={'n':0}
        def flaky(path,*args,**kwargs):
            if path.name=='active.json' and hits['n']<2:
                hits['n']+=1;raise PermissionError(13,'Permission denied')
            return real(path,*args,**kwargs)
        with patch.object(ui,'read_json',flaky):
            data=self.manager.active()
        self.assertEqual('live-run',data['run_id'])
        self.assertEqual(2,hits['n'],'the blocked read was never exercised')

    def test_active_still_reports_a_guard_that_stays_unreadable(self):
        from unittest.mock import patch
        import incidentforge.ui as ui
        self.manager.guard.write_text('{"run_id":"live-run"}')
        def blocked(path,*args,**kwargs):
            if path.name=='active.json': raise PermissionError(13,'Permission denied')
            return ui.read_json(path,*args,**kwargs)
        with patch.object(ui,'read_json',blocked):
            with self.assertRaises(PermissionError): self.manager.read_guard(timeout=.2)
        self.manager.guard.unlink()

    def test_release_guard_never_removes_another_runs_guard(self):
        self.manager.guard.write_text('{"run_id":"someone-else"}')
        self.assertFalse(self.manager.release_guard(run_id='mine'))
        self.assertTrue(self.manager.guard.exists())
        self.assertTrue(self.manager.release_guard(run_id='someone-else'))
        self.assertFalse(self.manager.guard.exists())

    def test_guard_release_gives_up_rather_than_spinning_forever(self):
        from unittest.mock import patch
        self.manager.guard.write_text('{"run_id":"stuck"}')
        def always(path,*args,**kwargs):
            raise PermissionError(32,'in use')
        with patch.object(Path,'unlink',always):
            with self.assertRaises(PermissionError): self.manager.release_guard(timeout=.2)
        self.manager.guard.unlink()

    def test_pending_usage_prevents_launch(self):
        b=Budget(self.root/'runs/t4-budget.sqlite',200000);b.reserve('previous',100,200000,10)
        with self.assertRaises(ValueError): self.manager.launch('IF-001','B0')
        self.assertEqual([],self.spawned)
    def finished_run(self,run_id,decision,reason,incident='IF-002',variant='B2',revision='rev-abc'):
        """A completed run on disk: chained evidence, terminal report event, report.json."""
        e=Evidence(self.root/'runs'/run_id,run_id)
        e.event('transition',{'from':'INGEST','to':'REPRODUCE'})
        e.event('stopped',{'reason':reason})
        e.event('transition',{'from':'VERIFY','to':'REPORT'})
        report={'run_id':run_id,'variant':variant,'decision':decision,'reason':reason,
                'model_claim_unverified':'model narrative','candidate_revision':revision,
                'accounting':{'calls':2}}
        e.event('report',report)
        (e.root/'report.json').write_text(json.dumps(report))
        (e.root/'candidate').mkdir()
        (e.root/'candidate'/'INCIDENT.json').write_text(json.dumps({'incident_id':incident}))
        return report

    def test_reconnecting_while_a_run_is_active_does_not_start_another(self):
        token=self.token()
        status,raw,_=self.request('/api/launch',{'incident':'IF-001','variant':'B0'},token,self.url)
        self.assertEqual(202,status);run_id=json.loads(raw)['run_id']
        # Each request is a fresh connection, as a browser refresh would be.
        for _ in range(3):
            state=json.loads(self.request('/api/state')[1])
            self.assertIsNotNone(state['active'],'active run disappeared across a refresh')
            self.assertEqual(run_id,state['active']['run_id'])
            self.assertEqual('live',state['active']['status'])
            self.assertFalse(state['active']['cancel_requested'])
        self.assertEqual(1,len(self.spawned),'a refresh started another worker')
        self.terminal.set()
        end=time.time()+2
        while self.manager.active() and time.time()<end: time.sleep(.01)
        state=json.loads(self.request('/api/state')[1])
        self.assertIsNone(state['active'])
        self.assertEqual(1,len(self.spawned))

    def test_active_run_shows_its_real_incident_and_variant_before_terminating(self):
        # The per-run receipt is only written when the worker exits. Until then the
        # launch metadata lives in the guard, so an active run must not be reported
        # with the default incident and an unknown variant.
        token=self.token()
        raw=self.request('/api/launch',{'incident':'IF-002','variant':'B2'},token,self.url)[1]
        run_id=json.loads(raw)['run_id']
        guard=json.loads(self.manager.guard.read_text())
        self.assertEqual(('IF-002','B2'),(guard['incident'],guard['variant']))
        detail=json.loads(self.request('/api/runs/'+run_id)[1])
        self.assertEqual('IF-002',detail['incident'],'active run displayed the default incident')
        self.assertEqual('B2',detail['variant'],'active run displayed an unknown variant')
        # A live run is surfaced through 'active'; run history lists runs that have
        # produced evidence, so it is not expected to carry it yet.
        state=json.loads(self.request('/api/state')[1])
        self.assertEqual(('IF-002','B2'),(state['active']['incident'],state['active']['variant']))
        self.assertNotIn(run_id,[r['run_id'] for r in state['runs']])

    def test_unresolved_run_exposes_its_reason_and_evidence(self):
        self.finished_run('unresolved-run','unresolved','Protected feedback incomplete')
        status,raw,_=self.request('/api/runs/unresolved-run')
        self.assertEqual(200,status);data=json.loads(raw)
        self.assertEqual('unresolved',data['decision'])
        self.assertEqual('Protected feedback incomplete',data['report']['reason'])
        self.assertEqual('verified',data['integrity'])
        self.assertIn('Protected feedback incomplete',[row['label'] for row in data['timeline']])
        self.assertEqual('REPORT',data['state'])
        # A finished unresolved run is exportable; the export must carry the
        # unresolved verdict rather than presenting it as a repair.
        status,payload,headers=self.request('/api/runs/unresolved-run/export')
        self.assertEqual(200,status);self.assertEqual('application/zip',headers['Content-Type'])
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            review=json.loads(archive.read('review.json'))
        self.assertEqual('unresolved',review['decision'])
        self.assertEqual([],review['diffs'],'an unresolved run must not export a patch')

    def test_displayed_fields_match_the_underlying_run_artifacts(self):
        report=self.finished_run('shown-run','accept_for_review','candidate frozen',
                                 incident='IF-002',variant='B2',revision='rev-7f3')
        on_disk=json.loads((self.root/'runs'/'shown-run'/'report.json').read_text())
        self.assertEqual(report,on_disk)
        listed=next(r for r in json.loads(self.request('/api/state')[1])['runs']
                    if r['run_id']=='shown-run')
        detail=json.loads(self.request('/api/runs/shown-run')[1])
        for shown in (listed,detail):
            self.assertEqual('IF-002',shown['incident'],'incident differs from candidate/INCIDENT.json')
            self.assertEqual(on_disk['variant'],shown['variant'])
            self.assertEqual(on_disk['decision'],shown['decision'])
            self.assertEqual('REPORT',shown['state'],'state differs from the last transition event')
            self.assertEqual(on_disk['candidate_revision'],shown['report']['candidate_revision'])
        # The export carries the same verdict the operator saw.
        payload=export_run(self.root,'shown-run')
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            review=json.loads(archive.read('review.json'))
        self.assertEqual(on_disk['decision'],review['decision'])
        self.assertEqual('IF-002',review['incident'])

    def test_export_is_allowlisted_and_unicode_evidence_verifies(self):
        self.evidence();data=details(self.root,'sample');self.assertEqual('verified',data['integrity'])
        payload=export_run(self.root,'sample')
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            self.assertEqual({'review.json','patch.diff','README.txt','SHA256SUMS.txt'},set(archive.namelist()))
            review=archive.read('review.json').decode()
            for secret in ('PRIVATE_CASE','PRIVATE_SCHEDULE','NEVER_EXPORT'): self.assertNotIn(secret,review)
        status,_,headers=self.request('/api/runs/sample/export')
        self.assertEqual(200,status);self.assertEqual('application/zip',headers['Content-Type'])
    def test_authored_tests_and_receipts_are_exported_without_other_tool_data(self):
        e=Evidence(self.root/'runs'/'tests-only','tests-only')
        spec={'assertions':[{'name':'recover','condition':'restart','path':'order.status','equals':'CANCELLED_DECLINED'}]}
        e.event('tool_result',{'artifact':e.artifact({'saved':True,'specification':e.artifact(spec)})})
        e.event('tool_result',{'artifact':e.artifact({'developer_tests':{'authored':True,'passed':True,'assertions':[{'passed':True}]},'private':'NEVER_EXPORT'})})
        report={'run_id':'tests-only','variant':'B2','decision':'unresolved','model_claim_unverified':None,'verified_work':{'developer_tests_passed_on_current_revision':True}}
        e.event('report',report);(e.root/'report.json').write_text(json.dumps(report))
        data=details(self.root,'tests-only')
        self.assertEqual(spec,data['developer_tests'][0]['specification'])
        self.assertTrue(data['developer_tests'][1]['receipt']['passed'])
        self.assertNotIn('NEVER_EXPORT',json.dumps(data))
        with zipfile.ZipFile(io.BytesIO(export_run(self.root,'tests-only'))) as archive:
            self.assertEqual(data['developer_tests'],json.loads(archive.read('review.json'))['developer_tests'])

    def test_tampered_evidence_export_rejected(self):
        e=self.evidence();(e.root/'events.jsonl').write_text('')
        # A report with a truncated stream must not be treated as verified.
        with self.assertRaises(ValueError): export_run(self.root,'sample')
    def test_path_escape_and_script_injection_surface(self):
        for name in ('../secret','..','a/b'):
            with self.assertRaises(ValueError): run_path(self.root,name)
        self.evidence();self.assertIn('<script>',details(self.root,'sample')['interpretations'][0]['conclusion'])
        js=self.request('/app.js')[1].decode()
        self.assertNotIn('innerHTML',js);self.assertIn('textContent',js)
        headers=self.request('/')[2];self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy'])


    def test_backend_selection_is_recorded_and_invalid_choice_rejected(self):
        token=self.token()
        with self.assertRaises(urllib.error.HTTPError):
            self.request('/api/launch',{'incident':'IF-002','variant':'B2','backend':'arbitrary'},token)
        self.assertEqual([],self.spawned)
        status,raw,_=self.request('/api/launch',{'incident':'IF-002','variant':'B2','backend':'contree'},token)
        self.assertEqual(202,status);self.assertEqual('contree',json.loads(raw)['backend'])
        self.assertEqual('contree',self.manager.active()['backend'])

    def test_spawn_passes_backend_and_preflight_failure_cannot_launch(self):
        from unittest.mock import patch,Mock
        import os
        with patch('incidentforge.remote_backend.reader_preflight',return_value='sha256:'+'a'*64), patch.dict(
                os.environ,{'CONTREE_PYTHON':sys.executable}), patch('incidentforge.ui.subprocess.Popen') as popen:
            self.manager._spawn('ui-'+'a'*32,'IF-002','B2','contree',Mock())
            command=popen.call_args.args[0]
            self.assertEqual('contree',command[command.index('--backend')+1])
        with patch('incidentforge.remote_backend.reader_preflight',side_effect=RuntimeError('Docker unavailable')), patch(
                'incidentforge.ui.subprocess.Popen') as popen:
            with self.assertRaisesRegex(ValueError,'Docker unavailable'):
                self.manager._spawn('ui-'+'b'*32,'IF-002','B2','contree',Mock())
            popen.assert_not_called()

class StaticPublishTests(unittest.TestCase):
    def test_static_allowlist_and_evidence_hash(self):
        import importlib.util
        import shutil
        root=Path(__file__).resolve().parents[1]
        spec=importlib.util.spec_from_file_location('check_site',root/'scripts/check-site.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            site=Path(tmp)/'site';shutil.copytree(root/'site',site)
            self.assertEqual(7,module.check(site)['files'])
            extra=site/'unreviewed.txt';extra.write_text('unexpected')
            with self.assertRaisesRegex(ValueError,'allowlist'):module.check(site)
            extra.unlink()
            evidence=site/'evidence.json';evidence.write_bytes(evidence.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError,'digest'):module.check(site)

    def test_inconsistent_publishing_claims_fail_even_with_matching_digest(self):
        import copy,hashlib,importlib.util,shutil
        root=Path(__file__).resolve().parents[1]
        spec=importlib.util.spec_from_file_location('check_site_semantics',root/'scripts/check-site.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        original=json.loads((root/'site/evidence.json').read_text(encoding='utf-8'))
        for mode in ('empty-property','failed-property','missing-property','denominator','accepted-count','duplicate-slot','cell'):
            data=copy.deepcopy(original)
            if mode=='empty-property': data['incidents'][0]['properties']['P1']=[]
            elif mode=='failed-property': data['incidents'][0]['properties']['P1'][0]='fail'
            elif mode=='missing-property': del data['incidents'][0]['properties']['P7']
            elif mode=='denominator': data['campaign']['launched_runs']+=1
            elif mode=='accepted-count': data['campaign']['accepted_final_repairs']+=1
            elif mode=='duplicate-slot': data['attempts'][1]['slot']=data['attempts'][0]['slot']
            else: data['cells'][0]['accepted']+=1
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as tmp:
                site=Path(tmp)/'site';shutil.copytree(root/'site',site)
                raw=json.dumps(data).encode();(site/'evidence.json').write_bytes(raw)
                (site/'evidence.sha256').write_text(hashlib.sha256(raw).hexdigest()+'  evidence.json\n')
                with self.assertRaises(ValueError): module.check(site)

if __name__=='__main__': unittest.main()
