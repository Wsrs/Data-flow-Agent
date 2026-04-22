from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


class DataSourceConfig(BaseModel):
    type: Literal["csv", "parquet", "json"] = "parquet"
    sample_size: int = 500
    encoding: str = "utf-8"


class MatchField(BaseModel):
    name: str
    weight: float = 1.0
    comparator: Literal["jaro_winkler", "levenshtein", "exact", "cosine"] = "jaro_winkler"


class FieldRule(BaseModel):
    field: str
    target_format: str  # e.g. "%Y-%m-%d", "+86-{area}-{number}"


class CleaningStrategyConfig(BaseModel):
    type: str

    # ── deduplication ────────────────────────────────────────────────────────
    mode: Optional[Literal["exact", "fuzzy"]] = None
    key_fields: list[str] = Field(default_factory=list)
    fuzzy_threshold: float = 0.90

    # ── entity_resolution ────────────────────────────────────────────────────
    algorithm: Optional[Literal["splink", "vector", "hybrid"]] = None
    match_fields: list[MatchField] = Field(default_factory=list)
    splink_threshold: float = 0.85
    vector_model: str = "BAAI/bge-m3"
    vector_top_k: int = 20
    llm_arbitration: bool = True

    # ── format_standardization ───────────────────────────────────────────────
    target_locale: str = "zh_CN"
    field_rules: list[FieldRule] = Field(default_factory=list)

    # ── missing_value_imputation ─────────────────────────────────────────────
    strategy_map: dict[str, str] = Field(default_factory=dict)
    max_llm_imputation_rate: float = 0.05

    # ── type_coercion ────────────────────────────────────────────────────────
    type_map: dict[str, str] = Field(default_factory=dict)


class CircuitBreakerConfig(BaseModel):
    max_row_reduction: float = 0.30
    min_confidence_score: float = 0.70


class MetricConfig(BaseModel):
    metric: str
    aggregation: Literal["mean", "sum"] = "mean"
    higher_is_better: bool = True
    weight: float = 1.0


class OutputConfig(BaseModel):
    format: Literal["parquet", "csv"] = "parquet"
    write_audit_log: bool = True
    write_flagged_records: bool = True


class TaskConfig(BaseModel):
    task: str
    version: int = 1
    description: str = ""
    llm_model: str = "gpt-4o"

    data_source: DataSourceConfig = Field(default_factory=DataSourceConfig)
    cleaning_strategy: CleaningStrategyConfig
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    metric_list: list[MetricConfig] = Field(default_factory=list)
    output: OutputConfig = Field(default_factory=OutputConfig)
    max_retries: int = 3
