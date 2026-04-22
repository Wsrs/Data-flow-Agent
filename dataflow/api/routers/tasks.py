"""Task listing endpoint."""
from __future__ import annotations

from fastapi import APIRouter

from dataflow.tasks.registry import TaskRegistry

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.get("", response_model=list[dict])
async def list_tasks():
    registry = TaskRegistry.get()
    tasks = []
    for name in registry.list_tasks():
        cfg = registry.get_task(name)
        tasks.append({
            "task": cfg.task,
            "version": cfg.version,
            "description": cfg.description,
            "cleaning_strategy_type": cfg.cleaning_strategy.type,
            "metrics": [m.metric for m in cfg.metric_list],
            "max_retries": cfg.max_retries,
        })
    return tasks


@router.get("/{task_name}", response_model=dict)
async def get_task(task_name: str):
    from fastapi import HTTPException
    registry = TaskRegistry.get()
    try:
        cfg = registry.get_task(task_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return cfg.model_dump(mode="json")
