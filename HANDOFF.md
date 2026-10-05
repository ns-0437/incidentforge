# Handoff

**State, October 5, 2026.** HEAD `c9ab37f`, working tree clean, repository private.
`docs/ORIGINAL_BRIEF.md` unchanged at sha256 `4a2d5f78…29af`. Frozen T8 results and
historical evidence untouched.

## Implemented

Three HTTP services with separate durable state and a trusted SQLite persistence
broker; IF-001 duplicate payment and IF-002 stranded compensation; Nemotron via
Token Factory and real Sandbox execution (recorded, not live in tests); bounded
controller with investigation, allowlisted edits, authored regression tests,
freeze and independent verification; protected evaluator; operator console with
launch, status, cancel, review and export; curated static replay.

## Latest results

Run [37289680131](https://github.com/ns-0437/incidentforge/actions/runs/37289680131),
all three jobs green: portable 243 collected / 61 skipped; windows-operator 36
tests; linux-isolation T1 34, T2 32, T6 19 with zero skips. Local bounded stress
of the four operator modules: 10 of 10 passed.

## Unresolved

**Observation, cause not established:** an intermittent `RemoteDisconnected` on
loopback GET seen earlier did not recur in a 10-run stress. Server-side
`handle_error` capture is now in place, so a handler fault can no longer be
mistaken for a transport drop. The GET retry is a mitigation, not a fix.

**Known, deliberately unhandled:** `do_GET` does not catch `TypeError`, unlike
`do_POST`. Catching it would turn a programming defect into an ordinary 400.

**Disclosed, not a defect:** the deterministic controller integration test feeds
the controller simulated protected results; the real protected evaluator does not
execute there. IF-001 v22's authored assertion also passes before repair.

## Highest-priority remaining engineering requirement

IF-002 diagnosis-to-patch consistency (`docs/PROJECT_STATUS.md`). Needs a specific
testable change, not repeated retries; $0.062620 of the $0.40 cap remains.

## Constraints

Private repository. No paid inference, no remote Sandbox calls, no production
ledger writes. Preserve the brief and frozen benchmark. No submission, release,
publication or demo-link work.
