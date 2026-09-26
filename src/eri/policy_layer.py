"""Policy layer: the readiness profile read as programme and funding decisions.

It adds what the profile cannot show on its own:

* an evidence state per requirement that can be a documented shortfall, which
  needs a recorded search that found nothing (evidence/search_log.csv);
* the action class (information, investment, infrastructure), owner and
  instruments for every unresolved requirement and every work package
  (instrument_register.yaml, policy_layer.yaml);
* funding-cycle exposure: the dated decision points inside each implementation
  path (decision_calendar.yaml), reported as a lower bound when dates are
  missing;
* the age of the evidence behind each capability (evidence/evidence_dates.csv);
* a list of the inputs that do not exist yet.

Nothing is estimated here. No number is written in Python: rules and thresholds
live in data/policy_layer.yaml. A missing input stays missing and is reported.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pandas as pd
import yaml

from eri.io import DATA

RESULTS = {'found', 'not_found', 'partial', 'inaccessible', 'ambiguous', 'contradicted', 'not_completed'}
SEARCH_COLUMNS = ['search_id', 'search_date', 'search_date_status', 'search_type', 'function', 'capability_key',
                  'scope_region', 'scope_sources', 'query', 'result', 'hits', 'record_ids',
                  'counts_toward_absence', 'route_scope', 'documented_in', 'note']
DATE_STATUSES = {'stated_in_source', 'year_only_in_source', 'not_announced_in_reviewed_sources',
                 'author_input_required'}
STATES = ('supported_at_stated_scope', 'documented_shortfall_in_reviewed_scope', 'unknown')


def _yaml(name):
    return yaml.safe_load((DATA / name).read_text())


# ------------------------------------------------------------------ loaders with validation
def load_rules():
    rules = _yaml('policy_layer.yaml')
    if rules['schema_version'] != 1:
        raise ValueError('Unsupported policy_layer.yaml schema')
    if set(rules['evidence_state_to_action']) - {'status'} != set(STATES):
        raise ValueError('Every evidence state needs an action mapping')
    return rules


def load_instruments():
    reg = _yaml('instrument_register.yaml')
    classes = set(reg['classes'])
    for ins in reg['instruments']:
        if ins['class'] not in classes:
            raise ValueError(f"Unknown action class for {ins['id']}")
        if ins['minimum_days'] is not None and ins['minimum_days_status'].split(' ')[0] != 'stated_in_source':
            raise ValueError(f"{ins['id']}: a minimum time needs a source that states it")
        if ins['basis'] is None and ins['basis_status'] != 'definitional':
            raise ValueError(f"{ins['id']}: an instrument without a basis must be declared definitional")
    return reg


def load_calendar():
    cal = _yaml('decision_calendar.yaml')
    for e in cal['events']:
        if e['date_status'] not in DATE_STATUSES:
            raise ValueError(f"{e['id']}: unknown date_status")
        if e['date_status'] == 'stated_in_source' and not (e['date_start'] and e['url']):
            raise ValueError(f"{e['id']}: a stated date needs the date and its source URL")
        if e['date_status'] != 'stated_in_source' and e['date_start']:
            raise ValueError(f"{e['id']}: only a stated date may carry a day")
    return cal


def load_search_log():
    log = pd.read_csv(DATA / 'evidence/search_log.csv', dtype=str, keep_default_na=False)
    if missing := set(SEARCH_COLUMNS) - set(log.columns):
        raise ValueError(f'search_log.csv misses columns {sorted(missing)}')
    if log.search_id.duplicated().any():
        raise ValueError('Duplicate search_id')
    if bad := set(log.result) - RESULTS:
        raise ValueError(f'Unknown search results {sorted(bad)}')
    if (log.documented_in == '').any():
        raise ValueError('Every search needs the document that records it')
    if not set(log.counts_toward_absence) <= {'true', 'false'}:
        raise ValueError('counts_toward_absence must be true or false')
    if ((log.counts_toward_absence == 'true') & (log.result != 'not_found')).any():
        raise ValueError('Only a search that found nothing can support an absence claim')
    return log


def load_evidence_dates():
    d = pd.read_csv(DATA / 'evidence/evidence_dates.csv', dtype=str, keep_default_na=False)
    if d.duplicated(['record_table', 'record_id']).any():
        raise ValueError('Duplicate evidence-date record')
    if ((d.evidence_year != '') & (d.evidence_date_basis == 'not_recorded')).any():
        raise ValueError('A year needs its basis')
    return d


def load_templates(rules):
    """Declared input tables that may still be empty; returns name -> DataFrame."""
    out = {}
    for name, meta in rules['templates'].items():
        out[name] = pd.read_csv(DATA / meta['file'], dtype=str, keep_default_na=False)
    return out


# ------------------------------------------------------------------ requirement evidence state and action
def _covers(scope, regions):
    return any(r in scope.split(';') for r in regions)


def classify_gaps(gaps, log, rules, instruments):
    """Evidence state, action class, owner and instruments per requirement and pool."""
    rule = rules['shortfall_rule']
    to_action = rules['evidence_state_to_action']
    rows = []
    for g in gaps.itertuples():
        for pool, status, confirmed in (('Europe', g.european_route_status, g.confirmed_european_delivery_routes),
                                        ('Outside Europe', g.worldwide_alternative_status, 0)):
            regions = rule['pool_regions'][pool]
            same = log[(log.function == g.function) & log.scope_region.apply(lambda s: _covers(s, regions))]
            absence = same[(same.result == 'not_found') & (same.counts_toward_absence == 'true')]
            other = log[(log.function == g.function) & (log.result == 'not_found') & (log.counts_toward_absence == 'false')]
            if not g.technology_id:
                # The architecture does not provide this function (e.g. the open reference): an
                # architecture-scope gap, not a supply question, so no programme action is attached.
                state = 'function_not_in_architecture'
            elif confirmed and int(confirmed) > 0:
                state = 'supported_at_stated_scope'
            elif status == 'no_route_found_in_reviewed_scope' and len(absence) >= rule['min_absence_searches']:
                state = 'documented_shortfall_in_reviewed_scope'
            else:
                state = 'unknown'
            action = to_action.get(state)
            why = ''
            if state == 'unknown' and len(absence):
                scopes = sorted(set(absence.route_scope))
                why = (f"negative search recorded for route scope {', '.join(scopes)}; "
                       f"other routes are recorded, so the requirement stays unknown")
            elif state == 'function_not_in_architecture':
                why = 'the candidate architecture does not provide this function'
            elif state == 'unknown' and status == 'no_route_found_in_reviewed_scope':
                why = 'no route in the reviewed scope and no qualifying negative search: a search gap, not an absence'
            rows.append(dict(case_id=g.case_id, candidate=g.candidate, function=g.function,
                             technology_id=g.technology_id, essential=g.essential, pool=pool,
                             route_status=status, evidence_state=state, action_class=action or '',
                             owner=instruments['classes'][action]['owner'] if action else '',
                             instruments=';'.join(i['id'] for i in instruments['instruments'] if i['class'] == action),
                             absence_searches=';'.join(absence.search_id), other_negative_searches=';'.join(other.search_id),
                             state_note=why))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ work packages
def tag_work(work, rules):
    mapping = [(re.compile(r['pattern']), r['class'], r['reason']) for r in rules['work_action_class']['rules']]
    rows = []
    for w in work.itertuples():
        hit = next(((c, why) for rx, c, why in mapping if rx.search(w.activity)), None)
        if hit is None:
            raise ValueError(f'No action class for work package {w.activity}; add a rule in policy_layer.yaml')
        resource = w.resource if isinstance(w.resource, str) else ''
        dependency = 'structure gate' if w.activity == '01_structure_available' else resource
        rows.append(dict(case_id=w.case_id, candidate=w.candidate, activity=w.activity, action_class=hit[0],
                         reason=hit[1], infrastructure_dependency=dependency if (
                             rules['work_action_class']['shared_resource_is_infrastructure_dependency'] or
                             w.activity == '01_structure_available') else '',
                         estimate_status=w.estimate_status))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ funding-cycle exposure
def _event_window(e):
    if e['date_start']:
        return date.fromisoformat(e['date_start']), date.fromisoformat(e['date_end'] or e['date_start'])
    if e['year']:
        return date(e['year'], 1, 1), date(e['year'], 12, 31)
    return None


def funding_cycle_exposure(capabilities, calendar):
    """Dated decisions inside each path; a lower bound when an applicable date is missing."""
    rows = []
    for c in capabilities.itertuples():
        start = date.fromisoformat(c.scenario_start_date)
        ends = {b: getattr(c, 'available_date_' + b) for b in ('low', 'high')}
        if any(not isinstance(v, str) for v in ends.values()):
            rows.append(dict(case_id=c.case_id, candidate=c.candidate, window_start=c.scenario_start_date,
                             window_end_low='', window_end_high='', decisions_in_window_low='',
                             decisions_in_window_high='', dated_event_ids='', unresolved_event_ids='',
                             exposure_status='no_implementation_path'))
            continue
        end = {b: date.fromisoformat(v) for b, v in ends.items()}
        inside = {'low': [], 'high': []}
        unresolved = []
        for e in calendar['events']:
            if c.case_id not in e['applies_to']:
                continue
            w = _event_window(e)
            if w is None:
                unresolved.append(e['id'])
                continue
            exact = e['date_status'] == 'stated_in_source'
            for b in ('low', 'high'):
                overlaps = w[0] <= end[b] and w[1] >= start
                if overlaps and exact:
                    inside[b].append(e['id'])
                elif overlaps:
                    unresolved.append(e['id'])
        rows.append(dict(case_id=c.case_id, candidate=c.candidate, window_start=c.scenario_start_date,
                         window_end_low=ends['low'], window_end_high=ends['high'],
                         decisions_in_window_low=len(inside['low']), decisions_in_window_high=len(inside['high']),
                         dated_event_ids=';'.join(dict.fromkeys(inside['low'] + inside['high'])),
                         unresolved_event_ids=';'.join(dict.fromkeys(unresolved)),
                         exposure_status='lower_bound_only' if unresolved else 'computed'))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ evidence age
def evidence_age(dates, actors, planning, rules):
    """Evidence years per capability key, reported against each case need year."""
    need = {k: int(str(v.get('need_window', [v.get('need_date')])[-1])[:4]) for k, v in planning['cases'].items()}
    a = actors[['record_id', 'capability_key', 'is_europe']].merge(
        dates[dates.record_table == 'ecosystem_actors'], on='record_id', how='left')
    a['year'] = pd.to_numeric(a.evidence_year, errors='coerce')
    rows = []
    stale = rules['evidence_age']['stale_after_years']
    for (key, europe), g in a.groupby(['capability_key', 'is_europe']):
        row = dict(capability_key=key, pool='Europe' if europe else 'Outside Europe', records=len(g),
                   records_with_evidence_year=int(g.year.notna().sum()),
                   newest_evidence_year=int(g.year.max()) if g.year.notna().any() else '',
                   median_evidence_year=float(g.year.median()) if g.year.notna().any() else '',
                   records_last_checked=int((g.last_checked.fillna('') != '').sum()))
        for case, year in need.items():
            row[f'median_age_at_need_{case}'] = year - row['median_evidence_year'] if row['median_evidence_year'] != '' else ''
        row['stale_records'] = int((g.year < min(need.values()) - stale).sum()) if stale is not None else 'no threshold set'
        rows.append(row)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ coverage and missing inputs
def search_coverage(log):
    t = log.assign(function=log.function.replace('', '(no single function)'))
    table = pd.crosstab([t.function, t.search_type], t.result).reset_index()
    latest = t[t.search_date != ''].groupby(['function', 'search_type']).search_date.max().rename('latest_search_date')
    return table.merge(latest.reset_index(), on=['function', 'search_type'], how='left').fillna({'latest_search_date': ''})


def missing_inputs(rules, templates, calendar, instruments, dates, log):
    rows = []
    for name, df in templates.items():
        meta = rules['templates'][name]
        rows.append(dict(input=meta['file'], kind='table', status='empty' if df.empty else f'{len(df)} rows',
                         what_it_would_answer=meta['holds'], where_to_get_it=meta['intended_sources']))
    for e in calendar['events']:
        if e['date_status'] in {'author_input_required', 'not_announced_in_reviewed_sources'}:
            rows.append(dict(input=f"decision_calendar.yaml: {e['id']}", kind='date', status=e['date_status'],
                             what_it_would_answer='Funding-cycle exposure of the paths it applies to: ' + ', '.join(e['applies_to']),
                             where_to_get_it=e['source']))
    for i in instruments['instruments']:
        if i['minimum_days'] is None and i['minimum_days_status'] == 'not_extracted':
            rows.append(dict(input=f"instrument_register.yaml: {i['id']}", kind='time limit', status='not_extracted',
                             what_it_would_answer='Minimum lead time of the instrument', where_to_get_it=i['basis'] or ''))
    undated = dates[dates.evidence_year == '']
    rows.append(dict(input='evidence/evidence_dates.csv', kind='dates', status=f'{len(undated)} of {len(dates)} records without an evidence year',
                     what_it_would_answer='Whether the evidence still holds at the need date',
                     where_to_get_it='The source of each record'))
    unsearched = log[log.result.isin(['not_completed', 'inaccessible'])]
    rows.append(dict(input='evidence/search_log.csv', kind='searches', status=f'{len(unsearched)} searches not completed or inaccessible',
                     what_it_would_answer='Whether the capability is documented at all', where_to_get_it='Re-run those searches'))
    if rules['evidence_age']['stale_after_years'] is None:
        rows.append(dict(input='policy_layer.yaml: evidence_age.stale_after_years', kind='threshold',
                         status='author_decision_pending', what_it_would_answer='Which evidence is too old to rely on',
                         where_to_get_it='Author decision'))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ export
def export(out='outputs/policy_layer'):
    from eri.capability_planning import load_config, study
    from eri.io import load_all
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    inp = load_all()
    tables = study(inp)
    rules, instruments, calendar = load_rules(), load_instruments(), load_calendar()
    log, dates = load_search_log(), load_evidence_dates()
    templates = load_templates(rules)
    req = classify_gaps(tables['technology_gaps'], log, rules, instruments)
    work = tag_work(tables['work_packages'], rules)
    exposure = funding_cycle_exposure(tables['capabilities'], calendar)
    age = evidence_age(dates, inp.actors, load_config(), rules)
    coverage = search_coverage(log)
    missing = missing_inputs(rules, templates, calendar, instruments, dates, log)
    for name, df in (('requirement_actions', req), ('work_actions', work), ('funding_cycle_exposure', exposure),
                     ('evidence_age_by_capability', age), ('search_coverage', coverage), ('missing_inputs', missing)):
        df.to_csv(out / f'{name}.csv', index=False)
    (out / 'README.md').write_text(summary(req, work, exposure, missing, log))
    return dict(requirement_actions=req, work_actions=work, funding_cycle_exposure=exposure,
                evidence_age=age, search_coverage=coverage, missing_inputs=missing)


def summary(req, work, exposure, missing, log):
    ess = req[req.essential.astype(str) == 'True']
    lines = ['# Policy layer', '',
             'Generated by `python scripts/run_policy_layer.py`. Rules: `data/policy_layer.yaml`. Nothing here is estimated;',
             'missing inputs are listed at the end.', '',
             '## Essential requirements by evidence state and action class', '',
             '| Case / candidate | Pool | Unknown (information) | Documented shortfall (investment) | Supported | Not in architecture |',
             '|---|---|---:|---:|---:|---:|']
    for (case, cand, pool), g in ess.groupby(['case_id', 'candidate', 'pool']):
        n = g.evidence_state.value_counts()
        lines.append(f"| {case} / {cand} | {pool} | {n.get('unknown', 0)} | "
                     f"{n.get('documented_shortfall_in_reviewed_scope', 0)} | {n.get('supported_at_stated_scope', 0)} | "
                     f"{n.get('function_not_in_architecture', 0)} |")
    qualifying = log[log.counts_toward_absence == 'true']
    lines += ['', f'Searches in the log: {len(log)}; searches that can support an absence claim: {len(qualifying)} '
              f"({', '.join(qualifying.search_id) or 'none'}).", '',
              '## Work packages by action class', '',
              '| Case / candidate | Investment | Information | Infrastructure | With an infrastructure dependency |',
              '|---|---:|---:|---:|---:|']
    for (case, cand), g in work.groupby(['case_id', 'candidate']):
        n = g.action_class.value_counts()
        lines.append(f"| {case} / {cand} | {n.get('investment', 0)} | {n.get('information', 0)} | "
                     f"{n.get('infrastructure', 0)} | {int((g.infrastructure_dependency != '').sum())} |")
    lines += ['', '## Funding-cycle exposure', '', '| Case / candidate | Dated decisions in path (short / long) | Status | Unresolved |',
              '|---|---|---|---|']
    for e in exposure.itertuples():
        lines.append(f'| {e.case_id} / {e.candidate} | {e.decisions_in_window_low} / {e.decisions_in_window_high} | '
                     f'{e.exposure_status} | {e.unresolved_event_ids} |')
    lines += ['', '## Missing inputs', '', '| Input | Status | What it would answer |', '|---|---|---|']
    for m in missing.itertuples():
        lines.append(f'| {m.input} | {m.status} | {m.what_it_would_answer} |')
    return '\n'.join(lines) + '\n'
