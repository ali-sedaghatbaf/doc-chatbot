import asyncio
from functools import lru_cache

from sentence_transformers import SentenceTransformer, util

from src.adapters import neo4j
from src.agent.chains import construction_chain
from src.models import Chunk, Document
from src.utils import encode_md5, parse_image_layout


@lru_cache
class KeyElementNormalizer:
    def __init__(self):

        self.model = SentenceTransformer(
            "all-MiniLM-L6-v2"
        )  # Model for semantic similarity
        self.threshold = 0.7  # Similarity threshold for normalization

    def _create_normalized_representatives(self, key_elements):
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

    def sanitize_key_elements(self, chunk):
        """Normalize key elements for each atomic fact."""
        existing_key_elements = neo4j.get_all_key_elements()
        afs = chunk["atomic_facts"]
        key_elements = set()
        for af in afs:
            key_elements |= set(af["key_elements"])
        normalized_mapping = self._create_normalized_representatives(
            existing_key_elements + list(key_elements)
        )
        for af in afs:

            af["key_elements"] = [normalized_mapping[ke] for ke in af["key_elements"]]


def extract_chunks_from_document(document: Document):

    chunks = []
    for image_index, image in enumerate(images):
        layout = parse_image_layout(image)
        for block in layout:
            chunk = Chunk(
                text=block.text,
                box=[block.block.x0, block.block.y0, block.block.x1, block.block.y1],
                type=block.type,
                page_number=image_index + 1,
            )
            print(chunk)
        chunks.append(chunk)
        exit()
    return chunks


async def process_document(doc: Document, chunk_size=1000, chunk_overlap=200):

    key_element_normalizer = KeyElementNormalizer()
    print("Chunking document")
    """
    chunking_tasks = [
        asyncio.create_task(
            chunking_chain().ainvoke({"image": image, "page_number": page_number})
            
        )
        for page_number, image in enumerate(doc_images)
    ] 

    chunks = await asyncio.gather(*chunking_tasks)
    """
    # chunks = chunking_chain_with_responses_api()(image=doc_images[1], page_number=1)
    chunks = extract_chunks_from_document(doc_images)
    print("Constructing knowledge graph")
    construction_tasks = [
        asyncio.create_task(construction_chain().ainvoke({"input": chunk["text"]}))
        for chunk in chunks
    ]
    print("Extracting atomic facts")
    results = await asyncio.gather(*construction_tasks)
    print("Calculating tf-idf matrix")
    """ tf_idf_matrix = calculate_tfidf_matrix(
        [chunk["text"] for chunk in chunks],
        [
            ke
            for result in results
            for af in result.atomic_facts
            for ke in af.key_elements
        ],
    ) """
    for index, chunk in enumerate(chunks):
        chunk["atomic_facts"] = [
            af for af in results[index].atomic_facts if af is not None
        ]
        chunk["chunk_id"] = encode_md5(chunk["text"])
        chunk["index"] = index
        # chunk["tfidf"] = tf_idf_matrix[index]

        # key_element_normalizer.sanitize_key_elements(chunk)

        for af in chunk["atomic_facts"]:
            af["id"] = encode_md5(af["atomic_fact"])

    print("Importing data into Neo4j")
    import_query = """
    MERGE (d:Document {id:$document_name})
    SET d.url = $document_url
    WITH d
    UNWIND $data AS row
    MERGE (c:Chunk {id: row.chunk_id})
    SET c.text = row.text,
        c.index = row.index,
        c.type = row.type,
        c.box = row.box,
        c.page = row.page_number

    MERGE (d)-[:HAS_CHUNK]->(c)
    WITH c, row
    UNWIND row.atomic_facts AS af
    MERGE (a:AtomicFact {id: af.id})
    SET a.text = af.atomic_fact
    MERGE (c)-[:HAS_ATOMIC_FACT]->(a)
    WITH c, a, af
    UNWIND af.key_elements AS ke
    MERGE (k:KeyElement {id: ke})
    /*SET k.tfidf = CASE 
        WHEN k.tfidf > c.tfidf[ke] THEN k.tfidf 
        ELSE c.tfidf[ke] 
    END*/
    MERGE (a)-[:HAS_KEY_ELEMENT]->(k)
    """

    graph = neo4j.get_graph()
    graph.query(
        import_query,
        params={
            "data": chunks,
            "document_name": document_name,
            "document_url": documemt_url,
        },
    )
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
