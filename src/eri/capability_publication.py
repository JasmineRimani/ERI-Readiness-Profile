"""Publish engineering capability results before interpreting readiness beliefs."""
from html import escape
from pathlib import Path

from eri import engineering
from eri.capability_planning import load_config, study
from eri.io import DATA
from eri.provenance import code_hashes, input_hashes, output_hashes, write_manifest


def figures(out, tables):
    """Keep rendering independent of plotting styles set by other exporters."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    with plt.style.context('default'):
        _figures(out, tables)


def _figures(out, tables):
    import matplotlib.pyplot as plt
    import numpy as np
    from datetime import date
    from eri.figure_style import (CASES, SHORT, CASE_COLOUR, CANDIDATE, BLUES, SERIES, STATUS, INK, INK2, MUTED, GRID,
                                  NEUTRAL, SURFACE, TECH, FUNCTION, tint, apply_style, grid, finish)
    apply_style()
    dpi = 220
    caps = tables['capabilities'].copy()
    caps['need_days'] = [(date.fromisoformat(n) - date.fromisoformat(s)).days for n, s in zip(caps.need_window_end, caps.scenario_start_date)]
    caps['need_start_days'] = [(date.fromisoformat(n) - date.fromisoformat(s)).days for n, s in zip(caps.need_window_start, caps.scenario_start_date)]
    panels = [('HLS_SORTIE', 'open'), ('HLS_SORTIE', 'integrated'), ('HLS_SORTIE', 'distributed'), ('ANALOGS', 'integrated'), ('ANALOGS', 'distributed')]

    # 01 Nominal work schedule per candidate: two duration endpoints, stage colour, shared resources, need date.
    stage_colour = {'design': BLUES[2], 'procure': BLUES[4], 'breadboard': BLUES[6], 'relevant_demo': BLUES[7], 'adapt': BLUES[9],
                    'qualify': BLUES[11], 'support': MUTED, 'acceptance': BLUES[12], 'structure': STATUS['critical']}
    stage_name = {'design': 'Design and interfaces', 'procure': 'Procure', 'breadboard': 'Breadboard', 'relevant_demo': 'Relevant-environment demo',
                  'adapt': 'Adapt to case', 'qualify': 'Qualify configuration', 'support': 'Enabling equipment package', 'acceptance': 'Integrated acceptance', 'structure': 'Structure availability target'}

    def stage_of(activity):
        if activity == '00_design': return 'design', 'Design and interfaces'
        if activity == '01_structure_available': return 'structure', 'Structure available: end 2027 target'
        if activity == 'support_equipment': return 'support', 'Enabling equipment package'
        if activity == 'zz_integrated_acceptance': return 'acceptance', 'Integrated acceptance campaign'
        tid, stage = activity.split('_', 1)
        return stage, f'{TECH.get(tid, tid)} · {stage_name[stage].lower()}'

    work = tables['work_packages']
    fig, axes = plt.subplots(2, 3, figsize=(16, 10.5))
    axes = axes.ravel()
    xmax = float(work.finish_high.max()) * 1.03
    for ax, (case, cand) in zip(axes, panels):
        g = work[(work.case_id == case) & (work.candidate == cand)].sort_values(['start_low', 'activity']).reset_index(drop=True)
        cap = caps[(caps.case_id == case) & (caps.candidate == cand)].iloc[0]
        for i, r in g.iterrows():
            stage, label = stage_of(r.activity)
            c = stage_colour[stage]
            ax.barh(i - .19, r.finish_low - r.start_low, left=r.start_low, height=.34, color=c, zorder=3)
            ax.barh(i + .19, r.finish_high - r.start_high, left=r.start_high, height=.34, color=tint(c, .55), zorder=3)
            if stage == 'structure':
                ax.scatter(r.start_low, i, marker='D', color=c, s=24, zorder=4)
            if isinstance(r.resource, str) and r.resource:
                ax.plot([r.start_low, r.start_high], [i - .19, i + .19], marker='|', ms=8, mew=1.4, ls='', color=INK, zorder=4)
            g.loc[i, 'label'] = label
        ax.axvline(cap.need_days, color=STATUS['critical'], lw=1.2, zorder=2)
        ax.axvspan(cap.need_start_days, cap.need_days, color=STATUS['critical'], alpha=.1)
        ax.text(cap.need_days + 8, -0.9, 'Q1 target' if case == 'ANALOGS' else 'scenario deadline', color=STATUS['critical'], fontsize=8, va='center')
        ax.set_yticks(range(len(g)), g.label, fontsize=7.8); ax.set_ylim(len(g) - .4, -1.3)
        ax.set_xlim(0, xmax)
        if cap.full_scope_covered:
            title = (f'{SHORT[case]} · {CANDIDATE[cand]}\ncompletion {cap.duration_days_low:g}–{cap.duration_days_high:g} days from start; '
                     f'margin {cap.schedule_margin_days_high:+.0f} to {cap.schedule_margin_days_low:+.0f} days')
        else:
            title = f'{SHORT[case]} · {CANDIDATE[cand]}\nminimum support only; regenerative functions missing'
        ax.set_title(title, loc='left', fontsize=9)
        grid(ax, 'x')
        ax.set_xlabel('Days after the declared scenario start')
    axes[-1].set_axis_off()
    handles = [plt.Rectangle((0, 0), 1, 1, color=stage_colour[s]) for s in stage_colour] + \
              [plt.Rectangle((0, 0), 1, 1, color=tint(INK2, .55)), plt.Line2D([], [], marker='|', ms=9, mew=1.4, ls='', color=INK),
               plt.Line2D([], [], color=STATUS['critical'], lw=1.2)]
    labels = [stage_name[s] for s in stage_colour] + ['lighter bar: high-duration endpoint (upper bar of each pair)',
                                                       'activity needs a single-slot shared resource (bench or test facility)', 'scenario need date']
    axes[-1].legend(handles, labels, loc='center left', fontsize=8.5, title='Work stages (ordered)', title_fontsize=9)
    fig.suptitle('Nominal capability work per candidate against the scenario need date; confirmed delivery dates remain unknown', y=.995, fontsize=12.5)
    fig.tight_layout(rect=(0, .06, 1, .97))
    finish(fig, out / '01_nominal_work_schedule.png', dpi=dpi, note=(
        'Dark lower bar: low-duration endpoint; light upper bar: high-duration endpoint; one slot per shared resource.\n'
        'ANALOGS structure/end-2027 and Q1-2029 target: author inputs. Durations are analyst scenarios; feasible, not optimal.'))

    # 02 Driver contrasts: fixed factor order, both cases, three consequences.
    effects = tables['driver_effects']
    metrics = [('water_kg', 'Δ carried water [kg]'), ('duration_days_midpoint', 'Δ duration, interval midpoint [days]'),
               ('development_exposure_keur_midpoint', 'Δ development exposure, midpoint [kEUR]')]
    factors = list(dict.fromkeys(effects.factor))
    names = {'air_recovery': 'Air recovery shortfall', 'water_recovery': 'Water recovery shortfall', 'air_maturity': 'Air chain less mature',
             'water_maturity': 'Water chain less mature', 'supplier_delay': 'Supplier delay', 'shared_service': 'Shared-service interruption'}
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    for ax, (metric, label) in zip(axes, metrics):
        top = 1e-9
        for k, case in enumerate(CASES):
            g = effects[(effects.case_id == case) & (effects.metric == metric)].set_index('factor').reindex(factors)
            ys = np.arange(len(factors)) + (-.19 if k == 0 else .19)
            vals = g.high_minus_low.fillna(0).to_numpy()
            top = max(top, vals.max())
            ax.barh(ys, vals, height=.34, color=CASE_COLOUR[case], zorder=3, label=SHORT[case])
            for y, v in zip(ys, vals):
                ax.text(v + top * .01, y, ('0' if not v else f'{v:.2f}' if v < 1 else f'{v:.0f}'), va='center', ha='left', fontsize=7.8, color=INK if v else MUTED)
        ax.set_xlim(0, top * 1.35)
        ax.set_yticks(range(len(factors)), [names.get(f, f) for f in factors]); ax.invert_yaxis()
        ax.set_xlabel(label); grid(ax, 'x')
    axes[0].legend(loc='lower right')
    fig.suptitle('Which technical or supply stress moves which consequence? Mean high-minus-low contrasts over 64 matched scenarios per case', y=.99, fontsize=12.5)
    fig.tight_layout(rect=(0, .1, 1, .95))
    finish(fig, out / '02_driver_comparison.png', dpi=dpi, note=(
        'Contrasts over the declared factorial grid; duration and exposure use interval midpoints. Zero can mean slack or an unchanged work stage.\n'
        'Amplitudes, reserves, costs and durations are assumptions; exposure excludes procurement prices.'))

    # 03 Development exposure versus schedule margin: every scenario, both duration endpoints.
    sens = tables['sensitivity_scenarios']
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.4))
    for ax, case in zip(axes, CASES):
        g = sens[sens.case_id == case]
        colour = CASE_COLOUR[case]
        for endpoint, marker in (('low', 'o'), ('high', '^')):
            x, y = g[f'development_exposure_keur_{endpoint}'], g[f'schedule_margin_days_{endpoint}']
            on = g.air_maturity == 1
            ax.scatter(x[~on], y[~on], marker=marker, s=30, facecolor=tint(MUTED, .3), edgecolor=SURFACE, lw=.6, zorder=3)
            ax.scatter(x[on], y[on], marker=marker, s=30, facecolor=colour, edgecolor=SURFACE, lw=.6, zorder=4)
        ref = g[g.factors.isna() | (g.factors == '')].iloc[0]
        for endpoint, dy in (('low', 10), ('high', -14)):
            x, y = ref[f'development_exposure_keur_{endpoint}'], ref[f'schedule_margin_days_{endpoint}']
            ax.scatter([x], [y], s=120, facecolor='none', edgecolor=INK, lw=1.3, zorder=5)
            ax.annotate(f'no stress, {endpoint} endpoint: {y:+.0f} d', xy=(x, y), xytext=(10, dy), textcoords='offset points', fontsize=8, color=INK)
        ax.axhline(0, color=STATUS['critical'], lw=1.1, zorder=2)
        ax.text(.01, 0, ' need date', transform=ax.get_yaxis_transform(), ha='left', va='bottom', fontsize=8, color=STATUS['critical'])
        ax.set_xlabel('Development exposure: work, incremental water and holding [kEUR]')
        ax.set_ylabel('Schedule margin to the need date [days]')
        ax.set_title(f'{SHORT[case]} · {CANDIDATE["integrated"].lower()} candidate, 64 stress combinations × 2 endpoints', loc='left')
        grid(ax, 'both')
    handles = [plt.Line2D([], [], marker='o', ls='', color=INK2, ms=6), plt.Line2D([], [], marker='^', ls='', color=INK2, ms=6),
               plt.Rectangle((0, 0), 1, 1, color=INK2), plt.Rectangle((0, 0), 1, 1, color=tint(MUTED, .3)),
               plt.Line2D([], [], marker='o', ls='', mfc='none', mec=INK, ms=9)]
    axes[0].legend(handles, ['low-duration endpoint', 'high-duration endpoint', 'air chain less mature (stress on)', 'air chain at scenario maturity',
                             'no-stress reference'], loc='lower left')
    fig.suptitle('Where the scenarios land in the cost–schedule plane', y=.99, fontsize=12.5)
    fig.tight_layout(rect=(0, .09, 1, .95))
    finish(fig, out / '03_scenario_outcomes.png', dpi=dpi, note=(
        'Each point is one declared stress combination at one duration endpoint; there is no probability over points.\n'
        'Exposure excludes procurement prices; need dates are analyst scenarios, not approved baselines.'))

    # 04 European supply-route status per required function and candidate.
    gaps = tables['technology_gaps']
    level = {'process_route_evidenced_configuration_unconfirmed': (BLUES[9], 'Process heritage,\nconfiguration unconfirmed', 'white'),
             'similarity_route_requires_assessment': (BLUES[6], 'Similar process,\nassessment required', 'white'),
             'research_or_catalogue_leads_only': (BLUES[2], 'Research or\ncatalogue leads only', INK),
             'no_route_found_in_reviewed_scope': (NEUTRAL, 'No route found\nin reviewed scope', INK2)}
    order = ['co2_removal', 'o2_generation', 'co2_reduction', 'water_processing', 'water_polishing', 'humidity_control', 'tccs',
             'monitoring_atmosphere', 'monitoring_trace_gas', 'water_disinfection', 'o2_storage', 'water_storage']
    functions = [f for f in order if f in set(gaps.function)] + sorted(set(gaps.function) - set(order))
    essential = gaps.groupby('function').essential.any()
    fig, ax = plt.subplots(figsize=(12.5, 7.4))
    for j, (case, cand) in enumerate(panels):
        g = gaps[(gaps.case_id == case) & (gaps.candidate == cand)].set_index('function')
        for i, f in enumerate(functions):
            if f not in g.index:
                ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, facecolor=SURFACE, edgecolor=GRID, lw=1))
                ax.text(j, i, 'not in\nallocation', ha='center', va='center', fontsize=7.5, color=MUTED); continue
            r = g.loc[f]
            if r.blocker_status == 'missing_required_function':
                ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, facecolor=tint(STATUS['critical'], .72), edgecolor=SURFACE, lw=2))
                ax.text(j, i, 'required function\nnot allocated', ha='center', va='center', fontsize=7.5, color=INK); continue
            colour, text, ink = level[r.european_route_status]
            ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, facecolor=colour, edgecolor=SURFACE, lw=2))
            ax.text(j, i, text, ha='center', va='center', fontsize=7.5, color=ink)
            if r.worldwide_alternative_status in ('process_route_evidenced_configuration_unconfirmed', 'similarity_route_requires_assessment'):
                ax.plot([j + .38], [i - .36], marker='o', ms=5, color=INK, mec=SURFACE, mew=.8, zorder=5)
    ax.set_xlim(-.5, len(panels) - .5); ax.set_ylim(len(functions) - .5, -.5)
    ax.set_xticks(range(len(panels)), [f'{SHORT[c]}\n{CANDIDATE[k]}' for c, k in panels]); ax.xaxis.tick_top()
    ax.set_yticks(range(len(functions)), [FUNCTION.get(f, f) + (' *' if essential.get(f, False) else '') for f in functions])
    ax.tick_params(length=0)
    for s in ('left', 'bottom'):
        ax.spines[s].set_visible(False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=level[k][0]) for k in level] + [plt.Rectangle((0, 0), 1, 1, color=tint(STATUS['critical'], .72)),
               plt.Line2D([], [], marker='o', ls='', color=INK, ms=5)]
    labels = [level[k][1].replace('\n', ' ') for k in level] + ['required function not allocated', 'a non-European route is also evidenced or similar']
    ax.legend(handles, labels, loc='upper center', bbox_to_anchor=(.5, -.02), ncol=3, fontsize=8.2)
    ax.set_title('European supply-route status for each required function and candidate (* essential function)', loc='left', pad=30)
    fig.tight_layout(rect=(0, .09, 1, 1))
    finish(fig, out / '04_supply_routes.png', dpi=dpi, note=(
        'Strongest reviewed European evidence per process family; no route confirms selected-configuration delivery.\n'
        '“No route found” is an evidence gap, not proof of market absence. Supplier records are leads; independence is not established.'))

    # 05 Single-point items whose loss blocks full capability.
    losses = tables['dependency_losses']
    blocking = losses[losses.blocks_full_capability].copy()
    blocking['n'] = blocking.lost_essential_functions.fillna('').map(lambda s: len([x for x in s.split(';') if x]))
    service = {'air_vent': 'Shared air vent', 'water_service': 'Shared water service'}
    fig, axes = plt.subplots(2, 3, figsize=(15, 8.2))
    axes = axes.ravel()
    for ax, (case, cand) in zip(axes, panels):
        g = blocking[(blocking.case_id == case) & (blocking.candidate == cand)].sort_values(['n', 'failed_item'], ascending=[False, True]).reset_index(drop=True)
        colours = [SERIES[2] if t == 'shared_service' else BLUES[8] for t in g.item_type]
        ax.barh(range(len(g)), g.n, color=colours, height=.5, zorder=3)
        labels = [f'{service.get(r.failed_item, TECH.get(r.failed_item, r.failed_item))}\n'
                  + ', '.join(FUNCTION.get(f, f) for f in r.lost_essential_functions.split(';')) for r in g.itertuples()]
        ax.set_yticks(range(len(g)), labels, fontsize=7.6); ax.invert_yaxis()
        for lab, r in zip(ax.get_yticklabels(), g.itertuples()):
            lab.set_color(INK)
        ax.set_title(f'{SHORT[case]} · {CANDIDATE[cand]}', loc='left', fontsize=9.5)
        ax.set_xlim(0, 3.4); ax.set_xticks([0, 1, 2, 3]); grid(ax, 'x')
        ax.set_xlabel('Essential functions lost with the item')
    axes[-1].set_axis_off()
    handles = [plt.Rectangle((0, 0), 1, 1, color=BLUES[8]), plt.Rectangle((0, 0), 1, 1, color=SERIES[2])]
    axes[-1].legend(handles, ['allocated hardware item', 'shared service'], loc='center left', fontsize=9)
    fig.suptitle('Single points in the declared dependencies: which item loss blocks full capability, and what it takes down', y=.995, fontsize=12.5)
    fig.tight_layout(rect=(0, .05, 1, .96))
    finish(fig, out / '05_single_point_dependencies.png', dpi=dpi, note=(
        'Structural loss under declared AND/OR dependencies: an integrated unit removes three air functions at once; a distributed chain spreads them over three items.\n'
        'Not failure rates or proof of installed redundancy; an external supplier is never counted as installed redundancy.'))

CAPTIONS = [
    ('01_nominal_work_schedule.png', 'Nominal capability work per candidate: design, procurement, remaining maturation stages, adaptation, qualification, enabling '
     'equipment and integrated acceptance, scheduled under one shared single-slot resource calendar for the low- and high-duration endpoints, against the '
     'scenario need date. Durations are analyst scenarios; confirmed delivery dates are unknown.'),
    ('02_driver_comparison.png', 'Mean high-minus-low contrasts of carried water, duration midpoint and development-exposure midpoint over the 64-scenario '
     'factorial grid per case. Zero effect can reflect schedule slack or an unchanged work stage.'),
    ('03_scenario_outcomes.png', 'Development exposure versus schedule margin to the need date for every stress combination at both duration endpoints, '
     'highlighting the air-maturity stress and the no-stress reference. Declared scenarios without probabilities.'),
    ('04_supply_routes.png', 'European supply-route status per required function and candidate, from process heritage to no route found, with a marker '
     'where a non-European route is also evidenced. Leads and heritage are not selected-configuration delivery.'),
    ('05_single_point_dependencies.png', 'Hardware items and shared services whose loss blocks full capability under the declared functional dependencies, '
     'with the essential functions each loss removes. Structural diagnostics, not failure probabilities.'),
]


def report(tables, cfg):
    lines = ['CAPABILITY PLANNING FOR THE READINESS PROFILE', '',
             'Engineering scenarios are separate from documented capability and delivery evidence.',
             'No selected configuration currently has an evidence-supported availability date.',
             'European routes lead the analysis; non-European alternatives are recorded separately.', '',
             'CAPABILITY AND TIMING']
    for r in tables['capabilities'].itertuples():
        if r.full_scope_covered:
            lines.append(f'{r.case_id} / {r.candidate}: {r.duration_days_low:g}–{r.duration_days_high:g} scenario days; '
                         f'{r.available_date_low} to {r.available_date_high}; {r.planning_status}.')
        else:
            lines.append(f'{r.case_id} / {r.candidate}: minimum-support reference; missing {r.missing_functions}.')
    lines += ['', 'SOURCE AND SUPPLY INTERPRETATION', *cfg.get('source_interpretation', []),
              'Supplier records are leads, not independent suppliers. No route in the reviewed register confirms selected-configuration delivery.',
              'A zero route count means no route found in this review; it does not establish market absence.', '',
              'BLOCKING FUNCTIONS AND SUPPLY EVIDENCE']
    # Function-family coverage is common to both cases; configuration matches
    # and all candidate allocations remain in the detailed route ledger.
    overview = tables['technology_gaps'].query("case_id == 'HLS_SORTIE' and candidate == 'integrated'")
    for r in overview.itertuples():
        lines.append(f'{r.function} ({r.technology_id}): Europe — {r.european_route_status}; '
                     f'outside Europe — {r.worldwide_alternative_status}.')
    lines += ['These are process-family leads, not qualified substitutions for the selected hardware.',
              'Structural blocking dependencies are listed separately in dependency_losses.csv.', '',
              'WHAT DRIVES FRAGILITY?']
    effects = tables['driver_effects']
    for (case, metric), g in effects.groupby(['case_id', 'metric']):
        best = g[g['rank'] == 1]
        lines.append(f'{case}, {metric}: largest declared contrast: ' + ', '.join(f'{r.factor} ({r.high_minus_low:.3g})' for r in best.itertuples()) + '.')
    lines += ['', 'INTERPRETATION LIMITS',
              ('Recovery assumptions call the physical sizing model, including lander wet-mass closure.' if engineering.source() == 'live' else
               'Recovery assumptions use the frozen engineering snapshot (data/engineering_snapshot), a recorded run of the sizing and lander wet-mass closure models.')
              + ' Exceeding a declared resource reserve triggers an explicit redesign package.',
              'Case-specific maturity determines declared remaining-work stages. Generic TRL9 never removes procurement, adaptation or acceptance.',
              'Hardware loss propagates through declared functional dependencies. Shared air services are a separate loss event; no failure frequency is inferred.',
              'A shared-service interruption can add restoration cash yet consume existing schedule slack. ANALOGS water TRL4→3 stays in the same declared breadboard stage.',
              'The scheduler uses fixed topological priority and one slot per named resource. It is feasible under its assumptions, not a resource schedule optimum.',
              'All numerical duration, recovery, maturity, cash, reserve and start/need-date inputs in this extension are analyst scenarios. Their rankings depend on the chosen ranges.',
              'Work and holding exposure excludes equipment procurement prices and is not whole-programme cost.',
              'Water polishing is an explicit candidate allocation requiring its own acceptance and supply evidence. Urine, brine, food and biological closure are outside this comparison.',
              *cfg.get('scope_notes', []), '']
    if 'eri_handoff' in tables:
        lines += ['OPTIONAL EXPLORATORY POMDP HANDOFF (NOT THE CURRENT PAPER)',
                  'The high-duration endpoint leaves a conditional additional-correction window before the scenario need date. Incomplete or late candidates are deferred.',
                  'The planner uses separately declared priors, likelihoods and correction costs. It cannot turn a supplier count or TRL into a readiness probability.',
                  'POMDP actions address additional unresolved work after the nominal schedule. They do not authorize operational or crew release.', '']
    lines += ['Reproduce: python scripts/run_capabilities.py',
              'Inputs: data/capability_planning.yaml; data/evidence/capability_routes.csv; data/evidence/capability_sources.json.',
              'See docs/capability_planning.md for equations, source uses and boundaries.']
    return '\n'.join(lines) + '\n'


def export(out=None):
    out = Path(out or 'outputs/capabilities')
    out.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    tables = study(cfg=cfg)
    for name, frame in tables.items():
        frame.to_csv(out / (name + '.csv'), index=False, float_format='%.10g')
    (out / 'sources.json').write_bytes((DATA / 'evidence/capability_sources.json').read_bytes())
    (out / 'assumptions.yaml').write_bytes((DATA / 'capability_planning.yaml').read_bytes())
    text = report(tables, cfg)
    (out / 'RESULTS.txt').write_text(text)
    figures(out, tables)
    (out / 'captions.txt').write_text('\n\n'.join(f'{name}\n{text}' for name, text in CAPTIONS) + '\n')
    links = '\n'.join(f'- [{p.name}]({p.name})' for p in sorted(out.iterdir()) if p.suffix in {'.csv', '.png', '.json', '.yaml', '.txt'} and p.name != 'manifest.json')
    (out / 'README.md').write_text('# Capability planning\n\nRead [the findings](RESULTS.txt) or [the visual index](index.html). '
                                 'All dates are conditional scenarios; documented delivery dates remain unknown.\n\n' + links + '\n')
    html = '<!doctype html><html lang="en"><meta charset="utf-8"><title>ECLSS capability planning</title>'
    html += '<style>body{font:16px/1.5 system-ui;max-width:1200px;margin:2em auto;padding:1em}img{width:100%}pre{white-space:pre-wrap}</style>'
    html += '<h1>ECLSS capability planning</h1><p>Engineering and supply evidence for the readiness profile. <a href="README.md">Tables and sources</a></p>'
    for name, _ in CAPTIONS:
        html += f'<img src="{name}" alt="{escape(name)}">'
    html += '<pre>' + escape(text) + '</pre></html>'
    (out / 'index.html').write_text(html)
    write_manifest(out, dict(schema_version=1, status=cfg['status'], code_sha256=code_hashes(),
                             input_sha256=input_hashes(), output_sha256=output_hashes(out)))
    return out
