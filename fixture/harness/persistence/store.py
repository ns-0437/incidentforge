"""T0 storage boundary. Only the broker owns database files.

This module is trusted code, never imported by a candidate service. SQL is
authorized at SQLite's parsed-operation layer, including trigger execution.
There is deliberately no UNIQUE constraint on operation_key or intent_id.
"""
from __future__ import annotations

import hashlib
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import time


class PolicyError(Exception):
    """Rejected or resource-bounded application operation."""


BASE_SCHEMA = """
CREATE TABLE app_state(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE claims(operation_key TEXT PRIMARY KEY, effect_id TEXT NOT NULL);
"""
PAYMENT_SCHEMA = """
CREATE TABLE charges(
    effect_id TEXT PRIMARY KEY NOT NULL,
    intent_id TEXT NOT NULL,
    operation_key TEXT NOT NULL,
    amount_cents INTEGER NOT NULL CHECK(typeof(amount_cents) = 'integer')
);
CREATE TABLE _effect_audit(
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    effect_id TEXT NOT NULL,
    intent_id TEXT NOT NULL,
    operation_key TEXT NOT NULL,
    amount_cents INTEGER NOT NULL
);
CREATE TRIGGER _audit_charge AFTER INSERT ON charges BEGIN
    INSERT INTO _effect_audit(effect_id,intent_id,operation_key,amount_cents)
    VALUES(NEW.effect_id,NEW.intent_id,NEW.operation_key,NEW.amount_cents);
END;
CREATE TRIGGER _immutable_charge_delete BEFORE DELETE ON charges BEGIN
    SELECT RAISE(ABORT, 'effect deletion prohibited');
END;
CREATE TRIGGER _immutable_charge_update BEFORE UPDATE ON charges BEGIN
    SELECT RAISE(ABORT, 'effect update prohibited');
END;
"""


def initialize(path: Path, service: str = "payment") -> None:
    """Create a NEW store only; never reset an existing file implicitly."""
    if service not in {"payment", "order", "inventory"}:
        raise ValueError("unknown service")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    if os.name == "posix":
        path.parent.chmod(0o700)
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=FULL")
        conn.executescript(BASE_SCHEMA + (PAYMENT_SCHEMA if service == "payment" else ""))
    if os.name == "posix":
        path.chmod(0o600)


class Session:
    """One client connection = one bounded SQL session/transaction context.

    A policy or SQL error rolls back the entire open transaction. This is
    deliberately fail-closed. The caller must explicitly retry a new transaction.
    """
    MAX_SQL = 8192
    MAX_ROWS = 256
    MAX_RESULT_BYTES = 65536
    MAX_STEPS = 100_000

    def __init__(self, path: Path, service: str = "payment", timeout: float = 10.0):
        self.service = service
        self.deadline = time.monotonic() + timeout
        self._control = False
        self._steps = 0
        self.conn = sqlite3.connect(path, isolation_level=None, timeout=0.1,
                                    cached_statements=0)
        self.conn.execute("PRAGMA recursive_triggers=ON")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, self.MAX_RESULT_BYTES)
        self.conn.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, self.MAX_SQL)
        self.conn.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED, 0)
        self.conn.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, 64)
        self.conn.setlimit(sqlite3.SQLITE_LIMIT_EXPR_DEPTH, 50)
        self.conn.set_authorizer(self._authorize)
        self.conn.set_progress_handler(self._progress, 100)

    def _authorize(self, action, arg1, arg2, database, source):
        allow, deny = sqlite3.SQLITE_OK, sqlite3.SQLITE_DENY
        if database not in (None, "main"):
            return deny
        if action in (sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_SAVEPOINT):
            return allow if self._control else deny
        if action == sqlite3.SQLITE_SELECT:
            return allow
        if action == sqlite3.SQLITE_FUNCTION:
            return allow if (arg2 or "").lower() in {
                "count", "sum", "min", "max", "coalesce", "length", "raise"
            } else deny
        if action == sqlite3.SQLITE_READ:
            return allow if arg1 in {"app_state", "claims", "charges"} else deny
        if action in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE):
            if arg1 == "_effect_audit":
                return allow if (action == sqlite3.SQLITE_INSERT and
                                 source == "_audit_charge") else deny
            if arg1 in {"app_state", "claims"}:
                return allow
            if arg1 == "charges" and self.service == "payment":
                return allow if action == sqlite3.SQLITE_INSERT else deny
        # No DDL, PRAGMA, ATTACH, DETACH, virtual tables, views or recursive CTE.
        return deny

    def _progress(self):
        if self._control:
            return 0  # Trusted rollback must remain available after a query timeout.
        self._steps += 100
        return int(self._steps > self.MAX_STEPS or time.monotonic() > self.deadline)

    def _transaction(self, operation):
        self._control = True
        try:
            self.conn.execute(operation)
        finally:
            self._control = False

    def rollback(self):
        if self.conn.in_transaction:
            self._transaction("ROLLBACK")

    def request(self, request: dict) -> dict:
        try:
            if time.monotonic() >= self.deadline:
                raise PolicyError("session lifetime exceeded")
            self._steps = 0
            if not isinstance(request, dict):
                raise PolicyError("request must be an object")
            op = request.get("op")
            if op in {"begin", "commit", "rollback"}:
                if set(request) != {"op"}:
                    raise PolicyError("unexpected transaction fields")
                self._transaction({"begin": "BEGIN", "commit": "COMMIT",
                                   "rollback": "ROLLBACK"}[op])
                return {"ok": True}
            if op != "execute" or set(request) - {"op", "sql", "params"}:
                raise PolicyError("unsupported operation")
            sql, params = request.get("sql"), request.get("params", [])
            if not isinstance(sql, str) or len(sql.encode()) > self.MAX_SQL:
                raise PolicyError("invalid SQL size/type")
            if not isinstance(params, list) or any(
                v is not None and type(v) not in (str, int, float) for v in params
            ):
                raise PolicyError("params must be scalar list")
            if not self.conn.in_transaction:
                raise PolicyError("explicit begin required")
            cursor = self.conn.execute(sql, params)
            rows = cursor.fetchmany(self.MAX_ROWS + 1) if cursor.description else []
            if len(rows) > self.MAX_ROWS:
                raise PolicyError("result row limit exceeded")
            result = {"ok": True, "rows": rows, "rowcount": cursor.rowcount}
            if len(json.dumps(result).encode()) > self.MAX_RESULT_BYTES:
                raise PolicyError("result byte limit exceeded")
            return result
        except (sqlite3.Error, PolicyError, ValueError, TypeError, OverflowError) as exc:
            self.rollback()
            raise PolicyError(str(exc)) from exc

    def close(self):
        try:
            self.rollback()
        finally:
            self.conn.close()


def snapshot(path: Path, target: Path) -> dict:
    """Trusted-only coherent backup including committed WAL contents."""
    if target.exists():
        raise FileExistsError(target)
    with closing(sqlite3.connect(path)) as src, closing(sqlite3.connect(target)) as dst:
        src.backup(dst, pages=64)
        result = dst.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise RuntimeError(result)
    return {"sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "bytes": target.stat().st_size, "integrity_check": result}


def effect_history(path: Path) -> list:
    """Trusted observer only, never exposed as a broker operation."""
    with closing(sqlite3.connect(path)) as conn:
        return conn.execute("SELECT seq,effect_id,intent_id,operation_key,amount_cents "
                            "FROM _effect_audit ORDER BY seq").fetchall()
