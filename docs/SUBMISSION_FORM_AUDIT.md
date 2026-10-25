# Submission form audit — October 25, 2026

Scope authority remains [ORIGINAL_BRIEF.md](ORIGINAL_BRIEF.md). This audit replaces
the October 4 signed-out assessment. It distinguishes saved draft content from
submission completion. No final submission was made.

## Sources and requirements

[Official rules](https://nebiusglobalaihackathon.devpost.com/rules) and
[FAQ](https://nebiusglobalaihackathon.devpost.com/details/faqs) rechecked October 25.
The deadline is October 30 at 10:00 PDT / 22:30 IST; judging ends December 15.
Required materials include a functioning demo or test build, public licensed
source with setup instructions, English description, model/platform feedback,
and a public YouTube demonstration under three minutes. Runtime Token Factory
inference with an NVIDIA open model meets the platform route; the frontend need
not run on Nebius. Working access must remain free through judging. Separate
provider credentials are not expressly mandated, but replay alone has not been
confirmed sufficient for this project. Eligibility, ownership and final terms
remain the entrant's declarations.

The generic form permits Vimeo/unlisted video and reviews the first three
minutes. Follow the stricter hackathon rules: public YouTube, under three minutes.

## Authenticated draft inspected and saved

Submission ID: `1262170`. Project preview:
https://devpost.com/software/incidentforge-73tvfa

The owner signed in and completed the creation CAPTCHA. Project overview saved
successfully. After an interruption, unsaved detail text was lost; it was restored,
saved with Save & continue, then reopened and read back. Additional information
was also saved and reopened. These are actual persistence checks, not inferred
from typing into fields. Devpost still displays **Draft**, 2/5 steps done, because
required items remain incomplete. The finalization page was read, but its terms
checkbox and Submit project button were not activated.

| Section | Observed fields/limits | Verified status |
|---|---|---|
| Manage team | Entrant listing | Navin Kumar listed as sole teammate on finalization |
| Project overview | Name (60 characters), pitch (200), thumbnail | Name and pitch saved; thumbnail remains placeholder |
| Project story | Required Markdown description | Saved; [copy](DEVPOST_DRAFT.md) mirrors submitted draft text |
| Built with | Required, up to 25 tags | Python, Docker, JavaScript saved; full stack described in story |
| Try it out | Multiple URL fields | Pages and public repository links saved |
| Image gallery | Up to 15 JPG/PNG/GIF files, 5 MB each; recommended 3:2 | Optional; not uploaded |
| Demo video URL | Required | Empty, deferred by owner |
| Additional file | Up to 35 MB | Optional; not uploaded |
| Finalization | Terms agreement and Submit project | Unchecked and not submitted |

No exact description length limit was exposed in the inspected UI. Thumbnail
and gallery fields were not marked required; no image requirement is inferred
from their presence.

## Additional information — field-level state

Numbers below are zero-based positions in the inspected form, not rule numbers.
Personal ratings and organizer-facing narrative are saved in Devpost; their full
private responses are not copied into this public audit.

| Field | Saved or remaining |
|---|---|
| 0 Submitter type | Individual, consistent with owner reporting a solo project |
| 1 Organization | N/A |
| 2 Country | Owner-provided residence saved |
| 3 Canadian province | N/A |
| 4 Track | Coding and agentic engineering |
| 5 New/existing | New; project work began during the submission period |
| 6 Existing-project updates | Unset; not applicable to New |
| 7 Public repository | https://github.com/ns-0437/incidentforge |
| 8 Demo/test build | https://ns-0437.github.io/incidentforge/ |
| 9 Model and variant rationale | Exact Nano endpoint and budget rationale; no size-ranking claim |
| 10 Output quality | Owner-authorized rating with evidence-based strengths and limitations |
| 11 Model adaptation | Prompt engineering, no fine-tuning; action/edit constraints and independent verification |
| 12 Other-model comparison | No controlled cross-model comparison; no superiority claim |
| 13 Nebius capabilities | Hosted Token Factory inference and Sandbox execution/artifact export; no dedicated GPU or autoscaling claim |
| 14 Recommendation | Owner-authorized rating and workflow-based explanation |
| 15 Experience comparison | Subjective rating; explicitly not a measured cloud/local benchmark |
| 16 Platform improvements | Timeout usage reconciliation and operation/artifact recovery examples |
| 17 Model improvements | Exact-edit and recovery reliability with structured coding-agent examples |
| 18 Tavily | No; no runtime integration claimed |
| 19 Builders & Brews city | Unset; owner confirmed no attendance |
| 20 Age-of-majority declaration | Unchecked; owner review required |
| 21 Promotion-entity employment declaration | Unchecked; owner review required |
| 22 AI tools | Claude Code/Codex for development; Nemotron for runtime proposals |
| 23 Learning | Owner answer saved and read back |
| 24 Career value | Owner answer saved and read back |

## Engineering and website checks

- GitHub API confirms public source, MIT detection and the correct Pages homepage.
- CI run [40166437242](https://github.com/ns-0437/incidentforge/actions/runs/40166437242)
  matches `888afc0` and passed portable, windows-operator and linux-isolation.
  Underlying code `cbfcb63` collected 267 portable tests (206 passed, 61 skipped),
  passed 37 Windows operator tests, and passed the Linux isolation job.
- Public HTML, JavaScript, CSS, icon, evidence and checksum returned HTTP 200 and
  matched checked-out content after newline normalization. The local site validator
  passed the seven-file allowlist and two-incident evidence checks.
- Both incidents' Observe/Investigate/Repair/Verify panels were inspected. All
  twelve campaign attempts expanded. Downloaded JSON parsed equal to the curated
  source evidence. Browser warning/error logs were empty in the inspected session.
- Keyboard ArrowRight advances the stage tab. All four architecture buttons
  expose their respective explanations. Mobile (390x844) and desktop (1440x900)
  checks showed no document-level horizontal overflow; screenshots were inspected.
  These are sampled checks, not a certification of every device or accessibility
  requirement.
- No live run, paid inference, new Sandbox operation or budget change was made.

## Remaining before final submission

1. Owner reviews the two eligibility declarations and authorship/reuse notices.
2. Owner supplies the deferred video and resolves the deferred working-access
   requirement; neither is marked complete by this audit.
3. Recheck the completed entry and its links, accept final terms with the owner's
   action-time approval, submit, and retain Devpost's confirmation.

The finalization page accepting draft navigation does not mean missing fields or
requirements have passed validation. No placeholder video, invented access promise,
or unverified personal declaration was entered.
