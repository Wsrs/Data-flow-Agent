"""
LangGraph AgentState definition.

Uses TypedDict with Annotated reducers – the canonical LangGraph pattern.
All complex objects are stored as plain dicts (via .model_dump()) so LangGraph
can serialise / checkpoint the state without custom type support.
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, Optional, TypedDict


class AgentState(TypedDict):
    # ── Inputs ────────────────────────────────────────────────────────────────
    job_id: str
    task_config: dict                              # serialised TaskConfig
    data_path: str
    output_path: str

    # ── Agent outputs (append-only via operator.add) ──────────────────────────
    quality_report: Optional[dict]                 # serialised DataQualityReport
    cleaning_scripts: Annotated[list[dict], operator.add]   # serialised CleaningScript list
    execution_results: Annotated[list[dict], operator.add]  # serialised ExecutionResult list

    # ── Control flow ──────────────────────────────────────────────────────────
    status: str           # pending | profiling | engineering | qa | complete | failed | human_review
    retry_count: int
    max_retries: int
    circuit_breaker_triggered: bool

    # ── Audit (append-only) ───────────────────────────────────────────────────
    audit_log: Annotated[list[dict], operator.add]          # serialised AuditEntry list
    error_messages: Annotated[list[str], operator.add]
