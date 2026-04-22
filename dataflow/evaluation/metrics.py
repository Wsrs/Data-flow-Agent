"""
Harness evaluation metric registry.

Each metric is a dataclass with a `compute` callable.
Mirrors lm-evaluation-harness metric_list / aggregation patterns.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Metric:
    name: str
    compute: Callable[..., float]
    higher_is_better: bool
    aggregation: str = "mean"


# ── Metric implementations ────────────────────────────────────────────────────

def _pair_f1(pred_pairs: set, gold_pairs: set) -> float:
    tp = len(pred_pairs & gold_pairs)
    return 2 * tp / (len(pred_pairs) + len(gold_pairs) + 1e-9)


def _precision(pred_pairs: set, gold_pairs: set) -> float:
    tp = len(pred_pairs & gold_pairs)
    return tp / (len(pred_pairs) + 1e-9)


def _recall(pred_pairs: set, gold_pairs: set) -> float:
    tp = len(pred_pairs & gold_pairs)
    return tp / (len(gold_pairs) + 1e-9)


def _completeness_rate(result_dict: dict) -> float:
    """1 - average null_rate_delta (null rate should decrease)."""
    delta = result_dict.get("quality_delta", {}).get("null_rate", 0.0)
    return max(0.0, min(1.0, 1.0 + delta))   # delta is negative when null rate drops


def _uniqueness_rate(result_dict: dict) -> float:
    before = result_dict.get("rows_before", 1)
    after  = result_dict.get("rows_after", before)
    if before == 0:
        return 1.0
    # Uniqueness: fewer rows means duplicates were removed → higher is better
    # We approximate as rows_after / rows_before capped to [0, 1]
    # The actual uniqueness requires reading the output dataframe; this is a proxy.
    return min(1.0, max(0.0, after / before))


def _row_retention_rate(result_dict: dict) -> float:
    before = result_dict.get("rows_before", 0)
    after  = result_dict.get("rows_after", before)
    if before == 0:
        return 1.0
    return min(1.0, max(0.0, after / before))


def _script_first_pass_rate(results: list[dict]) -> float:
    if not results:
        return 0.0
    passed = sum(1 for r in results if r.get("success") and r.get("retry_count", 0) == 0)
    return passed / len(results)


def _format_compliance_rate(result_dict: dict) -> float:
    return result_dict.get("quality_delta", {}).get("format_compliance_rate", 0.0)


def _null_rate_delta(result_dict: dict) -> float:
    """Lower (more negative) is better when null rate decreases."""
    return result_dict.get("quality_delta", {}).get("null_rate", 0.0)


def _imputation_confidence_score(result_dict: dict) -> float:
    return result_dict.get("quality_delta", {}).get("imputation_confidence", 0.75)


def _type_consistency_rate(result_dict: dict) -> float:
    return result_dict.get("quality_delta", {}).get("type_consistency_rate", 0.0)


def _coercion_success_rate(result_dict: dict) -> float:
    rows_before = result_dict.get("rows_before", 1)
    flagged     = result_dict.get("flagged_record_count", 0)
    return max(0.0, 1.0 - flagged / max(rows_before, 1))


# ── Registry ──────────────────────────────────────────────────────────────────

METRIC_REGISTRY: dict[str, Metric] = {
    "pair_f1": Metric(
        name="pair_f1",
        compute=_pair_f1,
        higher_is_better=True,
    ),
    "precision": Metric(
        name="precision",
        compute=_precision,
        higher_is_better=True,
    ),
    "recall": Metric(
        name="recall",
        compute=_recall,
        higher_is_better=True,
    ),
    "completeness_rate": Metric(
        name="completeness_rate",
        compute=_completeness_rate,
        higher_is_better=True,
    ),
    "uniqueness_rate": Metric(
        name="uniqueness_rate",
        compute=_uniqueness_rate,
        higher_is_better=True,
    ),
    "row_retention_rate": Metric(
        name="row_retention_rate",
        compute=_row_retention_rate,
        higher_is_better=True,
    ),
    "script_first_pass_rate": Metric(
        name="script_first_pass_rate",
        compute=_script_first_pass_rate,
        higher_is_better=True,
    ),
    "format_compliance_rate": Metric(
        name="format_compliance_rate",
        compute=_format_compliance_rate,
        higher_is_better=True,
    ),
    "null_rate_delta": Metric(
        name="null_rate_delta",
        compute=_null_rate_delta,
        higher_is_better=False,
    ),
    "imputation_confidence_score": Metric(
        name="imputation_confidence_score",
        compute=_imputation_confidence_score,
        higher_is_better=True,
    ),
    "type_consistency_rate": Metric(
        name="type_consistency_rate",
        compute=_type_consistency_rate,
        higher_is_better=True,
    ),
    "coercion_success_rate": Metric(
        name="coercion_success_rate",
        compute=_coercion_success_rate,
        higher_is_better=True,
    ),
}
