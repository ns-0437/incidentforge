"""Run only as root INSIDE the isolated local Linux test container.

Skipping on Windows is not a pass of the isolation gate. No host mount contains
credentials; the source mount is read-only and the container has no network.
"""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest

from fixture.harness.persistence.store import effect_history, initialize

LINUX_ROOT = sys.platform == "linux" and os.geteuid() == 0
PAYMENT_UID, ORDER_UID = 20001, 20002


def demote(uid):
    def drop():
        libc = ctypes.CDLL(None, use_errno=True)
        # PR_SET_NO_NEW_PRIVS, then remove the entire capability bounding set.
        if libc.prctl(38, 1, 0, 0, 0) != 0:
            raise OSError(ctypes.get_errno(), "no_new_privs")
        for cap in range(41):
            if libc.prctl(24, cap, 0, 0, 0) != 0:
                raise OSError(ctypes.get_errno(), "capability drop")
        os.setgroups([])
        os.setresgid(uid, uid, uid)
        os.setresuid(uid, uid, uid)
        # PR_SET_DUMPABLE=0 prevents candidate peers inspecting each other.
        if libc.prctl(4, 0, 0, 0, 0) != 0:
            raise OSError(ctypes.get_errno(), "dumpable")
    return drop


@unittest.skipUnless(LINUX_ROOT, "requires isolated Linux root launcher; NOT verified here")
class LinuxBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="if-t0-")
        self.root = Path(self.temp.name)
        self.root.chmod(0o755)
        self.procs = []
        self.addCleanup(self.cleanup_resources)
        self.db = self.root / "protected" / "payment.db"
        initialize(self.db)
        self.schedule = self.root / "protected" / "schedule.json"
        self.schedule.write_text('{"private":true}')
        self.schedule.chmod(0o600)
        self.harness = self.root / "protected" / "harness.py"
        self.harness.write_text("trusted sentinel\n")
        self.harness.chmod(0o600)
        self.sock = self.root / "payment.sock"
        self.broker = self.start(self.sock, self.db, "payment", PAYMENT_UID)

    def cleanup_resources(self):
        for proc in self.procs:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=3)
            if proc.stdout:
                proc.stdout.close()
            if proc.stderr:
                proc.stderr.close()
        self.temp.cleanup()

    def start(self, sock, db, service, uid, lifetime=5):
        proc = subprocess.Popen([sys.executable, "-m", "fixture.harness.persistence.broker",
                                 "--socket", str(sock), "--db", str(db), "--uid", str(uid),
                                 "--service", service, "--lifetime", str(lifetime)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.procs.append(proc)
        with selectors.DefaultSelector() as selector:
            selector.register(proc.stdout, selectors.EVENT_READ)
            self.assertTrue(selector.select(timeout=5), "broker readiness timeout")
            line = proc.stdout.readline()
        if not line:
            _, error = proc.communicate(timeout=3)
            self.fail("broker exited before readiness: " + error)
        self.assertTrue(json.loads(line)["ready"])
        return proc

    def candidate(self, mode, extra="", uid=PAYMENT_UID, sock=None, expected=0):
        result = subprocess.run([sys.executable, "-I", str(Path(__file__).with_name("linux_candidate.py")),
                                 mode, str(sock or self.sock), extra],
                                preexec_fn=demote(uid), capture_output=True, text=True, timeout=8,
                                env={"PATH": "/usr/local/bin:/usr/bin:/bin"}, cwd="/tmp")
        self.assertEqual(expected, result.returncode, result.stderr + result.stdout)
        return json.loads(result.stdout) if expected == 0 else None

    def test_candidate_can_commit_duplicate_effects(self):
        self.candidate("write", "one")
        self.candidate("write", "two")
        self.assertEqual(2, len(effect_history(self.db)))

    def test_runtime_file_process_and_uid_boundaries(self):
        before = hashlib.sha256(self.harness.read_bytes()).hexdigest()
        checks = [["schedule", str(self.schedule), "read"],
                  ["audit_database", str(self.db), "read"],
                  ["harness_write", str(self.harness), "write"],
                  ["broker_memory", f"/proc/{self.broker.pid}/mem", "read"],
                  ["broker_environment", f"/proc/{self.broker.pid}/environ", "read"]]
        result = self.candidate("filesystem", json.dumps(checks))
        self.assertEqual("denied", result["setuid_root"])
        self.assertEqual(before, hashlib.sha256(self.harness.read_bytes()).hexdigest())

    def test_wrong_uid_denied_even_if_socket_mode_is_permissive(self):
        # Check SO_PEERCRED independently of the normal 0600 socket permission.
        os.chown(self.sock, 0, 0)
        self.sock.chmod(0o666)
        self.candidate("forbidden_socket", uid=ORDER_UID)

    def test_cross_service_store_and_socket_access_denied(self):
        orderdb = self.root / "order-protected" / "order.db"
        initialize(orderdb, "order")
        ordersock = self.root / "order.sock"
        self.start(ordersock, orderdb, "order", ORDER_UID)
        self.candidate("forbidden_socket", sock=ordersock)
        self.candidate("filesystem", json.dumps([["other_store", str(orderdb), "read"]]))

    def test_sql_attacks_through_real_transport_are_denied(self):
        self.candidate("write", "good")
        before = effect_history(self.db)
        self.candidate("tamper_sql")
        self.assertEqual(before, effect_history(self.db))

    def test_client_death_rolls_back_and_releases_lock(self):
        self.candidate("crash", "uncommitted", expected=23)
        # Broker observes EOF; a bounded readiness wait permits handler cleanup.
        time.sleep(0.15)
        self.candidate("write", "after-crash")
        self.assertEqual(["after-crash"], [r[1] for r in effect_history(self.db)])

    def test_committed_effect_survives_client_and_broker_sigkill(self):
        self.candidate("crash", "committed", expected=23)
        os.kill(self.broker.pid, signal.SIGKILL)
        self.broker.wait(timeout=3)
        self.assertEqual(["crashed"], [r[1] for r in effect_history(self.db)])
        self.sock.unlink()  # Only this test-owned stale socket after verified death.
        self.broker = self.start(self.sock, self.db, "payment", PAYMENT_UID)
        self.candidate("write", "after-restart")
        self.assertEqual(2, len(effect_history(self.db)))

    def test_idle_transaction_and_slow_bytes_are_bounded(self):
        short = self.root / "short.sock"
        self.start(short, self.db, "payment", PAYMENT_UID, lifetime=0.5)
        self.candidate("idle_transaction", sock=short)
        self.candidate("trickle", sock=short)
        self.candidate("write", "unlocked")
        self.assertEqual(["unlocked"], [r[1] for r in effect_history(self.db)])

    def test_container_has_no_external_route(self):
        routes = Path("/proc/net/route").read_text().splitlines()[1:]
        self.assertFalse(any(line.split()[1] == "00000000" for line in routes))
        self.candidate("egress")


if __name__ == "__main__":
    unittest.main(verbosity=2)
