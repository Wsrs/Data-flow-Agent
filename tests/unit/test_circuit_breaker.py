"""Unit tests for CircuitBreaker."""
import pytest

from dataflow.agents.qa import CircuitBreaker
from dataflow.schemas.execution import ExecutionResult
from dataflow.schemas.task_config import (
    CircuitBreakerConfig,
    CleaningStrategyConfig,
    TaskConfig,
)


def _make_result(**kwargs) -> ExecutionResult:
    defaults = dict(
        script_id="scr-test",
        success=True,
        rows_before=10_000,
        rows_after=9_800,
        row_delta_rate=-0.02,
        flagged_record_count=0,
    )
    defaults.update(kwargs)
    return ExecutionResult(**defaults)


def _make_config(max_reduction: float = 0.30) -> TaskConfig:
    return TaskConfig(
        task="deduplication",
        cleaning_strategy=CleaningStrategyConfig(type="deduplication"),
        circuit_breaker=CircuitBreakerConfig(max_row_reduction=max_reduction),
    )


class TestCircuitBreaker:
    cb = CircuitBreaker()

    def test_no_trigger_normal(self):
        result = _make_result(row_delta_rate=-0.05)
        triggered, _ = self.cb.check(result, _make_config(0.30))
        assert not triggered

    def test_triggers_on_excessive_row_deletion(self):
        result = _make_result(rows_before=10_000, rows_after=5_000, row_delta_rate=-0.50)
        triggered, reason = self.cb.check(result, _make_config(0.30))
        assert triggered
        assert "50.0%" in reason or "reduction" in reason.lower()

    def test_triggers_exactly_at_threshold(self):
        result = _make_result(rows_before=10_000, rows_after=7_001, row_delta_rate=-0.2999)
        triggered, _ = self.cb.check(result, _make_config(0.30))
        assert not triggered

        result_over = _make_result(rows_before=10_000, rows_after=6_999, row_delta_rate=-0.3001)
        triggered2, _ = self.cb.check(result_over, _make_config(0.30))
        assert triggered2

    def test_triggers_on_high_flagged_rate(self):
        result = _make_result(
            rows_before=10_000,
            rows_after=10_000,
            row_delta_rate=0.0,
            flagged_record_count=2_500,   # 25 % > 20 % threshold
        )
        triggered, reason = self.cb.check(result, _make_config(0.30))
        assert triggered
        assert "flagged" in reason.lower() or "review" in reason.lower()

    def test_no_trigger_below_flagged_threshold(self):
        result = _make_result(
            rows_before=10_000,
            rows_after=10_000,
            row_delta_rate=0.0,
            flagged_record_count=1_999,   # 19.99 % < 20 %
        )
        triggered, _ = self.cb.check(result, _make_config(0.30))
        assert not triggered

    def test_custom_threshold(self):
        result = _make_result(rows_before=1_000, rows_after=900, row_delta_rate=-0.10)
        triggered_strict, _ = self.cb.check(result, _make_config(max_reduction=0.05))
        assert triggered_strict

        triggered_loose, _ = self.cb.check(result, _make_config(max_reduction=0.20))
        assert not triggered_loose
