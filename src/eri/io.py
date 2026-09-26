"""Input location and the supplier catalogue of the public ERI release.

Every input is a text file (YAML, CSV or JSON) under ``data/``. The study
modules read their own files from ``DATA``; this module only resolves that
folder and loads the pseudonymised ecosystem catalogue used by the supply-route
assessment and the policy layer.

``ERI_TOOLKIT_DATA=/absolute/path`` points the loader at a complete alternative
copy of the data folder.
"""
from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ["ERI_TOOLKIT_DATA"]) if "ERI_TOOLKIT_DATA" in os.environ else (
    ROOT / "data" if (ROOT / "data/capability_planning.yaml").is_file() else Path(str(resources.files("eri.data"))))

REGIONS = {'Europe', 'Outside Europe'}


@dataclass
class Inputs:
    """The shared inputs of the profile: the ecosystem catalogue."""
    actors: pd.DataFrame


def load_actors() -> pd.DataFrame:
    """Pseudonymised catalogue: record_id, entity_name, region, capability_key, supplier_scope."""
    a = pd.read_csv(DATA / "ecosystem_actors.csv", dtype=str, keep_default_na=False)
    if a.record_id.duplicated().any():
        raise ValueError("Duplicate catalogue record ID")
    if not set(a.region) <= REGIONS:
        raise ValueError(f"Unknown catalogue region: {sorted(set(a.region) - REGIONS)}")
    a["capability_key"] = a["capability_key"].replace("", "NOT_APPLICABLE").str.strip()
    a["is_europe"] = a["region"].eq("Europe")
    return a


def load_all() -> Inputs:
    return Inputs(actors=load_actors())
