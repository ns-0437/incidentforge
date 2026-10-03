"""Freeze protocol and model-visible isolation checks, without inference."""
import importlib.util
import unittest
from pathlib import Path
from tests import test_t4
from incidentforge.workspace import Workspace
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('campaign',ROOT/'scripts/run-t8.py')
campaign=importlib.util.module_from_spec(spec);spec.loader.exec_module(campaign)

class T8Tests(unittest.TestCase):
    def test_equal_independent_slots_and_rotated_order(self):
        rows=campaign.schedule();self.assertEqual(12,len(rows))
        for family in ('IF-001','IF-002'):
            for variant in ('B0','B1','B2'):
                self.assertEqual(2,sum(r['incident']==family and r['variant']==variant for r in rows))
        self.assertNotEqual([r['variant'] for r in rows[:3]],[r['variant'] for r in rows[3:6]])
    def test_agent_cannot_read_holdout_docs_history_or_runs(self):
        w=Workspace(ROOT)
        for name in ('evaluation/holdout.py','docs/T8_PROTOCOL.md','.git/config','runs/t4-budget.sqlite'):
            with self.assertRaises(ValueError): w.read(name)
    def test_holdout_not_available_as_model_action(self):
        from incidentforge.records import action
        with self.assertRaises(ValueError): action('{"action":"final_holdout"}')

if __name__=='__main__': unittest.main()
