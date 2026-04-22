"""Job submission, status, audit-log, approve, abort endpoints."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel

from dataflow.api.dependencies import JobStore, get_job_store
from dataflow.graph.builder import build_graph
from dataflow.observability.logger import get_logger
from dataflow.tasks.registry import TaskRegistry

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])
logger = get_logger(__name__)


# ── Request / Response models ─────────────────────────────────────────────────

class CreateJobRequest(BaseModel):
    task_name: str
    data_path: str
    output_path: str
    custom_config: Optional[dict] = None


class JobStatusResponse(BaseModel):
    job_id: str
    task_name: str
    status: str
    created_at: str
    updated_at: Optional[str] = None
    progress_summary: str = ""
    retry_count: int = 0
    circuit_breaker_triggered: bool = False
    flagged_record_count: int = 0
    rows_before: Optional[int] = None
    rows_after: Optional[int] = None
    error_messages: list[str] = []
    result_path: Optional[str] = None


# ── Background pipeline runner ────────────────────────────────────────────────

async def _run_pipeline(job_id: str, initial_state: dict, store: JobStore) -> None:
    graph = build_graph()
    try:
        store.update(job_id, {"status": "profiling", "progress_summary": "Profiling data..."})
        final_state = await graph.ainvoke(initial_state)

        exec_results = final_state.get("execution_results", [])
        last = exec_results[-1] if exec_results else {}

        store.update(job_id, {
            "status": final_state.get("status", "unknown"),
            "progress_summary": f"Pipeline finished with status: {final_state.get('status')}",
            "retry_count": final_state.get("retry_count", 0),
            "circuit_breaker_triggered": final_state.get("circuit_breaker_triggered", False),
            "flagged_record_count": last.get("flagged_record_count", 0),
            "rows_before": last.get("rows_before"),
            "rows_after": last.get("rows_after"),
            "result_path": final_state.get("output_path") if final_state.get("status") == "complete" else None,
            "audit_log": final_state.get("audit_log", []),
            "error_messages": final_state.get("error_messages", []),
        })
    except Exception as exc:
        logger.error("pipeline_exception", job_id=job_id, error=str(exc))
        store.update(job_id, {
            "status": "failed",
            "progress_summary": f"Unexpected error: {exc}",
            "error_messages": [str(exc)],
        })


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=dict)
async def create_job(
    req: CreateJobRequest,
    background_tasks: BackgroundTasks,
    store: JobStore = Depends(get_job_store),
):
    registry = TaskRegistry.get()
    try:
        task_config = registry.get_task(req.task_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    if req.custom_config:
        raw = task_config.model_dump()
        raw.update(req.custom_config)
        from dataflow.schemas.task_config import TaskConfig
        task_config = TaskConfig.model_validate(raw)

    job_id = f"job-{uuid4().hex[:8]}"

    initial_state: dict = {
        "job_id": job_id,
        "task_config": task_config.model_dump(mode="json"),
        "data_path": req.data_path,
        "output_path": req.output_path,
        "quality_report": None,
        "cleaning_scripts": [],
        "execution_results": [],
        "status": "pending",
        "retry_count": 0,
        "max_retries": task_config.max_retries,
        "circuit_breaker_triggered": False,
        "audit_log": [],
        "error_messages": [],
    }

    store.create(job_id, {
        "job_id": job_id,
        "task_name": req.task_name,
        "status": "pending",
        "progress_summary": "Job queued",
        "retry_count": 0,
        "circuit_breaker_triggered": False,
        "flagged_record_count": 0,
        "rows_before": None,
        "rows_after": None,
        "error_messages": [],
        "result_path": None,
        "audit_log": [],
    })

    background_tasks.add_task(_run_pipeline, job_id, initial_state, store)
    logger.info("job_created", job_id=job_id, task=req.task_name)
    return {"job_id": job_id, "status": "pending"}


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str, store: JobStore = Depends(get_job_store)):
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return JobStatusResponse(**{k: v for k, v in job.items() if k != "audit_log"})


@router.get("/{job_id}/audit-log", response_model=list)
async def get_audit_log(job_id: str, store: JobStore = Depends(get_job_store)):
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return job.get("audit_log", [])


@router.post("/{job_id}/approve", response_model=dict)
async def approve_job(job_id: str, store: JobStore = Depends(get_job_store)):
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    if job.get("status") != "human_review":
        raise HTTPException(status_code=409, detail="Job is not in 'human_review' state")
    store.update(job_id, {"status": "approved", "progress_summary": "Approved by human reviewer"})
    return {"job_id": job_id, "status": "approved"}


@router.post("/{job_id}/abort", response_model=dict)
async def abort_job(job_id: str, store: JobStore = Depends(get_job_store)):
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    if job.get("status") in ("complete", "failed", "approved"):
        raise HTTPException(status_code=409, detail=f"Cannot abort job with status '{job['status']}'")
    store.update(job_id, {"status": "aborted", "progress_summary": "Aborted by user"})
    return {"job_id": job_id, "status": "aborted"}
