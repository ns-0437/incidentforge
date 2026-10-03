import os
from pathlib import Path
import sys
import tempfile
import unittest

LINUX = sys.platform == "linux" and os.geteuid() == 0


@unittest.skipUnless(LINUX, "T1 requires isolated Linux root launcher")
class TestbedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="if-t1-")
        Path(self.temp.name).chmod(0o755)
        self.addCleanup(self.temp.cleanup)
        self.worlds = []
        self.addCleanup(self.close_worlds)

    def close_worlds(self):
        for world in self.worlds:
            world.close()

    def world(self, **kwargs):
        from fixture.harness.t1 import World
        world = World(Path(self.temp.name) / str(len(self.worlds)), **kwargs)
        self.worlds.append(world)
        return world.start()

    def test_clean_faulty_revision_has_one_effect_and_three_processes(self):
        w = self.world()
        self.assertEqual(202, w.submit()[0])
        self.assertEqual("CONFIRMED", w.terminal()["status"])
        data = w.evidence()
        self.assertEqual(1, len(data["effects"]))
        self.assertEqual(3, len(set(data["service_pids"].values())))
        self.assertEqual({"initial": 10, "available": 9, "held": 1}, data["stock"])

    def test_response_loss_reproducibly_duplicates_faulty_revision(self):
        for _ in range(3):
            w = self.world(fault=True)
            w.submit()
            self.assertEqual("CONFIRMED", w.terminal()["status"])
            data = w.evidence()
            self.assertEqual(2, len(data["effects"]))
            self.assertEqual(2, len({r[3] for r in data["effects"]}))
            self.assertEqual(1, sum(e["event"] == "response_lost_after_commit" for e in data["events"]))
            w.close()

    def test_reference_identity_repairs_same_fault_without_lost_order(self):
        w = self.world(strategy="reference", fault=True)
        w.submit()
        order = w.terminal()
        self.assertEqual("CONFIRMED", order["status"])
        self.assertGreaterEqual(order["attempts"], 2)
        self.assertEqual(1, len(w.evidence()["effects"]))

    def test_payment_restart_retains_dedup_after_response_loss(self):
        w = self.world(strategy="reference", fault=True, pause=True)
        w.submit()
        self.assertTrue(w.dropped.wait(4))
        w.restart("payment")
        w.release.set()
        self.assertEqual("CONFIRMED", w.terminal()["status"])
        self.assertEqual(1, len(w.evidence()["effects"]))

    def test_order_crash_recovers_durable_pending_payment(self):
        w = self.world(strategy="reference", fault=True, pause=True)
        w.submit()
        self.assertTrue(w.dropped.wait(4))
        w.restart("order")
        w.release.set()
        self.assertEqual("CONFIRMED", w.terminal()["status"])
        self.assertEqual(1, len(w.evidence()["effects"]))

    def test_decline_releases_stock_and_out_of_stock_never_charges(self):
        w = self.world(strategy="reference", stock=1)
        w.submit("decline", customer_id="CUST-DECLINE")
        self.assertEqual("CANCELLED_DECLINED", w.terminal("decline")["status"])
        self.assertEqual(1, w.evidence()["stock"]["available"])
        w.submit("too-many", qty=2)
        self.assertEqual("REJECTED_STOCK", w.terminal("too-many")["status"])
        self.assertEqual([], w.evidence()["effects"])

    def test_duplicate_client_request_and_conflicting_payload(self):
        w = self.world(strategy="reference")
        w.submit()
        w.terminal()
        self.assertEqual(200, w.submit()[0])
        self.assertEqual(409, w.submit(amount_cents=200)[0])
        self.assertEqual(1, len(w.evidence()["effects"]))

    def test_inventory_restart_preserves_hold_and_idempotent_release(self):
        from fixture.app.common import http
        from fixture.harness.t1 import PORTS
        w = self.world(strategy="reference")
        body = {"order_id": "inventory-control", "operation_key": "rsv-control", "qty": 2}
        self.assertEqual(201, http(PORTS['inventory'], 'POST', '/reservations', body)[0])
        w.restart('inventory')
        self.assertEqual(200, http(PORTS['inventory'], 'POST', '/reservations', body)[0])
        self.assertEqual(2, w.evidence()['stock']['held'])
        for _ in range(2):
            self.assertEqual(200, http(PORTS['inventory'], 'POST', '/release',
                                      {'reservation_id': 'rsv-control'})[0])
        self.assertEqual({'initial': 10, 'available': 10, 'held': 0}, w.evidence()['stock'])

    def test_clean_faulted_clean_fresh_state(self):
        counts = []
        for fault in (False, True, False):
            w = self.world(fault=fault)
            self.assertEqual([], w.evidence()["effects"])
            self.assertEqual(10, w.evidence()["stock"]["available"])
            w.submit()
            w.terminal()
            counts.append(len(w.evidence()["effects"]))
            w.close()
        self.assertEqual([1, 2, 1], counts)
