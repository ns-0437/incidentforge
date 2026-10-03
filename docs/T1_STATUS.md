# T1 local fixture status

October 2, 2026. The original brief and full application contract remain unchanged.

Implemented three real HTTP service processes under distinct Linux UIDs, with
separate broker-backed SQLite stores. Order writes durable workflow phases before
downstream calls. Payment records its deduplication result atomically with the
charge; the trusted broker records effects but deliberately allows duplicate
logical intents under different operation keys.

IF-001 is an actual post-commit response loss. The trusted proxy correlates the
response charge ID, logical intent and request key with committed audit history
before dropping the connection. The faulty Order generates a fresh retry key;
the reference control derives a stable key from the order identity.

## Verification

Initial run `runs/t1-linux-20261002-170147` failed on a naming collision between
the HTTP helper and its imported module. Corrected the import. Next run
`runs/t1-linux-20261002-170309` passed 33 tests, zero skips, in 64.453 seconds,
including all 25 T0 regressions and eight T1 integration checks.

Saved scenario results: clean = one charge; unpatched IF-001 = two charges for
one confirmed order; manually authored reference = one charge despite retry.
The duplicate case repeated three times; clean-faulted-clean produced [1,2,1].
Order and Payment restarts retained correct reference recovery and deduplication.
Decline released inventory; insufficient stock produced no charge; repeated
client requests replayed and conflicting payloads returned 409.

Final acceptance: `runs/t1-linux-20261002-170538/report.json` is PASS: 34 tests,
zero failures/errors/skips; 57.197 seconds for tests and 67.716 seconds including
the three evidence exports. Inventory restart preserved holds and deduplication;
repeated release restored stock exactly once. All writers, including brokers,
are stopped before snapshot export. All nine databases passed integrity checks.
The disposable Docker container and evidence volume were removed successfully.
The original brief SHA-256 remains
`4a2d5f78d37fdfd9bcd450b32374533f146e66c28eecdaf55488d6dfe9bb29af`.

## Evidence and limitations

The runner pins the cached local image by ID, disables external networking,
mounts only fixture/tests/probes read-only, bounds resources and removes its own
temporary container/volume. It exports runtime/source hashes, test logs, three
scenario directories, service/proxy logs, terminal orders and integrity-checked
SQLite backups with hashes. No model or remote Sandbox calls; no credits used.

This is a fixture gate, not full behavioral verification or an autonomous repair.
Single-item quantities and integer cents are the current T1 input slice. T2 must
complete item/currency canonicalization, cancellation/refunds and reconciliation,
inventory mutation auditing, retry backoff, the protected evaluator, public
contract export, migration policy implementation and all five harmful controls.
ConTree execution and boundary compatibility remain untested. Reference controls
and private authoring material must be excluded from eventual runtime agent input.
