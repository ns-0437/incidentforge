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
A frozen twelve-attempt B0/B1/B2 comparison produced two accepted final repairs,
two rejected frozen candidates and eight unresolved attempts. Three inference
timeouts crossed our predeclared infrastructure threshold, so we make no variant
ranking claim. Later development reduced JSON-escaping friction, added explicit
completion guidance, and prevented unrun or placeholder tests from masquerading
as completed work. The current implementation passes 107 portable tests. Later development includes
an accepted IF-002 Sandbox repair after schema-constrained investigation, as well
as retained failed attempts. That accepted pilot omitted authored tests; the current
completion gate now requires passing authored regression assertions. These are
development results, not a new benchmark.

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
NVIDIA Nemotron, HTML/CSS/JavaScript, GitHub Pages.
Track: Coding and Agentic Engineering.

## Platform feedback
Sandbox image snapshots and evidence export enabled repeatable isolated workloads.
Runtime uncertainty required durable operation guards and bounded polling. Inference
timeouts left usage unknown; per-request reconciliation would simplify budget-safe
recovery. Strict structured-output contracts needed explicit field examples and
clear separation between developer and experiment observations.

## Links and release placeholders
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
