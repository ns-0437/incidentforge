"""Single SDK operation with durable reservation, cancellation and bounded export.
Run under the existing ConTree Python environment. Exceptions never print secrets.
"""
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import time
from contree_client.sync import ContreeClient
from contree_client.runtime import RetryPolicy
from contree_client.models import FileSpec,InstanceNetworking

def main():
    request=json.loads(Path(sys.argv[1]).read_text())
    out=Path(request['output']);guard=Path(request['guard']);cancel=Path(request['cancel'])
    client=ContreeClient.from_profile(timeout=20,retry=RetryPolicy(max_attempts=1,retry_unsafe=False))
    terminal=False;operation=None;dispatching=False
    try:
        if '--recover' in sys.argv:
            launch=json.loads((out/'launch.json').read_text())
            dispatching=True
        else:
            files={}
            for local,remote in [(out/'source.zip','/tmp/source.zip'),(Path(request['bootstrap']),'/tmp/bootstrap.py')]:
                uploaded=client.upload_file(local.read_bytes())
                files[remote]=FileSpec(uuid=uploaded.uuid,uid=0,gid=0,mode='0600')
            if cancel.exists():
                terminal=True
                raise RuntimeError('cancelled before dispatch')
            dispatching=True
            launch=client.spawn_instance(command='python',image=request['image'],args=['/tmp/bootstrap.py',request['mode'],request['incident']],
              cwd='/tmp',timeout=120,truncate_output_at=4096,networking=InstanceNetworking(enabled=False),files=files,disposable=False).to_dict()
            (out/'launch.json').write_text(json.dumps(launch,indent=2))
        operation=launch['uuid'];deadline=time.monotonic()+140;cancelled=False
        while True:
            state=client.get_operation_status(operation,inflight=False).to_dict()
            (out/'operation.json').write_text(json.dumps(state,indent=2))
            if state['status'] in ('SUCCESS','FAILED','CANCELLED'):
                terminal=True;break
            if cancel.exists() and not cancelled:
                client.cancel_operation(operation);cancelled=True
            if time.monotonic()>deadline:
                if not cancelled: client.cancel_operation(operation)
                raise TimeoutError('terminal state unconfirmed')
            time.sleep(1)
        execution=state.get('metadata',{}).get('result') or {}
        if state['status']!='SUCCESS' or execution.get('state',{}).get('exit_code')!=0: raise RuntimeError('remote runner unsuccessful')
        if execution['stdout'].get('truncated'): raise ValueError('truncated completion receipt')
        metadata=json.loads(execution['stdout']['value'].strip())
        if not 0<metadata['bytes']<=16_000_000: raise ValueError('archive size')
        data=bytearray()
        for block in client.inspect_image_archive(state['result_image_uuid'],'/tmp/evidence.zip',compressed=False):
            data.extend(block)
            if len(data)>17_000_000: raise ValueError('tar size')
        with tarfile.open(fileobj=io.BytesIO(data),mode='r:') as archive:
            members=archive.getmembers()
            if len(members)!=1 or not members[0].isfile() or members[0].size!=metadata['bytes']: raise ValueError('tar shape')
            content=archive.extractfile(members[0]).read(16_000_001)
        if hashlib.sha256(content).hexdigest()!=metadata['sha256']: raise ValueError('archive hash')
        (out/'evidence.zip').write_bytes(content)
        (out/'receipt.json').write_text(json.dumps({'operation':operation,'terminal':True,'sha256':metadata['sha256'],
            'duration_seconds':state.get('duration'),'provider_resources':execution.get('resources'),
            'provider_cost_unit':'unspecified; not USD inference spend'}))
        return 0
    except Exception as exc:
        # An upload failure cannot have started execution. A spawn failure may have.
        if not dispatching: terminal=True
        (out/'error.json').write_text(json.dumps({'exception_type':type(exc).__name__,
           'operation':operation,'terminal_confirmed':terminal,'redispatch_allowed':terminal}))
        return 1
    finally:
        if terminal and guard.exists() and json.loads(guard.read_text()).get('output')==str(out):
            guard.unlink()

if __name__=='__main__': raise SystemExit(main())
