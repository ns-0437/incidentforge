"""Trusted T1 local orchestrator and post-commit response-loss proxy."""
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import selectors
import socket
import sqlite3
import subprocess
import sys
import threading
import time

from fixture.app.common import canonical, http
from fixture.harness.persistence.store import initialize, effect_history, snapshot
from tests.test_linux_boundary import demote

UIDS = {"order": 20001, "inventory": 20002, "payment": 20003}
PORTS = {"order": 8081, "inventory": 8082, "payment": 8083}


class World:
    def __init__(self, root: Path, strategy="faulty", fault=False, stock=10, pause=False):
        self.root, self.strategy, self.fault, self.pause = root, strategy, fault, pause
        self.root.mkdir(parents=True)
        self.root.chmod(0o755)
        self.processes, self.files, self.services = [], [], {}
        self.events = []
        self.dropped = threading.Event()
        self.release = threading.Event()
        self.event_lock = threading.Lock()
        self.injected = False
        self.event_file = self.root / "proxy.jsonl"
        self.event_file.touch(mode=0o600)
        for service in UIDS:
            initialize(self.db(service), service)
        with closing(sqlite3.connect(self.db("inventory"))) as conn:
            conn.execute("INSERT INTO app_state VALUES(?,?)", ("stock", canonical(
                {"initial": stock, "held": 0, "available": stock})))
            conn.commit()
        self.proxy = None

    def db(self, service):
        return self.root / service / "state.db"

    def sock(self, service):
        return self.root / (service + ".sock")

    def log(self, value):
        with self.event_lock:
            value = {"seq": len(self.events), "time_monotonic": time.monotonic(), **value}
            self.events.append(value)
            with self.event_file.open("a") as file:
                file.write(canonical(value) + "\n")

    def start(self):
        try:
            for service, uid in UIDS.items():
                error = (self.root / (service + "-broker.log")).open("w")
                self.files.append(error)
                proc = subprocess.Popen([sys.executable, "-m", "fixture.harness.persistence.broker",
                    "--socket", str(self.sock(service)), "--db", str(self.db(service)),
                    "--service", service, "--uid", str(uid), *getattr(self,'broker_args',[])], stdout=subprocess.PIPE, stderr=error,
                    text=True)
                self.processes.append(proc)
                with selectors.DefaultSelector() as sel:
                    sel.register(proc.stdout, selectors.EVENT_READ)
                    if not sel.select(5) or not proc.stdout.readline():
                        raise RuntimeError("broker readiness failed: " + service)
            self.start_proxy()
            for service in ("inventory", "payment", "order"):
                self.start_service(service)
            return self
        except BaseException:
            self.close()
            raise

    def start_service(self, service):
        file = (self.root / (service + "-service.log")).open("a")
        self.files.append(file)
        proc = subprocess.Popen([sys.executable, "-m", "fixture.app.service", "--service", service,
            "--socket", str(self.sock(service)), "--port", str(PORTS[service]),
            "--key-strategy", self.strategy], stdout=file, stderr=file,
            preexec_fn=demote(UIDS[service]), env={"PATH": "/usr/local/bin:/usr/bin:/bin",
                "PYTHONDONTWRITEBYTECODE": "1"}, cwd="/app")
        self.processes.append(proc)
        self.services[service] = proc
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise RuntimeError("service exited: " + service)
            try:
                if http(PORTS[service], "GET", "/healthz", timeout=0.2)[0] == 200:
                    return
            except OSError:
                pass
            time.sleep(0.03)
        raise RuntimeError("service not ready: " + service)

    def restart(self, service):
        old = self.services[service]
        old.kill()
        old.wait(timeout=3)
        self.start_service(service)
        self.log({"event": "service_restarted", "service": service,
                  "old_pid": old.pid, "new_pid": self.services[service].pid})

    def start_proxy(self):
        world = self

        class Proxy(BaseHTTPRequestHandler):
            def do_POST(self):
                raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                body = json.loads(raw)
                # One selected response is withheld. Later retries wait only in
                # restart scenarios, giving the trusted controller a barrier.
                if world.pause and world.dropped.is_set():
                    if not world.release.wait(timeout=5):
                        self.connection.close()
                        return
                status, response = http(PORTS["payment"], "POST", self.path, body)
                history = effect_history(world.db("payment"))
                matches = [r for r in history if r[1] == response.get("charge_id") and
                           r[2] == body.get("intent_id") and r[3] == body.get("operation_key")]
                world.log({"event": "payment_response", "request": body, "status": status,
                           "response": response, "matching_commits": len(matches)})
                with world.event_lock:
                    drop = world.fault and not world.injected and status == 201 and len(matches) == 1
                    if drop:
                        world.injected = True
                if drop:
                    world.log({"event": "response_lost_after_commit", "effect_id": matches[0][1],
                               "audit_seq": matches[0][0]})
                    world.dropped.set()
                    self.connection.shutdown(socket.SHUT_RDWR)
                    self.connection.close()
                    return
                encoded = canonical(response).encode()
                try:
                    self.send_response(status)
                    self.send_header("Content-Length", str(len(encoded)))
                    self.end_headers()
                    self.wfile.write(encoded)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *_):
                pass

        self.proxy = ThreadingHTTPServer(("127.0.0.1", 8084), Proxy)
        threading.Thread(target=self.proxy.serve_forever, daemon=True).start()

    def submit(self, identity="order-1", **overrides):
        body = {"client_request_id": identity, "customer_id": "CUST-OK", "qty": 1,
                "amount_cents": 100, **overrides}
        return http(PORTS["order"], "POST", "/orders", body)

    def terminal(self, identity="order-1"):
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            status, order = http(PORTS["order"], "GET", "/orders/" + identity)
            if status == 200 and order["status"] in {"CONFIRMED", "CANCELLED_DECLINED", "REJECTED_STOCK"}:
                return order
            time.sleep(0.04)
        raise AssertionError("order did not complete within T1 test timeout")

    def evidence(self):
        return {"effects": effect_history(self.db("payment")),
                "stock": http(PORTS["inventory"], "GET", "/stock")[1], "events": self.events,
                "service_pids": {k: v.pid for k, v in self.services.items()}}

    def export(self, output):
        output.mkdir(parents=True, exist_ok=True)
        data = self.evidence()
        # Stop writers before a coherent cross-store export.
        for proc in self.services.values():
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=3)
        self.release.set()
        self.proxy.shutdown()
        self.proxy.server_close()
        self.proxy = None
        # Stop broker handlers too: a request already received before its client
        # died must not commit between separate service snapshots.
        for proc in self.processes:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=3)
        data["snapshots"] = {service: snapshot(self.db(service), output / (service + ".db"))
                             for service in UIDS}
        data["effects"] = effect_history(output / "payment.db")
        with closing(sqlite3.connect(output / "inventory.db")) as conn:
            data["stock"] = json.loads(conn.execute(
                "SELECT value FROM app_state WHERE key='stock'").fetchone()[0])
        data["events"] = list(self.events)
        for path in self.root.glob('*.log'):
            (output / path.name).write_bytes(path.read_bytes())
        (output / 'proxy.jsonl').write_bytes(self.event_file.read_bytes())
        (output / "evidence.json").write_text(json.dumps(data, indent=2))
        return data

    def close(self):
        self.release.set()
        for proc in reversed(self.processes):
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=3)
            if proc.stdout:
                proc.stdout.close()
        if self.proxy:
            self.proxy.shutdown()
            self.proxy.server_close()
            self.proxy = None
        for file in self.files:
            file.close()
