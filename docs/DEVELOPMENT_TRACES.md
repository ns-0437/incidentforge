# Development execution traces

IF-002 developer and compensation-probe runs now include bounded execution
observations from Order's `step` function. Each process generation has its own
first-seen unique line and return events, mapped to the candidate source hash.
Generation zero is the initial process; later generations are restarts.

The recorder captures no locals, arguments or return values. It emits at most
128 unique events per process. The reader consumes at most 128 KiB of log data,
validates line ranges and process identifiers, and records truncation/limit flags.
These events are not a full chronological trace: repeats are deduplicated.
An absent line is not proof that a path can never execute.

The wrapper runs after privilege drop under the candidate UID. It can be spoofed
or disabled by candidate code and is explicitly labeled as diagnostic evidence.
It does not expose private schedules, root-only state or protected verdicts.
Protected development validation and final schedules keep tracing disabled.
Instrumentation can affect timing; acceptance remains based on uninstrumented
protected checks. Do not use a traced development run as a new benchmark score.

## Validation

- 64 portable tests pass, including executed-line filtering, no local-value
  capture, deduplication, malformed rows and wrong-process filtering.
- 17 Linux checks pass. A traced faulty Order restart reaches its early return
  before release; the reference restart reaches release and completes cancellation.
- Linux evidence: `runs/t6-linux-20261003-180743/report.json` (local evidence only).

The original T8 evidence remains frozen. Any follow-up model result is reported
separately in POST_T8_RELIABILITY.md, including failed attempts.


## Compact return-site focus

The host now presents up to eight observed return sites per process, each with
nearby source context. Context is taken from the actual candidate source, not
from text claimed by the trace. A SHA-256 match is required before displaying
locations. Source edits suppress stale locations until a matching observation is
available. Generations stay separate, and truncation flags remain visible.
This summary appears in investigation and action guidance; it does not turn
candidate-process diagnostics into protected measurements or a causal verdict.

Three additional tests cover generation separation, forged snippet avoidance,
stale-source suppression and bounded incomplete data. The full portable suite is
now 68 passing tests; CI passed at `446ba21`. The one live pilot timed out before
model response, so repair improvement from this presentation is unestablished.
