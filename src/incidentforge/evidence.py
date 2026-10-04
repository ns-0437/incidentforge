"""Append-only, hash-chained controller events and content-addressed artifacts."""
from datetime import datetime,timezone
import hashlib
import json
import os
import re
from .records import encoded,digest

ARTIFACT_BOUND=2_000_000
CANONICAL_DIGEST=re.compile(r'[0-9a-f]{64}\Z')

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
        if len(raw)>ARTIFACT_BOUND: raise ValueError('artifact bound')
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
    """Append EVERY {'sha256','bytes'}-shaped reference at any depth.

    The shape is the signature emitted by Evidence.artifact and is the only
    producer of it. Occurrences are collected in a list, not a set, so that each
    one is validated individually; deduplication belongs to artifact reading.
    """
    if isinstance(value,dict):
        if set(value)=={'sha256','bytes'}:
            found.append((value.get('sha256'),value.get('bytes')));return
        for item in value.values(): references(item,found)
    elif isinstance(value,list):
        for item in value: references(item,found)

def admit(found,sizes,queue):
    """Validate every reference occurrence, then queue its digest for reading.

    Validation precedes path construction, so a malformed digest can never be
    turned into a filesystem path. A digest seen twice with different byte
    counts is rejected whichever occurrence arrives first.
    """
    for sha,size in found:
        if not isinstance(sha,str) or not CANONICAL_DIGEST.match(sha):
            raise ValueError('malformed artifact reference digest')
        if type(size) is not int or not 0<=size<=ARTIFACT_BOUND:
            raise ValueError('malformed artifact reference size: '+sha)
        if sizes.setdefault(sha,size)!=size:
            raise ValueError('conflicting artifact reference sizes: '+sha)
        queue.append(sha)

def verify(root):
    previous='0'*64
    count=0
    sizes={};queue=[]
    for line in (root/'events.jsonl').read_text(encoding='utf-8').splitlines():
        obj=json.loads(line);sha=obj.pop('sha256')
        if obj['seq']!=count or obj['previous']!=previous or digest(obj)!=sha: raise ValueError('event integrity')
        found=[];references(obj['payload'],found);admit(found,sizes,queue)
        previous=sha;count+=1
    for path in (root/'artifacts').iterdir():
        if hashlib.sha256(path.read_bytes()).hexdigest()!=path.name: raise ValueError('artifact integrity')
    # A hash chain proves events were not altered or reordered. It does not prove
    # that referenced content still exists, so resolve every reference, including
    # references nested inside artifact contents.
    seen=set()
    while queue:
        sha=queue.pop()
        if sha in seen: continue  # dedupes reads only; every reference is already validated
        seen.add(sha)
        path=root/'artifacts'/sha
        if not path.exists(): raise ValueError('missing referenced artifact: '+sha)
        raw=path.read_bytes()
        if len(raw)!=sizes[sha] or hashlib.sha256(raw).hexdigest()!=sha:
            raise ValueError('referenced artifact integrity: '+sha)
        try: nested=json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError,json.JSONDecodeError): continue
        found=[];references(nested,found);admit(found,sizes,queue)
    return count
