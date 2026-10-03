# T7: local investigation console

The local interface is implemented at http://127.0.0.1:8765. It uses the existing standard-library Python runtime, with no new npm or Python dependencies. The original brief remains unchanged.

## Delivered

- IF-001/IF-002 selection and B0/B1/B2 protocol selection.
- Real bounded launch through the existing CLI/controller, polling status, cancellation request and terminal process receipt.
- Recorded run history and incident filtering. Recorded evidence is explicitly labeled and does not invoke inference.
- Timeline, hypotheses, model interpretations, experiment specifications and measured observations, source diffs and independent property-level validation.
- Persisted project budget and estimated per-run usage; unresolved reservations block new launches.
- Curated review ZIP containing review.json, patch.diff, README.txt and SHA256SUMS.txt. Private evaluator schedules, raw prompts, databases and credentials are excluded.

Model claims are labeled unverified. Legacy reports that mixed model claims into the reason field are presented separately from the independent verdict. Export requires a verified event chain, artifact hashes and a terminal report matching the final report event. A patch is retained for review, not promoted automatically.

## Verification

22 controller/UI tests pass. UI-specific checks cover same-origin/session-token enforcement, duplicate launch prevention, cancellation and process termination, pending-budget blocking, path traversal, safe text rendering, Unicode evidence, export allowlisting and rejection of truncated evidence.

Browser checks exercised recorded run selection, hypotheses, experiment disclosures, patch diff, accepted validation, and download. The downloaded b2-20261003T052430Z-fc5821-review.zip passed its SHA256SUMS checks. Narrow and 1280px desktop layouts were inspected. The final observation-summary presentation change was followed by passing tests; the browser connection became unavailable before its final visual recheck. The local HTTP server still returned 200.

Real launch/cancel smoke test: ui-0e7e9597cc8f48d3bf77a8c24386c3ae. Cancellation occurred during Docker reproduction, cleanup was confirmed, the launcher exited, and the UI returned to recorded state. Zero inference calls and zero inference cost. Total estimated project inference spend remains $0.029322, within the shared $0.20 cap.

## Operating

The server binds only 127.0.0.1. Start from the project directory with:

```powershell
python scripts/serve-ui.py --port 8765
```

Open http://127.0.0.1:8765. Browsing recorded results is free. Launch uses existing Nebius credentials and requires Docker plus the cached python:3.12-slim image. Credentials never enter the browser. A cancellation during inference waits for the current HTTP call (timeout 60 seconds); cancellation checks prevent the next model or execution dispatch. The UI does not report a cancellation request as confirmed termination.

Keep the server running until live work is terminal. If the UI server exits during an investigation, its persisted active launch guard blocks new UI launches on restart until the old process is reconciled. Automatic orphan recovery is not implemented. Do not blindly delete the guard or retry a pending inference reservation. This is a local operator console, not a public multi-user deployment. CLI launches should not be started concurrently with UI runs.

## Next

T7's local product interface is delivered. Before T8 benchmark freeze, complete the already documented remote controller integration, diagnosis/interpretation quality checks, editable developer-test capability, stronger record typing and recovery calibration. T6's negative B1/B2 results remain visible. T8 must not turn the current development pilots into final comparative claims.
