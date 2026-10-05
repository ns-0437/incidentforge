"""Derive only defensible metrics from the frozen T8 summary.

Reads benchmarks/t8/summary.json, never writes it. Every metric states its unit,
denominator and supporting field. A metric the retained evidence does not measure
is null with an explanation, never zero. No ranking is computed or implied.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'benchmarks/t8/summary.json'
TARGET = ROOT / 'benchmarks/t8/derived_metrics.json'

# evaluation/holdout.py sets fault=True only for these two IF-001 cases, so the
# remaining shared cases are the fault-free workloads.
FAULT_CASES = ('dual_restart_response_loss', 'cancel_after_dual_restart')
CLEAN_CASES = ('canonical_mixed_payload', 'contended_inventory')


def unavailable(reason):
    return {'value': None, 'unavailable_reason': reason}


def quantiles(values):
    ordered = sorted(values)
    if not ordered: return None
    middle = len(ordered) // 2
    median = ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2
    return {'n': len(ordered), 'min': round(ordered[0], 3), 'median': round(median, 3),
            'max': round(ordered[-1], 3)}


def derive(summary, source_text=None):
    attempts = summary['attempts']
    resolved = [a for a in attempts if a.get('independently_verified') is True]
    evaluated = [a for a in attempts if a.get('case_outcomes')]
    outcomes = {}
    for attempt in attempts:
        outcomes[attempt['final_decision']] = outcomes.get(attempt['final_decision'], 0) + 1

    clean_instances, clean_failures = 0, []
    liveness_attempts = set()
    for attempt in evaluated:
        for case in attempt['case_outcomes']:
            failed = sorted(p for p, v in case['properties'].items() if v == 'fail')
            if case['case'] in CLEAN_CASES:
                clean_instances += 1
                if failed or case['decision'] != 'accept_for_review':
                    clean_failures.append({'slot': attempt['slot'], 'case': case['case'],
                                              'failed_properties': failed})
            if 'P3' in failed:
                liveness_attempts.add(attempt['slot'])

    return {
        'schema_version': 1,
        'source': {'path': 'benchmarks/t8/summary.json',
                   'sha256': (hashlib.sha256(source_text.encode('utf-8')).hexdigest()
                              if source_text is not None else None),
                   'sha256_unavailable_reason': (None if source_text is not None else
                       'the summary was supplied directly to derive(), so no input text was hashed'),
                   'freeze_sha256': summary.get('freeze_sha256'),
                   'hash_basis': 'sha256 of the LF-normalized UTF-8 text of the input actually used '
                                 'for this derivation, not of a separately read file and not of '
                                 'canonical JSON',
                   'note': 'Derived view only. The frozen summary is never modified.'},
        'attempts_preserved': {'total': len(attempts), 'outcomes': outcomes,
                               'infrastructure_failed_attempts': summary.get('infrastructure_failed_attempts'),
                               'ranking_supported': summary.get('ranking_supported')},
        'metrics': {
            'reproduction_rate': unavailable(
                'No attempt records a reproduction outcome. Execution completing is not symptom '
                'reproduction, and the incident-specific reproduction assessment added after this '
                'campaign is not applied retroactively.'),
            'time_to_reproduction_seconds': unavailable(
                'No reproduction timestamp or duration was retained per attempt.'),
            'time_to_final_verdict_seconds': {
                'value': quantiles([a['elapsed_seconds'] for a in resolved]) if resolved else None,
                'unit': 'seconds',
                'denominator': 'attempts reaching an independent final verdict '
                               '(independently_verified true): %d of %d' % (len(resolved), len(attempts)),
                'source_field': 'attempts[].elapsed_seconds',
                'note': 'Time to a final verdict, accepting or rejecting. A rejected repair is a '
                        'verdict, not a resolution, so this is not a resolution time. The %d '
                        'unresolved attempts are excluded and reported as runtime below.'
                        % (len(attempts) - len(resolved))},
            'successful_resolution_time_seconds': unavailable(
                'elapsed_seconds measures wall-clock time to a verdict, not a resolution-specific '
                'interval, and no separate resolution timestamp was retained. The %d accepted '
                'attempts are reported under time_to_final_verdict_seconds instead.'
                % sum(1 for a in attempts if a['final_decision'] == 'accept_for_review')),
            'runtime_seconds_all_attempts': {
                'value': quantiles([a['elapsed_seconds'] for a in attempts]),
                'unit': 'seconds', 'denominator': 'all %d launched attempts' % len(attempts),
                'source_field': 'attempts[].elapsed_seconds',
                'note': 'Wall-clock runtime, not resolution time.'},
            'clean_workload_failures': {
                'value': len(clean_failures), 'unit': 'failing clean case instances',
                'denominator': '%d clean case instances across %d independently evaluated attempts'
                               % (clean_instances, len(evaluated)),
                'clean_cases': list(CLEAN_CASES),
                'clean_case_basis': 'evaluation/holdout.py sets fault=True only for %s' % (FAULT_CASES,),
                'source_field': 'attempts[].case_outcomes[].properties',
                'detail': clean_failures,
                'note': 'Counts clean case instances with a failed property or a non-accepting '
                        'case decision. Named failures, not regressions: the campaign retained no '
                        'baseline run of these cases, so no baseline-to-candidate comparison is '
                        'possible. Attempts that never reached evaluation contribute none.'},
            'lost_orders': unavailable(
                'No order-level count was retained. P3 is a property verdict, not a count of lost '
                'orders. Attempts with a P3 failure: %s.' % sorted(liveness_attempts)),
            'duplicate_effects': unavailable(
                'No duplicate-effect count was retained. P1 and P6 are property verdicts, not '
                'counts, and P1 did not fail in any evaluated attempt.'),
        },
        'limitations': [
            'Derived from retained fields only; no re-execution and no new measurement.',
            'Property statuses are pass, fail or not_applicable. not_applicable is not a failure.',
            'Metrics over evaluated attempts describe 4 of 12; the 8 unresolved attempts are '
            'preserved and counted in every denominator that mentions them.',
            'No variant ranking is supported or implied, per the frozen campaign.',
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='fail if the written view is stale')
    args = parser.parse_args(argv)
    text = SOURCE.read_text(encoding='utf-8')  # read_text normalizes CRLF to LF
    derived = derive(json.loads(text), text)
    rendered = json.dumps(derived, indent=2) + '\n'
    if args.check:
        if not TARGET.exists() or TARGET.read_text() != rendered:
            print('derived_metrics.json is stale; rerun scripts/derive-t8-metrics.py')
            return 1
        print('derived metrics are current')
        return 0
    # Fixed newline so the committed view is byte-identical on every platform.
    TARGET.write_text(rendered, newline='\n')
    print(json.dumps(derived['metrics'], indent=2)[:400])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
