# Submission package

Prepared October 4, 2026. Core demonstrations and local reproducibility checks are
recorded. This package is ready for owner review, not yet for final submission.
Main source is public and the recorded frontend is deployed. No provider call is
triggered by these files.

## Copy and recording

- [Devpost draft](DEVPOST_DRAFT.md): project description, results, track and platform feedback.
  Resolve the maintainer notes before copying the final entry; use public repository
  links for evidence after release rather than local relative links.
- [Timed narration and screen sequence](VIDEO_SCRIPT.md): target 2:45;
  [plain narration](VIDEO_NARRATION.txt) for reading during recording.
- [Recording setup](RECORDING_HANDOFF.md): serve the retained frontend locally with no inference.
- [Judge guide](JUDGE_GUIDE.md): prerequisites, tests, local console and live-access limitations.
- [License and reuse inventory](THIRD_PARTY_NOTICES.md): owner review and AI-assistance disclosure.
- [Submission form audit](SUBMISSION_FORM_AUDIT.md): verified entry requirements mapped
  to prepared content, copy-ready testing instructions, placeholders and owner actions.
  The form UI itself remains unaudited pending a signed-in session.

## Claims and supporting evidence

| Claim | Evidence | Boundary |
|---|---|---|
| Runtime Nemotron calls and real Sandbox execution | [IF-001 v22](../benchmarks/reliability/v22-pilot.json), [IF-002 v25](../benchmarks/reliability/v25-pilot.json) | Recorded development, not a hosted public inference service |
| Regression detects the IF-002 restart symptom | [v25 baseline assessment and validation](../benchmarks/reliability/v25-pilot.json) | Assertion covers terminal state; protected checks separately cover effects and stock |
| IF-001 authored test is weak | [v22 post-run baseline assessment](../benchmarks/reliability/v22-pilot.json) | Already passes before repair; do not present it as defect detection |
| Frozen comparison: 2 accepted, 2 rejected, 8 unresolved | [T8 report](T8_RESULTS.md), [data](../benchmarks/t8/summary.json) | Three timeouts invalidate variant ranking |
| 115 portable and 19 Linux checks passed | [clean-checkout rehearsal](../benchmarks/release/rehearsal-v25.json) | No fresh-user funded execution claim |
| Curated replay can run without credentials | [frontend guide](JUDGE_FRONTEND.md), [committed data](../site/evidence.json) | Checksum verifies artifact consistency, not independent attestation of execution |

Do not claim reliable repair on arbitrary repositories, universal correctness,
verified causal explanations, or superiority of B2. One accepted development run
closes a demonstration gap, not a repeat-reliability evaluation.

## Release sequence

1. Owner reviews attribution and the final claims. Preserve the original brief.
2. Incorporate the Nebius reply into concrete judge access instructions and rehearse
   the supported path. Owner-account availability alone is not delivered judge access.
3. Owner records the final viewer walkthrough, checks duration and uploads the public
   YouTube video. Verify playback signed out and add its URL to the final entry.
4. At owner-approved release, make the main repository public and run the manual
   Pages workflow using [the deployment guide](JUDGE_FRONTEND.md).
5. Verify the actual Pages URL signed out. Only then replace the retained old demo
   link in GitHub About, README, recording handoff and Devpost copy.
6. Recheck the live hackathon entry requirements, source/demo/video links and free
   access instructions; submit the reviewed entry and retain confirmation.

Hosting steps 4 and 5 were completed October 11 with owner approval.
Live frontend: https://ns-0437.github.io/incidentforge/
About and README now use that URL. Do not recreate the deleted demo repository.

## Current constraints

Exposure: $0.337380 of the $0.40 cumulative development limit; $0.062620 remains.
No pending inference at this checkpoint. Do not reset the ledger or spend the
unallocated trial credits. Recording the static replay requires no model calls.
Video, supported judge access and actual submission remain open.
See [completion gates](COMPLETION_GATES.md) for the detailed status.
