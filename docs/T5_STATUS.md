# T5 IF-001 B2 repair: accepted for review

October 3, 2026. The original brief is unchanged. The core local IF-001 investigation-to-repair path is exercised with real Nebius Nemotron inference. This is a development pilot, not a frozen benchmark or a universal correctness claim.

## Measured outcome

Run `b2-20261003T052430Z-fc5821` generated one patch, requested one developer test and one protected feedback evaluation, then froze its candidate for an independent final evaluation. Both protected evaluations passed all six scenarios, with zero failures, errors or skips. The final candidate revision is `b0af7dd6a4ed1612ef0e1b61410887d576828bf3e20b0d5611c64598d87618bf`. All 57 evidence events and referenced artifact hashes verified.

The model changed the Order retry transition to generate a payment key only when one is absent, preserving the key across retries. This fixes the tested duplicate-charge mechanism while preserving recovery, compensation and concurrent-workload behavior under the declared development schedules. The candidate stays in its run folder for review; the faulty fixture remains available for reproducing the incident.

Before editing, the model generated competing hypotheses and predictions. The controller recorded the experiment specification, then ran four fresh-state Payment experiments. Same-key sequential, restart and concurrent conditions each committed one charge; different keys committed two. The model interpreted these measurements before editing. Protected feedback exposed only the verdict, completion and failing property IDs, never private schedules or evaluator source.

## Attempts and cost

| Run | Outcome | Calls | Estimated USD |
| --- | --- | ---: | ---: |
| `b2-20261003T052129Z-f0fb37` | Schema failure, then output exhausted; no edits | 2 | 0.003666 |
| `b2-20261003T052334Z-6abc72` | Schema correction failed; no edits | 2 | 0.001722 |
| `b2-20261003T052430Z-fc5821` | Accepted for review | 7 | 0.006421 |

Including the preserved T4 B0 failure ($0.003908), total estimated inference spend is $0.015717. No unresolved reservations remain. The cumulative $0.20 limit remains enforced. These are usage-based estimates, not a refreshed provider balance or invoice. Sandbox beta execution is free per the user's Nebius support confirmation; this stage used local Docker execution.

## Judge review and remaining integration

The behavioral repair passes this stage's declared development checks. Investigation quality is weaker: predictions such as `multi|single` do not clearly map outcomes to named hypotheses, and some source references are imprecise. The model overstated causal certainty and described concurrency coverage inaccurately. The actual probe did include direct concurrent Payment requests; the protected suite also includes declared concurrency scenarios. Neither establishes universal race freedom.

The retained run's model-written workload label says `single_order_workflow`, although the trusted probe actually sent direct Payment requests. Future ExperimentSpecs now take workload and controlled-variable descriptions from the runner definition. Original run artifacts remain unchanged; this note records the discrepancy.

Before benchmark freeze: improve semantic hypothesis/prediction validation, complete record typing and source-reference checks, unify the controller with the proven remote Sandbox lifecycle, and test the generated candidate remotely. T3 established remote fixture compatibility; it did not remotely validate this new candidate. Broader B0/B1/B2 comparisons, IF-002, final holdout and UI remain on the original plan. One successful B2 pilot versus one failed B0 pilot is not evidence of general superiority.

## Verification and next stage

Fourteen T4/T5 controller tests pass, including budget retention, evidence tampering, private-feedback filtering and refusal to edit before experiment interpretation. The actual Docker probe passed without inference. All five live B2 execution containers and volumes reported confirmed cleanup. Existing harmful controls and the rejected T4 B0 run remain labeled negative examples.

Next: T6 compensation/restart incident and benchmark development, while retaining the investigation-quality and remote-controller integration work above as explicit gates before T8. Do not publish benchmark claims or silently narrow the original scope.

Run another explicitly budgeted development pilot with `python scripts/run-t4.py --live --variant B2`; it creates fresh evidence and shares the existing budget ledger. Do not run it merely to reproduce these already-recorded results.
