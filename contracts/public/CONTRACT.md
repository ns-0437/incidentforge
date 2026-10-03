# IncidentForge business contract v1

Three HTTP services own independent durable stores. Amounts are positive integer
cents; currencies are uppercase three-letter codes. An order contains
client_request_id (1–64 letters/digits or `_.:-`), customer_id, items (sku, qty),
amount_cents and currency. Duplicate SKUs aggregate and item order is irrelevant.
At most 32 item entries and 1,000,000,000 units/cents are accepted.

POST /orders durably accepts 202; the same canonical request replays 200;
changed payload under the same client_request_id returns 409. GET /orders/{id}
returns the durable workflow result. POST /orders/{id}/cancel accepts a stable
cancel_request_id before confirmation, durably serializes with confirmation,
and eventually compensates. The same cancellation replays; reuse for a different
order conflicts. Terminal orders reject new cancellation with 409.

Inventory POST /reservations accepts order_id, operation_key and items. It holds
stock or returns 409 INSUFFICIENT_STOCK. POST /reservations/{id}/release takes an
operation_key and releases once. GET /stock exposes available and held by SKU.
Payment POST /charges accepts order_id, payment_intent_id (equal to order_id),
customer_id, operation_key, amount_cents and currency. CUST-DECLINE is declined
with 402. POST /refunds takes charge_id, operation_key, amount_cents and currency;
only full matching refunds are supported. Replays retain effect IDs; changed
payloads under the same operation key conflict. IDs are scoped by operation type.

There may be at most one committed charge per logical payment intent, even if
refunded. Confirmed orders retain matching HELD reservations and exactly one
unrefunded charge. Eligible orders must complete after bounded faults cease.
Declined, rejected and successfully cancelled orders must leave no unreconciled
charges or holds. Cancellation of an uncertain payment reconciles it before
refunding; compensation must survive crashes. Inventory must never be negative
or diverge from initial stock minus live holds at a committed transaction.

Retries and recovery preserve logical operation identity across concurrency and
restart. Pending work is durable, with bounded retry backoff rather than permanent
abandonment after a fixed retry count. GET /healthz signals readiness only.

The persistence client provides explicit begin/execute/commit/rollback sessions.
App state is mutable; canonical payment_effects are append-only. Schema changes
use trusted pre-run structured table/index declarations, not runtime SQL DDL.
New table/index/column names use app_ followed by lowercase letters/digits/_;
allowed types are TEXT, INTEGER and their PRIMARY KEY forms. Indexes may target
app_state, claims or declared app tables; canonical effects/audit are protected.
