"""Read-only audit of retained development runs and the contradictory pilot claim."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from incidentforge.evidence import verify
from incidentforge.grounding import check_interpretation,factual_conclusion
names=['prefreeze-e90836be','prefreeze-e60ebc10','remote-lifecycle-6a44eaf9','remote-lifecycle-8fa4228f',
       'b2-if-002-20261003T100824Z-46dfa7','b2-if-002-20261003T101112Z-580ac9','b2-if-002-20261003T101505Z-4c2892']
chains={name:verify(ROOT/'runs'/name) for name in names}
p=ROOT/'runs'/names[-1]
events=[json.loads(line) for line in (p/'events.jsonl').read_text(encoding='utf-8').splitlines()]
interpretation=next(e['payload'] for e in events if e['kind']=='model_interpretation')
facts=json.loads(interpretation['observed_facts'])
try: check_interpretation(interpretation,facts)
except ValueError: rejected=True
else: rejected=False
assert rejected,'Historical reversed conclusion must be rejected by current protocol'
corrected={**interpretation,'conclusion':factual_conclusion(facts)}
check_interpretation(corrected,facts)
assert not (ROOT/'runs/contree-active.json').exists(),'unresolved remote execution'
with sqlite3.connect(ROOT/'runs/t4-budget.sqlite') as db:
    spend,pending,calls=db.execute('SELECT SUM(actual),SUM(CASE WHEN actual IS NULL THEN 1 ELSE 0 END),COUNT(*) FROM calls').fetchone()
assert pending==0 and spend<=200000
brief=hashlib.sha256((ROOT/'docs/ORIGINAL_BRIEF.md').read_bytes()).hexdigest()
assert brief=='4a2d5f78d37fdfd9bcd450b32374533f146e66c28eecdaf55488d6dfe9bb29af'
result={'verified_event_chains':chains,'original_brief_sha256':brief,'estimated_inference_microusd':spend,
  'pending_inference_calls':pending,'total_inference_calls':calls,'historical_reversed_conclusion_rejected':rejected,
  'required_factual_conclusion':corrected['conclusion'],
  'limitations':['Final factual-conclusion protocol tested offline against the retained live failure; no subsequent live pilot.',
                 'Hypothesis causality remains unverified. No frozen benchmark campaign.']}
(ROOT/'runs/prefreeze-review.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
