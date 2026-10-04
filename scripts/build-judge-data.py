"""Export an explicit allowlist of synthetic, recorded development evidence."""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from incidentforge.evidence import verify

items=[]
for incident,run_id,title in [
    ('IF-001','b2-if-001-20261004T083619Z-fb280e','The charge that happened twice'),
    ('IF-002','b2-if-002-20261004T111830Z-d03bc1','The reservation that never cleared')]:
    root=ROOT/'runs'/run_id;count=verify(root)
    report=json.loads((root/'report.json').read_text(encoding='utf-8'))
    events=[json.loads(line) for line in (root/'events.jsonl').read_text(encoding='utf-8').splitlines()]
    assert events[-1]['kind']=='report' and events[-1]['payload']==report
    records=json.loads((root/'records.json').read_text(encoding='utf-8'))
    hypotheses=[{'mechanism':r['data']['mechanism'],'confidence_basis':r['data']['confidence_basis']}
                for r in records if r['kind']=='Hypothesis']
    experiments=[r['data']['observations'] for r in records if r['kind']=='ExperimentResult']
    observations=[]
    for experiment in experiments:
        for o in experiment.get('observations',[]):
            condition=o.get('condition')
            if not condition: continue
            cell={'condition':condition}
            for key in ('committed_charge_count','http_statuses'):
                if key in o: cell[key]=o[key]
            if 'order' in o: cell['order_status']=(o['order'] or {}).get('status','UNKNOWN')
            if 'stock' in o: cell['available_stock']={k:v['available'] for k,v in o['stock'].items()}
            observations.append(cell)
    validations=[r['data'] for r in records if r['kind']=='ValidationReport']
    last=validations[-1];properties={}
    for case in last['properties']:
        for values in case.values():
            for name,p in values.items(): properties.setdefault(name,[]).append(p['status'])
    diffs=[]
    for r in records:
        if r['kind']=='PatchCandidate':
            for ref in r['artifacts']:
                text=(root/'artifacts'/ref['sha256']).read_text(encoding='utf-8')
                diffs.extend(line for line in text.splitlines() if line.startswith(('+','-')) and not line.startswith(('+++','---')))
    regression=[]
    for event in events:
        if event['kind']!='tool_result': continue
        value=json.loads((root/'artifacts'/event['payload']['artifact']['sha256']).read_text(encoding='utf-8'))
        if not isinstance(value,dict): continue
        if value.get('saved') is True and 'specification' in value:
            spec=json.loads((root/'artifacts'/value['specification']['sha256']).read_text(encoding='utf-8'))
            regression.append({'kind':'authored','assertions':spec['assertions'],
                               'baseline_assessment':value.get('baseline_assessment')})
        elif isinstance(value.get('developer_tests'),dict):
            receipt=value['developer_tests']
            regression.append({'kind':'execution','passed':receipt.get('passed'),
                               'assertions':receipt.get('assertions',[])})
    if incident=='IF-001':
        # A later audit is explicitly labeled; never rewrite the historical run.
        audit=json.loads((ROOT/'benchmarks/reliability/v22-pilot.json').read_text(encoding='utf-8'))
        assert audit['report']['run_id']==run_id
        authored=[r for r in regression if r['kind']=='authored']
        if authored and authored[-1]['baseline_assessment'] is None:
            authored[-1]['baseline_assessment']=audit['post_run_baseline_assessment']
            authored[-1]['baseline_assessment_provenance']='Post-run assessment against retained original observations; not recorded during the run.'
    items.append({'incident':incident,'run_id':run_id,'title':title,'backend':report['backend'],
      'decision':report['decision'],'calls':report['accounting']['calls'],
      'estimated_usd':report['accounting']['estimated_usage_microusd']/1e6,'verified_events':count,
      'candidate_revision':report['candidate_revision'],'observations':observations,'hypotheses':hypotheses,
      'regression_tests':regression,'final_authored_tests_passed':report.get('verified_work',{}).get('developer_tests_passed_on_current_revision'),
      'patch_lines':diffs,'properties':properties,'protected_cases':len(last['properties']),
      'judge_note':'Repair passed declared development checks. Causal prose is not independently validated.',
      'scope':'Recorded development run, not a T8 final comparison.'})
campaign=json.loads((ROOT/'benchmarks/t8/summary.json').read_text(encoding='utf-8'))
data={'version':1,'updated':'2026-10-04','mode':'recorded','incidents':items,
      'campaign':{k:campaign[k] for k in ('status','planned_runs','launched_runs','unlaunched_runs','ranking_supported','stop_reason','accepted_final_repairs','final_candidates_evaluated')},
      'cells':campaign.get('cells',[]),
      'attempts':[{k:r[k] for k in ('slot','incident','variant','final_decision','reason')} for r in campaign['attempts']],
      'limitations':['Development runs are separate from the frozen comparison.',
        'Two synthetic defect implementations; finite checks are not a correctness proof.',
        'GitHub Pages serves recorded evidence. Live execution requires the local controller and credentials.',
        'IF-002 restarts Inventory and Order to discard queued pre-crash requests.']}
out=ROOT/'site';out.mkdir(exist_ok=True)
raw=json.dumps(data,indent=2,ensure_ascii=False).encode()
(out/'evidence.json').write_bytes(raw)
(out/'evidence.sha256').write_text(hashlib.sha256(raw).hexdigest()+'  evidence.json\n')
print(json.dumps({'incidents':len(items),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}))
