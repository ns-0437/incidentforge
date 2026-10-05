"""Operator lifecycle across HTTP, the Manager watcher and a real subprocess.

Every scenario launches an actual local process through Manager's injectable
spawn seam, drives the real /api endpoints, and waits on explicit file signals
rather than sleeping. The project root, runs directory and ledger are temporary.
No inference or Sandbox client is imported, and the production runs/ tree,
ledger and credentials are never touched.
"""
import io
import json
import zipfile
from pathlib import Path
import sys
import unittest
import urllib.error

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'src'))
from tests.operator_harness import OperatorHarness

WORKER = REPO / 'tests' / 'local_worker.py'


class OperatorLifecycleTests(OperatorHarness):
    mode = 'complete'

    def worker_command(self, run_id, incident, variant, control):
        return [sys.executable, str(WORKER), '--root', str(self.root), '--run-id', run_id,
                '--control', str(control), '--mode', self.mode,
                '--incident', incident, '--variant', variant]

    def terminated(self, run_id):
        return self.settle(run_id)

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
        result = json.loads(self.request('/api/cancel', {'run_id': run_id}, self.state()['token'], self.url)[1])
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

    def test_watcher_survives_a_transient_guard_read_failure(self):
        """_watch reads the guard before its protected release block."""
        from unittest.mock import patch
        import incidentforge.ui as ui
        run_id = self.launch()
        real = ui.read_json
        hits = {'n': 0}

        def flaky(path, *args, **kwargs):
            if path.name == 'active.json' and hits['n'] < 1:
                hits['n'] += 1
                raise PermissionError(13, 'Permission denied')
            return real(path, *args, **kwargs)

        with patch.object(ui, 'read_json', flaky):
            (self.controls[run_id] / 'proceed').write_text('go', encoding='utf-8')
            receipt = self.settle(run_id)
        self.assertEqual(1, hits['n'], 'the blocked read was never exercised')
        self.assertTrue(receipt['terminal_confirmed'])
        self.assertEqual(0, receipt['exit_code'])
        self.assertNotIn('guard_read_error', receipt, 'a transient read should have recovered')
        self.assertFalse(self.manager.guard.exists())
        self.assertEqual([], self.thread_errors)

    def test_watcher_records_a_permanently_unreadable_guard_and_keeps_it(self):
        from unittest.mock import patch
        import incidentforge.ui as ui
        run_id = self.launch()
        real = ui.read_json

        def blocked(path, *args, **kwargs):
            if path.name == 'active.json': raise PermissionError(13, 'Permission denied')
            return real(path, *args, **kwargs)

        receipt_path = self.manager.meta / (run_id + '.json')
        with patch.object(ui, 'read_json', blocked):
            (self.controls[run_id] / 'proceed').write_text('go', encoding='utf-8')
            self.until(lambda: self.processes[-1].poll() is not None, 'the worker to exit')
            self.until(receipt_path.exists, 'a receipt despite the unreadable guard')
        receipt = json.loads(receipt_path.read_text())
        # Local process termination is still recorded, with what is certain only.
        self.assertTrue(receipt['terminal_confirmed'])
        self.assertEqual(0, receipt['exit_code'])
        self.assertEqual(run_id, receipt['run_id'])
        self.assertIn('PermissionError', receipt.get('guard_read_error', ''))
        self.assertIn('PermissionError', receipt.get('guard_release_error', ''))
        # Ownership could not be established, so the guard is left alone.
        self.assertTrue(self.manager.guard.exists(), 'an unattributable guard was erased')
        self.assertEqual([], self.thread_errors, 'the watcher died instead of recording')
        self.manager.release_guard(run_id=run_id)

    def test_watcher_never_erases_a_guard_owned_by_another_run(self):
        run_id = self.launch()
        (self.controls[run_id] / 'proceed').write_text('go', encoding='utf-8')
        self.until(lambda: self.processes[-1].poll() is not None, 'the worker to exit')
        self.until(lambda: self.manager.active() is None, 'the guard to clear')
        # A later launch writes its own guard; the finished run must not remove it.
        self.manager.guard.write_text(json.dumps({'run_id': 'ui-' + 'f' * 32}))
        self.assertFalse(self.manager.release_guard(run_id=run_id))
        self.assertTrue(self.manager.guard.exists())
        self.manager.guard.unlink()

    def test_a_permanently_stuck_guard_is_recorded_instead_of_killing_the_watcher(self):
        """Deterministic fault injection: the guard can never be unlinked.

        The watcher must still write a terminal receipt, record why the guard
        survived, and leave the stuck guard in place rather than dying silently.
        """
        from unittest.mock import patch
        run_id = self.launch()
        real = Path.unlink

        def blocked(path, *args, **kwargs):
            if path.name == 'active.json':
                raise PermissionError(32, 'in use by another process')
            return real(path, *args, **kwargs)

        receipt_path = self.manager.meta / (run_id + '.json')
        with patch.object(Path, 'unlink', blocked):
            (self.controls[run_id] / 'proceed').write_text('go', encoding='utf-8')
            self.until(lambda: self.processes[-1].poll() is not None, 'the worker to exit')
            self.until(receipt_path.exists, 'a terminal receipt despite the stuck guard')
        receipt = json.loads(receipt_path.read_text())
        self.assertTrue(receipt['terminal_confirmed'])
        self.assertEqual(0, receipt['exit_code'])
        self.assertIn('PermissionError', receipt.get('guard_release_error', ''),
                      'the watcher did not record why the guard survived')
        self.assertTrue(self.manager.guard.exists(), 'a stuck guard must not vanish silently')
        self.assertEqual([], self.thread_errors, 'the watcher thread died instead of recording')
        # Clear the injected condition so teardown finds a quiet tree.
        self.manager.release_guard(run_id=run_id)

    # 4. Reconnect during the run, then launch again after confirmed termination.
    def test_reconnect_does_not_duplicate_and_a_later_launch_is_allowed(self):
        run_id = self.launch()
        for _ in range(3):
            active = self.state()['active']
            self.assertEqual(run_id, active['run_id'])
            self.assertEqual('live', active['status'])
        self.assertEqual(1, len(self.processes), 'a reconnect started another worker')
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.request('/api/launch', {'incident': 'IF-001', 'variant': 'B0'}, self.state()['token'], self.url)
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
