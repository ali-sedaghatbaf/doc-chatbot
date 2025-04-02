from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.reader_agent import kg_explorer
from src.reader_agent.states import InputState, OutputState, OverallState


def build_state_graph():
    sg_builder = StateGraph(OverallState, input=InputState, output=OutputState)
    sg_builder.add_node(kg_explorer.rational_plan_creation)
    sg_builder.add_node(kg_explorer.initial_node_selection)
    sg_builder.add_node(kg_explorer.atomic_fact_check)
    sg_builder.add_node(kg_explorer.chunk_check)
    sg_builder.add_node(kg_explorer.answer_reasoning)
    sg_builder.add_node(kg_explorer.neighbor_select)

    sg_builder.add_edge(START, "rational_plan_creation")
    sg_builder.add_edge("rational_plan_creation", "initial_node_selection")
    sg_builder.add_edge("initial_node_selection", "atomic_fact_check")
    sg_builder.add_conditional_edges(
        "atomic_fact_check",
        atomic_fact_condition,
    )
    sg_builder.add_conditional_edges(
        "chunk_check",
        chunk_condition,
    )
    sg_builder.add_conditional_edges(
        "neighbor_select",
        neighbor_condition,
    )
    sg_builder.add_edge("answer_reasoning", END)

    checkpointer = (
        MemorySaver()
        # if os.getenv("PERSISTANT_CHECKPOINT") == "false"
        # else SqliteSaver(db_path="checkpoints.db")
    )
    graph = sg_builder.compile(checkpointer=checkpointer)
    return graph


def atomic_fact_condition(
    state: OverallState,
) -> Literal["neighbor_select", "chunk_check"]:
    if state.get("chosen_action") == "stop_and_read_neighbor":
        return "neighbor_select"
    elif state.get("chosen_action") == "read_chunk":
        return "chunk_check"


def chunk_condition(
    state: OverallState,
) -> Literal["answer_reasoning", "chunk_check", "neighbor_select"]:
    if state.get("chosen_action") == "termination":
        return "answer_reasoning"
    elif state.get("chosen_action") in [
        "read_subsequent_chunk",
        "read_previous_chunk",
        "search_more",
    ]:
        return "chunk_check"
    elif state.get("chosen_action") == "search_neighbor":
        return "neighbor_select"


def neighbor_condition(
    state: OverallState,
) -> Literal["answer_reasoning", "atomic_fact_check"]:
    if state.get("chosen_action") == "termination":
        return "answer_reasoning"
    elif state.get("chosen_action") == "read_neighbor_node":
        return "atomic_fact_check"


reader_graph = build_state_graph()
reader_graph.name = "reader_agent"
# graph.get_graph().draw_mermaid_png(output_file_path="langgraph.png")
