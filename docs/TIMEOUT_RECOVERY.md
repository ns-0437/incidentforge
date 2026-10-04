# Conservative timeout recovery

The operator can reconcile a completed inference wall-time failure without
pretending the provider reported usage. The full reservation stays counted and
`actual` stays NULL. The project cap is unchanged. This does not retry a call,
resume its failed run or issue new inference.

Preview first (read-only):

```powershell
python scripts/reconcile-timeout.py RUN_ID
```

With explicit authority to use full-reservation accounting:

```powershell
python scripts/reconcile-timeout.py RUN_ID --apply --authority "Record the actual authorization here"
```

The tool validates the evidence hash chain and terminal timeout report, matches
exactly one unanswered reservation to the ledger, then changes only its status
from `reserved` to `conservative_unknown`. The status change and receipt are in
one SQLite transaction. Repeated application, nonterminal runs, settled calls
and mismatched/tampered evidence are rejected. Preview does not create a ledger.
The audit records the terminal event hash, evidence-file hash, amount, authority
and time. Evidence integrity is not independent provider billing confirmation.

The terminal wall-time report is generated after the local request worker is
killed and reaped. This does not assert the provider cancelled remote inference;
its possible cost is why the full maximum reservation remains counted.
Other pending calls, Sandbox-operation guards and the cumulative cap still apply.
Do not delete databases, clear reservations or change unknown actual usage to zero.

## October 4 accounting checkpoint

The completed v11 timeout was conservatively reconciled with no new inference:

- Cap: $0.400000
- Settled token-price estimate: $0.170632
- Four unknown reservations: $0.070780
- Total counted exposure: $0.241412
- Remaining allocation: $0.158588
- Pending reservations: zero

See `benchmarks/reliability/v11-reconciliation.json` for the receipt. The original
v11 report remains unchanged and still records the pending state at its finish.
The UI headline now displays total exposure; it separately shows settled estimates
and unknown reservations. This is project accounting, not a provider balance.
