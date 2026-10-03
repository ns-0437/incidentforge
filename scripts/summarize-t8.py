"""Verify retained campaign evidence and publish only curated result fields."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from incidentforge.evidence import verify
from incidentforge.workspace import Workspace

campaign=ROOT/'runs/t8-final-20261003'
spec=importlib.util.spec_from_file_location('frozen_driver',ROOT/'scripts/run-t8.py')
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
freeze=json.loads((campaign/'freeze.json').read_text())
assert freeze['source_hashes']==driver.pins(), 'Frozen source changed'
assert freeze['driver_sha256']==hashlib.sha256((ROOT/'scripts/run-t8.py').read_bytes().replace(b'\r\n',b'\n')).hexdigest()
launches=[json.loads(s) for s in (campaign/'launches.jsonl').read_text().splitlines()]
assert len({r['slot'] for r in launches})==len(launches)
attempts=[]
for launch in launches:
    outcome=json.loads((campaign/f"slot-{launch['slot']:02}.json").read_text())
    assert all(outcome[k]==launch[k] for k in ('slot','incident','variant','repetition','run_id'))
    run=ROOT/'runs'/outcome['run_id']; report=outcome['agent_report']
    count=verify(run)
    assert count==outcome['verified_events']
    assert json.loads((run/'report.json').read_text())==report
    events=[json.loads(s) for s in (run/'events.jsonl').read_text().splitlines()]
    assert events[-1]['kind']=='report' and events[-1]['payload']==report
    rejections=Counter(e['payload']['reason'] for e in events if e['kind']=='action_rejected')
    usage=[e['payload']['usage'] for e in events if e['kind']=='model_response']
    cases=[]; independent=False; receipts=[]
    receipt_roots=[run]
    if outcome['final_evidence']:
        final_root=ROOT/'runs'/outcome['final_evidence'];verify(final_root)
        final_events=[json.loads(s) for s in (final_root/'events.jsonl').read_text().splitlines()]
        assert final_events[-1]['kind']=='final_result' and final_events[-1]['payload']==outcome['final_result']
        assert Workspace(run/'candidate').revision()==report['candidate_revision']
        independent_report=json.loads((final_root/'execution-1/independent-verification.json').read_text())
        cases=[{'case':c['case'],'decision':c['decision'],
                'properties':{k:v['status'] for k,v in c['properties'].items()}}
               for c in outcome['final_result']['cases']]
        assert sorted((c['case'],c['decision']) for c in cases)==sorted((c['case'],c['decision']) for c in independent_report['cases'])
        independent=True
        receipt_roots.append(final_root)
    for receipt_root in receipt_roots:
        for path in sorted(receipt_root.glob('execution-*/receipt.json')):
            receipt=json.loads(path.read_text())
            receipts.append({k:receipt[k] for k in ('terminal','sha256','duration_seconds','provider_resources','provider_cost_unit')})
    attempts.append({'slot':outcome['slot'],'incident':outcome['incident'],'variant':outcome['variant'],
        'repetition':outcome['repetition'],'run_id':outcome['run_id'],'final_decision':outcome['final_decision'],
        'elapsed_seconds':outcome['elapsed_seconds'],'reason':report['reason'],
        'accounting':report['accounting'],'edits':report['edits'],'frozen_candidate':bool(report.get('candidate_revision')),
        'candidate_revision':report.get('candidate_revision'),'verified_events':count,'case_outcomes':cases,
        'final_case_errors':[{'case':c['case'],'error_type':c['error'].split(':',1)[0]} for c in outcome['final_result'].get('case_errors',[])],
        'independently_verified':independent,'action_rejections':dict(rejections),'resource_receipts':receipts,
        'reported_prompt_tokens':sum(u['prompt_tokens'] for u in usage),
        'reported_completion_tokens':sum(u['completion_tokens'] for u in usage),
        'remote_operations':sum(e['kind']=='execution_reserved' for e in events)+(1 if outcome['final_evidence'] else 0)})
with sqlite3.connect(ROOT/'runs/t4-budget.sqlite') as db:
    settled,exposure,unknown,pending=db.execute("SELECT COALESCE(SUM(actual),0),COALESCE(SUM(COALESCE(actual,cap)),0),SUM(actual IS NULL),SUM(status='reserved') FROM calls").fetchone()
    conservative=db.execute("SELECT COALESCE(SUM(cap),0) FROM calls WHERE status='conservative_unknown'").fetchone()[0]
assert exposure<=200000
complete=len(attempts)==12
summary=json.loads((ROOT/'benchmarks/t8/summary.json').read_text())
summary.update(status='completed_with_unknown_usage' if complete else 'incomplete',launched_runs=len(attempts),
    unlaunched_runs=12-len(attempts),attempts=attempts,
    accepted_final_repairs=sum(a['final_decision']=='accept_for_review' for a in attempts),
    final_candidates_evaluated=sum(a['independently_verified'] for a in attempts),
    campaign_estimated_settled_microusd=sum(a['accounting']['estimated_usage_microusd'] for a in attempts),
    project_estimated_settled_microusd=settled,project_reserved_or_spent_microusd=exposure,
    pending_calls=pending,unknown_usage_calls=unknown,conservatively_charged_microusd=conservative,
    stop_reason='All 12 scheduled attempts completed. Unknown provider usage is retained at its full reservation; no failed attempts were replaced.' if complete else 'Continuation stopped; inspect retained ledger.',
    continuation='T8_CONTINUATION.md: accounting amendment after slots 1–4; frozen agent and evaluator unchanged.',
    continuation_driver_sha256=hashlib.sha256((ROOT/'scripts/continue-t8.py').read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
    limitations=['Two independent attempts per variant/family; descriptive counts only.',
      'Same two defects with different withheld schedules; not novel-incident generalization.',
      'Interrupted campaign with disclosed accounting amendment.',
      'Unknown provider usage counted at full reservation, never reported as known actual cost.',
      'Unfrozen attempts count against valid-repair yield but are not measured schedule failures.',
      'Raw prompts, credentials, databases and account data excluded.'])
summary['cells']=[{'incident':incident,'variant':variant,'launched':sum(a['incident']==incident and a['variant']==variant for a in attempts),
    'accepted':sum(a['incident']==incident and a['variant']==variant and a['final_decision']=='accept_for_review' for a in attempts)}
    for incident in ('IF-001','IF-002') for variant in ('B0','B1','B2')]
summary['infrastructure_failed_attempts']=sum('usage unknown' in a['reason'] or a['final_decision']=='invalid_evaluation' or 'BackendUnknown' in a['reason'] for a in attempts)
summary['infrastructure_invalidity_triggered']=summary['infrastructure_failed_attempts']>2
summary['ranking_supported']=False
(ROOT/'benchmarks/t8/summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:summary[k] for k in ('status','launched_runs','accepted_final_repairs','final_candidates_evaluated','project_reserved_or_spent_microusd','unknown_usage_calls')}))
