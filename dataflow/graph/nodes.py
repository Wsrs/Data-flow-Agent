"""
LangGraph node functions.

Each function receives the full AgentState dict and returns a partial dict
of fields to update.  LangGraph merges the return value into the state via
the registered reducers (operator.add for list fields).
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from dataflow.agents.engineer import EngineerAgent
from dataflow.agents.profiler import ProfilerAgent
from dataflow.agents.qa import QAAgent
from dataflow.observability.logger import get_logger
from dataflow.sandbox import get_sandbox
from dataflow.schemas.execution import AuditEntry
from dataflow.schemas.report import DataQualityReport
from dataflow.schemas.task_config import TaskConfig

logger = get_logger(__name__)


def _entry(node: str, status: str, detail: str, job_id: str) -> dict:
    return AuditEntry(
        node=node, status=status, detail=detail, job_id=job_id
    ).model_dump(mode="json")


# ── Node: validate_input ──────────────────────────────────────────────────────

async def validate_input_node(state: dict) -> dict:
    job_id = state["job_id"]
    data_path = state["data_path"]
    path = Path(data_path)

    if not path.exists():
        logger.error("input_not_found", job_id=job_id, data_path=data_path)
        return {
            "status": "failed",
            "error_messages": [f"Data path not found: {data_path}"],
            "audit_log": [_entry("validate_input", "error", f"path not found: {data_path}", job_id)],
        }

    if path.suffix.lower() not in (".csv", ".parquet", ".json"):
        msg = f"Unsupported file format: {path.suffix}"
        logger.error("unsupported_format", job_id=job_id, suffix=path.suffix)
        return {
            "status": "failed",
            "error_messages": [msg],
            "audit_log": [_entry("validate_input", "error", msg, job_id)],
        }

    logger.info("input_validated", job_id=job_id, data_path=data_path)
    return {
        "status": "profiling",
        "audit_log": [_entry("validate_input", "ok", f"file={data_path}", job_id)],
    }


# ── Node: profiler_node ───────────────────────────────────────────────────────

async def profiler_node(state: dict) -> dict:
    job_id = state["job_id"]
    task_config = TaskConfig.model_validate(state["task_config"])

    agent = ProfilerAgent(
        model=task_config.llm_model,
        base_url=os.getenv("LLM_BASE_URL"),
        api_key=os.getenv("LLM_API_KEY"),
    )

    try:
        report = await agent.run(
            data_path=state["data_path"],
            sample_size=task_config.data_source.sample_size,
        )
    except Exception as exc:
        msg = f"Profiler failed: {exc}"
        logger.error("profiler_failed", job_id=job_id, error=str(exc))
        return {
            "status": "failed",
            "error_messages": [msg],
            "audit_log": [_entry("profiler_node", "error", msg, job_id)],
        }

    logger.info(
        "profiling_complete",
        job_id=job_id,
        quality_score=report.overall_quality_score,
        recommended=report.recommended_tasks,
    )
    return {
        "quality_report": report.model_dump(mode="json"),
        "status": "engineering",
        "audit_log": [
            _entry(
                "profiler_node",
                "ok",
                f"quality_score={report.overall_quality_score:.2f} "
                f"recommended={report.recommended_tasks}",
                job_id,
            )
        ],
    }


# ── Node: engineer_node ───────────────────────────────────────────────────────

async def engineer_node(state: dict) -> dict:
    job_id = state["job_id"]
    task_config = TaskConfig.model_validate(state["task_config"])
    report = DataQualityReport.model_validate(state["quality_report"])

    previous_errors = [
        r.get("stderr_excerpt")
        for r in state.get("execution_results", [])
        if not r.get("success")
    ]

    agent = EngineerAgent(
        model=task_config.llm_model,
        base_url=os.getenv("LLM_BASE_URL"),
        api_key=os.getenv("LLM_API_KEY"),
    )

    try:
        scripts = await agent.run(
            report=report,
            task_config=task_config,
            input_path=state["data_path"],
            output_path=state["output_path"],
            previous_errors=previous_errors,
        )
    except Exception as exc:
        msg = f"Engineer failed: {exc}"
        logger.error("engineer_failed", job_id=job_id, error=str(exc))
        return {
            "status": "failed",
            "error_messages": [msg],
            "audit_log": [_entry("engineer_node", "error", msg, job_id)],
        }

    logger.info(
        "engineering_complete",
        job_id=job_id,
        script_ids=[s.script_id for s in scripts],
        retry_count=state.get("retry_count", 0),
    )
    return {
        "cleaning_scripts": [s.model_dump(mode="json") for s in scripts],
        "status": "qa",
        "audit_log": [
            _entry(
                "engineer_node",
                "ok",
                f"generated {len(scripts)} script(s), retry={state.get('retry_count', 0)}",
                job_id,
            )
        ],
    }


# ── Node: qa_node ─────────────────────────────────────────────────────────────

async def qa_node(state: dict) -> dict:
    job_id = state["job_id"]
    task_config = TaskConfig.model_validate(state["task_config"])
    sandbox = get_sandbox()

    agent = QAAgent(
        task_config=task_config,
        sandbox=sandbox,
        base_url=os.getenv("LLM_BASE_URL"),
        api_key=os.getenv("LLM_API_KEY"),
    )

    results = await agent.run(
        scripts=state.get("cleaning_scripts", []),
        data_path=state["data_path"],
    )

    result_dicts = [r.model_dump(mode="json") for r in results]

    all_pass = all(r.success and not r.circuit_breaker_hit for r in results)
    any_circuit = any(r.circuit_breaker_hit for r in results)

    if all_pass:
        new_status = "complete"
    elif any_circuit:
        new_status = "human_review"
    else:
        new_status = "engineering"  # retry

    logger.info(
        "qa_complete",
        job_id=job_id,
        new_status=new_status,
        retry_count=state.get("retry_count", 0),
    )
    return {
        "execution_results": result_dicts,
        "status": new_status,
        "retry_count": state.get("retry_count", 0) + (0 if all_pass else 1),
        "circuit_breaker_triggered": any_circuit,
        "audit_log": [
            _entry(
                "qa_node",
                "pass" if all_pass else ("circuit_break" if any_circuit else "fail"),
                str([{"success": r.success, "rows_before": r.rows_before,
                       "rows_after": r.rows_after} for r in results]),
                job_id,
            )
        ],
    }


# ── Node: human_review_node ───────────────────────────────────────────────────

async def human_review_node(state: dict) -> dict:
    job_id = state["job_id"]
    reason = (
        f"circuit_breaker={state.get('circuit_breaker_triggered')}, "
        f"retries={state.get('retry_count')}"
    )
    logger.warning("human_review_required", job_id=job_id, reason=reason)
    return {
        "status": "human_review",
        "audit_log": [_entry("human_review_node", "escalated", reason, job_id)],
    }


# ── Node: finalize_node ───────────────────────────────────────────────────────

async def finalize_node(state: dict) -> dict:
    job_id = state["job_id"]
    output_path = state["output_path"]
    logger.info("job_complete", job_id=job_id, output_path=output_path)
    return {
        "status": "complete",
        "audit_log": [_entry("finalize_node", "complete", f"output={output_path}", job_id)],
    }
