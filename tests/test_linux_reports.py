"""The Linux acceptance report check must fail closed, never on absent fields.

Every case writes synthetic reports into a temporary directory and passes it with
--runs. Nothing here reads or writes the real runs/ tree.
"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('check_linux_reports', ROOT / 'scripts' / 'check-linux-reports.py')
checker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(checker)

GOOD = {
    't1': {'status': 'PASS', 'tests_run': 34, 'failures': 0, 'errors': 0, 'skipped': []},
    't2': {'status': 'PASS', 'tests_run': 32, 'failures': 0, 'errors': 0, 'skipped': []},
    't6': {'complete': True, 'tests': 19, 'failures': 0, 'errors': 0, 'skips': 0},
}


class LinuxReportCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.runs = Path(self.temp.name) / 'runs'
        self.runs.mkdir()

    def write(self, reports):
        for stage, body in reports.items():
            directory = self.runs / (stage + '-linux-20260101-000000')
            directory.mkdir(exist_ok=True)
            text = body if isinstance(body, str) else json.dumps(body)
            (directory / 'report.json').write_text(text)

    def check(self, reports):
        for existing in self.runs.glob('*'):
            for child in existing.glob('*'): child.unlink()
            existing.rmdir()
        self.write(reports)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            with contextlib.redirect_stderr(io.StringIO()):
                code = checker.main(['--runs', str(self.runs)])
        return code, json.loads(buffer.getvalue())['problems']

    def assertRejected(self, reports, fragment):
        code, problems = self.check(reports)
        self.assertEqual(1, code, 'expected rejection, got acceptance')
        self.assertTrue(any(fragment in p for p in problems),
                        'no problem mentioned %r; got %r' % (fragment, problems))

    def test_valid_reports_from_all_three_schemas_pass(self):
        code, problems = self.check(GOOD)
        self.assertEqual([], problems)
        self.assertEqual(0, code)

    def test_report_carrying_only_the_expected_count_is_rejected(self):
        self.assertRejected({'t1': {'tests_run': 34}, 't2': {'tests_run': 32}, 't6': {'tests': 19}},
                            "has no 'failures' field")

    def test_missing_status_and_completion_fields_are_rejected(self):
        self.assertRejected({**GOOD, 't1': {'tests_run': 34, 'failures': 0, 'errors': 0, 'skipped': []}},
                            "has no 'status' field")
        self.assertRejected({**GOOD, 't6': {'tests': 19, 'failures': 0, 'errors': 0, 'skips': 0}},
                            "has no 'complete' field")

    def test_false_completion_and_failing_status_are_rejected(self):
        self.assertRejected({**GOOD, 't6': {**GOOD['t6'], 'complete': False}}, "'complete' is False")
        self.assertRejected({**GOOD, 't1': {**GOOD['t1'], 'status': 'FAIL'}}, "'status' is 'FAIL'")

    def test_missing_failure_and_error_counts_are_rejected(self):
        self.assertRejected({**GOOD, 't1': {'status': 'PASS', 'tests_run': 34, 'skipped': []}},
                            "has no 'failures' field")
        self.assertRejected({**GOOD, 't2': {'status': 'PASS', 'tests_run': 32, 'failures': 0, 'skipped': []}},
                            "has no 'errors' field")

    def test_missing_skip_field_is_rejected_rather_than_treated_as_zero(self):
        self.assertRejected({**GOOD, 't2': {'status': 'PASS', 'tests_run': 32, 'failures': 0, 'errors': 0}},
                            "has no 'skipped' field")
        self.assertRejected({**GOOD, 't6': {'complete': True, 'tests': 19, 'failures': 0, 'errors': 0}},
                            "has no 'skips' field")

    def test_nonzero_failures_errors_and_skips_are_rejected(self):
        self.assertRejected({**GOOD, 't2': {**GOOD['t2'], 'failures': 3}}, '3 failures')
        self.assertRejected({**GOOD, 't1': {**GOOD['t1'], 'errors': 1}}, '1 errors')
        self.assertRejected({**GOOD, 't6': {**GOOD['t6'], 'skips': 2}}, '2 skipped')
        self.assertRejected({**GOOD, 't1': {**GOOD['t1'], 'skipped': [['case', 'why']]}}, '1 skipped')

    def test_bool_string_and_negative_counts_are_rejected(self):
        for stage, field, value in (('t1', 'failures', True), ('t2', 'errors', '0'),
                                    ('t1', 'tests_run', -34), ('t6', 'skips', -1),
                                    ('t6', 'tests', True)):
            with self.subTest(stage=stage, field=field, value=value):
                self.assertRejected({**GOOD, stage: {**GOOD[stage], field: value}},
                                    'expected a nonnegative integer')

    def test_wrong_executed_count_is_rejected(self):
        self.assertRejected({**GOOD, 't6': {**GOOD['t6'], 'tests': 18}}, 'ran 18 tests, expected 19')

    def test_conflicting_aliases_are_rejected(self):
        self.assertRejected({**GOOD, 't1': {**GOOD['t1'], 'tests': 1}}, 'disagree')
        self.assertRejected({**GOOD, 't6': {**GOOD['t6'], 'skipped': [['x', 'y']]}}, 'disagree')

    def test_malformed_json_and_wrong_root_type_are_rejected(self):
        self.assertRejected({**GOOD, 't6': '{not json'}, 'not readable JSON')
        self.assertRejected({**GOOD, 't6': '[]'}, 'root is list')

    def test_missing_stage_directory_and_missing_report_are_rejected(self):
        self.assertRejected({'t1': GOOD['t1'], 't2': GOOD['t2']}, 'the stage did not run')
        code, problems = self.check(GOOD)
        self.assertEqual(0, code)
        (self.runs / 't6-linux-20260101-000000' / 'report.json').unlink()
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            with contextlib.redirect_stderr(io.StringIO()):
                code = checker.main(['--runs', str(self.runs)])
        self.assertEqual(1, code)
        self.assertTrue(any('produced no result' in p for p in json.loads(buffer.getvalue())['problems']))


if __name__ == '__main__':
    unittest.main()
