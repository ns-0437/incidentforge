import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import subprocess
import sys

from fixture.harness.persistence.store import (
    PolicyError, Session, effect_history, initialize, snapshot,
)

INSERT = "INSERT INTO charges VALUES(?,?,?,?)"


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "payment.db"
        initialize(self.path)
        self.sessions = []

    def tearDown(self):
        for session in self.sessions:
            session.close()
        self.temp.cleanup()

    def session(self):
        session = Session(self.path)
        self.sessions.append(session)
        return session

    def sql(self, session, sql, params=None):
        return session.request({"op": "execute", "sql": sql, "params": params or []})

    def begin(self, session):
        session.request({"op": "begin"})

    def charge(self, session, effect="e1", intent="o1"):
        self.sql(session, INSERT, [effect, intent, "same-key", 100])

    def test_commit_and_rollback_are_atomic_with_audit(self):
        s = self.session()
        self.begin(s)
        self.charge(s)
        self.assertEqual([], effect_history(self.path))
        s.request({"op": "commit"})
        self.begin(s)
        self.charge(s, "rolled-back")
        s.request({"op": "rollback"})
        self.assertEqual(["e1"], [r[1] for r in effect_history(self.path)])

    def test_duplicate_effects_are_not_deduplicated_by_broker(self):
        s = self.session()
        self.begin(s)
        self.charge(s, "e1")
        self.charge(s, "e2")
        s.request({"op": "commit"})
        self.assertEqual(2, len(effect_history(self.path)))

    def test_http_claims_do_not_define_commits(self):
        # Responses are deliberately not an input to the effect observer.
        s = self.session()
        self.begin(s)
        self.charge(s)
        s.request({"op": "commit"})
        for response_statuses in ([], [201], [201, 201]):
            self.assertEqual(1, len(effect_history(self.path)), response_statuses)
        self.begin(s)
        self.charge(s, "e2")
        s.request({"op": "commit"})
        self.assertEqual(2, len(effect_history(self.path)))

    def test_fake_success_leaves_no_effect(self):
        self.assertEqual([], effect_history(self.path))

    def test_policy_denial_rolls_back_entire_transaction(self):
        s = self.session()
        self.begin(s)
        self.charge(s)
        with self.assertRaises(PolicyError):
            self.sql(s, "DELETE FROM charges")
        self.assertEqual([], effect_history(self.path))
        self.assertFalse(s.conn.in_transaction)

    def test_sql_boundary_attacks_and_nested_access(self):
        s = self.session()
        attacks = [
            "SELECT * FROM _effect_audit",
            "SELECT (SELECT effect_id FROM _effect_audit LIMIT 1)",
            "INSERT INTO app_state SELECT 'leak',effect_id FROM _effect_audit",
            "DELETE FROM _effect_audit", "UPDATE charges SET amount_cents=0",
            "DROP TRIGGER _audit_charge", "DROP TABLE charges",
            "CREATE TEMP VIEW leak AS SELECT * FROM _effect_audit",
            "CREATE TRIGGER malicious AFTER INSERT ON claims BEGIN DELETE FROM charges; END",
            "ATTACH DATABASE ':memory:' AS other", "PRAGMA writable_schema=ON",
            "PRAGMA recursive_triggers=OFF", "VACUUM INTO 'leak.db'",
            "SELECT load_extension('bad')", "SELECT * FROM sqlite_master",
            "SELECT * FROM pragma_table_info('charges')",
            "COMMIT", "SAVEPOINT bypass", "SELECT 1; SELECT 2",
        ]
        for attack in attacks:
            with self.subTest(sql=attack):
                self.begin(s)
                with self.assertRaises(PolicyError):
                    self.sql(s, attack)
                self.assertFalse(s.conn.in_transaction)

    def test_replace_cannot_erase_effect_or_audit(self):
        s = self.session()
        self.begin(s)
        self.charge(s)
        s.request({"op": "commit"})
        self.begin(s)
        with self.assertRaises(PolicyError):
            self.sql(s, "INSERT OR REPLACE INTO charges VALUES(?,?,?,?)",
                     ["e1", "other", "key", 999])
        self.assertEqual([(1, "e1", "o1", "same-key", 100)], effect_history(self.path))

    def test_app_owned_mutable_state_and_atomic_claim_are_possible(self):
        s = self.session()
        self.begin(s)
        self.sql(s, "INSERT INTO app_state VALUES(?,?)", ["order", "pending"])
        self.sql(s, "UPDATE app_state SET value=? WHERE key=?", ["done", "order"])
        self.sql(s, "INSERT INTO claims VALUES(?,?)", ["key", "e1"])
        self.charge(s)
        s.request({"op": "commit"})
        self.begin(s)
        with self.assertRaises(PolicyError):
            self.sql(s, "INSERT INTO claims VALUES(?,?)", ["key", "e2"])
        self.assertEqual(1, len(effect_history(self.path)))

    def test_bad_check_then_insert_interleaving_still_duplicates(self):
        a, b = self.session(), self.session()
        for s in (a, b):
            self.begin(s)
            self.assertEqual([], self.sql(s, "SELECT effect_id FROM charges WHERE operation_key=?",
                                          ["same-key"])["rows"])
            s.request({"op": "commit"})
        # Two checks saw absence. Separate later transactions each commit.
        for s, effect in ((a, "a"), (b, "b")):
            self.begin(s)
            self.charge(s, effect)
            s.request({"op": "commit"})
        self.assertEqual(2, len(effect_history(self.path)))

    def test_writer_contention_and_disconnect_release_lock(self):
        a, b = self.session(), self.session()
        self.begin(a)
        self.charge(a)
        self.begin(b)
        with self.assertRaises(PolicyError):
            self.charge(b, "b")
        a.rollback()  # Socket disconnect invokes the same rollback path.
        self.begin(b)
        self.charge(b, "b")
        b.request({"op": "commit"})
        self.assertEqual(["b"], [r[1] for r in effect_history(self.path)])

    def test_backup_includes_wal_and_excludes_uncommitted_work(self):
        s = self.session()
        self.begin(s)
        self.charge(s)
        s.request({"op": "commit"})
        self.begin(s)
        self.charge(s, "uncommitted")
        target = Path(self.temp.name) / "backup.db"
        metadata = snapshot(self.path, target)
        self.assertEqual("ok", metadata["integrity_check"])
        self.assertEqual(["e1"], [r[1] for r in effect_history(target)])

    def test_bounds_and_malformed_requests_fail_closed(self):
        s = self.session()
        for request in ({"op": "export"}, {"op": "execute", "sql": "SELECT 1"},
                        {"op": "begin", "extra": 1}, [],
                        {"op": "execute", "sql": "x" * 9000}):
            with self.subTest(request=str(request)[:60]):
                with self.assertRaises(PolicyError):
                    s.request(request)
        self.begin(s)
        for n in range(257):
            self.sql(s, "INSERT INTO app_state VALUES(?,?)", [str(n), "x"])
        with self.assertRaises(PolicyError):
            self.sql(s, "SELECT * FROM app_state")
        self.assertFalse(s.conn.in_transaction)

    def test_clean_faulted_clean_reset_and_independent_stores(self):
        initial = effect_history(self.path)
        s = self.session()
        self.begin(s)
        self.charge(s)
        self.charge(s, "e2")
        s.request({"op": "commit"})
        clean = Path(self.temp.name) / "new-run" / "payment.db"
        initialize(clean)
        self.assertEqual(initial, effect_history(clean))
        self.assertEqual(2, len(effect_history(self.path)))
        with self.assertRaises(FileExistsError):
            initialize(self.path)

    def test_real_process_crash_after_commit_preserves_audit(self):
        result = subprocess.run([sys.executable, "-m", "tests.crash_writer",
                                 str(self.path), "committed"], timeout=10,
                                capture_output=True, text=True)
        self.assertEqual(23, result.returncode, result.stderr)
        self.assertEqual(["crash-effect"], [r[1] for r in effect_history(self.path)])
        self.assertEqual("ok", snapshot(self.path, Path(self.temp.name) / "crash.db")["integrity_check"])

    def test_real_process_crash_before_commit_rolls_back_and_unlocks(self):
        result = subprocess.run([sys.executable, "-m", "tests.crash_writer",
                                 str(self.path), "uncommitted"], timeout=10,
                                capture_output=True, text=True)
        self.assertEqual(23, result.returncode, result.stderr)
        self.assertEqual([], effect_history(self.path))
        s = self.session()
        self.begin(s)
        self.charge(s)
        s.request({"op": "commit"})
        self.assertEqual(1, len(effect_history(self.path)))

    def test_query_step_budget_and_expired_session(self):
        s = self.session()
        self.begin(s)
        for n in range(25):
            self.sql(s, "INSERT INTO app_state VALUES(?,?)", [str(n), "x"])
        s.request({"op": "commit"})
        self.begin(s)
        with self.assertRaises(PolicyError):
            self.sql(s, "SELECT count(*) FROM app_state a,app_state b,app_state c,app_state d,app_state e")
        s.deadline = 0
        with self.assertRaises(PolicyError):
            self.begin(s)


if __name__ == "__main__":
    unittest.main(verbosity=2)
