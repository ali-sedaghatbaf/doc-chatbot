from typing import Dict, List

from rank_bm25 import BM25Okapi

from src.adapters import neo4j
from src.agent import chains
from src.agent.states import InputState, OutputState, OverallState
from src.utils import parse_function


def rational_plan_creation(state: InputState) -> OverallState:
    rational_plan = chains.rational_chain().invoke({"question": state.get("question")})

    print("Step: rational_plan")
    print(f"Rational plan: {rational_plan}")
    return {
        "rational_plan": rational_plan,
        "previous_actions": ["rational_plan"],
    }


def get_potential_nodes(question: str, count=10) -> List[str]:

    similarity_based_data = neo4j.retrieve_key_elements_by_similarity(question, count)
    all_keys = neo4j.get_all_key_elements()
    bm25 = BM25Okapi(all_keys)
    bm25_scores = bm25.get_scores(question.split())
    bm25_based_data = sorted(
        zip(all_keys, bm25_scores), key=lambda item: item[1], reverse=True
    )[:count]
    similarity_based_keys = [key for key, _ in similarity_based_data]
    bm25_based_keys = [key for key, _ in bm25_based_data]
    print(f"Similarity based keys: {similarity_based_keys}")
    print(f"BM25 based keys: {bm25_based_keys}")
    return list(set(similarity_based_keys + bm25_based_keys))


def initial_node_selection(state: OverallState) -> OverallState:

    potential_nodes = get_potential_nodes(state.get("question"))
    initial_nodes = chains.initial_nodes_chain().invoke(
        {
            "question": state.get("question"),
            "rational_plan": state.get("rational_plan"),
            "nodes": potential_nodes,
        }
    )
    # paper uses 5 initial nodes
    check_atomic_facts_queue = [
        el.key_element
        for el in sorted(
            initial_nodes.initial_nodes,
            key=lambda node: node.score,
            reverse=True,
        )
    ][:5]
    return {
        "check_atomic_facts_queue": check_atomic_facts_queue,
        "previous_actions": ["initial_node_selection"],
    }


def get_atomic_facts(key_elements: List[str]) -> List[Dict[str, str]]:
    data = neo4j.get_graph().query(
        """
    MATCH (k:KeyElement)<-[:HAS_KEY_ELEMENT]-(fact)<-[:HAS_ATOMIC_FACT]-(chunk)
    WHERE k.id IN $key_elements
    RETURN distinct chunk.id AS chunk_id, fact.text AS text
    """,
        params={"key_elements": key_elements},
    )
    return data


def get_neighbors_by_key_element(key_elements):
    print(f"Key elements: {key_elements}")
    data = neo4j.get_graph().query(
        """
    MATCH (k:KeyElement)<-[:HAS_KEY_ELEMENT]-()-[:HAS_KEY_ELEMENT]->(neighbor)
    WHERE k.id IN $key_elements AND NOT neighbor.id IN $key_elements
    WITH neighbor, count(*) AS count
    ORDER BY count DESC LIMIT 50
    RETURN collect(neighbor.id) AS possible_candidates
    """,
        params={"key_elements": key_elements},
    )
    return data


def atomic_fact_check(state: OverallState) -> OverallState:

    atomic_facts = get_atomic_facts(state.get("check_atomic_facts_queue"))
    print("-" * 20)
    print(f"Step: atomic_fact_check")
    print(f"Reading atomic facts about: {state.get('check_atomic_facts_queue')}")
    atomic_facts_results = chains.atomic_fact_chain().invoke(
        {
            "question": state.get("question"),
            "rational_plan": state.get("rational_plan"),
            "notebook": state.get("notebook"),
            "previous_actions": state.get("previous_actions"),
            "atomic_facts": atomic_facts,
        }
    )

    notebook = atomic_facts_results.updated_notebook
    print(
        f"Rational for next action after atomic check: {atomic_facts_results.rational_next_action}"
    )
    chosen_action = parse_function(atomic_facts_results.chosen_action)
    print(f"Chosen action: {chosen_action}")
    response = {
        "notebook": notebook,
        "chosen_action": chosen_action.get("function_name"),
        "check_atomic_facts_queue": [],
        "previous_actions": [
            f"atomic_fact_check({state.get('check_atomic_facts_queue')})"
        ],
    }
    if chosen_action.get("function_name") == "stop_and_read_neighbor":
        neighbors = get_neighbors_by_key_element(state.get("check_atomic_facts_queue"))
        response["neighbor_check_queue"] = neighbors
    elif chosen_action.get("function_name") == "read_chunk":
        response["check_chunks_queue"] = chosen_action.get("arguments")[0]
    return response


def get_subsequent_chunk_id(chunk_id: str):
    data = neo4j.get_graph().query(
        """
    MATCH (c:Chunk)-[:NEXT]->(next)
    WHERE c.id = $id
    RETURN next.id AS next
    """,
        params={"id": chunk_id},
    )
    return data


def get_previous_chunk_id(chunk_id: str):
    data = neo4j.get_graph().query(
        """
    MATCH (c:Chunk)<-[:NEXT]-(previous)
    WHERE c.id = $id
    RETURN previous.id AS previous
    """,
        params={"id": chunk_id},
    )
    return data


def get_chunk(chunk_id: str) -> List[Dict[str, str]]:
    data = neo4j.get_graph().query(
        """
    MATCH (c:Chunk)
    WHERE c.id = $chunk_id
    RETURN c.text AS text
    """,
        params={"chunk_id": chunk_id},
    )
    return data


def get_document(chunk_id: str) -> str:
    doc = neo4j.get_graph().query(
        """
    MATCH (c:Chunk)<-[:HAS_CHUNK]-(d:Document)
    WHERE c.id = $chunk_id
    RETURN d.url AS url, d.id AS name
    """,
        params={"chunk_id": chunk_id},
    )
    return doc


def chunk_check(state: OverallState) -> OverallState:
    check_chunks_queue = state.get("check_chunks_queue")
    chunk_id = check_chunks_queue.pop(0)
    print("-" * 20)
    print(f"Step: read chunk({chunk_id})")

    chunks_text = get_chunk(chunk_id)
    read_chunk_results = chains.chunk_read_chain().invoke(
        {
            "question": state.get("question"),
            "rational_plan": state.get("rational_plan"),
            "notebook": state.get("notebook"),
            "previous_actions": state.get("previous_actions"),
            "chunk": chunks_text,
        }
    )

    notebook = read_chunk_results.updated_notebook
    print(
        f"Rational for next action after reading chunks: {read_chunk_results.rational_next_move}"
    )
    chosen_action = parse_function(read_chunk_results.chosen_action)
    print(f"Chosen action: {chosen_action}")
    print(f"\nNotebook content: {state.get('notebook')}")
    response = {
        "notebook": notebook,
        "chosen_action": chosen_action.get("function_name"),
        "previous_actions": [f"read_chunks({chunk_id})"],
    }
    if chosen_action.get("function_name") == "read_subsequent_chunk":
        subsequent_id = get_subsequent_chunk_id(chunk_id)
        check_chunks_queue.append(subsequent_id)
    elif chosen_action.get("function_name") == "read_previous_chunk":
        previous_id = get_previous_chunk_id(chunk_id)
        check_chunks_queue.append(previous_id)
    elif chosen_action.get("function_name") == "search_more":
        # Go over to next chunk
        # Else explore neighbors
        if not check_chunks_queue:
            response["chosen_action"] = "search_neighbor"
            # Get neighbors/use vector similarity
            print(f"Neighbor rational: {read_chunk_results.rational_next_move}")
            neighbors = get_potential_nodes(read_chunk_results.rational_next_move)
            response["neighbor_check_queue"] = neighbors

    response["check_chunks_queue"] = check_chunks_queue

    context = state.get("context", [])
    context.append(chunk_id)
    response["context"] = context

    return response


def neighbor_select(state: OverallState) -> OverallState:
    print("-" * 20)
    print("Step: neighbor select")
    print(f"Possible candidates: {state.get('neighbor_check_queue')}")
    neighbor_select_results = chains.neighbor_select_chain().invoke(
        {
            "question": state.get("question"),
            "rational_plan": state.get("rational_plan"),
            "notebook": state.get("notebook"),
            "nodes": state.get("neighbor_check_queue"),
            "previous_actions": state.get("previous_actions"),
        }
    )
    print(
        f"Rational for next action after selecting neighbor: {neighbor_select_results.rational_next_move}"
    )
    chosen_action = parse_function(neighbor_select_results.chosen_action)
    print(f"Chosen action: {chosen_action}")
    print(f"\nNotebook content: {state.get('notebook')}")
    # Empty neighbor select queue
    response = {
        "chosen_action": chosen_action.get("function_name"),
        "neighbor_check_queue": [],
        "previous_actions": [
            f"neighbor_select({chosen_action.get('arguments', [''])[0] if chosen_action.get('arguments', ['']) else ''})"
        ],
    }
    if chosen_action.get("function_name") == "read_neighbor_node":
        response["check_atomic_facts_queue"] = [chosen_action.get("arguments")[0]]
    return response


def answer_reasoning(state: OverallState) -> OutputState:
    print("-" * 20)
    print("Step: Answer Reasoning")
    final_answer = chains.answer_reasoning_chain().invoke(
        {"question": state.get("question"), "notebook": state.get("notebook")}
    )
    context = state.get("context")
    citations = {}
    for chunk_id in context:
        doc = get_document(chunk_id)[0]

        citations[doc["name"]] = doc["url"]

    print(f"Final answer: {final_answer.final_answer}")
    print(f"\nNotebook content: {state.get('notebook')}")
    return {
        "answer": final_answer.final_answer,
        "analysis": final_answer.analyze,
        "previous_actions": ["answer_reasoning"],
        "citations": citations,
    }
