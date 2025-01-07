import json
import os

from SPARQLWrapper import JSON, SPARQLWrapper


class WikibaseAdapter:
    def __init__(self):

        self.SPARQL_API = os.environ["SPARQL_API"]
        self.WIKIBASE_BASE_URL = os.environ["WIKIBASE_BASE_URL"]
        self.sparql = SPARQLWrapper(self.SPARQL_API)
        self.sparql.setReturnFormat(JSON)
        self.query_prefix = f"""
            PREFIX wd: <{self.WIKIBASE_BASE_URL}/entity/>
            PREFIX schema: <http://schema.org/>
            PREFIX wdt: <{self.WIKIBASE_BASE_URL}/prop/direct/>H
            PREFIX bd: <http://www.bigdata.com/rdf#>
            PREFIX p: <{self.WIKIBASE_BASE_URL}/prop/>
            PREFIX pq: <{self.WIKIBASE_BASE_URL}/prop/qualifier/>
            PREFIX ps: <{self.WIKIBASE_BASE_URL}/prop/statement/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>"""

    def get_requirement(self, requirement_title: str = "null"):
        self.sparql.setQuery(
            f"""
            {self.query_prefix}
            
            SELECT ?requirement ?requirementLabel ?description ?partOf WHERE {{
              ?requirement wdt:P359 wd:Q47470.  # any entity that is an instance of "Requirement"
              ?requirement rdfs:label {requirement_title}.
              OPTIONAL {{
                ?requirement wdt:P282 ?description
              }}
              OPTIONAL {{
                ?requirement wdt:P119 ?partOf
              }}
            }}
            """
        )

        results = self.sparql.queryAndConvert()
        return results

    def get_gov_doc(self, doc_title: str = "null"):

        self.sparql.setQuery(
            f"""
            {self.query_prefix}

            SELECT ?govDoc ?docLifecycleLabel ?docTypeLabel ?legalEntityLabel ?relatedToLabel ?ownedByOrgUnitLabel ?basedOnLegislationLabel ?approvedByLabel ?approvalDate ?revisionDate ?sitelink WHERE {{
            ?govDoc wdt:P359 wd:Q27697.  # any entity that is an instance of "Governing Document"
            ?govDoc rdfs:label ?govDocLabel.  # get the label of the governing document
            FILTER (lang(?govDocLabel) = "en")  # filter results to only include English labels
            OPTIONAL {{
                ?govDoc wdt:P363 ?ownedByOrgUnit.
                ?ownedByOrgUnit rdfs:label ?ownedByOrgUnitLabel.
                FILTER (lang(?ownedByOrgUnitLabel) = "en")  # filter results to only include English labels
            }}
            OPTIONAL {{
                ?govDoc wdt:P1854 ?docLifecycle.
                ?docLifecycle rdfs:label ?docLifecycleLabel.
            }}
            OPTIONAL {{
                ?govDoc wdt:P1888 ?docType.
                ?docType rdfs:label ?docTypeLabel.
            }}
            OPTIONAL {{
                ?govDoc wdt:P294 ?legalEntity.
                ?legalEntity rdfs:label ?legalEntityLabel.
                FILTER (lang(?legalEntityLabel) = "en")  # filter results to only include English labels
            }}
            OPTIONAL {{
                ?govDoc wdt:P1035 ?relatedTo.
                ?relatedTo rdfs:label ?relatedToLabel.
                FILTER (lang(?relatedToLabel) = "en")  # filter results to only include English labels
            }}
            OPTIONAL {{
                ?govDoc wdt:P703 ?basedOnLegislation.
                ?basedOnLegislation rdfs:label ?basedOnLegislationLabel.
                FILTER (lang(?basedOnLegislationLabel) = "en")  # filter results to only include English     labels
            }}
            OPTIONAL {{
                ?govDoc p:P755 ?approvedByStatement.
                ?approvedByStatement ps:P755 ?approvedBy.
                ?approvedBy rdfs:label ?approvedByLabel.
                FILTER (lang(?approvedByLabel) = "en")  # filter results to only include English labels
                #?approvedByStatement pq:P1789 ?approvalDate.
                #?approvedByStatement pq:P681 ?revisionDate.

                OPTIONAL {{ ?approvedByStatement pq:P1789 ?rawApprovalDate. }}
                OPTIONAL {{ ?approvedByStatement pq:P681 ?rawRevisionDate. }}
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
        results = self.sparql.queryAndConvert()
        return results

    def get_legislation(self, legislation_title: str = "null"):
        self.sparql.setQuery(
            f"""
            {self.query_prefix}
            
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
              ?legislation wdt:P359 wd:Q47632.  # any entity that is an instance of "Legislation"
              ?legislation rdfs:label {legislation_title}.
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
        results = self.sparql.queryAndConvert()
        return results


def read_doc(doc_name):
    wikibase_adapter = WikibaseAdapter()
    doc = wikibase_adapter.get_gov_doc(doc_title=doc_name)
    print(doc)
    return doc
