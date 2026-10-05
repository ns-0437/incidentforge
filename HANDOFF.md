# Handoff

**State, October 5, 2026.** HEAD `a14cc30`, working tree clean, repository private.
`docs/ORIGINAL_BRIEF.md` unchanged at sha256 `4a2d5f78…29af`. Frozen T8
`summary.json` and `freeze.json` untouched.

## Implemented

Three HTTP services with separate durable state and a trusted SQLite persistence
broker; IF-001 duplicate payment and IF-002 stranded compensation; Nemotron via
Token Factory and real Sandbox execution (recorded, not exercised by tests);
bounded controller with investigation, allowlisted edits, authored regression
tests, freeze and independent verification; protected evaluator; operator console
with launch, status, cancel, review and export; curated static replay.

Added in this pass: dependency and import provenance measured from the
allowlisted source, with import records reaching the investigator through the
existing index; reproduction bounds attached to the reproduction record,
separating execution completing from symptom reproduction; an incident-specific
IF-002 reproduction verdict assessed against the declared recovery window; and a
derived T8 metric view with corrected labels.

## Latest results

Run [37341854060](https://github.com/ns-0437/incidentforge/actions/runs/37341854060),
all three jobs green: portable, windows-operator, linux-isolation.

## Limitations, unchanged

- **IF-001 symptom reproduction stays undetermined.** Developer mode exposes HTTP
  responses and request identity counts, never committed effects.
- **Repeat live repair reliability is unproven.** One IF-002 success (v25); the
  rejected-edit recovery path has offline coverage only.
- **The controller integration test consumes simulated protected results**; the
  real protected evaluator does not execute there.
- T8 supports no variant ranking. Reproduction rate, time to reproduction,
  successful-resolution time, lost orders and duplicate effects remain
  unavailable from retained evidence.
- An intermittent loopback `RemoteDisconnected` was observed; cause not
  established.

## Scope

Implemented functionality is not demonstrated reliability. Not every original
requirement is established as complete: the gaps above are capability limits, not
pending polish.

## Constraints

Private repository. No paid inference, remote Sandbox calls or production ledger
writes. Preserve the brief and frozen benchmark. No submission, release,
publication or demo-link work.
