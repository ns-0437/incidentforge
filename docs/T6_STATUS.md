# T6: IF-002 and benchmark development

October 3, 2026. Original project scope preserved. The local IF-002 fixture, reference/negative controls, incident-aware agent runner and B1 variant are implemented. No final holdout or statistically meaningful model comparison is claimed.

## Verified fixture and adapter

`runs/t6-linux-20261003-054254`: 16 Linux tests, 23 evaluated cases, zero failures/errors/skips. This includes existing T2 regression checks. The known-good compensation loop resumes after restart. The authored volatile-compensation defect passes without a crash but leaves COMPENSATING plus HELD stock after restart and fails P4. Independently authored terminal-without-release fails P4; double release credit fails P5. Replaying release after Inventory restart creates exactly one release mutation.

`runs/t6-adapter-5831ed7d`: actual candidate backend verified the four-condition probe, rejected the faulty candidate, and accepted the reference across eight protected scenarios. Nine evidence events verified. No inference was used for these controls.

The trusted schedule observes committed COMPENSATING state and its audit transaction plus a HELD reservation before killing Order. Inventory is restarted with the same store to discard queued requests before Order restarts. This is an explicitly declared two-service restart schedule, not a claim that only Order restarted. The two-second development observation limit is not a calibrated final benchmark bound.

## Development pilots

The predeclared campaign is `runs/t6-pilots-35b13480`. Its manifest pins implementation hashes, records B0/B1/B2 order and common budgets, and its ledger retains every launch and outcome. Each pilot begins from the same isolated faulty IF-002 source and public contract. Previous IF-001 pilots used evolving tools/prompts and are not matched comparison trials.

B0 has optional access to the same distinguishing experiment and source as B1/B2. B1 requires investigation and interpretation before repair. B2 additionally receives one protected property-only feedback opportunity. All variants receive post-freeze protected validation. No private evaluator source, exact schedules or planning docs enter model context.

See the campaign ledger and the exported T6 review JSON for final case-level outcomes and usage. A failed pilot remains a failed pilot, not a reason to change the frozen-in-advance development order or discard its record.

| Variant | Outcome | Calls | Estimated USD | Evidence events |
| --- | --- | ---: | ---: | ---: |
| B0 | Accepted; 8/8 protected tests passed | 3 | 0.002295 | 33 |
| B1 | Rejected; 4/8 protected tests failed, no errors/skips | 7 | 0.005850 | 53 |
| B2 | Unresolved; three exact-edit mismatches, zero edits, no protected verdict | 5 | 0.005460 | 41 |

B1 incorrectly turned a declined order into CANCELLED_BY_CLIENT. B2 exhausted its correction allowance before reaching protected feedback. These results provide no evidence that B2 outperforms the other variants. There was one accepted repair out of three launched IF-002 attempts; one trial per variant cannot establish reliability or ranking.

T6 inference subtotal: $0.013605. Project inference total including T4/T5: $0.029322, with zero pending reservations, within the cumulative $0.20 cap. These are calculated usage estimates, not a live provider balance or invoice. All nine pilot execution cleanups were confirmed; no disposable pilot containers/volumes remain.

The post-run audit found a Windows encoding bug: events were written as UTF-8 but the verifier used the default text encoding. B1/B2 launcher logs retain the resulting verification exception. The event bytes were intact. Explicit UTF-8 decoding now verifies all 127 pilot events and all artifact hashes. No original run was rewritten or rerun. The pre-fix evidence.py is preserved alongside the campaign manifest; the post-pilot changes are the encoding fix and its regression test. All implementation hashes matched before those changes. Sixteen controller tests now pass, including Unicode evidence and B1 feedback isolation.

## Judge findings and remaining gates

The implementation demonstrates a distinct second incident mechanism and catches plausible harmful compensation patches. The reference and candidate adapter passed before live model launches.

Investigation quality remains an explicit weakness: model explanations have reversed the meaning of CANCELLED_DECLINED versus COMPENSATING, and format validation cannot detect that semantic error. Claims must be checked against structured measured facts before final benchmark freeze. Source-reference quality and named-hypothesis prediction mapping also need improvement. B0's passing patch removes the process-local gate, but its prose incorrectly calls the volatile set persistent; model explanations are not trusted verdicts.

Remote controller/candidate integration, editable developer tests, stronger record typing, calibrated recovery deadlines and distinct final schedules remain pre-T8 gates. See BENCHMARK_DEVELOPMENT.md. The original two-family plan remains intact. Next product stage is T7's interface, which must distinguish measured verdicts, model claims, live runs and recorded evidence.
