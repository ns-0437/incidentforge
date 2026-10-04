"""Validate the exact static publishing allowlist without inference or raw runs."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ALLOWED={'.nojekyll','index.html','style.css','app.js','icon.svg','evidence.json','evidence.sha256'}

def check(site):
    entries=list(site.iterdir())
    if {p.name for p in entries}!=ALLOWED or any(p.is_symlink() or not p.is_file() for p in entries):
        raise ValueError('Static directory differs from publishing allowlist')
    expected=(site/'evidence.sha256').read_text().split()
    if len(expected)!=2 or expected[1]!='evidence.json': raise ValueError('Invalid evidence manifest')
    if hashlib.sha256((site/'evidence.json').read_bytes()).hexdigest()!=expected[0]:
        raise ValueError('Evidence digest mismatch')
    data=json.loads((site/'evidence.json').read_text(encoding='utf-8'))
    if data.get('version')!=1 or len(data.get('incidents',[]))!=2:
        raise ValueError('Unexpected evidence schema')
    return {'files':len(entries),'evidence_sha256':expected[0],'incidents':len(data['incidents'])}

if __name__=='__main__': print(json.dumps(check(ROOT/'site'),indent=2))
