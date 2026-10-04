"""Assert the restricted Docker acceptance stages actually produced clean reports.

The stage probes already exit non-zero on failure, so this guards the case the
exit code cannot express: a stage that never ran, wrote no report, or quietly
executed fewer tests than the suite it claims to cover. Counts are pinned so a
shrinking suite fails instead of passing with less coverage.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

# stage -> (expected test count, modules the stage loads)
EXPECTED = {
    't1': (34, 'tests.test_store + tests.test_linux_boundary + tests.test_t1'),
    't2': (32, 'tests.test_store + tests.test_t2_storage + tests.test_t2'),
    't6': (19, 'tests.test_t6.CompensationTests, which inherits the 12 ContractTests methods'),
}


def latest(stage):
    runs = sorted((ROOT / 'runs').glob(stage + '-linux-*'))
    return runs[-1] if runs else None


def main():
    problems, summary = [], []
    for stage, (expected, modules) in EXPECTED.items():
        directory = latest(stage)
        if directory is None:
            problems.append('%s: no runs/%s-linux-* directory; the stage did not run' % (stage, stage))
            continue
        report = directory / 'report.json'
        if not report.exists():
            problems.append('%s: %s is missing; the stage produced no result' % (stage, report))
            continue
        data = json.loads(report.read_text())
        run = data.get('tests_run', data.get('tests'))
        failures, errors = data.get('failures'), data.get('errors')
        skipped = data.get('skipped', data.get('skips'))
        skip_count = skipped if isinstance(skipped, int) else len(skipped or [])
        if failures: problems.append('%s: %d failures' % (stage, failures))
        if errors: problems.append('%s: %d errors' % (stage, errors))
        if skip_count: problems.append('%s: %d skipped; the Linux suite must not skip in CI' % (stage, skip_count))
        if run != expected:
            problems.append('%s: ran %r tests, expected %d (%s)' % (stage, run, expected, modules))
        summary.append({'stage': stage, 'tests_run': run, 'expected': expected,
                        'failures': failures, 'errors': errors, 'skipped': skip_count,
                        'evidence': str(directory.relative_to(ROOT))})
    print(json.dumps({'stages': summary, 'problems': problems}, indent=2))
    if problems:
        print('\nLinux acceptance did not pass cleanly.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
