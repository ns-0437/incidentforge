"""Operator HTTP launch through the real Controller to detail response and export.

A deterministic integration double. Only the model and the execution backend are
simulated, through the constructor seams Controller already takes. Workspace,
Evidence, the investigation schema and validator, the edit and compile gates, the
authored-regression gate, the B2 feedback limit, freeze and the final independent
verification all execute as production code in a real subprocess.

It is not evidence about live model reliability and performs no Sandbox execution.
Project root, runs directory and budget ledger are temporary.
"""
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
import zipfile

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'src'))
from incidentforge.ui import Manager, make_server

WORKER = REPO / 'tests' / 'controller_worker.py'
TIMEOUT = 60.0
HTTP_TIMEOUT = 15.0


class ControllerThroughOperatorTests(unittest.TestCase):
    final = 'accept'

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'runs').mkdir()
        self.processes = []
        self.controls = {}
        self.addCleanup(self.reap)
        self.manager = Manager(self.root, self.spawn)
        self.server = make_server(self.root, 0, self.manager)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.url = 'http://127.0.0.1:' + str(self.server.server_port)

    def spawn(self, run_id, incident, variant, backend, log):
        control = self.root / 'control' / run_id
        control.mkdir(parents=True)
        self.controls[run_id] = control
        process = subprocess.Popen(
            [sys.executable, str(WORKER), '--root', str(self.root), '--run-id', run_id,
             '--control', str(control), '--incident', incident, '--variant', variant,
             '--final', self.final],
            stdout=log, stderr=log, stdin=subprocess.DEVNULL, cwd=str(REPO))
        self.processes.append(process)
        return process

    def reap(self):
        for process in self.processes:
            try:
                process.wait(10)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(5)
        self.assertEqual([], [p for p in self.processes if p.poll() is None])

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(5)

    def until(self, predicate, message, timeout=TIMEOUT):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            value = predicate()
            if value:
                return value
            time.sleep(0.05)
        self.fail('timed out waiting for ' + message)

    def request(self, path, body=None, token=None, origin=None):
        headers = {}
        if token:
            headers['X-IncidentForge-Token'] = token
        if origin:
            headers['Origin'] = origin
        request = urllib.request.Request(
            self.url + path, data=json.dumps(body).encode() if body else None, headers=headers)
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
            return response.status, response.read(), response.headers

    def state(self):
        return json.loads(self.request('/api/state')[1])

    def run_to_completion(self):
        """Launch through HTTP, let the real controller finish, return everything."""
        status, raw, _ = self.request('/api/launch', {'incident': 'IF-002', 'variant': 'B2'},
                                      self.state()['token'], self.url)
        self.assertEqual(202, status)
        run_id = json.loads(raw)['run_id']
        self.until(lambda: (self.controls[run_id] / 'ready').exists(), 'the controller bundle')
        self.assertEqual(run_id, self.state()['active']['run_id'])
        self.until(lambda: self.processes[-1].poll() is not None, 'the controller process to exit')
        self.until(lambda: self.manager.active() is None, 'the launch guard to clear')
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
