# Hackathon project brief: IncidentForge — autonomous incident investigation and verified code repair

I want to build this project for the **Coding and Agentic Engineering Track of the Nebius Global AI Hackathon**. My goal is a technically substantial system that investigates a distributed application incident, constructs a reproduction, performs controlled experiments, proposes source patches, and checks whether those patches preserve the application's required behavior.

Treat this as a complete, standalone project brief. **Begin with research and planning. Do not implement, provision resources, or launch paid workloads until I explicitly start execution.** I want an ambitious engineering project with a credible end-to-end demonstration. Challenge unsupported assumptions and propose a staged plan that fits my actual time and resources.

## 1. Product and contribution

The intended user is a backend engineer responding to an incident. They provide a supported incident bundle: source revision, dependency locks, topology, runtime configuration, selected logs and traces, synthetic initial data, and a behavior contract. IncidentForge returns:

- An executable reproduction and its limitations.
- Ranked explanations linked to observations and distinguishing experiments.
- A reviewable source patch and developer regression tests.
- Independent behavioral validation, including rejected candidate explanations.
- A reproducible evidence bundle with time and resource consumption.

The hard problem is deciding whether a repair restores intended behavior. Removing retries can eliminate duplicate-payment errors while silently losing orders. An agent that only checks whether the original stack trace disappeared can accept a harmful repair.

My proposed contribution is the combination of **incident reconstruction, hypothesis-driven interventions, and protected verification under unfamiliar fault schedules**. This combination must be assessed against current prior art. [Microsoft AIOpsLab](https://github.com/microsoft/AIOpsLab) already provides microservice environments, fault injection, workloads, telemetry, and agent evaluation. Generic execution loops, AST retrieval, and dashboards are established techniques. Do not claim that existing coding agents never run tests or use feedback.

Use “validated under declared conditions,” because finite experiments cannot prove a patch universally correct. The initial deliverable is a patch for human review. “Self-evolving” is a later research direction: saving incident memories or revising prompts alone does not demonstrate general improvement.

## 2. Hackathon constraints to verify

As checked on September 30, 2026, the official rules set submission for **October 30, 2026, 10:00 a.m. PDT**. They require a functional application with a runtime Token Factory call or Nebius AI Cloud deployment, plus an NVIDIA open model. The coding track currently refers to writing, running, and testing code in Token Factory. Submit a public repository with an accepted open-source license, setup instructions, integration details, a working demo/test build, project description, category, platform feedback, and a public YouTube video shorter than three minutes. Disclose pre-existing work and changes; provide English materials or translations. Keep judging access available through December 15. Implementation, design, impact, and idea quality are equally weighted. Recheck all eligibility and submission provisions before finalizing the plan. [Official rules](https://nebiusglobalaihackathon.devpost.com/rules)

I specifically want real **Token Factory Sandbox execution** and a Nemotron model in the reasoning/coding path. The current track wording should not be paraphrased as an explicit rule requiring Sandboxes. Verify model IDs, account availability, quotas, licenses, and actual API behavior; do not invent a Super or Ultra endpoint.

## 3. Concrete application and first incident

Build an order-processing application with three communicating services:

| Service | Responsibility |
|---|---|
| Order | Accept requests, coordinate processing, maintain order state, and recover interrupted work. |
| Inventory | Reserve and release stock with durable operation identity. |
| Payment | Record synthetic charges and refunds with durable deduplication. |

Use real HTTP requests, separate service state, retries, and process restarts. Synthetic payments are enough. The initial fixture can run all three processes inside one environment; Kubernetes is optional later.

First failure: payment commits a charge, its response is lost, the order service retries, and a defect permits a second charge. The incident bundle includes incomplete evidence of the symptoms. The agent must investigate the checked-out code and observations. It should not receive the hidden bug identifier, reference patch, or exact benchmark fault schedule.

Plausible explanations include missing propagation of the request identifier, a non-atomic deduplication check, state kept only in memory, and retry behavior inconsistent with the downstream API. Experiments should distinguish them. Holding identity constant while varying concurrency can expose a race; adding a restart can expose volatile deduplication state.

A second incident should require a distinct mechanism or an interaction between services. Candidate families are concurrent duplicate requests, restart between durable state transitions, and delayed compensation. Add families only after one complete incident-to-patch workflow works.

## 4. Behavioral contract and repair validity

Define business properties before constructing the agent:

- A logical order cannot produce multiple committed charges for the same intended payment.
- A confirmed order has the required charge and stock reservation.
- Valid accepted orders complete successfully after bounded transient faults cease, subject to declared business preconditions and a measured recovery bound.
- Legitimate business rejection reaches the correct terminal state and releases or refunds resources as specified.
- Inventory remains consistent and never becomes negative.
- Duplicate requests preserve the same business outcome without introducing additional effects.

Separate **safety** properties, such as avoiding duplicate charges, from **liveness**, such as eventually completing eligible orders. Merely cancelling every order must fail the contract. So must returning success without the required durable effects.

Construct intentionally bad candidate repairs for verifier development: disable retries, always return success, cancel all orders, deduplicate only in memory, or use a race-prone check followed by an insert. The evaluator should reject these audited cases. Passing these checks establishes useful coverage, not complete verifier soundness.

The demonstration must label manually constructed bad patches as verifier fixtures. It must not pretend the live agent independently generated them.

## 5. Execution and sandbox design

[Token Factory Sandboxes documentation](https://docs.tokenfactory.nebius.com/sandboxes/overview) describes isolated environments, OCI image import, checkpoint branching, asynchronous operations, and resource metrics. These capabilities make alternative patch experiments plausible, but actual application compatibility needs confirmation.

Prefer one imported OCI image containing the three services, dependencies, a workload runner, and an application-level fault proxy. The proxy can delay or drop a response after a named commit event. A controller can restart a service at a declared barrier. This avoids depending on privileged packet filtering.

Verify multi-process execution, localhost connectivity, storage, timeouts, cancellation, export limits, and SDK versions before choosing the implementation. Do not assume Docker-in-Docker, GPUs, cross-sandbox networking, or live process-memory snapshots.

A checkpoint might preserve files without preserving running processes, sockets, or consistent database state. Prefer quiescing services, exporting state, and reconstructing from a versioned fixture when necessary. All mutable experimental state must be inside the reset boundary. A rollback of one service does not reset other services automatically.

Record logical events and synchronization barriers for replay. A random seed alone cannot reproduce an arbitrary OS thread schedule. Repeat experiments where residual nondeterminism remains and state the limits.

If sandbox capabilities cannot support the integration fixture, assess Nebius AI Cloud for that portion while retaining meaningful sandbox code execution. Document the split and verify track alignment before committing to it.

## 6. Architecture and component contracts

Use an explicit workflow: `INGEST → REPRODUCE → INVESTIGATE → PATCH → VERIFY → REPORT`. Bounded loops return to investigation or patching when evidence warrants it. A deterministic controller enforces budgets, allowed tools, schemas, cancellation, and stop conditions.

| Component | Main contract |
|---|---|
| Intake | Validate the bundle, source revision, topology, synthetic state, and behavior specification. |
| Evidence store | Append observations, commands, model decisions, code changes, costs, and experiment outcomes. |
| Repository index | Combine symbol/import information, text search, runtime spans, and dependency evidence. |
| Investigator | Produce competing hypotheses with supporting and contradicting evidence. |
| Experiment planner | Specify intervention, controls, expected result, reset state, and budget. |
| Sandbox adapter | Create environments, execute commands, branch states, collect artifacts, and terminate jobs. |
| Repair worker | Modify permitted source and add developer-visible regression tests. |
| Protected evaluator | Apply patches to clean instances and assess external properties and workloads. |
| Decision controller | Continue, reject, accept for review, or stop with an unresolved report. |
| Interface | Present incident timeline, hypotheses, experiments, diffs, validation, and costs. |

Start with one Nemotron-backed worker operating in distinct roles. Multiple roles do not require multiple models. Add parallel candidate branches only after serial execution and accounting work reliably.

Define logical records before implementation:

- `IncidentBundle`: revision, image/dependency identity, topology, evidence, initial-state reference, contract.
- `Hypothesis`: mechanism, relevant symbols, evidence references, counterevidence, proposed distinguishing experiment.
- `ExperimentSpec`: baseline state, intervention, controlled variables, workload, observation expectations, limits.
- `ExperimentResult`: actual observations, exit status, violations, artifacts, resources, interpretation.
- `PatchCandidate`: base revision, diff hash, permitted files, migration requirements, rationale.
- `ValidationReport`: evaluator version, tested conditions, failures, regressions, decision, limitations.

AST indexing is an aid to context selection. Dynamic dependencies require runtime and textual evidence too. Store concise structured findings with links to raw artifacts so context compression does not erase contradictory evidence.

## 7. Verification and information separation

Maintain three layers:

1. **Agent development checks:** visible and editable tests used for iteration.
2. **Protected development evaluation:** immutable business checks that return useful feedback during repair.
3. **Final held-out evaluation:** frozen incidents and schedules used only after the candidate system is frozen.

The evaluator belongs to a separate controller boundary. Private tests placed in the agent's readable workspace are not private. Enforce access through workspace scope, credentials, process boundaries, and allowlisted patch paths. Model instructions alone are insufficient.

The agent may edit application files and designated local tests. It cannot alter authoritative grading logic, protected fault schedules, reference solutions, or accounting. Explicitly decide whether schema migrations are supported and how they are applied to clean instances.

The evaluator should check durable effects and trusted external observations. Agent-written logs claiming “all passed” cannot decide acceptance. Public repository transparency remains compatible with evaluation isolation: freeze and identify evaluation artifacts, keep them outside the agent context during runs, and publish reproducibility materials after measurement when appropriate.

Once final feedback is used to tune the system, those cases become development data. Record this and replace the final holdout before claiming independent performance.

## 8. Evaluation and evidence of value

Compare against a competent baseline using the same Nemotron model, available tools, incident evidence, source state, and resource limits:

- **B0:** Generic coding loop: inspect evidence, patch, execute checks, repeat.
- **B1:** Add explicit competing hypotheses and controlled interventions.
- **B2:** Add protected behavioral feedback during repair.
- **B3, optional:** Add bounded parallel patch branches.

Evaluate every variant with the same independent final evaluator. Use ablations that change one mechanism where practical. Budget both tokens and execution; extra candidate attempts must be visible in comparisons.

Plan initially for several incident variants across two or three fault families. Select actual counts and repetitions after a cost probe. Distinguish independent agent runs from repetitions of one patch under different schedules. Final cases should vary mechanisms or implementations where possible; changing only seeds supports a narrower generalization claim.

Measure reproduction rate, valid repair rate, wrong-repair acceptance, clean-workload regressions, lost orders, duplicate effects, time to reproduction, total resolution time, tokens, execution resources, and cost. Use injected ground truth for diagnosis assessment without revealing it to the agent.

Predeclare runtime limits, allowed regressions, comparison criteria, and sample-size rationale before final runs. Small samples support descriptive findings with uncertainty. Severe behavioral violations should not disappear inside an average score. Record failed and unresolved incidents, not only successful demonstrations.

Each run needs source and patch hashes, image digest, dependencies, model/configuration, fixture version, fault schedule, event trace, evaluator version, command outputs, and resource accounting. Reproducibility is part of the product.

## 9. Product demonstration

The user selects a supported incident, sees the failing behavior, launches an investigation, inspects hypotheses and experiment results, reviews a patch, and exports the evidence bundle. Provide a bounded fixture so judges can try the system without supplying their own infrastructure.

An effective short demo shows a failure, its reproduction, an experiment that separates two explanations, a harmful candidate rejected by behavioral checks, and a final patch/report if achieved. Recorded runs can supplement a live run when clearly labeled. Display measured results for declared conditions; do not imply universal correctness.

The difficult engineering is in state reset, meaningful fault schedules, evidence-guided repair, and trustworthy evaluation. The UI should make these visible without consuming the entire implementation budget.

## 10. Milestones and gates

| Stage | Required evidence before expanding scope |
|---|---|
| Feasibility | Current rules, model/API access, sandbox capability matrix, prior-art comparison, and budget assumptions. |
| Testbed | Three services, one faulty revision, repeatable incident, clean reset, and a verifier rejecting audited harmful fixes. |
| Baseline | Real Nemotron tool calls, source edits, sandbox execution, and a recorded generic-agent baseline. |
| Investigation | Structured competing explanations and an intervention that distinguishes at least two. |
| Repair | Candidate patch applied to a clean instance, protected feedback, bounded retries, and useful failure reports. |
| Evaluation | Frozen system and task split, matched comparisons, costs, regressions, and uncertainty. |
| Submission | Testable demo, licensed repository, documentation, requirements checklist, and short video. |

Propose a calendar after checking my available hours and team size. Protect time for evaluation and submission. If behind schedule, reduce incident families, framework complexity, and parallelism while retaining one complete investigation-and-repair path.

Defer production deployment, unrestricted repository support, learned policy updates, many programming languages, and elaborate infrastructure orchestration. Those are future extensions once this system demonstrates value.

## 11. What I want from the new chat first

Ask the few questions that materially change the plan: team size, engineering experience, weekly hours, credits/spend limit, sandbox access, and preferred stack. Continue planning with explicit provisional assumptions where possible.

Then provide:

1. A current source-backed feasibility and prior-art assessment.
2. A precise contribution statement and measurable success criteria.
3. Architecture, trust boundaries, component interfaces, and proposed repository layout.
4. A concrete first incident specification and protected behavioral contract.
5. A prioritized implementation backlog with dependencies and milestone gates.
6. Baseline, ablation, holdout, and reproducibility plans.
7. Resource estimates with assumptions, failure risks, and fallback choices.
8. A hackathon submission checklist and demonstration script.

Separate verified facts from design proposals and estimates. Do not start implementation yet. My separate autonomous RL research project may later use new training incidents from this platform, but it must not become a dependency of the hackathon or consume its held-out evaluation cases.
