"""Conditional edge routing functions for the LangGraph workflow."""
from __future__ import annotations


def route_after_validate(state: dict) -> str:
    if state.get("status") == "failed":
        return "__end__"
    return "profiler_node"


def route_after_profiler(state: dict) -> str:
    if state.get("status") == "failed":
        return "__end__"
    return "engineer_node"


def route_after_engineer(state: dict) -> str:
    if state.get("status") == "failed":
        return "__end__"
    return "qa_node"


def route_after_qa(state: dict) -> str:
    status = state.get("status", "")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)

    if status == "complete":
        return "finalize_node"

    if status == "human_review" or state.get("circuit_breaker_triggered"):
        return "human_review_node"

    # Retry limit reached → escalate to human review
    if retry_count >= max_retries:
        return "human_review_node"

    # Still failing but retries remaining → back to engineer
    return "engineer_node"
