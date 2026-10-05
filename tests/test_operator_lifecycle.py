"""Operator lifecycle across HTTP, the Manager watcher and a real subprocess.

Every scenario launches an actual local process through Manager's injectable
spawn seam, drives the real /api endpoints, and waits on explicit file signals
rather than sleeping. The project root, runs directory and ledger are temporary.
No inference or Sandbox client is imported, and the production runs/ tree,
ledger and credentials are never touched.
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
import urllib.error
import urllib.request
import zipfile

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'src'))
from incidentforge.ui import Manager, make_server

WORKER = REPO / 'tests' / 'local_worker.py'
TIMEOUT = 25.0
HTTP_TIMEOUT = 10.0


class OperatorLifecycleTests(unittest.TestCase):
    mode = 'complete'

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
             '--control', str(control), '--mode', self.mode,
             '--incident', incident, '--variant', variant],
            stdout=log, stderr=log, stdin=subprocess.DEVNULL, cwd=str(REPO))
        self.processes.append(process)
        return process

    def reap(self):
        """Never leak a worker, even when an assertion failed mid-scenario."""
        for control in self.controls.values():
            (control / 'proceed').write_text('cleanup', encoding='utf-8')
        for process in self.processes:
            try:
                process.wait(5)
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
            time.sleep(0.02)
        self.fail('timed out waiting for ' + message)

    def request(self, path, body=None, token=None, origin=None):
        headers = {}
        if token:
            headers['X-IncidentForge-Token'] = token
        if origin:
            headers['Origin'] = origin
        request = urllib.request.Request(
            self.url + path, data=json.dumps(body).encode() if body else None, headers=headers)
        # Bounded so one stalled request cannot outlast the outer polling deadline.
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
            return response.status, response.read(), response.headers

    def state(self):
        return json.loads(self.request('/api/state')[1])

    def token(self):
        return self.state()['token']

    def launch(self, incident='IF-002', variant='B2'):
        status, raw, _ = self.request('/api/launch', {'incident': incident, 'variant': variant},
                                      self.token(), self.url)
        self.assertEqual(202, status)
        run_id = json.loads(raw)['run_id']
        self.until(lambda: (self.controls[run_id] / 'ready').exists(), 'worker to report ready')
        return run_id

    def terminated(self, run_id):
        """Wait for the real process to exit and the watcher to clear the guard."""
        self.until(lambda: self.processes[-1].poll() is not None, 'the worker process to exit')
        self.until(lambda: self.manager.active() is None, 'the launch guard to be cleared')
        receipt = self.root / 'runs' / 'ui-launches' / (run_id + '.json')
        self.until(receipt.exists, 'the terminal receipt to be written')
        return json.loads(receipt.read_text())

    # 1. Normal completion, one run id from launch to export.
    def test_launch_progress_terminal_report_and_export(self):
        run_id = self.launch()
        active = self.state()['active']
        self.assertEqual(run_id, active['run_id'])
        self.assertEqual('live', active['status'])
        progress = json.loads(self.request('/api/runs/' + run_id)[1])
        self.assertEqual(run_id, progress['run_id'])
        self.assertIsNone(progress['decision'], 'a running worker must not show a verdict')
        self.assertEqual('IF-002', progress['incident'])

        (self.controls[run_id] / 'proceed').write_text('go', encoding='utf-8')
        receipt = self.terminated(run_id)
        self.assertEqual(0, receipt['exit_code'])
        self.assertTrue(receipt['terminal_confirmed'])

        final = json.loads(self.request('/api/runs/' + run_id)[1])
        self.assertEqual(run_id, final['run_id'], 'run id changed between launch and result')
        self.assertEqual('accept_for_review', final['decision'])
        self.assertEqual('REPORT', final['state'])
        self.assertEqual('verified', final['integrity'])
        self.assertEqual('rev-test', final['report']['candidate_revision'])
        on_disk = json.loads((self.root / 'runs' / run_id / 'report.json').read_text())
        self.assertEqual(on_disk['decision'], final['decision'])

        status, payload, headers = self.request('/api/runs/' + run_id + '/export')
        self.assertEqual(200, status)
        self.assertEqual('application/zip', headers['Content-Type'])
        self.assertIn(run_id, headers['Content-Disposition'])
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            review = json.loads(archive.read('review.json'))
        self.assertEqual(run_id, review['run_id'])
        self.assertEqual('accept_for_review', review['decision'])

    # 2. Cancellation confirmed by the subprocess actually exiting.
    def test_cancellation_is_observed_by_the_worker_and_confirmed_by_exit(self):
        self.mode = 'cancel'
        run_id = self.launch()
        result = json.loads(self.request('/api/cancel', {'run_id': run_id}, self.token(), self.url)[1])
        self.assertTrue(result['requested'])
        self.assertFalse(result['terminal_confirmed'],
                         'requesting cancellation must not be reported as termination')
        self.assertTrue((self.root / 'runs' / run_id / 'CANCEL').exists())
        active = self.manager.active()
        if active is not None:  # the worker may already have exited
            self.assertTrue(active['cancel_requested'])

        receipt = self.terminated(run_id)
        self.assertEqual(1, receipt['exit_code'], 'worker did not exit on the cancellation path')
        self.assertTrue(receipt['terminal_confirmed'])
        self.assertIsNone(self.manager.active())

        final = json.loads(self.request('/api/runs/' + run_id)[1])
        self.assertEqual('unresolved', final['decision'])
        self.assertIn('Cancelled', final['report']['reason'])
        self.assertIsNone(final['report']['candidate_revision'])
        self.assertEqual('verified', final['integrity'])
        self.assertIn('Cancelled: cancelled before action',
                      [row['label'] for row in final['timeline']])

    # 3. Unexpected nonzero exit before any terminal report.
    def test_unexpected_worker_exit_is_not_live_and_not_accepted(self):
        self.mode = 'crash'
        run_id = self.launch()
        (self.controls[run_id] / 'proceed').write_text('go', encoding='utf-8')
        receipt = self.terminated(run_id)
        self.assertEqual(3, receipt['exit_code'])
        self.assertTrue(receipt['terminal_confirmed'])

        self.assertIsNone(self.manager.active(), 'a crashed run must not still look live')
        self.assertIsNone(self.state()['active'])
        self.assertFalse((self.root / 'runs' / run_id / 'report.json').exists())

        final = json.loads(self.request('/api/runs/' + run_id)[1])
        self.assertIsNone(final['report'], 'a crashed run must not present a report')
        self.assertIsNone(final['decision'])
        self.assertNotEqual('accept_for_review', final['decision'])
        self.assertEqual('pending', final['integrity'])
        self.assertTrue(final['process_terminal'])
        self.assertEqual(3, final['process_exit'])
        # Diagnostic evidence is retained rather than discarded.
        self.assertIn('worker exited unexpectedly', [row['label'] for row in final['timeline']])
        self.assertGreaterEqual(final['event_count'], 2)
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.request('/api/runs/' + run_id + '/export')
        self.assertEqual(400, caught.exception.code)
        # A docker-backend run never creates the unconfirmed remote-operation guard.
        self.assertFalse((self.root / 'runs' / 'contree-active.json').exists())

    def test_guard_clears_even_if_the_first_unlink_hits_a_sharing_violation(self):
        """A console poll holding the guard open must not strand it.

        Windows refuses to delete a file another handle has open. The watcher used
        a bare unlink, so one unlucky /api/state poll killed the watcher thread and
        left the run looking live forever, refusing every later launch.
        """
        from unittest.mock import patch
        run_id = self.launch()
        real = Path.unlink
        failed = {'n': 0}

        def flaky(path, *args, **kwargs):
            if path.name == 'active.json' and failed['n'] < 1:
                failed['n'] += 1
                raise PermissionError(32, 'in use by another process')
            return real(path, *args, **kwargs)

        with patch.object(Path, 'unlink', flaky):
            (self.controls[run_id] / 'proceed').write_text('go', encoding='utf-8')
            self.until(lambda: self.processes[-1].poll() is not None, 'the worker to exit')
            self.until(lambda: self.manager.active() is None,
                       'the guard to clear despite a sharing violation')
        self.assertEqual(1, failed['n'], 'the sharing violation was never exercised')
        # The operator can launch again rather than being stuck behind a dead run.
        second = self.launch(incident='IF-001', variant='B0')
        self.assertNotEqual(run_id, second)

    # 4. Reconnect during the run, then launch again after confirmed termination.
    def test_reconnect_does_not_duplicate_and_a_later_launch_is_allowed(self):
        run_id = self.launch()
        for _ in range(3):
            active = self.state()['active']
            self.assertEqual(run_id, active['run_id'])
            self.assertEqual('live', active['status'])
        self.assertEqual(1, len(self.processes), 'a reconnect started another worker')
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.request('/api/launch', {'incident': 'IF-001', 'variant': 'B0'}, self.token(), self.url)
        self.assertEqual(400, caught.exception.code)
        self.assertEqual(1, len(self.processes))

        (self.controls[run_id] / 'proceed').write_text('go', encoding='utf-8')
        self.terminated(run_id)

        second = self.launch(incident='IF-001', variant='B0')
        self.assertNotEqual(run_id, second)
        self.assertEqual(2, len(self.processes))
        self.assertEqual(second, self.state()['active']['run_id'])
        (self.controls[second] / 'proceed').write_text('go', encoding='utf-8')
        self.until(lambda: self.manager.active() is None, 'the second run to clear the guard')
        listed = {row['run_id'] for row in self.state()['runs']}
        self.assertEqual({run_id, second}, listed & {run_id, second})


if __name__ == '__main__':
    unittest.main()
