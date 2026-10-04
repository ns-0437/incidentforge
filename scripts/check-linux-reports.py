"""Assert the restricted Docker acceptance stages produced clean, complete reports.

The stage probes exit non-zero on failure, so this guards what an exit code cannot
express: a stage that never ran, wrote no report, or quietly executed fewer tests
than the suite it claims to cover. It fails closed. A field that is missing, of the
wrong type, or negative is a failure, not a zero.

Two producer schemas exist and are declared rather than guessed:
  probes/run_t1.py and probes/run_t2.py emit status/tests_run/failures/errors and
  skipped as a list; probes/run_t6.py emits complete/tests/failures/errors and
  skips as an integer.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

# stage -> expected executed tests, count field, skip field and its type,
# completion gate, and the suite the stage loads.
SCHEMAS = {
    't1': {'expected': 34, 'count': 'tests_run', 'skips': ('skipped', list), 'gate': ('status', 'PASS'),
           'modules': 'tests.test_store + tests.test_linux_boundary + tests.test_t1'},
    't2': {'expected': 32, 'count': 'tests_run', 'skips': ('skipped', list), 'gate': ('status', 'PASS'),
           'modules': 'tests.test_store + tests.test_t2_storage + tests.test_t2'},
    't6': {'expected': 19, 'count': 'tests', 'skips': ('skips', int), 'gate': ('complete', True),
           'modules': 'tests.test_t6.CompensationTests, which inherits the 12 ContractTests methods'},
}
ALIASES = {'tests_run': 'tests', 'tests': 'tests_run', 'skipped': 'skips', 'skips': 'skipped'}


def counted(value):
    """A real nonnegative integer. bool is not a count."""
    return type(value) is int and value >= 0


def check_stage(stage, schema, directory, problems):
    if directory is None:
        problems.append('%s: no runs/%s-linux-* directory; the stage did not run' % (stage, stage))
        return None
    report = directory / 'report.json'
    if not report.exists():
        problems.append('%s: %s is missing; the stage produced no result' % (stage, report))
        return None
    try:
        data = json.loads(report.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        problems.append('%s: report.json is not readable JSON: %s' % (stage, exc))
        return None
    if not isinstance(data, dict):
        problems.append('%s: report.json root is %s, expected an object' % (stage, type(data).__name__))
        return None

    count_field, (skip_field, skip_type) = schema['count'], schema['skips']
    gate_field, gate_value = schema['gate']
    for field in (count_field, skip_field, gate_field, 'failures', 'errors'):
        if field not in data:
            problems.append('%s: report.json has no %r field' % (stage, field))
    # An alias carrying a different value means the report is self-contradictory.
    for field in (count_field, skip_field):
        other = ALIASES[field]
        if other in data and data[other] != data.get(field):
            problems.append('%s: %r and %r disagree (%r vs %r)'
                            % (stage, field, other, data.get(field), data[other]))
    if problems and any(p.startswith('%s: report.json has no' % stage) for p in problems):
        return None

    for field in ('failures', 'errors'):
        if not counted(data[field]):
            problems.append('%s: %r is %r, expected a nonnegative integer' % (stage, field, data[field]))
        elif data[field]:
            problems.append('%s: %d %s' % (stage, data[field], field))
    if not counted(data[count_field]):
        problems.append('%s: %r is %r, expected a nonnegative integer' % (stage, count_field, data[count_field]))
    elif data[count_field] != schema['expected']:
        problems.append('%s: ran %d tests, expected %d (%s)'
                        % (stage, data[count_field], schema['expected'], schema['modules']))
    skips = data[skip_field]
    if skip_type is list:
        if not isinstance(skips, list):
            problems.append('%s: %r is %r, expected a list' % (stage, skip_field, skips))
            skip_count = None
        else:
            skip_count = len(skips)
    else:
        skip_count = skips if counted(skips) else None
        if skip_count is None:
            problems.append('%s: %r is %r, expected a nonnegative integer' % (stage, skip_field, skips))
    if skip_count:
        problems.append('%s: %d skipped; the Linux suite must not skip in CI' % (stage, skip_count))
    if data[gate_field] is not gate_value and data[gate_field] != gate_value:
        problems.append('%s: %r is %r, expected %r' % (stage, gate_field, data[gate_field], gate_value))
    return {'stage': stage, 'tests_run': data.get(count_field), 'expected': schema['expected'],
            'failures': data.get('failures'), 'errors': data.get('errors'), 'skipped': skip_count,
            gate_field: data.get(gate_field), 'evidence': directory.name}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--runs', type=Path, default=None,
                        help='directory holding <stage>-linux-* result directories')
    args = parser.parse_args(argv)
    runs = args.runs if args.runs is not None else ROOT / 'runs'
    problems, summary = [], []
    for stage, schema in SCHEMAS.items():
        found = sorted(runs.glob(stage + '-linux-*')) if runs.is_dir() else []
        row = check_stage(stage, schema, found[-1] if found else None, problems)
        if row is not None:
            summary.append(row)
    print(json.dumps({'runs': str(runs), 'stages': summary, 'problems': problems}, indent=2))
    if problems:
        print('\nLinux acceptance did not pass cleanly.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
