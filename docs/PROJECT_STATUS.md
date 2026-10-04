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

1. Rehearse the complete local judge flow including Sandbox selection, cancellation
   and export, using retained evidence and bounded funded runs only when useful.
2. Address IF-002 diagnosis-to-patch consistency with a specific testable change;
   do not burn remaining credits on identical retries or claim improved reliability.
3. Rehearse delivery of free working judge access through December 15. The owner
   confirmed provider availability on October 4; the actual judge access path remains open.
4. Record the under-three-minute demonstration using VIDEO_SCRIPT.md; publish the
   reviewed video, release the main repository when the owner chooses, check all
   links signed out and submit the completed entry.

## Budget and access

Cumulative accounted exposure: **$0.254663 / $0.40**. Remaining allocation:
**$0.145337**. No new inference was used for this status review or UI change.
The other trial credits are unallocated. The GitHub Pages site is a recorded replay,
not a hosted inference service. The main source repository stays private until release.

Validation for the backend selector: **94 portable tests passed** and JavaScript
syntax validation passed. Tests verify HTTP allowlisting, recorded selection,
child-process arguments and failure before launch when Docker is unavailable.
October 4 browser review confirmed Sandbox selection, recorded patch and validation
views, and review download. The archive CRC and manifest hashes passed. Live UI
launch/cancellation and fresh-user judge access were not rehearsed in this check.

Owner clarification, October 4: confirmation covers continued access to the owner
account only. Separate judge credentials/access have **not** been confirmed.
