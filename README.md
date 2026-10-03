# IncidentForge

Autonomous incident investigation and behavioral repair validation. The original
scope is preserved in `docs/ORIGINAL_BRIEF.md`.

## Current implementation

T0 through T7 are implemented as development stages. The bounded Nemotron controller
supports both incident families, B0/B1/B2 protocols, evidence records, patch review,
and a local launch/cancel UI. Generated repairs passed 6 IF-001 and 8 IF-002
protected development cases on Nebius Sandbox. These are not final comparison results.
See `docs/PRE_T8_STATUS.md` for current evidence, failed pilots and remaining gates.

Start the local UI with `python scripts/serve-ui.py --port 8765` and open
http://127.0.0.1:8765. Recorded history is free to browse. UI launches use Docker.

For an explicitly budgeted live Sandbox run:

```powershell
python scripts/run-t4.py --live --variant B2 --incident IF-002 --backend contree
```

This uses the existing ConTree profile and installed SDK Python. Set CONTREE_PYTHON
if that runtime is elsewhere. Docker is still required for independent exported
evidence verification. The persisted $0.20 cumulative inference allocation is enforced;
unknown usage or execution prevents redispatch. Do not delete unresolved guards.

- Order, Inventory and Payment run as separate Linux processes and UIDs with
  separate durable stores. Order recovers pending work after restart.
- IF-001 drops a Payment response only after correlating it with a committed
  audit effect. The faulty retry generates a new key and duplicates the charge.
- A manually authored reference strategy reuses the logical payment identity.
  This is a test control, not an agent-generated repair.

- Explicit SQLite transaction sessions through a protected broker.
- Charge audit captured by a trusted trigger in the same transaction.
- SQL authorizer denies audit access, effect deletion/update, DDL, unsafe PRAGMAs,
  extension loading and attached databases.
- The broker intentionally permits duplicate payment effects. It does not fix
  operation identity, retry logic or application deduplication.
- Linux Unix-domain transport authenticates kernel peer UIDs and bounds session
  lifetime, requests, output, SQL length, query steps and connection count.

The fixture and local controller use Python 3.12+ without third-party dependencies.
Remote execution additionally uses the installed ConTree SDK environment.

## Run the portable checks

From this repository root:

```powershell
python -m probes.run_t0 --output runs/t0-local
```

Windows can validate SQLite/transaction behavior and actual abrupt writer-process
death. Linux UID/socket/isolation tests are explicitly skipped on Windows, and
the report is PARTIAL. Skips are not evidence that isolation works.

## Run the Linux acceptance gate

With a working Docker Desktop Linux engine:

```powershell
.\scripts\run-t0-linux.ps1 -PullImage
```

For the T1 fixture plus all T0 regressions, using the cached image:

```powershell
.\scripts\run-t0-linux.ps1 -Stage t1
```

T1 also exports clean, unpatched IF-001 and reference-control scenarios with
proxy logs, terminal orders, protected effect history and SQLite backups.

Run the T2 contract, migrations, private verifier and harmful-control gate:

```powershell
.\scripts\run-t0-linux.ps1 -Stage t2
```

T2 uses a separate versioned service/schema so the T0/T1 regression fixtures
remain reproducible. Candidate processes receive only copied app code and
`contracts/public/CONTRACT.md`. Private harness, tests and evaluator mounts sit
behind a root-only directory. Case exports contain manifests, database hashes,
boundary receipts and per-property validation reports. They are private
development evidence, not material to include in a model's incident bundle.

The flag downloads an ordinary local Python container image if needed. It does
not create cloud resources. Subsequent runs can omit it. The script resolves the
image to its local immutable ID and records image metadata. It runs with no
network, a read-only root filesystem and source mounts, bounded memory/processes,
no-new-privileges and only the launcher capabilities needed for UID separation.
Services drop all capabilities before execution. Evidence is copied after the
test exits, and only this test's disposable container and uniquely named evidence
volume are removed. No volume or image pruning is performed.

Reports contain interpreter/SQLite/platform versions, source hashes, counts,
failures/skips, duration and limitations. Logs and reports are under `runs/`.
No credentials belong in this repository or its evidence.

## Scope and limits

The T0 schema is a payment-effect test fixture plus an independent order store;
it is not the final application schema. Runtime migrations are intentionally
unsupported until a separate trusted migration interface is implemented and
tested. Application-owned state/claims can change; canonical effects and audit
cannot. Broker initialization only creates new stores and never overwrites one.

The test suite is selected boundary coverage, not a proof against arbitrary
malicious code or kernel exploits. Local Docker results do not establish ConTree
compatibility. Full application readiness, topology/fault delivery, inventory
history, schema migrations and complete behavioral properties come in later gates.

T1 preserves its original single-item slice. T2 adds canonical multi-item/currency
payloads, durable cancellation and refunds, transaction-level inventory history,
bounded retry backoff, public bundle export and harmful-repair controls.
Structured pre-run migrations allow app tables and indexes while protecting
canonical effect/audit schemas. The original contract remains unchanged.

See `docs/T0_STATUS.md`, `docs/T1_STATUS.md` and `docs/T2_STATUS.md` for measured status, and the execution backlog for
the next gate. No inference or remote Sandbox workload is used by these tests.
