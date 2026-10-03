# T3: Nebius Sandbox compatibility — PASS

October 3, 2026 (IST). The user explicitly approved the reviewed upload. The supplied Nebius emails confirm active access, standard Token Factory key plus project ID authentication, free Sandbox execution while in beta during the hackathon, and up to 50 concurrent operations.

## Remote results

| Operation | Outcome |
|---|---|
| Minimal compatibility: 01a0ffae-2ff6-74e5-ba0c-b73f3ace711f | SUCCESS, exit 0, 1.379 seconds; three processes, distinct UIDs, loopback HTTP, protected read denial and durable SQLite restart |
| Cancellation: 01a0ffb0-5fbe-7739-9338-612658229bc4 | Explicitly cancelled; terminal CANCELLED confirmed |
| Full T2: 01a10012-9533-712c-972c-c89c7851d4af | SUCCESS, exit 0, not timed out, 29.868 seconds; 32 tests, zero failures/errors/skips |

Seventeen case reports: seven accepted reference/evidence cases and ten rejected negative controls. All five original harmful repairs were rejected for their required violations. Reference compensation restart, cancellation with an uncertain payment, refund/release replay and inventory history checks passed remotely.

Boundary receipts passed for private evaluator/control reads, protected store reads, other-service broker access, source writes, root escalation, capabilities, process-memory access and external egress. Full-suite request and operation metadata confirm networking.enabled=false. The earlier synthetic probes used CLI defaults and do not establish egress isolation.

## Provenance

- Input image UUID: 4fa16c8f-62a9-35a4-a4ea-07b7e8cd44ae, listed as python:3.12-slim.
- Remote Python 3.12.13, Linux 7.0.6, glibc 2.41.
- Full-suite result image: 3cad0f9f-3d95-40d8-a2aa-96657454dd26.
- Uploaded source matched all 32 entries in the user-reviewed manifest. No credentials, planning documents, original brief, Git history or previous run artifacts were uploaded.
- Private evaluator/control code resides behind the trusted harness boundary, outside candidate-visible bundles.
- Evidence ZIP SHA-256: 71447934aa4b199874a87db41c066ca585dc7d922c18aa6ba71bf44b0ba47eb6.
- Downloaded archive matched the remote digest. A restricted, network-disabled local Docker reader verified archive paths/size bounds, all 17 manifest hashes, boundary receipts, all 51 database hashes and all 51 SQLite integrity checks.
- All 32 recorded remote source hashes matched the uploaded archive. Evidence was extracted only after verification; databases were not parsed on the host.

Evidence: runs/t3-remote-t2/ contains launch/operation records, source archive, evidence.zip, extracted reports, verification.json and ledger.json. Initial probes are in runs/t3-remote-capability/.

## Lifecycle and costs

The full suite had a 120-second server cap and 100-second internal test cap. SDK dispatch disables unsafe retries and records uncertain dispatch outcomes instead of retrying blindly. All three launched operations have known terminal states; none remains running or unknown. Result checkpoints remain for reproducibility under provider retention policy.

CLI 0.9.4 works outside the restricted local launcher. Its first detached command waited on inherited stdin even after remote completion; the exact operation UUID was recovered from session history, terminal success confirmed, and the stale local command interrupted. SDK dispatch explicitly closes stdin. The CLI does not expose network disable; installed contree-client 0.4.0 supports InstanceNetworking(enabled=False).

Provider records contain raw cost metrics 0.00486375 and 0.15381902. Units/billing meaning remain unverified; these are not asserted USD charges. Free-beta coverage is confirmed by the support email. No inference/model calls were made. Model credits, license, pricing and judging access remain separate gates.

## Limits and next stage

This establishes T3 compatibility under declared development conditions, not universal sandbox security, final holdout performance or autonomous repair. Direct interservice sockets remain reachable; complete proxy observation is not claimed. Required fault delivery is checked against committed audit history.

Next is T4: bounded controller/evidence/model integration and the first B0 run. Build local schemas/accounting first; verify model license, current price and usable free inference credits before any model call. IF-002 defective variant, full interface, comparison campaign and submission remain planned.
