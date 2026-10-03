# IncidentForge: authoring incident specification

Updated 2026-10-03. PRIVATE AUTHORING MATERIAL: contains intended defects and repair controls. NEVER copy this document, planning docs or repository history into a runtime agent bundle. Only contracts/public/ content is agent-visible. T2 implements the local contract and development controls; see T2_STATUS.md for measured limits. T6 implements the IF-002 development defect and controls; final campaign remains later work. See BENCHMARK_DEVELOPMENT.md for actual restart scheduling and limitations.

## Application contract

Three separate HTTP processes, separate durable stores, real retries and crash restarts. Synthetic payments. Persistence broker/audit as specified in ARCHITECTURE.md; it records effects but does not implement idempotency. All amounts are integer cents; one payment intent per order in v1.

| API | Required semantics |
|---|---|
| POST /orders | client_request_id, customer_id, item quantities, amount, currency; durably accept 202; replay existing logical order on same key/payload; reject changed payload 409 |
| GET /orders/{id} | Logical status and effect references; trusted evaluator cross-checks durable state |
| POST /orders/{id}/cancel | Stable cancellation request ID; linearize against confirmation; pending order enters durable cancellation; confirmed order returns 409; repeated cancel preserves result |
| POST /reservations | order_id, stable operation key and items; HELD reservation or declared insufficient-stock rejection |
| POST /reservations/{id}/release | Stable key; idempotent HELD -> RELEASED; already released replays; no extra stock credit |
| POST /charges | order_id, payment_intent_id, customer_id, amount, currency and operation key; committed effect or configured business decline |
| POST /refunds | charge_id, full amount in v1, stable operation key; append refund effect once; never delete charge history |
| GET /healthz | Bounded readiness; health response alone does not prove recovery |

v1 confirmed orders RETAIN HELD reservations. No CONSUMED transition or fulfillment API is needed: fulfillment is outside this fixture. A confirmed order has a charge and matching HELD stock. Cancelling before confirmation must eventually release holds and refund any committed charge, even if its response was lost. Do not terminalize cancellation before reconciliation and compensation finish.

Order phases: RECEIVED -> RESERVING -> RESERVED -> CHARGING -> CHARGED -> CONFIRMED. Insufficient stock -> REJECTED_STOCK; deterministic decline -> COMPENSATING -> CANCELLED_DECLINED; successful pending cancellation -> CANCEL_REQUESTED -> COMPENSATING -> CANCELLED_BY_CLIENT. Transitions/recovery intent are durable. Confirmation and accepting cancellation serialize via a durable transaction; after cancellation wins no later CONFIRMED is allowed. Recovery of COMPENSATING and CANCEL_REQUESTED is required.

One operation identity per intended reservation, payment, release or refund; either deterministic derivation or a random key durably saved before first use is valid. Same key + canonical payload returns the original outcome without another effect. Different payload yields 409 with no mutation. In-flight duplicates may receive declared retryable IN_PROGRESS; after original completion they must converge. Compare business outcome/IDs, not byte equality of HTTP status or timestamps. Canonicalize field order, item ordering and duplicate SKU aggregation; integers only. Changing downstream keys does not change the trusted logical payment intent.

Retries: proposed burst of three attempts, followed by durable pending recovery with bounded backoff, not permanent abandonment. A fixed total-attempt cap cannot guarantee completion after faults that outlast it. Workloads define maximum faults/duration, service availability and finite arrivals; evaluator bounds total run time and reports failure if recovery misses its frozen deadline. Values are pilot-calibrated configuration, not hardcoded benchmark hints.

## Properties and independent expectations

Trusted workload registry holds accepted requests, expected identities, prices, customer decline rules, cancellations and initial inventory. Candidate responses do not decide eligibility or whether a decline test applies.

| Property | Test |
|---|---|
| P1 payment safety | Count unique committed charge effects in trusted audit per original payment intent; at most one, even if later refunded; every effect must map to a valid registered intent and amount |
| P2 confirmation safety | CONFIRMED implies one valid charge, no refund, and matching HELD reservation; client-visible claims agree with durable state |
| P3 eligible completion | Nondeclined, noncancelled, nonoversubscribed accepted workload completes successfully by the frozen recovery deadline |
| P4 rejection/cancellation | Independently declared decline, stock rejection or accepted cancellation reaches the specified terminal outcome by its deadline; no unreconciled charge/hold remains |
| P5 inventory | At every committed inventory mutation, available = initial stock - active HELD quantities and is nonnegative; releases occur once; rejected/cancelled orders eventually have no hold |
| P6 idempotency | Same logical request retains outcome/effect identity across retries/concurrency/restart; changed payload conflicts; IN_PROGRESS is temporary, not a terminal replay failure |
| P7 evidence integrity | Audit capture, broker policy, boundary, workload completion and export integrity all valid; failure invalidates evaluation, never supplies a behavioral pass |

Maintain a trusted inventory mutation history as well as payment effects to evaluate 'never negative'; occasional snapshots cannot establish that invariant. Broker audits stock/reservation mutations transactionally without enforcing nonnegative stock itself. The application must enforce business consistency.

P3 uses separate nonoversubscribed workloads with sufficient aggregate stock (e.g. 20 eligible orders require at least their summed quantities). Contention tests permit any valid serialization: winners never exceed capacity, losers receive stock rejection by deadline, no holds leak. They do not require every concurrent request to win or accept arbitrary cancellation as a valid stock rejection. Check returned outcomes against the committed reservation history.

Let finite submissions stop at T_submit_end and injected faults cease at T_fault_end. Recovery starts at T0=max(T_submit_end,T_fault_end), provided required services have actually restarted. An application that cannot restart is a candidate failure, not a reason to exclude its orders. Orders already correctly terminal contribute zero residual latency. Late submissions are invalid workload execution. Calibrate positive recovery bounds on development-only schedules/reference behavior: proposed max(1 second, ceil(3*maximum observed residual latency)), with startup margin separately budgeted. Freeze before final evaluation; no recalibration on final results. Pilot selects repetitions with explicit cost/precision rationale, not a mandatory 200-order remote run.

## IF-001: payment commit followed by response loss

1. Accept one valid order; reserve stock.
2. Order calls Payment with its operation identity.
3. Payment commits a charge; protected transaction audit confirms commit.
4. Proxy withholds the matching response; correlate request and commit identity.
5. Order times out and retries; faulty source creates a new operation key.
6. Payment commits a second effect; audit shows two charges for one intended payment.

A response-only fault barrier is permitted for reproducing transport symptoms but is not evidence that step 3 occurred. Missing commit/correlation makes this schedule inconclusive. Snapshot only through trusted backup/quiescence; no raw live SQLite file copies.

Primary authored defect: key created per attempt. Candidate explanations include identity propagation, non-atomic claim, volatile dedup state and retry/API mismatch. Vary one factor: stable identity with/without concurrency; stable identity with/without restart; response code with fixed key. Different keys support the primary defect but do not refute coexisting faults. Negative results in finite trials weaken rather than universally refute a race explanation.

An additional non-atomic Payment defect is a DEVELOPMENT variant, not automatically mandatory in every IF-001 case. Preserve a simple IF-001 for first end-to-end delivery. Use a declared combined variant to test incomplete repairs after the simple path works. This adds no third incident family. Difficulty and variant placement freeze after development pilot, before holdout creation/use. Never remove hard final cases after seeing results.

## IF-002: lost compensation across restart

Inventory reserves, configured customer is declined, Order durably enters COMPENSATING, but its recovery implementation omits that state and relies on a volatile release task. Crash Order after the durable state transition before release. After restart the hold remains. The durable COMPENSATING state already records intent; the precise defect is missing recovery of that intent, not absence of all durable intent.

Required outcome: release exactly once and reach CANCELLED_DECLINED. If a separate cancellation scenario has a committed charge, refund exactly once too. Distinguish omitted recovery state from lost release response and Inventory release dedup defects. Trusted commit barriers identify the pre-release durable state; source log messages alone are not authoritative barriers. T6 implements this as a volatile pending-compensation set: COMPENSATING is durable but the recovery loop skips it when the set is empty after restart. The development schedule also restarts Inventory, retaining its durable store, to discard queued pre-crash requests before Order restarts.

## Controls and expected verdicts

Build every harmful fixture from a known-good revision so the named defect is isolated. The unpatched incident revisions are separate negative controls. A table entry names a required violation, not proof that every other property passes. Evaluate all applicable properties.

| Control | Schedule/precondition | Required verdict |
|---|---|---|
| Known-good reference | Clean, response loss, stable-key concurrency/restart, decline/cancel | All applicable properties pass; boundary passes |
| Faulty IF-001 | Commit response lost, fresh retry key | P1 fails |
| Disable retries AND recovery | Eligible order stranded after response loss | P3 fails |
| Always success without effect | Accepted order confirmed without charge | P2 fails; configured declined workload also fails P4 |
| Cancel all | Eligible noncancelled workload | P3 fails |
| Memory-only dedup | Same key after Payment crash | P1/P6 fail |
| Race-prone claim | Concurrent same-key requests with repeatable interleaving | P1/P6 fail when duplicate witnessed; unwitnessed race is inconclusive |
| Charge then delete | Candidate tries effect deletion/trigger removal | Broker denies and records attempted policy violation; no silent acceptance |
| Faulty IF-002 | Crash after COMPENSATING before release | P4 fails |
| Repair IF-002 | Same schedule, recovery resumes compensation | P4/P5 pass along with other applicable checks |

Observer controls: two 201s/one committed effect count as ONE; two committed effects/one response count as TWO; 201/no commit counts as ZERO and fails confirmation if claimed; rolled-back inserts count as ZERO. Broker deliberately permits duplicate inserts under distinct effect IDs so the evaluator can witness the original fault. Test a transaction that inserts then attempts deletion: it must be denied/rolled back under a documented policy, never disappear unnoticed as a committed effect.

## Reset, visibility and outcomes

Whole-run reset includes broker stores/audit, proxy, timers, queued work, process identities and artifacts. Crash with SIGKILL, record process start identity (PID alone can be reused), restart with identical durable store and verify recovery. Record synchronization barriers and residual scheduler nondeterminism. Any observed safety violation fails its schedule; repetitions are not majority voting.

Export only explicit contracts/public files into runtime bundles, plus source, locks, topology, initial data and incomplete incident evidence. Exclude this document, all planning notes, controls, evaluator, protected schedules, hidden defects and Git history. Test complete bundle/image/context contents, not only filenames. Public docs can state business invariants and API semantics; they must not disclose exact defective expressions or a reference patch.

Candidate hangs/crashes and blocked tampering are candidate outcomes. Proven platform outage is infrastructure failure. Unknown cause remains unknown. Observer/boundary failure is invalid evaluation. Watchdog firing alone does not establish which class occurred. All launches, repeats, costs and incomplete outcomes remain in the ledger.
