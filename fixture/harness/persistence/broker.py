"""Linux-only bounded JSON-line broker with kernel peer UID authentication."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import socketserver
import struct
import threading
import time

from .store import PolicyError, Session


class Broker(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    block_on_close = False
    request_queue_size = 8

    def __init__(self, address, db, service, uid, lifetime):
        self.db, self.service, self.uid, self.lifetime = db, service, uid, lifetime
        self.slots = threading.BoundedSemaphore(8)
        super().__init__(address, Handler)

    def verify_request(self, request, client_address):
        _, uid, _ = struct.unpack("3i", request.getsockopt(
            socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")))
        return uid == self.uid

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        session = self.server.session_class(self.server.db, self.server.service, self.server.lifetime)
        def expire():
            try:
                self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        # A socket timeout alone is per receive and permits slow-byte trickling.
        timer = threading.Timer(self.server.lifetime, expire)
        timer.daemon = True
        timer.start()
        try:
            # Limit requests AND absolute lifetime; trickling bytes cannot renew it.
            for _ in range(128):
                remaining = session.deadline - time.monotonic()
                if remaining <= 0:
                    break
                self.connection.settimeout(min(remaining, 1.0))
                raw = self.rfile.readline(16385)
                if not raw or len(raw) > 16384 or not raw.endswith(b"\n"):
                    break
                try:
                    request = json.loads(raw)
                    response = session.request(request)
                except (ValueError, PolicyError) as exc:
                    session.rollback()
                    response = {"ok": False, "error": str(exc)}
                self.wfile.write(json.dumps(response).encode() + b"\n")
                self.wfile.flush()
        except (OSError, TimeoutError):
            pass  # Disconnect/timeout always rolls back uncommitted work.
        finally:
            timer.cancel()
            session.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--uid", type=int, required=True)
    parser.add_argument("--service", choices=["order", "payment", "inventory"], required=True)
    parser.add_argument("--lifetime", type=float, default=10)
    parser.add_argument("--v2", action="store_true")
    args = parser.parse_args()
    if not hasattr(socket, "SO_PEERCRED") or os.getuid() != 0:
        parser.error("Linux trusted root launcher required for T0 broker")
    # Refuse stale sockets; the trusted orchestrator owns cleanup/reset.
    with Broker(str(args.socket), args.db, args.service, args.uid, args.lifetime) as server:
        if args.v2:
            from .v2 import Session as V2Session
            server.session_class = V2Session
        else:
            server.session_class = Session
        args.socket.chmod(0o600)
        os.chown(args.socket, args.uid, args.uid)
        print(json.dumps({"ready": True, "socket": str(args.socket)}), flush=True)
        try:
            server.serve_forever(poll_interval=0.1)
        finally:
            args.socket.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
