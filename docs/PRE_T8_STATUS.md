# Pre-T8 integration review

October 3, 2026. The original project scope is unchanged. This work is development integration, not a frozen comparison or holdout result.

## Implemented and exercised

- The controller now supports `--backend contree` through the installed ConTree SDK environment. Candidate execution has no guest network access. Source uploads use explicit allowlists; credentials stay on the host. A durable project-level reservation prevents redispatch after unknown execution state. Server timeout is 120 seconds, with a bounded SDK helper. Actual cancellation returned CANCELLED and released the reservation.
- Generated IF-001 and IF-002 repairs were exercised remotely, passing 6 and 8 protected development cases respectively. A separate, network-disabled Docker reader recomputed all 14 exported verdicts. Protected remote calls now include this reader automatically. The remote backend therefore still requires local Docker for independent evidence reading.
- The known-bad lost-compensation control was rejected remotely. Six exported cases were independently checked; two additional tests failed before case export. Missing case exports can accompany rejection, but never qualify as complete acceptance.
- Records enforce top-level field types. Investigation requires exactly two hypotheses, named H1/H2 predictions per condition, at least one different prediction, actual source identifiers and source references. Numbered line IDs resolve to exact source text; nonexistent/empty lines are rejected. Literal excerpts must be verbatim. Failed quotation feedback identifies the bad excerpt and nearby actual source lines.
- Interpretation must reproduce the measured condition facts exactly, including compensation state. Its conclusion must also equal a controller-generated factual summary. This final check was added after the live pilot below copied the facts correctly but reversed them in its prose. The retained bad interpretation is rejected offline by the new gate. Other hypothesis commentary remains explicitly unverified; different prediction strings do not prove scientifically useful competing hypotheses.
- Candidates can author up to 12 bounded declarative assertions against public developer observations. They are included in the candidate revision, count toward the edit budget, and cannot alter protected tests. An actual assertion failed on COMPENSATING in the faulty program and passed on CANCELLED_DECLINED in the reference.
- Inference runs in a killable host subprocess with a 60-second wall limit. Unknown usage retains its budget reservation. Conservative remaining-time checks reserve room for execution, verification and cleanup before another controller operation starts.
- New live runs pin source hashes and identify the prefreeze development protocol. Historical runs and failed attempts remain intact.

## Evidence

| Check | Evidence under `runs/` |
| --- | --- |
| Generated IF-001 remote repair, six cases | `prefreeze-e90836be/execution-1` |
| Generated IF-002 remote repair, eight cases; local developer assertions | `prefreeze-e60ebc10/summary.json` |
| Remote recovery calibration and rejected negative control | `remote-lifecycle-6a44eaf9` |
| Real SDK cancellation and recovered checks | `remote-lifecycle-8fa4228f/summary.json` |
| Local recovery calibration | `calibration-20261003-100100.json` |
| Linux compensation and fixture regressions | `t6-linux-20261003-100920` |

The first SDK response reader assumed the CLI response shape. Its successful remote operation was recovered by ID after fixing the parser; it was not rerun. The negative-control reader initially required every failing test to reach evidence export. That check was corrected to permit incomplete rejection evidence while keeping acceptance strict. Both original error receipts remain available.

## Recovery calibration

Each family has three reference repetitions on each backend. The clock begins before the recovering service is launched and includes readiness time. IF-001 includes Payment restart before releasing the retry barrier. IF-002 includes Order startup after discarding old Inventory requests; this is still the declared two-service crash schedule.

| Family | Local maximum seconds | Sandbox maximum seconds | Proposed shared bound |
| --- | --- | --- | --- |
| IF-001 | 0.781 | 0.249 | 3 seconds |
| IF-002 | 0.502 | 0.191 | 2 seconds |

The proposal is the ceiling of three times the observed maximum, with a two-second minimum. Six observations per family do not estimate tail latency or establish a guarantee. Final evaluator bounds have not been changed or frozen.

## Development pilot review

`b2-if-002-20261003T100824Z-46dfa7`: unresolved before editing. Two inference calls, estimated $0.002012, no pending usage. Source-reference validation caught a model quote that combined separate source lines. The follow-up revision improved correction feedback without relaxing verbatim validation.

`b2-if-002-20261003T101112Z-580ac9`: also unresolved on a fabricated source quotation, two calls and $0.001832. Neither failed attempt edited code. Both remain in the development record.

After introducing numbered source references, `b2-if-002-20261003T101505Z-4c2892` completed the full remote B2 controller path: reproduction, investigation, experiment, interpretation, one repair, developer test, property-only feedback, candidate freeze and fresh protected validation. Eight cases passed both during feedback and after freeze, and both exports were independently recomputed. Seven model calls, five remote executions, estimated $0.005955, 51 verified events. The patch removes the process-local pending-compensation guard; it is retained for review, not promoted into the reference fixture.

Judge finding: **repair passes; causal explanation fails**. The model claimed restart was required for compensation even though no-restart completed and restart remained COMPENSATING. Correct structured facts alone did not catch that contradictory prose. The final revision requires the conclusion to equal a derived factual summary, and a regression test plus replay of this retained live output confirms rejection. This last protocol revision has not had another live pilot. Hypothesis quality and remaining free-text causal commentary must still be scored separately from repair correctness.

26 controller/UI/grounding tests pass. The Linux T6 regression has 16 tests, zero failures/errors/skips. Total estimated inference spend is $0.039121 across 43 historical calls, with zero pending calls, under the existing $0.20 cap. No pilot is a final efficacy comparison.

## Remaining T8 work

### Final-gate live rehearsal (October 3)

Run `b2-if-002-20261003T102651Z-c2cb96` passed the factual interpretation gate on real Sandbox observations. Its conclusion correctly states that no-restart completed compensation while restart remained COMPENSATING. Audit verified 39 events and 59 unchanged source pins. Free-text causal commentary still overstates what the experiment supports and is not validated by this gate.

The overall run is **unresolved**, not accepted: three exact-text replacements failed, exhausting the correction limit. Zero edits were applied, no candidate was frozen, and no protected validation ran. This demonstrates the factual gate live but does not establish end-to-end readiness of the final revision. Preserve the failed attempt; improve edit grounding and rehearse before freezing.

Five inference calls cost an estimated $0.007247. Project cumulative estimated spend is $0.046368, with zero pending calls and no unresolved remote reservation. The audit is saved at `runs/b2-if-002-20261003T102651Z-c2cb96/rehearsal-review.json`. The original scope is unchanged.

### Successful rehearsal after edit recovery improvement

Run `b2-if-002-20261003T103551Z-6109b9` completed the revised remote B2 loop. One applied repair passed 8/8 protected development cases during feedback and 8/8 after candidate freeze. Both archives were independently recomputed. The factual interpretation gate passed; 45 events and 59 unchanged source pins were audited. Six model calls, four remote executions, estimated $0.005221. No separate developer-test action was requested in this run; protected feedback and final validation are the measured checks.

Failed exact edits now return a bounded verbatim source excerpt and match count without applying a fuzzy replacement. The shared prompt recommends short edits, tracing early returns, and distinguishing durable from process-local prerequisites. The correction budget is unchanged. The new regression test confirms mismatches leave source intact and expose real source context. All 27 controller/UI/grounding tests pass. This successful run applied its repair without exercising mismatch recovery live; that recovery path is verified by regression testing, not claimed as a live recovery success.

Judge assessment: factual reporting and the repair pass the development gate. Free-text causal reasoning remains weak and is explicitly unverified. One successful run does not establish reliability or superiority over B0/B1. The failed previous rehearsal remains in the record. Current total estimated inference spend is $0.051589 of the $0.20 allocation, with zero pending calls and no unresolved remote reservation. See `runs/b2-if-002-20261003T103551Z-6109b9/rehearsal-review.json`.

The revised loop has now passed a complete live rehearsal. Next, freeze the selected development revision, recovery bounds, budgets, prompts, model, evaluator and source hashes after authoring and validating distinct final schedules without prompt tuning against them. Predeclare equal attempts per variant and family, rotate order, retain every error/unknown in the denominator, and report raw case counts and costs. Continue to label causal prose as a model claim. The UI currently launches Docker; Sandbox is available through the CLI. Public judge access and trial expiry remain T9 concerns.

No final benchmark campaign has been launched. Original brief SHA256 remains `4a2d5f78d37fdfd9bcd450b32374533f146e66c28eecdaf55488d6dfe9bb29af`.
