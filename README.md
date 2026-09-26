# Ecosystem-readiness profile (ERI) for early-phase ECLSS design

This repository contains the ecosystem-readiness profile and the two case studies of the paper

> J. Rimani, G. Luccisano, G. Narducci, R. Fusaro and N. Viola, *Ecosystem-Aware Design: Formalizing Programmatic Fragility in Early-Phase ECLSS Sizing for Human Lunar Missions*, 77th International Astronautical Congress (IAC), Antalya, Türkiye, 5 to 9 October 2026, IAC-26,D3,3,4,x109477.

For an architecture *a*, an industrial ecosystem *e* and a required milestone *t_n*, the profile

R(a, e, t_n) = {E, W, D; C_W, M_T, M_C}

records the requirements and their evidence (E), the remaining work (W) and the dependencies between that work and the resources it needs (D), together with three figures of merit: the cost of the remaining work C_W, the schedule margin M_T and the cost margin M_C. Each requirement keeps one of three evidence states: *supported at the stated scope*, *documented shortfall* or *unknown*. The figures of merit are reported separately. There is no weighted score, no readiness probability and no automatic architecture ranking.

The case studies are the HUMANS terrestrial analog at Politecnico di Torino (two crew, fourteen days, readiness with integration and testing completed in Q1 2029, structure available by the end of 2027) and a reference short-sortie lunar lander (four crew, eight active life-support days, illustrative deadline). Integrated and distributed air-processing architectures share a membrane water-processing function; an open lander is kept as a physical reference.

## What is in this repository, and what is not

| Included | Not included |
|---|---|
| Capability work graph and resource-constrained scheduler (`eri.capability_schedule`, `eri.capability_planning`) | ECLSS sizing and lander mass-closure models |
| Supply-route assessment with European routes first (`eri.supply_routes`) | TRIS technology roadmapping tool |
| Readiness profiles, roadmap and schedule-stress figures (`eri.readiness_profile`) | HyCost cost models and programme budget records |
| Policy layer: evidence state, action class, funding-cycle exposure (`eri.policy_layer`) | Exploratory numerical POMDP, belief and scoring studies |
| POMDP belief update of Eq. (6), without calibrated probabilities (`eri.profile_pomdp`) | Named supplier records (pseudonymised here) |
| Frozen engineering values used by the profile (`data/engineering_snapshot/`) | Paper sources |

The sizing, TRIS and HyCost models belong to Politecnico di Torino and to ESA-funded projects and cannot be distributed. The profile only needs a few of their outputs (carried water, ECLSS package mass, lander wet mass, power, volume and the function-to-hardware allocation of each candidate). These are shipped as a recorded run in `data/engineering_snapshot/`, so the profile, the work graph and the schedule are computed exactly as in the paper. See [the engineering snapshot](docs/engineering_snapshot.md).

## Quick start

Python 3.9 or newer.

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/build_results.py            # writes outputs/
python -m unittest discover -s tests
```

Or install the package and use the command line:

```sh
pip install .
eri-profile all --out outputs              # capabilities, profiles and policy layer
eri-profile profile                        # readiness profiles only
eri-profile inputs                         # input folder and engineering source
```

`requirements-reference.txt` lists the library versions of the reference run.

## Paper to repository

| Paper | Where |
|---|---|
| Eq. (2) to (5): profile and figures of merit | `src/eri/readiness_profile.py`, `outputs/readiness_profile/profiles.json` |
| Table 1: questions and programme actions | `data/instrument_register.yaml`, `outputs/policy_layer/requirement_actions.csv` |
| Eq. (6): belief update | `src/eri/profile_pomdp.py` |
| Fig. 5: capability roadmap | `outputs/readiness_profile/01_capability_roadmap.png` |
| Table 2: conditional implementation scenarios | `outputs/readiness_profile/summary.csv` |
| Fig. 6: schedule consequences of the declared stresses | `outputs/readiness_profile/05_schedule_stress.png`, `schedule_stress.csv` |
| Table 3: proposed HUMANS activities | `data/humans_to_flight.csv` |
| Fig. 1 masses (inputs to the profile) | `data/engineering_snapshot/values.csv` |

Figures 2 to 4 (programme costs and TRIS reference paths) come from the models that are not included. `tests/test_reference_results.py` checks that this repository reproduces Table 2, the Fig. 1 masses and the Fig. 6 extremes.

## Repository map

| Location | Role |
|---|---|
| `src/eri/` | Profile code (one Python package, `eri`) |
| `data/` | Scenario inputs, evidence registers, pseudonymised catalogue and engineering snapshot; see [data/README.md](data/README.md) |
| `scripts/` | `build_results.py` and one wrapper per study |
| `tests/` | Scheduling, missing-evidence, policy-rule, belief-update and reference-result checks |
| `docs/` | Method notes; start at [docs/README.md](docs/README.md) |

## Interpretation

Scenario work costs and schedule margins are engineering figures of merit under declared analyst assumptions. A positive schedule margin means that the declared work could fit before the milestone; it does not confirm that equipment will arrive, that facilities will be accessible or that tests will pass. Supplier commitments, configuration acceptance, facility access and integration staffing remain explicit unknowns. No approved budget exists for the same work scope, so the cost margin M_C is reported as unresolved. Generic TRL 9 heritage never removes procurement, adaptation, verification or integrated acceptance. A route absent from the reviewed evidence is a search gap, not proof that no supplier exists.

The POMDP module states the belief update only. It holds no priors, transition or observation probabilities and computes no policy; those require programme records, supplier information and test outcomes.

## Licence and citation

Code: Apache License 2.0 ([LICENSE](LICENSE)). Data tables and documentation: CC BY 4.0 ([data/LICENSE](data/LICENSE)). See [NOTICE](NOTICE). Please cite the paper; [CITATION.cff](CITATION.cff) has the details.

This work draws on the HUMANS analog under development at Politecnico di Torino.
