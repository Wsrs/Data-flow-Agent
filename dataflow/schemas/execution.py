from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional
from pydantic import BaseModel, Field


class CleaningScript(BaseModel):
    script_id: str
    task_name: str
    version: int = 1
    code: str
    dependencies: list[str] = Field(default_factory=list)
    input_path: str
    output_path: str
    estimated_row_delta: float = 0.0
    generated_by_model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0


class ExecutionResult(BaseModel):
    script_id: str
    success: bool
    rows_before: int = 0
    rows_after: int = 0
    row_delta_rate: float = 0.0
    execution_time_seconds: float = 0.0
    peak_memory_mb: float = 0.0
    quality_delta: dict[str, float] = Field(default_factory=dict)
    stderr_excerpt: Optional[str] = None
    circuit_breaker_hit: bool = False
    flagged_record_count: int = 0


class AuditEntry(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    node: str
    status: str
    detail: str = ""
    job_id: str = ""
