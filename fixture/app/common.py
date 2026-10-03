"""Candidate-side broker and HTTP clients. No database-file access."""
from contextlib import contextmanager
from http.client import HTTPConnection
import json
import socket


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class DB:
    def __init__(self, path):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(2)
        self.sock.connect(path)
        self.stream = self.sock.makefile("rwb", buffering=0)

    def call(self, op, **fields):
        self.stream.write((canonical({"op": op, **fields}) + "\n").encode())
        result = json.loads(self.stream.readline(65537))
        if not result["ok"]:
            raise RuntimeError(result["error"])
        return result

    def sql(self, sql, *params):
        return self.call("execute", sql=sql, params=list(params))["rows"]

    def get(self, key):
        rows = self.sql("SELECT value FROM app_state WHERE key=?", key)
        return json.loads(rows[0][0]) if rows else None

    def put(self, key, value):
        self.sql("INSERT INTO app_state VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                 key, canonical(value))

    def close(self):
        self.stream.close()
        self.sock.close()


@contextmanager
def transaction(path):
    db = DB(path)
    try:
        db.call("begin")
        yield db
        db.call("commit")
    finally:
        db.close()  # Server rolls back any incomplete transaction on EOF.


def http(port, method, path, body=None, timeout=1):
    conn = HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        conn.request(method, path, body=canonical(body) if body is not None else None,
                     headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        data = response.read(65537)
        if len(data) > 65536:
            raise ValueError("oversized response")
        return response.status, json.loads(data)
    finally:
        conn.close()
