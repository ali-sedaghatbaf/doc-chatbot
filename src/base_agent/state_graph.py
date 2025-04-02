from langgraph.graph import END, START, StateGraph

from src.base_agent.states import State
from src.reader_agent.state_graph import reader_graph


def call_reader_agent(state: State):

    return reader_graph.invoke(
        {
            "question": state["messages"][-1].content,
        },
        {"recursion_limit": 100, "thread_id": 1},
    )


def build_state_graph():
    sg_builder = StateGraph(State)
    sg_builder.add_node(call_reader_agent)
    sg_builder.add_edge(START, "call_reader_agent")
    sg_builder.add_edge("call_reader_agent", END)
    graph = sg_builder.compile()
    return graph


graph = build_state_graph()
graph.name = "agent"
