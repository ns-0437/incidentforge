# Release checklist — October 3, 2026

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
- [x] Recorded frontend retained locally; main repository remains private.
- [ ] Replacement public demo delivery after owner-requested demo retirement.
- [x] 81 portable controller/regression tests passed locally; CI status must be checked at release.
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

October 4: owner requested retirement of the separate public demo repository and
will delete it manually. Main About URL cleared; local `site/` retained. Public
demo delivery is now an open release gate. Identifier vocabulary is supplied
before investigation; no new live efficacy result is claimed.
