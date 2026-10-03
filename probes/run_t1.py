"""Local T1 acceptance, T0 regressions, and exported scenario evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import sqlite3
import sys
import tempfile
import time
import traceback
import unittest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--require-linux', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    suite = unittest.defaultTestLoader.loadTestsFromNames([
        'tests.test_store', 'tests.test_linux_boundary', 'tests.test_t1'])
    buffer = io.StringIO()
    result = unittest.TextTestRunner(stream=buffer, verbosity=2).run(suite)
    scenarios, export_error = [], None
    if result.wasSuccessful() and not result.skipped:
        from fixture.harness.t1 import World
        try:
            with tempfile.TemporaryDirectory(prefix='if-evidence-') as temp:
                Path(temp).chmod(0o755)
                for name, fault, strategy, expected in (
                    ('clean', False, 'faulty', 1),
                    ('if001-unpatched', True, 'faulty', 2),
                    ('if001-reference', True, 'reference', 1)):
                    world = World(Path(temp) / name, fault=fault, strategy=strategy)
                    try:
                        world.start()
                        assert world.submit()[0] == 202
                        order = world.terminal()
                        assert order['status'] == 'CONFIRMED'
                        data = world.export(args.output / name)
                        assert len(data['effects']) == expected
                        (args.output / name / 'order.json').write_text(json.dumps(order, indent=2))
                        scenarios.append({'name': name, 'effects': len(data['effects']),
                                          'order_status': order['status']})
                    finally:
                        world.close()
        except Exception:
            export_error = traceback.format_exc()
    root = Path(__file__).resolve().parents[1]
    passed = result.wasSuccessful() and not result.skipped and export_error is None
    report = {'stage': 'T1', 'status': 'PASS' if passed else 'FAIL',
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'python': sys.version, 'platform': platform.platform(), 'sqlite': sqlite3.sqlite_version,
        'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'skipped': [(str(t), reason) for t, reason in result.skipped],
        'duration_seconds': round(time.monotonic() - started, 3),
        'scenarios': scenarios, 'export_error': export_error,
        'source_sha256': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for folder in ('fixture', 'tests', 'probes')
                          for p in (root / folder).rglob('*.py')},
        'model_calls': 0, 'remote_calls': 0,
        'limitations': ['Manual reference control, not an agent-generated repair.',
                        'T2 full verifier, harmful repairs, cancellation/refunds remain pending.',
                        'Local Docker evidence only; ConTree compatibility untested.']}
    (args.output / 'tests.log').write_text(buffer.getvalue())
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(buffer.getvalue())
    print(json.dumps({k: v for k, v in report.items() if k != 'source_sha256'}, indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
