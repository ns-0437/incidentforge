"""Validate the exact static publishing allowlist without inference or raw runs."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ALLOWED={'.nojekyll','index.html','style.css','app.js','icon.svg','evidence.json','evidence.sha256'}

def validate_evidence(data):
    """Reject internally contradictory claims even when their digest is updated."""
    incidents=data.get('incidents',[])
    if data.get('version')!=1 or data.get('mode')!='recorded' or len(incidents)!=2:
        raise ValueError('Unexpected evidence schema')
    if {r.get('incident') for r in incidents}!={'IF-001','IF-002'}:
        raise ValueError('Missing or duplicate incident')
    for row in incidents:
        count=row.get('protected_cases')
        if type(count) is not int or count<1: raise ValueError('Missing protected cases')
        props=row.get('properties',{})
        if set(props)!={f'P{i}' for i in range(1,8)}: raise ValueError('Missing protected property')
        for values in props.values():
            if not isinstance(values,list) or len(values)!=count or any(v not in ('pass','fail','not_applicable','unknown') for v in values):
                raise ValueError('Invalid property coverage')
            if row.get('decision')=='accept_for_review' and any(v not in ('pass','not_applicable') for v in values):
                raise ValueError('Accepted candidate contains failed or unknown property')
    campaign=data.get('campaign',{});attempts=data.get('attempts',[])
    for key in ('planned_runs','launched_runs','unlaunched_runs','accepted_final_repairs','final_candidates_evaluated'):
        if type(campaign.get(key)) is not int or campaign[key]<0: raise ValueError('Invalid campaign count')
    if campaign['planned_runs']!=campaign['launched_runs']+campaign['unlaunched_runs'] or len(attempts)!=campaign['launched_runs']:
        raise ValueError('Campaign denominator mismatch')
    if len({a['slot'] for a in attempts})!=len(attempts): raise ValueError('Duplicate attempt slot')
    if sum(a['final_decision']=='accept_for_review' for a in attempts)!=campaign['accepted_final_repairs']:
        raise ValueError('Campaign acceptance mismatch')
    for cell in data.get('cells',[]):
        matches=[a for a in attempts if a['incident']==cell['incident'] and a['variant']==cell['variant']]
        if len(matches)!=cell['launched'] or sum(a['final_decision']=='accept_for_review' for a in matches)!=cell['accepted']:
            raise ValueError('Campaign cell mismatch')


def check(site):
    entries=list(site.iterdir())
    if {p.name for p in entries}!=ALLOWED or any(p.is_symlink() or not p.is_file() for p in entries):
        raise ValueError('Static directory differs from publishing allowlist')
    expected=(site/'evidence.sha256').read_text().split()
    if len(expected)!=2 or expected[1]!='evidence.json': raise ValueError('Invalid evidence manifest')
    if hashlib.sha256((site/'evidence.json').read_bytes()).hexdigest()!=expected[0]:
        raise ValueError('Evidence digest mismatch')
    data=json.loads((site/'evidence.json').read_text(encoding='utf-8'))
    validate_evidence(data)
    return {'files':len(entries),'evidence_sha256':expected[0],'incidents':len(data['incidents'])}

if __name__=='__main__': print(json.dumps(check(ROOT/'site'),indent=2))
