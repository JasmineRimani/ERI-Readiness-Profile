"""Boundary between the readiness profile and the engineering models.

The capability work graph needs, for every case, candidate architecture and
recovery stress, a few engineering quantities (carried water, ECLSS package
mass, lander wet mass, power, volume) and the function-to-hardware allocation.
Two interchangeable sources provide them:

``live``
    The sizing and vehicle-closure models (``sizing`` package). Candidate
    overrides are applied to a local copy of the inputs, so sweeps cannot
    alter the shared architecture table.
``snapshot``
    Frozen tables under ``data/engineering_snapshot/`` written from a live run
    by ``scripts/export_engineering_snapshot.py``. A release without the
    engineering models ships only this source; the profile, the work graph and
    the schedule are computed exactly as with the live models.

``ERI_ENGINEERING=live`` or ``snapshot`` forces one source. The default is
``live`` when the ``sizing`` package is importable and its inputs
(``technologies.yaml``) are in the data folder, and ``snapshot`` otherwise. An
unrelated installed copy of ``sizing`` therefore never overrides the snapshot
of a release that has no engineering inputs.
"""
from copy import deepcopy
from functools import lru_cache
from importlib.util import find_spec
import json
import os

import pandas as pd
import yaml

from eri.io import DATA

SNAPSHOT_DIR = 'engineering_snapshot'
RECOVERY_FACTORS = ('air_recovery', 'water_recovery')
VALUE_COLUMNS = ('water_kg', 'eclss_kg', 'vehicle_wet_kg', 'power_w', 'volume_m3')
KEY_COLUMNS = ('case_id', 'candidate') + RECOVERY_FACTORS


def live_available():
    """True when the sizing models and their inputs are both present."""
    return find_spec('sizing') is not None and (DATA / 'technologies.yaml').is_file()


def source():
    """Return ``'live'`` or ``'snapshot'`` for this run."""
    choice = os.environ.get('ERI_ENGINEERING', 'auto').strip().lower()
    if choice == 'auto':
        return 'live' if live_available() else 'snapshot'
    if choice not in ('live', 'snapshot'):
        raise ValueError(f'ERI_ENGINEERING must be live, snapshot or auto, not {choice!r}')
    if choice == 'live' and not live_available():
        raise ImportError('ERI_ENGINEERING=live requires the sizing package and its inputs, which are not available')
    return choice


def architecture_config():
    """Candidate definitions used by the live models (``eri_architecture_study.yaml``)."""
    return yaml.safe_load((DATA / 'eri_architecture_study.yaml').read_text())


# ---------------------------------------------------------------------------
# snapshot source
# ---------------------------------------------------------------------------
@lru_cache(maxsize=None)
def _snapshot(folder):
    folder = DATA / SNAPSHOT_DIR if folder is None else folder
    values = pd.read_csv(folder / 'values.csv', float_precision='round_trip')
    allocations = pd.read_csv(folder / 'allocations.csv', keep_default_na=False, dtype=str)
    meta = json.loads((folder / 'manifest.json').read_text())
    if meta.get('schema_version') != 1:
        raise ValueError('Unsupported engineering snapshot schema')
    missing = set(KEY_COLUMNS + VALUE_COLUMNS) - set(values.columns)
    if missing:
        raise ValueError(f'Engineering snapshot lacks columns {sorted(missing)}')
    if values.duplicated(list(KEY_COLUMNS)).any():
        raise ValueError('Duplicate engineering snapshot key')
    if allocations.duplicated(['case_id', 'candidate', 'function']).any():
        raise ValueError('Duplicate function allocation in the engineering snapshot')
    return values, allocations, meta


def snapshot_tables(folder=None):
    """``(values, allocations, manifest)`` of the frozen engineering run."""
    return _snapshot(folder)


def _snapshot_candidates(case):
    values, _, _ = _snapshot(None)
    rows = values[values.case_id == case]
    if rows.empty:
        raise KeyError(f'No engineering snapshot for case {case}')
    return list(dict.fromkeys(rows.candidate))


def _snapshot_technical(cfg, case, candidate, factors):
    values, allocations, meta = _snapshot(None)
    frozen = meta['recovery_assumptions']
    if (frozen['recovery_reference'] != cfg['recovery_reference']
            or frozen['recovery_shortfall'] != cfg['recovery_shortfall']):
        raise ValueError('capability_planning.yaml recovery assumptions differ from the frozen engineering '
                         'snapshot; regenerate it with scripts/export_engineering_snapshot.py')
    flags = {f: int(f in factors) for f in RECOVERY_FACTORS}
    match = values[(values.case_id == case) & (values.candidate == candidate)]
    for f, v in flags.items():
        match = match[match[f] == v]
    if len(match) != 1:
        raise KeyError(f'No engineering snapshot row for {case}/{candidate} with {flags}')
    row = match.iloc[0]
    out = {k: (None if pd.isna(row[k]) else float(row[k])) for k in VALUE_COLUMNS}
    alloc = allocations[(allocations.case_id == case) & (allocations.candidate == candidate)]
    functions = dict(zip(alloc.function, alloc.technology_id))
    return out, functions


# ---------------------------------------------------------------------------
# live source (sizing models)
# ---------------------------------------------------------------------------
def candidate_inputs(inp, architecture_cfg, case, candidate):
    """Keep candidate overrides local so parameter sweeps cannot alter inputs."""
    local = deepcopy(inp)
    option = architecture_cfg['cases'][case]['candidates'][candidate]
    aid = f'capability_{case}_{candidate}'
    functions = deepcopy(local.archs['architectures'][option['base']])
    functions.update(option['overrides'])
    for function in architecture_cfg['remove_functions']:
        functions.pop(function, None)
    local.archs['architectures'][aid] = functions
    return local, aid


def _live_technical(inp, architecture_cfg, cfg, case, candidate, factors):
    from sizing.design_loop import close_lander
    from sizing.eclss import resolve_architecture, size

    local, aid = candidate_inputs(inp, architecture_cfg, case, candidate)
    functions = resolve_architecture(local, aid)
    for chain, function in (('air', 'co2_reduction'), ('water', 'water_processing')):
        if function in functions:
            value = cfg['recovery_reference'][chain]
            if chain + '_recovery' in factors:
                value -= cfg['recovery_shortfall']
            if not 0 <= value <= 1:
                raise ValueError('Recovery scenario outside [0,1]')
            local.tech.loc[functions[function], 'recovery_fraction_demonstrated'] = value
    ledger = size(local, case, aid)
    wet = close_lander(local, case, aid, 'demonstrated')['vehicle_wet_upper_kg'] if case == 'HLS_SORTIE' else None
    return dict(water_kg=ledger.water_carried_kg, eclss_kg=ledger.total_launched_kg,
                vehicle_wet_kg=wet, power_w=ledger.power_w, volume_m3=ledger.volume_m3), functions


# ---------------------------------------------------------------------------
# public interface
# ---------------------------------------------------------------------------
def candidates(case, architecture_cfg=None):
    """Candidate architectures of a case, in their declared order."""
    if source() == 'live':
        return list((architecture_cfg or architecture_config())['cases'][case]['candidates'])
    return _snapshot_candidates(case)


def technical(inp, architecture_cfg, cfg, case, candidate, factors=()):
    """Engineering values and function allocation for one candidate and recovery stress.

    Only the recovery factors change the physical result; the other stresses
    act on the work graph and are ignored here.
    """
    factors = frozenset(factors) & set(RECOVERY_FACTORS)
    if source() == 'live':
        return _live_technical(inp, architecture_cfg or architecture_config(), cfg, case, candidate, factors)
    return _snapshot_technical(cfg, case, candidate, factors)
