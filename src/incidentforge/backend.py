"""Bounded local Docker execution; candidates never receive host tools/credentials."""
import json
from pathlib import Path
import subprocess
import time
import uuid

class BackendUnknown(RuntimeError): pass
class Cancelled(RuntimeError): pass

class DockerBackend:
    name='local-docker'
    def __init__(self,project,evidence,cancel_file=None,incident='IF-001'):
        if incident not in ('IF-001','IF-002'): raise ValueError('incident')
        self.incident=incident
        self.project=project.resolve();self.evidence=evidence;self.cancel_file=cancel_file
        self.count=0;self.unknown=False
        self.image=self.command(['image','inspect','python:3.12-slim','--format','{{.Id}}']).strip()
        if not self.image.startswith('sha256:'): raise RuntimeError('immutable image ID unavailable')

    def command(self,args,timeout=20):
        completed=subprocess.run(['docker',*args],capture_output=True,text=True,timeout=timeout)
        if completed.returncode: raise RuntimeError('Docker command failed: '+args[0]+' '+completed.stderr[:300])
        return completed.stdout

    def run(self,candidate,mode):
        if time.monotonic()+240>getattr(self,'deadline',float('inf')):
            raise TimeoutError('Insufficient controller time for execution and cleanup')
        if self.cancel_file and self.cancel_file.exists(): raise Cancelled('cancelled before execution')
        if self.unknown: raise BackendUnknown('previous execution state unknown')
        if self.count>=7: raise RuntimeError('execution cap exhausted')
        if mode not in {'developer','protected','identity_probe','compensation_probe','final_holdout'}: raise ValueError('mode')
        self.count+=1
        identity='incidentforge-t4-'+uuid.uuid4().hex
        volume=identity+'-evidence'
        output=self.evidence.root/('execution-'+str(self.count));output.mkdir()
        self.evidence.event('execution_reserved',{'name':identity,'mode':mode,'backend':self.name,
            'timeout_seconds':100,'image':self.image,'ordinal':self.count})
        created=False;volume_created=False;terminal=False
        try:
            self.command(['volume','create',volume]);volume_created=True
            args=['create','--name',identity,'--read-only','--network','none','--pids-limit','128',
                '--memory','512m','--cpus','2','--cap-drop','ALL','--security-opt','no-new-privileges=true']
            for cap in ('SETUID','SETGID','SETPCAP','CHOWN','KILL'): args+=['--cap-add',cap]
            args+=['--tmpfs','/tmp:rw,nosuid,nodev,size=128m,mode=1777',
                '--tmpfs','/app:rw,nosuid,nodev,size=1m,mode=700','--workdir','/app',
                '--env','PYTHONDONTWRITEBYTECODE=1','--env','IF_CANDIDATE_ROOT=/app/candidate',
                '--mount',f'type=volume,source={volume},target=/evidence']
            for folder in ('fixture','tests','probes','evaluation','contracts'):
                args+=['--mount',f'type=bind,source={self.project/folder},target=/app/{folder},readonly']
            args+=['--mount',f'type=bind,source={candidate.resolve()},target=/app/candidate,readonly',
                self.image,'python','-m','probes.run_candidate','--mode',mode,'--incident',self.incident,'--output','/evidence/result']
            self.command(args);created=True
            self.command(['start',identity])
            end=time.monotonic()+100
            while True:
                state=json.loads(self.command(['inspect','--format','{{json .State}}',identity]))
                if not state['Running']:
                    terminal=True;break
                if self.cancel_file and self.cancel_file.exists(): raise Cancelled('user cancelled')
                if time.monotonic()>end: raise TimeoutError('candidate execution watchdog')
                time.sleep(.5)
            self.command(['cp',identity+':/evidence/result/.',str(output)])
            (output/'container-state.json').write_text(json.dumps(state))
            if state['ExitCode']!=0: raise RuntimeError('candidate runner failed; inspect execution evidence')
            result_path=output/'result.json'
            if result_path.is_symlink() or result_path.stat().st_size>1_000_000: raise ValueError('result bound')
            result=json.loads(result_path.read_text())
            self.evidence.event('execution_complete',{'name':identity,'terminal':True,
                'result':self.evidence.artifact(result),'mode':mode})
            return result
        finally:
            if created:
                try:
                    self.command(['rm','--force',identity])
                    terminal=True
                except Exception:
                    self.unknown=True
            if volume_created and terminal: self.command(['volume','rm',volume])
            self.evidence.event('execution_cleanup',{'name':identity,'terminal_confirmed':terminal,'unknown':self.unknown})
            if self.unknown: raise BackendUnknown('cannot confirm candidate termination; halt')
