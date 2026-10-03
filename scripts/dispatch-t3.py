"""One-shot T3 SDK dispatch. Standard profile auth; no secret serialization.

Invoke using the Python environment which owns the installed contree-client.
Unlike the CLI defaults this disables unsafe retries and guest networking.
"""
import hashlib
import json
from pathlib import Path
import zipfile
from contree_client.sync import ContreeClient
from contree_client.runtime import RetryPolicy
from contree_client.models import FileSpec,InstanceNetworking

root=Path(__file__).resolve().parents[1]
output=root/'runs'/'t3-remote-t2'
output.mkdir(parents=True,exist_ok=True)
reservation=output/'reservation.json'
if reservation.exists(): raise SystemExit('Dispatch already reserved: inspect its outcome before any new launch.')
reservation.write_text(json.dumps({'maximum_operations':1,'server_timeout_seconds':120,
    'networking':False,'free_coverage':'user confirmed 2026-10-03','state':'reserved'}))
bundle=output/'source.zip'
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
    for folder in ('fixture','tests','probes','evaluation','contracts'):
        for file in (root/folder).rglob('*'):
            if file.is_symlink(): raise ValueError('symlink')
            if file.is_file() and file.suffix in {'.py','.md'}:
                z.write(file,file.relative_to(root))
client=ContreeClient.from_profile(timeout=20,retry=RetryPolicy(max_attempts=1,retry_unsafe=False))
files={}
for local,remote in [(bundle,'/tmp/incidentforge-source.zip'),
                     (root/'probes/remote_t2_bootstrap.py','/tmp/incidentforge-bootstrap.py')]:
    uploaded=client.upload_file(local.read_bytes())
    files[remote]=FileSpec(uuid=uploaded.uuid,uid=0,gid=0,mode='0600')
try:
    result=client.spawn_instance(command='python',image='4fa16c8f-62a9-35a4-a4ea-07b7e8cd44ae',
        args=['/tmp/incidentforge-bootstrap.py'],cwd='/tmp',timeout=120,truncate_output_at=4096,
        networking=InstanceNetworking(enabled=False),files=files,disposable=False)
except Exception as exc:
    (output/'unknown.json').write_text(json.dumps({'state':'dispatch_unknown','exception_type':type(exc).__name__,
        'instruction':'Do not redispatch; reconcile project operations first.'}))
    raise SystemExit('Dispatch status unknown; do not retry. '+type(exc).__name__)
record=result.to_dict()
(output/'launch.json').write_text(json.dumps(record,indent=2))
(output/'source-sha256.txt').write_text(hashlib.sha256(bundle.read_bytes()).hexdigest())
print(json.dumps(record))
