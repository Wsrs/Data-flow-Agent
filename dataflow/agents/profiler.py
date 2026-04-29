"""ProfilerAgent – samples data, computes column statistics, calls LLM for analysis."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from langchain_core.messages import HumanMessage, SystemMessage
from dataflow.agents.llm_factory import build_llm
from dataflow.schemas.report import ColumnProfile, DataQualityReport


class ProfilerAgent:
    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self._llm = build_llm(model=model, base_url=base_url, api_key=api_key, timeout=120)

    async def run(self, data_path: str, sample_size: int = 500) -> DataQualityReport:
        import polars as pl

        path = Path(data_path)
        df = self._load_sample(path, sample_size)

        columns = [self._profile_column(df, col) for col in df.columns]

        try:
            dup_rate = 1.0 - df.unique().height / df.height if df.height > 0 else 0.0
        except Exception:
            dup_rate = 0.0

        avg_null = sum(c.null_rate for c in columns) / max(len(columns), 1)
        quality_score = max(0.0, round(1.0 - avg_null - dup_rate * 0.5, 4))

        # Send sample to LLM for semantic analysis
        sample_json = df.head(20).write_json()
        col_summary = "\n".join(
            f"  - {c.name} ({c.dtype}): null={c.null_rate:.1%}, "
            f"unique={c.unique_rate:.1%}, issues={c.detected_issues}"
            for c in columns
        )

        prompt_path = Path(__file__).parent / "prompts" / "profiler_v1.txt"
        sys_content = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""

        user_msg = (
            f"## Data sample (first 20 rows)\n{sample_json}\n\n"
            f"## Column profiles\n{col_summary}\n\n"
            f"Duplicate row rate: {dup_rate:.1%}\n"
            f"Overall quality score: {quality_score:.2f}\n\n"
            "Analyse the quality issues and recommend cleaning tasks."
        )

        messages = []
        if sys_content:
            messages.append(SystemMessage(content=sys_content))
        messages.append(HumanMessage(content=user_msg))

        response = await self._llm.ainvoke(messages)
        llm_output: str = response.content

        # Extract recommended tasks from lines starting with "TASK: "
        recommended = []
        for line in llm_output.splitlines():
            if line.strip().startswith("TASK:"):
                task_name = line.split(":", 1)[1].strip().lower()
                recommended.append(task_name)
        # Fallback: keyword scan
        if not recommended:
            for task in [
                "deduplication", "entity_resolution",
                "format_standardization", "missing_value_imputation", "type_coercion",
            ]:
                if task in llm_output.lower():
                    recommended.append(task)

        return DataQualityReport(
            report_id=f"rpt-{uuid4().hex[:8]}",
            generated_at=datetime.now(UTC),
            total_rows=df.height,
            total_columns=df.width,
            duplicate_row_rate=round(dup_rate, 4),
            overall_quality_score=quality_score,
            columns=columns,
            recommended_tasks=recommended,
            llm_summary=llm_output,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _load_sample(path: Path, sample_size: int):
        import polars as pl

        if path.suffix == ".parquet":
            return pl.read_parquet(str(path)).head(sample_size)
        if path.suffix == ".csv":
            return pl.read_csv(str(path), n_rows=sample_size, ignore_errors=True)
        if path.suffix == ".json":
            return pl.read_json(str(path)).head(sample_size)
        raise ValueError(f"Unsupported file format: {path.suffix}")

    @staticmethod
    def _profile_column(df, col: str) -> ColumnProfile:
        import polars as pl

        series = df[col]
        total = len(series)
        null_rate = series.null_count() / total if total > 0 else 0.0

        try:
            unique_rate = series.n_unique() / total if total > 0 else 0.0
        except Exception:
            unique_rate = 0.0

        sample_values = [str(v) for v in series.drop_nulls().head(10).to_list()]

        issues: list[str] = []
        if null_rate > 0.10:
            issues.append(f"high_null_rate:{null_rate:.1%}")
        if unique_rate < 0.01 and total > 100:
            issues.append("low_cardinality")

        # Detect leading/trailing whitespace in string columns
        if series.dtype == pl.Utf8 or series.dtype == pl.String:
            try:
                non_null = series.drop_nulls()
                if non_null.len() > 0:
                    stripped = non_null.str.strip_chars()
                    if (non_null != stripped).any():
                        issues.append("leading_trailing_whitespace")
            except Exception:
                pass

        return ColumnProfile(
            name=col,
            dtype=str(series.dtype),
            null_rate=round(null_rate, 4),
            unique_rate=round(unique_rate, 4),
            sample_values=sample_values,
            detected_issues=issues,
        )
