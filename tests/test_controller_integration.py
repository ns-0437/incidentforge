"""Operator HTTP launch through the real Controller to detail response and export.

A deterministic integration double. Only the model and the execution backend are
simulated, through the constructor seams Controller already takes. Workspace,
Evidence, the investigation schema and validator, the edit and compile gates, the
authored-regression gate, the B2 feedback limit, freeze and the final
verification step all execute as production code in a real subprocess.

The controller consumes simulated protected results. The real protected evaluator
does not execute here, so this says nothing about protected evaluation itself,
and nothing about live model reliability. No Sandbox execution occurs.
"""
import io
import json
from pathlib import Path
import sys
import zipfile

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'src'))
from tests.operator_harness import OperatorHarness

WORKER = REPO / 'tests' / 'controller_worker.py'


class ControllerThroughOperatorTests(OperatorHarness):
    final = 'accept'

    def worker_command(self, run_id, incident, variant, control):
        return [sys.executable, str(WORKER), '--root', str(self.root), '--run-id', run_id,
                '--control', str(control), '--incident', incident, '--variant', variant,
                '--final', self.final]

    def run_to_completion(self):
        """Launch through HTTP, let the real controller finish, return everything."""
        run_id = self.launch()
        self.assertEqual(run_id, self.state()['active']['run_id'])
        self.settle(run_id)
        exit_code = self.processes[-1].returncode
        on_disk = json.loads((self.root / 'runs' / run_id / 'report.json').read_text())
        detail = json.loads(self.request('/api/runs/' + run_id)[1])
        return run_id, exit_code, on_disk, detail

    def export(self, run_id):
        status, payload, headers = self.request('/api/runs/' + run_id + '/export')
        self.assertEqual(200, status)
        self.assertEqual('application/zip', headers['Content-Type'])
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            return json.loads(archive.read('review.json'))

    def test_successful_if002_repair_reaches_the_operator_and_the_export(self):
        self.final = 'accept'
        run_id, exit_code, report, detail = self.run_to_completion()

        # The controller's own verdict, produced by its gates rather than scripted.
        self.assertEqual('accept_for_review', report['decision'])
        self.assertEqual(0, exit_code)
        self.assertTrue(report['candidate_revision'], 'no frozen candidate revision')
        self.assertEqual(['fixture/app/service.py'], report['verified_work']['changed_source_paths'])
        self.assertTrue(report['verified_work']['developer_test_file_present'])
        self.assertTrue(report['verified_work']['developer_tests_executed_on_current_revision'])
        self.assertTrue(report['verified_work']['developer_tests_passed_on_current_revision'])
        self.assertEqual(1, report['protected_feedback_requests'])

        # The operator response agrees with it, for the same run id.
        self.assertEqual(run_id, detail['run_id'])
        self.assertEqual('IF-002', detail['incident'])
        self.assertEqual('B2', detail['variant'])
        self.assertEqual(report['decision'], detail['decision'])
        self.assertEqual(report['candidate_revision'], detail['report']['candidate_revision'])
        self.assertEqual('verified', detail['integrity'])
        self.assertTrue(detail['diffs'], 'no reviewable patch reached the operator')

        review = self.export(run_id)
        self.assertEqual(run_id, review['run_id'])
        self.assertEqual(report['decision'], review['decision'])
        self.assertEqual(report['candidate_revision'], review['report']['candidate_revision'])

    def test_failed_final_validation_is_not_rescued_by_passing_feedback(self):
        self.final = 'reject'
        run_id, exit_code, report, detail = self.run_to_completion()

        # The same candidate work happened, and the intermediate feedback passed.
        self.assertEqual(1, report['protected_feedback_requests'])
        self.assertEqual('accept_for_review', report['protected_feedback']['decision'],
                         'this scenario requires the intermediate feedback to pass')
        self.assertTrue(report['candidate_revision'])
        self.assertTrue(report['verified_work']['developer_tests_passed_on_current_revision'])

        # The final independent verification decides, and it rejected.
        self.assertEqual('reject_behavior', report['decision'])
        self.assertEqual(1, exit_code)
        self.assertEqual('reject_behavior', detail['decision'])
        self.assertEqual('verified', detail['integrity'])
        review = self.export(run_id)
        self.assertEqual('reject_behavior', review['decision'])
        for layer, value in (('report', report['decision']), ('operator', detail['decision']),
                             ('export', review['decision'])):
            self.assertNotEqual('accept_for_review', value,
                                layer + ' presented an accepted verdict after a failed final check')


if __name__ == '__main__':
    unittest.main()
