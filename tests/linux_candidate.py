"""Untrusted candidate-side probe. Deliberately imports no trusted store code."""
import ctypes
import json
import os
from pathlib import Path
import socket
import sys
import time

mode, address, extra = sys.argv[1:4]


def connect():
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(2)
    sock.connect(address)
    return sock, sock.makefile("rwb", buffering=0)


def request(stream, obj):
    stream.write(json.dumps(obj).encode() + b"\n")
    line = stream.readline()
    if not line:
        raise EOFError("broker closed")
    return json.loads(line)


if mode == "write":
    sock, stream = connect()
    assert request(stream, {"op": "begin"})["ok"]
    assert request(stream, {"op": "execute", "sql": "INSERT INTO charges VALUES(?,?,?,?)",
                            "params": [extra, "intent", "same-key", 100]})["ok"]
    assert request(stream, {"op": "commit"})["ok"]
    print(json.dumps({"committed": True}), flush=True)
elif mode == "crash":
    sock, stream = connect()
    assert request(stream, {"op": "begin"})["ok"]
    assert request(stream, {"op": "execute", "sql": "INSERT INTO charges VALUES(?,?,?,?)",
                            "params": ["crashed", "intent", "same-key", 100]})["ok"]
    if extra == "committed":
        assert request(stream, {"op": "commit"})["ok"]
    os._exit(23)
elif mode == "forbidden_socket":
    denied = False
    try:
        sock, stream = connect()
        request(stream, {"op": "begin"})
    except (PermissionError, ConnectionError, EOFError):
        denied = True
    assert denied, "wrong UID got broker access"
    print(json.dumps({"denied": True}))
elif mode == "filesystem":
    checks = {}
    for label, path, action in json.loads(extra):
        try:
            if action == "read":
                Path(path).read_bytes()
            else:
                with open(path, "ab") as file:
                    file.write(b"tampered")
        except PermissionError:
            checks[label] = "denied"
        else:
            raise AssertionError(f"access unexpectedly succeeded: {label}")
    try:
        os.setuid(0)
    except PermissionError:
        checks["setuid_root"] = "denied"
    else:
        raise AssertionError("candidate became root")
    status = Path("/proc/self/status").read_text()
    for key in ("CapEff", "CapPrm", "CapInh", "CapAmb", "CapBnd"):
        value = next(line.split()[1] for line in status.splitlines() if line.startswith(key + ":"))
        assert int(value, 16) == 0, (key, value)
    assert "NoNewPrivs:\t1" in status
    print(json.dumps(checks))
elif mode == "tamper_sql":
    sock, stream = connect()
    checks = []
    for sql in ["SELECT * FROM _effect_audit", "DELETE FROM charges",
                "DROP TRIGGER _audit_charge", "PRAGMA writable_schema=ON",
                "ATTACH DATABASE '/tmp/other.db' AS other"]:
        assert request(stream, {"op": "begin"})["ok"]
        result = request(stream, {"op": "execute", "sql": sql})
        assert result["ok"] is False, sql
        checks.append(sql)
    print(json.dumps({"denied": checks}))
elif mode == "idle_transaction":
    sock, stream = connect()
    assert request(stream, {"op": "begin"})["ok"]
    assert request(stream, {"op": "execute", "sql": "INSERT INTO charges VALUES(?,?,?,?)",
                            "params": ["idle", "intent", "key", 100]})["ok"]
    time.sleep(1.5)
    assert stream.readline() == b""
    print(json.dumps({"expired": True}))
elif mode == "trickle":
    sock, stream = connect()
    started = time.monotonic()
    closed = False
    try:
        while time.monotonic() - started < 3:
            sock.sendall(b" ")
            time.sleep(0.1)
    except (BrokenPipeError, ConnectionResetError):
        closed = True
    assert closed, "slow-byte client bypassed absolute lifetime"
    print(json.dumps({"expired": True}))
elif mode == "egress":
    # Numeric reserved test address; network=none should deny connection locally.
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    try:
        sock.connect(("192.0.2.1", 443))
    except OSError:
        print(json.dumps({"connection_failed": True}))
    else:
        raise AssertionError("external connection unexpectedly possible")
else:
    raise ValueError(mode)
