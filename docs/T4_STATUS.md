# T4: first live B0 pilot recorded — October 3, 2026

The user explicitly approved the inference payload. Real Nemotron calls completed.
The controller/evidence/accounting path and first B0 development run are now exercised.
The model repair FAILED independent validation; it is not a successful repair.

Run: `b0-20261003T051311Z-23c3db`. Six model calls, one applied edit, one requested
developer test, then six protected scenarios on the frozen candidate. Five passed;
the response-loss/Payment-restart scenario failed P1/P2 with three committed charges
for one order. No test errors/skips. Candidate remains in its run directory and
was not promoted into the application fixture.

Estimated inference cost: $0.003908 from 36,195 prompt and 7,221 completion tokens,
using verified catalog prices and per-call rounding. This is a calculated estimate,
not an account balance or invoice. Zero unresolved reservations. All 46 evidence
events and artifact hashes verified; all local pilot containers/volumes cleaned up.
The $0.20 project pilot cap remains enforced across future calls.

The model changed CHARGED to CONFIRMED after a successful payment response but
left fresh payment identities on retries. Its assertion that duplication was fixed
was contradicted by the protected audit. The original run report retains this claim
in its reason field; review.json labels it unverified. Future controller reports
now separate model_claim_unverified from the independent verdict explanation.
All 11 controller tests passed after that reporting-only correction; no live rerun.

Next: T5 investigation/B2 repair. Preserve this B0 result unchanged. Develop
competing hypotheses and a distinguishing experiment before the next repair.
One failed Nano pilot does not establish B2 superiority or model inadequacy.
Remote controller lifecycle unification, richer developer test authoring, full
record field typing, final evaluation freeze and UI remain further integration
work; the current action set is the bounded T4 pilot surface.

## Earlier preparation record (superseded live-status statements)

# T4 checkpoint â€” October 3, 2026

PARTIAL: controller foundations and local integration passed; live B0 has not run.

Implemented versioned records, hash-chained events/content-addressed artifacts,
allowlisted source read/search/replace actions, source indexing, persistent atomic
project/run budget reservations, a no-retry Nebius adapter, bounded B0 loop and
isolated Docker candidate execution with terminal cleanup. Unreconciled model
calls retain their conservative reservation and block further dispatch. B0 sees
developer HTTP observations, never private evaluator feedback during repair.
Candidate freezes before protected development validation.

Eleven controller safety/accounting tests pass. An actual local Docker integration
run reproduced IF-001 and validated the manually authored reference through six
protected scenarios. This is explicitly not an AI-generated repair. Evidence:
`runs/t4-local-1d1680ed/`; hash-chain verification passed. A Windows CRLF mismatch
found by the edit test was fixed by normalizing source reads.

The user screenshot confirms $1 trial balance and 27 days remaining. Pilot total
cap is $0.20 across the persisted project budget, up to ten calls, three edits,
two requested developer runs plus reproduction/final validation. No model calls
or inference spending have occurred. Remaining credit is not remeasured here.

Model: nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B. Public Nebius catalog checked October
3 lists $0.06/M input and $0.24/M output. NVIDIA's official quick reference names
the NVIDIA Nemotron Open Model License. Per-call reservation uses the complete
262,144-token context at input rate plus 8,192 output tokens; usage is estimated
from provider counters, not asserted as billed dollars.

Sources:
- https://tokenfactory.nebius.com/model-catalog.md
- https://github.com/NVIDIA-NeMo/Nemotron/blob/main/skills/nemotron-nano3/context/quick-reference.md

Automatic approval review rejected the live invocation because model inference
sends project source and incident observations to a different destination from
Sandbox. The user previously approved Sandbox uploads; explicit inference-payload
approval is pending. No live request was sent. A reviewable model payload folder
and MANIFEST.json are saved in this chat's outputs/IncidentForge-T4-model-payload.
It includes public app source, contract, synthetic incident, system prompt and
declares dynamic developer observations. It excludes credentials, private
controls/evaluator, planning notes, Git history and personal/customer data.

After explicit approval, run scripts/run-t4.py --live. Do not call T4 complete
until a real Nemotron attempt, accounting and final outcome are recorded. A
failed/unresolved pilot remains evidence and must not be relabeled as success.
Full B1/B2 investigation, remote controller backend lifecycle unification,
final holdouts and product UI remain later integration work.
