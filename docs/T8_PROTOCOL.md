# T8 frozen comparison protocol

Closeout: all twelve slots were recorded. See [results](T8_RESULTS.md) and the
[disclosed accounting continuation](T8_CONTINUATION.md). Three infrastructure
failures triggered the ranking-invalidity rule below. This original protocol
description is retained; the amendment did not change agent or evaluator inputs.

Two independent attempts for each B0/B1/B2 × IF-001/IF-002 cell: twelve slots.
Variant order rotates across family/repetition blocks. All launched attempts,
including malformed actions, exhausted budgets, infrastructure errors and unknown
outcomes, remain in the primary denominator. No automatic retries or replacement
attempts. If funding or an unknown operation blocks dispatch, report every planned
but unlaunched slot separately and do not claim a complete comparison.

## Frozen controls

Use the same Nemotron Nano endpoint, temperature 0.2, 8192 output-token maximum,
ten calls, three edits, two optional developer tests, six agent executions and
one separately counted final execution per attempt. The agent deadline is 900
seconds; final execution uses the same bounded backend. Inference shares the
existing $0.20 project cap. Calls reserve their conservative maximum first.

Freeze source, schedule, prompt, contract and evaluator hashes before the first
launch. Record the actual Git commit and campaign-driver hash. Do not modify these
files or tune prompts during the campaign. Store final artifacts separately from
agent evidence. The controller never receives final results as feedback.

B0 may voluntarily use an experiment. B1 must investigate and interpret before
repair. B2 additionally requires one property-only development feedback request.
All variants receive protected development checks after freezing their candidate,
then four withheld final schedules. A frozen candidate is evaluated even when its
development verdict rejects it. Runs without a frozen candidate remain unresolved.

## Withheld schedules

Two shared cases exercise changed mixed-item/currency payloads and inventory
contention. IF-001 adds committed response loss with both Payment and Order
restart, followed by a new order, plus cancellation across the same restart
combination. IF-002 adds decline/restart followed by a larger eligible order, and
two sequential declined orders with restart barriers before the eligible order.

Every case uses a fresh store and boundary checks; exports include independent
effect audit and snapshot manifests. Recovery bounds are three seconds for
IF-001 and two seconds for IF-002, measured from before service startup. Cases
retain the declared IF-002 Inventory restart to discard queued old requests.
Validate schedule infrastructure with authored reference/harmful controls before
freeze. Do not use model final outcomes for threshold or prompt tuning.

These are new schedules over the SAME defect implementations. Results support
only schedule generalization under these conditions, not novel incident classes.
Two runs per cell support descriptive counts, not a statistical superiority claim.

## Decisions and metrics

Primary valid repair: all four final cases accepted, independently verified exports,
unchanged frozen candidate, no missing case evidence. A failed or unknown run does
not pass. Report per-cell numerator/denominator, per-case decisions, all failures,
tokens, estimated inference costs, elapsed time, remote operations and raw provider
resource receipts. Provider execution cost units are unspecified, never USD.

More than two infrastructure-failed attempts among twelve launches invalidates any
ranking. A smaller sample also forbids a ranking claim. Candidate-caused test
failures and malformed model actions remain repair failures, not infrastructure
exclusions. Diagnosis is a separate qualitative audit: factual copying and passing
repairs do not prove causal understanding.

Full raw runs remain local. Publish a curated summary, source/schedule freeze and
case-level outcomes without credentials, prompts, databases, local paths or
account identifiers. Private repository visibility is retained as requested.
