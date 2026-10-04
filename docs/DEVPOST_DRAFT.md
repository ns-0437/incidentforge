# Devpost draft — review before submission

## Project name
IncidentForge

## Tagline
Investigate incidents, propose repairs, and verify business behavior with evidence.

## Inspiration
An API can return success while charging a customer twice. A restart can leave
inventory reserved forever. We wanted a coding agent that investigates those
failures and submits a reviewable patch with independently checked evidence.

## What it does
IncidentForge runs a synthetic three-service application: Order, Inventory and
Payment. It reproduces two distributed failure mechanisms, asks a model to compare
hypotheses and run a controlled experiment, then allows bounded source edits and
developer assertions. A protected evaluator checks durable effects, recovery,
inventory and idempotency. The result is a patch for human review or an explicit
rejection/unresolved report. No production deployment occurs.

## How we built it
Python implements the controller, HTTP services, persistence broker, evidence
chain and local UI. NVIDIA Nemotron Nano is called through Nebius Token Factory
at runtime. Nebius Sandboxes execute isolated candidate workloads; an independent
restricted Docker reader recomputes protected results from exported evidence.
The static frontend explores recorded synthetic evidence without
exposing keys or triggering paid operations.

## Challenges and measured results
The frozen twelve-attempt B0/B1/B2 comparison produced two accepted final repairs,
two rejected frozen candidates and eight unresolved attempts. Three inference
timeouts crossed the predeclared infrastructure threshold, so we make no variant
ranking claim. All attempts remain in the published results.

Later development added constrained action formats, compile checks, source rereads
after rejected edits, and required authored assertions on the final revision.
The recorded IF-001 repair passed protected checks, but its retry-count assertion
also passed before repair and therefore does not detect the original defect.
The recorded IF-002 repair has a restart assertion that fails before repair and
passes afterward; eight protected cases accepted the candidate in each of two
executions. These are development examples, not replacement benchmark results.
Repeat autonomous repair reliability remains unproven.

A clean checkout passed 115 portable tests and 19 Linux behavioral/isolation checks
with no skips. The local console and static replay started without model calls.
Evidence: [frozen results](../benchmarks/t8/summary.json),
[IF-001](../benchmarks/reliability/v22-pilot.json),
[IF-002](../benchmarks/reliability/v25-pilot.json),
[clean checkout](../benchmarks/release/rehearsal-v25.json).

## What we learned
Correct measurements, plausible explanations, useful edits and a completed agent
workflow are different outcomes. We retain failures and costs rather than selecting
only successful demos. Intermediate feedback cannot replace post-freeze validation.

## What's next
Improve compensation-repair reliability, extend
fault coverage with new incident mechanisms, and finish durable judge access.
The current system does not establish universal repair correctness or reliable
completion on arbitrary repositories.

## Built with / track
Python, Docker, SQLite, Nebius Token Factory, Nebius Sandboxes/ConTree,
NVIDIA Nemotron, HTML/CSS/JavaScript. GitHub Pages deployment is prepared for release.
Track: Coding and Agentic Engineering.

## Platform feedback
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

## Maintainer notes — resolve before pasting the final entry
- Recorded demo: https://ns-0437.github.io/incidentforge-demo/
- Source: https://github.com/ns-0437/incidentforge (PRIVATE until release)
- Video: NOT RECORDED / NOT PUBLISHED
- Free provider availability through December 15: owner-confirmed October 4.
- Working judge access delivery and fresh-user rehearsal: PENDING.
- AI assistance disclosure: developed with Claude Code and Codex assistance;
  Navin Kumar must review authorship, reused components and final claims.

Do not submit this draft with unresolved placeholders. Publishing the repository,
YouTube video and final Devpost entry are separate release actions.

Owner clarification, October 4: confirmation covers continued access to the owner
account only. Separate judge credentials/access have **not** been confirmed.

Release check October 4: the recorded demo URL returns HTTP 404. The requested
link remains unchanged, but deployment is not currently available. Restore
working hosting before submission. The private source returning signed-out 404
is expected until the owner authorizes publication. Nebius access/credit email
has been sent by the owner; reply pending.
