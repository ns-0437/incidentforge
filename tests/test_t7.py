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

    def test_pending_usage_prevents_launch(self):
        b=Budget(self.root/'runs/t4-budget.sqlite',200000);b.reserve('previous',100,200000,10)
        with self.assertRaises(ValueError): self.manager.launch('IF-001','B0')
        self.assertEqual([],self.spawned)
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
