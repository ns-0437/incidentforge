"""Small platform compatibility probe. No project source, secrets or model calls.

No external connections are attempted. A parent watchdog bounds child work.
"""
import argparse
import ctypes
import hashlib
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import platform
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time


def drop(uid):
    libc=ctypes.CDLL(None,use_errno=True)
    if libc.prctl(38,1,0,0,0): raise OSError('no_new_privs')
    for cap in range(41):
        if libc.prctl(24,cap,0,0,0): raise OSError('capability drop')
    os.setgroups([])
    os.setresgid(uid,uid,uid)
    os.setresuid(uid,uid,uid)


def child(args):
    from http.server import BaseHTTPRequestHandler,HTTPServer
    drop(args.uid)
    state=Path(args.state)
    private=Path(args.private)
    denied=False
    try: private.read_bytes()
    except PermissionError: denied=True
    if not denied: raise RuntimeError('protected read allowed')
    state.mkdir(exist_ok=True)
    db=sqlite3.connect(state/'state.db')
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS counter(value INTEGER)')
    row=db.execute('SELECT value FROM counter').fetchone()
    value=(row[0] if row else 0)+1
    db.execute('DELETE FROM counter')
    db.execute('INSERT INTO counter VALUES(?)',(value,))
    db.commit()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            raw=json.dumps({'uid':os.getuid(),'pid':os.getpid(),'starts':value,'private_denied':denied}).encode()
            self.send_response(200)
            self.send_header('Content-Length',str(len(raw)))
            self.end_headers();self.wfile.write(raw)
        def log_message(self,*_): pass
    server=HTTPServer(('127.0.0.1',0),Handler)
    print(json.dumps({'port':server.server_port}),flush=True)
    server.serve_forever()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--child',action='store_true')
    parser.add_argument('--uid',type=int)
    parser.add_argument('--state')
    parser.add_argument('--private')
    parser.add_argument('--output',type=Path,default=Path('/tmp/incidentforge-capability.json'))
    args=parser.parse_args()
    if args.child: return child(args)
    signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError('probe watchdog')))
    signal.alarm(12)
    procs=[]
    started=time.monotonic()
    report={'probe':'incidentforge-t3-capability-v1','python':sys.version,'platform':platform.platform(),
            'uid':os.getuid(),'checks':{},'scope':'three processes, loopback HTTP, UID drop, protected read, WAL restart'}
    try:
        import selectors
        with tempfile.TemporaryDirectory(prefix='if-capability-',ignore_cleanup_errors=True) as temp:
            root=Path(temp);root.chmod(0o755)
            secret=root/'private';secret.write_text('synthetic boundary sentinel');secret.chmod(0o600)
            def start(uid):
                state=root/str(uid)
                if not state.exists():
                    state.mkdir();state.chmod(0o700);os.chown(state,uid,uid)
                p=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--child','--uid',str(uid),
                    '--state',str(state),'--private',str(secret)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                procs.append(p)
                with selectors.DefaultSelector() as sel:
                    sel.register(p.stdout,selectors.EVENT_READ)
                    if not sel.select(3): raise TimeoutError('child readiness')
                    line=p.stdout.readline()
                    if not line: raise RuntimeError('child failed: '+p.stderr.read(2000))
                port=json.loads(line)['port']
                conn=HTTPConnection('127.0.0.1',port,timeout=1)
                try:
                    conn.request('GET','/')
                    result=json.loads(conn.getresponse().read(4096))
                finally: conn.close()
                return p,result
            observations=[]
            for uid in (20001,20002,20003):
                _,data=start(uid);observations.append(data)
            report['checks']['three_distinct_processes']=len({r['pid'] for r in observations})==3
            report['checks']['distinct_uids']=[r['uid'] for r in observations]==[20001,20002,20003]
            report['checks']['protected_read_denied']=all(r['private_denied'] for r in observations)
            procs[0].kill();procs[0].wait(timeout=1)
            _,restarted=start(20001)
            report['checks']['durable_restart']=restarted['starts']==2 and restarted['pid']!=observations[0]['pid']
            report['observations']=observations+[restarted]
            for proc in procs:
                if proc.poll() is None: proc.kill()
                proc.wait(timeout=1)
            for uid in (20001,20002,20003):
                os.chown(root/str(uid),0,0)
    except Exception as exc:
        report['error']=type(exc).__name__+': '+str(exc)
    finally:
        for proc in procs:
            if proc.poll() is None: proc.kill()
            proc.wait(timeout=1)
            if proc.stdout: proc.stdout.close()
            if proc.stderr: proc.stderr.close()
        signal.alarm(0)
    report['status']='PASS' if not report.get('error') and report['checks'] and all(report['checks'].values()) else 'FAIL'
    report['seconds']=round(time.monotonic()-started,3)
    raw=(json.dumps(report,indent=2)+'\n').encode()
    args.output.write_bytes(raw)
    print(json.dumps({'status':report['status'],'artifact':str(args.output),'sha256':hashlib.sha256(raw).hexdigest(),'report':report}))
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__': raise SystemExit(main())
