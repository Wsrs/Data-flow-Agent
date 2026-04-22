#!/usr/bin/env python3
"""
Harness evaluation CLI – mirrors EleutherAI lm-evaluation-harness interface.

Usage:
    python scripts/evaluate.py --tasks deduplication,entity_resolution
    python scripts/evaluate.py --tasks all --min-score 0.85
    python scripts/evaluate.py --tasks all --output reports/eval.json --format json
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from dataflow.evaluation.reporter import check_min_score, print_report, save_report
from dataflow.evaluation.runner import EvaluationRunner
from dataflow.tasks.registry import TaskRegistry


async def _run(args: argparse.Namespace) -> int:
    registry = TaskRegistry.get()

    try:
        task_names = registry.resolve_task_names(args.tasks)
    except KeyError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1

    benchmark_dir = args.benchmark_dir or os.getenv("BENCHMARK_DIR", "./benchmarks")

    print(f"Running evaluation on tasks: {task_names}")
    print(f"Benchmark dir: {benchmark_dir}\n")

    runner = EvaluationRunner(task_names=task_names, benchmark_dir=benchmark_dir)

    try:
        report = await runner.run()
    except Exception as exc:
        print(f"✗ Evaluation error: {exc}", file=sys.stderr)
        return 1

    print_report(report, output_format=args.format)

    if args.output:
        save_report(report, args.output)

    if args.min_score is not None:
        passed = check_min_score(report, args.min_score)
        if not passed:
            overall = report.get("overall_weighted_score", 0.0)
            print(
                f"✗ Min-score gate FAILED: {overall:.4f} < {args.min_score}",
                file=sys.stderr,
            )
            return 1
        print(f"✓ Min-score gate PASSED: {report.get('overall_weighted_score', 0):.4f} >= {args.min_score}")

    return 0


def cli() -> None:
    parser = argparse.ArgumentParser(
        prog="dataflow-eval",
        description="Run DataFlow-Agent harness evaluation",
    )
    parser.add_argument(
        "--tasks",
        default="all",
        help="Comma-separated task names or 'all' (default: all)",
    )
    parser.add_argument(
        "--benchmark-dir",
        default=None,
        help="Path to benchmark directory (default: $BENCHMARK_DIR or ./benchmarks)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Save JSON report to this path",
    )
    parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=None,
        help="Fail (exit 1) if overall_weighted_score < MIN_SCORE",
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(_run(args)))


if __name__ == "__main__":
    cli()
