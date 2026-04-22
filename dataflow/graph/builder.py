"""Assembles the LangGraph StateGraph and compiles it into a runnable."""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from dataflow.graph.edges import (
    route_after_engineer,
    route_after_profiler,
    route_after_qa,
    route_after_validate,
)
from dataflow.graph.nodes import (
    engineer_node,
    finalize_node,
    human_review_node,
    profiler_node,
    qa_node,
    validate_input_node,
)
from dataflow.schemas.state import AgentState


def build_graph():
    """
    Build and compile the DataFlow Agent graph.

    Returns a CompiledStateGraph that can be invoked with:
        await graph.ainvoke(initial_state_dict)
    """
    g = StateGraph(AgentState)

    # ── Register nodes ────────────────────────────────────────────────────────
    g.add_node("validate_input",   validate_input_node)
    g.add_node("profiler_node",    profiler_node)
    g.add_node("engineer_node",    engineer_node)
    g.add_node("qa_node",          qa_node)
    g.add_node("human_review_node", human_review_node)
    g.add_node("finalize_node",    finalize_node)

    # ── Entry point ───────────────────────────────────────────────────────────
    g.set_entry_point("validate_input")

    # ── Edges ─────────────────────────────────────────────────────────────────
    g.add_conditional_edges("validate_input", route_after_validate,
                            {"profiler_node": "profiler_node", "__end__": END})

    g.add_conditional_edges("profiler_node", route_after_profiler,
                            {"engineer_node": "engineer_node", "__end__": END})

    g.add_conditional_edges("engineer_node", route_after_engineer,
                            {"qa_node": "qa_node", "__end__": END})

    g.add_conditional_edges(
        "qa_node",
        route_after_qa,
        {
            "finalize_node":    "finalize_node",
            "human_review_node": "human_review_node",
            "engineer_node":    "engineer_node",
        },
    )

    g.add_edge("human_review_node", END)
    g.add_edge("finalize_node",     END)

    return g.compile()


# Module-level singleton – lazily compiled on first import
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
