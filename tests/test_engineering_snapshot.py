"""The frozen engineering snapshot is complete, consistent and guarded against silent drift."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from eri import engineering
from eri.capability_planning import load_config


class SnapshotTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values, cls.allocations, cls.manifest = engineering.snapshot_tables()
        cls.cfg = load_config()

    def test_every_case_candidate_and_recovery_stress_is_present(self):
        for case in self.cfg['cases']:
            candidates = engineering.candidates(case)
            self.assertTrue(candidates)
            for candidate in candidates:
                rows = self.values[(self.values.case_id == case) & (self.values.candidate == candidate)]
                self.assertEqual(len(rows), 4, f'{case}/{candidate}')
                self.assertTrue(((self.allocations.case_id == case) & (self.allocations.candidate == candidate)).any())
        self.assertEqual(self.manifest['rows'], dict(values=len(self.values), allocations=len(self.allocations)))

    def test_engineering_source_is_the_snapshot(self):
        self.assertEqual(engineering.source(), 'snapshot')

    def test_wet_mass_only_for_the_lander(self):
        self.assertTrue(self.values.loc[self.values.case_id == 'HUMANS', 'vehicle_wet_kg'].isna().all())
        self.assertTrue(self.values.loc[self.values.case_id == 'HLS_SORTIE', 'vehicle_wet_kg'].notna().all())

    def test_changed_recovery_assumption_is_refused(self):
        cfg = load_config()
        cfg['recovery_shortfall'] = cfg['recovery_shortfall'] + 0.05
        with self.assertRaises(ValueError):
            engineering.technical(None, None, cfg, 'HUMANS', 'integrated', ('water_recovery',))

    def test_other_stresses_do_not_change_physical_values(self):
        base, _ = engineering.technical(None, None, self.cfg, 'HLS_SORTIE', 'integrated')
        same, _ = engineering.technical(None, None, self.cfg, 'HLS_SORTIE', 'integrated', ('supplier_delay', 'air_maturity'))
        self.assertEqual(base, same)


if __name__ == '__main__':
    unittest.main()
