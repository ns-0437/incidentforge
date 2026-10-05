"""The harness must never retry a mutating request, and must bound GET retries.

A dropped response does not mean the server did not act. Retrying POST /api/launch
could start a second run; retrying POST /api/cancel could cancel a later one. These
tests pin that policy so a future convenience change cannot reintroduce it.
"""
import json
from pathlib import Path
import sys
import unittest
import urllib.error

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'src'))
from tests.operator_harness import OperatorHarness, GET_ATTEMPTS


class TransportPolicyTests(OperatorHarness):
    """No worker is ever started here; spawn would fail loudly if it were."""

    def worker_command(self, run_id, incident, variant, control):
        raise AssertionError('this suite must not start a worker')

    def dropping_opener(self, fail_paths, drops=99):
        """Count attempts per path and raise a transport drop for the chosen ones."""
        harness = self
        real = self.opener

        class Counting:
            def __init__(self):
                self.attempts = []

            def open(self, request, timeout=None):
                path = request.full_url[len(harness.url):]
                self.attempts.append(path)
                if path in fail_paths and self.attempts.count(path) <= drops:
                    raise ConnectionResetError(10054, 'connection forcibly closed')
                return real.open(request, timeout=timeout)

        counting = Counting()
        self.opener = counting
        return counting

    def test_a_failed_post_is_issued_exactly_once(self):
        counting = self.dropping_opener({'/api/launch'})
        token = self.state()['token']
        with self.assertRaises(AssertionError) as caught:
            self.request('/api/launch', {'incident': 'IF-002', 'variant': 'B2'}, token, self.url)
        self.assertIn('after 1 attempt', str(caught.exception))
        self.assertEqual(1, counting.attempts.count('/api/launch'),
                         'a mutating request was retried')
        self.assertEqual(1, len(self.transport_attempts))

    def test_a_failed_cancel_is_issued_exactly_once(self):
        counting = self.dropping_opener({'/api/cancel'})
        token = self.state()['token']
        with self.assertRaises(AssertionError):
            self.request('/api/cancel', {'run_id': 'ui-' + '0' * 32}, token, self.url)
        self.assertEqual(1, counting.attempts.count('/api/cancel'))

    def test_get_retries_follow_the_declared_bounded_policy(self):
        counting = self.dropping_opener({'/api/state'}, drops=GET_ATTEMPTS - 1)
        state = self.state()
        self.assertIn('token', state, 'a bounded GET retry should have recovered')
        self.assertEqual(GET_ATTEMPTS, counting.attempts.count('/api/state'))
        self.assertEqual(GET_ATTEMPTS - 1, len(self.transport_attempts))

    def test_get_gives_up_after_the_declared_bound(self):
        counting = self.dropping_opener({'/api/state'})
        with self.assertRaises(AssertionError) as caught:
            self.state()
        self.assertIn('after %d attempt' % GET_ATTEMPTS, str(caught.exception))
        self.assertEqual(GET_ATTEMPTS, counting.attempts.count('/api/state'))
        self.transport_attempts.clear()  # expected by this test, not a defect

    def test_a_lost_launch_response_does_not_become_a_second_launch(self):
        """The server acts, the response is lost, and the client must not retry."""
        import threading
        real = self.opener
        started = []

        class Immediate:
            def wait(self):
                return 0

        def spawn(run_id, incident, variant, backend, log):
            # The server really acts: a guard is written and a watcher starts.
            started.append(run_id)
            return Immediate()

        self.manager.spawn = spawn
        before = set(threading.enumerate())

        class LosesTheLaunchResponse:
            def open(self, request, timeout=None):
                response = real.open(request, timeout=timeout)
                if request.full_url.endswith('/api/launch'):
                    raise ConnectionResetError(10054, 'response lost after the server acted')
                return response

        token = self.state()['token']
        self.opener = LosesTheLaunchResponse()
        with self.assertRaises(AssertionError):
            self.request('/api/launch', {'incident': 'IF-002', 'variant': 'B2'}, token, self.url)
        self.opener = real
        self.note_watcher(before)
        self.assertEqual(1, len(started), 'the client turned one lost response into two launches')
        # The launch really happened, so the guard must drain through the watcher.
        self.until(lambda: self.manager.active() is None, 'the launched run to settle')
        self.assertEqual(1, len(started), 'a settled run was relaunched by the client')
        self.transport_attempts.clear()


if __name__ == '__main__':
    unittest.main()
