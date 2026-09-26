# Capability planning for the readiness profile

The capability layer answers two engineering questions: what regenerative capability is allocated to the lunar lander and to HUMANS, and what work and supply evidence would be needed to make it available? Run `python scripts/run_capabilities.py` (or `eri-profile capabilities`) and open `outputs/capabilities/index.html`.

The lander is the flight case; HUMANS is the terrestrial crew-support and air and water experiment case. Integrated and distributed air-processing candidates have equivalent declared functional scope, with membrane water processing and an explicit T-WR-006 polishing allocation. These allocations are generic study designs requiring validation. The open lander remains a minimum-support reference; it cannot fulfil the full regenerative objective. Urine, brine, food and biological closure are outside this comparison.

## Computation and inputs

`data/capability_planning.yaml` declares start and need dates, functional requirements, resource reserves, configuration-maturity scenarios, work profiles and single-slot resource calendars. Every numerical scenario input is marked as an assumption. Configuration-specific assessed TRLs remain null. The source register records access limitations; extracted measurements are retained in `evidence_observations.csv` with test context and transfer limits, not silently installed as selected-equipment parameters.

The engineering values (carried water, ECLSS mass, power, volume and lander wet mass) come from the [engineering snapshot](engineering_snapshot.md). The shortfall experiment lowers the air feedwater credit or the eligible-stream water recovery by 0.10 from the declared 0.40 and 0.95 references. Water and wet-mass differences are compared with the case's declared reserves. Redesign is a conditional work package; lower recovery can consume spare capacity without adding schedule work.

For each actual core technology allocation, the work graph includes procurement, any remaining breadboard and relevant-environment demonstration stages, adaptation and qualification. Multifunction equipment is counted once. An enabling-equipment package and integrated acceptance are also required. For HUMANS, procurement waits for the structure-availability milestone. The stage thresholds and durations are analyst scenarios, not a statistical development law. Unmeasured maturity can instead be represented by an unknown-duration assessment task.

For a chosen duration endpoint, an activity starts at the maximum of prerequisite finishes, its release time, and resource availability or previous booking. Its finish is start plus duration. The same fixed topological priority applies to both endpoints. This produces a reproducible feasible resource schedule, not an optimum. Unknown duration or access propagates to dependent work and subsequent users of the resource; independent branches remain calculable. Evidence-only execution removes analyst durations and calendars, so its dates remain unresolved for the current inputs. Even a documented work estimate is not a supplier commitment or an operational release.

Development exposure sums work costs, incremental water cost and holding cost over elapsed development time. Hardware procurement prices are excluded because selected-unit quotations are missing. The result is neither whole-programme cost nor a confidence interval.

The two cases each use all 64 combinations of six stresses: air and water recovery shortfalls, air and water maturity stages, supplier delay and shared-air-service interruption. `driver_effects.csv` reports mean high-minus-low contrasts across matched factorial settings, separately by metric and case. Interval midpoints are comparison statistics only. Ranks depend on declared stress sizes and resources; zero effect can reflect spare time or unchanged work stages. There is no global technology ranking that is independent of architecture and assumptions.

`dependency_losses.csv` separately reports each hardware or shared-service loss and the essential functions it blocks. Required functional dependencies use AND semantics; multiple installed hardware allocations for a function use OR semantics. These are structural loss diagnostics, not failure rates, reliability certification or proof of actual redundancy in the selected equipment.

## Sources and what they establish

- [NASA Systems Engineering Handbook, Appendix G](https://www.nasa.gov/wp-content/uploads/2018/09/nasa_systems_engineering_handbook_0.pdf): assess maturity and advancement difficulty for the relevant configuration and environment. It does not supply universal TRL-to-day conversions.
- [ESA ACLS on-orbit report, ICES-2020-510](https://hdl.handle.net/2346/86479): integrated European air-process heritage and commissioning and interface constraints. The shared vent is a reason to model shared services, not evidence that either proposed case has that exact defect.
- [ESA Bulletin 97, Water Recovery in Space](https://www.esa.int/esapub/bulletin/bullet97/tamponne.pdf): historical UF/RO measurements and quality limitations. This is a different process from the selected membrane proxy, so its recovery result is not transferred.

The complete [source register](../data/evidence/capability_sources.json) lists every document behind the routes and observations, what each establishes and its access limits. No present delivery commitment, selected-configuration lead time, verified resource margin, facility booking or calibrated intervention probability was established by this review.

## European supply and blockers

`technology_gaps.csv` leads with European process-route evidence and lists non-European alternatives separately. `supplier_routes.csv` retains source IDs, catalogue links, technology-proxy matching, adaptation gaps, configuration acceptance and delivery confirmation. Similarity denotes work requiring assessment; it is not equivalence or permission to use equipment. Provider grouping avoids interpreting duplicated records as independent sources. Independence remains unknown. Provider names are pseudonymised in this release; see [data release](data_release.md).

"No route found in reviewed scope" is an evidence gap, not a claim that no supplier exists. Documented process routes still need configuration and delivery confirmation. Enabling functions such as polishing and monitoring retain their own evidence gaps instead of disappearing behind the air and water headline.

## Tests

Tests cover scheduling with parallel branches and shared resources, unknown propagation, invalid graphs and bounds, physical reserve crossings, unchanged work when spare capacity exists, high-TRL procurement and qualification, the structure prerequisite, equivalent full-capability scope, supplier roles, cross-function routes, installed redundancy and the reproduction of the published results. Every exporter writes a `manifest.json` with code, input and output hashes.
