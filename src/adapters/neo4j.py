from functools import lru_cache

from langchain_community.graphs import Neo4jGraph
from langchain_community.vectorstores import Neo4jVector

from src.agent import chains


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
        embedding=chains.get_embeddings(),
        index_name="keyelements",
        node_label="KeyElement",
        text_node_properties=["id"],
        embedding_node_property="embedding",
        retrieval_query="RETURN node.id AS text, score, {} AS metadata",
    )
    return neo4j_vector
