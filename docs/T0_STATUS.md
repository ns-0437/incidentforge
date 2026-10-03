# T0 local feasibility: PASS

Updated October 2, 2026. User authorized local implementation and verification.

## Measured result

All 25 tests passed on Linux, zero failures/errors/skips, in approximately 12 seconds.
Evidence: runs/t0-linux-20261002-164933/report.json and tests.log.
Runtime: Python 3.12.15, SQLite 3.46.1, Docker Desktop Linux/WSL2.
Image metadata and immutable identity are recorded alongside the report.
Earlier Windows run: 16 portable checks passed, 9 Linux-only checks skipped.

## What passed

Atomic effect/audit commit and rollback; duplicate effects remain possible for a
faulty application; application-owned claims can implement atomic deduplication;
SQL tampering and replacement attacks are denied; coherent WAL backup; independent
reset; real writer-process death before/after commit; client disconnect rollback;
broker SIGKILL/restart; wrong-UID socket denial even with permissive socket mode;
separate-store access denial; protected schedule/harness/process-memory denial;
zero candidate capabilities and no-new-privileges; idle/slow-byte lifetime bounds;
no external route in the isolated container.

## Failure found and corrected

First Linux run failed at broker startup because socket chmod followed chown while
CAP_FOWNER was deliberately absent. Set mode before transferring ownership instead
of adding privileges. Test setup now preserves stderr on readiness failure and
registers cleanup even when setup fails. The wrong-UID control independently tests
SO_PEERCRED by first returning ownership to the trusted launcher before relaxing
socket permissions. Failed-run evidence is retained in runs/t0-linux-20261002-164754.

Docker startup issue was resolved before this run, confirmed by the user's engine
output and the successful local execution. Both test containers and their uniquely
named evidence volumes were removed by the runner and cleanup was verified. The
Python image remains cached for reuse. No unrelated Docker projects were changed.

## Limits and next gate

This is selected local prototype coverage, not a complete evaluator or proof
against arbitrary attacks. Real three-service HTTP topology, inventory history,
migration interface, fault-delivery coverage and full behavioral checks are next.
ConTree execution and its permissions must be tested separately before remote
protected-validation claims. No inference, cloud workload or ConTree execution
was run; no paid service used. Only a public local Python image was downloaded.

Next: T1 three-service fixture, deterministic IF-001 response-loss reproduction,
clean reset, and a negative/positive reference pair, preserving the original scope.