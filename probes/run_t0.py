"""Run T0 and emit machine-readable evidence. No model or cloud calls."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import sqlite3
import sys
import time
import unittest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-linux", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    suite = unittest.defaultTestLoader.loadTestsFromNames([
        "tests.test_store", "tests.test_linux_boundary"])
    buffer = io.StringIO()
    started = time.monotonic()
    result = unittest.TextTestRunner(stream=buffer, verbosity=2).run(suite)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "tests.log").write_text(buffer.getvalue(), encoding="utf-8")
    hashes = {str(path.relative_to(root)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
              for folder in ("fixture", "tests", "probes") for path in (root / folder).rglob("*.py")}
    report = {"stage": "T0", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "python": sys.version, "platform": platform.platform(), "sqlite": sqlite3.sqlite_version,
              "tests_run": result.testsRun, "failures": len(result.failures),
              "errors": len(result.errors), "skipped": [(str(t), reason) for t, reason in result.skipped],
              "duration_seconds": round(time.monotonic() - started, 3),
              "status": "PASS" if result.wasSuccessful() and not result.skipped else
                        "PARTIAL" if result.wasSuccessful() else "FAIL",
              "source_sha256": hashes, "remote_calls": 0, "model_calls": 0,
              "limitations": ["T0 only; no three-service HTTP app or full protected evaluator yet.",
                              "Linux tests must pass on ConTree separately before remote boundary claims.",
                              "Selected controls are coverage, not a proof against arbitrary adversaries."]}
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(buffer.getvalue())
    print(json.dumps({k: v for k, v in report.items() if k != "source_sha256"}, indent=2))
    return 0 if result.wasSuccessful() and not (args.require_linux and result.skipped) else 1


if __name__ == "__main__":
    raise SystemExit(main())
