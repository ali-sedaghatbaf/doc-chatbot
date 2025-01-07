import os

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SQLiteSaver
from langgraph.graph import END, START, StateGraph

from src.agent import graph_explorer as kg_explorer
from src.agent.states import InputState, OutputState, OverallState

def build_state_graph():
    sg_builder = StateGraph(OverallState, input=InputState, output=OutputState)
    sg_builder.add_node(kg_explorer.rational_plan_node)
    sg_builder.add_node(kg_explorer.initial_node_selection)
    sg_builder.add_node(kg_explorer.atomic_fact_check)
    sg_builder.add_node(kg_explorer.chunk_check)
    sg_builder.add_node(kg_explorer.answer_reasoning)
    sg_builder.add_node(kg_explorer.neighbor_select)

    sg_builder.add_edge(START, "rational_plan_node")
    sg_builder.add_edge("rational_plan_node", "initial_node_selection")
    sg_builder.add_edge("initial_node_selection", "atomic_fact_check")
    sg_builder.add_conditional_edges(
        "atomic_fact_check",
        kg_explorer.atomic_fact_condition,
    )
    sg_builder.add_conditional_edges(
        "chunk_check",
        kg_explorer.chunk_condition,
    )
    sg_builder.add_conditional_edges(
        "neighbor_select",
        kg_explorer.neighbor_condition,
    )
    sg_builder.add_edge("answer_reasoning", END)

    checkpointer = (
        MemorySaver()
        if os.getenv("PERSISTANT_CHECKPOINT") == "false"
        else SQLiteSaver(db_path="checkpoints.db")
    )
    graph = sg_builder.compile(checkpointer=checkpointer)
    return graph

graph = build_state_graph()
# graph.get_graph().draw_mermaid_png(output_file_path="langgraph.png")
