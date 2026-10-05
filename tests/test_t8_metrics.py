"""Derived T8 metrics: calculations, missing data and source immutability."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('derive_t8', ROOT / 'scripts' / 'derive-t8-metrics.py')
derive_t8 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(derive_t8)

SUMMARY = ROOT / 'benchmarks/t8/summary.json'
DERIVED = ROOT / 'benchmarks/t8/derived_metrics.json'


def attempt(slot, decision, elapsed, verified, cases=None):
    return {'slot': slot, 'final_decision': decision, 'elapsed_seconds': elapsed,
            'independently_verified': verified, 'case_outcomes': cases or []}


def case(name, decision='accept_for_review', **properties):
    base = {'P%d' % i: 'pass' for i in range(1, 8)}
    base.update(properties)
    return {'case': name, 'decision': decision, 'properties': base}


class DerivedMetricTests(unittest.TestCase):
    def test_resolution_time_excludes_unresolved_runtime(self):
        summary = {'attempts': [attempt(1, 'unresolved', 500.0, False),
                                attempt(2, 'accept_for_review', 10.0, True),
                                attempt(3, 'reject_behavior', 30.0, True)]}
        metrics = derive_t8.derive(summary)['metrics']
        resolution = metrics['resolution_time_seconds']
        self.assertEqual({'n': 2, 'min': 10.0, 'median': 20.0, 'max': 30.0}, resolution['value'])
        self.assertIn('2 of 3', resolution['denominator'])
        self.assertIn('not a resolution time', resolution['note'])
        # Runtime keeps every attempt and is labelled as runtime.
        self.assertEqual(3, metrics['runtime_seconds_all_attempts']['value']['n'])
        self.assertEqual(500.0, metrics['runtime_seconds_all_attempts']['value']['max'])

    def test_clean_regressions_count_failures_not_not_applicable(self):
        summary = {'attempts': [
            attempt(1, 'accept_for_review', 10.0, True,
                    [case('canonical_mixed_payload', P6='not_applicable'),
                     case('contended_inventory')]),
            attempt(2, 'reject_behavior', 20.0, True,
                    [case('canonical_mixed_payload', P3='fail'),
                     case('dual_restart_response_loss', P4='fail')])]}
        metrics = derive_t8.derive(summary)['metrics']
        clean = metrics['clean_workload_regressions']
        # not_applicable is not a failure; the fault case is not a clean case.
        self.assertEqual(1, clean['value'])
        self.assertEqual([{'slot': 2, 'case': 'canonical_mixed_payload', 'failed_properties': ['P3']}],
                         clean['detail'])
        self.assertIn('3 clean case instances', clean['denominator'])

    def test_unmeasured_metrics_are_null_with_a_reason_never_zero(self):
        metrics = derive_t8.derive({'attempts': [attempt(1, 'unresolved', 5.0, False)]})['metrics']
        for name in ('reproduction_rate', 'time_to_reproduction_seconds', 'lost_orders',
                     'duplicate_effects'):
            with self.subTest(metric=name):
                self.assertIsNone(metrics[name]['value'])
                self.assertTrue(metrics[name]['unavailable_reason'].strip())
        self.assertIn('not applied retroactively', metrics['reproduction_rate']['unavailable_reason'])
        self.assertIsNone(metrics['resolution_time_seconds']['value'],
                          'no resolved attempt means no resolution time')

    def test_property_verdicts_are_not_reported_as_counts(self):
        summary = {'attempts': [attempt(1, 'reject_behavior', 10.0, True,
                                        [case('decline_then_new_order', 'reject_behavior', P3='fail')])]}
        metrics = derive_t8.derive(summary)['metrics']
        self.assertIsNone(metrics['lost_orders']['value'])
        self.assertIn('[1]', metrics['lost_orders']['unavailable_reason'])
        self.assertIn('not a count', metrics['lost_orders']['unavailable_reason'])

    def test_real_campaign_preserves_all_twelve_attempts(self):
        derived = derive_t8.derive(json.loads(SUMMARY.read_text()))
        preserved = derived['attempts_preserved']
        self.assertEqual(12, preserved['total'])
        self.assertEqual({'unresolved': 8, 'accept_for_review': 2, 'reject_behavior': 2},
                         preserved['outcomes'])
        self.assertFalse(preserved['ranking_supported'])
        self.assertEqual(4, derived['metrics']['resolution_time_seconds']['value']['n'])
        self.assertEqual(0, derived['metrics']['clean_workload_regressions']['value'])

    def test_derived_file_is_current_and_records_an_unmodified_source(self):
        self.assertEqual(0, derive_t8.main(['--check']), 'derived_metrics.json is stale')
        stored = json.loads(DERIVED.read_text())
        self.assertEqual(hashlib.sha256(SUMMARY.read_text(encoding='utf-8').encode('utf-8')).hexdigest(),
                         stored['source']['sha256'],
                         'the source hash must be of canonical text, not checkout bytes')
        self.assertEqual(json.loads(SUMMARY.read_text())['freeze_sha256'], stored['source']['freeze_sha256'])

    def test_deriving_never_writes_the_frozen_summary(self):
        before = SUMMARY.read_bytes()
        derive_t8.derive(json.loads(SUMMARY.read_text()))
        self.assertEqual(before, SUMMARY.read_bytes())


if __name__ == '__main__':
    unittest.main()
