# IncidentForge: feasibility

Current checkpoint (October 3, 2026): T3 PASSED. The user approved the reviewed source upload and supplied Nebius free-beta confirmation emails. All 32 T2 tests passed remotely, with 17 case reports and 51 verified backups. Cancellation and remote boundary checks passed. See T3_STATUS.md, which supersedes older unverified-remote statements below. Next: T4 controller/model integration; inference funding/license checks remain separate. No paid overage authorized.

Revised 2026-10-02. Planning only; no application or remote probe has been executed by this revision. ORIGINAL_BRIEF.md remains the scope authority. Design choices below are proposals for implementation, not observed capabilities.

## Current evidence and gates

| Item | Evidence | Status |
|---|---|---|
| Developer | User: solo, 2.5 years AI/backend experience, 6–7 hours/day | Known constraint |
| Spending | User: stay within free credits | No out-of-pocket spending authorized |
| Balance | Earlier screenshot: $1 trial, 29 days remaining at capture; grants unconfirmed | Historical observation, recheck before usage |
| Registration/key | User reports joined and key created | Account setup complete |
| Sandbox authentication | Latest user terminal output: auth accepted without disabled warning | Succeeded |
| Sandbox listing | Latest user output: thousands of images returned; catalog truncated at 3,000 | List permission works; previous list-403 resolved |
| Sandbox execution | No execution result supplied | Unverified, not access-blocked by assumption |
| Local CLI in this app | 2026-10-02 invocation fails to locate its Python 3.11 runtime | Local launcher issue; user's PowerShell previously worked |
| Model catalog | User screenshot contains Nano, Super, Ultra, Lightning | Display availability only; API access/pricing not tested |
| Beta pricing | User screenshot says free while in beta | Account terms/limits and coverage still to confirm before workloads |

Do not repeat beta signup or replace the key solely because this app's launcher fails. No credential files need to be read or printed. Capture CLI help from the working terminal if necessary.

## Requirements and contribution

The [official rules](https://nebiusglobalaihackathon.devpost.com/rules), reviewed in this conversation on October 1, specify October 30, 2026, 10:00 PDT (22:30 IST), a runtime Token Factory inference call or qualifying Nebius AI Cloud deployment, and an NVIDIA open model. Repository licenses listed are examples, not an exclusive list. Recheck submission requirements before release; see SUBMISSION_PLAN.md.

Real Token Factory Sandbox execution is an explicit PROJECT requirement regardless of whether the track text independently mandates that product. It cannot silently be replaced by local execution. Both distinct incident families, the full product flow, and B0/B1/B2 remain planned. B3 is optional in the original brief.

Contribution to measure: controlled incident investigation followed by source repair and protected business-contract evaluation under additional declared faults. Do not claim universal repair correctness or established superiority before measurement.

[Microsoft AIOpsLab](https://github.com/microsoft/AIOpsLab) already provides applications, workloads, fault injection, agent orchestration and evaluation; reviewed October 1. IncidentForge's proposed distinction is its integrated source-repair workflow and safety/liveness evidence, not generic tool use or tests. This is a preliminary comparison, not an exhaustive novelty review. Complete a focused primary-source comparison with a competent coding-agent implementation before writing novelty claims.

## Models and spending

Prior planning recorded catalog IDs and prices from https://tokenfactory.nebius.com/model-catalog.md on October 1. Treat these as historical research notes pending verification, not active configuration:

| Candidate ID | Recorded input/output USD per million tokens |
|---|---|
| nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B | 0.06 / 0.24 |
| nvidia/nemotron-3-super-120b-a12b | 0.30 / 0.90 |
| nvidia/Nemotron-3-Ultra-550b-a55b | 1.00 / 3.00 |
| nvidia/Nemotron-3_5-Lightning | 0.06 / 0.24 |

Select one model after exact ID, model license, account availability, tool/structured-output behavior and current price are verified. Keep it identical across comparison variants. Test one selected model first, not every catalog entry. No claim that the largest model is needed or that a cheaper model has adequate quality without a pilot.

Illustrative arithmetic using the recorded Super rate: 300,000 input and 40,000 output tokens cost 0.3*0.30 + 0.04*0.90 = $0.126 per run, before other categories. Ten times those tokens costs $1.26. Neither estimate is a measurement or guaranteed campaign budget. Include probes, development, retries, failures, experiments, storage, exports, rehearsals and December access separately.

Before every remote action, reserve a conservative upper bound against BOTH run and project ledgers. Bound prompt size, output/reasoning tokens, calls, retries and execution duration. Unknown billable limits or prices block the affected operation. Reconcile actual usage, distinguishing provider-reported cost from calculated estimates. Reserve 20% contingency and a separately calculated judging allowance; these percentages do not establish that the project fits the balance. Expired or pending grants are not available credit. Stop before an operation that might exceed funded coverage; no auto-top-up.

## Capability and probe plan

Documentation supports OCI import, image checkpoints, asynchronous operations and metrics ([overview](https://docs.tokenfactory.nebius.com/sandboxes/overview), reviewed previously). It does not prove this fixture works. Read the installed CLI's `contree agent` and command help before execution. CLI syntax/version, SDK deadlines, MCP wrapper defaults and server limits are separate facts.

| Probe | Purpose and bounded acceptance evidence |
|---|---|
| P0 | Verify selected model license, ID, price, actual credit expiry and beta coverage without inference |
| P1 | After execution is started: one bounded model call; record usage and parse result, never key |
| P2 | Tiny structured action/schema pilot with capped correction retries |
| P3-local | Measure actual fixture duration and cancellation locally; do not search long timeouts with sleeps |
| P3-remote | One bounded command on a listed immutable image; then target the measured required duration |
| P4 | Three child processes and real loopback HTTP inside one run, readiness and cleanup recorded |
| P5 | Crash/restart a service while durable state survives; verify process identity and recovery |
| P6 | Export artifacts, verify hashes, check size limits with the smallest representative bundle |
| P7 | Inspect metrics, operation lifecycle, cancellation and terminal-state confirmation |
| P8 | Verify distinct identities, denied protected reads/writes, no elevated privileges and store isolation |
| P9 | Verify commit-history observer, atomicity, reset and harmful controls on the selected backend |

Gate LIST has passed. EXECUTION, COMPATIBILITY, PROTECTED_BOUNDARY and FUNDED_USAGE are separate unpassed gates. Local work can validate logic; it cannot establish a remote gate. One experiment should initially be one orchestrator invocation with child processes, not a claim that daemons survive calls.

Each probe gets a watchdog, request/operation count cap, artifacts, expected outcome and cleanup. A client timeout is not cancellation. Request cancel, verify terminal state, and halt further remote launches if status stays unknown. An in-instance watchdog is useful but not sufficient proof that the platform operation ended.

## Reset and alternatives

Pin image digest and dependency lock. Create fresh run directories/stores; verify initial data, process/socket set, queues, logs and absence of external mutable dependencies. Reset the trusted audit too. Test clean–faulted–clean sequences and concurrent run isolation. Freeze app configuration and record residual OS scheduling nondeterminism. A random seed is not a deterministic thread schedule.

If the required boundary or runtime is unavailable, continue applicable local development and report the exact integration blocker. The original brief's AI Cloud split is a conditional design requiring funded access, meaningful Sandbox work and track alignment. Local-only submission is an UNAPPROVED contingency, not successful completion. In-memory calls do not replace real HTTP. See EXECUTION_BACKLOG.md for early integration checkpoints.
