import asyncio
import json
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer, util

from src.adapters import neo4j
from src.models import Document
from src.reader_agent.chains import construction_chain
from src.utils import encode_md5


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


def extract_chunks_from_document(document: Document, chunk_size=2000):
    """
    Extract chunks from document while maintaining proper header hierarchy and context.
    """
    chunks = []
    current_chunk = []
    current_tokens = 0
    current_context = {
        "headers": [],  # List of headers in hierarchical order
        "footnotes": [],
        "captions": []
    }
    
    # Block types that should be kept together
    atomic_blocks = {
        "Table", "Figure", "ListGroup", "Code", "Equation",
        "TableOfContents", "PictureGroup"
    }
    
    # Block types that provide context
    header_types = {"SectionHeader", "PageHeader"}
    context_types = {"Caption", "Footnote"}
    
    def get_header_level(header_text: str) -> int:
        """Get header level from number of leading '#' characters"""
        return len(header_text) - len(header_text.lstrip('#'))
    
    def update_header_hierarchy(new_header: str) -> bool:
        """
        Update header hierarchy and return True if context changed.
        """
        new_level = get_header_level(new_header)
        
        # Remove headers of same or lower level
        existing_headers = current_context["headers"]
        current_context["headers"] = [
            h for h in existing_headers
            if get_header_level(h) < new_level
        ]
        
        # Add new header
        current_context["headers"].append(new_header)
        return existing_headers and existing_headers not in current_context["headers"]
    
    def create_chunk_with_context(page, blocks, chunk_type="TextGroup"):
        """Create a chunk with proper context and header hierarchy"""
        if not blocks:
            return None
            
        # Get text with headers
        header_text = "\n".join(current_context["headers"]) if current_context["headers"] else ""
        block_text = "\n".join(b.text for b in blocks)
        combined_text = f"{header_text}\n\n{block_text}" if header_text else block_text
        
        return {
            "text": combined_text,
            "type": chunk_type,
            "context": {
                "headers": current_context["headers"].copy(),
                "footnotes": current_context["footnotes"].copy(),
                "captions": current_context["captions"].copy()
            },
            "page": page.number,
            "block_positions": [coord for b in blocks for coord in b.position.to_list()]
        }
    
    # Process blocks in order
    for page in document.pages:
        context_changed = False
        
        for block in page.blocks:
            # Update context for headers
            if block.type in header_types:
                context_changed = update_header_hierarchy(block.text)
                continue
                
            # Update context for footnotes and captions
            if block.type in context_types:
                current_context[block.type.lower() + "s"].append(block.text)
                continue
            
            # Handle atomic blocks (keep intact)
            if block.type in atomic_blocks:
                # Save current chunk if exists
                if current_chunk:
                    chunk = create_chunk_with_context(current_chunk)
                    if chunk:
                        chunks.append(chunk)
                    current_chunk = []
                    current_tokens = 0
                
                # Create atomic block chunk
                atomic_chunk = create_chunk_with_context([block], block.type)
                if atomic_chunk:
                    chunks.append(atomic_chunk)
                continue
            
            # Handle regular text blocks
            if block.type in {"Text", "TextInlineMath", "ListItem"}:
                estimated_tokens = len(block.text.split())
                
                # Start new chunk if current is too large or context changed
                if current_tokens + estimated_tokens > chunk_size or context_changed:
                    if current_chunk:
                        chunk = create_chunk_with_context(page,current_chunk)
                        if chunk:
                            chunks.append(chunk)
                        current_chunk = []
                        current_tokens = 0
                    context_changed = False
                
                current_chunk.append(block)
                current_tokens += estimated_tokens
        
        # Add remaining blocks at end of page
        if current_chunk:
            chunk = create_chunk_with_context(page, current_chunk)
            if chunk:
                chunks.append(chunk)
            current_chunk = []
            current_tokens = 0
    
    return chunks


async def process_document(doc: Document):

    # key_element_normalizer = KeyElementNormalizer()
    print("Chunking document")

    chunks = extract_chunks_from_document(doc)
    
    print("Constructing knowledge graph")
    construction_tasks = [
        asyncio.create_task(
            construction_chain().ainvoke(
                {
                    "input": chunk["text"]
                }
            )
        )
        for chunk in chunks
    ]
    
    print("Extracting atomic facts")
    results = await asyncio.gather(*construction_tasks)
    # print("Calculating tf-idf matrix")
    # tf_idf_matrix = calculate_tfidf_matrix(
    #    [chunk["text"] for chunk in chunks],
    #    [
    #        ke
    #        for result in results
    #        for af in result.atomic_facts
    #        for ke in af.key_elements
    #    ],
    # )
    for index, chunk in enumerate(chunks):
        chunk["atomic_facts"] = [
            af for af in results[index].atomic_facts if af is not None
        ]
        
        chunk["id"] = encode_md5(chunk["text"])
        chunk["index"] = index
        # chunk["tfidf"] = tf_idf_matrix[index]

        # key_element_normalizer.sanitize_key_elements(chunk)

        for af in chunk["atomic_facts"]:
            af["id"] = encode_md5(af["atomic_fact"])

    print("Importing data into Neo4j")
    import_query = """
    MERGE (d:Document {id:$document_name})
    SET d.address = $document_address
    WITH d
    UNWIND $data AS row
    MERGE (c:Chunk {id: row.id})
    SET c.text = row.text,
        c.index = row.index,
        c.type = row.type,
        c.block_positions = row.block_positions,
        c.page = row.page
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
    graph.query(
        import_query,
        params={
            "data": chunks,
            "document_name": doc.name,
            "document_address": doc.address,
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
        params={"document_name": doc.name},
    )
