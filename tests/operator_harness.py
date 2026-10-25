"""Shared operator-test harness. Test-only helper, never imported by the product.

Teardown is strict. A temporary tree that cannot be removed, a worker that is
still running, or an exception raised inside the Manager watcher thread fails the
test with diagnostics instead of being suppressed.

Three things the earlier harness got wrong:
  * ignore_cleanup_errors hid residual files rather than reporting them.
  * It waited for the subprocess but not for the watcher thread, so cleanup could
    delete the runs tree while the watcher was still writing the receipt and
    releasing the guard.
  * A daemon-thread exception prints to stderr and never fails a unittest, so a
    dead watcher looked like a passing run.
"""
import http.client
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.request
PROCESS_WAIT = 15.0
WATCHER_WAIT = 20.0
HTTP_TIMEOUT = 15.0
GET_ATTEMPTS = 3


class OperatorHarness(unittest.TestCase):
    """Real Manager and HTTP server over a temporary root, with real subprocesses."""

    timeout = 60.0

    def setUp(self):
        from incidentforge.ui import Manager, make_server
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'runs').mkdir()
        self.processes = []
        self.controls = {}
        self.watchers = []
        self.thread_errors = []
        self.transport_attempts = []
        self.handler_errors = []
        # Registered first, so it runs last: everything else must already be quiet.
        self.addCleanup(self.remove_temp)
        self.previous_hook = threading.excepthook
        threading.excepthook = self.record_thread_error
        self.addCleanup(self.finish)
        self.manager = Manager(self.root, self.spawn)
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.server = make_server(self.root, 0, self.manager)
        # socketserver swallows handler exceptions into handle_error, which
        # threading.excepthook never sees. Record them so a server-side fault
        # cannot look like a bare transport drop.
        self.server.handle_error = self.record_handler_error
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = 'http://127.0.0.1:' + str(self.server.server_port)

    # ----- subprocess management -------------------------------------------------

    def worker_command(self, run_id, incident, variant, control):
        raise NotImplementedError

    def spawn(self, run_id, incident, variant, backend, log):
        control = self.root / 'control' / run_id
        control.mkdir(parents=True, exist_ok=True)
        self.controls[run_id] = control
        process = subprocess.Popen(
            self.worker_command(run_id, incident, variant, control),
            stdout=log, stderr=log, stdin=subprocess.DEVNULL, cwd=str(REPO))
        self.processes.append(process)
        return process

    def note_watcher(self, before):
        for thread in threading.enumerate():
            if thread not in before and thread is not threading.current_thread():
                if thread not in self.watchers:
                    self.watchers.append(thread)

    def record_handler_error(self, request, client_address):
        """Separate a server fault from a client that has already gone away.

        socketserver calls this for any handler exception. A write to a socket the
        test client closed is a transport condition, counted and bounded with the
        other transport failures. Anything else is a real fault and fails the test.
        """
        import sys
        import traceback
        exc_type, exc, tb = sys.exc_info()
        if isinstance(exc, (ConnectionAbortedError, ConnectionResetError, BrokenPipeError)):
            self.transport_attempts.append('server write aborted: %r' % (exc,))
            return
        text = (''.join(traceback.format_exception(exc_type, exc, tb))[-1500:] if exc
                else 'handler error reported with no active exception')
        self.handler_errors.append(text)

    def record_thread_error(self, args):
        import traceback
        self.thread_errors.append(''.join(traceback.format_exception(
            args.exc_type, args.exc_value, args.exc_traceback))[-1500:])

    # ----- diagnostics -----------------------------------------------------------

    def diagnostics(self):
        lines = ['worker return codes: %r' % [p.poll() for p in self.processes]]
        lines.append('guard present: %s' % self.manager.guard.exists())
        if self.manager.guard.exists():
            try:
                lines.append('guard contents: %s' % self.manager.guard.read_text()[:200])
            except OSError as exc:
                lines.append('guard unreadable: %s' % exc)
        receipts = sorted(p.name for p in self.manager.meta.glob('ui-*.json'))
        lines.append('receipts: %r' % receipts)
        for run_id, control in self.controls.items():
            log = self.manager.meta / (run_id + '.log')
            if log.exists():
                tail = log.read_text(errors='replace')[-700:]
                if tail.strip():
                    lines.append('worker log %s tail:\n%s' % (run_id, tail))
        for error in self.thread_errors:
            lines.append('watcher thread exception:\n' + error)
        # These were recorded but never printed, so a failure reported a count
        # without the traceback that explains it.
        for error in self.handler_errors:
            lines.append('server handler exception:\n' + error)
        if self.transport_attempts:
            lines.append('loopback transport failures: %r' % (self.transport_attempts,))
        return '\n'.join(lines)

    # ----- teardown --------------------------------------------------------------

    def finish(self):
        threading.excepthook = self.previous_hook
        for control in self.controls.values():
            try:
                (control / 'proceed').write_text('cleanup', encoding='utf-8')
            except OSError:
                pass
        stuck = []
        for process in self.processes:
            try:
                process.wait(PROCESS_WAIT)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(5)
                stuck.append(process.pid)
        # The watcher writes the receipt and releases the guard after the process
        # exits. Deleting the tree before it finishes is the teardown race.
        for watcher in self.watchers:
            watcher.join(WATCHER_WAIT)
        alive = [w.name for w in self.watchers if w.is_alive()]
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(5)
        problems = []
        if stuck:
            problems.append('workers needed termination: %r' % stuck)
        if alive:
            problems.append('watcher threads still running: %r' % alive)
        if self.thread_errors:
            problems.append('%d exception(s) escaped a background thread' % len(self.thread_errors))
        if len(self.transport_attempts) > 5:
            problems.append('%d loopback transport failures: %r'
                            % (len(self.transport_attempts), self.transport_attempts[:5]))
        if self.handler_errors:
            problems.append('%d server-side handler exception(s)' % len(self.handler_errors))
        if [p for p in self.processes if p.poll() is None]:
            problems.append('a worker process survived teardown')
        if problems:
            raise AssertionError('; '.join(problems) + '\n' + self.diagnostics())

    def remove_temp(self):
        try:
            self.temp.cleanup()
        except OSError as exc:
            residual = []
            for path in sorted(self.root.rglob('*'))[:25]:
                if path.is_file():
                    residual.append(str(path.relative_to(self.root)))
            raise AssertionError('temporary tree was not removed: %s\nresidual files: %r'
                                 % (exc, residual)) from exc

    # ----- helpers ---------------------------------------------------------------

    def until(self, predicate, message, timeout=None):
        end = time.monotonic() + (timeout or self.timeout)
        while time.monotonic() < end:
            value = predicate()
            if value:
                return value
            time.sleep(0.05)
        self.fail('timed out waiting for ' + message + '\n' + self.diagnostics())

    def request(self, path, body=None, token=None, origin=None):
        headers = {}
        if token:
            headers['X-IncidentForge-Token'] = token
        if origin:
            headers['Origin'] = origin
        mutating = body is not None
        request = urllib.request.Request(
            self.url + path, data=json.dumps(body).encode() if mutating else None, headers=headers)
        # A mutating request is issued exactly once. A dropped response does not
        # mean the server did not act, so retrying could launch or cancel twice.
        # Only idempotent reads are retried, and HTTPError is a real response.
        attempts = 1 if mutating else GET_ATTEMPTS
        method = 'POST' if mutating else 'GET'
        last = None
        for attempt in range(attempts):
            try:
                with self.opener.open(request, timeout=HTTP_TIMEOUT) as response:
                    return response.status, response.read(), response.headers
            except ConnectionResetError as exc:
                last = exc
                self.transport_attempts.append('%s %s: %r' % (method, path, exc))
                if attempt + 1 < attempts:
                    time.sleep(0.05)
        raise AssertionError('loopback %s to %s failed after %d attempt(s): %r\n%s'
                             % (method, path, attempts, last, self.diagnostics()))

    def state(self):
        return json.loads(self.request('/api/state')[1])

    def launch(self, incident='IF-002', variant='B2'):
        before = set(threading.enumerate())
        status, raw, _ = self.request('/api/launch', {'incident': incident, 'variant': variant},
                                      self.state()['token'], self.url)
        self.assertEqual(202, status)
        run_id = json.loads(raw)['run_id']
        self.note_watcher(before)
        self.until(lambda: (self.controls[run_id] / 'ready').exists(), 'the worker to report ready')
        return run_id

    def settle(self, run_id):
        """Wait for the real process to exit and the watcher to finish its work."""
        self.until(lambda: self.processes[-1].poll() is not None, 'the worker process to exit')
        self.until(lambda: self.manager.active() is None, 'the launch guard to be cleared')
        receipt = self.manager.meta / (run_id + '.json')
        self.until(receipt.exists, 'the terminal receipt to be written')
        return json.loads(receipt.read_text())


REPO = Path(__file__).resolve().parents[1]
