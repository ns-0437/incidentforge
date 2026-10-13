# Project status — October 4, 2026

**Estimated overall completion: 70%; remaining: 30%.** This is a judgment-based
planning estimate, not a measured acceptance rate or a promise about time remaining.
The original brief remains unchanged and authoritative. Counting completed task
labels alone would overstate readiness: quality and external release gates matter.

| Workstream | Planning weight | Earned estimate | Evidence and remaining work |
|---|---:|---:|---|
| Core engine and platform integration | 40 | 35 | Real HTTP services, protected persistence/evaluator, Nemotron, Sandbox, controller and evidence exist. Intake/indexing remain tailored to the supported fixtures. |
| Investigation, repair and evaluation | 25 | 18 | Frozen T8 complete with all failures retained; some accepted repairs. Reliable IF-002 repair and stronger evidence of value remain unresolved. |
| Product interface and reproducibility | 15 | 12 | Local console, exports, public replay and clean-checkout rehearsal exist. Sandbox UI selection now implemented; full judge workflow rehearsal still needed. |
| Judge access and submission | 20 | 5 | MIT, guide, draft, recording script prepared. Provider availability owner-confirmed through December 15; access delivery, final recording, public release, signed-out checks and actual submission remain. |
| Total | 100 | 70 | Approximately 30 points of work remain. |

## Position in the implementation plan

T0–T7 implementation milestones are delivered. T8's twelve-attempt frozen campaign
and report are complete: two accepted final repairs, two rejected frozen candidates
and eight unresolved attempts. Three inference timeouts invalidate variant ranking.
Post-T8 changes are development work, not replacement benchmark results.
T9 is in progress, with release drafts and setup rehearsal complete but external
access and publication/submission gates open. B3 parallel branches were optional
in the original brief and are not counted as required missing work.

The latest improvements add bounded source traces, explicit budget accounting,
timeout reconciliation, early verifier checks and UI backend selection. They do
not establish reliable autonomous compensation repair. A fresh independent
comparison would need newly frozen evaluation cases and an adequate declared
budget; repeatedly tuning against old schedules cannot support that claim.

## Next priorities

1. Preserve the verified local launch, immediate cancellation, review export and
   clean-checkout checks; repeat them only for material changes or final release.
2. Address IF-002 diagnosis-to-patch consistency with a specific testable change;
   do not burn remaining credits on identical retries or claim improved reliability.
3. Rehearse delivery of free working judge access through December 15. The owner
   confirmed provider availability on October 4; the actual judge access path remains open.
4. Record the under-three-minute demonstration using VIDEO_SCRIPT.md; publish the
   reviewed video, retain the completed October 11 public release, check all
   links signed out and submit the completed entry.

## Budget and access

Cumulative accounted exposure: **$0.337380 / $0.40**. Remaining allocation:
**$0.062620**. Includes retained development attempts through v25; no inference remains pending.
The other trial credits are unallocated. The GitHub Pages site is a recorded replay,
not a hosted inference service. The main source is public with owner approval
since October 11, and the recorded frontend is live at https://ns-0437.github.io/incidentforge/

Validation for the backend selector: **115 portable tests passed** and JavaScript
syntax validation passed. Tests verify HTTP allowlisting, recorded selection,
child-process arguments and failure before launch when Docker is unavailable.
October 4 browser review confirmed Sandbox selection, recorded patch and validation
views, and review download. The archive CRC and manifest hashes passed. Live UI
launch and immediate cancellation were also rehearsed; fresh-user judge access remains pending.

Owner clarification, October 4: confirmation covers continued access to the owner
account only. Separate judge credentials/access have **not** been confirmed.

Current detailed acceptance matrix: [COMPLETION_GATES.md](COMPLETION_GATES.md).
IF-001 completed the required authored-test gate in v22, with weak test coverage
explicitly disclosed. IF-002 has mixed retained outcomes; v23 exposed an edit-compilation
gap that is now fixed. No new reliability percentage is claimed.

Public regression observations passed 19 Linux checks, including faulty/reference
assertion discrimination. v24 still stopped before repair after repeated edit
mismatches. Mandatory source re-reading after rejected edits is now enforced offline.

IF-002 v25 completed the latest authored-test gate: a restart assertion failed on
baseline and passed after repair, with eight accepted cases in each of two protected
executions. This closes the single successful end-to-end demonstration gap; reliable
repeat performance remains unproven. The original T8 comparison is unchanged.

## October 5 engineering completion pass

Four scope items from the original brief were implemented, at HEAD `a14cc30`:

- **Dependency and import provenance.** `lock_hash` was a hardcoded
  `{'python':'3.12','dependencies':[]}`. It is now derived from the allowlisted
  source: an AST scan finds only standard-library imports and no third-party
  package, so the empty external list is measured rather than declared, and no
  host interpreter version is asserted because the fixture runs in the pinned
  image. `Workspace.index()` now returns symbols and import records (module,
  name, alias, relative level, line), which reach the investigator through the
  existing `source_index` path.
- **Reproduction bounds.** The reproduction `ExperimentResult` now carries
  incident, executed conditions, reset, workload, declared limits, repetitions,
  the stated limitations, and a scope line that finite authored fixture
  conditions do not establish reproduction of arbitrary production incidents.
  `completion` distinguishes execution completing from symptom reproduction.
- **IF-002 reproduction assessment.** `order_restart` establishes a durable
  COMPENSATING barrier with the reservation confirmed HELD, then measures
  recovery against a declared deadline, so the verdict is observed, not observed
  or not determined, with its criterion and supporting observation. A
  non-terminal status counts as reproduced only after the declared window
  elapses; an intermediate state is not a failure.
- **Derived T8 metrics.** `benchmarks/t8/derived_metrics.json`, generated by
  `scripts/derive-t8-metrics.py`, restates the brief's requested measurements
  from retained fields only, hashing the input it actually derived from. Time to
  final verdict (n=4) is not called resolution time, because two of those
  verdicts are rejections. Clean-workload *failures* (0 of 8 evaluated clean case
  instances) are not called regressions, because no baseline run was retained.
  Reproduction rate, time to reproduction, successful-resolution time, lost
  orders and duplicate effects are null with reasons, never zero. All twelve
  attempts and their outcomes are preserved and `summary.json` is unchanged.

These are implemented capabilities, not evidence of reliability. IF-001 symptom
reproduction remains undetermined for want of committed-effect evidence, repeat
live repair reliability remains unproven, and the scripted controller
integration consumes simulated protected results rather than running the real
protected evaluator. No new reliability percentage is claimed and T8 still
supports no variant ranking.
