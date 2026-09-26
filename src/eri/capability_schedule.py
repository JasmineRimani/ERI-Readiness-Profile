"""Interval schedules with explicit missing data, release times and resources.

The scheduler uses a fixed topological priority and a single slot per named
resource. It is a reproducible feasible list schedule, not a schedule optimizer.
Ranges are scenario bounds, not confidence intervals or a duration distribution.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


EVIDENCE_STATUSES = {'documented_estimate', 'confirmed', 'completed'}
STATUSES = EVIDENCE_STATUSES | {'analyst_scenario', 'project_target', 'unknown'}


def interval(value, name):
    """Validate bounds; missing endpoints are kept missing, never zero-filled."""
    if len(value) != 2:
        raise ValueError(f'{name} requires two bounds')
    for x in value:
        if x is not None and (not math.isfinite(x) or x < 0):
            raise ValueError(f'{name} must be finite and nonnegative or unknown')
    if all(x is not None for x in value) and value[0] > value[1]:
        raise ValueError(f'{name} lower bound exceeds upper bound')
    return tuple(value)


@dataclass(frozen=True)
class Activity:
    name: str
    days: tuple
    cost_keur: tuple = (0.0, 0.0)
    prerequisites: tuple = ()
    resource: str = ''
    release_days: tuple = (0.0, 0.0)
    status: str = 'unknown'
    source_id: str = ''
    reason: str = ''

    def validate(self):
        interval(self.days, self.name)
        interval(self.cost_keur, self.name + ' cost')
        interval(self.release_days, self.name + ' release')
        if self.status not in STATUSES:
            raise ValueError(f'Unknown estimate status: {self.status}')
        if self.status in EVIDENCE_STATUSES and not self.source_id:
            raise ValueError(f'Evidence estimate requires a source: {self.name}')
        if self.status == 'completed' and self.days != (0, 0):
            raise ValueError('Completed work must have zero remaining duration')


def ordered_graph(activities):
    """Reject invalid graphs before scheduling, including disconnected cycles."""
    activities = list(activities)
    nodes = {a.name: a for a in activities}
    if len(nodes) != len(activities):
        raise ValueError('Duplicate activity')
    for a in activities:
        a.validate()
        if set(a.prerequisites) - nodes.keys():
            raise ValueError(f'Missing prerequisite: {a.name}')
    ordered, pending = [], dict(nodes)
    while pending:
        ready = sorted(n for n, a in pending.items() if set(a.prerequisites) <= set(ordered))
        if not ready:
            raise ValueError('Activity graph contains a cycle')
        # One at a time: newly ready work participates in the next priority
        # decision. Both interval endpoints use exactly the same ordering.
        name = ready[0]
        ordered.append(name)
        del pending[name]
    return nodes, ordered


def schedule(activities, resources=None, *, evidence_only=False):
    """Return activity starts/finishes and reasons why a date is unresolved.

    Resource precedence is explicit: an unresolved earlier booking also makes
    later work on that slot unresolved. Independent branches remain calculable.
    Evidence-only execution excludes analyst-scenario durations and calendars.
    """
    resources = resources or {}
    nodes, order = ordered_graph(activities)
    previous, parents = {}, {}
    for name in order:
        a = nodes[name]
        dependencies = list(a.prerequisites)
        if a.resource:
            if a.resource not in resources:
                raise ValueError(f'Missing resource calendar: {a.resource}')
            calendar = resources[a.resource]
            interval(calendar['available_after_days'], a.resource)
            if calendar['status'] not in STATUSES:
                raise ValueError('Unknown calendar status')
            if calendar['status'] in EVIDENCE_STATUSES and not calendar.get('source_id'):
                raise ValueError('Evidence calendar requires a source')
            if a.resource in previous:
                dependencies.append(previous[a.resource])
            previous[a.resource] = name
        parents[name] = tuple(dict.fromkeys(dependencies))
    results = {}
    for name in order:
        a = nodes[name]
        row = dict(activity=name, prerequisites=';'.join(a.prerequisites),
                   scheduled_predecessors=';'.join(parents[name]), resource=a.resource,
                   estimate_status=a.status, source_id=a.source_id, reason=a.reason,
                   declared_duration_low=a.days[0], declared_duration_high=a.days[1],
                   declared_cost_keur_low=a.cost_keur[0], declared_cost_keur_high=a.cost_keur[1])
        for index, bound in enumerate(('low', 'high')):
            missing = []
            duration = a.days[index]
            if a.status == 'unknown' or (evidence_only and a.status not in EVIDENCE_STATUSES):
                duration = None
            if duration is None:
                missing.append(name + ':duration')
            candidates = [(a.release_days[index], 'release')]
            if a.resource:
                calendar = resources[a.resource]
                available = calendar['available_after_days'][index]
                if calendar['status'] == 'unknown' or (evidence_only and calendar['status'] not in EVIDENCE_STATUSES):
                    available = None
                candidates.append((available, 'resource:' + a.resource))
            for parent in parents[name]:
                candidates.append((results[parent]['finish_' + bound], parent))
                missing.extend(results[parent]['unresolved_' + bound])
            missing.extend(label for value, label in candidates if value is None)
            start = None if any(v is None for v, _ in candidates) else max(v for v, _ in candidates)
            finish = None if start is None or duration is None else start + duration
            row['start_' + bound], row['finish_' + bound] = start, finish
            # A controlling predecessor traces the realized critical chain,
            # including competition for a shared resource.
            controlling = max(candidates, key=lambda x: x[0])[1] if start is not None else ''
            row['controlling_' + bound] = controlling
            row['unresolved_' + bound] = sorted(set(missing))
        results[name] = row
    return results


def critical_chain(timing, milestone, bound='high'):
    """Trace the controlling activities for one milestone, not a global rank."""
    if milestone not in timing:
        raise KeyError(milestone)
    if timing[milestone]['finish_' + bound] is None:
        return []
    chain, name = [], milestone
    while name in timing:
        chain.append(name)
        name = timing[name]['controlling_' + bound]
    return list(reversed(chain))
