"""EvaluationReporter – serialises and prints evaluation reports."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def print_report(report: dict, output_format: str = "table") -> None:
    if output_format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return

    # Human-readable table
    print(f"\n{'=' * 60}")
    print(f"  DataFlow-Agent Evaluation Report")
    print(f"  Generated: {report.get('generated_at', '')}")
    print(f"{'=' * 60}")

    results: dict = report.get("results", {})
    for task_name, metrics in results.items():
        print(f"\n  Task: {task_name}")
        if "error" in metrics:
            print(f"    ERROR: {metrics['error']}")
            continue
        for metric, value in metrics.items():
            marker = "★" if metric == "weighted_score" else " "
            print(f"    {marker} {metric:<35} {value:.4f}")

    overall = report.get("overall_weighted_score", 0.0)
    print(f"\n{'─' * 60}")
    print(f"  Overall weighted score: {overall:.4f}")
    print(f"{'=' * 60}\n")


def save_report(report: dict, path: str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Report saved to: {out}", file=sys.stderr)


def check_min_score(report: dict, min_score: float) -> bool:
    """Return True if overall_weighted_score >= min_score."""
    return report.get("overall_weighted_score", 0.0) >= min_score
