"""Engineering capability, supply-route and development-work assessment.

Physical changes come through ``eri.engineering``: the sizing/vehicle models
when they are installed, otherwise the frozen engineering snapshot. Programme
effects follow declared resource margins and explicit work, not a universal
TRL law. Evidence-only dates and conditional scenario dates remain separate
throughout.
"""
from datetime import date, timedelta
from itertools import product
import math

import pandas as pd
import yaml

from eri import engineering
from eri.io import DATA, load_all
from eri.capability_schedule import Activity, critical_chain, schedule
from eri.supply_routes import routes_for, summarize_routes


def deadline_bounds(case):
    """Preserve a quarter target without inventing an exact programme deadline."""
    return tuple(case['need_window']) if case.get('need_window') else (case['need_date'], case['need_date'])


def load_config():
    cfg = yaml.safe_load((DATA / 'capability_planning.yaml').read_text())
    if cfg['schema_version'] != 1:
        raise ValueError('Unsupported capability planning schema')
    for c in cfg['cases'].values():
        begin, end = map(date.fromisoformat, deadline_bounds(c))
        if begin > end or begin <= date.fromisoformat(c['start_date']):
            raise ValueError('Need date must follow scenario start date')
        for key in ('extra_water_reserve_kg', 'extra_wet_mass_reserve_kg'):
            v = c[key]
            if v is not None and (not math.isfinite(v) or v < 0):
                raise ValueError('Invalid resource margin')
        for v in c['scenario_assessed_trl'].values():
            if not isinstance(v, int) or not 1 <= v <= 9:
                raise ValueError('Scenario maturity must be an integer TRL in [1,9]')
    return cfg


def technical(inp, architecture_cfg, cfg, case, candidate, factors=()):
    """Allocated hardware and physical consequences of the recovery stresses.

    Delegates to ``eri.engineering`` (live sizing models or frozen snapshot).
    """
    return engineering.technical(inp, architecture_cfg, cfg, case, candidate, factors)


def lost_functions(functions, dependencies, *, lost_technologies=(), lost_services=(), services=None):
    """Propagate a loss through required functions, allowing installed redundancy.

    A list/tuple allocation denotes installed alternatives for this diagnostic.
    A potential external supplier is never treated as installed redundancy.
    """
    lost = set()
    for function, allocation in functions.items():
        hardware = [allocation] if isinstance(allocation, str) else list(allocation)
        if not hardware or all(t in lost_technologies for t in hardware):
            lost.add(function)
    for service in lost_services:
        lost.update((services or {}).get(service, ()))
    changed = True
    while changed:
        before = set(lost)
        for function in functions:
            if any(p not in functions or p in lost for p in dependencies.get(function, ())):
                lost.add(function)
        changed = before != lost
    return sorted(lost)


def activities_for(cfg, case, functions, factors, extra_water, extra_wet, *, trl_override=None):
    c = cfg['cases'][case]
    tasks = []

    def add(name, profile, parents=(), reason='', duration=None):
        p = c['work_profiles'][profile]
        tasks.append(Activity(name, tuple(p['days'] if duration is None else duration),
                              tuple(p['cost_keur']), tuple(parents), p['resource'],
                              status=p['status'], source_id=p['source_id'], reason=reason))
        return name

    design = add('00_design', 'design', reason='Case requirements and interfaces')
    structure_gate = None
    if c.get('structure'):
        gate = c['structure']
        release = gate['procurement_not_before']
        release_days = ((date.fromisoformat(release) - date.fromisoformat(c['start_date'])).days
                        if release else None)
        structure_gate = '01_structure_available'
        tasks.append(Activity(structure_gate, (0, 0), release_days=(release_days, release_days),
                              status=gate['status'], source_id=gate['source_id'],
                              reason=gate['scope'] + ' Structure cost is outside this work-cost scope.'))
    margin_exceeded = extra_water > c['extra_water_reserve_kg'] + 1e-9
    if c['extra_wet_mass_reserve_kg'] is not None and extra_wet is not None:
        margin_exceeded |= extra_wet > c['extra_wet_mass_reserve_kg'] + 1e-9
    redesign = None
    if margin_exceeded:
        redesign = add('01_restore_resource_margin', 'resource_redesign', (design,),
                       'Additional carried/supplied water exceeds a declared scenario margin; resize/review and reverify')
    service = None
    if 'shared_service' in factors:
        service = add('02_restore_air_service', 'restore_service', (design,),
                      'Common air service interrupts air integration')
    core = {}
    for function, chain in cfg['chain_by_function'].items():
        if function in functions:
            core.setdefault(functions[function], set()).add(chain)
    releases = []
    for tid, chains in sorted(core.items()):
        parents = (redesign or design,) + ((structure_gate,) if structure_gate else ())
        days = list(c['work_profiles']['procure']['days'])
        if 'supplier_delay' in factors and 'air' in chains:
            days = [a + b for a, b in zip(days, cfg['supplier_delay_days'])]
        current = add(tid + '_procure', 'procure', parents,
                      'Unconfirmed selected-unit lead time; scenario only; procurement price excluded', days)
        # A shared multifunction unit is procured and qualified once. Maturity
        # is assessed for this case, never copied from a generic flight TRL.
        levels = []
        for chain in chains:
            level = (trl_override or {}).get(chain, c['scenario_assessed_trl'][chain])
            if chain + '_maturity' in factors:
                level = cfg['assessed_trl_stress'][chain]
            if level is not None and (not isinstance(level, int) or not 1 <= level <= 9):
                raise ValueError('Invalid configuration maturity scenario')
            levels.append(level)
        level = min(levels) if all(x is not None for x in levels) else None
        if level is None:
            tasks.append(Activity(tid + '_assess_maturity', (None, None), prerequisites=(current,),
                                  reason='Configuration-specific remaining work is unknown'))
            current = tid + '_assess_maturity'
        else:
            if level < 5:
                current = add(tid + '_breadboard', 'breadboard', (current,), 'Explicit case breadboard work profile')
            if level < 6:
                current = add(tid + '_relevant_demo', 'relevant_demo', (current,), 'Explicit relevant-environment demonstration profile')
        parents = (current,) + ((service,) if service and 'air' in chains else ())
        current = add(tid + '_adapt', 'adapt', parents, 'Load, interfaces and environment transfer')
        current = add(tid + '_qualify', 'qualification', (current,), 'Selected-configuration verification is not waived by generic TRL9')
        releases.append(current)
    support = add('support_equipment', 'procure', (redesign or design,) + ((structure_gate,) if structure_gate else ()),
                  'Enabling equipment package; individual function supply gaps are retained in the route ledger')
    releases.append(support)
    integration = add('zz_integrated_acceptance', 'integration', tuple(releases),
                      'One shared integrated campaign after all required packages')
    return tasks, integration, margin_exceeded


def calendar_date(start, days):
    return None if days is None else (date.fromisoformat(start) + timedelta(days=math.ceil(days))).isoformat()


def assess_candidate(inp, architecture_cfg, cfg, case, candidate, factors=(), *, cache=None, trl_override=None):
    c = cfg['cases'][case]
    factors = frozenset(factors)
    if factors - set(cfg['factors']):
        raise ValueError('Unknown capability stress')
    cache = {} if cache is None else cache
    key = (case, candidate, tuple(sorted(factors & {'air_recovery', 'water_recovery'})))
    if key not in cache:
        cache[key] = technical(inp, architecture_cfg, cfg, case, candidate, factors)
    base_key = (case, candidate, ())
    if base_key not in cache:
        cache[base_key] = technical(inp, architecture_cfg, cfg, case, candidate)
    values, functions = cache[key]
    base = cache[base_key][0]
    extra_water = values['water_kg'] - base['water_kg']
    extra_wet = values['vehicle_wet_kg'] - base['vehicle_wet_kg'] if values['vehicle_wet_kg'] is not None else None
    missing = sorted(set(c['required_functions']) - functions.keys())
    tasks, milestone, redesign = activities_for(cfg, case, functions, factors, extra_water, extra_wet, trl_override=trl_override)
    timing = schedule(tasks, c['resources'])
    evidence_tasks, _, _ = activities_for(cfg, case, functions, factors, extra_water, extra_wet,
                                               trl_override=c['configuration_assessed_trl'])
    evidence = schedule(evidence_tasks, c['resources'], evidence_only=True)
    need_start, need_end = deadline_bounds(c)
    need_days_start, need_days_end = [(date.fromisoformat(d) - date.fromisoformat(c['start_date'])).days
                                    for d in (need_start, need_end)]
    row = dict(case_id=case, candidate=candidate, required_capability=c['full_capability'],
               full_scope_covered=not missing, minimum_support_covered=('co2_removal' in functions and
               bool({'o2_generation','o2_storage'} & functions.keys()) and bool({'water_processing','water_storage'} & functions.keys())),
               missing_functions=';'.join(missing), factors=';'.join(f for f in cfg['factors'] if f in factors),
               **values, extra_water_kg=extra_water, extra_vehicle_wet_kg=extra_wet,
               resource_redesign_required=redesign, scenario_start_date=c['start_date'], need_date=c['need_date'],
               need_window_start=need_start, need_window_end=need_end,
               need_label=c.get('need_label', c['need_date']), date_status=c['date_status'],
               programme_source=c.get('programme_source', ''),
               structure_target=c.get('structure', {}).get('available_by'),
               structure_status=c.get('structure', {}).get('status', 'not_in_case_scope'),
               evidence_available_date=calendar_date(c['start_date'], evidence[milestone]['finish_high']) if not missing else None,
               evidence_status='documented_work_estimates_only_not_delivery_commitment',
               cost_scope=cfg['cost_scope'], probability_inferred=False, configuration_maturity_status=c['maturity_status'])
    for i, bound in enumerate(('low', 'high')):
        finish = timing[milestone]['finish_' + bound] if not missing else None
        row['duration_days_' + bound] = finish
        row['available_date_' + bound] = calendar_date(c['start_date'], finish)
        # Legacy low/high suffixes follow duration endpoints. With a quarter
        # target they pair short duration with latest deadline, and vice versa.
        need_days = need_days_end if bound == 'low' else need_days_start
        row['schedule_margin_days_' + bound] = None if finish is None else need_days - finish
        row['margin_to_window_start_days_' + bound] = None if finish is None else need_days_start - finish
        row['margin_to_window_end_days_' + bound] = None if finish is None else need_days_end - finish
        costs = [t.cost_keur[i] for t in tasks]
        work_cost = sum(costs) if all(v is not None for v in costs) else None
        row['work_cost_keur_' + bound] = work_cost
        row['incremental_water_cost_keur_' + bound] = max(0, extra_water) * c['water_supply_keur_per_kg'][i]
        row['development_exposure_keur_' + bound] = (work_cost + row['incremental_water_cost_keur_' + bound] +
             c['holding_keur_per_day'] * finish) if work_cost is not None and finish is not None else None
        row['critical_chain_' + bound] = ';'.join(critical_chain(timing, milestone, bound)) if not missing else ''
    lo, hi = row['duration_days_low'], row['duration_days_high']
    if missing:
        status = 'required_function_missing'
    elif lo is None or hi is None:
        status = 'unresolved_remaining_work'
    elif lo > need_days_end:
        status = 'late_even_at_lower_scenario_duration'
    elif hi > need_days_start:
        status = 'scenario_range_crosses_need_window' if need_start != need_end else 'scenario_range_crosses_need_date'
    else:
        status = 'within_dates_under_scenario_assumptions'
    row['planning_status'] = status
    row['unresolved_evidence_items'] = ';'.join(evidence[milestone]['unresolved_high'])
    return row, timing, functions


def sensitivity(frame, factors):
    """Matched factorial effects, separately for every metric and case.

    Comparisons use midpoint scenario bounds solely as a sensitivity statistic;
    they do not treat the midpoint as a forecast or parameter expectation.
    """
    rows = []
    metrics = ['water_kg', 'vehicle_wet_kg', 'duration_days_midpoint', 'development_exposure_keur_midpoint']
    for case, g in frame.groupby('case_id'):
        for metric in metrics:
            if g[metric].isna().all():
                continue
            local = []
            for factor in factors:
                contrast = float(g.loc[g[factor] == 1, metric].mean() - g.loc[g[factor] == 0, metric].mean())
                local.append(dict(case_id=case, metric=metric, factor=factor,
                                  high_minus_low=0.0 if abs(contrast) < 1e-9 else contrast))
            effect = pd.DataFrame(local)
            effect['rank'] = effect.high_minus_low.abs().where(effect.high_minus_low.abs() > 1e-9).rank(ascending=False, method='min')
            rows.extend(effect.to_dict('records'))
    return pd.DataFrame(rows)


def decision_handoff(capabilities, cfg):
    """Bound additional POMDP work by the remaining scenario calendar.

    The conservative duration endpoint sets a conditional correction window.
    Nominal procurement and qualification are already in the engineering DAG;
    planner interventions represent additional corrective work only.
    """
    from eri.belief_planning import Planner, actions_from_config, prior

    belief_cfg = yaml.safe_load((DATA / 'eri_beliefs.yaml').read_text())
    rows = []
    for r in capabilities.to_dict('records'):
        c = cfg['cases'][r['case_id']]
        margin = r['schedule_margin_days_high']
        feasible = r['full_scope_covered'] and pd.notna(margin) and margin >= 0
        days = min(c['maximum_decision_days'], math.floor(margin)) if feasible else 0
        for p in cfg['belief_priors']:
            result = {}
            if feasible:
                actions = actions_from_config(belief_cfg, r['case_id'], .8)
                planner = Planner(actions, c['correction_cash_reserve_keur'], days,
                                  belief_cfg['horizon_actions'])
                result, _ = planner.solve(prior([p] * 4, 0.0))
            rows.append(dict(case_id=r['case_id'], candidate=r['candidate'],
                             conditional_window_feasible=feasible,
                             correction_window_days=days,
                             correction_cash_keur=c['correction_cash_reserve_keur'],
                             prior_each_gate=p, observation_accuracy=.8,
                             dependence_mixture=0.0, belief_status=cfg['belief_status'],
                             nominal_schedule_bound='high',
                             first_action='DEFER_FULL_CAPABILITY' if not feasible else result['first_action'],
                             expected_final_joint_adequacy=result.get('expected_final_joint_adequacy'),
                             operational_release_authorized=False,
                             scope='additional_correction_after_nominal_work; mandatory_acceptance_external'))
    return pd.DataFrame(rows)


def study(inp=None, cfg=None):
    inp, cfg = inp or load_all(), cfg or load_config()
    architectures = engineering.architecture_config() if engineering.source() == 'live' else None
    summaries, routes, gaps, task_rows, losses, grid, cache = [], [], [], [], [], [], {}
    for case, c in cfg['cases'].items():
        for candidate in engineering.candidates(case, architectures):
            row, tasks, functions = assess_candidate(inp, architectures, cfg, case, candidate, cache=cache)
            summaries.append(row)
            task_rows.extend(dict(case_id=case, candidate=candidate, **r) for r in tasks.values())
            for function in sorted(set(c['required_functions']) | functions.keys()):
                tid = functions.get(function, '')
                candidates = routes_for(inp, function, tid) if tid else []
                routes.extend(dict(case_id=case, candidate=candidate, **r) for r in candidates)
                eu, other = summarize_routes(candidates), summarize_routes(candidates, 'Outside Europe')
                gaps.append(dict(case_id=case, candidate=candidate, function=function, technology_id=tid,
                                 essential=function in c['required_functions'],
                                 european_route_status=eu['route_status'], european_providers=eu['providers'],
                                 worldwide_alternative_status=other['route_status'], worldwide_alternative_providers=other['providers'],
                                 confirmed_european_delivery_routes=eu['confirmed_delivery_routes'],
                                 blocker_status=('missing_required_function' if not tid else
                                     'no_european_route_found_in_reviewed_scope' if eu['route_status'] == 'no_route_found_in_reviewed_scope' else
                                     'similarity_adaptation_unresolved' if eu['route_status'] == 'similarity_route_requires_assessment' else
                                     'delivery_or_configuration_evidence_unresolved'),
                                 independent_supplier_count=None, absence_proven=False))
            for item in sorted(set(functions.values())) + sorted(cfg['shared_services']):
                lost = lost_functions(functions, cfg['function_dependencies'],
                                      lost_technologies=[item] if item not in cfg['shared_services'] else [],
                                      lost_services=[item] if item in cfg['shared_services'] else [],
                                      services=cfg['shared_services'])
                affected = sorted(set(lost) & set(c['required_functions']))
                losses.append(dict(case_id=case, candidate=candidate, failed_item=item,
                                   item_type='shared_service' if item in cfg['shared_services'] else 'allocated_hardware',
                                   lost_functions=';'.join(lost), lost_essential_functions=';'.join(affected),
                                   blocks_full_capability=bool(affected),
                                   status='structural_loss_under_declared_dependencies_not_failure_probability'))
        # Controlled factorial study uses one common functional candidate.
        for bits in product((0, 1), repeat=len(cfg['factors'])):
            factors = [f for f, b in zip(cfg['factors'], bits) if b]
            r, _, _ = assess_candidate(inp, architectures, cfg, case, 'integrated', factors, cache=cache)
            r.update(dict(zip(cfg['factors'], bits)))
            r['scenario_id'] = case + '_' + ''.join(map(str, bits))
            for metric in ('duration_days', 'development_exposure_keur'):
                values = [r[metric + '_' + b] for b in ('low','high')]
                r[metric + '_midpoint'] = sum(values) / 2 if all(v is not None for v in values) else None
            grid.append(r)
    frame = pd.DataFrame(grid)
    capabilities = pd.DataFrame(summaries)
    observations = pd.read_csv(DATA / 'evidence/capability_observations.csv')
    tables = dict(capabilities=capabilities, supplier_routes=pd.DataFrame(routes),
                  evidence_observations=observations,
                  technology_gaps=pd.DataFrame(gaps), work_packages=pd.DataFrame(task_rows),
                  dependency_losses=pd.DataFrame(losses), sensitivity_scenarios=frame,
                  driver_effects=sensitivity(frame, cfg['factors']))
    # Optional exploratory POMDP handoff: only when belief priors are declared.
    if cfg.get('belief_priors'):
        tables['eri_handoff'] = decision_handoff(capabilities, cfg)
    return tables
