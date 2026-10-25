# Devpost draft — saved technical copy, October 25, 2026

Project name: IncidentForge

Pitch: Investigate distributed incidents, propose source repairs, and verify business behavior with independent evidence—powered by NVIDIA Nemotron on Nebius Token Factory.

The project story below was saved in Devpost and reopened to verify persistence.
It is draft content, not a submitted entry.

## Inspiration
An API can return success while charging a customer twice. A restart can leave inventory reserved indefinitely. IncidentForge helps backend engineers inspect a proposed repair together with the evidence supporting it.

## What it does
IncidentForge investigates two synthetic failures across Order, Inventory and Payment: duplicate payment after a lost response (IF-001), and stranded compensation after restart (IF-002). A bounded NVIDIA Nemotron agent compares hypotheses, runs controlled experiments, edits allowed source and authors assertions. A protected evaluator independently checks durable effects, recovery, inventory and idempotency. The result is a patch accepted for human review, a rejection, or an explicit unresolved outcome. It never deploys to production.

The public frontend is a recorded evidence viewer. Select an incident and follow Observe, Investigate, Repair and Verify; expand the campaign attempts and download the evidence. A separate local operator console supports bounded live execution and review exports. The hosted viewer cannot launch new investigations or spend credits.

## How we built it
Python implements the controller, HTTP services, persistence broker, evidence records and local operator. SQLite preserves the inference allocation. The runtime model is nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B through Nebius Token Factory. Nebius Sandboxes/ConTree execute candidate workloads; a separate restricted Docker reader recomputes protected results from exported evidence. HTML, CSS and JavaScript render the GitHub Pages frontend. Model proposals cannot replace the independent final verdict.

## Challenges and results
The frozen twelve-attempt B0/B1/B2 campaign retained two accepted repairs, two rejected candidates and eight unresolved attempts. Three inference timeouts crossed the predeclared infrastructure threshold; these data do not support a variant ranking. Later successful examples do not replace frozen results.

The displayed IF-001 repair passed protected checks, but its authored retry-count assertion also passed before repair and does not detect the original defect. The IF-002 restart assertion fails before repair and passes afterward; its candidate passed eight protected cases per validation. These finite examples do not establish repeat autonomous repair reliability or universal correctness.

Later work added compile checks, mandatory source rereads after rejected edits, final-revision assertions, evidence-integrity checks and atomic budget initialization. CI at code revision cbfcb63 collected 267 portable tests (206 passed, 61 explicitly skipped); 37 Windows operator tests and the Linux isolation job also passed. Scripted controller integration consumes simulated protected results and is not live-model reliability evidence.

## What we learned
Plausible explanations, useful edits and independently accepted repairs are different outcomes. Request counts are not committed effects. We retain unresolved attempts, limitations and unknown usage instead of treating them as successes or free calls. Intermediate feedback cannot replace post-freeze validation.

## Try it and inspect the evidence
- [Recorded demo](https://ns-0437.github.io/incidentforge/)
- [Public MIT-licensed source](https://github.com/ns-0437/incidentforge)
- [Setup and test-build guide](https://github.com/ns-0437/incidentforge/blob/main/docs/JUDGE_GUIDE.md)
- [Frozen campaign results](https://github.com/ns-0437/incidentforge/blob/main/docs/T8_RESULTS.md)

The viewer and portable tests need no provider credentials. Live inference and Sandbox execution require separately arranged Nebius access; the viewer is not a hosted live agent.

## What's next
Improve repeat repair reliability and broaden incident mechanisms without rewriting frozen results. This prototype does not claim production readiness or reliable completion on arbitrary repositories.

## Development assistance
Claude Code and Codex assisted development. NVIDIA Nemotron performs runtime investigation and repair proposals. Third-party runtime and model notices are documented in the repository.


## Platform feedback — supporting evidence
Nebius Sandboxes let us run isolated repairs and export artifacts for independent
checks. Token Factory served the NVIDIA Nemotron Nano agent at runtime. The
IF-002 development example completed eight model calls and produced a patch whose
restart assertion failed before the repair and passed afterward.

Our frozen comparison also exposed three inference timeouts with unknown usage.
We retained the full reservations instead of assuming those requests were free.
A request-status and usage-reconciliation API would let budget-limited agents
recover safely after a client timeout. A useful response would distinguish a
request still running, a terminal request with usage, and a request that was
never accepted. This is a product suggestion based on our client observations,
not a claim that the provider lost usage records.

For Sandboxes, a documented recovery example linking an operation ID, terminal
status and downloadable output would reduce the work needed to recover failed
runs. Our adapter now preserves diagnostic archives even when the command exits
unsuccessfully. An SDK example should cover both successful and nonzero exits,
with bounded polling and artifact verification.

For Nemotron coding workflows, examples combining structured action schemas,
exact source edits and source rereads after rejected edits would help. Our
retained development runs include an uncompilable edit and repeated nonmatching
edits. We added local compilation and mandatory rereads; the later successful
run does not prove either change caused success. These observations describe
this fixture, prompt and bounded budget, not general model capability.

Evidence: [frozen results](../benchmarks/t8/summary.json),
[compile failure](../benchmarks/reliability/v23-pilot.json),
[edit mismatch](../benchmarks/reliability/v24-pilot.json),
[successful development example](../benchmarks/reliability/v25-pilot.json).

## Maintainer notes

- Public source: https://github.com/ns-0437/incidentforge (MIT detected).
- Recorded demo: https://ns-0437.github.io/incidentforge/
- Draft submission ID: 1262170; project preview: https://devpost.com/software/incidentforge-73tvfa
- Track: Coding and agentic engineering.
- Video and working judge-access completion deferred by the owner; neither is certified complete.
- The owner must review eligibility, authorship, reused components and final terms before submission.
- Ratings and private organizer-facing answers are saved in the authenticated draft, not published here.
- See [actual form audit](SUBMISSION_FORM_AUDIT.md) for field-level status.
