"""Trusted no-network remote candidate runner; no credentials are uploaded."""
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import subprocess
import sys
import zipfile

root=Path('/app');root.mkdir(exist_ok=True);root.chmod(0o700)
with zipfile.ZipFile('/tmp/source.zip') as z:
    entries=z.infolist()
    if len(entries)>256 or sum(i.file_size for i in entries)>2_000_000: raise ValueError('bundle bound')
    seen=set()
    for i in entries:
        p=PurePosixPath(i.filename)
        if not p.parts or p.is_absolute() or '..' in p.parts or '\\' in i.filename or ':' in i.filename or i.filename in seen:
            raise ValueError('bundle path')
        if p.parts[0] not in {'fixture','tests','probes','evaluation','contracts','candidate'}: raise ValueError('bundle root')
        seen.add(i.filename)
        target=root.joinpath(*p.parts);target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(z.read(i))
Path('/tmp/source.zip').unlink()
out=Path('/evidence');out.mkdir(exist_ok=True);out.chmod(0o700)
env={'PATH':'/usr/local/bin:/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','IF_CANDIDATE_ROOT':'/app/candidate'}
with (out/'runner.log').open('w') as log:
    command=[sys.executable,'-m','probes.run_candidate','--mode',sys.argv[1],'--incident',sys.argv[2],'--output','/evidence/result']
    completed=subprocess.run(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=100)
target=Path('/tmp/evidence.zip')
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
    for p in out.rglob('*'):
        if p.is_file() and not p.is_symlink(): z.write(p,p.relative_to(out))
target.chmod(0o600)
print(json.dumps({'exit_code':completed.returncode,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
                  'bytes':target.stat().st_size}),flush=True)
raise SystemExit(completed.returncode)
