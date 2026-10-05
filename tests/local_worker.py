"""A real local worker process for operator-lifecycle tests. Never a product path.

Run as a subprocess through Manager's injectable spawn seam. It writes the same
evidence shape the real worker does, so the operator API and the Manager watcher
see a genuine process start, progress, observe cancellation and exit.

It imports nothing from the inference or Sandbox clients and makes no network
call. The run root, control directory and ledger are supplied by the test and
live in a temporary directory.

Synchronisation is by file, so the test controls progress without sleeping:
  <control>/ready    written by the worker once its run directory and first
                     events exist, which is when the operator can cancel it
  <control>/proceed  written by the test to release the worker to its ending
"""
import argparse
import json
from pathlib import Path
import sys
import time

MODES = ('complete', 'cancel', 'crash')
WAIT_SECONDS = 30.0
POLL_SECONDS = 0.02


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--control', required=True, type=Path)
    parser.add_argument('--mode', required=True, choices=MODES)
    parser.add_argument('--incident', default='IF-002')
    parser.add_argument('--variant', default='B2')
    args = parser.parse_args(argv)

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
    from incidentforge.evidence import Evidence

    run = args.root / 'runs' / args.run_id
    evidence = Evidence(run, args.run_id)
    evidence.event('transition', {'from': 'INGEST', 'to': 'REPRODUCE'})
    (run / 'candidate').mkdir()
    (run / 'candidate' / 'INCIDENT.json').write_text(json.dumps({'incident_id': args.incident}))
    # From here the operator can see the run and may cancel it.
    (args.control / 'ready').write_text(args.run_id, encoding='utf-8')

    cancel_file = run / 'CANCEL'
    proceed = args.control / 'proceed'
    observed_cancel = False
    deadline = time.monotonic() + WAIT_SECONDS
    while time.monotonic() < deadline:
        if args.mode == 'cancel' and cancel_file.exists():
            observed_cancel = True
            break
        if proceed.exists():
            break
        time.sleep(POLL_SECONDS)

    if args.mode == 'cancel':
        if not observed_cancel:
            # Exit distinctly so a test never mistakes a timeout for cancellation.
            evidence.event('stopped', {'reason': 'cancellation never observed', 'state': 'REPRODUCE'})
            return 9
        evidence.event('stopped', {'reason': 'Cancelled: cancelled before action', 'state': 'REPRODUCE'})
        decision, reason, code = 'unresolved', 'Cancelled: cancelled before action', 1
    elif args.mode == 'crash':
        # Nonzero exit with no terminal report, as an abrupt worker failure leaves it.
        evidence.event('stopped', {'reason': 'worker exited unexpectedly', 'state': 'REPRODUCE'})
        (args.control / 'exited').write_text('crash', encoding='utf-8')
        return 3
    else:
        decision, reason, code = 'accept_for_review', 'All declared protected development checks passed.', 0

    evidence.event('transition', {'from': 'VERIFY', 'to': 'REPORT'})
    report = {'schema_version': 1, 'run_id': args.run_id, 'variant': args.variant,
              'incident': args.incident, 'decision': decision, 'reason': reason,
              'model_claim_unverified': 'TEST WORKER narrative, not a model output',
              'candidate_revision': 'rev-test' if decision == 'accept_for_review' else None,
              'edits': 1 if decision == 'accept_for_review' else 0,
              'accounting': {'calls': 0}, 'backend': 'test-local-worker',
              'limitations': ['Test worker. No inference or Sandbox execution occurred.']}
    evidence.event('report', report)
    (run / 'report.json').write_text(json.dumps(report, indent=2))
    (args.control / 'exited').write_text(decision, encoding='utf-8')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
