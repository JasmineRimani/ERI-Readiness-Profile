# Data

Every input is a text file. The study modules read them from this folder; `ERI_TOOLKIT_DATA=/absolute/path` selects a complete alternative copy. Data tables are licensed under CC BY 4.0 ([LICENSE](LICENSE)).

## Scenario inputs

| File | Holds | Read by |
|---|---|---|
| `capability_planning.yaml` | Start and need dates, required functions, resource reserves, case maturity scenarios, work profiles, single-slot resource calendars and the six declared stresses of both cases. Every number is marked as an analyst scenario or an author-provided project input | `eri.capability_planning`, `eri.capability_publication`, `eri.policy_layer` |
| `humans_to_flight.csv` | Proposed HUMANS evidence-transfer register (Table 3 of the paper); every entry is proposed, not demonstrated | `eri.readiness_profile` |
| `policy_layer.yaml` | Shortfall rule, evidence-state to action mapping, work-package action classes and the register of empty input tables | `eri.policy_layer` |
| `decision_calendar.yaml` | Dated funding decisions (ESA Councils at Ministerial Level) with their sources; HUMANS funding dates remain author inputs | `eri.policy_layer` |
| `instrument_register.yaml` | Action classes and the programme or legal instruments that implement them (Table 1 of the paper) | `eri.policy_layer` |

## Engineering snapshot

`engineering_snapshot/` holds the recorded output of the sizing and lander closure models for every case, candidate and recovery stress: `values.csv` (carried water, ECLSS package mass, lander wet mass, power, volume), `allocations.csv` (function to technology allocation) and `manifest.json` (recovery assumptions, units, digests of the generating code and inputs). The models themselves are not part of this release. See [docs/engineering_snapshot.md](../docs/engineering_snapshot.md).

## Evidence registers

| File | Holds |
|---|---|
| `evidence/capability_routes.csv` | Reviewed process routes per function, with route kind, region, source, adaptation gap, configuration acceptance and delivery confirmation. Provider names are pseudonymised |
| `evidence/capability_sources.json` | Public documents behind the routes and observations, with what each establishes and its access limits |
| `evidence/capability_observations.csv` | Measurements extracted from the sources, with test context and transfer limits; none is applied to the selected configuration |
| `evidence/function_capabilities.csv` | Function to capability-key mapping |
| `evidence/search_log.csv` | Documented searches, including those that found nothing; the basis of the documented-shortfall rule |
| `evidence/evidence_dates.csv` | Evidence and last-checked dates of catalogue records and routes |
| `evidence/humans_programme_constraints.json` | Author-provided HUMANS programme inputs (structure by end 2027, readiness in Q1 2029) |
| `evidence/tender_lead_times.csv`, `expert_elicitation.csv`, `technology_materials.csv`, `critical_raw_materials.csv`, `test_services.csv`, `reference_class_programmes.csv` | Empty tables with headers, by design: `policy_layer.yaml` states what each would answer |

## Ecosystem catalogue

`ecosystem_actors.csv` is the pseudonymised ecosystem catalogue: `record_id`, `entity_name`, `region` (Europe or Outside Europe), `capability_key` and `supplier_scope`. Organisation names and record identifiers are replaced by stable pseudonyms (`ORG-E001`, `REC-0001`); regions, capability keys and supplier roles are unchanged, so every route status and count in the profile is identical to the authors' run. See [docs/data_release.md](../docs/data_release.md).
