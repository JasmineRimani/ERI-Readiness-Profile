"""The policy layer may only report what the evidence records; missing inputs stay missing."""
from pathlib import Path
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from eri.capability_planning import study
from eri.policy_layer import (classify_gaps, funding_cycle_exposure, load_calendar, load_evidence_dates,
                              load_instruments, load_rules, load_search_log, load_templates, tag_work)

LOG_COLUMNS = ['search_id', 'search_date', 'search_date_status', 'search_type', 'function', 'capability_key',
               'scope_region', 'scope_sources', 'query', 'result', 'hits', 'record_ids',
               'counts_toward_absence', 'route_scope', 'documented_in', 'note']


def gap(function='co2_removal', technology='T-X', eu='no_route_found_in_reviewed_scope', confirmed=0):
    return pd.DataFrame([dict(case_id='ANALOGS', candidate='integrated', function=function, technology_id=technology,
                              essential=True, european_route_status=eu, confirmed_european_delivery_routes=confirmed,
                              worldwide_alternative_status='no_route_found_in_reviewed_scope')])


def search(function='co2_removal', region='Europe', result='not_found', counts='true'):
    row = dict.fromkeys(LOG_COLUMNS, '')
    row.update(search_id='T-1', function=function, scope_region=region, result=result,
               counts_toward_absence=counts, route_scope='commercial_product', documented_in='test')
    return pd.DataFrame([row])


class InputTest(unittest.TestCase):
    def test_inputs_load_and_validate(self):
        rules = load_rules()
        load_instruments(), load_calendar(), load_search_log(), load_evidence_dates()
        self.assertIsNone(rules['evidence_age']['stale_after_years'])

    def test_template_rows_carry_a_source(self):
        for name, df in load_templates(load_rules()).items():
            source_cols = [c for c in df.columns if c in ('source', 'source_report', 'url', 'legal_basis', 'protocol')]
            self.assertTrue(source_cols, name)
            for _, row in df.iterrows():
                self.assertTrue(any(row[c] for c in source_cols), f'{name}: row without a source')

    def test_stated_dates_have_sources_and_unknown_dates_stay_null(self):
        for e in load_calendar()['events']:
            if e['date_status'] == 'stated_in_source':
                self.assertTrue(e['url'] and e['date_start'])
            else:
                self.assertIsNone(e['date_start'])

    def test_every_search_is_documented(self):
        log = load_search_log()
        self.assertTrue((log.documented_in != '').all())
        self.assertTrue(set(log.result[log.counts_toward_absence == 'true']) <= {'not_found'})


class RuleTest(unittest.TestCase):
    rules, instruments = load_rules(), load_instruments()

    def state(self, gaps, log):
        r = classify_gaps(gaps, log, self.rules, self.instruments)
        return r[r.pool == 'Europe'].iloc[0]

    def test_no_route_without_negative_search_is_unknown_not_shortfall(self):
        row = self.state(gap(), search(result='found', counts='false'))
        self.assertEqual(row.evidence_state, 'unknown')
        self.assertEqual(row.action_class, 'information')

    def test_documented_negative_search_and_no_route_is_a_shortfall(self):
        row = self.state(gap(), search())
        self.assertEqual(row.evidence_state, 'documented_shortfall_in_reviewed_scope')
        self.assertEqual(row.action_class, 'investment')

    def test_negative_search_does_not_override_a_recorded_route(self):
        row = self.state(gap(eu='process_route_evidenced_configuration_unconfirmed'), search())
        self.assertEqual(row.evidence_state, 'unknown')
        self.assertIn('stays unknown', row.state_note)

    def test_search_outside_the_pool_does_not_count(self):
        row = self.state(gap(), search(region='Country A;Country B'))
        self.assertEqual(row.evidence_state, 'unknown')

    def test_confirmed_delivery_is_supported_and_needs_no_action(self):
        row = self.state(gap(eu='process_route_evidenced_configuration_unconfirmed', confirmed=1), search())
        self.assertEqual(row.evidence_state, 'supported_at_stated_scope')
        self.assertEqual(row.action_class, '')

    def test_missing_calendar_date_gives_a_lower_bound(self):
        caps = pd.DataFrame([dict(case_id='ANALOGS', candidate='integrated', scenario_start_date='2027-01-01',
                                  available_date_low='2028-05-13', available_date_high='2029-02-20')])
        cal = {'events': [dict(id='X', applies_to=['ANALOGS'], date_start=None, date_end=None, year=None,
                               date_status='author_input_required')]}
        e = funding_cycle_exposure(caps, cal).iloc[0]
        self.assertEqual(e.exposure_status, 'lower_bound_only')
        self.assertEqual(e.decisions_in_window_high, 0)

    def test_dated_decision_inside_the_path_is_counted(self):
        caps = pd.DataFrame([dict(case_id='ANALOGS', candidate='integrated', scenario_start_date='2027-01-01',
                                  available_date_low='2028-05-13', available_date_high='2029-02-20')])
        cal = {'events': [dict(id='D', applies_to=['ANALOGS'], date_start='2028-11-01', date_end='2028-11-02',
                               year=2028, date_status='stated_in_source')]}
        e = funding_cycle_exposure(caps, cal).iloc[0]
        self.assertEqual((e.decisions_in_window_low, e.decisions_in_window_high), (0, 1))
        self.assertEqual(e.exposure_status, 'computed')


class CurrentProfileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables = study()

    def test_analogs_requirements_are_unknown_and_call_for_information(self):
        r = classify_gaps(self.tables['technology_gaps'], load_search_log(), load_rules(), load_instruments())
        analogs = r[(r.case_id == 'ANALOGS') & (r.pool == 'Europe') & (r.essential.astype(str) == 'True')]
        self.assertEqual(set(analogs.evidence_state), {'unknown'})
        self.assertEqual(set(analogs.action_class), {'information'})

    def test_every_work_package_has_a_class_and_the_structure_is_infrastructure(self):
        w = tag_work(self.tables['work_packages'], load_rules())
        self.assertTrue((w.action_class != '').all())
        gate = w[w.activity == '01_structure_available']
        self.assertEqual(set(gate.action_class), {'infrastructure'})

    def test_funding_exposure_is_never_reported_as_zero_when_dates_are_missing(self):
        e = funding_cycle_exposure(self.tables['capabilities'], load_calendar())
        paths = e[e.exposure_status != 'no_implementation_path']
        self.assertEqual(set(paths.exposure_status), {'lower_bound_only'})


if __name__ == '__main__':
    unittest.main()
