# T8 results: completed campaign, unreliable infrastructure

October 3, 2026. **12/12 planned attempts recorded; 2 accepted final repairs.**
4 frozen candidates reached independently verified final evaluation. Unfrozen attempts count against repair yield, but are not measured final-schedule failures.

**No variant ranking is supported.** 3 attempts encountered infrastructure failure; the predeclared threshold is more than two. Two attempts per variant/family would in any event support only descriptive counts.

## All attempts

| Slot | Family | Variant | Final outcome | Settled estimate | Unknown reservation |
| --- | --- | --- | --- | --- | --- |
| 1 | IF-001 | B0 | unresolved | $0.004977 | $0.000000 |
| 2 | IF-001 | B1 | unresolved | $0.004344 | $0.000000 |
| 3 | IF-001 | B2 | unresolved | $0.003943 | $0.000000 |
| 4 | IF-002 | B1 | unresolved | $0.003351 | $0.017695 |
| 5 | IF-002 | B2 | accept_for_review | $0.004337 | $0.000000 |
| 6 | IF-002 | B0 | unresolved | $0.000000 | $0.017695 |
| 7 | IF-001 | B1 | unresolved | $0.001371 | $0.017695 |
| 8 | IF-001 | B2 | unresolved | $0.005272 | $0.000000 |
| 9 | IF-001 | B0 | accept_for_review | $0.002376 | $0.000000 |
| 10 | IF-002 | B2 | reject_behavior | $0.007384 | $0.000000 |
| 11 | IF-002 | B0 | reject_behavior | $0.004557 | $0.000000 |
| 12 | IF-002 | B1 | unresolved | $0.008987 | $0.000000 |

## Descriptive repair yield

Accepted final repairs / launched independent attempts:

| Family | B0 | B1 | B2 |
| --- | --- | --- | --- |
| IF-001 | 1/2 | 0/2 | 0/2 |
| IF-002 | 0/2 | 0/2 | 1/2 |

## Final-case evidence

- Slot 5 (IF-002 / B2): canonical_mixed_payload: accept_for_review; contended_inventory: accept_for_review; decline_then_new_order: accept_for_review; two_declines_with_restart: accept_for_review.
- Slot 9 (IF-001 / B0): canonical_mixed_payload: accept_for_review; contended_inventory: accept_for_review; dual_restart_response_loss: accept_for_review; cancel_after_dual_restart: accept_for_review.
- Slot 10 (IF-002 / B2): canonical_mixed_payload: accept_for_review; contended_inventory: accept_for_review; decline_then_new_order: reject_behavior; two_declines_with_restart: reject_behavior.
- Slot 11 (IF-002 / B0): canonical_mixed_payload: accept_for_review; contended_inventory: accept_for_review; decline_then_new_order: reject_behavior; two_declines_with_restart: reject_behavior.

Each final export was independently recomputed by the restricted Docker reader. Candidate hashes were checked before and after final evaluation. Final results never fed back to the controller. Finite schedules do not prove universal correctness.

## Failures and follow-up

- Slot 1: RuntimeError: format/action correction limit. Rejections: {"assertion fields": 3}.
- Slot 2: RuntimeError: format/action correction limit. Rejections: {"conclusion must equal required_factual_conclusion exactly; causal claims belong in the unverified hypothesis commentary": 2, "string fields required": 1}.
- Slot 3: RuntimeError: format/action correction limit. Rejections: {"string fields required": 1, "conclusion must equal required_factual_conclusion exactly; causal claims belong in the unverified hypothesis commentary": 2}.
- Slot 4: TimeoutError: Inference wall-time cap; usage unknown, no retry.
- Slot 6: TimeoutError: Inference wall-time cap; usage unknown, no retry.
- Slot 7: TimeoutError: Inference wall-time cap; usage unknown, no retry.
- Slot 8: RuntimeError: format/action correction limit. Rejections: {"conclusion must equal required_factual_conclusion exactly; causal claims belong in the unverified hypothesis commentary": 3}.
- Slot 10: Protected development validation did not accept the candidate; inspect case evidence. Rejections: {"replacement must match exactly once; no edit applied": 2}.
- Slot 11: Protected development validation did not accept the candidate; inspect case evidence. Rejections: {"unsupported action or fields": 1}.
- Slot 12: RuntimeError: format/action correction limit. Rejections: {"Expecting value: line 1 column 1 (char 0)": 1, "unsupported action or fields": 1, "interpret experiment before repair": 1}.

Slot 10 is a concrete claim/evidence mismatch: the model said it added a release, but the controller recorded zero edits. The frozen candidate failed the two IF-002 restart schedules on eligible-order progress (P3) and compensation (P4). Model prose is not accepted as evidence of a code change.

The failures expose two development priorities: model adherence to the exact action/assertion and factual-conclusion schemas, and inference completion within the fixed timeout. Investigate these in a new development revision. Do not tune this frozen campaign or replace failed attempts. A fresh comparison needs a new declared freeze.

## Accounting and interruption

Campaign settled token-price estimate: **$0.050899**. Project settled estimate: **$0.102488**. Project exposure including all unknown reservations: **$0.155573 / $0.20**.

3 calls retain unknown actual usage. Their full reservations remain charged against the cap; no fabricated usage or refund is recorded. These are token-price estimates and conservative allocations, not a provider invoice. Sandbox resource cost units are unspecified and are not USD inference spend.

After slot 4, the campaign paused. The user authorized the [accounting amendment](T8_CONTINUATION.md). Slots 1–4, the original freeze, model, prompts, source, evaluator and schedule were preserved. Only unlaunched slots continued. No failed slot was retried. This interruption and amendment are part of the result.

## Evaluator readiness and limitations

Both authored references passed four final schedules locally and on Nebius Sandbox before freeze. Five harmful controls were rejected locally. These controls establish evaluator readiness, not model repair success.

The final schedules use the same two defect implementations as development. The inherited per-case `conditions` label and controller report pilot disclaimer are stale labels from shared code; the separately recorded `final_holdout` mode, schedule version, source freeze and final evidence establish which workloads ran. Original raw records were preserved rather than rewritten.

The original freeze SHA256 remains `68ee6f0d191abc0789b8224001e7d1b25ee28d2d9fa4e37eaca0004c140f528f`. The original Git commit maps to identical source at `4a05d43eab46ba24dc405fbcf7e7a84275fca15c` after author-email correction.

Curated [machine-readable results](../benchmarks/t8/summary.json) include all attempt denominators, candidate revisions, case outcomes, reported tokens, elapsed times, action rejections and sanitized provider resource receipts. Full event chains and raw exports remain local. The project repository remains private.

T8 execution and reporting are complete: all twelve slots are recorded. The observed infrastructure threshold prevents a reliable variant comparison. T9 packaging can proceed with these limitations disclosed.

## Derived metrics

[derived_metrics.json](../benchmarks/t8/derived_metrics.json) restates the brief's
requested measurements from retained fields only. It is generated by
`scripts/derive-t8-metrics.py`, records the source hash, and never modifies the
frozen summary. All twelve attempts and their outcomes are preserved.

| Requested metric | Result | Basis |
|---|---|---|
| Reproduction rate | **unavailable** | No attempt records a reproduction outcome. Execution completing is not symptom reproduction, and the later incident-specific assessment is not applied retroactively |
| Time to reproduction | **unavailable** | No reproduction timestamp or duration was retained |
| Resolution time | n=4, min 97.6 s, median 158.0 s, max 229.2 s | `attempts[].elapsed_seconds`, over attempts reaching an independent verdict. The 8 unresolved attempts are excluded: their runtime is not a resolution time |
| Runtime, all attempts | n=12, min 67.1 s, median 108.0 s, max 229.2 s | Same field, reported as runtime rather than resolution |
| Clean-workload regressions | 0 of 8 clean case instances | `case_outcomes[].properties` for `canonical_mixed_payload` and `contended_inventory`, the cases `evaluation/holdout.py` does not fault-inject |
| Lost orders | **unavailable** | No order-level count retained. P3 is a property verdict, not a count; P3 failed in attempts 10 and 11 |
| Duplicate effects | **unavailable** | No duplicate-effect count retained. P1 and P6 are verdicts, not counts, and P1 never failed |

Property statuses are pass, fail or not_applicable; `not_applicable` is not a
failure. Metrics over evaluated attempts describe 4 of 12. No variant ranking is
supported or implied.
