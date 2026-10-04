# Submission form audit

Inspected October 4, 2026. Scope authority stays [ORIGINAL_BRIEF.md](ORIGINAL_BRIEF.md).
Release sequence stays in [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md); this file
covers submission fields only and does not repeat it.

## What was actually accessible

| Source | Accessed | Result |
|---|---|---|
| `nebiusglobalaihackathon.devpost.com` overview | yes | "What to submit" list read in full |
| `nebiusglobalaihackathon.devpost.com/rules` | yes | Full Official Rules read, including Submission Requirements, Testing, Language, IP and Judging |
| `devpost.com/submit-to/30790-.../manage/submissions` | reached, **not authenticated** | Page rendered "Log in" and "Join hackathon". No submission manager content |
| The "Enter a Submission" form itself | **no** | Behind authentication. Never reached |

**This is a requirements audit and a field-readiness review. It is not an audit of
the live form UI.** The browser available in this session holds no Devpost session,
and the Chrome extension is not connected. Nothing was saved, submitted, declared,
or changed. No project visibility was altered.

Consequently the following are **not recorded here and must not be assumed**:
exact on-screen field labels, character or word limits, image and thumbnail
requirements and their dimensions, which fields the UI marks required versus
optional, and the text of any checkbox declarations. The rules reference "images"
as submission content, which implies a gallery or thumbnail field exists, but that
field was not observed. Owner action O-1 below closes this.

## Verified requirements and where each one stands

Sources: hackathon overview page and Official Rules, both read 2026-10-04.

| # | Requirement (verified wording in brief) | Prepared content | Gap |
|---|---|---|---|
| 1 | Working project running on Token Factory or AI Cloud, using an NVIDIA open source model. Rules define this as "makes a runtime call to the Token Factory inference API, or is deployed/run using Nebius AI Cloud compute (Serverless Jobs, Serverless Endpoints, or DevPods)" | Runtime Nemotron Nano calls through Token Factory, retained in [v22](../benchmarks/reliability/v22-pilot.json) and [v25](../benchmarks/reliability/v25-pilot.json) | **None.** Satisfied by the inference-API clause |
| 2 | A category / track | "Coding and Agentic Engineering" in [DEVPOST_DRAFT.md](DEVPOST_DRAFT.md) | None |
| 3 | Project description explaining features and functionality | DEVPOST_DRAFT.md sections through "What's next" | None, pending owner review of claims |
| 4 | URL to a working demo, hosted application, or test build | Static replay prepared in `site/`; Pages not deployed | **Open.** Depends on release and Pages deployment. See placeholder P-1 |
| 5 | Public repo on GitHub/GitLab/Bitbucket with all source, assets and instructions | github.com/ns-0437/incidentforge, currently private | **Open on release authorization only.** Content is ready |
| 6 | Open source license **file**, "detectable and visible at the top of the repository page (in the About section)" | `LICENSE`, MIT. GitHub API reports `license.spdx_id = MIT` | **None.** Detection verified 2026-10-04; it will render in About once public |
| 7 | README with setup instructions and clear guidance for running the project | README plus [JUDGE_GUIDE.md](JUDGE_GUIDE.md) | None |
| 8 | README must highlight Nemotron use, where Token Factory accelerated the workflow, and other Nebius tools used | Present in README and DEVPOST_DRAFT | None |
| 9 | Public YouTube video, "should be less than three (3) minutes", showing the project functioning | [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md) at 2:45 target, 243-word narration | **Open.** Owner records. See placeholder P-2 |
| 10 | Video must not include third-party trademarks or copyrighted music without permission | Added to [RECORDING_HANDOFF.md](RECORDING_HANDOFF.md) review step | None |
| 11 | Feedback on Token Factory, AI Cloud and NVIDIA tools used | DEVPOST_DRAFT "Platform feedback", evidence-linked | None |
| 12 | Written explanation of significant updates if the project predates the Submission Period | Project is new within the period; no prior work to disclose beyond the AI-assistance note | Owner confirms at O-3 |
| 13 | Testing access, free of charge and without restriction, until the Judging Period ends | **Was not written anywhere** | **Closed by this document.** See copy-ready text below |
| 14 | All materials in English | All materials are English | None |
| 15 | City selection if the entrant attended a Builders & Brews event | Not applicable unless the owner attended one of the 20 listed cities | Owner confirms at O-4 |

## The testing requirement changes the judge-access picture

Verified wording from the Official Rules, Testing section:

> "Access must be provided to an Entrant's working Project for judging and testing
> by providing a link to a website, functioning demo, **or a test build**. ... The
> Entrant must make the Project available free of charge and without any
> restriction, for testing, evaluation and use by the Sponsor, Administrator and
> Judges until the Judging Period ends. **Judges are not required to test the
> Project and may choose to judge based solely on the text description, images, and
> video provided in the Submission.**"

Two consequences, both material:

1. A **test build** satisfies the requirement. A public repository with a working
   quick start, a credential-free test suite and a credential-free replay is a test
   build, and it needs no provider account for anyone.
2. Judging does not depend on judges running anything.

**This does not mean judge access is arranged, and nothing here should be stated as
if it were.** The pending Nebius reply still matters for anyone who wants to
reproduce live inference. What changes is the risk: the submission's testing
requirement is satisfiable without that reply, so the reply is an improvement rather
than a blocker. [COMPLETION_GATES.md](COMPLETION_GATES.md) should be read with that
distinction in mind.

The rules also say that if an entrant's **website** is private, credentials must be
included in testing instructions. That clause is about the entrant's own hosted
site. It does not call for sharing a personal provider API key, and this project
will not share one.

## Copy-ready text

### Testing instructions (new, field 13)

> IncidentForge is supplied as a test build. Everything below is free, needs no
> account, and needs no API key.
>
> 1. Clone the public repository and follow the quick start in `docs/JUDGE_GUIDE.md`.
>    Python 3.12 or newer is the only prerequisite for steps 2 and 3. Docker Desktop
>    with Linux containers is needed only for the additional isolation checks the
>    guide describes separately.
> 2. Run the portable test suite. It exercises the controller, the protected
>    evaluator, the grounding checks and the frozen campaign data:
>    `python -m unittest tests.test_t4 tests.test_t5 tests.test_t6_controller tests.test_t7 tests.test_prefreeze tests.test_t8 tests.test_reliability`
>    115 tests are expected to pass. No model calls are made.
> 3. Open the recorded evidence viewer at the demo URL, or serve it locally with
>    `python -m http.server 8766 --bind 127.0.0.1 --directory site`. It replays
>    retained investigations, repairs, authored assertions and protected evaluation
>    results for both incidents, including the attempts that failed.
> 4. Optionally start the local operator console as described in the judge guide.
>
> The hosted viewer replays retained synthetic execution. It is not a live
> inference service and it will not start new investigations. Reproducing live
> runs requires your own Nebius Token Factory credentials, which the quick start
> explains how to configure; this is optional and not required to evaluate the
> retained evidence. No credential of ours is distributed.

### Track (field 2)

> Coding and Agentic Engineering

### Significant-updates note (field 12)

> IncidentForge was created new during the Submission Period. It reuses no prior
> project of ours. Development was assisted by AI coding tools; the design,
> evaluation methodology, measurements and all claims are the entrant's own work
> and were reviewed by the entrant. Third-party components and their licenses are
> inventoried in `docs/THIRD_PARTY_NOTICES.md`.

Project description, platform feedback and the built-with list are already written
in [DEVPOST_DRAFT.md](DEVPOST_DRAFT.md) and are not duplicated here.

## Placeholders that must not be submitted as-is

| ID | Placeholder | Resolves when |
|---|---|---|
| **P-1** | Demo URL. The retained link `https://ns-0437.github.io/incidentforge-demo/` returned 404 on October 4 and is kept only until a replacement deploys. Planned replacement `https://ns-0437.github.io/incidentforge/` is not deployed | Repository is public and the Pages workflow has run and been verified signed out |
| **P-2** | Video URL. Not recorded, not uploaded | Owner records, verifies duration under three minutes, uploads public, checks signed-out playback |
| **P-3** | Repository URL is live but private, so it returns 404 when signed out | Owner authorizes public release |
| **P-4** | Live-execution access for judges beyond the credential-free test build | Nebius reply arrives and a supported path is rehearsed. Not required for field 13 |

## Owner actions this audit cannot perform

| ID | Action |
|---|---|
| **O-1** | Sign in to Devpost and open the "Enter a Submission" form so the remaining UI details can be recorded: field labels, character limits, image or thumbnail requirements, required-versus-optional marking, and any checkbox declarations |
| **O-2** | Confirm hackathon registration. The rules require clicking "Join Hackathon" before a submission can be created, and the unauthenticated page could not show whether this is done |
| **O-3** | Review authorship, the AI-assistance disclosure and the IP representations in the rules, which require the submission to be the entrant's original and solely owned work |
| **O-4** | Confirm whether any Builders & Brews city event was attended. If not, leave the city field unset |
| **O-5** | Review and approve the testing-instructions text above before it is pasted |

## Useful operational facts observed

- Deadline renders as **Oct 30, 2026 @ 10:30pm GMT+5:30** on the site, matching the
  rules' 10:00 am Pacific. Judging ends **December 15, 2026, 12:00 pm Pacific**.
- **Draft submissions can be saved** before the deadline and edited until it passes.
  After the Submission Period ends no changes are permitted. Filling the form early
  as a draft costs nothing and surfaces unknown fields sooner.
- Devpost shows planned maintenance on **Oct 7, 06:00 UTC**. Avoid relying on that
  window.
- "Most Valuable Feedback" eligibility is "All Eligible Submissions that complete
  the feedback submission section", so the prepared feedback should be entered in
  that section rather than folded into the description.
- Stage One is pass/fail on whether the project reasonably fits the track and
  reasonably applies the featured APIs. A runtime Token Factory call in a coding
  agent addresses both.
- Each project is eligible for one Overall Award **or** one Track Award, plus one
  Bonus Award. This is structure, not a prediction of any result.
- The rules require the project to "function as depicted in the video and/or
  expressed in the text description". The video must therefore keep the
  recorded-replay labelling the script already specifies.
