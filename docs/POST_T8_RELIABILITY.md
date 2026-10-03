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

57 portable tests pass, including fourteen new regressions for malformed action
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
