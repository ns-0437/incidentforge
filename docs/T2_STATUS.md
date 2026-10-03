# T2: local contract and protected development verification

October 3, 2026 (IST). Original scope and brief unchanged. T2 introduces a separate
v2 service/schema; T0/T1 remain available as regression fixtures.

## Implemented

- Canonical multi-SKU quantities, duplicate SKU aggregation, integer cents and
  currency; request replay/conflict semantics.
- Durable Order phases, bounded retry backoff, cancellation serialized with
  confirmation, reconciliation of a lost charge response, append-only full refunds
  and release of held inventory. Recovery includes pending compensation.
- Separate Linux service UIDs/stores. A candidate-visible bundle contains only
  app modules and the public contract. Root-only mounts hide evaluator, controls
  and tests. Previous completed control bundles become root-only as well.
- Atomic protected payment audit and app-state mutation history with transaction
  IDs. Inventory properties replay every committed transaction; final snapshots
  cannot conceal earlier violations. Denied operations are recorded outside the
  rolled-back application transaction.
- Structured, atomic pre-run migrations for app tables and indexes/uniqueness.
  Arbitrary SQL, protected schema alterations and unsupported forms are rejected;
  failed uniqueness creation preserves seeded data and rolls back prior DDL.
- A bounded, read-only protected evaluator over quiesced SQLite backups and a
  trusted workload registry. Responses do not define expected outcomes or payment
  effects. Missing boundary receipts, wrong hashes or incomplete evidence cannot
  pass. Malformed candidate state is a rejected behavior, not a verifier crash.

## Measured controls

Each harmful source is independently derived from the reference. These are
authored controls, not agent-generated patches.

| Case | Required observed rejection |
|---|---|
| Unpatched IF-001: fresh retry identity | P1 duplicate committed charge |
| Disable retries and recovery | P3 eligible order stranded |
| Always success without payment | P2 invalid confirmation; decline also violates P4 |
| Cancel every order | P3 eligible order lost |
| Memory-only deduplication | P1/P6 duplicate after actual Payment restart |
| Race-prone claim | P1/P6 duplicate under a two-request interleaving barrier |
| Delete committed-effect representation | Broker denies/rolls back, logs attempt; P7/P3 reject |
| Temporarily negative inventory, then restored | P5 rejects committed historical violation |
| Malformed durable app state | Contract-state rejection without evaluator crash |

Reference cases cover clean/replay/conflict, stock contention, decline/stock
rejection, Payment restart after response loss, cancellation with an uncertain
charge and Order restart, compensation crash before release, and payment/refund
concurrency/restart. Inventory replay/release/conflict is checked across restart.

Initial T2 run: `runs/t2-linux-20261003-023423`, 29 tests passed.
Expanded run: `runs/t2-linux-20261003-023804`, 31 tests passed, zero skips;
16 case reports, 75.968 seconds including exports. The separate T0/T1 regression
run `runs/t1-linux-20261003-023805` passed all 34 tests, zero skips, 74.065 seconds.
Final acceptance: `runs/t2-linux-20261003-024057/report.json` passed all 32 tests,
zero failures/errors/skips, in 75.164 seconds. Seventeen case reports: seven
accepted reference/evidence cases and ten rejected negative controls. All five
original harmful fixes were rejected for their required property violations.
After export, all 51 backup hashes and SQLite integrity checks, all 17 manifest
hashes and all 30 recorded source hashes were independently rechecked. Temporary
test containers and evidence volumes were removed. Original brief SHA-256 remains
`4a2d5f78d37fdfd9bcd450b32374533f146e66c28eecdaf55488d6dfe9bb29af`.

## Evidence and judgment

Per-case manifests record independent expectations, observed responses, process
start identities, fault/commit correlations, bundle hashes and quiesced backup
hashes. Validation reports record boundary checks and P1–P7 results. A property
not exercised by a case can be marked not_applicable; acceptance is under those
declared conditions. Hash provenance comes from the trusted local runner, not
from candidate-provided hashes. Logs are supporting narrative, not commit truth.

Development recovery waits are bounded test settings, not calibrated final
benchmark deadlines. This is finite local control coverage, not a security proof,
autonomous repair measurement or B0/B1/B2 comparison. The race schedule deliberately
forces the check/commit gap so its rejection is based on an observed duplicate.
Direct service sockets remain reachable inside the fixture: no complete proxy
coverage claim is made; required fault delivery is checked explicitly.

No model/cloud/Sandbox calls and no credit spending. Next gate is T3: actual
ConTree compatibility and boundary checks after free execution coverage and caps
are established. IF-002's authored defective variant remains T6; T2 verifies the
reference compensation behavior it will need. Final holdouts, runtime bundles,
agent tool/patch mediation, interface and judging access remain in their planned
later stages.
