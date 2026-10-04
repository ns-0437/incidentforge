# Release checklist — October 4, 2026

[Submission package](SUBMISSION_PACKAGE.md) contains the copy, recording walkthrough
and claim-to-evidence map. [Completion gates](COMPLETION_GATES.md) tracks limitations.
This checklist describes release work, not authorization to publish now.

## Engineering evidence ready

- [x] Original brief retained byte-identical; MIT license present.
- [x] Real Token Factory inference and Sandbox execution retained for both incidents.
- [x] Frozen T8: all 12 attempts retained; 2 accepted, 2 rejected, 8 unresolved; no ranking claim.
- [x] IF-001 v22 accepted with its weak authored assertion disclosed.
- [x] IF-002 v25 accepted with a baseline-failing, final-revision-passing restart assertion and eight protected cases per validation.
- [x] Clean checkout: 115 portable tests, 19 Linux checks, no skips, four operator HTTP routes and seven-file static package passed at 85b4612.
- [x] Review ZIP CRC and manifest checks passed; immediate browser cancellation rehearsed with zero model calls.
- [x] Manual public-main-only Pages workflow and publishing consistency checks prepared.
- [x] README, Devpost draft, judge guide, attribution inventory and timed script prepared for review.

Evidence: [latest clean checkout](../benchmarks/release/rehearsal-v25.json),
[IF-001](../benchmarks/reliability/v22-pilot.json),
[IF-002](../benchmarks/reliability/v25-pilot.json),
[T8](T8_RESULTS.md). Historical rehearsals remain in benchmarks/release/.
Passing development examples do not establish repeat autonomous repair reliability.

## Owner and external release steps

- [ ] Owner reviews authorship, reuse/model notices and final claims in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [DEVPOST_DRAFT.md](DEVPOST_DRAFT.md).
- [ ] Incorporate Nebius's reply into a concrete free judge-access path and rehearse it with a fresh user.
- [ ] Record the walkthrough, verify duration, publish on YouTube and check signed-out playback.
- [ ] Make the main repository public at owner-approved release.
- [ ] Deploy Pages from the main repository. Expand into the ordered sub-steps in
      [Pages deployment is unexercised](#pages-deployment-is-unexercised) below; the
      workflow has never executed, so treat this as a first run rather than a repeat.
- [ ] Only after successful deployment, replace the retained old About/README demo link and other submission links.
- [ ] Check final CI, source/demo/video links, setup instructions and actual hackathon entry requirements.
- [ ] Submit the reviewed Devpost entry and retain confirmation.

The owner confirmed continued access to their account through December 15; this
does not establish judge access. The owner has sent the support email and will
provide the reply. Never share the owner's personal key or require judges to buy
credits. The static recorded viewer alone does not settle live execution access.

## Pages deployment is unexercised

Observed October 4, 2026 against ns-0437/incidentforge:

- `gh run list --workflow pages.yml` returns nothing. The workflow has **never run**.
- `gh api repos/ns-0437/incidentforge/pages` returns **404**. No Pages site is
  configured, so no publishing source has been selected yet.
- The repository is private, which is why neither of the above has happened.

The deploy job is guarded by `github.repository`, `github.event.repository.private
== false` and `github.ref == 'refs/heads/main'`. **A guard that evaluates false
skips the job, and a run whose only job is skipped still reports as successful.**
On release day that reads as a green run with nothing deployed, which is the one
outcome most likely to be mistaken for success. Check the job's own status, not
the run's colour, and confirm a `page_url` was emitted.

The deployment sequence itself lives in [JUDGE_FRONTEND.md](JUDGE_FRONTEND.md) and
is not restated here. Two additions to it, both consequences of the above:

- Its step 1 and step 2 are prerequisites for the guard, not formalities. The job
  cannot pass while the repository is private, and it has nowhere to publish until
  the Pages source is set to GitHub Actions.
- At its step 3, read the **job** status. A skipped job is the failure mode to
  watch for, and it does not look like a failure.
- At its step 4, `python scripts/check-site.py` validates the local artifact only.
  Confirming what is actually served needs a signed-out fetch of
  `https://ns-0437.github.io/incidentforge/` returning 200.

The workflow pins `ubuntu-24.04` and uses `actions/checkout@v6`,
`configure-pages@v5`, `upload-pages-artifact@v4` and `deploy-pages@v4`. Newer
majors exist (`configure-pages@v6`, `upload-pages-artifact@v5`, `deploy-pages@v5`)
and were deliberately not adopted: an untested bump to an untested workflow adds
risk at the moment there is least time to absorb it. If the first dispatch fails
on a deprecated action, bumping these is the first thing to try.

## Timing and constraints

Official rules rechecked October 4 at https://nebiusglobalaihackathon.devpost.com/rules:
October 30, 10:00 PDT (22:30 IST) submission; judging through December 15; public
licensed source, working demo/test build, English description, public YouTube video
under three minutes, track and platform feedback. Recheck the live rules and entry
form before submitting; the signed-in submission form has not been audited.
Separate provider accounts for judges are not explicitly required. The supported
access method still needs to satisfy free working access through judging.

The cumulative development allocation remains $0.40. Current accounted exposure
is $0.337380, including unknown historical usage reserved at full cost; $0.062620
remains and no inference is pending. Do not reset the ledger or expand spending.

Main source remains private. The old demo link is retained as requested and was
last observed returning 404; the replacement main-repository Pages site is prepared
but not deployed. Follow [JUDGE_FRONTEND.md](JUDGE_FRONTEND.md) at release. Do not
recreate the separate demo repository. Recording setup needs no inference calls.
