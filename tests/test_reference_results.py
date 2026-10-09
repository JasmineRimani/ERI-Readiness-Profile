"""The public release reproduces the ERI results published in the IAC-26 paper (Table 2, Figs. 1, 5 and 6)."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from eri import engineering
from eri.capability_planning import study
from eri.readiness_profile import build_profiles

# Table 2 of the paper: elapsed days, direct work (kEUR) and schedule margin (days).
TABLE_2 = {
    ('HLS_SORTIE', 'integrated'): ((270, 810), (115, 345), (-445, 95)),
    ('HLS_SORTIE', 'distributed'): ((300, 900), (175, 525), (-535, 65)),
    ('ANALOGS', 'integrated'): ((498, 781), (165, 495), (-50, 322)),
    ('ANALOGS', 'distributed'): ((538, 901), (265, 795), (-170, 282)),
}
# Fig. 1: accounted ECLSS package mass [kg]; lander upper-retention wet mass [t].
FIG_1_MASS = {('HLS_SORTIE', 'open'): 614, ('HLS_SORTIE', 'integrated'): 1530, ('HLS_SORTIE', 'distributed'): 953,
              ('ANALOGS', 'integrated'): 1127, ('ANALOGS', 'distributed'): 763}
FIG_1_WET_T = {'open': 33.73, 'integrated': 40.09, 'distributed': 35.80}


class ReferenceResultsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables = study()
        cls.profiles = {(p['case_id'], p['candidate']): p for p in build_profiles(cls.tables)}

    def test_table_2(self):
        for key, (duration, cost, margin) in TABLE_2.items():
            p = self.profiles[key]
            self.assertEqual(tuple(p['scenario_duration_days']), duration, key)
            self.assertEqual(tuple(p['scenario_work_cost_keur']), cost, key)
            self.assertEqual(tuple(p['scenario_schedule_margin_days']), margin, key)

    def test_open_lander_is_a_reference_only(self):
        self.assertEqual(self.profiles[('HLS_SORTIE', 'open')]['functional_scope'], 'reference_outside_regenerative_scope')

    def test_analogs_integrated_completion_window(self):
        row = self.tables['capabilities'].query("case_id == 'ANALOGS' and candidate == 'integrated'").iloc[0]
        self.assertEqual((row.available_date_low, row.available_date_high), ('2028-05-13', '2029-02-20'))

    def test_figure_1_masses_from_the_snapshot(self):
        values, _, _ = engineering.snapshot_tables()
        base = values[(values.air_recovery == 0) & (values.water_recovery == 0)].set_index(['case_id', 'candidate'])
        for key, mass in FIG_1_MASS.items():
            self.assertEqual(round(base.loc[key, 'eclss_kg']), mass, key)
        for candidate, wet in FIG_1_WET_T.items():
            self.assertAlmostEqual(base.loc[('HLS_SORTIE', candidate), 'vehicle_wet_kg'] / 1000, wet, places=2)

    def test_figure_6_all_declared_stresses(self):
        grid = self.tables['sensitivity_scenarios']
        flags = ['air_recovery', 'water_recovery', 'air_maturity', 'water_maturity', 'supplier_delay', 'shared_service']
        worst = grid[grid[flags].sum(axis=1) == len(flags)].set_index('case_id')
        self.assertEqual((worst.loc['ANALOGS', 'schedule_margin_days_high'], worst.loc['ANALOGS', 'schedule_margin_days_low']), (-320, 232))
        self.assertEqual((worst.loc['HLS_SORTIE', 'schedule_margin_days_high'], worst.loc['HLS_SORTIE', 'schedule_margin_days_low']), (-1405, -235))


if __name__ == '__main__':
    unittest.main()
