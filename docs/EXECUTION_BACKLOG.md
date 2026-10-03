# IncidentForge: execution backlog

Current checkpoint (October 3, 2026): T0–T7 delivered as development stages. Pre-T8 work adds remote candidate/controller execution, stricter evidence checks, editable developer assertions and recovery calibration. See PRE_T8_STATUS.md for verified results and remaining freeze work. The original scope is retained. No final comparison has run; no paid overage is authorized.

Historical T2 checkpoint: 32 tests, 17 case reports, all five required harmful fixes rejected; separate T0/T1 regression: 34 tests, zero skips. T3 subsequently verified remote compatibility. Solo, 6–7 hours/day: roughly 162–189 hours across October 3–29, with October 30 reserved as contingency. Estimates are ranges, not guarantees.

## Ordered work and gates

| Task | Dependencies | Hours | Deliverable and acceptance |
|---|---|---:|---|
| T0 environment + narrow observer feasibility | Planning review | 8–12 | Linux runtime inventory; protected broker prototype, atomic audit, UID/store denial and duplicate-permitted controls; no model/platform call |
| T1 three-service fixture | T0 observer gate | 16–22 | Real HTTP, separate stores, clean workflow, response-loss IF-001, restart/reset; unpatched duplicate demonstrated |
| T2 contract/verifier/controls | T1 | 16–22 | Known-good passes; original five harmful fixes rejected for declared reasons; observer/boundary tests pass; public contract export excludes secrets |
| T3 ConTree integration | Listed access + coverage, T0; overlaps T1/T2 | 6–10 | Real bounded execution, HTTP/process/restart/export/boundary compatibility and cancellation; actual provider artifacts |
| T4 controller/evidence/model + B0 | T2; funded inference | 14–20 | Bounded real Nemotron editing/testing loop; valid accounting; useful unresolved report; first recorded B0 |
| T5 investigation + B2 repair | T4 | 16–22 | Distinguishing experiment; clean candidate validation; rejected harmful fixture labeled; full IF-001 path |
| T6 IF-002 + benchmark development | T5 | 10–14 | Compensation restart incident, reference/negative controls, distinct mechanism; pilot variants |
| T7 complete product interface | Stable records from T4; finish with T6 | 12–16 | Select incident, launch/cancel/status, hypotheses, experiments, diff, validation and evidence export |
| T8 calibration/freeze/comparison | T3–T7, funded campaign | 12–18 | Frozen B0/B1/B2 campaign, two families, denominators/costs/uncertainty, reproducible artifacts |
| T9 judge package/video/submission | T8 | 8–12 | Clean setup rehearsal, licensed repo, access plan, <3 minute video, complete checklist |

Total engineering estimate: 118–168 hours. Reserve at least 20–28 hours for integration failures and rework, yielding 138–196 hours. High estimates exhaust capacity; identify overruns early, do not silently reduce original scope. B3 has no allocation in the critical path because it is explicitly optional. No commitment to 72 runs.

## Calendar targets (IST)

October 2–4: T0 and begin T1. October 5–9: T1/T2, funded Sandbox compatibility as early as possible. October 10–14: T4 and early T7. October 15–19: T5/T6. October 20–23: complete T6/T7, pilot and freeze preparation. October 24–26: T8. October 27–29: T9 and access rehearsal. October 30: final contingency before 22:30 IST, not planned core engineering.

These are dependencies and targets, not authorization to execute. Listing access is already working; do not wait until October 20 to discover runtime incompatibility. Escalate any remote capability failure immediately while continuing independent local work. Reforecast after T0 and the first remote fixture. A missed date prompts an explicit status/decision, not automatic fallback to local-only submission.

## First implementation slice after execution starts

T0: local persistence/observation feasibility, restricted to prototype and tests. Inventory Python/container/WSL and instructions; do not reinstall working tools indiscriminately. Define broker transaction/session semantics and two separate test clients under different UIDs. Demonstrate:

1. A committed effect appears exactly once in protected audit; rollback appears zero times.
2. Two intentional inserts remain two effects; the broker has not repaired deduplication.
3. Response count does not decide effect count; a crash after commit preserves evidence.
4. Service cannot read audit/schedule/other store or change harness/trigger policy.
5. Concurrent transactions and session death clean up without leaked locks or partial audit.
6. Export uses a coherent backup including WAL commits; clean–faulted–clean reset is identical.

Save commands, exit codes, assertions, runtime versions and artifacts. Failures stop expansion to the full agent. If the broker cannot support ordinary app atomicity without excessive complexity, revise that narrow persistence interface before building services, retaining all business requirements. No GPU, cloud provisioning, model calls or public publishing in T0.

## External gates

Model ID/license/price and actual credit validity must be known before inference. Beta coverage and operation caps must be known before Sandbox workloads. Protected-boundary compatibility must pass on the actual execution backend before protected claims. December judge access/funding needs an explicit solution by submission, not an assumption that trial credits persist. Existing support request need not be duplicated.
