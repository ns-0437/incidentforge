"""Trusted local T2 world; candidate receives only an allowlisted public bundle."""
from contextlib import closing
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import hashlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import threading
import time
from fixture.app.common import canonical,http
from fixture.harness.t1 import World as T1World,UIDS,PORTS
from fixture.harness.persistence.v2 import initialize,Session
from fixture.harness.persistence.store import snapshot
from evaluation.controls import mutate

ROOT=Path(__file__).resolve().parents[2]


def read_rows(path,query):
    with closing(sqlite3.connect(path)) as db:
        db.row_factory=sqlite3.Row
        return [dict(r) for r in db.execute(query)]


class World(T1World):
    def __init__(self,root,control='reference',fault=False,pause=False,stock=None,trace=False):
        self.trace=trace
        self.root,self.control,self.fault,self.pause=root,control,fault,pause
        root.mkdir(parents=True)
        root.chmod(0o755)
        self.processes,self.files,self.services=[],[],{}
        self.events=[]
        self.dropped,self.release=threading.Event(),threading.Event()
        self.event_lock=threading.Lock()
        self.injected=False
        self.proxy=None
        self.event_file=root/'proxy.jsonl'
        self.event_file.touch(mode=0o600)
        self.broker_args=['--v2']
        self.initial=stock or {'A':10,'B':10}
        self.registry={}
        self.responses={}
        self.cancellations=set()
        self.started_ids=[]
        self.protocol_checks=[]
        self.bundle=root/'public'
        app=self.bundle/'fixture'/'app'
        app.mkdir(parents=True)
        for parent in (self.bundle,self.bundle/'fixture',app): parent.chmod(0o755)
        (self.bundle/'fixture'/'__init__.py').write_text('')
        (app/'__init__.py').write_text('')
        for name in ('common.py','contract.py'):
            (app/name).write_bytes((ROOT/'fixture'/'app'/name).read_bytes())
        (app/'service.py').write_text(mutate((ROOT/'fixture'/'app'/'service_v2.py').read_text(),control))
        candidate=os.environ.get('IF_CANDIDATE_ROOT')
        if candidate:
            if control!='reference': raise ValueError('candidate cannot mix with authored control')
            for name in ('service.py','common.py','contract.py'):
                source=Path(candidate)/'fixture'/'app'/name
                if source.is_symlink() or source.stat().st_size>64000: raise ValueError('candidate source bound')
                (app/name).write_bytes(source.read_bytes())
        (self.bundle/'CONTRACT.md').write_bytes((ROOT/'contracts'/'public'/'CONTRACT.md').read_bytes())
        if trace:
            (self.bundle/'_if_trace.py').write_bytes((ROOT/'fixture/harness/trace_runtime.py').read_bytes())
        self.bundle_hashes={str(p.relative_to(self.bundle)):hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in self.bundle.rglob('*') if p.is_file()}
        for p in self.bundle.rglob('*'):
            if p.is_file(): p.chmod(0o444)
        for service in UIDS: initialize(self.db(service),service)
        session=Session(self.db('inventory'),'inventory')
        try:
            session.request({'op':'begin'})
            session.request({'op':'execute','sql':'INSERT INTO app_state VALUES(?,?)',
                'params':['stock',canonical({sku:{'initial':n,'available':n,'held':0} for sku,n in self.initial.items()})]})
            session.request({'op':'commit'})
        finally: session.close()

    def start_service(self,service):
        path=self.root/(service+'-service.log')
        path.touch(mode=0o600,exist_ok=True)
        file=path.open('a')
        self.files.append(file)
        proc=subprocess.Popen([sys.executable,str(ROOT/'fixture/harness/launch.py'),str(UIDS[service]),
            str(self.bundle),'-m',('_if_trace' if self.trace and service=='order' else 'fixture.app.service'),'--service',service,'--socket',str(self.sock(service)),
            '--port',str(PORTS[service])],stdout=file,stderr=file,
            env={'PATH':'/usr/local/bin:/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'})
        self.processes.append(proc)
        self.services[service]=proc
        self.started_ids.append({'service':service,'pid':proc.pid,'start_ns':time.monotonic_ns()})
        end=time.monotonic()+5
        while time.monotonic()<end:
            if proc.poll() is not None:
                raise RuntimeError(service+' exited: '+path.read_text()[-2000:])
            try:
                if http(PORTS[service],'GET','/healthz',timeout=.2)[0]==200: return
            except OSError: pass
            time.sleep(.03)
        raise RuntimeError('service readiness timeout')

    def start_proxy(self):
        world=self
        class Proxy(BaseHTTPRequestHandler):
            def do_POST(self):
                self.connection.settimeout(2)
                try:
                    size=int(self.headers.get('Content-Length',0))
                    if not 0<size<=8192: raise ValueError('size')
                    body=json.loads(self.rfile.read(size))
                    if world.pause and world.dropped.is_set() and not world.release.wait(4):
                        self.connection.close()
                        return
                    status,res=http(PORTS['payment'],'POST',self.path,body)
                    effects=read_rows(world.db('payment'),'SELECT * FROM _payment_audit')
                    matching=[r for r in effects if r['effect_id']==res.get('charge_id') and
                              r['intent_id']==body.get('payment_intent_id') and
                              r['operation_key']==body.get('operation_key') and r['kind']=='charge']
                    world.log({'event':'payment_response','path':self.path,'body':body,'status':status,'response':res})
                    with world.event_lock:
                        drop=world.fault and not world.injected and status==201 and len(matching)==1
                        if drop: world.injected=True
                    if drop:
                        world.log({'event':'response_lost_after_commit','effect_id':matching[0]['effect_id'],
                                   'audit_seq':matching[0]['seq']})
                        world.dropped.set()
                        self.connection.shutdown(socket.SHUT_RDWR)
                        self.connection.close()
                        return
                    encoded=canonical(res).encode()
                    self.send_response(status)
                    self.send_header('Content-Length',str(len(encoded)))
                    self.end_headers()
                    self.wfile.write(encoded)
                except (OSError,ValueError):
                    self.connection.close()
            def log_message(self,*_): pass
        self.proxy=ThreadingHTTPServer(('127.0.0.1',8084),Proxy)
        threading.Thread(target=self.proxy.serve_forever,daemon=True).start()

    def submit(self,identity='order-1',expect='eligible',**overrides):
        body={'client_request_id':identity,'customer_id':'CUST-OK','items':[{'sku':'A','qty':1}],
              'amount_cents':100,'currency':'USD',**overrides}
        # Registered before HTTP. Candidate response cannot redefine expected outcome.
        expected=json.loads(json.dumps(body))
        counts={}
        for item in expected['items']: counts[item['sku']]=counts.get(item['sku'],0)+item['qty']
        expected['items']=[{'sku':sku,'qty':qty} for sku,qty in sorted(counts.items())]
        self.registry.setdefault(identity,{'payload':expected,'expect':expect})
        response=http(PORTS['order'],'POST','/orders',body)
        self.log({'event':'submit','id':identity,'status':response[0]})
        return response

    def cancel(self,oid='order-1',cid='cancel-1'):
        result=http(PORTS['order'],'POST','/orders/'+oid+'/cancel',{'cancel_request_id':cid})
        if result[0] in (200,202): self.cancellations.add(oid)
        self.log({'event':'cancel','id':oid,'status':result[0]})
        return result

    def observe(self,oid='order-1',timeout=4):
        end=time.monotonic()+timeout
        result=None
        while time.monotonic()<end:
            try:
                code,result=http(PORTS['order'],'GET','/orders/'+oid,timeout=.7)
                if code==200:
                    self.responses[oid]=result
                    if result['status'] in {'CONFIRMED','REJECTED_STOCK','CANCELLED_DECLINED','CANCELLED_BY_CLIENT'}:
                        return result
            except OSError: pass
            time.sleep(.04)
        return result

    def export(self,output):
        for oid in self.registry:
            try: self.responses[oid]=http(PORTS['order'],'GET','/orders/'+oid)[1]
            except OSError: pass
        self.close()
        self.root.chmod(0o700)  # Later candidates cannot inspect a previous control's bundle.
        output.mkdir(parents=True)
        output.chmod(0o700)
        snapshots={s:snapshot(self.db(s),output/(s+'.db')) for s in UIDS}
        manifest={'schema_version':1,'snapshots':snapshots,'registry':self.registry,
            'cancellations':sorted(self.cancellations),'responses':self.responses,'initial':self.initial,
            'events':self.events,'process_starts':self.started_ids,'bundle_sha256':self.bundle_hashes,
            'fault_requested':self.fault,'quiesced':all(p.poll() is not None for p in self.processes)}
        manifest['protocol_checks']=self.protocol_checks
        for p in self.root.glob('*.log'): (output/p.name).write_bytes(p.read_bytes())
        (output/'manifest.json').write_text(json.dumps(manifest,indent=2))
        return manifest
