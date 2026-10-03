# IncidentForge: submission and demonstration

Planning updated October 2, 2026. Source: [official rules](https://nebiusglobalaihackathon.devpost.com/rules), reviewed October 1 in this conversation. Recheck against the live entry form before submission. No publication or deployment is authorized by this document.

## Checklist

- Deadline October 30, 2026, 10:00 PDT / 22:30 IST. Aim to submit October 29.
- Working application with actual Token Factory inference or qualifying Nebius AI Cloud runtime, plus an NVIDIA open model. Our project additionally requires meaningful real Token Factory Sandbox execution.
- Public GitHub/GitLab/Bitbucket repository with an open-source license. Apache-2.0 proposed; MIT/MPL-2.0 are other examples in the rules, not the only possible licenses.
- Complete source/assets, pinned setup instructions, integration details, reproducible demo/test build, project description, Coding and Agentic Engineering category and platform feedback.
- Disclose reused/pre-existing work and changes honestly; new Git history does not remove disclosure duties. Preserve model and dependency licenses separately.
- Public YouTube demonstration shorter than three minutes; English text/narration or translations. Use only permitted media.
- Working access free of charge to judges through the end of judging December 15 (judging December 1–15). Include credentials/testing instructions if private.
- Functional behavior must match claims and video. UI, implementation, impact and idea quality are equally weighted; no implied guarantee of a score.

## Judge access and funding: unresolved requirement

Current trial balance/expiry does not establish December availability. Request extension or additional free credits via the existing program/support route; do not assume success. Funded hosted access or a supported test build with project-funded controlled runtime access must be demonstrated before submission. Do not embed a permanent API key in a public client/repository or require judges to buy credits.

A prerecorded run and offline evidence viewer can supplement the working build and reduce repeated costs, clearly labeled. They do not replace required working access or real runtime integration. If future model/Sandbox access cannot be funded through grants or confirmed free beta, surface the blocker to the owner; no automatic paid hosting or local-only substitution.

Use a bounded fixture, per-run concurrency/cost cap, authenticated server-side credential handling where a hosted endpoint is chosen, reliable cleanup, and a known-good reset. Choose the access mechanism after platform probes; building an elaborate hosting system is not on the core critical path. Rehearse from a clean machine/environment and document expected run duration and limitations.

## Video script: target 2 minutes 45 seconds

| Time | Demonstration |
|---|---|
| 0:00–0:20 | Backend incident: one order, duplicate synthetic charges. Explain why removing an error is not sufficient. |
| 0:20–0:40 | Select fixture and show actual Nebius/Nemotron integration and reproduction evidence. Label live versus recorded playback. |
| 0:40–1:10 | Competing hypotheses and one controlled experiment that separates them; link observations. |
| 1:10–1:35 | Explicitly hand-authored harmful verifier fixture: retry removal hides duplicate symptom but loses order completion; evaluator rejects it. |
| 1:35–2:10 | Actual agent-generated patch if achieved, clean validation and additional fault conditions; show limitations. If unresolved, do not simulate success. |
| 2:10–2:30 | Evidence export, costs, second incident mechanism and measured comparison with denominators. |
| 2:30–2:45 | Who benefits, reproducible judge entry point and 'validated under declared conditions'. |

If actual end-to-end runtime exceeds video length, use labeled cuts or recorded playback with artifact/run IDs. Never imply authored bad patches were agent discoveries. Avoid claims of universal correctness, autonomous production deployment or self-evolution.

## Release evidence

Include setup verification, model identity/license, platform probe logs, source/image/patch/evaluator hashes, sample evidence exports, results including failures, public contract, current constraints, bounded live demo instructions and platform feedback. Release held-out material only after measurement and mark it unsuitable as future independent holdout. Redact secrets and personal account details. Verify licensing, public links, video visibility, access lifetime and startup/cleanup before submission.
