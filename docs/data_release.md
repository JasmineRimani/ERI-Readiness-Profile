# Data release

The public data keep what the paper states and the public-source evidence behind the profile. Three kinds of material are handled differently from the authors' repository.

## Pseudonymised

- **Ecosystem catalogue** (`data/ecosystem_actors.csv`). The authors' catalogue names organisations and links each record to its source. Here each organisation name is replaced by a stable pseudonym (`ORG-E001` for Europe, `ORG-W001` outside Europe) and each record identifier by `REC-0001` and so on. Only the columns the profile uses are kept: region, capability key and supplier role. Source titles, URLs, countries and qualification notes are removed.
- **Route register** (`data/evidence/capability_routes.csv`). Provider names, provider groups and route identifiers are pseudonymised (`Route provider EU-R01`, `EU-R01:co2_removal`). Route kind, region, source, technology match, adaptation gap, configuration acceptance and delivery confirmation are unchanged.
- **References to catalogue records** in `evidence_dates.csv` and `search_log.csv` use the same pseudonyms.

Because regions, capability keys and supplier roles are unchanged, every route status, provider count and evidence state in the profile equals the authors' run; only the names differ.

## Rewritten

- The analyst notes in `capability_sources.json`, the source interpretation in `capability_planning.yaml` and a few search-log notes no longer name companies. Titles and URLs of the public documents are kept, except one whose title names an organisation.
- Record-verification rows of the search log keep their result and date but not the page that identifies the verified record.
- The exploratory POMDP handoff (belief priors) is removed from `capability_planning.yaml`.

## Not included

- ECLSS sizing, lander closure, TRIS and HyCost models and their inputs (technology database, mass-estimating relationships, cost models, TRIS stakeholders and method files, archived model runs);
- the HUMANS project budget breakdown, design interface and sizing handoff;
- the authors' supplier directories, verification sheets and literature-mining registers;
- the exploratory scoring, belief, fragility, tree-search and numerical POMDP studies;
- the paper sources.

The engineering values the profile needs are provided by the [engineering snapshot](engineering_snapshot.md).
