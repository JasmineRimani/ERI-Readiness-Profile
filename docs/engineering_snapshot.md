# Engineering snapshot

The readiness profile starts from an engineering comparison: which hardware each candidate allocates to each function, and what the recovery assumptions mean for carried water, package mass and, for the lander, vehicle wet mass. In the authors' toolkit these quantities come from the ECLSS sizing ledger and the lander mass-closure loop. Those models are not part of this release.

`eri.engineering` is the only boundary between the profile and the engineering models. It has two interchangeable sources:

- `live`: the sizing and vehicle models, used when the `sizing` package is installed (authors' toolkit only);
- `snapshot`: the recorded run in `data/engineering_snapshot/`, used here.

`ERI_ENGINEERING=live|snapshot` forces a source; by default the snapshot is used whenever `sizing` is not installed. `eri-profile inputs` prints the active source.

## Contents

`values.csv` has one row per case, candidate and recovery stress:

| Column | Meaning |
|---|---|
| `case_id`, `candidate` | `HLS_SORTIE` (open, integrated, distributed) or `HUMANS` (integrated, distributed) |
| `air_recovery`, `water_recovery` | 1 when the declared recovery shortfall (0.10) is applied to the air feedwater credit (reference 0.40) or to the eligible-stream water recovery (reference 0.95) |
| `water_kg` | Carried or supplied water |
| `eclss_kg` | Accounted ECLSS package: hardware, tanks and initial supplies (Fig. 1 of the paper) |
| `vehicle_wet_kg` | Upper-retention lander wet mass; empty for HUMANS |
| `power_w`, `volume_m3` | Package power and volume |

`allocations.csv` lists the technology allocated to each function of each candidate. `manifest.json` records the recovery assumptions used, the units, the row counts and digests of the generating code and inputs.

## What the profile does with it

Only the recovery stresses change the physical values; the maturity, supplier-delay and shared-service stresses act on the work graph. The differences in water and wet mass are compared with each case's declared reserve in `capability_planning.yaml`. Exceeding a reserve inserts an explicit redesign and reverification work package. The allocation decides which procurement, development, adaptation and verification packages the work graph contains; multifunction equipment is procured and verified once.

## Guard against drift

The profile refuses to run when the recovery reference or shortfall in `capability_planning.yaml` differs from the values recorded in the snapshot manifest, because the frozen masses would no longer correspond to the stated assumptions. Changing work profiles, resources, dates, reserves or maturity scenarios needs no new snapshot. Changing recovery assumptions, candidates or hardware requires a new run of the engineering models by the authors.

The snapshot values are model outputs under generic equipment properties, not measured or validated masses. See the paper, Section 5.1, for their limits.
