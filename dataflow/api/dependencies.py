"""FastAPI dependency injectors."""
from __future__ import annotations

import asyncio
import threading
from datetime import datetime
from typing import Any
from uuid import uuid4

from dataflow.observability.logger import get_logger

logger = get_logger(__name__)


# ── In-process job store (replace with Redis in production) ───────────────────

class JobStore:
    """Thread-safe in-memory job store keyed by job_id."""

    def __init__(self) -> None:
        self._jobs: dict[str, dict] = {}
        self._lock = threading.Lock()

    def create(self, job_id: str, initial: dict) -> None:
        with self._lock:
            self._jobs[job_id] = {**initial, "created_at": datetime.utcnow().isoformat()}

    def get(self, job_id: str) -> dict | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, patch: dict) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(patch)
                self._jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()

    def list_all(self) -> list[dict]:
        with self._lock:
            return list(self._jobs.values())


_job_store = JobStore()


def get_job_store() -> JobStore:
    return _job_store


# ── Eval store ────────────────────────────────────────────────────────────────

class EvalStore:
    """Thread-safe in-memory evaluation result store."""

    def __init__(self) -> None:
        self._evals: dict[str, dict] = {}
        self._lock = threading.Lock()

    def create(self, eval_id: str, report: dict) -> None:
        with self._lock:
            self._evals[eval_id] = report

    def get(self, eval_id: str) -> dict | None:
        with self._lock:
            return self._evals.get(eval_id)


_eval_store = EvalStore()


def get_eval_store() -> EvalStore:
    return _eval_store
