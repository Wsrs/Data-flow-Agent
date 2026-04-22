from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ColumnProfile(BaseModel):
    name: str
    dtype: str
    null_rate: float
    unique_rate: float
    sample_values: list[str] = Field(default_factory=list)
    detected_issues: list[str] = Field(default_factory=list)
    format_pattern: Optional[str] = None


class DataQualityReport(BaseModel):
    report_id: str
    generated_at: datetime
    total_rows: int
    total_columns: int
    duplicate_row_rate: float
    overall_quality_score: float
    columns: list[ColumnProfile]
    recommended_tasks: list[str] = Field(default_factory=list)
    llm_summary: str = ""
