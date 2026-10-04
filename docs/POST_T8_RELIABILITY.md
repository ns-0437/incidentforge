# Post-T8 reliability development

This is a new development revision, not a modification or rerun of T8. The
complete original campaign and its frozen implementation are retained at commit
`f10d49c`. Use that checkout to reproduce the T8 summary; its source-pin check
intentionally refuses the newer development implementation.

## Changes motivated by observed failures

- Interpretation facts and developer-test specifications accept native JSON
  objects. Legacy JSON strings still work. Exact factual equality, allowed
  action fields and declarative assertion restrictions remain enforced.
- Every action response and correction includes the current action contract,
  edit/test counters, valid assertion shape and the exact required factual
  conclusion. Before interpretation, repair actions remain prohibited. The
  controller supplies measured facts, never a verified causal explanation.
- The investigator receives the public incident description as well as source,
  contract and reproduction. Compensation-only guidance is confined to IF-002;
  probe names are explicitly test interventions, not application mechanisms.
- No-op replacements are rejected. Finishing requires a net application-source
  change, so no edit, test-only edits and reverted source edits cannot masquerade
  as repairs. This does not establish that a nonempty patch is correct; protected
  verification still decides acceptance.
- Reports separate verified changed paths, test-file presence and requested test
  runs from the unverified model summary. Test-file presence is not a passing test.
- After the second pilot exposed an authored-but-unrun test, finish now requires
  any authored tests to have executed on the current candidate revision. An
  earlier test run cannot cover a later edit or a later test specification. This
  last guard was regression-tested locally, not tested in another paid pilot.
- A single inference request may wait 120 seconds rather than 60. Both the HTTP
  socket and killable process use the same bound. The controller reserves 130
  seconds of remaining wall time before dispatch. The 900-second run limit,
  ten-call limit, full per-call reservations, no retries, and $0.20 project cap
  remain unchanged. The longer wait is a mitigation, not proof that timeouts are
  solved; it may leave less time for later actions.

## Validation

61 portable tests pass, including eighteen new regressions for malformed action
types, exact factual checks with native objects, guided correction, unchanged
and reverted source, no-op edits, unsupported assertion operators and deadline
refusal without dispatch and quote-free factual conclusions. Scripted tests establish controller behavior, not live
model success rates.

An IF-001/B2 Nebius Sandbox pilot tested the first revision. It failed after three
interpretation rejections: the structured counts were correct, but the copied
conclusion contained extra JSON escaping. The failure is retained as
`b2-if-001-20261003T130224Z-9bc3d1`; four calls cost an estimated $0.004033.

The revised conclusion is a controller-generated plain-text list of condition
counts, with no embedded JSON or quote escaping. Structured measurements and
the factual conclusion must still match exactly; no fuzzy matching, silent
correction, or relaxed fact check was introduced. A second, final IF-001/B2
development pilot was declared for this new revision. Both pilots use fresh
candidate state and no T8 withheld schedules. They cannot establish comparative
efficacy or a success rate.

## Retained results

| Revision / pilot | Calls | Action rejections | Outcome | Estimated inference |
| --- | --- | --- | --- | --- |
| First interface revision / `130224Z-9bc3d1` | 4 | 3 conclusion-escaping mismatches | Unresolved; no patch | $0.004033 |
| Plain-text conclusion and incident context / `130552Z-391087` | 6 | 0 | Behavior rejected | $0.005841 |

The second pilot passed the exact interpretation gate, applied a source edit,
authored a test, received protected feedback and froze a candidate. Independent
development validation rejected it for P1/P2 failures. The model still claimed
its fix resolved duplicate charging despite those failures; that prose remains
explicitly unverified. The authored test was not run, motivating the final local
guard above. No successful repair or improved success rate is claimed.

Both protected development archives from the second pilot were independently
recomputed. Hash-verified reports, action rejection counts and sanitized outcomes
are in [the development summary](../benchmarks/reliability/summary.json).

Project settled token-price estimate: **$0.112362**. Conservative exposure including
T8's three unknown reservations: **$0.165447 / $0.20**. No new unknown inference
usage or pending sandbox operation remains. No further inference was launched.

## Follow-up: persistent negative feedback and grounded tests

The controller now retains property-only feedback in subsequent action guidance
and the final report. It marks whether the candidate is unchanged since that
feedback. A revised candidate is explicitly unvalidated; changing code does not
turn a rejected result into a pass. Guidance asks the model to revisit the public
contract and durable state transitions before revising its proposal. Finishing
with a known limitation is still possible, and independent verification remains
the only acceptance authority. No additional protected feedback is available.

Developer assertions must name exactly one condition and an existing field from
the most recent developer observations. This rejects the literal placeholder
test authored in the second pilot. Expected values may differ from observed
values, so genuine failing regression assertions remain valid. This authoring
check uses no protected observations, schedules or case names. Exhausted edit
and test actions are omitted from guidance; server-side bounds still apply.

Three new local regressions verify placeholder refusal, retained negative
feedback across a revision without private case leakage, and field validation
that still permits failing expected values. These follow-up changes have not
been tested with another live model; no further inference credit was spent.

Next priority is validating repair reasoning with a separately declared pilot.
Any future live comparison needs a new freeze and adequate budget;
these two sequential development revisions must not be merged into T8 results.

## Frozen follow-up pilot and separate diagnostic

One IF-001/B2 pilot at revision `3680c8b8594e5edde1a3a43a7f3e037944956481`
was declared with source hashes before dispatch. Run
`b2-if-001-20261003T142249Z-a154d9` made seven calls ($0.006911 estimated),
passed interpretation and applied one payment-key preservation edit. It then
repeatedly authored assertions using experiment-only fields against the developer
workload. Three rejected paths exhausted the correction limit. The run remains
**unresolved**, with no frozen candidate, authored test file or protected feedback.
It therefore did not exercise the negative-feedback revision behavior.

A separately initiated, post-hoc protected development diagnostic of that exact
retained patch passed **6/6 cases**, independently recomputed by the restricted
reader. Candidate revision was checked before and after execution. This is useful
patch evidence, not successful autonomous completion or a final withheld score.
The source pins were verified before diagnostic execution. Results are preserved
in [v4-pilot.json](../benchmarks/reliability/v4-pilot.json).

The subsequent local fix exposes a bounded catalog of actual developer condition,
field path and scalar-type pairs in action guidance and corrections. Experiment
observations are explicitly excluded. Duplicate conditions are omitted because
they cannot uniquely identify an assertion target. This preserves existing strict
validation; it does not invent values or weaken acceptance. Two local regressions
check scope, ambiguous conditions and output bounds. This latest fix has not had
a live pilot.

Current conservative project exposure: **$0.172358 / $0.20**, leaving **$0.027642**.
No new unknown usage or pending operations. T8 and earlier pilot records remain
unchanged. The end-to-end live-validation gate is still unmet, so T9 cannot yet
claim a reliably completing autonomous repair workflow.

## Field-catalog live pilot

A single IF-001/B2 pilot was declared at frozen revision
`bfe82c57bc4fd85a53d8a62cc84cbb7520c9fffb`. Run
`b2-if-001-20261003T142937Z-37e8ac` used ten calls ($0.010740 estimated).
It passed interpretation, recovered from an exact-edit mismatch, applied the
payment-key repair and authored a test using a real developer field. Protected
development feedback accepted the candidate with six independently verified cases.

The controller refused premature finish because the authored test had not run.
The agent then executed a developer test, rewrote its assertion specification,
and incorrectly requested a second protected feedback call. That exhausted the
correction limit. **The run remains unresolved**, without candidate freeze or
post-freeze validation. Passing intermediate feedback is not completed autonomous
repair. The rewritten test specification was not executed on the final revision.
Negative-feedback revision behavior was not exercised because feedback passed.

The [curated outcome](../benchmarks/reliability/v5-pilot.json) retains all rejection
reasons, verified-work counters, accounting and the independent verification receipt.
The original source hashes were checked again after execution. No extra diagnostic
or model retry was launched; T8 remains unchanged.

Project settled estimate is **$0.123102**; conservative exposure is **$0.183098**.
The remaining **$0.016902** cannot fund the **$0.017695** conservative reservation
for even one further inference call. There are no pending calls or remote operations.
The cap was not increased and prior unknown reservations were not refunded.

Next work must be local: test an explicit post-feedback completion path, make
current test revision and remaining feedback allowance prominent, and prevent
redundant test-specification writes from invalidating completed tests. A fresh
live validation requires additional allocation within confirmed free credits.
T9 materials may be prepared, but the live completion gate is not passed.

## Local completion-flow revision after the field-catalog pilot

The controller now reports `finish_ready`, explicit `finish_blockers`, the
remaining protected-feedback allowance, and whether tests ran on the current
revision. Its advertised actions omit finish until the same checks used by the
actual finish gate pass. After positive feedback and completed tests it directs
the worker to finish rather than rewrite tests or repeat validation. Negative
feedback instead directs review/revision or an honest limited submission; it is
never relabeled as success. Post-freeze independent verification still runs.

Saving an identical developer-test specification is idempotent: object-key order
and JSON whitespace do not create a change, consume an edit, rewrite the file or
invalidate its completed test. Changed values, scalar types, names or assertion
order remain changes. No failed test is converted into a pass; the existing gate
records execution, while the independent evaluator determines acceptance.

A scripted B2 regression covers interpretation, edit, test authoring, protected
feedback, required test execution, repeated identical save, finish and fresh
independent validation. A second regression proves that changing `1` to `true`
invalidates prior execution. Existing negative-feedback checks also verify the
completion advice does not encourage a false success claim. **61 tests pass.**
These are deterministic local checks, not another live model result. No inference
or Sandbox calls were made for this revision; exposure remains **$0.183098**.


## Explicit allocation amendment

The owner approved a cumulative maximum of **$0.40** from existing free credits,
with no further increase. The persisted ledger retains all settled and unknown
calls; exposure before this amendment is **$0.183098**. See
[the audit record](../benchmarks/reliability/allocation-amendment.json).
Historical T8 caps and results are unchanged. Access is confirmed by the owner
through submission only; December judging access remains unresolved.


## Live completion checks after the allocation amendment

At revision `212d95b`, two separately declared B2 attempts tested the completion
flow. IF-001 (`b2-if-001-20261003T160414Z-6c7d7c`) completed in five calls with one
source edit and no action rejections. The frozen repair passed development
validation and all four previously used final schedules. Inference: **$0.005378**.

IF-002 (`b2-if-002-20261003T160752Z-e8b71a`) completed in seven calls with one source
edit but failed protected compensation property P4. The model acknowledged the
failure and submitted a rejected candidate rather than claiming acceptance.
Final schedule follow-up also rejected the frozen candidate.
Inference: **$0.008102**. The edit changed handling of a failed release instead of
repairing restart recovery; completion-flow improvements do not ensure repair quality.

Neither attempt authored developer tests, so neither exercised the new authored-test
completion path live. These two development attempts do not replace any T8 outcome
or establish a comparative success rate. Curated records are `v6-pilot.json` and
`v7-pilot.json` under `benchmarks/reliability/`.

Cumulative exposure is **$0.196578 / $0.40**, including **$0.053085** in conservative
unknown-call reservations. No calls remain pending. The remaining allocation is
**$0.203422**. The unallocated portion of the original trial is reserved, not committed.


## Reachability-instruction follow-up: rejected repair, live test path exercised

Revision `dc9155e` adds general instructions to separate independent conditions,
trace source reachability before editing and preserve side-effect success checks.
The evaluator, fixture and budgets are unchanged. All **62 local tests** and CI pass.

One declared IF-002 B2 attempt (`b2-if-002-20261003T161722Z-d4051d`) still edited a
downstream reconciliation error into `pass`; it failed protected compensation
property P4. Prompting alone did not establish repair-quality improvement. The
model did author a developer assertion, execute it on the current revision, observe
its failure, and finish with explicit limitations. Fresh post-freeze protected
validation rejected the candidate. This exercises the authored-test completion
path live, but does not demonstrate successful compensation repair.

Nine model calls cost **$0.010978**. Cumulative exposure is **$0.207556 / $0.40**;
**$0.192444** remains, with no pending calls. See [retained result](../benchmarks/reliability/v8-pilot.json).
No automatic retry was launched. The next useful intervention is stronger measured
execution-path evidence, not another identical prompt attempt or weakened acceptance
criteria. Historical accepted repairs and T8 outcomes remain unchanged.


## Development execution traces: implemented, repair improvement not established

[Development traces](DEVELOPMENT_TRACES.md) provide bounded source line/return
observations by Order process generation. They are candidate-process diagnostics,
not protected evidence. Tracing is disabled for protected and final evaluation.
65 portable tests and CI pass; 17 Linux checks pass, including a trace comparison
where the faulty restart returns early while the reference reaches release.

The first declared trace pilot at `4ad1e92` stopped after two model calls because
both investigation responses named nonexistent source symbols. It made no edits
and cost **$0.003072**. The trace itself was available; its repair value was not tested.
The next revision `af5bcd3` reports the exact invalid identifiers and valid choices
without relaxing grounding. Its one declared follow-up passed investigation, but
again suppressed a downstream release error and failed protected P4 after freeze.
It used nine calls and cost **$0.013089**. Both attempts are retained as v9/v10.

The model's v10 claim that further repair exceeded its edit budget is unverified
and contradicted by the controller count of one applied edit. Do not promote
that prose into a factual explanation of the stopping decision.

Cumulative exposure is **$0.223717 / $0.40**; **$0.176283** remains. No calls are
pending. No further identical pilot was started. Measured traces are implemented,
but these attempts do not establish reliable compensation repair or a benchmark
improvement. The original T8 comparison remains unchanged.


## Compact trace focus and live timeout

Two implementation commits separate the source-bound summary (`d7a397d`) from
its agent-guidance integration (`446ba21`). The summary highlights observed returns
and nearby source while suppressing locations whose source hash no longer matches.
All **68 portable tests** and implementation CI pass. Protected evaluation is unchanged.

The declared IF-002 B2 attempt `b2-if-002-20261003T182559Z-12a807` timed out at
120 seconds on its first inference call, before any edits. No retry was made.
The full **$0.017695** reservation remains pending with unknown actual usage.
This is an infrastructure failure, not evidence for or against repair quality.

Cumulative exposure is **$0.241412 / $0.40**. The nominal remainder is **$0.158588**,
but dispatch is blocked pending explicit accounting reconciliation. All prior
usage remains in the same ledger. See [v11 evidence](../benchmarks/reliability/v11-pilot.json).


## October 4: audited timeout accounting and clearer budget display

The [timeout recovery tool](TIMEOUT_RECOVERY.md) now previews by default and can
apply an explicit full-reservation reconciliation after checking terminal evidence.
The v11 timeout is accounted as `conservative_unknown`, with actual usage still
NULL and its full $0.017695 counted. The transaction preserves exposure and the
$0.40 cap; no inference was issued or retried. Its historical result is unchanged.

Exposure remains **$0.241412**, including **$0.070780** in four unknown reservations.
The remaining allocation is **$0.158588**, and no reservation remains pending.
The local UI now headlines this total exposure instead of only settled estimates.
**71 portable tests pass**, including preview immutability, atomic accounting,
repeat rejection, nonterminal/tampered evidence and settled-call protection.
JavaScript syntax validation also passes. This improves recovery and reporting;
it makes no new repair-quality claim.


## October 4: compact-focus follow-up and verifier startup guard

One declared IF-002 attempt at `9c60fd7` completed investigation and applied one
edit, but stopped when the independent reader discovered Docker Desktop's Linux
engine was unavailable. Six model calls settled at **$0.009764**. The autonomous
outcome remains **unresolved**; it was not resumed or relabeled.

After restoring Docker, a read-only, network-disabled reader recomputed the
already-exported archive. It rejected the candidate. Six exported cases were
checked; two tests did not export cases. This is a later diagnostic, not an
accepted autonomous repair. See [v12 record](../benchmarks/reliability/v12-pilot.json).

The Sandbox adapter now checks Docker Linux availability and pins the reader's
image ID during construction, before remote workload or model calls. It records
readiness in evidence and reuses that image for later verification. Startup checks
cannot guarantee the daemon stays available, but they prevent this specific
late discovery of an already-missing dependency. **74 portable tests pass**, with
negative checks for missing daemon, wrong engine OS and malformed image IDs.
The actual restored engine passed the new check without spending inference credits.

Exposure is **$0.251176 / $0.40**; **$0.148824** remains. No pending reservations
or active Sandbox guard remain. No further model attempt was started.

## v13: return-guard source references — October 4

Revision 6d51cc2 adds bounded AST references to state used by an observed return
guard. The IF-002 B2 Sandbox pilot remained **unresolved**: two calls returned
invalid AST symbol references (`reservation_id`, `release`). No edits, freeze or
protected feedback occurred. All 16 evidence events and artifact hashes verified.
Cost estimate **$0.003487**; cumulative exposure **$0.254663 / $0.40**, remaining
**$0.145337**, pending calls zero. Four unknown-usage calls retain **$0.070780**
in conservative reservations. No reliability improvement claimed.
See [v13 record](../benchmarks/reliability/v13-pilot.json). Further inference is
paused while release work and the source-grounding failure are reviewed.

## Upfront source vocabulary — October 4

The investigator now receives `allowed_source_symbols` before its first call.
The list and validator share the same AST extractor. String keys and operation
labels remain invalid in `symbols`; their exact source lines can be cited in
`supporting_refs`. Regression tests check the initial prompt and exclusion of
data-only strings. All 81 portable tests pass. No additional live pilot was run,
so this change establishes prompt/validator consistency, not improved repair rate.

## Evidence-reference validation — October 4

Blank and whitespace-only source quotes are rejected rather than counting as
grounding through substring matching. Each hypothesis must also name the actual
selected experiment. Three regression tests cover both rejection paths and valid
line IDs/verbatim excerpts. All 84 portable tests pass. These are validation
corrections, not evidence of a higher autonomous repair success rate. No new
inference spending or replacement of frozen results occurred.

## Exact experiment coverage — October 4

The investigation-to-repair handoff now requires a literal completed result and
each declared condition exactly once, with a supported measurement. Previously
four rows could contain duplicate condition names and overwrite facts during
summarization. Invalid results are rejected before publishing a complete
ExperimentResult or returning measurements to repair.

Four regression tests cover valid reordered results, duplicate/missing/unexpected
conditions, malformed or unmeasured results, and rejection at the investigator
handoff. All 88 portable tests pass. A read-only compatibility check accepted
all 23 retained results explicitly labeled declared four-condition experiments;
36 other experiment records, including reproduction, were outside this check.
Historical evidence and frozen benchmark outcomes were not modified. No live
inference was used; cumulative exposure remains $0.254663 of the $0.40 cap.

## Incomplete protected feedback stops B2 — October 4

B2 now stops unresolved when its protected-feedback execution is incomplete.
The request remains counted and its sanitized feedback retained, but no further
model action is requested and no candidate is frozen. Previously the request
count alone satisfied the feedback gate even without completed feedback.
Only literal boolean true counts as completion; truthy strings or numbers do
not. A completed behavioral rejection still permits revision under the existing
limits. Two regression tests verify completion typing and the controller stop,
including no extra model calls, no final execution, and no private-data leakage.
All 90 portable tests pass. No live inference was used and no historical result
was changed. Exposure remains $0.254663 of the $0.40 allocation.

## Final acceptance receipt consistency — October 4

The controller now checks final acceptance receipts before assigning an accepted
verdict: literal completion, a positive test count matching distinct case records,
zero runner errors/failures/skips, accepted case decisions, all seven property
results, and nonempty isolation receipts containing only literal true values.
Only P2/P6 may be not applicable, matching the evaluator. Missing or contradictory
acceptance evidence becomes invalid_evaluation. This checks internal consistency;
it does not authenticate evidence or prove universal correctness.

Four regressions cover valid receipts, contradictory cases/properties/isolation,
completion typing, and the final controller handoff. All 94 portable tests pass.
A read-only compatibility scan accepted all 17 retained protected acceptance
receipts. Historical outcomes remain unchanged. No new inference spending.
