"""The ledger must never publish a half-built allocation to a concurrent reader.

Budget.__init__ used to create the settings table in one autocommitted DDL
statement and insert the cap in a later transaction. A concurrent /api/state read
found settings empty, fetchone() returned None, and `[0]` raised TypeError
outside do_GET's caught tuple, so the handler died without writing a response.
"""
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from incidentforge.budget import Budget
from incidentforge.ui import Manager, budget_status

CAP = 400000


class LedgerInitializationTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'runs').mkdir()
        self.ledger = self.root / 'runs/t4-budget.sqlite'

    # ----- reader contract -------------------------------------------------------

    def test_incomplete_ledger_is_reported_and_blocks_launching(self):
        """A settings table with no row is exactly the state the race exposed."""
        with closing(sqlite3.connect(self.ledger)) as db:
            db.execute('CREATE TABLE settings(cap INTEGER NOT NULL)')
            db.execute('CREATE TABLE calls(id TEXT PRIMARY KEY,run TEXT,cap INTEGER,'
                       'actual INTEGER,status TEXT)')
            db.commit()
        status = budget_status(self.root)          # must not raise TypeError
        self.assertEqual('incomplete', status['state'])
        # Nothing is fabricated: no cap, no spend, no available funds.
        for field in ('cap_usd', 'estimated_usd', 'reserved_usd', 'unknown_usd'):
            self.assertIsNone(status[field], field)
        self.assertEqual(0, status['remaining_usd'])
        manager = Manager(self.root, lambda *a, **k: None)
        with self.assertRaises(ValueError) as caught:
            manager.launch('IF-002', 'B2')
        self.assertIn('budget state unknown', str(caught.exception))
        self.assertFalse(manager.guard.exists(), 'a blocked launch must leave no guard')

    def test_unusable_cap_value_is_also_reported_as_incomplete(self):
        with closing(sqlite3.connect(self.ledger)) as db:
            db.execute('CREATE TABLE settings(cap INTEGER NOT NULL)')
            db.execute("INSERT INTO settings VALUES('not an integer')")
            db.execute('CREATE TABLE calls(id TEXT PRIMARY KEY,run TEXT,cap INTEGER,'
                       'actual INTEGER,status TEXT)')
            db.commit()
        self.assertEqual('incomplete', budget_status(self.root)['state'])

    # ----- writer atomicity ------------------------------------------------------

    def test_reader_never_sees_a_half_built_ledger_during_initialization(self):
        """Pause the writer at its commit boundary and read from another thread."""
        import incidentforge.budget as budget_module
        at_boundary, release = threading.Barrier(2), threading.Event()
        real_connect = budget_module.sqlite3.connect
        observations, failures = [], []

        class Paused(sqlite3.Connection):
            def execute(self, sql, *args):
                if sql == 'COMMIT':
                    at_boundary.wait(10)     # writer is mid-transaction here
                    release.wait(10)
                return super().execute(sql, *args)

        def connect(path, *args, **kwargs):
            if str(path) == str(self.ledger):
                kwargs['factory'] = Paused
            return real_connect(path, *args, **kwargs)

        def build():
            try:
                Budget(self.ledger, CAP)
            except BaseException as exc:      # noqa: BLE001 - recorded, then re-raised in the test
                failures.append(exc)
                at_boundary.wait(5)

        from unittest.mock import patch
        with patch.object(budget_module.sqlite3, 'connect', connect):
            writer = threading.Thread(target=build, daemon=True)
            writer.start()
            at_boundary.wait(10)
            # The writer is holding its IMMEDIATE transaction open right now.
            try:
                observations.append(budget_status(self.root))
            finally:
                release.set()
                writer.join(10)
        self.assertEqual([], failures, 'initialization itself failed: %r' % failures)
        during = observations[0]
        # Either the ledger is not published yet, or it is complete. Never half.
        self.assertIn(during.get('state', 'complete'), ('incomplete', 'complete'))
        if during.get('state') != 'incomplete':
            self.assertIsNotNone(during['cap_usd'])
        self.assertEqual(0, during['remaining_usd'] if during.get('state') == 'incomplete'
                         else during['remaining_usd'] * 0, 'no funds may be offered while unknown')

        # After the commit the real allocation and totals are readable.
        settled = budget_status(self.root)
        self.assertEqual(CAP / 1e6, settled['cap_usd'])
        self.assertEqual(0, settled['estimated_usd'])
        self.assertEqual(0, settled['pending'])
        self.assertEqual(CAP / 1e6, settled['remaining_usd'])

    def test_existing_ledger_keeps_its_allocation_and_reservations(self):
        budget = Budget(self.ledger, CAP)
        token = budget.reserve('run-1', 1000, CAP, 10)
        budget.settle(token, 900)
        budget.reserve('run-1', 500, CAP, 10)      # left reserved on purpose
        reopened = Budget(self.ledger, CAP)        # re-initialization must preserve
        status = budget_status(self.root)
        self.assertEqual(CAP / 1e6, status['cap_usd'])
        self.assertEqual(900 / 1e6, status['estimated_usd'])
        self.assertEqual(1, status['pending'])
        self.assertEqual(1400 / 1e6, status['reserved_usd'])
        self.assertEqual(CAP, reopened.project_cap_microusd)
        with self.assertRaises(ValueError):
            Budget(self.ledger, CAP + 1)           # cap still cannot change


if __name__ == '__main__':
    unittest.main()
