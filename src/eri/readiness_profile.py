"""Architecture-specific readiness profiles, with no scalar aggregation.

Evidence, conditional work estimates and engineering figures of merit remain
separate. An early scenario completion date never establishes delivery readiness.
"""
from datetime import date
from html import escape
import json
from pathlib import Path

import pandas as pd

from eri.capability_planning import study
from eri.io import DATA
from eri.provenance import code_hashes, input_hashes, output_hashes, write_manifest


def native(value):
    """Represent missing evidence as JSON null, never zero or NaN."""
    if isinstance(value, dict):
        return {k: native(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [native(v) for v in value]
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    return value.item() if hasattr(value, 'item') else value


def build_profiles(tables):
    """Keep programme evidence and scenario margins distinct for every candidate."""
    profiles = []
    for row in tables['capabilities'].to_dict('records'):
        case, candidate = row['case_id'], row['candidate']
        select = lambda frame: frame[(frame.case_id == case) & (frame.candidate == candidate)]
        gaps = select(tables['technology_gaps'])
        work = select(tables['work_packages'])
        losses = select(tables['dependency_losses'])
        # Low/high in the source name duration endpoints. A longer duration
        # gives the LOWER schedule margin, so export ordered margin bounds.
        margins = [native(row['schedule_margin_days_' + b]) for b in ('low', 'high')]
        margin_bounds = [min(margins), max(margins)] if all(v is not None for v in margins) else [None, None]
        profiles.append(native(dict(
            case_id=case, candidate=candidate, ecosystem_scope='European routes; worldwide alternatives recorded separately',
            required_capability=row['required_capability'],
            functional_scope='allocated' if row['full_scope_covered'] else 'reference_outside_regenerative_scope',
            missing_functions=row['missing_functions'],
            readiness_status='unresolved' if row['full_scope_covered'] else 'required_function_missing',
            # Configuration qualification, access and integration are not
            # established by a numerical work schedule or by process heritage.
            configuration_acceptance_status='unknown', facility_access_status='unknown',
            integration_team_status='unknown', approved_budget_status='unknown',
            evidence_supported_delivery_date=row['evidence_available_date'],
            scenario_start_date=row['scenario_start_date'], scenario_need_date=row['need_date'],
            required_milestone=row['need_label'],
            required_milestone_window=[row['need_window_start'], row['need_window_end']],
            programme_source=row['programme_source'],
            structure_availability_target=row['structure_target'], structure_status=row['structure_status'],
            date_status=row['date_status'], scenario_planning_status=row['planning_status'],
            scenario_duration_days=[row['duration_days_low'], row['duration_days_high']],
            scenario_work_cost_keur=[row['work_cost_keur_low'], row['work_cost_keur_high']],
            scenario_development_exposure_keur=[row['development_exposure_keur_low'], row['development_exposure_keur_high']],
            scenario_schedule_margin_days=margin_bounds,
            margin_to_window_start_days=[row['margin_to_window_start_days_high'], row['margin_to_window_start_days_low']],
            margin_to_window_end_days=[row['margin_to_window_end_days_high'], row['margin_to_window_end_days_low']],
            cost_scope=row['cost_scope'],
            cost_margin_keur=None,
            cost_margin_status='unresolved_no_approved_budget_for_the_same_work_scope',
            supply_requirements=gaps.to_dict('records'),
            remaining_work=work.to_dict('records'),
            structural_dependencies=losses[losses.blocks_full_capability].to_dict('records'),
            unresolved_evidence_items=row['unresolved_evidence_items'],
            interpretation='conditional figures of merit and named evidence gaps; no scalar readiness or success probability',
        )))
    return profiles


def roadmap_figure(out, tables):
    """Show the actual scheduled work, including the resource-constrained stages."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from eri.figure_style import TECH
    colours = {'design': '#425b76', 'procure': '#bf8756', 'breadboard': '#4c8984',
               'relevant_demo': '#4c8984', 'adapt': '#4c8984', 'qualify': '#75688b',
               'support': '#909ba3', 'acceptance': '#75688b', 'structure': '#9c3f3f'}
    labels = {'design': 'Requirements / interfaces', 'procure': 'Procurement',
              'breadboard': 'Breadboard work', 'relevant_demo': 'Relevant-environment demonstration',
              'adapt': 'Configuration adaptation', 'qualify': 'Configuration verification',
              'support': 'Supporting equipment', 'acceptance': 'Integrated acceptance'}
    fig, axes = plt.subplots(2, 1, figsize=(8.2, 9.3))
    for ax, case, title in zip(axes, ('HUMANS', 'HLS_SORTIE'), ('HUMANS', 'Lunar lander')):
        rows = tables['work_packages'].query('case_id == @case and candidate == "integrated"').sort_values('start_low')
        cap = tables['capabilities'].query('case_id == @case and candidate == "integrated"').iloc[0]
        ylabels = []
        for i, row in enumerate(rows.itertuples()):
            if row.activity == '00_design': stage, name = 'design', labels['design']
            elif row.activity == '01_structure_available': stage, name = 'structure', 'Structure available: end 2027 target'
            elif row.activity == 'support_equipment': stage, name = 'support', labels['support']
            elif row.activity == 'zz_integrated_acceptance': stage, name = 'acceptance', labels['acceptance']
            else:
                tid, stage = row.activity.split('_', 1)
                name = f'{"Air" if tid.startswith("T-AR") else "Water"}: {labels[stage].lower()}'
            ylabels.append(name)
            for bound, dy, alpha in [('low', -.19, 1), ('high', .19, .38)]:
                start, end = getattr(row, 'start_' + bound), getattr(row, 'finish_' + bound)
                ax.barh(i + dy, end - start, left=start, height=.34, color=colours[stage], alpha=alpha)
                if stage == 'structure':
                    ax.scatter(start, i + dy, marker='D', color=colours[stage], s=26, alpha=alpha)
            if row.resource:
                ax.plot(row.start_high, i + .19, '|', color='#222222', ms=9)
        origin = date.fromisoformat(cap.scenario_start_date)
        need_start, need = [(date.fromisoformat(d) - origin).days for d in (cap.need_window_start, cap.need_window_end)]
        ax.axvspan(need_start, need, color='#9c3f3f', alpha=.10)
        ax.axvline(need, color='#9c3f3f', ls='--', lw=1.2)
        target = 'Q1 2029: testing complete ' if case == 'HUMANS' else 'Illustrative lander deadline '
        ax.text(need, .97, target, transform=ax.get_xaxis_transform(),
                color='#9c3f3f', rotation=90, va='top', ha='right', fontsize=8)
        ax.set_yticks(range(len(ylabels)), ylabels, fontsize=8)
        ax.invert_yaxis()
        ax.set_xlim(0, max(need, rows.finish_high.max()) * 1.1)
        ticks = [(date(y, m, 1) - origin).days for y in (2027, 2028, 2029) for m in (1, 7)]
        ax.set_xticks(ticks, [f'{m:02d}/{y}' for y in (2027, 2028, 2029) for m in (1, 7)], fontsize=8)
        ax.set_xlim(0, max(need, rows.finish_high.max()) * 1.1)
        ax.set_xlabel('Calendar date; preparatory-work start is an analyst assumption', fontsize=8)
        ax.set_title(title + ' / integrated candidate', fontsize=11)
        ax.spines[['top', 'right']].set_visible(False)
        ax.grid(axis='x', alpha=.15)
    fig.suptitle('Capability roadmap: technology work, procurement and integration', fontsize=11)
    fig.text(.5, .02, 'Dark bars: low-duration scenario; light bars: high-duration scenario. Vertical ticks: shared-resource use.\n'
             'HUMANS structure and Q1 target: author-provided constraints. Task durations and resource access: assumptions; delivery unconfirmed.',
             ha='center', fontsize=7)
    fig.tight_layout(rect=(0, .08, 1, .95))
    fig.savefig(out / '01_capability_roadmap.png', dpi=240, bbox_inches='tight')
    plt.close(fig)


def development_cost_figures(out, tables):
    """Cost the declared development/test work, without treating CAPEX as effort."""
    import matplotlib.pyplot as plt
    import numpy as np
    groups = [('design', 'Requirements / interfaces'), ('breadboard', 'Breadboard development'),
              ('relevant_demo', 'Relevant-environment demonstration'), ('adapt', 'Configuration adaptation'),
              ('qualify', 'Configuration verification'), ('acceptance', 'Integration / acceptance testing')]
    colours = ['#425b76', '#4c8984', '#75a6a0', '#bf8756', '#75688b', '#a295b4']
    rows = []
    for work in tables['work_packages'].to_dict('records'):
        stage = ('design' if work['activity'] == '00_design' else 'acceptance'
                 if work['activity'] == 'zz_integrated_acceptance' else work['activity'].split('_', 1)[-1])
        if stage in dict(groups):
            rows.append(dict(case_id=work['case_id'], candidate=work['candidate'], stage=stage,
                             lower_keur=work['declared_cost_keur_low'], upper_keur=work['declared_cost_keur_high']))
    costs = pd.DataFrame(rows).groupby(['case_id', 'candidate', 'stage'], as_index=False)[['lower_keur', 'upper_keur']].sum()
    costs.to_csv(out / 'development_testing_costs.csv', index=False)
    fig, axes = plt.subplots(1, 2, figsize=(10, 5.8))
    for ax, case, name in zip(axes, ('HUMANS', 'HLS_SORTIE'), ('HUMANS', 'Lunar lander')):
        subset = costs.query('case_id == @case and candidate == "integrated"').set_index('stage')
        values = [subset.loc[stage, 'lower_keur'] if stage in subset.index else 0 for stage, _ in groups]
        total = sum(values)
        ax.pie(values, colors=colours, startangle=90, wedgeprops=dict(width=.43, edgecolor='white'),
               autopct=lambda p: f'{p:.0f}%' if p > 0 else '', pctdistance=.78,
               textprops=dict(fontsize=9))
        ax.text(0, 0, f'{total:.0f}\nkEUR', ha='center', va='center', fontsize=16)
        ax.set_title(name + ' / integrated candidate', fontsize=11)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in colours]
    fig.legend(handles, [label for _, label in groups], loc='lower center', ncol=2, frameon=False, fontsize=9,
               bbox_to_anchor=(.5, .09))
    fig.suptitle('Development and testing: where the declared work cost goes', fontsize=13)
    fig.text(.5, .02, 'Lower cost scenario, not expenditure or an approved budget. Equipment purchase, structure and holding costs excluded.',
             ha='center', fontsize=8)
    fig.tight_layout(rect=(0, .24, 1, .94))
    fig.savefig(out / '02_development_testing_breakdown.png', dpi=240, bbox_inches='tight')
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    caps = tables['capabilities'].query('full_scope_covered').copy()
    labels = []
    for i, row in enumerate(caps.itertuples()):
        low, high = row.work_cost_keur_low, row.work_cost_keur_high
        ax.barh(i, high, height=.46, color='#dce6ec')
        ax.barh(i, low, height=.46, color='#425b76')
        ax.text(high + 10, i, f'{low:.0f}–{high:.0f}', va='center', fontsize=10)
        labels.append(f'{"HUMANS" if row.case_id == "HUMANS" else "Lander"} / {row.candidate}')
        subtotal = costs.query('case_id == @row.case_id and candidate == @row.candidate')[['lower_keur', 'upper_keur']].sum()
        if not np.allclose(subtotal.to_numpy(), [low, high]):
            raise ValueError('Development/test breakdown does not reconcile with direct work cost')
    ax.set_yticks(range(len(labels)), labels)
    ax.invert_yaxis()
    ax.set_xlim(0, caps.work_cost_keur_high.max() * 1.22)
    ax.set_xlabel('Direct development and testing work [kEUR]')
    ax.spines[['top', 'right']].set_visible(False)
    ax.set_title('Conditional work-cost ranges by architecture', fontsize=13)
    ax.grid(axis='x', alpha=.15)
    fig.text(.5, .02, 'Dark: lower scenario; pale extension: upper scenario. Estimates are uncalibrated; ranges are not confidence intervals.',
             ha='center', fontsize=8)
    fig.tight_layout(rect=(0, .06, 1, 1))
    fig.savefig(out / '03_development_testing_comparison.png', dpi=240, bbox_inches='tight')
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    for ax, case, name in zip(axes, ('HUMANS', 'HLS_SORTIE'), ('HUMANS', 'Lunar lander')):
        grid = tables['sensitivity_scenarios'].query('case_id == @case')
        for bound, marker, label in [('low', 'o', 'Short duration / later deadline'), ('high', '^', 'Long duration / earlier deadline')]:
            ax.scatter(grid['work_cost_keur_' + bound], grid['schedule_margin_days_' + bound],
                       marker=marker, s=25, alpha=.55, label=label)
        ax.axhline(0, color='#9c3f3f', lw=1)
        ax.set_title(name, fontsize=12)
        ax.set_xlabel('Direct work cost [kEUR]')
        ax.set_ylabel('Schedule margin [days]')
        ax.grid(alpha=.15)
        ax.spines[['top', 'right']].set_visible(False)
    axes[0].legend(fontsize=7, loc='best')
    fig.suptitle('Development/testing cost and time consequences', fontsize=13)
    fig.text(.5, .015, 'HUMANS margins span the Q1 2029 target window; lander uses one illustrative deadline. Scenarios have no assigned probabilities.',
             ha='center', fontsize=8)
    fig.tight_layout(rect=(0, .06, 1, .95))
    fig.savefig(out / '04_development_cost_schedule.png', dpi=240, bbox_inches='tight')
    plt.close(fig)


def schedule_stress_figure(out, tables):
    """Show timing effects without treating exploratory work costs as budgets."""
    import matplotlib.pyplot as plt
    factors = [('air_recovery', 'Lower air recovery'), ('water_recovery', 'Lower water recovery'),
               ('air_maturity', 'Additional air development'), ('water_maturity', 'Additional water development'),
               ('supplier_delay', 'Supplier delay'), ('shared_service', 'Shared-service interruption')]
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.4), sharey=True)
    exported = []
    for ax, case, title in zip(axes, ['HUMANS', 'HLS_SORTIE'], ['HUMANS', 'Lunar lander']):
        grid = tables['sensitivity_scenarios'].query('case_id == @case').copy()
        flags = [name for name, _ in factors]
        selected = [('Reference', grid.loc[grid[flags].sum(axis=1) == 0].iloc[0])]
        for name, label in factors:
            selected.append((label, grid.loc[(grid[name] == 1) & (grid[flags].sum(axis=1) == 1)].iloc[0]))
        selected.append(('All declared stresses', grid.loc[grid[flags].sum(axis=1) == len(flags)].iloc[0]))
        for i, (label, row) in enumerate(selected):
            lower, upper = row.schedule_margin_days_high, row.schedule_margin_days_low
            ax.plot([lower, upper], [i, i], color='#355c7d', lw=3)
            ax.scatter([lower, upper], [i, i], color='#355c7d', s=25)
            exported.append({'case_id':case, 'scenario':label, 'margin_lower_days':lower, 'margin_upper_days':upper})
        ax.axvline(0, color='#a54742', lw=1, ls='--')
        ax.set_yticks(range(len(selected)), [label for label, _ in selected])
        ax.set_title(title + ' / integrated candidate', fontsize=11)
        ax.set_xlabel('Schedule margin [days]')
        ax.grid(axis='x', alpha=.16)
        ax.spines[['top', 'right']].set_visible(False)
    axes[0].invert_yaxis()
    fig.suptitle('Schedule consequences of the declared stresses', fontsize=14)
    fig.text(.5,.025,'Ranges combine the stated duration endpoints; HUMANS also spans the Q1 2029 target window.\n'
             'Lander deadline and task durations remain illustrative. Negative values indicate lateness to the evaluated boundary.',
             ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.12,1,.94))
    fig.savefig(Path(out)/'05_schedule_stress.png',dpi=240,bbox_inches='tight')
    plt.close(fig)
    pd.DataFrame(exported).to_csv(Path(out)/'schedule_stress.csv',index=False)


def export(out='outputs/readiness_profile'):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    tables = study()
    profiles = build_profiles(tables)
    (out / 'profiles.json').write_text(json.dumps(profiles, indent=2, allow_nan=False) + '\n')
    summary = []
    for p in profiles:
        r = {k: p[k] for k in ('case_id', 'candidate', 'functional_scope', 'readiness_status',
             'evidence_supported_delivery_date', 'scenario_start_date', 'scenario_need_date', 'scenario_planning_status',
             'required_milestone', 'structure_availability_target', 'structure_status',
             'cost_margin_keur', 'cost_margin_status')}
        for key in ('scenario_duration_days', 'scenario_work_cost_keur', 'scenario_development_exposure_keur', 'scenario_schedule_margin_days'):
            r[key + '_lower'], r[key + '_upper'] = p[key]
        summary.append(r)
    pd.DataFrame(summary).to_csv(out / 'summary.csv', index=False)
    for key in ('technology_gaps', 'work_packages', 'dependency_losses', 'supplier_routes'):
        tables[key].to_csv(out / (key + '.csv'), index=False)
    (out / 'humans_to_flight.csv').write_bytes((DATA / 'humans_to_flight.csv').read_bytes())
    roadmap_figure(out, tables)
    development_cost_figures(out, tables)
    schedule_stress_figure(out, tables)
    lines = ['# Ecosystem-readiness profiles', '',
             'Readiness records for one architecture, ecosystem and milestone.',
             'Monetary work scenarios below are supplementary, not the programme totals in the main paper.',
             'Programme cost totals (facility budget, whole-vehicle lifecycle) are a separate accounting view and are not part of this profile.',
             'No weighted score, probability or automatic architecture ranking is calculated.', '',
             '| Case / architecture | Work cost scenario (kEUR) | Schedule margin scenario (days) | Evidence status |',
             '|---|---:|---:|---|']
    for p in profiles:
        if p['functional_scope'] != 'allocated':
            lines.append(f"| {p['case_id']} / {p['candidate']} | Reference only | Outside regenerative scope | Required functions missing |")
        else:
            cost, margin = p['scenario_work_cost_keur'], p['scenario_schedule_margin_days']
            show = lambda x: 'unknown' if any(v is None for v in x) else f'{x[0]:g} to {x[1]:g}'
            lines.append(f"| {p['case_id']} / {p['candidate']} | {show(cost)} | {show(margin)} | Delivery / acceptance unresolved |")
    lines += ['', 'HUMANS: structure targeted for end 2027; procurement starts no earlier than January 2028; integration/testing complete in Q1 2029.',
              'The exact Q1 deadline is unresolved. Margin bounds combine the earlier/later quarter endpoints with longer/shorter task durations.',
              'Positive schedule margin means the declared work scenario finishes before the evaluated milestone boundary. It does not confirm delivery.',
              'Cost margin remains unknown because an approved budget for the same work scope is unavailable. Correction reserves are not a nominal-work budget.',
              'Work costs and programme procurement/lifecycle estimates have overlapping integration scope; they must not be added without reconciliation.', '',
              'The HUMANS-to-flight register lists proposed evidence to obtain, not completed tests or demonstrated flight capability.', '',
              '- [Complete profiles](profiles.json)', '- [Summary table](summary.csv)',
              '- [Capability roadmap](01_capability_roadmap.png)', '- [Proposed HUMANS-to-flight evidence](humans_to_flight.csv)',
              '- [Development and testing costs](development_testing_costs.csv)',
              '- [Supply requirements](technology_gaps.csv)', '- [Work packages](work_packages.csv)',
              '- [Structural dependencies](dependency_losses.csv)', '- [Method](../../docs/readiness_profile.md)', '',
              'Reproduce: `python scripts/run_profile.py`', '']
    (out / 'README.md').write_text('\n'.join(lines))
    html = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Ecosystem-readiness profiles</title>'
    html += '<style>body{font:16px/1.5 system-ui;max-width:1200px;margin:2em auto;padding:1em}img{width:100%}pre{white-space:pre-wrap}</style>'
    html += '<h1>Ecosystem-readiness profiles</h1><p>Architecture, ecosystem and milestone; conditional figures of merit with explicit evidence gaps.</p>'
    html += '<p><a href="README.md">Tables and method</a> · <a href="profiles.json">Complete profiles</a></p>'
    html += '<img src="01_capability_roadmap.png" alt="Capability work roadmap for HUMANS and the lunar lander">'
    html += '<pre>' + escape('\n'.join(lines)) + '</pre></html>'
    (out / 'index.html').write_text(html)
    write_manifest(out, dict(schema_version=1, status='readiness_profile_no_scalar_aggregation',
                   code_sha256=code_hashes(), input_sha256=input_hashes(), output_sha256=output_hashes(out)))
    return out
