"""Separate evidenced process routes, catalogue leads and delivery commitments.

No broad capability match, commodity label, organisation count or historical
qualification is converted into present supplier availability. Explicit reviewed
function links resolve multifunction equipment without inventing text matches.
"""
import json

import pandas as pd

from eri.io import DATA

SUPPLIER_ROLES = {'system_integrator', 'historical_supplier', 'development_partner',
                  'component_supplier', 'adjacent_industrial_supplier'}
ROUTE_KINDS = {'same_process_heritage', 'same_process_development',
               'similar_process_requires_redesign', 'research_route'}


def reviewed_routes():
    routes = pd.read_csv(DATA / 'evidence/capability_routes.csv', keep_default_na=False, dtype=str)
    sources = json.loads((DATA / 'evidence/capability_sources.json').read_text())['sources']
    if routes.route_id.duplicated().any():
        raise ValueError('Duplicate reviewed route ID')
    for r in routes.itertuples():
        if r.source_id not in sources or r.route_kind not in ROUTE_KINDS:
            raise ValueError(f'Unresolved route provenance: {r.route_id}')
        if r.region not in {'Europe', 'Outside Europe'}:
            raise ValueError('Unknown route region')
        if r.configuration_accepted not in {'true', 'false'} or r.delivery_confirmed not in {'true', 'false'}:
            raise ValueError('Route confirmation must be explicit')
        if r.delivery_confirmed == 'true' and not r.delivery_date:
            raise ValueError('Confirmed delivery needs a date')
    return routes


def candidate_actors(inp, function, capability):
    """Include adjacent industry and reviewed cross-key links; exclude operators."""
    links = reviewed_routes()
    ids = {record for value in links[links.function == function].catalogue_record_ids
           for record in value.split(';') if record}
    actors = inp.actors
    selected = actors[(actors.capability_key == capability) | actors.record_id.isin(ids)]
    return selected[selected.supplier_scope.isin(SUPPLIER_ROLES)].copy()


def routes_for(inp, function, technology_id):
    """Return European routes first and non-European alternatives separately.

    A process-family route still needs a selected product/configuration match.
    Catalogue-only rows retain their weaker evidence status and original IDs.
    """
    mapping = pd.read_csv(DATA / 'evidence/function_capabilities.csv').set_index('function')
    if function not in mapping.index:
        raise ValueError(f'Unmapped function: {function}')
    capability = mapping.loc[function, 'required_capability_key']
    reviewed = reviewed_routes()
    reviewed = reviewed[reviewed.function == function]
    rows, covered = [], set()
    for r in reviewed.itertuples():
        record_ids = [x for x in r.catalogue_record_ids.split(';') if x]
        covered.update(record_ids)
        matched = technology_id in r.technology_ids.split(';')
        rows.append(dict(function=function, technology_id=technology_id,
                         capability_key=capability, provider=r.provider, provider_group=r.provider_group,
                         region=r.region, route_kind=r.route_kind, source_id=r.source_id,
                         catalogue_record_ids=r.catalogue_record_ids,
                         technology_proxy_matched=matched, adaptation_gap=r.adaptation_gap,
                         evidence_status='reviewed_process_route',
                         configuration_accepted=r.configuration_accepted == 'true' and matched,
                         delivery_confirmed=r.delivery_confirmed == 'true' and matched,
                         delivery_date=r.delivery_date if matched else '',
                         independence_status='not_established'))
    for r in candidate_actors(inp, function, capability).itertuples():
        if r.record_id in covered:
            continue
        rows.append(dict(function=function, technology_id=technology_id,
                         capability_key=capability, provider=r.entity_name,
                         provider_group='unresolved:' + r.record_id,
                         region='Europe' if r.is_europe else 'Outside Europe',
                         route_kind='similarity_candidate' if r.supplier_scope == 'adjacent_industrial_supplier' else 'catalogue_lead',
                         source_id='', catalogue_record_ids=r.record_id,
                         technology_proxy_matched=False,
                         adaptation_gap='Product, performance, environment, independence and delivery require review',
                         evidence_status='unreviewed_catalogue_lead', configuration_accepted=False,
                         delivery_confirmed=False, delivery_date='', independence_status='not_established'))
    return sorted(rows, key=lambda r: (r['region'] != 'Europe', r['evidence_status'] != 'reviewed_process_route', r['provider']))


def summarize_routes(rows, region='Europe'):
    """Classify evidence coverage; a zero count never asserts market absence."""
    rows = [r for r in rows if r['region'] == region]
    direct = [r for r in rows if r['evidence_status'] == 'reviewed_process_route'
              and r['route_kind'].startswith('same_process')]
    similar = [r for r in rows if r['route_kind'] in {'similar_process_requires_redesign', 'similarity_candidate'}]
    if direct:
        status = 'process_route_evidenced_configuration_unconfirmed'
    elif similar:
        status = 'similarity_route_requires_assessment'
    elif rows:
        status = 'research_or_catalogue_leads_only'
    else:
        status = 'no_route_found_in_reviewed_scope'
    return dict(route_status=status, candidate_records=len(rows),
                reviewed_provider_groups=len({r['provider_group'] for r in rows if r['evidence_status'] == 'reviewed_process_route'}),
                accepted_configuration_routes=sum(r['configuration_accepted'] for r in rows),
                confirmed_delivery_routes=sum(r['delivery_confirmed'] for r in rows),
                providers='; '.join(dict.fromkeys(r['provider'] for r in rows)),
                independent_supplier_count=None, market_absence_established=False)
