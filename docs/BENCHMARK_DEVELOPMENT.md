# Two-family benchmark development specification

T6 development version, October 3, 2026. This is not a holdout freeze.

| Family | Independent defect | Positive control | Negative controls | Main distinguishing experiment |
| --- | --- | --- | --- | --- |
| IF-001 | New payment identity on each retry after committed response loss | Known-good stable identity | Fresh key, no recovery, false success, cancel all, memory dedup, non-atomic claim | Same key sequentially, across restart, concurrently; different keys |
| IF-002 | Durable COMPENSATING intent scheduled only by a volatile process-local set | Known-good durable recovery loop | Missing restart recovery, terminal without release, double stock credit | Decline without/with restart; direct release replay without/with Inventory restart |

All harmful mutations are independently applied to the reference. IF-002 has no IF-001 key mutation. The IF-002 defect is required to pass decline without a crash and fail after a witnessed durable compensation barrier. Missing the barrier is a test error, never a successful reproduction.

The IF-002 crash schedule stops Payment until Order reaches CHARGING, then stops Inventory and resumes Payment. It observes committed COMPENSATING state plus a HELD reservation, checks the protected Order audit, kills Order, and restarts Inventory before restarting Order. Inventory retains its store but loses queued requests from the killed process. This second restart is declared: the current fixture does not claim a strictly Order-only crash experiment. Without discarding those queued requests, a pre-crash release might complete and conceal the recovery omission.

The pre-T8 revision measures compensation recovery from before Order process launch and includes readiness. Earlier T6 pilots measured residual time after readiness and cannot support total recovery latency claims. Three reference repetitions per family on Docker and Sandbox now support proposed development bounds of three seconds for IF-001 and two seconds for IF-002; these are not final tail-latency estimates or a holdout freeze. See PRE_T8_STATUS.md.

## Variant protocol

B0/B1/B2 share the same public contract, incident source, initial evidence, read/search/edit/test tools and one available distinguishing experiment. B0 may voluntarily use that experiment or interpret evidence. B1 must produce competing hypotheses and precommitted predictions, execute the experiment and interpret it before repair. B2 adds one property-only protected feedback request before finish. All variants receive final protected evaluation after freezing a candidate; no final result is fed back into its repair loop.

Current common bounds: ten model calls including investigation, three edits (including authored developer assertions), two requested developer tests, seven total executions, 900-second controller deadline and 100-second guest workload watchdog. Calls share the persisted $0.20 project allocation; pending/unknown usage prevents another dispatch. No paid overage is authorized. Final evaluation is counted in execution resources. Inference now has a killable 60-second host wall limit. Before dispatch, conservative remaining-time checks reserve room for the execution and its cleanup. Sandbox operations have a 120-second server timeout; a host transport failure retains the execution reservation until terminal status is reconciled.

T6 predeclares one IF-002 development attempt per B0/B1/B2, serial order B0, B1, B2. This order is for integration debugging and is not a randomized or rotated efficacy experiment. The launch manifest pins source hashes and records all launched outcomes. Prior T4/T5 IF-001 runs used evolving prompts/tool visibility and are historical development evidence; they must not be pooled as matched trials with these runs.

## Freeze gates for T8

1. Complete remote controller integration and exercise generated candidates on the Sandbox backend; remote T3 reference compatibility alone is insufficient.
2. Complete field typing, meaningful named-hypothesis prediction checks, source-reference validation, editable developer-test capability and prompt/bundle leakage checks.
3. Calibrate recovery bounds on development workloads for both families; account for startup and use a common recovery-start barrier. Freeze budgets, model, prompts, source, evaluator and schedule hashes.
4. Author distinct final schedules without using them for prompt tuning. Predeclare equal independent runs per variant/family, preferably at least two per cell when free-credit and time capacity permits. Rotate variant order. Retain both families.
5. Record all launched attempts in the primary denominator, including errors and unknowns. Report raw case-level numerator/denominator, attempts, model usage, execution cost/time, rejected controls and limitations. No significance claim from one run per cell.

No final campaign is launched or implied by this development specification. Neutral and unsuccessful pilots remain evidence; changes after observing results create a new development revision.
