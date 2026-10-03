# IncidentForge: evaluation plan

Updated 2026-10-03. T2 local reference/harmful-control measurements exist in T2_STATUS.md. No model comparison or final holdout result exists yet. Preserve original two incident families and competent comparisons. All final claims say 'validated under declared conditions'.

T6 update: both development incident families and B0/B1/B2 runner variants now exist. One IF-002 pilot per variant is retained in T6_STATUS.md; these integration results are not a frozen comparative study. BENCHMARK_DEVELOPMENT.md records shared tool access, actual schedules, costs and remaining freeze gates. Prior IF-001 pilots used different development revisions and must not be pooled as matched comparison trials.

## Variants and fairness

| Variant | Behavior |
|---|---|
| B0 | Competent generic inspect/edit/run-tests loop; public business contract, visible tests, same source/evidence and tool capabilities |
| B1 | B0 plus explicit competing hypotheses and controlled intervention protocol |
| B2 | B1 plus protected development evaluator feedback during repair |
| B3 optional | B2 plus bounded parallel candidate branches with total resource accounting |

B0 may investigate or design experiments spontaneously; do not forbid competent behavior. B1 changes the required workflow, not access to useful tools. B2 uniquely receives L2 feedback; every variant gets the same L3 evaluator after its candidate is frozen. B0 need not satisfy a B1-only hypothesis gate to patch. Give each equal total model/token/execution/wall-clock limits and the same selected model/sampling configuration, source/evidence and editable tests. All additional B2 checks and B3 branches consume declared budgets. Record fixed final evaluation costs separately and equally; do not hide extra attempts.

## Data separation and freeze

Development: visible tests, protected L2 schedules, authored controls, tuning pilot. Calibration: development-only reference workloads for recovery limits and resource caps. Final holdout: distinct cases/schedules frozen after development and not used to set thresholds or tune prompts.

Author holdout variants across both mechanisms and, where affordable, different implementations; a reseeded schedule supports a narrower claim. Pin system commit, prompts, model/settings, public contract, evaluator, fixture/image, boundary tests, budgets, recovery limits, incident split and schedule hashes before campaign. The final campaign includes multiple independent agent runs; it is not a single trial. Compare matched incident cases and rotate variant execution order to reduce time/order effects.

Final outputs used to tune anything convert affected cases to development data. Keep the contaminated results labeled and use a new holdout for renewed independence claims. No dropping difficult cases or repairing the reference to fit final observations mid-campaign. Freeze artifacts outside runtime agent scope; release reproducibility materials after measurement when appropriate. Verify actual bundle/context leakage tests, including planning docs and Git history.

## Pilot and sample-size decision

1. Validate reference, all harmful fixtures and boundary tests locally before measuring any agent.
2. After funded remote access is confirmed, reserve a small capped pilot allocation from usable credits after contingency/judging reserves. Start with one selected model and one development incident; account for every call.
3. Estimate conservative per-run cost/time from actual pilot usage plus worst-case retry caps. Compute funded campaign capacity using the lesser of credit and time capacity.
4. Predeclare equal independent run counts per B0/B1/B2 case. Retain both incident families. Target at least two independent trials per cell if affordable; more is a proposed target, not a guaranteed statistical claim. Reserve final evaluator and failure/retry costs before launching.
5. If funded capacity cannot cover a minimally interpretable comparison, report the evaluation as blocked/limited and seek additional free grants. Do not authorize paid overage, remove a family silently, or present a demo as a comparative study.

Schedule repetitions measure robustness of ONE patch; independent model runs measure repair reliability. Record both. Calibration/repetition counts follow pilot cost and residual nondeterminism; concurrency tests require an observed distinguishing result or explicitly inconclusive status. Small counts support descriptive results with raw numerators, not broad significance claims.

## Metrics and decision rule

Report reproduction rate, valid repair rate, harmful-control rejection/acceptance, clean regressions, lost eligible orders, duplicate effects, correct compensation, time to reproduction/resolution, tokens, execution resources and costs. Diagnosis scoring uses withheld authored ground truth without leaking it. Do not call a model confidence number calibrated probability.

Accept for human review only if clean reset, runtime boundary, audit completeness, required workload completion and every applicable business check pass. Missing evidence and unknown outcomes cannot pass. A single safety violation is never averaged away. False-acceptance counts on authored harmful controls are explicitly fixture coverage, not an estimate of all possible harmful patches.

Primary end-to-end valid repair denominator: ALL launched independent agent runs, including infrastructure and unknown outcomes. Separately report a conditional rate over runs with validated infrastructure, with reasons and counts for every exclusion. Candidate-caused errors never leave that conditional denominator. No automatic timeout exclusion. An infrastructure retry creates a linked attempt and consumes budget; do not retain only its success. Predeclare a campaign validity threshold for infrastructure failure after pilot; if exceeded, report unreliable campaign execution rather than a clean ranking.

Show case-level outcomes and intervals where justified (e.g. binomial intervals for independent runs); paired contrasts share cases and are not independent observations. With tiny samples, raw counts, paired differences and limitations are sufficient. Report neutral/negative B2 results unchanged.

## Manifest and reproducibility

Every run: ID/time, system commit, source/base revision, patch hash, fixture version/image digest, dependency locks, backend, CLI/SDK versions, model ID/config, prompt/tool transcript refs, public contract hash, evaluator version, private schedule IDs/hashes, event/audit/proxy/backup hashes, synchronization barriers, repetitions, reset/boundary checks, budgets/reservations/usage, cancellation/terminal status, outcome and limitations. Record units and distinguish estimates from billed amounts; never put credentials in artifacts.

Append launch ledger before dispatch; reconcile every row with outcome/cost, including abandoned runs. Hash all exported evidence. Archive extraction and database reads are bounded and isolated. Developer-facing evidence export is redacted while cases remain held out; full reproducibility export after measurement is separately labeled. Recorded replays and live runs are distinct UI modes.
