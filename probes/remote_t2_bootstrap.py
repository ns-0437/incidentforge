"""Trusted remote entrypoint: unpack reviewed source, protect it, run T2, export."""
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import subprocess
import sys
import zipfile

root=Path('/app')
root.mkdir(exist_ok=True)
root.chmod(0o700)
with zipfile.ZipFile('/tmp/incidentforge-source.zip') as archive:
    if sum(i.file_size for i in archive.infolist())>2_000_000: raise ValueError('source size')
    for entry in archive.infolist():
        p=PurePosixPath(entry.filename)
        if p.is_absolute() or '..' in p.parts or p.parts[0] not in {'fixture','tests','probes','evaluation','contracts'}:
            raise ValueError('source path')
        target=root/str(p)
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(archive.read(entry))
Path('/tmp/incidentforge-source.zip').unlink()
evidence=Path('/evidence')
evidence.mkdir(exist_ok=True);evidence.chmod(0o700)
log=evidence/'runner.log'
with log.open('w') as output:
    result=subprocess.run([sys.executable,'-m','probes.run_t2','--require-linux','--output','/evidence/t2'],
        cwd=root,env={'PATH':'/usr/local/bin:/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'},
        stdout=output,stderr=subprocess.STDOUT,timeout=100)
target=Path('/tmp/incidentforge-t2-evidence.zip')
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
    for p in evidence.rglob('*'):
        if p.is_file(): archive.write(p,p.relative_to(evidence))
target.chmod(0o600)
print(json.dumps({'exit_code':result.returncode,'artifact':str(target),
                  'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'bytes':target.stat().st_size}),flush=True)
raise SystemExit(result.returncode)
