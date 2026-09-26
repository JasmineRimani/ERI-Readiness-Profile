# Ecosystem-readiness profile

The profile assesses the fit between an architecture, its industrial ecosystem and a required milestone. It replaces an index: there is no weighted aggregate, readiness probability, threshold on an invented score, or automatic architecture winner.

Run `python scripts/run_profile.py` (or `eri-profile profile`) and open `outputs/readiness_profile/index.html`. Run `python scripts/build_results.py` to regenerate the capability analysis, profiles and policy layer together.

## Assessment and figures of merit

Each profile records required functions, the evidence for supply routes, configuration verification, facility access, integration personnel, remaining work and structural dependencies. The evidence status remains distinct from numerical planning assumptions. A process heritage record or a supplier lead does not establish selected-configuration delivery.

The engineering figures of merit are the cost of the declared remaining work and the schedule margin to the specified need date. For a work plan W:

- Direct work cost: C_W = sum of the distinct work-package costs.
- Completion: T_finish is produced by the dependency and shared-resource schedule.
- Schedule margin: M_T = t_n - T_finish. Positive values mean the scenario finishes before its need date.
- Cost margin, when an approved budget exists for precisely that scope: M_C = B_W - C_W. The present export leaves M_C unknown.

The source capability table names `low` and `high` by duration endpoint. The profile explicitly reverses those endpoints when reporting an ordered schedule-margin interval. For the HUMANS quarter target, the lower margin uses the beginning of Q1 and the longer duration; the upper margin uses the end of Q1 and the shorter duration. Separate margins to each quarter boundary are also exported. None of these endpoint ranges is a confidence interval.

The additional development exposure includes direct work, incremental water and a declared holding rate over the schedule. It excludes hardware procurement. Programme procurement or lifecycle estimates are a separate accounting view with overlapping integration scope; a reconciled work breakdown is required before adding them.

The case acceptance tasks and resource calendar come from `data/capability_planning.yaml`. Generic catalogue TRLs and common TRL 9 reference curves do not replace them. Case-specific assessed maturity, supplier commitments, facility bookings and approved budgets remain unresolved in the current evidence.

## Decision interpretation

An architecture with missing required functions is a reference outside the specified functional comparison. An architecture with allocated functions and favourable scenario margins still has unresolved readiness while essential evidence is missing. The profile identifies the next review, procurement or demonstration needed; it does not assign a success probability or rank the uncertainty away.

The lander's open configuration remains a crew-support and physical-mass reference. It is outside the regenerative-capability objective used for the profile comparison. Its missing regeneration functions do not make it an invalid crew-support architecture.

## HUMANS to later flight development

`data/humans_to_flight.csv` is a proposed evidence-development register. It records the ground activity, evidence to capture, possible reuse question and remaining flight-specific work. Every entry is explicitly proposed, not an accomplished test. There are no assumed TRL gains, schedule savings or financial benefits for a future flight programme.

HUMANS can be examined as a place to establish integration practice, characterise air and water processing, measure operating workload and develop specialist capability. Transfer depends on configuration and environmental similarity. Ground commissioning and flight qualification are separate milestones.

## Basis and limits

- [NASA Systems Engineering Handbook, decision analysis](https://www.nasa.gov/reference/6-8-decision-analysis/): measurable criteria, mandatory requirements and uncertainty.
- [NASA Systems Engineering Handbook, Appendix G](https://www.nasa.gov/reference/appendix-g-technology-assessment-insertion/): maturity, advancement work and reassessment of heritage in a changed environment.
- [Narducci, Fusaro and Viola (2025)](https://www.mdpi.com/2226-4310/12/8/682): technology roadmap time and budget estimates and constrained maturation paths.
- [Ridley et al., NASA report ICES-2023-259](https://ntrs.nasa.gov/citations/20230006553): ECLSS testbed development precedent. This is not evidence of HUMANS performance.

The profile is the authors' proposed engineering assessment structure. These sources support its systems-engineering rationale, not an externally validated ERI scale.

The deterministic capability scheduler uses a fixed priority and a single slot for each declared shared resource. The feasible schedule is not proven optimal. Procurement prices, work durations and maturity assumptions require configuration-specific assessment. The HUMANS structure and Q1 targets are author-provided; the precise Q1 deadline remains unspecified. The lander deadline is illustrative. The engineering values are recorded model outputs with generic equipment properties; see [the engineering snapshot](engineering_snapshot.md).

A POMDP can operate on joint capability beliefs and use cost and time objectives while this profile remains unaggregated. See [the decision-layer formulation and missing inputs](pomdp_profile.md).
