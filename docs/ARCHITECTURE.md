# IncidentForge: architecture

Updated October 4, 2026. T0-T7 are implemented and the frozen T8 campaign is
reported. ORIGINAL_BRIEF.md governs scope. The sections below preserve the design
contract; the implementation map identifies concrete modules and remaining limits.

## Implementation map

| Responsibility | Current implementation |
|---|---|
| Bounded orchestration and action validation | `src/incidentforge/controller.py`, `action_schema.py`, `investigation.py` |
| Token Factory calls and persistent allocation | `llm.py`, `budget.py` |
| Source edits and evidence | `workspace.py`, `evidence.py`, `records.py` |
| Local/remote workload execution | `backend.py`, `remote_backend.py`, `scripts/contree-execute.py` |
| HTTP services and protected store broker | `fixture/app/service_v2.py`, `fixture/harness/persistence/v2.py` |
| Trusted workload and developer assertions | `probes/run_candidate.py`, `fixture/harness/developer_tests.py` |
| Independent evaluation | `evaluation/verifier.py`, `evaluation/holdout.py` |
| Operator console and recorded frontend | `src/incidentforge/ui.py`, `src/incidentforge/web/`, `site/` |

The service and UI servers use Python standard-library HTTP implementations;
FastAPI was a planning option, not an installed dependency. Services run under
separate Linux identities. The trusted execution image contains evaluation tools;
its candidate-readable bundle excludes them. A separate restricted Docker reader
checks exported protected evidence. Image boundaries and filesystem permissions
must not be confused.

Developer assertions observe declared public HTTP data. Public stock counts can
expose unreleased holds; payment-request identity counts can expose changed retry
keys. Neither is a committed-payment-effect verdict. The protected evaluator
remains responsible for effect safety. Baseline assessment reveals assertions that
already pass before repair; such assertions do not demonstrate defect detection.

See [completion gates](COMPLETION_GATES.md) for unresolved release and reliability
work. No additional end-to-end success rate is implied by this implementation map.


## Workflow and component interfaces

INGEST -> REPRODUCE -> INVESTIGATE -> PATCH -> VERIFY -> REPORT, with bounded returns from VERIFY to PATCH or INVESTIGATE. Invalid bundles stop with a diagnostic report. Budget exhaustion or insufficient evidence yields UNRESOLVED, never a forced patch. B0 uses the same controller/accounting but does not require B1's hypothesis protocol.

| Component | Input -> output |
|---|---|
| Intake | Allowlisted bundle -> validated revision, initial state and public contract |
| Index | Source symbols/imports, textual search, runtime spans and lockfile -> bounded evidence references |
| Investigator | Evidence -> competing explanations, counterevidence and experiments |
| Planner | Question -> controls, intervention, outcomes, reset and limits |
| Execution backend | Pinned fixture + allowed patch + experiment -> operation handle, artifacts, metrics |
| Repair worker | Source/evidence -> diff and developer regression tests |
| Protected evaluator | Clean candidate + private workload -> property results and decision |
| Controller | Validated actions -> authorized operations, state transitions, budgets and cancellation |
| Interface | Run events -> selection, launch/status, hypotheses, experiments, diff, validation and export |

Use one Nemotron-backed worker with role-specific prompts. Initial proposed limits: 4 reproduction attempts, 6 experiment rounds, 3 patch revisions, 1 return to investigation, 2 format corrections per call. All also obey global call/token/execution/time/credit caps. Calibrate on development data before freeze. A model cannot authorize larger budgets. For B1/B2, advance to patch when evidence locates a plausible mechanism and an experiment distinguishes alternatives; contradictions remain visible. Statistical support is not logical refutation of all alternatives.

## Records

All records have schema_version, run_id, record_id and artifact references. Below are required fields; implementation adds schema tests before any agent run. No illustrative success numbers are measurements.

| Record | Required fields |
|---|---|
| IncidentBundle | revision, image digest, lock hash, topology, config, evidence refs, initial-state hash, PUBLIC contract hash, declared gaps |
| Hypothesis | mechanism, symbols, supporting refs, counterevidence, alternatives, predicted signatures, distinguishing experiment, confidence basis |
| ExperimentSpec | question, baseline/reset, intervention, controlled variables, workload, both-outcome predictions, repetitions/reason, limits |
| ExperimentResult | spec hash, backend, reset result, per-repetition observations, completion/completeness, violations, artifacts, resources, interpretation author |
| PatchCandidate | base revision, diff/hash, allowed paths, migration declaration, rationale, developer tests/results |
| ValidationReport | candidate hash, evaluator/version, conditions, per-property pass/fail/not-applicable/unknown, boundary status, costs, decision, limitations |

Decisions: accept_for_review, reject_behavior, reject_patch_invalid, unresolved, invalid_evaluation. Acceptance requires complete evidence, valid boundary, all applicable required properties passing and clean-workload checks. A process exit code or model message never decides acceptance. Full private reports remain evaluator-side during repair; only declared L2 feedback enters the worker.

## Source and deployment layout

```
src/incidentforge/{controller,schemas,llm,index,agent,sandbox,evidence,ui}/
fixture/app/{order,inventory,payment,common,tests}/
fixture/harness/{orchestrator,proxy,persistence,observer}/
contracts/public/
evaluation/{properties,development,holdout,controls}/
probes/
docs/
runs/
```

Host: controller, protected evaluator, model credentials, authoritative result aggregation. Linux execution image: three HTTP services, fault proxy, persistence/observation helper and orchestrator. One fixture image with separately owned stores. No evaluator source, reference solution, history, planning documents or model credentials in worker images. One concrete schedule may be injected only into protected harness storage in an evaluation run.

Python/FastAPI and separate SQLite stores remain the proposed backend. A small local web UI may use server-rendered templates and JavaScript; React is not a requirement. CLI and web share events/actions. Keep ALL requested panels, launch, cancellation/status and export; effort estimates are not automatic feature-removal permissions.

ExecutionBackend must provide prepare, launch, await/poll, fetch_artifacts, cancel, confirm_terminal and metrics. Local and ConTree backends run the same fixture contract; results identify backend and are not assumed equivalent. On Windows, use a verified Linux container/WSL execution path for boundary tests. An ordinary Windows subprocess run cannot prove Linux permission isolation.

## Protected persistence and actual commit evidence

Design proposal requiring an early local feasibility slice: a narrow persistence broker owns each service's SQLite file. Services cannot directly open those files. Each service connects through its own Unix-domain socket; peer UID and socket permissions restrict it to its own store. The broker is a fixture support component, not a fourth business service.

Expose parameterized SQL execution and explicit BEGIN/COMMIT/ROLLBACK transaction sessions against that service's application tables, with ordinary SQLite locking semantics and bounded transaction lifetime. Different sessions permit interleaving. The broker does NOT derive operation keys, deduplicate charges, choose order states, retry business actions, perform compensation or add uniqueness constraints. Correctness remains candidate application work. A faulty SELECT followed later by INSERT can still race; a correct transaction/constraint remains a repair choice.

Trusted triggers capture effect-table inserts into a protected audit table IN THE SAME SQLite transaction, including immutable sequence, effect ID, order/payment intent, amounts and row payload. A rolled-back insert leaves no committed audit effect. Two inserts remain two events even if responses lie. The protected audit and effects are append-only during application execution. The broker enforces permissions using a deny-by-default SQL authorizer and a fixed operation surface, not substring matching. Deny ATTACH, extension loading, audit access, schema mutation, unsafe PRAGMAs and effect UPDATE/DELETE; prevent bypass through triggers/views or nested SQL. Remove arbitrary filesystem and shell operations from this surface. App-owned identity/state tables remain editable as required for repair.

Migrations run before workload under the trusted runner, through a separate validated path. Support new app tables and indexes/unique constraints; protect effect/audit schema and trusted triggers. Reject unsupported migration forms explicitly. No raw trusted executescript over candidate input. Constraints failing on seeded data are a rejected migration, not silent data cleanup. Existing effect deletion is forbidden; refunds are separate effects. This policy must not accidentally repair the original fault.

The definition of a synthetic committed payment effect is an authorized committed insert in the canonical payment effect table. This is a declared simulation boundary, not a claim about a real bank. Candidate files called 'charges' elsewhere are not financial effects. Missing canonical effects fail the contract. Validate identity/amount association against independently registered test requests; reject unknown or misattributed effects. Zero-value or unassociated extra charges cannot be hidden from counts.

Read audit data using trusted broker export/SQLite backup after transactions are bounded and quiesced. Do not copy only a live main database file with WAL omitted. Per-store backups are transaction-consistent; cross-store cuts require a declared quiescence barrier. Retain committed audit history even when a response is lost or a service crashes. Capture broker/observer failures as invalid evaluation, not candidate success.

Evidence roles: audit = committed effect history; proxy = actual HTTP exchanges; snapshots = sampled durable state; service logs = untrusted narrative. These sources are not all independent truths. Count effects by trusted audit, never by response status. A response-only barrier can schedule response loss but does not prove commitment; the trusted commit event does. Barrier alignment and audit atomicity are acceptance tests.

## Isolation and boundary gates

Separate UIDs for Order, Inventory and Payment; a separate trusted broker/harness identity; protected run directories and audit files. Drop supplementary groups and capabilities; enforce no-new-privileges, no setuid escalation, no ptrace/process-memory access and restricted proc exposure. Services cannot read schedules, signing material, other stores or trusted artifacts. Root ownership alone is insufficient if candidate processes retain capabilities. Restrict external egress at the execution boundary; private localhost ports alone are not a security control.

Proxy coverage matters to network interpretation and fault delivery. Where direct interservice sockets cannot be blocked, do not claim complete proxy observation; use audit history for effects and mark experiments with unverifiable fault delivery inconclusive. Missing socket observations cannot prove absence of bypass. Verify the intended topology through explicit tests rather than hidden port numbers.

The model only issues schema-validated tools mediated by the controller, with no host shell or host filesystem access. Candidate code runs only inside the isolated fixture. Patch allowlists reject traversal, symlinks, renames and writes outside app paths. Allowlist checks supplement runtime restrictions. Protect artifact extraction against traversal/symlinks, bound sizes, and parse downloaded databases/artifacts in a restricted reader. Publishing the repository must not expose host credentials or let runtime agents fetch private cases.

Protected validation is BLOCKED if required file/process/broker restrictions cannot be enforced. Do not claim protected evaluation merely because grading happens on the host. HMAC is not required initially: protected immutable capture plus trusted extraction/hashes is simpler. Hashes detect changes only when their origin is trusted.

Required boundary tests: denied schedule/key/audit reads; denied harness writes from running candidate code; denied other-service store access; denied audit/effect alteration and trigger removal; SQL indirection bypass rejection; denied host/egress access; denied process-memory inspection; protected export integrity; incomplete run cannot pass. Check explicit denial and unchanged protected contents. Also demonstrate that two legitimate bad-app inserts STILL produce two audited effects: protection must not solve deduplication.

## Evidence, cost and stop behavior

Trusted controller appends sequenced events with UTC time, actor, kind, payload hash and refs. Store large raw artifacts by hash, preserving contradictory evidence. Separate public/worker feedback from full evaluator manifests. Record model/configuration, prompts/tool calls, source and diff hashes, backend/image/dependencies, fixture/evaluator/schedule identities, reset/boundary checks, audit/proxy/log artifacts and resource accounting. See EVALUATION_PLAN.md.

Reserve budget before calls; all retries count. Cancellation requests are followed by terminal-state confirmation; unknown operations halt new launches. Candidate-caused hangs/crashes count as candidate failures. Infrastructure failure needs positive evidence. Unknown causality remains unknown and appears in end-to-end denominators. Complete useful unresolved reports with the best next experiment, never unsupported certainty.
