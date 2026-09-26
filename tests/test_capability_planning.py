"""Verify physical-to-programme coupling and conservative missing-data handling.

Engineering values come from the frozen engineering snapshot (data/engineering_snapshot).
"""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from eri.capability_schedule import Activity, schedule, critical_chain
from eri.capability_planning import assess_candidate, load_config, lost_functions, study
from eri.io import load_all
from eri.supply_routes import routes_for, candidate_actors, summarize_routes


class ScheduleTest(unittest.TestCase):
    def test_parallel_work_resource_queue_and_release(self):
        jobs = [Activity('a', (10, 20), resource='test', status='analyst_scenario'),
                Activity('b', (5, 8), resource='test', status='analyst_scenario'),
                Activity('c', (2, 3), release_days=(30, 40), status='analyst_scenario'),
                Activity('done', (1, 2), prerequisites=('b', 'c'), status='analyst_scenario')]
        rows = schedule(jobs, {'test': dict(available_after_days=(5, 10), status='analyst_scenario')})
        self.assertEqual(rows['b']['start_low'], 15)
        self.assertEqual(rows['b']['finish_high'], 38)
        self.assertEqual(rows['done']['finish_low'], 33)
        self.assertEqual(rows['done']['finish_high'], 45)
        self.assertEqual(critical_chain(rows, 'done'), ['c', 'done'])

    def test_unknown_propagates_without_poisoning_independent_branch(self):
        jobs = [Activity('a', (None, None), resource='test'),
                Activity('b', (1, 2), resource='test', status='confirmed', source_id='report'),
                Activity('independent', (3, 4), status='confirmed', source_id='report')]
        rows = schedule(jobs, {'test': dict(available_after_days=(0, 0), status='confirmed', source_id='booking')})
        self.assertIsNone(rows['b']['finish_high'])
        self.assertEqual(rows['independent']['finish_high'], 4)
        self.assertIn('a:duration', rows['b']['unresolved_high'])

    def test_scenario_is_excluded_from_evidence_schedule(self):
        jobs = [Activity('a', (10, 20), status='analyst_scenario')]
        self.assertEqual(schedule(jobs)['a']['finish_high'], 20)
        self.assertIsNone(schedule(jobs, evidence_only=True)['a']['finish_high'])

    def test_invalid_graphs_and_bounds_fail_loudly(self):
        for jobs in ([Activity('a', (0, 1), prerequisites=('b',)), Activity('b', (0, 1), prerequisites=('a',))],
                     [Activity('a', (0, 1), prerequisites=('missing',))],
                     [Activity('a', (2, 1))], [Activity('a', (0, float('inf')))],
                     [Activity('a', (1, 2), status='confirmed')],
                     [Activity('a', (1, 2)), Activity('a', (1, 2))]):
            with self.assertRaises(ValueError):
                schedule(jobs)


class CapabilityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inp = load_all()
        cls.cfg = load_config()
        cls.arch = None   # candidate definitions live in the engineering snapshot
        cls.tables = study(cls.inp, cls.cfg)

    def assess(self, factors=(), cfg=None, **kwargs):
        return assess_candidate(self.inp, self.arch, cfg or self.cfg, 'HLS_SORTIE', 'integrated', factors, **kwargs)

    def test_recovery_crosses_reserve_and_adds_real_work(self):
        base, _, _ = self.assess()
        short, jobs, _ = self.assess(['water_recovery'])
        self.assertGreater(short['extra_water_kg'], 0)
        self.assertGreater(short['extra_vehicle_wet_kg'], 0)
        self.assertTrue(short['resource_redesign_required'])
        self.assertIn('01_restore_resource_margin', jobs)
        self.assertGreater(short['duration_days_low'], base['duration_days_low'])
        cfg = deepcopy(self.cfg)
        cfg['cases']['HLS_SORTIE'].update(extra_water_reserve_kg=1e6, extra_wet_mass_reserve_kg=1e6)
        relaxed, _, _ = self.assess(['water_recovery'], cfg)
        self.assertFalse(relaxed['resource_redesign_required'])
        self.assertEqual(relaxed['duration_days_high'], base['duration_days_high'])

    def test_generic_trl9_does_not_skip_procurement_or_qualification(self):
        _, jobs, _ = self.assess(trl_override={'air': 9, 'water': 9})
        self.assertTrue(any(n.endswith('_procure') for n in jobs))
        self.assertTrue(any(n.endswith('_qualify') for n in jobs))
        unknown, _, _ = self.assess(trl_override={'air': None, 'water': None})
        self.assertIsNone(unknown['duration_days_high'])
        self.assertEqual(unknown['planning_status'], 'unresolved_remaining_work')

    def test_humans_procurement_waits_for_structure_even_with_mature_equipment(self):
        row, jobs, _ = assess_candidate(self.inp, self.arch, self.cfg, 'HUMANS', 'integrated',
                                        trl_override={'air': 9, 'water': 9})
        gate = jobs['01_structure_available']
        self.assertEqual(gate['finish_low'], 365)
        for name, job in jobs.items():
            if name.endswith('_procure') or name == 'support_equipment':
                self.assertIn('01_structure_available', job['prerequisites'])
                self.assertGreaterEqual(job['start_low'], gate['finish_low'])
        self.assertIsNone(row['evidence_available_date'])
        self.assertIsNone(row['need_date'])

    def test_unknown_structure_release_blocks_completion_without_inventing_a_date(self):
        cfg = deepcopy(self.cfg)
        cfg['cases']['HUMANS']['structure']['procurement_not_before'] = None
        row, jobs, _ = assess_candidate(self.inp, self.arch, cfg, 'HUMANS', 'integrated')
        self.assertIsNone(row['available_date_low'])
        self.assertIsNone(row['schedule_margin_days_high'])
        self.assertEqual(jobs['00_design']['finish_low'], 10)
        self.assertIsNone(jobs['support_equipment']['start_low'])

    def test_quarter_margin_reports_both_boundaries(self):
        row, _, _ = assess_candidate(self.inp, self.arch, self.cfg, 'HUMANS', 'integrated')
        self.assertEqual(row['schedule_margin_days_high'], row['margin_to_window_start_days_high'])
        self.assertEqual(row['schedule_margin_days_low'], row['margin_to_window_end_days_low'])
        self.assertEqual(row['margin_to_window_end_days_high'] - row['margin_to_window_start_days_high'], 89)

    def test_full_scope_and_evidence_dates(self):
        frame = self.tables['capabilities']
        self.assertEqual(frame.full_scope_covered.sum(), 4)
        self.assertTrue(frame.evidence_available_date.isna().all())
        open_case = frame[frame.candidate == 'open'].iloc[0]
        self.assertTrue(open_case.minimum_support_covered)
        self.assertFalse(open_case.full_scope_covered)
        self.assertTrue(self.tables['supplier_routes'].delivery_confirmed.eq(False).all())
        self.assertFalse(self.tables['technology_gaps'].absence_proven.any())

    def test_catalogue_is_pseudonymised_and_supplier_roles_are_kept(self):
        actors = self.inp.actors
        self.assertTrue(actors.entity_name.str.match(r'^ORG-[EW]\d{3}$').all())
        self.assertTrue(actors.record_id.str.match(r'^REC-\d{4}$').all())
        adjacent = actors[actors.is_europe & actors.supplier_scope.eq('adjacent_industrial_supplier')]
        self.assertFalse(adjacent.empty)

    def test_cross_function_route_and_similarity_are_distinct(self):
        rows = routes_for(self.inp, 'co2_reduction', 'T-AR-014')
        eu = summarize_routes(rows)
        self.assertEqual(eu['route_status'], 'process_route_evidenced_configuration_unconfirmed')
        self.assertIn('Route provider EU-R', eu['providers'])
        self.assertIsNone(eu['independent_supplier_count'])
        self.assertEqual(eu['confirmed_delivery_routes'], 0)
        reviewed = [r for r in rows if r['evidence_status'] == 'reviewed_process_route' and r['region'] == 'Europe']
        linked = {x for r in reviewed for x in r['catalogue_record_ids'].split(';') if x}
        actors = candidate_actors(self.inp, 'co2_reduction', 'CO2_REDUCTION')
        self.assertTrue(linked and linked <= set(actors.record_id))
        self.assertFalse(actors.supplier_scope.isin(['operator', 'research_institute']).any())
        self.assertFalse(summarize_routes([])['market_absence_established'])

    def test_installed_redundancy_and_shared_hardware_loss(self):
        functions = {'co2_removal': ['unit_a', 'unit_b'], 'o2_generation': 'unit_a', 'co2_reduction': 'reactor'}
        deps = {'co2_reduction': ['co2_removal', 'o2_generation']}
        lost = lost_functions(functions, deps, lost_technologies=['unit_a'])
        self.assertNotIn('co2_removal', lost)
        self.assertEqual(lost, ['co2_reduction', 'o2_generation'])
        self.assertEqual(lost_functions(functions, deps, lost_services=['vent'], services={'vent': ['co2_removal']}),
                         ['co2_reduction', 'co2_removal'])

    def test_factorial_effects_respect_scope(self):
        self.assertEqual(len(self.tables['sensitivity_scenarios']), 128)
        effects = self.tables['driver_effects']
        schedule_effects = effects[effects.metric.eq('duration_days_midpoint')]
        self.assertGreater(schedule_effects.high_minus_low.max(), 0)
        self.assertNotIn('eri_handoff', self.tables)   # exploratory POMDP handoff is not part of this release


if __name__ == '__main__':
    unittest.main()
