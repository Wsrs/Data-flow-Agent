"""Evaluation trigger and report retrieval endpoints."""
from __future__ import annotations

import asyncio
import os
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from dataflow.api.dependencies import EvalStore, get_eval_store
from dataflow.evaluation.runner import EvaluationRunner
from dataflow.tasks.registry import TaskRegistry

router = APIRouter(prefix="/api/v1/evaluate", tags=["evaluation"])


class EvaluateRequest(BaseModel):
    tasks: str = "all"   # comma-separated task names or "all"
    benchmark_dir: str | None = None


async def _run_eval(eval_id: str, task_names: list[str], benchmark_dir: str, store: EvalStore) -> None:
    store.create(eval_id, {"eval_id": eval_id, "status": "running"})
    try:
        runner = EvaluationRunner(task_names=task_names, benchmark_dir=benchmark_dir)
        report = await runner.run()
        store.create(eval_id, {"eval_id": eval_id, "status": "complete", **report})
    except Exception as exc:
        store.create(eval_id, {"eval_id": eval_id, "status": "error", "error": str(exc)})


@router.post("", response_model=dict, status_code=202)
async def trigger_evaluation(
    req: EvaluateRequest,
    background_tasks: BackgroundTasks,
    store: EvalStore = Depends(get_eval_store),
):
    registry = TaskRegistry.get()
    try:
        task_names = registry.resolve_task_names(req.tasks)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    benchmark_dir = req.benchmark_dir or os.getenv("BENCHMARK_DIR", "./benchmarks")
    eval_id = f"eval-{uuid4().hex[:8]}"
    background_tasks.add_task(_run_eval, eval_id, task_names, benchmark_dir, store)
    return {"eval_id": eval_id, "tasks": task_names, "status": "running"}


@router.get("/{eval_id}", response_model=dict)
async def get_evaluation(eval_id: str, store: EvalStore = Depends(get_eval_store)):
    report = store.get(eval_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Evaluation '{eval_id}' not found")
    return report
