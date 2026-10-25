# Release checklist — submission audit updated October 25, 2026

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
- [x] Main repository made public October 11 with owner approval.
- [x] Pages deploy job succeeded and public assets were checked October 11.
- [x] About/README and primary recording/submission links point to the new site.
- [ ] Check final CI, source/demo/video links, setup instructions and actual hackathon entry requirements.
- [ ] Submit the reviewed Devpost entry and retain confirmation.

The owner confirmed continued access to their account through December 15; this
does not establish judge access. The owner has sent the support email and will
provide the reply. Never share the owner's personal key or require judges to buy
credits. The static recorded viewer alone does not settle live execution access.

## Pages deployment verified

[Deployment run](https://github.com/ns-0437/incidentforge/actions/runs/38141923974) succeeded October 11.
The page, JavaScript, styles, icon and evidence were fetched publicly and checked
against source. Live frontend: https://ns-0437.github.io/incidentforge/
For future manual deployments follow [JUDGE_FRONTEND.md](JUDGE_FRONTEND.md);
confirm the deploy job actually runs rather than relying on a green skipped run.
GitHub serves the static replay independently of the owner computer.

## Timing and constraints

Official rules rechecked October 25 at https://nebiusglobalaihackathon.devpost.com/rules:
October 30, 10:00 PDT (22:30 IST) submission; judging through December 15; public
licensed source, working demo/test build, English description, public YouTube video
under three minutes, track and platform feedback. The signed-in form was audited October 25 and the technical draft saved;
see [field-level audit](SUBMISSION_FORM_AUDIT.md). Final submission is pending.
Separate provider accounts for judges are not explicitly required. The supported
access method still needs to satisfy free working access through judging.

The cumulative development allocation remains $0.40. Current accounted exposure
is $0.337380, including unknown historical usage reserved at full cost; $0.062620
remains and no inference is pending. Do not reset the ledger or expand spending.

Main source and the recorded Pages frontend are public. This does not deploy
the live inference backend. Recording the replay needs no inference calls.

## October 25 draft preparation

- [x] Rechecked public repository, MIT detection, Pages link and CI at `888afc0`.
- [x] Audited authenticated Devpost fields and saved story, source/demo links, technical feedback and owner-supplied survey answers.
- [ ] Owner reviews eligibility declarations and final terms.
- [ ] Video and working-access items remain deferred by the owner.
- [ ] Submit and retain confirmation after the remaining requirements are fulfilled.

No inference was dispatched during this audit. Application code, original brief,
frozen campaign artifacts and the budget ledger were not changed.
