"""Memory API – long/short-term memory and template management."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from dataflow.memory.store import (
    add_memory, add_template,
    delete_memory, find_similar_templates,
    get_template, list_memories, list_templates, search_memories,
)

router = APIRouter(prefix="/memory", tags=["memory"])


# ── Request models ────────────────────────────────────────────────────────────

class AddMemoryReq(BaseModel):
    type: str = "short"
    category: str = "general"
    task_name: str
    summary: str
    tags: list[str] = []
    score: float = 0.0
    job_id: Optional[str] = None


class AddTemplateReq(BaseModel):
    name: str
    task_name: str
    description: str
    tags: list[str] = []
    config_snippet: dict = {}
    score: float = 0.0


class SimilarReq(BaseModel):
    task_name: str
    tags: list[str] = []


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("")
def get_memories(type: Optional[str] = Query(None)):
    return list_memories(type_filter=type)


@router.get("/search")
def search(q: str = Query(..., min_length=1)):
    return search_memories(q)


@router.post("", status_code=201)
def create_memory(req: AddMemoryReq):
    return add_memory(**req.model_dump())


@router.delete("/{memory_id}")
def remove_memory(memory_id: str):
    if not delete_memory(memory_id):
        raise HTTPException(404, "Memory not found")
    return {"deleted": memory_id}


# ── Templates ─────────────────────────────────────────────────────────────────

@router.get("/templates")
def get_templates(task: Optional[str] = Query(None)):
    return list_templates(task_filter=task)


@router.post("/templates", status_code=201)
def create_template(req: AddTemplateReq):
    return add_template(**req.model_dump())


@router.get("/templates/similar")
def similar_templates(task_name: str = Query(...), tags: str = Query("")):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    return find_similar_templates(task_name, tag_list)


@router.get("/templates/{template_id}")
def apply_template(template_id: str):
    tmpl = get_template(template_id)
    if not tmpl:
        raise HTTPException(404, "Template not found")
    return tmpl
