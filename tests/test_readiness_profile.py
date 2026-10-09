"""Ensure planning scenarios never erase missing programme evidence."""
from copy import deepcopy
from datetime import date
from pathlib import Path
import json
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from eri.capability_planning import study
from eri.readiness_profile import build_profiles


class ProfileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables = study()

    def test_quarter_target_and_structure_do_not_establish_readiness(self):
        profiles = build_profiles(self.tables)
        analogs = next(p for p in profiles if p['case_id'] == 'ANALOGS' and p['candidate'] == 'integrated')
        self.assertIsNone(analogs['scenario_need_date'])
        self.assertEqual(analogs['required_milestone_window'], ['2029-01-01', '2029-03-31'])
        self.assertEqual(analogs['structure_availability_target'], '2027-12-31')
        self.assertEqual(analogs['structure_status'], 'project_target')
        self.assertEqual(analogs['readiness_status'], 'unresolved')
        self.assertIsNone(analogs['evidence_supported_delivery_date'])
        self.assertIsNone(analogs['cost_margin_keur'])
        json.dumps(profiles, allow_nan=False)

    def test_margin_bounds_reverse_duration_endpoints(self):
        for p in build_profiles(self.tables):
            if p['functional_scope'] == 'allocated':
                lo, hi = p['scenario_schedule_margin_days']
                self.assertLessEqual(lo, hi)
                duration_lo, duration_hi = p['scenario_duration_days']
                begin, end = map(date.fromisoformat, p['required_milestone_window'])
                self.assertAlmostEqual(hi - lo, duration_hi - duration_lo + (end - begin).days)

    def test_missing_schedule_stays_unknown_and_reference_is_not_ranked(self):
        tables = deepcopy(self.tables)
        tables['capabilities'].loc[:, 'schedule_margin_days_high'] = float('nan')
        profiles = build_profiles(tables)
        self.assertTrue(all(p['scenario_schedule_margin_days'] == [None, None] for p in profiles))
        reference = next(p for p in profiles if p['candidate'] == 'open')
        self.assertEqual(reference['readiness_status'], 'required_function_missing')
        self.assertTrue(reference['missing_functions'])
        json.dumps(profiles, allow_nan=False)

if __name__ == '__main__':
    unittest.main()
