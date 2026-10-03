"""Three separate HTTP service processes. T1 fixture, not production software.

The selectable reference key strategy is a manually authored control. It is
never represented as an agent-generated repair. Full contract hardening is T2.
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time
import uuid

from .common import canonical, http, transaction


class App:
    def __init__(self, args):
        self.args = args
        self.lock = threading.RLock()

    def dispatch(self, method, path, body):
        with self.lock:
            if path == "/healthz":
                return 200, {"service": self.args.service, "ready": True}
            return getattr(self, self.args.service)(method, path, body)

    def payment(self, method, path, body):
        if method != "POST" or path != "/charges":
            return 404, {"error": "not_found"}
        key = body["operation_key"]
        payload = {k: body[k] for k in ("order_id", "intent_id", "customer_id", "amount_cents")}
        if type(payload["amount_cents"]) is not int or payload["amount_cents"] <= 0:
            return 400, {"error": "amount"}
        with transaction(self.args.socket) as db:
            previous = db.get("payment:" + key)
            if previous:
                if previous["payload"] != payload:
                    return 409, {"error": "IDEMPOTENCY_KEY_CONFLICT"}
                return previous["status"] if previous["status"] == 402 else 200, previous["result"]
            if payload["customer_id"] == "CUST-DECLINE":
                result, status = {"status": "DECLINED"}, 402
            else:
                effect = str(uuid.uuid4())
                db.sql("INSERT INTO charges VALUES(?,?,?,?)", effect, body["intent_id"], key,
                       body["amount_cents"])
                result, status = {"charge_id": effect, "status": "COMMITTED"}, 201
            db.put("payment:" + key, {"payload": payload, "result": result, "status": status})
        return status, result

    def inventory(self, method, path, body):
        with transaction(self.args.socket) as db:
            stock = db.get("stock")
            if method == "GET" and path == "/stock":
                return 200, stock
            if method == "POST" and path == "/reservations":
                key = body["operation_key"]
                payload = {k: body[k] for k in ("order_id", "qty")}
                if type(payload["qty"]) is not int or payload["qty"] <= 0:
                    return 400, {"error": "quantity"}
                previous = db.get("reservation:" + key)
                if previous:
                    if previous["payload"] != payload:
                        return 409, {"error": "IDEMPOTENCY_KEY_CONFLICT"}
                    return 200, previous["result"]
                if stock["available"] < payload["qty"]:
                    return 409, {"error": "INSUFFICIENT_STOCK"}
                stock["available"] -= payload["qty"]
                stock["held"] += payload["qty"]
                result = {"reservation_id": key, "status": "HELD"}
                db.put("reservation:" + key, {"payload": payload, "result": result})
                db.put("stock", stock)
                return 201, result
            if method == "POST" and path == "/release":
                key = body["reservation_id"]
                previous = db.get("reservation:" + key)
                if previous is None:
                    return 404, {"error": "not_found"}
                if previous["result"]["status"] == "HELD":
                    qty = previous["payload"]["qty"]
                    stock["available"] += qty
                    stock["held"] -= qty
                    previous["result"]["status"] = "RELEASED"
                    db.put("reservation:" + key, previous)
                    db.put("stock", stock)
                return 200, previous["result"]
        return 404, {"error": "not_found"}

    def order(self, method, path, body):
        if method == "POST" and path == "/orders":
            payload = {k: body[k] for k in ("client_request_id", "customer_id", "qty", "amount_cents")}
            if (type(payload["qty"]) is not int or payload["qty"] <= 0 or
                    type(payload["amount_cents"]) is not int or payload["amount_cents"] <= 0):
                return 400, {"error": "invalid_order"}
            order_id = payload["client_request_id"]
            if not isinstance(order_id, str) or not order_id or len(order_id) > 80:
                return 400, {"error": "invalid_id"}
            with transaction(self.args.socket) as db:
                previous = db.get("order:" + order_id)
                if previous:
                    if previous["payload"] != payload:
                        return 409, {"error": "CLIENT_REQUEST_ID_CONFLICT"}
                    return 200, previous
                order = {"order_id": order_id, "payload": payload, "status": "RECEIVED",
                         "attempts": 0}
                db.put("order:" + order_id, order)
            return 202, order
        if method == "GET" and path.startswith("/orders/"):
            with transaction(self.args.socket) as db:
                order = db.get("order:" + path.removeprefix("/orders/"))
            return (200, order) if order else (404, {"error": "not_found"})
        return 404, {"error": "not_found"}

    def update(self, order):
        with transaction(self.args.socket) as db:
            db.put("order:" + order["order_id"], order)

    def step(self, order):
        identity, payload = order["order_id"], order["payload"]
        state = order["status"]
        if state in {"RECEIVED", "RESERVING"}:
            order["status"] = "RESERVING"
            self.update(order)
            status, result = http(self.args.inventory_port, "POST", "/reservations",
                                  {"order_id": identity, "qty": payload["qty"],
                                   "operation_key": "rsv:" + identity})
            if status in (200, 201):
                order.update(status="RESERVED", reservation_id=result["reservation_id"])
            elif result.get("error") == "INSUFFICIENT_STOCK":
                order["status"] = "REJECTED_STOCK"
            else:
                raise RuntimeError("reservation failed")
            self.update(order)
        elif state in {"RESERVED", "CHARGING"}:
            order["status"] = "CHARGING"
            order["attempts"] += 1
            self.update(order)
            # IF-001 intentionally faulty: a fresh identity per HTTP attempt.
            key = str(uuid.uuid4()) if self.args.key_strategy == "faulty" else "chg:" + identity
            status, result = http(self.args.payment_port, "POST", "/charges",
                                  {"order_id": identity, "intent_id": identity,
                                   "customer_id": payload["customer_id"],
                                   "amount_cents": payload["amount_cents"], "operation_key": key},
                                  timeout=0.4)
            if status in (200, 201):
                order.update(status="CHARGED", charge_id=result["charge_id"])
            elif status == 402:
                order["status"] = "COMPENSATING"
            else:
                raise RuntimeError("payment failed")
            self.update(order)
        elif state == "CHARGED":
            order["status"] = "CONFIRMED"
            self.update(order)
        elif state == "COMPENSATING":
            status, result = http(self.args.inventory_port, "POST", "/release",
                                  {"reservation_id": order["reservation_id"],
                                   "operation_key": "rls:" + order["reservation_id"]})
            if status == 200 and result["status"] == "RELEASED":
                order["status"] = "CANCELLED_DECLINED"
                self.update(order)

    def worker(self):
        while True:
            try:
                with self.lock:
                    with transaction(self.args.socket) as db:
                        rows = db.sql("SELECT value FROM app_state")
                    for row in rows:
                        order = json.loads(row[0])
                        try:
                            self.step(order)
                        except Exception as exc:
                            print(canonical({"event": "retry_pending", "order_id": order["order_id"],
                                             "error": type(exc).__name__}), flush=True)
            except Exception as exc:
                print(canonical({"event": "worker_error", "error": type(exc).__name__}), flush=True)
            time.sleep(0.05)  # Durable pending phases retry after transient errors.


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", choices=["order", "inventory", "payment"], required=True)
    parser.add_argument("--socket", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--payment-port", type=int, default=8084)
    parser.add_argument("--inventory-port", type=int, default=8082)
    parser.add_argument("--key-strategy", choices=["faulty", "reference"], default="faulty")
    args = parser.parse_args()
    app = App(args)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.handle_request()

        def do_POST(self):
            self.handle_request()

        def handle_request(self):
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if size < 0 or size > 8192:
                    raise ValueError("request size")
                body = json.loads(self.rfile.read(size)) if size else {}
                status, result = app.dispatch(self.command, self.path, body)
            except (ValueError, KeyError, TypeError):
                status, result = 400, {"error": "invalid_request"}
            except Exception:
                status, result = 503, {"error": "temporarily_unavailable"}
            encoded = canonical(result).encode()
            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *_):
            pass

    if args.service == "order":
        threading.Thread(target=app.worker, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
