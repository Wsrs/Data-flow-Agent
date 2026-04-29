"""FastAPI application entry-point."""
from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

load_dotenv()

from dataflow.api.routers import jobs, tasks, evaluation  # noqa: E402
from dataflow.api.routers import memory, llm  # noqa: E402
from dataflow.observability.logger import get_logger  # noqa: E402

logger = get_logger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="DataFlow-Agent API",
        description="Intelligent data governance and automated cleaning engine",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(jobs.router)
    app.include_router(tasks.router)
    app.include_router(evaluation.router)
    app.include_router(memory.router, prefix="/api/v1")
    app.include_router(llm.router)

    # ── Prometheus metrics endpoint ───────────────────────────────────────────
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok", "service": "dataflow-agent"}

    @app.on_event("startup")
    async def on_startup():
        from dataflow.tasks.registry import TaskRegistry
        registry = TaskRegistry.get()
        logger.info("app_started", registered_tasks=registry.list_tasks())

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "dataflow.api.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8080")),
        workers=int(os.getenv("API_WORKERS", "1")),
        reload=False,
    )
