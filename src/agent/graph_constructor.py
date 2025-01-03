import asyncio
from datetime import datetime
from functools import lru_cache

from langchain_text_splitters import TokenTextSplitter
from sentence_transformers import SentenceTransformer, util

from src.adapters import neo4j
from src.agent.chains import construction_chain
from src.utils import encode_md5

@lru_cache
class KeyElementNormalizer:
    def __init__(self):
        self.neo4j_graph = neo4j.get_graph()
        self.model = SentenceTransformer(
            "all-MiniLM-L6-v2"
        )  # Model for semantic similarity
        self.threshold = 0.7  # Similarity threshold for normalization

    def _normalize_key_elements(self, key_elements):
        """Normalize a list of keywords using semantic similarity."""
        embeddings = self.model.encode(key_elements, convert_to_tensor=True)
        similarity_matrix = util.cos_sim(embeddings, embeddings)

        groups = []
        used_indices = set()

        for i, key_element in enumerate(key_elements):
            if i in used_indices:
                continue
            group = [key_element]
            used_indices.add(i)
            for j, score in enumerate(similarity_matrix[i]):
                if j != i and score >= self.threshold and j not in used_indices:
                    group.append(key_elements[j])
                    used_indices.add(j)
            groups.append(group)

        # Return a mapping of each key element to its normalized representative
        normalized_mapping = {ke: group[0] for group in groups for ke in group}
        return normalized_mapping

    def _fetch_existing_key_elements(self):
        """Fetch all existing key elements from the Neo4j database."""
        query = "MATCH (k:KeyElement) RETURN k.id AS id"
        result = self.neo4j_graph.query(query)
        return [record["id"] for record in result]

    def normalize_af_key_elements(self, af_key_elements):
        """Normalize key elements for each atomic fact."""
        existing_key_elements = self._fetch_existing_key_elements()
        for af, key_elements in af_key_elements.items():
            normalized_mapping = self._normalize_key_elements(
                existing_key_elements + key_elements
            )
            af_key_elements[af] = [normalized_mapping[ke] for ke in key_elements]


async def process_document(text, document_name, chunk_size=2000, chunk_overlap=200):
    start = datetime.now()
    print(f"Started extraction at: {start}")
    text_splitter = TokenTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    # text_splitter = SemanticChunker(get_embeddings())
    texts = text_splitter.split_text(text)
    print(f"Total text chunks: {len(texts)}")
    tasks = [
        asyncio.create_task(construction_chain().ainvoke({"input": chunk_text}))
        for index, chunk_text in enumerate(texts)
    ]
    results = await asyncio.gather(*tasks)
    print(f"Finished LLM extraction after: {datetime.now() - start}")
    docs = [el.dict() for el in results]
    af_key_elements = {}
    for index, doc in enumerate(docs):
        doc["chunk_id"] = encode_md5(texts[index])
        doc["chunk_text"] = texts[index]
        doc["index"] = index
        for af in doc["atomic_facts"]:
            af["id"] = encode_md5(af["atomic_fact"])
            af_key_elements[af["id"]] = af["key_elements"]  # Collect key elements
    
    # Normalize key elements
    key_element_normalizer = KeyElementNormalizer()
    key_element_normalizer.normalize_af_key_elements(af_key_elements)

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

    graph = neo4j.get_graph()
    graph.query(import_query, params={"data": docs, "document_name": document_name})
    # Create next relationships between chunks
    graph.query(
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
