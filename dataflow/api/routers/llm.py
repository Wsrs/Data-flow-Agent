"""LLM status & health router."""
from __future__ import annotations

import httpx
from fastapi import APIRouter

from dataflow.agents.llm_factory import get_provider_info

router = APIRouter(prefix="/api/v1/llm", tags=["llm"])

_OLLAMA_BASE = "http://localhost:11434"


@router.get("/status")
async def llm_status():
    info = get_provider_info()
    reachable = False
    models: list[str] = []

    if info["provider"] == "ollama":
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                r = await client.get(f"{_OLLAMA_BASE}/api/tags")
                if r.status_code == 200:
                    reachable = True
                    models = [m["name"] for m in r.json().get("models", [])]
        except Exception:
            pass
    else:
        reachable = True  # assume cloud API reachable (key validity checked at call time)

    return {**info, "reachable": reachable, "available_models": models}
