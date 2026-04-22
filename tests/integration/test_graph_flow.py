"""
Integration tests for the LangGraph pipeline.

Uses a MockLLM that returns pre-scripted responses so no real LLM API key is needed.
Uses a MockSandbox so no real file I/O or subprocess is needed.
"""
from __future__ import annotations

import asyncio
import textwrap
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dataflow.graph.builder import build_graph
from dataflow.schemas.execution import ExecutionResult
from dataflow.schemas.task_config import CleaningStrategyConfig, TaskConfig

# ── Fixtures ──────────────────────────────────────────────────────────────────

TASK_CONFIG = TaskConfig(
    task="deduplication",
    version=1,
    description="Test deduplication",
    llm_model="gpt-4o",
    cleaning_strategy=CleaningStrategyConfig(type="deduplication"),
    max_retries=2,
)

VALID_SCRIPT = textwrap.dedent("""\
    import polars as pl, sys
    df = pl.read_parquet("/data/input.parquet")
    rows_before = len(df)
    df = df.unique()
    rows_after = len(df)
    df.write_parquet("/data/output.parquet")
    print(f"ROWS_BEFORE={rows_before}")
    print(f"ROWS_AFTER={rows_after}")
    print("FLAGGED=0")
    sys.exit(0)
""")

BROKEN_SCRIPT = "this is not valid python code!!!##"


def _initial_state(data_path: str = "input.parquet") -> dict:
    return {
        "job_id": "test-job-001",
        "task_config": TASK_CONFIG.model_dump(mode="json"),
        "data_path": data_path,
        "output_path": "output.parquet",
        "quality_report": None,
        "cleaning_scripts": [],
        "execution_results": [],
        "status": "pending",
        "retry_count": 0,
        "max_retries": TASK_CONFIG.max_retries,
        "circuit_breaker_triggered": False,
        "audit_log": [],
        "error_messages": [],
    }


def _mock_sandbox_result(success: bool, rows_before: int = 1000, rows_after: int = 950) -> ExecutionResult:
    return ExecutionResult(
        script_id="scr-mock",
        success=success,
        rows_before=rows_before,
        rows_after=rows_after,
        row_delta_rate=(rows_after - rows_before) / max(rows_before, 1),
        execution_time_seconds=0.1,
        flagged_record_count=0,
    )


# ── Test helpers ──────────────────────────────────────────────────────────────

class _FakeChatResponse:
    def __init__(self, content: str) -> None:
        self.content = content
        self.usage_metadata = {"input_tokens": 10, "output_tokens": 50}


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestGraphFlow:
    @pytest.mark.asyncio
    async def test_fails_when_input_missing(self, tmp_path):
        graph = build_graph()
        state = _initial_state(data_path=str(tmp_path / "nonexistent.parquet"))
        final = await graph.ainvoke(state)
        assert final["status"] == "failed"
        assert any("not found" in m.lower() for m in final["error_messages"])

    @pytest.mark.asyncio
    async def test_happy_path_completes(self, tmp_path):
        """Full pipeline from validate → profiler → engineer → qa → finalize."""
        import polars as pl

        # Create a real parquet file
        data_path = tmp_path / "data.parquet"
        out_path = tmp_path / "output.parquet"
        df = pl.DataFrame({"id": [1, 2, 2, 3], "name": ["a", "b", "b", "c"]})
        df.write_parquet(str(data_path))
        # Pre-create a valid output so the mock sandbox "succeeds"
        df.unique().write_parquet(str(out_path))

        mock_response = _FakeChatResponse(VALID_SCRIPT)
        mock_sandbox = AsyncMock()
        mock_sandbox.execute.return_value = _mock_sandbox_result(
            success=True, rows_before=4, rows_after=3
        )

        with (
            patch("dataflow.agents.profiler.ChatOpenAI") as MockProfilerLLM,
            patch("dataflow.agents.engineer.ChatOpenAI") as MockEngineerLLM,
            patch("dataflow.agents.qa.ChatOpenAI"),
            patch("dataflow.graph.nodes.get_sandbox", return_value=mock_sandbox),
        ):
            # Profiler LLM returns a summary with recommended task
            profiler_resp = _FakeChatResponse(
                "Data has duplicate rows.\nTASK: deduplication"
            )
            MockProfilerLLM.return_value.ainvoke = AsyncMock(return_value=profiler_resp)
            MockEngineerLLM.return_value.ainvoke = AsyncMock(return_value=mock_response)

            graph = build_graph()
            state = _initial_state(data_path=str(data_path))
            state["output_path"] = str(out_path)

            final = await graph.ainvoke(state)

        assert final["status"] == "complete", f"Expected complete, got {final['status']}: {final['error_messages']}"
        assert len(final["cleaning_scripts"]) >= 1
        assert len(final["execution_results"]) >= 1
        assert final["execution_results"][-1]["success"] is True

    @pytest.mark.asyncio
    async def test_retry_on_script_failure(self, tmp_path):
        """Broken script should trigger engineer retry; second attempt succeeds."""
        import polars as pl

        data_path = tmp_path / "data.parquet"
        out_path = tmp_path / "output.parquet"
        pl.DataFrame({"id": [1, 2], "v": ["a", "b"]}).write_parquet(str(data_path))
        pl.DataFrame({"id": [1, 2], "v": ["a", "b"]}).write_parquet(str(out_path))

        call_count = 0

        async def _llm_side_effect(messages):
            nonlocal call_count
            call_count += 1
            # First call returns broken script, second call returns valid
            code = BROKEN_SCRIPT if call_count == 1 else VALID_SCRIPT
            return _FakeChatResponse(code)

        mock_sandbox = AsyncMock()
        mock_sandbox.execute.return_value = _mock_sandbox_result(success=True)

        with (
            patch("dataflow.agents.profiler.ChatOpenAI") as MockProfilerLLM,
            patch("dataflow.agents.engineer.ChatOpenAI") as MockEngineerLLM,
            patch("dataflow.agents.qa.ChatOpenAI"),
            patch("dataflow.graph.nodes.get_sandbox", return_value=mock_sandbox),
        ):
            MockProfilerLLM.return_value.ainvoke = AsyncMock(
                return_value=_FakeChatResponse("TASK: deduplication")
            )
            MockEngineerLLM.return_value.ainvoke = _llm_side_effect

            graph = build_graph()
            state = _initial_state(data_path=str(data_path))
            state["output_path"] = str(out_path)
            final = await graph.ainvoke(state)

        # First script has syntax error → retry_count increments → second script succeeds
        assert final["status"] == "complete"
        assert final["retry_count"] == 1
        assert call_count == 2   # engineer was called twice

    @pytest.mark.asyncio
    async def test_circuit_breaker_escalates_to_human_review(self, tmp_path):
        """Sandbox result that trips circuit-breaker should end in human_review."""
        import polars as pl

        data_path = tmp_path / "data.parquet"
        out_path = tmp_path / "output.parquet"
        pl.DataFrame({"id": list(range(100))}).write_parquet(str(data_path))
        pl.DataFrame({"id": list(range(100))}).write_parquet(str(out_path))

        # Simulate 60 % row deletion – should trip the 30 % circuit breaker
        bad_result = _mock_sandbox_result(success=True, rows_before=100, rows_after=40)

        mock_sandbox = AsyncMock()
        mock_sandbox.execute.return_value = bad_result

        with (
            patch("dataflow.agents.profiler.ChatOpenAI") as MockProfilerLLM,
            patch("dataflow.agents.engineer.ChatOpenAI") as MockEngineerLLM,
            patch("dataflow.agents.qa.ChatOpenAI"),
            patch("dataflow.graph.nodes.get_sandbox", return_value=mock_sandbox),
        ):
            MockProfilerLLM.return_value.ainvoke = AsyncMock(
                return_value=_FakeChatResponse("TASK: deduplication")
            )
            MockEngineerLLM.return_value.ainvoke = AsyncMock(
                return_value=_FakeChatResponse(VALID_SCRIPT)
            )

            graph = build_graph()
            state = _initial_state(data_path=str(data_path))
            state["output_path"] = str(out_path)
            final = await graph.ainvoke(state)

        assert final["status"] == "human_review"
        assert final["circuit_breaker_triggered"] is True
