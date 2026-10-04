"""Append-only, hash-chained controller events and content-addressed artifacts."""
from datetime import datetime,timezone
import hashlib
import json
import os
from .records import encoded,digest

class Evidence:
    def __init__(self,root,run_id):
        self.root=root
        root.mkdir(parents=True,exist_ok=False)
        (root/'artifacts').mkdir()
        self.run_id=run_id
        self.previous='0'*64
        self.seq=0

    def artifact(self,value):
        raw=value if isinstance(value,bytes) else encoded(value)
        if len(raw)>2_000_000: raise ValueError('artifact bound')
        sha=hashlib.sha256(raw).hexdigest()
        target=self.root/'artifacts'/sha
        if not target.exists(): target.write_bytes(raw)
        return {'sha256':sha,'bytes':len(raw)}

    def event(self,kind,payload):
        value={'schema_version':1,'run_id':self.run_id,'seq':self.seq,
            'time_utc':datetime.now(timezone.utc).isoformat(),'actor':'controller',
            'kind':kind,'previous':self.previous,'payload':payload}
        sha=digest(value)
        with (self.root/'events.jsonl').open('ab') as f:
            f.write(encoded({**value,'sha256':sha})+b'\n');f.flush();os.fsync(f.fileno())
        self.previous=sha;self.seq+=1
        return sha

def references(value,found):
    """Collect {'sha256','bytes'} artifact references at any depth."""
    if isinstance(value,dict):
        if set(value)=={'sha256','bytes'} and isinstance(value.get('sha256'),str) and type(value.get('bytes')) is int:
            found.add((value['sha256'],value['bytes']));return
        for item in value.values(): references(item,found)
    elif isinstance(value,list):
        for item in value: references(item,found)

def verify(root):
    previous='0'*64
    count=0
    referenced=set()
    for line in (root/'events.jsonl').read_text(encoding='utf-8').splitlines():
        obj=json.loads(line);sha=obj.pop('sha256')
        if obj['seq']!=count or obj['previous']!=previous or digest(obj)!=sha: raise ValueError('event integrity')
        references(obj['payload'],referenced)
        previous=sha;count+=1
    for path in (root/'artifacts').iterdir():
        if hashlib.sha256(path.read_bytes()).hexdigest()!=path.name: raise ValueError('artifact integrity')
    # A hash chain proves events were not altered or reordered. It does not prove
    # that referenced content still exists, so resolve every reference, including
    # references nested inside artifact contents.
    pending=list(referenced);seen=set()
    while pending:
        sha,size=pending.pop()
        if sha in seen: continue
        seen.add(sha)
        path=root/'artifacts'/sha
        if not path.exists(): raise ValueError('missing referenced artifact: '+sha)
        raw=path.read_bytes()
        if len(raw)!=size or hashlib.sha256(raw).hexdigest()!=sha:
            raise ValueError('referenced artifact integrity: '+sha)
        try: nested=json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError,json.JSONDecodeError): continue
        found=set();references(nested,found)
        pending.extend(ref for ref in found if ref[0] not in seen)
    return count
