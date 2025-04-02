from functools import lru_cache

from langchain_community.graphs import Neo4jGraph
from langchain_community.vectorstores import Neo4jVector

from src.reader_agent import chains


@lru_cache
def get_graph():
    graph = Neo4jGraph(refresh_schema=False)

    graph.query("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE")
    graph.query(
        "CREATE CONSTRAINT IF NOT EXISTS FOR (c:AtomicFact) REQUIRE c.id IS UNIQUE"
    )
    graph.query(
        "CREATE CONSTRAINT IF NOT EXISTS FOR (c:KeyElement) REQUIRE c.id IS UNIQUE"
    )
    graph.query(
        "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE"
    )
    return graph


@lru_cache
def get_vector():
    neo4j_vector = Neo4jVector.from_existing_graph(
        embedding=chains.get_openai_embeddings(),
        index_name="keyelements",
        node_label="KeyElement",
        text_node_properties=["id"],
        embedding_node_property="embedding",
        retrieval_query="RETURN node.id AS text, score, {tfidf: Null} AS metadata",
    )
    return neo4j_vector


@lru_cache
def get_all_key_elements():
    """Fetch all existing key elements from the Neo4j database."""
    query = "MATCH (k:KeyElement) RETURN k.id AS id"
    result = get_graph().query(query)
    return [record["id"] for record in result]


def retrieve_key_elements_by_similarity(question, count):
    data = get_vector().similarity_search_with_relevance_scores(question, k=count)

    return [(record[0].page_content, record[1]) for record in data]
