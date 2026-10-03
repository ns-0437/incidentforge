"""Render the review report from the verified curated campaign summary."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=json.loads((ROOT/'benchmarks/t8/summary.json').read_text())
money=lambda n:f'${n/1e6:.6f}'
lines=['# T8 results: '+('completed campaign, unreliable infrastructure' if s['launched_runs']==12 else 'incomplete campaign'),'',
 'October 3, 2026. **'+str(s['launched_runs'])+'/12 planned attempts recorded; '+str(s['accepted_final_repairs'])+' accepted final repairs.**',
 str(s['final_candidates_evaluated'])+' frozen candidates reached independently verified final evaluation. Unfrozen attempts count against repair yield, but are not measured final-schedule failures.', '',
 '**No variant ranking is supported.** '+str(s['infrastructure_failed_attempts'])+' attempts encountered infrastructure failure; the predeclared threshold is more than two. Two attempts per variant/family would in any event support only descriptive counts.', '',
 '## All attempts', '', '| Slot | Family | Variant | Final outcome | Settled estimate | Unknown reservation |',
 '| --- | --- | --- | --- | --- | --- |']
for a in s['attempts']:
    account=a['accounting']; unknown=account['reserved_or_spent_microusd']-account['estimated_usage_microusd']
    lines.append(f"| {a['slot']} | {a['incident']} | {a['variant']} | {a['final_decision']} | {money(account['estimated_usage_microusd'])} | {money(unknown)} |")
lines+=['','## Descriptive repair yield','','Accepted final repairs / launched independent attempts:','',
 '| Family | B0 | B1 | B2 |','| --- | --- | --- | --- |']
for incident in ('IF-001','IF-002'):
    cells=[next(c for c in s['cells'] if c['incident']==incident and c['variant']==v) for v in ('B0','B1','B2')]
    lines.append('| '+incident+' | '+' | '.join(f"{c['accepted']}/{c['launched']}" for c in cells)+' |')
lines+=['','## Final-case evidence','']
for a in s['attempts']:
    if a['case_outcomes']:
        lines.append(f"- Slot {a['slot']} ({a['incident']} / {a['variant']}): "+'; '.join(c['case']+': '+c['decision'] for c in a['case_outcomes'])+'.')
lines+=['','Each final export was independently recomputed by the restricted Docker reader. Candidate hashes were checked before and after final evaluation. Final results never fed back to the controller. Finite schedules do not prove universal correctness.','',
 '## Failures and follow-up','']
for a in s['attempts']:
    if a['final_decision']!='accept_for_review':
        lines.append(f"- Slot {a['slot']}: {a['reason'].rstrip('.')}."+(' Rejections: '+json.dumps(a['action_rejections'],ensure_ascii=False)+'.' if a['action_rejections'] else ''))
lines+=['',
 'Slot 10 is a concrete claim/evidence mismatch: the model said it added a release, but the controller recorded zero edits. The frozen candidate failed the two IF-002 restart schedules on eligible-order progress (P3) and compensation (P4). Model prose is not accepted as evidence of a code change.', '',
 'The failures expose two development priorities: model adherence to the exact action/assertion and factual-conclusion schemas, and inference completion within the fixed timeout. Investigate these in a new development revision. Do not tune this frozen campaign or replace failed attempts. A fresh comparison needs a new declared freeze.', '',
 '## Accounting and interruption','',
 'Campaign settled token-price estimate: **'+money(s['campaign_estimated_settled_microusd'])+'**. Project settled estimate: **'+money(s['project_estimated_settled_microusd'])+'**. Project exposure including all unknown reservations: **'+money(s['project_reserved_or_spent_microusd'])+' / $0.20**.', '',
 str(s['unknown_usage_calls'])+' calls retain unknown actual usage. Their full reservations remain charged against the cap; no fabricated usage or refund is recorded. These are token-price estimates and conservative allocations, not a provider invoice. Sandbox resource cost units are unspecified and are not USD inference spend.', '',
 'After slot 4, the campaign paused. The user authorized the [accounting amendment](T8_CONTINUATION.md). Slots 1–4, the original freeze, model, prompts, source, evaluator and schedule were preserved. Only unlaunched slots continued. No failed slot was retried. This interruption and amendment are part of the result.', '',
 '## Evaluator readiness and limitations','',
 'Both authored references passed four final schedules locally and on Nebius Sandbox before freeze. Five harmful controls were rejected locally. These controls establish evaluator readiness, not model repair success.', '',
 'The final schedules use the same two defect implementations as development. The inherited per-case `conditions` label and controller report pilot disclaimer are stale labels from shared code; the separately recorded `final_holdout` mode, schedule version, source freeze and final evidence establish which workloads ran. Original raw records were preserved rather than rewritten.', '',
 'The original freeze SHA256 remains `'+s['freeze_sha256']+'`. The original Git commit maps to identical source at `'+s['equivalent_commit_after_author_email_correction']+'` after author-email correction.', '',
 'Curated [machine-readable results](../benchmarks/t8/summary.json) include all attempt denominators, candidate revisions, case outcomes, reported tokens, elapsed times, action rejections and sanitized provider resource receipts. Full event chains and raw exports remain local. The project repository remains private.', '',
 'T8 execution and reporting are complete: all twelve slots are recorded. The observed infrastructure threshold prevents a reliable variant comparison. T9 packaging can proceed with these limitations disclosed.']
(ROOT/'docs/T8_RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('Rendered T8_RESULTS.md')
