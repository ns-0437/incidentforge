# Release checklist â€” October 3, 2026

Rules rechecked: https://nebiusglobalaihackathon.devpost.com/rules

The official deadline is October 30, 10:00 PDT (22:30 IST). The rules call for a
public licensed source repository, a working demo or test-build link, an English
description, a public YouTube video under three minutes, track selection and
platform feedback. Free working access must last through judging, which ends
December 15. Recheck the live entry form before final submission.

## Engineering artifacts
- [x] Original brief retained; MIT license present.
- [x] Real Token Factory inference and Sandbox execution evidenced.
- [x] Frozen twelve-slot T8 results, failures and accounting retained.
- [ ] Restore working frontend deployment; existing URL returned 404 on October 4. Main repository remains private.
- [x] 113 portable controller/regression tests passed locally; CI status must be checked at release.
- [x] Judge guide, submission copy and timed recording script prepared.
- [x] Fresh-checkout Linux/setup rehearsal recorded: 61 portable tests, 16 Linux checks, four HTTP routes; see [record](../benchmarks/release/rehearsal.json).
- [x] Two live completion attempts retained: IF-001 accepted, IF-002 rejected. A third rejected IF-002 pilot exercised authored-test completion live.

## Owner/access gates
- [x] Owner approved $0.40 cumulative maximum from existing free credits; no further increase.
- [x] Owner confirmed free provider access through December 15 on October 4 (not independently verified).
- [ ] Rehearse the actual judge access and credential-delivery path without requiring judges to buy credits.
- [ ] Review model/dependency license notices and ownership/reuse disclosure.
- [ ] Record final demo and publish it on YouTube; verify signed-out playback.
- [ ] Make main repository public at release, as owner requested.
- [ ] Verify source/demo/video links and judge instructions from a fresh browser.
- [ ] Submit the reviewed Devpost entry and retain confirmation.

No API key needs to be pasted into chat. The operator profile is already usable.
No paid overage, automatic public-source release or final submission is implied by
this checklist. A passing historical repair or offline replay does not certify
the current autonomous workflow; disclose the mixed live results and limits of the tested coverage.

Supporting materials: [third-party inventory](THIRD_PARTY_NOTICES.md) and
[draft access request](JUDGE_ACCESS_REQUEST.md). Neither replaces owner review or
provider confirmation. The historical submission plan proposed Apache; the
actual project license is MIT.

An earlier live pilot timed out before response. On October 4 its full reservation
was conservatively reconciled with actual usage still unknown; exposure unchanged.
See [timeout recovery](TIMEOUT_RECOVERY.md).

Owner clarification, October 4: confirmation covers continued access to the owner
account only. Separate judge credentials/access have **not** been confirmed.

Fresh-checkout repeat: 97 portable tests and 17 Linux controls passed on f6fc999;
see benchmarks/release/rehearsal-oct4.json. Current source has 113 portable tests, including startup failure reporting.
Owner sent the updated Nebius access/credit request; response pending.

## Main repository Pages preparation â€” October 4

- [x] Manual public-main-only deployment workflow prepared; uploads only site/.
- [x] Static artifact allowlist and evidence digest check added to CI.
- [x] Regression rejects extra files and altered evidence; 113 portable tests pass.
- [ ] Publish source at owner-approved release, enable Pages Actions and deploy.
- [ ] Verify the resulting URL signed out before changing the current About link.

Workflow preparation is not a deployment. The local recording handoff now works
without the unavailable former demo hosting. See JUDGE_FRONTEND.md.

Current requirement-by-requirement status: [completion gates](COMPLETION_GATES.md).
Review export CRC and manifest checks passed for accepted and unresolved evidence;
see benchmarks/release/export-oct4.json. A subsequent browser download also passed CRC and manifest checks.
Immediate browser cancellation stopped before execution with zero model calls;
see benchmarks/release/cancellation-oct4.json. The latest Linux suite passed all
17 checks; see benchmarks/release/linux-oct4-final.json.
