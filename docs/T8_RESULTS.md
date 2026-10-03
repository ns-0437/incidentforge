# T8 results: incomplete campaign

October 3, 2026. Four of twelve planned independent runs launched. None reached
candidate freeze, so **no final agent-patch evaluation or variant ranking exists**.
Eight slots were never launched and are not counted as failed attempts.

| Slot | Family | Variant | Outcome | Settled estimated USD |
| --- | --- | --- | --- | --- |
| 1 | IF-001 | B0 | Correction limit; one edit, no frozen candidate | 0.004977 |
| 2 | IF-001 | B1 | Correction limit; no edits | 0.004344 |
| 3 | IF-001 | B2 | Correction limit; no edits | 0.003943 |
| 4 | IF-002 | B1 | Inference timeout; usage unknown | 0.003351 plus unresolved usage |

The fourth attempt hit the 60-second inference wall limit. Its conservative
$0.017695 reservation remains unresolved. The budget guard prevented slot 5.
Do not reset the ledger, delete that reservation, or call this a completed study.
Reconcile usage against provider evidence before another inference dispatch.

Project settled estimates total **$0.068204**; settled plus reserved exposure is
**$0.085899**, within the $0.20 allocation. The campaign's settled estimate is
$0.016615. These are token-price estimates, not a provider invoice.

## Evaluator readiness is a separate result

Both references passed four new schedules locally and on Nebius Sandbox. Remote
archives were independently verified. All five tested harmful controls were
rejected locally. The always-success control failed two cases before export;
those errors count against it and cannot support acceptance.

The final schedules remain four per family over the same two defect implementations.
No final outcome was fed to the model or used to tune its prompt. Raw evidence is
retained locally; curated records and the original freeze are in
[`benchmarks/t8`](../benchmarks/t8/summary.json).

The Git author email was corrected before the first push. The original freeze
commit maps to an identical source tree at
`4a05d43eab46ba24dc405fbcf7e7a84275fca15c`; the original manifest is preserved
unchanged, with the mapping recorded in the curated summary.

## What is next

Reconcile the single unknown model request. Preserve all four failed attempts.
Inspect the correction-limit failures in a separately labeled development revision;
do not modify this frozen campaign and silently continue it as the same protocol.
Any revised comparison must predeclare a new campaign and retain these results.
T9 packaging can continue independently, but the benchmark remains incomplete.
