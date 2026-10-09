# Data release

The public data preserve the numerical inputs and evidence states behind the profile while masking project, country and supplier identifiers in the case data.

## Pseudonymised

- **Terrestrial analog case**. `ANALOGS` is the case identifier throughout the data, code, documentation and generated results. The proposed activity register is `data/analogs_to_flight.csv`, with the field `proposed_analogs_activity`; programme constraints are in `data/evidence/analogs_programme_constraints.json`. The project-specific source identifier and funding/procurement event identifiers use the same pseudonym. The host institution is unnamed in the case description and national procurement record.
- **Country-specific case and search records**. `Country A` and `Country B` are stable anonymous labels, not claims about different real countries. Directory names and national procurement authority names that reveal the countries are withheld. The national procurement framework is withheld (`null`), with that reason recorded explicitly. Original directory edition years, reported entry counts, search results and scope limitations are retained; those counts are inherited evidence-register entries, not newly verified counts. The European and outside-European analysis pools are unchanged.
- **Ecosystem catalogue** (`data/ecosystem_actors.csv`). The authors' catalogue names organisations and links each record to its source. Here each organisation name is replaced by a stable pseudonym (`ORG-E001` for Europe, `ORG-W001` outside Europe) and each record identifier by `REC-0001` and so on. Only the columns the profile uses are kept: region, capability key and supplier role. Source titles, URLs, countries and qualification notes are removed.
- **Route register** (`data/evidence/capability_routes.csv`). Provider names, provider groups and route identifiers are pseudonymised (`Route provider EU-R01`, `EU-R01:co2_removal`). Route kind, region, source, technology match, adaptation gap, configuration acceptance and delivery confirmation are unchanged.
- **References to catalogue records** in `evidence_dates.csv` and `search_log.csv` use the same pseudonyms.

Numerical engineering values, dates, schedule assumptions, costs, catalogue rows, capability keys and supplier roles are preserved. Country-level searches remain limited in scope and cannot establish a shortfall across an entire analysis pool. Route statuses, provider counts and evidence states therefore retain their original meaning.

## Attribution and limits

The original preprint, scholarly publication titles, author/copyright attribution and NASA/ESA source citations retain their correct details. Locations of cited ESA Council meetings are historical source facts and are also retained. Masked directory descriptions are labelled as having their titles withheld; they are not replacement citations.

This is pseudonymisation of the working case data, not complete de-identification of the repository. The retained publications, numerical values and existing Git history may identify the original case. No new scientific sources, observations or replacement-country evidence have been invented.

## Rewritten

- The analyst notes in `capability_sources.json`, the source interpretation in `capability_planning.yaml` and a few search-log notes no longer name companies. Titles and URLs of the public documents are kept, except one whose title names an organisation.
- Record-verification rows of the search log keep their result and date but not the page that identifies the verified record.
- The exploratory POMDP handoff (belief priors) is removed from `capability_planning.yaml`.

## Not included

- ECLSS sizing, lander closure, TRIS and HyCost models and their inputs (technology database, mass-estimating relationships, cost models, TRIS stakeholders and method files, archived model runs);
- the ANALOGS project budget breakdown, design interface and sizing handoff;
- the authors' supplier directories, verification sheets and literature-mining registers;
- the exploratory scoring, belief, fragility, tree-search and numerical POMDP studies;
- the paper sources.

The engineering values the profile needs are provided by the [engineering snapshot](engineering_snapshot.md).
