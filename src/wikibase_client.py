import json
import os

from SPARQLWrapper import JSON, SPARQLWrapper

governing_doc_type_id = "Q27697"
instance_of_property_id = "P359"
owned_by_property_id = "P363"
documentation_lifecycle_property_id = "P1854"
type_property_id = "P1888"
legal_entity_property_id = "P294"
related_to_property_id = "P1035"
based_on_legislation_property_id = "P703"
approved_by_property_id = "P755"
approval_date_property_id = "P1789"
next_revision_date_property_id = "P681"
legislation_type_id = "Q47632"
external_requirement_type_id = "Q47470"
description_property_id = "P282"
part_of_property_id = "P119"
# additional required properties
purpose_property_id = "P426"
access_policy_property_id = "P557"
change_policy_property_id = "P764"
regulatory_disclosure_requirement_property_id = "P1953"
WIKIBASE_BASE_URL = {
    "production": "https://knowledgegraph.klarna.net",
    "playground": "https://knowledgegraph.playground.klarna.net",
}
SPARQL_API = {
    "production": "https://pinkbase-proxy-eu.production.c2c.klarna.net/sparql",
    "playground": "https://pinkbase-proxy-eu.playground.c2c.klarna.net/sparql",
}


def get_requirements(env: str = "playground"):
    SPARQL_API = json.loads(os.getenv("SPARQL_API"))[env]
    WIKIBASE_BASE_URL = json.loads(os.getenv("WIKIBASE_BASE_URL"))[env]
    sparql = SPARQLWrapper(SPARQL_API)
    sparql.setReturnFormat(JSON)
    sparql.setQuery(
        f"""
        PREFIX wd: <{WIKIBASE_BASE_URL}/entity/>
        PREFIX schema: <http://schema.org/>
        PREFIX wdt: <{WIKIBASE_BASE_URL}/prop/direct/>H
        PREFIX bd: <http://www.bigdata.com/rdf#>
        PREFIX p: <{WIKIBASE_BASE_URL}/prop/>
        PREFIX pq: <{WIKIBASE_BASE_URL}/prop/qualifier/>
        PREFIX ps: <{WIKIBASE_BASE_URL}/prop/statement/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        
        SELECT ?requirement ?requirementLabel ?description ?partOf WHERE {{
          ?requirement wdt:{instance_of_property_id} wd:{external_requirement_type_id}.  # any entity that is an instance of "Requirement"
          ?requirement rdfs:label ?requirementLabel.
          OPTIONAL {{
            ?requirement wdt:{description_property_id} ?description
          }}
          OPTIONAL {{
            ?requirement wdt:{part_of_property_id} ?partOf
          }}
        }}
        """
    )

    results = sparql.queryAndConvert()
    return results


def get_gov_docs(env: str = "playground"):
    SPARQL_API = json.loads(os.getenv("SPARQL_API"))[env]
    WIKIBASE_BASE_URL = json.loads(os.getenv("WIKIBASE_BASE_URL"))[env]
    sparql = SPARQLWrapper(SPARQL_API)
    sparql.setReturnFormat(JSON)

    sparql.setQuery(
        f"""
    PREFIX wd: <{WIKIBASE_BASE_URL}/entity/>
    PREFIX schema: <http://schema.org/>
    PREFIX wdt: <{WIKIBASE_BASE_URL}/prop/direct/>
    PREFIX bd: <http://www.bigdata.com/rdf#>
    PREFIX p: <{WIKIBASE_BASE_URL}/prop/>
    PREFIX pq: <{WIKIBASE_BASE_URL}/prop/qualifier/>
    PREFIX ps: <{WIKIBASE_BASE_URL}/prop/statement/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    SELECT ?govDoc ?govDocLabel ?docLifecycleLabel ?docTypeLabel ?legalEntityLabel ?relatedToLabel ?ownedByOrgUnitLabel ?basedOnLegislationLabel ?approvedByLabel ?approvalDate ?revisionDate ?sitelink WHERE {{
        ?govDoc wdt:{instance_of_property_id} wd:{governing_doc_type_id}.  # any entity that is an instance of "Governing Document"
        ?govDoc rdfs:label ?govDocLabel.  # get the label of the governing document
        FILTER (lang(?govDocLabel) = "en")  # filter results to only include English labels
        OPTIONAL {{
            ?govDoc wdt:{owned_by_property_id} ?ownedByOrgUnit.
            ?ownedByOrgUnit rdfs:label ?ownedByOrgUnitLabel.
            FILTER (lang(?ownedByOrgUnitLabel) = "en")  # filter results to only include English labels
        }}
        OPTIONAL {{
            ?govDoc wdt:{documentation_lifecycle_property_id} ?docLifecycle.
            ?docLifecycle rdfs:label ?docLifecycleLabel.
        }}
        OPTIONAL {{
            ?govDoc wdt:{type_property_id} ?docType.
            ?docType rdfs:label ?docTypeLabel.
        }}
        OPTIONAL {{
            ?govDoc wdt:{legal_entity_property_id} ?legalEntity.
            ?legalEntity rdfs:label ?legalEntityLabel.
            FILTER (lang(?legalEntityLabel) = "en")  # filter results to only include English labels
        }}
        OPTIONAL {{
            ?govDoc wdt:{related_to_property_id} ?relatedTo.
            ?relatedTo rdfs:label ?relatedToLabel.
            FILTER (lang(?relatedToLabel) = "en")  # filter results to only include English labels
        }}
        OPTIONAL {{
            ?govDoc wdt:{based_on_legislation_property_id} ?basedOnLegislation.
            ?basedOnLegislation rdfs:label ?basedOnLegislationLabel.
            FILTER (lang(?basedOnLegislationLabel) = "en")  # filter results to only include English     labels
        }}
        OPTIONAL {{
            ?govDoc p:{approved_by_property_id} ?approvedByStatement.
            ?approvedByStatement ps:{approved_by_property_id} ?approvedBy.
            ?approvedBy rdfs:label ?approvedByLabel.
            FILTER (lang(?approvedByLabel) = "en")  # filter results to only include English labels
            #?approvedByStatement pq:{approval_date_property_id} ?approvalDate.
            #?approvedByStatement pq:{next_revision_date_property_id} ?revisionDate.

            OPTIONAL {{ ?approvedByStatement pq:{approval_date_property_id} ?rawApprovalDate. }}
            OPTIONAL {{ ?approvedByStatement pq:{next_revision_date_property_id} ?rawRevisionDate. }}
        }}
        OPTIONAL {{
            ?sitelink schema:about ?govDoc.
            ?sitelink schema:isPartOf <https://wiki.klarna.net/>.
        }}
        BIND(IF(BOUND(?rawApprovalDate), xsd:date(?rawApprovalDate), "") AS ?approvalDate)
        BIND(IF(BOUND(?rawRevisionDate), xsd:date(?rawRevisionDate), "") AS ?revisionDate)
    }}
    """
    )
    results = sparql.queryAndConvert()
    return results


def get_legislations(env: str = "playground"):
    SPARQL_API = json.loads(os.getenv("SPARQL_API"))[env]
    WIKIBASE_BASE_URL = json.loads(os.getenv("WIKIBASE_BASE_URL"))[env]
    sparql = SPARQLWrapper(SPARQL_API)
    sparql.setReturnFormat(JSON)
    sparql.setQuery(
        f"""
        PREFIX wd: <{WIKIBASE_BASE_URL}/entity/>
        PREFIX wdt: <{WIKIBASE_BASE_URL}/prop/direct/>
        PREFIX bd: <http://www.bigdata.com/rdf#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT 
                        ?legislation 
                        ?legislationLabel
                        ?typeLabel
                        ?explanation 
                        ?url
                        ?language
                        (GROUP_CONCAT(DISTINCT ?jurisdiction; SEPARATOR=", ") AS ?jurisdictions )
                        (GROUP_CONCAT(DISTINCT ?authorityLabel; SEPARATOR=", ") AS ?authorities)
                        (GROUP_CONCAT(DISTINCT ?authorityDescription; SEPARATOR=", ") AS ?authorityDescriptions)
                        (GROUP_CONCAT(DISTINCT ?legalAreaLabel; SEPARATOR=", ") AS ?legalAreas)
                        (GROUP_CONCAT(DISTINCT ?impact; SEPARATOR=", ") AS ?impacts)
                        WHERE {{
          ?legislation wdt:{instance_of_property_id} wd:{legislation_type_id}.  # any entity that is an instance of "Legislation"
          ?legislation rdfs:label ?legislationLabel.
          OPTIONAL {{
            ?legislation wdt:P1948 ?explanation
          }}
          OPTIONAL {{
            ?legislation wdt:P1888 ?type .
            ?type rdfs:label ?typeLabel
          }}
          OPTIONAL {{
            ?legislation wdt:P120 ?url
          }}
          OPTIONAL {{
            ?legislation wdt:P746 ?language
          }}
          OPTIONAL {{
            ?legislation wdt:P291 ?jurisdiction
          }}
          OPTIONAL {{
            ?legislation wdt:P1737 ?authority. 
            ?authority rdfs:label ?authorityLabel
            OPTIONAL {{
              ?authority wdt:P282 ?authorityDescription
            }}
          }}
          OPTIONAL {{
            ?legislation wdt:P1501 ?legalArea .
            ?legalArea rdfs:label ?legalAreaLabel
          }}
          OPTIONAL {{
            ?legislation wdt:P886 ?impact
          }}
        }} GROUP BY ?legislation ?legislationLabel ?typeLabel ?explanation ?url ?language
        """
    )
    results = sparql.queryAndConvert()
    return results
