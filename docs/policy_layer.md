# Policy layer: the readiness profile read as programme and funding decisions

`src/eri/policy_layer.py`, run with `python scripts/run_policy_layer.py` (or `eri-profile policy`),
writes `outputs/policy_layer/`. It reads the capability study and adds what a programme or funding body
needs from it, without estimating anything.

## What it adds

| Output | Question it answers | Inputs |
|---|---|---|
| `requirement_actions.csv` | Is each requirement supported, unknown or a documented shortfall, and which action class, owner and instruments follow? | capability study, `evidence/search_log.csv`, `policy_layer.yaml`, `instrument_register.yaml` |
| `work_actions.csv` | Which work packages are investment, information or infrastructure, and which depend on the structure or a shared resource? | capability study, `policy_layer.yaml` |
| `funding_cycle_exposure.csv` | How many dated funding decisions fall inside each implementation path? | capability study, `decision_calendar.yaml` |
| `evidence_age_by_capability.csv` | How old is the evidence behind each capability, measured at each case's need date? | `evidence/evidence_dates.csv`, `ecosystem_actors.csv` |
| `search_coverage.csv` | Which functions were searched, how, and with what result? | `evidence/search_log.csv` |
| `missing_inputs.csv` | Which inputs do not exist yet, and what would each one answer? | all of the above |

## Rules

- **Documented shortfall.** A requirement becomes a documented shortfall in the reviewed scope only when no route of
  any kind is recorded for the function in that pool, and the search log holds a search for that function, covering
  that pool, that found nothing and is marked `counts_toward_absence`. Anything else that is not delivery-confirmed
  stays unknown. A negative search for one route type (for example commercial products) does not override a
  recorded development route; the table says so in `state_note`.
- **Function not in the architecture.** When the candidate does not provide a function (the open lander reference),
  the gap is architectural, not a supply question, and no programme action is attached.
- **Funding-cycle exposure.** Only events with a date stated in a source are counted. An applicable event without a
  date makes the result a lower bound (`lower_bound_only`), never zero.
- **Evidence age.** Reported, never flagged, until `stale_after_years` is set in `policy_layer.yaml`.

## Where the new data come from

- `evidence/search_log.csv`: 24 hand-documented searches (directory string searches, the 9-10 September mining
  gaps, the 14 September "not found" list) and 100 record verifications of 14 September 2026, built by the authors
  from their evidence registers. Verification rows whose search could not be carried out are recorded as
  `not_completed`, not as negatives. Catalogue references are pseudonymised in this release.
- `evidence/evidence_dates.csv`: evidence and last-checked dates of the catalogue records and routes, from the mining
  register, source-title years (labelled `year_in_source_title`), the route source dates and the verification
  retrieval dates.
- `decision_calendar.yaml`: ESA Councils at Ministerial Level with the dates ESA pages state (reviewed 2026-09-26).
  The next council after CM25 has no announced date in the pages reviewed. HUMANS funding and procurement dates are
  placeholders for the author.
- `instrument_register.yaml`: Directive 2014/24/EU Articles 27, 28, 31 and 40 (text checked 2026-09-26), COM(2007)
  799 on pre-commercial procurement, the ESA GSTP; practice-only instruments are marked `definitional`.

## Current result (2026-09-26)

Every essential requirement of both cases is `unknown`, so the first action class is information. The code can now
record a documented shortfall, but the log holds a single search that qualifies (MIN-02, a European commercial
cabin-scale CO2 removal unit), and a development route exists for that function, so it stays unknown. Funding-cycle
exposure is a lower bound for every path: the next ESA council date and the HUMANS funding and procurement dates are
not in the data.

## Empty input tables, by design

`tender_lead_times.csv`, `expert_elicitation.csv`, `technology_materials.csv`, `critical_raw_materials.csv`,
`test_services.csv` and `reference_class_programmes.csv` have headers and no rows. `policy_layer.yaml` states what
each would answer and where its data should come from. A test checks that any future row carries a source.
