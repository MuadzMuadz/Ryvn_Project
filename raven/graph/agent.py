"""LangGraph agent definition."""
from __future__ import annotations

from langgraph.graph import StateGraph, END

from raven.graph.state import AgentState
from raven.graph.nodes import retrieve_node, agent_node, tool_node, should_continue


def build_graph():
    g = StateGraph(AgentState)

    g.add_node("retrieve", retrieve_node)
    g.add_node("agent", agent_node)
    g.add_node("tools", tool_node)

    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "agent")
    g.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
    g.add_edge("tools", "agent")

    return g.compile()


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
