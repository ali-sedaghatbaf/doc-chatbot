import asyncio
from datetime import datetime
from functools import lru_cache

from langchain_community.graphs import Neo4jGraph
from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import TokenTextSplitter

from src.chains import construction_chain, get_embeddings
from src.utils import encode_md5


@lru_cache
class GraphCnstructor:
    def __init__(self) -> None:
        self.graph = Neo4jGraph(refresh_schema=False)

        self.graph.query(
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE"
        )
        self.graph.query(
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:AtomicFact) REQUIRE c.id IS UNIQUE"
        )
        self.graph.query(
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:KeyElement) REQUIRE c.id IS UNIQUE"
        )
        self.graph.query(
            "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE"
        )
        self.construction_chain = construction_chain()

    async def process_document(
        self, text, document_name, chunk_size=2000, chunk_overlap=200
    ):
        start = datetime.now()
        print(f"Started extraction at: {start}")
        text_splitter = TokenTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        #text_splitter = SemanticChunker(get_embeddings())
        texts = text_splitter.split_text(text)
        print(f"Total text chunks: {len(texts)}")
        tasks = [
            asyncio.create_task(self.construction_chain.ainvoke({"input": chunk_text}))
            for index, chunk_text in enumerate(texts)
        ]
        results = await asyncio.gather(*tasks)
        print(f"Finished LLM extraction after: {datetime.now() - start}")
        docs = [el.dict() for el in results]
        for index, doc in enumerate(docs):
            doc["chunk_id"] = encode_md5(texts[index])
            doc["chunk_text"] = texts[index]
            doc["index"] = index
            for af in doc["atomic_facts"]:
                af["id"] = encode_md5(af["atomic_fact"])
        # Import chunks/atomic facts/key elements

        import_query = """
        MERGE (d:Document {id:$document_name})
        WITH d
        UNWIND $data AS row
        MERGE (c:Chunk {id: row.chunk_id})
        SET c.text = row.chunk_text,
            c.index = row.index,
            c.document_name = row.document_name
        MERGE (d)-[:HAS_CHUNK]->(c)
        WITH c, row
        UNWIND row.atomic_facts AS af
        MERGE (a:AtomicFact {id: af.id})
        SET a.text = af.atomic_fact
        MERGE (c)-[:HAS_ATOMIC_FACT]->(a)
        WITH c, a, af
        UNWIND af.key_elements AS ke
        MERGE (k:KeyElement {id: ke})
        MERGE (a)-[:HAS_KEY_ELEMENT]->(k)
        """
        self.graph.query(
            import_query, params={"data": docs, "document_name": document_name}
        )
        # Create next relationships between chunks
        self.graph.query(
            """MATCH (c:Chunk)<-[:HAS_CHUNK]-(d:Document)
        WHERE d.id = $document_name
        WITH c ORDER BY c.index WITH collect(c) AS nodes
        UNWIND range(0, size(nodes) -2) AS index
        WITH nodes[index] AS start, nodes[index + 1] AS end
        MERGE (start)-[:NEXT]->(end)
        """,
            params={"document_name": document_name},
        )
        print(f"Finished import at: {datetime.now() - start}")
