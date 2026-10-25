"""Loopback-only operator interface. No candidate code executes in this server."""
import argparse
from contextlib import closing
from datetime import datetime,timezone
import hashlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import subprocess
import sys
import threading
import time
from urllib.parse import urlparse
import uuid
import zipfile
from .evidence import verify

ROOT=Path(__file__).resolve().parents[2]
STATIC=Path(__file__).with_name('web')
ID=re.compile(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,100}')
INCIDENTS=[{'id':'IF-001','title':'Duplicate payment','description':'A committed payment response is lost. Retries create duplicate charges.'},
           {'id':'IF-002','title':'Stranded compensation','description':'A declined order keeps inventory reserved after services restart.'}]

def read_json(path,limit=2_000_000):
    if path.is_symlink() or path.stat().st_size>limit: raise ValueError('File outside evidence limits')
    return json.loads(path.read_text(encoding='utf-8'))

def run_path(root,run_id):
    if not ID.fullmatch(run_id): raise ValueError('Invalid run ID')
    base=(root/'runs').resolve();path=base/run_id
    if path.is_symlink() or path.resolve().parent!=base: raise ValueError('Invalid run path')
    return path

def events_for(path):
    source=path/'events.jsonl'
    if not source.exists(): return []
    if source.is_symlink() or source.stat().st_size>8_000_000: raise ValueError('Event stream exceeds bounds')
    raw=source.read_bytes()
    # The last append may be in progress. Never turn a partial line into an event.
    lines=raw.split(b'\n')[:-1]
    return [json.loads(line.decode('utf-8')) for line in lines if line]

def artifact(path,ref):
    sha=ref.get('sha256','')
    if not re.fullmatch('[a-f0-9]{64}',sha): raise ValueError('Invalid artifact hash')
    target=path/'artifacts'/sha
    if target.is_symlink() or target.stat().st_size>2_000_000: raise ValueError('Artifact outside bounds')
    raw=target.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=sha: raise ValueError('Artifact hash mismatch')
    return raw.decode('utf-8')

def budget_status(root):
    path=root/'runs/t4-budget.sqlite'
    if not path.exists(): return {'cap_usd':.20,'estimated_usd':0,'reserved_usd':0,'pending':0,'remaining_usd':.20,'unknown_usd':0,'unknown_calls':0}
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        try: settings=db.execute('SELECT cap FROM settings').fetchone()
        except sqlite3.OperationalError:
            # Schema not published yet, or the ledger is locked by its writer.
            # Either way the allocation is unknown, which is the same condition.
            settings=None
        if settings is None or type(settings[0]) is not int:
            # The ledger exists but carries no usable allocation. Report that
            # plainly: inventing a cap or a zero spend here would understate real
            # usage, and remaining_usd 0 keeps launching blocked while unknown.
            return {'state':'incomplete','cap_usd':None,'estimated_usd':None,'reserved_usd':None,
                    'pending':None,'remaining_usd':0,'unknown_usd':None,'unknown_calls':None}
        cap=settings[0]
        unknown,unknown_calls=db.execute('SELECT COALESCE(SUM(cap),0),COUNT(*) FROM calls WHERE actual IS NULL').fetchone()
        spent,reserved,pending=db.execute("SELECT COALESCE(SUM(actual),0),COALESCE(SUM(CASE WHEN actual IS NULL THEN cap ELSE actual END),0),COALESCE(SUM(status='reserved'),0) FROM calls").fetchone()
    return {'cap_usd':cap/1e6,'estimated_usd':spent/1e6,'reserved_usd':reserved/1e6,
            'pending':pending,'remaining_usd':max(0,cap-reserved)/1e6,
            'unknown_usd':unknown/1e6,'unknown_calls':unknown_calls}

def overview(root,run_id):
    path=run_path(root,run_id);events=events_for(path)
    report=read_json(path/'report.json') if (path/'report.json').exists() else None
    receipt_path=root/'runs/ui-launches'/(run_id+'.json')
    receipt=read_json(receipt_path) if receipt_path.exists() else {}
    if not receipt:
        # The per-run receipt is only written once the worker terminates. While a
        # run is live its launch metadata lives in the guard, so fall back to that
        # rather than reporting the default incident and an unknown variant.
        guard=root/'runs/ui-launches/active.json'
        if guard.exists():
            try:
                active=read_json(guard)
                if active.get('run_id')==run_id: receipt=active
            except (ValueError,OSError): pass
    if report and 'model_claim_unverified' not in report:
        report={**report,'model_claim_unverified':report.get('reason'),
                'reason':'Legacy report: use the independent verdict and validation records below. Original narrative is an unverified model claim.'}
    state=next((e['payload']['to'] for e in reversed(events) if e['kind']=='transition'),'PREPARING')
    bundle=None
    for e in events:
        if e['kind']=='record':
            r=json.loads(artifact(path,e['payload']['record']))
            if r['kind']=='IncidentBundle': bundle=r['data'];break
    incident=receipt.get('incident','IF-001')
    candidate=path/'candidate/INCIDENT.json'
    if candidate.exists(): incident=read_json(candidate).get('incident_id',incident)
    return {'run_id':run_id,'incident':incident,'variant':(report or {}).get('variant',(bundle or {}).get('config',{}).get('variant',receipt.get('variant','unknown'))),
            'process_terminal':receipt.get('terminal_confirmed',False),'process_exit':receipt.get('exit_code'),
            'decision':(report or {}).get('decision'),'state':state,'report':report,
            'started':events[0]['time_utc'] if events else None,'event_count':len(events)}

def details(root,run_id):
    path=run_path(root,run_id);result=overview(root,run_id);events=events_for(path)
    records=[];diffs=[];timeline=[];interpretations=[];developer_tests=[]
    for e in events:
        kind=e['kind'];payload=e['payload']
        if kind=='record':
            r=json.loads(artifact(path,payload['record']))
            if r['kind']=='PatchCandidate':
                for ref in r['artifacts']: diffs.append(artifact(path,ref))
            if r['kind']=='ValidationReport':
                # Operator summary/export deliberately excludes private case names/schedules.
                data=r['data'];properties={}
                for case in data.get('properties',[]):
                    for values in case.values():
                        for name,item in values.items():
                            properties.setdefault(name,[]).append(item.get('status','unknown'))
                r={**r,'artifacts':[],'data':{**data,'properties':properties}}
            records.append(r)
        if kind=='model_interpretation': interpretations.append(payload)
        if kind=='tool_result':
            value=json.loads(artifact(path,payload['artifact']))
            if isinstance(value,dict) and value.get('saved') is True and 'specification' in value:
                spec=json.loads(artifact(path,value['specification']))
                developer_tests.append({'event':e['seq'],'kind':'authored','specification':spec,
                    'baseline_assessment':value.get('baseline_assessment'),
                    'test_quality_note':value.get('test_quality_note')})
            elif isinstance(value,dict) and isinstance(value.get('developer_tests'),dict):
                receipt=value['developer_tests']
                developer_tests.append({'event':e['seq'],'kind':'execution',
                    'receipt':{k:receipt[k] for k in ('authored','passed','assertions','scope') if k in receipt}})
        if kind in ('transition','action_rejected','stopped','execution_reserved','execution_cleanup','model_response'):
            label=(payload.get('to') if kind=='transition' else payload.get('reason') if kind in ('action_rejected','stopped')
                   else payload.get('mode') if kind=='execution_reserved' else
                   'Terminal confirmed' if kind=='execution_cleanup' and payload.get('terminal_confirmed') else kind)
            timeline.append({'time':e['time_utc'],'kind':kind,'label':label,'sequence':e['seq']})
    integrity='pending'
    if result['report']:
        try:
            verify(path)
            if not events or events[-1]['kind']!='report' or events[-1]['payload']!=read_json(path/'report.json'):
                raise ValueError('Terminal report missing or mismatched')
            integrity='verified'
        except (ValueError,OSError): integrity='failed'
    result.update(records=records,diffs=diffs,timeline=timeline,interpretations=interpretations,developer_tests=developer_tests,integrity=integrity,
                  scope='Development evidence; not a final holdout or comparative study.')
    return result

def export_run(root,run_id):
    data=details(root,run_id)
    if not data['report']: raise ValueError('Wait for the run to finish before exporting')
    if data['integrity']!='verified': raise ValueError('Evidence integrity failed; export blocked')
    # Curated operator export, never a recursive archive of runs, credentials or private schedules.
    files={'review.json':json.dumps(data,indent=2).encode('utf-8'),
           'patch.diff':'\n'.join(data['diffs']).encode('utf-8'),
           'README.txt':b'IncidentForge development review export. Recorded evidence, not a live execution.\nModel claims are unverified; independent validation decides the verdict.\nPrivate schedules, raw prompts, databases and credentials are excluded.\n'}
    files['SHA256SUMS.txt']=''.join(hashlib.sha256(raw).hexdigest()+'  '+name+'\n' for name,raw in files.items()).encode()
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,raw in files.items(): archive.writestr(name,raw)
    return buffer.getvalue()

class LaunchCleanupError(RuntimeError):
    """A launch failed and its guard could not be removed, so relaunch is blocked.

    `original` is the actionable spawn failure the operator must act on. `detail`
    keeps the cleanup error for local diagnosis and is deliberately not returned
    over HTTP, because it carries a filesystem path.
    """
    def __init__(self,original,guard_name,detail):
        self.original=original;self.guard_name=guard_name;self.detail=detail
        super().__init__('Launch failed and its guard could not be removed, so relaunch stays '
                         'blocked until '+guard_name+' is cleared by hand. Original failure: '
                         +original+'. Cleanup failure: '+detail)

class Manager:
    def __init__(self,root,spawn=None):
        self.root=root;self.lock=threading.Lock();self.process=None;self.current=None
        self.spawn=spawn or self._spawn
        self.meta=root/'runs/ui-launches';self.meta.mkdir(parents=True,exist_ok=True)
        self.guard=self.meta/'active.json'

    def _spawn(self,run_id,incident,variant,backend,log):
        from .remote_backend import reader_preflight
        try: reader_preflight()
        except RuntimeError as exc: raise ValueError(str(exc)) from exc
        if backend=='contree':
            sdk=Path(os.environ.get('CONTREE_PYTHON',str(Path.home()/'AppData/Roaming/uv/tools/contree-cli/Scripts/python.exe')))
            if not sdk.is_file(): raise ValueError('Set CONTREE_PYTHON to the installed ConTree SDK Python')
            if (self.root/'runs/contree-active.json').exists(): raise ValueError('Sandbox operation remains unconfirmed; reconcile before launch')
        args=[sys.executable,str(self.root/'scripts/run-t4.py'),'--live','--incident',incident,'--variant',variant,'--backend',backend,'--run-id',run_id]
        return subprocess.Popen(args,stdout=log,stderr=log,stdin=subprocess.DEVNULL,cwd=self.root,
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)

    def read_guard(self,timeout=1.0):
        """Read the launch guard, tolerating the moment it is being removed.

        On Windows a file that another handle has open, or that is pending
        deletion, raises PermissionError rather than FileNotFoundError. A console
        poll landing in that window returned an error instead of state, so retry
        briefly before giving up.
        """
        deadline=time.monotonic()+timeout
        while True:
            try: return read_json(self.guard)
            except FileNotFoundError: return None
            except PermissionError:
                if time.monotonic()>=deadline: raise
                time.sleep(.02)

    def active(self):
        data=self.read_guard()
        if data is None:
            # The watcher removes the guard after confirming process termination.
            return None
        data['status']='live' if self.current==data['run_id'] else 'unknown'
        data['cancel_requested']=(run_path(self.root,data['run_id'])/'CANCEL').exists()
        return data

    def launch(self,incident,variant,backend='docker'):
        if incident not in ('IF-001','IF-002') or variant not in ('B0','B1','B2'): raise ValueError('Unsupported incident or variant')
        if backend not in ('docker','contree'): raise ValueError('Unsupported execution backend')
        with self.lock:
            if self.guard.exists(): raise ValueError('A live or unconfirmed launch already exists')
            budget=budget_status(self.root)
            if budget.get('state')=='incomplete':
                raise ValueError('Project ledger is initializing or incomplete; budget state unknown, launch blocked')
            if budget['pending']: raise ValueError('An inference call is pending or unreconciled; new launch blocked')
            from .llm import CALL_RESERVATION
            if budget['remaining_usd']<CALL_RESERVATION/1e6: raise ValueError('Insufficient remaining project allocation')
            run_id='ui-'+uuid.uuid4().hex
            metadata={'run_id':run_id,'incident':incident,'variant':variant,'backend':backend,'started':datetime.now(timezone.utc).isoformat()}
            # Exclusive creation also guards against a second local UI server.
            with self.guard.open('x',encoding='utf-8') as file: json.dump(metadata,file)
            log=(self.meta/(run_id+'.log')).open('wb')
            try: process=self.spawn(run_id,incident,variant,backend,log)
            except Exception as spawn_error:
                # Clean up our own guard only, and never let a transient sharing
                # violation replace the spawn failure the operator has to act on.
                log.close()
                # Short bound: an operator is waiting on a failed launch, so this
                # must answer quickly. The watcher keeps the longer retry.
                try: self.release_guard(timeout=2.0,run_id=run_id)
                except OSError as cleanup_error:
                    raise LaunchCleanupError(
                        type(spawn_error).__name__+': '+str(spawn_error)[:200],
                        self.guard.name,str(cleanup_error)[:120]) from spawn_error
                raise
            self.current=run_id;self.process=process
            threading.Thread(target=self._watch,args=(process,run_id,log),daemon=True).start()
            return metadata

    def _watch(self,process,run_id,log):
        code=process.wait();log.close()
        # terminal_confirmed describes this local worker process only. It says
        # nothing about a remote Sandbox operation, whose own guard is never
        # touched here.
        confirmed={'run_id':run_id,'exit_code':code,'terminal_confirmed':True}
        try: metadata=self.read_guard() or {}
        except OSError as exc:
            # Unreadable guard: record the run with what is certain, and do not
            # guess at an owner. release_guard below will refuse to remove a
            # guard it cannot attribute to this run.
            metadata={};confirmed['guard_read_error']=type(exc).__name__+': '+str(exc)[:120]
        receipt={**metadata,**confirmed}
        with self.lock:
            self.current=None;self.process=None
            # A guard that cannot be released is recorded rather than killing this
            # thread, which would leave the run looking live with no explanation.
            try: self.release_guard(run_id=run_id)
            except OSError as exc: receipt['guard_release_error']=type(exc).__name__+': '+str(exc)[:120]
        (self.meta/(run_id+'.json')).write_text(json.dumps(receipt),encoding='utf-8')

    def release_guard(self,timeout=10.0,run_id=None):
        """Remove the launch guard, tolerating a concurrent reader.

        Windows refuses to delete a file another handle has open, and the console
        polls this guard through /api/state. An unlink that raised would end the
        watcher thread and strand the guard, so every later launch would be
        refused with a live run that has already exited. Retry instead.

        With run_id, only a guard recording that run is removed, so no cleanup
        path can delete a guard another launch owns. Returns False in that case.
        """
        deadline=time.monotonic()+timeout
        while True:
            try:
                if run_id is not None:
                    try: owner=read_json(self.guard).get('run_id')
                    except FileNotFoundError: return True
                    if owner!=run_id: return False
                self.guard.unlink();return True
            except FileNotFoundError: return True
            except PermissionError:
                if time.monotonic()>=deadline: raise
                time.sleep(.05)

    def cancel(self,run_id):
        with self.lock:
            active=self.active()
            if not active or active['run_id']!=run_id: raise ValueError('This run is not active')
            path=run_path(self.root,run_id)
            if not path.exists(): raise ValueError('Run is preparing; retry cancellation shortly')
            (path/'CANCEL').touch()
            return {'requested':True,'terminal_confirmed':False,
                    'message':'Cancellation requested. An in-flight model request can take up to 120 seconds to return; execution cleanup must finish.'}

def make_server(root=ROOT,port=8765,manager=None):
    manager=manager or Manager(root);token=secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_): pass
        def send(self,code,data,mime='application/json',download=None):
            raw=json.dumps(data).encode() if mime=='application/json' else data
            self.send_response(code);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            if download: self.send_header('Content-Disposition','attachment; filename="'+download+'"')
            self.end_headers();self.wfile.write(raw)
        def trusted(self):
            return self.headers.get('Host') in ('127.0.0.1:'+str(self.server.server_port),'localhost:'+str(self.server.server_port))
        def do_GET(self):
            if not self.trusted(): return self.send(403,{'error':'Loopback host required'})
            path=urlparse(self.path).path
            try:
                if path in ('/','/app.js','/style.css'):
                    file={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}[path]
                    return self.send(200,(STATIC/file).read_bytes(),{'/':'text/html; charset=utf-8','/app.js':'text/javascript; charset=utf-8','/style.css':'text/css; charset=utf-8'}[path])
                if path=='/api/state':
                    runs=[]
                    for p in (root/'runs').iterdir():
                        if p.is_dir() and not p.is_symlink() and (p/'events.jsonl').exists():
                            try:
                                item=overview(root,p.name)
                                if item['variant'] in ('B0','B1','B2'): runs.append(item)
                            except (ValueError,OSError,KeyError): continue
                    known={r['run_id'] for r in runs}
                    for p in manager.meta.glob('ui-*.json'):
                        if p.stem not in known:
                            try: item=overview(root,p.stem)
                            except (ValueError,OSError,KeyError) as exc:
                                # Surface the run as unreadable rather than letting it
                                # break the whole response or vanish from the list. A
                                # run whose evidence exists but cannot be summarised is
                                # exactly what an operator needs to see.
                                runs.append({'run_id':p.stem,'incident':'unknown','variant':'unknown',
                                    'process_terminal':False,'process_exit':None,'decision':None,
                                    'state':'UNREADABLE','report':None,'started':None,'event_count':0,
                                    'unreadable':type(exc).__name__+': '+str(exc)[:120]})
                                continue
                            if item['variant'] in ('B0','B1','B2'): runs.append(item)
                    return self.send(200,{'token':token,'incidents':INCIDENTS,'budget':budget_status(root),'active':manager.active(),
                        'runs':sorted(runs,key=lambda r:r['started'] or '',reverse=True)})
                match=re.fullmatch(r'/api/runs/([A-Za-z0-9_-]+)(/export)?',path)
                if match:
                    run_id=match[1]
                    if match[2]: return self.send(200,export_run(root,run_id),'application/zip',run_id+'-review.zip')
                    return self.send(200,details(root,run_id))
                self.send(404,{'error':'Not found'})
            except (ValueError,OSError,KeyError,sqlite3.Error) as exc: self.send(400,{'error':str(exc)[:200]})
        def do_POST(self):
            origin=self.headers.get('Origin')
            if not self.trusted() or self.headers.get('X-IncidentForge-Token')!=token or (origin and origin not in (
                'http://127.0.0.1:'+str(self.server.server_port),'http://localhost:'+str(self.server.server_port))):
                return self.send(403,{'error':'Local session token and same origin required'})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=2048: raise ValueError('Request size bound')
                body=json.loads(self.rfile.read(size));path=urlparse(self.path).path
                if path=='/api/launch' and set(body) in ({'incident','variant'},{'incident','variant','backend'}): return self.send(202,manager.launch(**body))
                if path=='/api/cancel' and set(body)=={'run_id'}: return self.send(202,manager.cancel(body['run_id']))
                self.send(400,{'error':'Unsupported action'})
            # Narrow, expected condition: the launch failed and its guard survived.
            # The operator needs the original failure and the residual state, not a
            # dropped connection. The cleanup detail carries a path and stays local.
            except LaunchCleanupError as exc:
                self.send(409,{'error':exc.original,'cleanup':'unconfirmed',
                    'residual_guard':exc.guard_name,
                    'relaunch':'blocked until the residual launch guard is cleared'})
            except (ValueError,OSError,TypeError,KeyError,subprocess.SubprocessError) as exc: self.send(400,{'error':str(exc)[:200]})
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    server.daemon_threads=True
    return server

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);args=parser.parse_args()
    server=make_server(port=args.port)
    print('IncidentForge: http://127.0.0.1:'+str(server.server_port),flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=='__main__': main()
