"""Unit tests for evaluation metric computations."""
import pytest

from dataflow.evaluation.metrics import METRIC_REGISTRY


class TestPairF1:
    metric = METRIC_REGISTRY["pair_f1"]

    def test_perfect_match(self):
        gold = {(1, 2), (3, 4), (5, 6)}
        assert self.metric.compute(gold, gold) == pytest.approx(1.0, abs=1e-6)

    def test_no_overlap(self):
        pred = {(1, 2)}
        gold = {(3, 4)}
        assert self.metric.compute(pred, gold) == pytest.approx(0.0, abs=1e-4)

    def test_partial_match(self):
        pred = {(1, 2), (3, 4), (5, 6)}
        gold = {(1, 2), (3, 4)}
        # precision = 2/3, recall = 2/2=1.0, f1 = 2*(2/3*1)/(2/3+1)
        f1 = self.metric.compute(pred, gold)
        assert 0.75 < f1 < 0.85

    def test_empty_sets_no_crash(self):
        score = self.metric.compute(set(), set())
        assert score == pytest.approx(0.0, abs=1e-4)


class TestPrecisionRecall:
    precision = METRIC_REGISTRY["precision"]
    recall = METRIC_REGISTRY["recall"]

    def test_precision_perfect(self):
        pairs = {(1, 2), (3, 4)}
        assert self.precision.compute(pairs, pairs) == pytest.approx(1.0)

    def test_recall_perfect(self):
        pairs = {(1, 2), (3, 4)}
        assert self.recall.compute(pairs, pairs) == pytest.approx(1.0)

    def test_precision_zero(self):
        assert self.precision.compute({(1, 2)}, {(3, 4)}) == pytest.approx(0.0, abs=1e-4)

    def test_recall_zero(self):
        assert self.recall.compute({(1, 2)}, {(3, 4)}) == pytest.approx(0.0, abs=1e-4)


class TestRowRetentionRate:
    metric = METRIC_REGISTRY["row_retention_rate"]

    def test_no_deletion(self):
        result = {"rows_before": 1000, "rows_after": 1000}
        assert self.metric.compute(result) == pytest.approx(1.0)

    def test_half_deleted(self):
        result = {"rows_before": 1000, "rows_after": 500}
        assert self.metric.compute(result) == pytest.approx(0.5)

    def test_zero_before(self):
        result = {"rows_before": 0, "rows_after": 0}
        assert self.metric.compute(result) == pytest.approx(1.0)


class TestCoercionSuccessRate:
    metric = METRIC_REGISTRY["coercion_success_rate"]

    def test_no_flagged(self):
        result = {"rows_before": 1000, "flagged_record_count": 0}
        assert self.metric.compute(result) == pytest.approx(1.0)

    def test_all_flagged(self):
        result = {"rows_before": 1000, "flagged_record_count": 1000}
        assert self.metric.compute(result) == pytest.approx(0.0)

    def test_partial(self):
        result = {"rows_before": 1000, "flagged_record_count": 100}
        assert self.metric.compute(result) == pytest.approx(0.9)


class TestMetricRegistry:
    def test_all_expected_metrics_present(self):
        expected = {
            "pair_f1", "precision", "recall",
            "completeness_rate", "uniqueness_rate", "row_retention_rate",
            "script_first_pass_rate", "format_compliance_rate",
            "null_rate_delta", "imputation_confidence_score",
            "type_consistency_rate", "coercion_success_rate",
        }
        for name in expected:
            assert name in METRIC_REGISTRY, f"Metric '{name}' missing from registry"

    def test_higher_is_better_flags(self):
        assert METRIC_REGISTRY["pair_f1"].higher_is_better is True
        assert METRIC_REGISTRY["null_rate_delta"].higher_is_better is False
