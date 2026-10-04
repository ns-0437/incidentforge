"""Shared controller adapter for Nebius Sandbox, using the installed SDK runtime."""
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import time
import uuid
import zipfile
from .backend import BackendUnknown,Cancelled

def read_export(out,mode):
    receipt=json.loads((out/'receipt.json').read_text())
    path=out/'evidence.zip'
    if path.stat().st_size>16_000_000 or hashlib.sha256(path.read_bytes()).hexdigest()!=receipt['sha256']:
        raise ValueError('export hash')
    with zipfile.ZipFile(path) as z:
        infos=z.infolist()
        if len(infos)>512 or sum(i.file_size for i in infos)>16_000_000: raise ValueError('export bound')
        names=[i.filename for i in infos]
        if len(set(names))!=len(names): raise ValueError('duplicate export path')
        info=z.getinfo('result/result.json')
        if info.file_size>1_000_000: raise ValueError('result bound')
        observed=json.loads(z.read(info))
    if observed.get('mode')!=mode or observed.get('complete') is not True: raise ValueError('incomplete execution')
    return observed

def reader_preflight():
    """Check the local verifier before remote execution or inference spending."""
    try:
        server=subprocess.run(['docker','info','--format','{{.OSType}}'],
                              capture_output=True,text=True,timeout=20,check=True).stdout.strip()
        if server!='linux': raise RuntimeError('Independent verifier requires Docker Linux containers')
        pinned=subprocess.run(['docker','image','inspect','python:3.12-slim','--format','{{.Id}}'],
                              capture_output=True,text=True,timeout=20,check=True).stdout.strip()
        if not re.fullmatch(r'sha256:[0-9a-f]{64}',pinned): raise RuntimeError('Invalid verifier image identity')
    except (OSError,subprocess.SubprocessError) as exc:
        raise RuntimeError('Independent verifier unavailable. Start Docker Desktop with Linux containers and ensure python:3.12-slim is cached before launching inference.') from exc
    return pinned

class ContreeBackend:
    name='nebius-sandbox'
    image='4fa16c8f-62a9-35a4-a4ea-07b7e8cd44ae'
    def __init__(self,project,evidence,cancel_file=None,incident='IF-001'):
        if incident not in ('IF-001','IF-002'): raise ValueError('incident')
        self.project=project.resolve();self.evidence=evidence;self.incident=incident;self.count=0
        self.cancel_file=cancel_file or evidence.root/'CANCEL'
        self.python=Path(os.environ.get('CONTREE_PYTHON',str(Path.home()/'AppData/Roaming/uv/tools/contree-cli/Scripts/python.exe')))
        if not self.python.is_file(): raise RuntimeError('Set CONTREE_PYTHON to installed ConTree SDK Python')
        self.reader_image=reader_preflight()
        self.evidence.event('verifier_preflight',{'backend':'docker','image':self.reader_image,'status':'ready','scope':'startup check only; later daemon failure remains possible'})

    def run(self,candidate,mode):
        if time.monotonic()+340>getattr(self,'deadline',float('inf')):
            raise TimeoutError('Insufficient controller time for remote execution and verification')
        if self.cancel_file.exists(): raise Cancelled('cancelled before execution')
        if mode not in {'developer','protected','identity_probe','compensation_probe','calibration','final_holdout'}: raise ValueError('mode')
        if self.count>=7: raise RuntimeError('execution cap exhausted')
        guard=self.project/'runs/contree-active.json'
        if guard.exists(): raise BackendUnknown('Remote reservation unresolved; reconcile before launch')
        self.count+=1;out=self.evidence.root/('execution-'+str(self.count));out.mkdir()
        # Explicit source allowlist; never include repository runs, .env, or auth files.
        with zipfile.ZipFile(out/'source.zip','w',zipfile.ZIP_DEFLATED) as z:
            for folder in ('fixture','tests','probes','evaluation','contracts'):
                for p in (self.project/folder).rglob('*'):
                    if p.is_symlink(): raise ValueError('source symlink')
                    if p.is_file() and p.suffix in {'.py','.md'}: z.write(p,p.relative_to(self.project))
            for name in ('fixture/app/service.py','fixture/app/common.py','fixture/app/contract.py','developer-tests.json'):
                p=candidate/name
                if not p.exists():
                    if name=='developer-tests.json': continue
                    raise ValueError('missing candidate source')
                if p.is_symlink() or p.stat().st_size>100_000: raise ValueError('candidate bound')
                z.write(p,'candidate/'+name)
        request={'output':str(out),'guard':str(guard),'cancel':str(self.cancel_file),'image':self.image,
                 'bootstrap':str(self.project/'probes/remote_candidate_bootstrap.py'),'mode':mode,'incident':self.incident}
        (out/'request.json').write_text(json.dumps(request))
        with guard.open('x') as f: json.dump({'output':str(out),'state':'reserved'},f)
        self.evidence.event('execution_reserved',{'mode':mode,'backend':self.name,'ordinal':self.count,
          'image':self.image,'source_sha256':hashlib.sha256((out/'source.zip').read_bytes()).hexdigest()})
        try:
            result=subprocess.run([str(self.python),str(self.project/'scripts/contree-execute.py'),str(out/'request.json')],
                capture_output=True,timeout=260,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        except Exception:
            raise BackendUnknown('SDK helper incomplete; reservation retained for reconciliation')
        if guard.exists(): raise BackendUnknown('Remote termination unconfirmed; reservation retained')
        if self.cancel_file.exists(): raise Cancelled('user cancelled; remote terminal confirmed')
        if result.returncode: raise RuntimeError('remote operation failed; inspect execution error receipt')
        # Only bounded JSON is parsed on the host. No returned code or database is executed.
        observed=read_export(out,mode)
        if mode in {'protected','final_holdout'}:
            pinned=self.reader_image
            reader='incidentforge-reader-'+uuid.uuid4().hex
            args=['docker','run','--name',reader,'--rm','--read-only','--network','none','--pids-limit','32','--memory','256m',
                  '--cpus','1','--cap-drop','ALL','--security-opt','no-new-privileges=true',
                  '--tmpfs','/tmp:rw,nosuid,nodev,size=64m,mode=1777','--workdir','/app',
                  '--env','PYTHONDONTWRITEBYTECODE=1','--mount',f'type=bind,source={out},target=/input,readonly']
            for folder in ('probes','evaluation'):
                args+=['--mount',f'type=bind,source={self.project/folder},target=/app/{folder},readonly']
            receipt=json.loads((out/'receipt.json').read_text())
            args+=[pinned,'python','-m','probes.verify_candidate_archive','/input/evidence.zip',receipt['sha256']]
            try:
                verified=subprocess.run(args,capture_output=True,text=True,timeout=30,check=True)
            finally:
                # Normal --rm exit already removes it. A client timeout must also stop the reader.
                cleanup=subprocess.run(['docker','rm','--force',reader],capture_output=True,text=True,timeout=20)
                if cleanup.returncode and 'No such container' not in cleanup.stderr:
                    raise BackendUnknown('Reader cleanup unconfirmed')
            (out/'independent-verification.json').write_text(verified.stdout)
        self.evidence.event('execution_complete',{'mode':mode,'backend':self.name,'terminal':True,
            'result':self.evidence.artifact(observed),'receipt':self.evidence.artifact(json.loads((out/'receipt.json').read_text()))})
        return observed
