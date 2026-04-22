#!/usr/bin/env python3
"""
CLI script to submit and run a DataFlow-Agent cleaning job locally.

Usage:
    python scripts/run_job.py --task deduplication \
        --input data/sample_dirty.parquet \
        --output data/sample_clean.parquet

    python scripts/run_job.py --task entity_resolution \
        --input data/companies_dirty.parquet \
        --output data/companies_clean.parquet \
        --job-id my-custom-job-id
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

# Add project root to sys.path so script works without `pip install -e .`
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from dataflow.graph.builder import build_graph
from dataflow.tasks.registry import TaskRegistry


async def _run(args: argparse.Namespace) -> int:
    registry = TaskRegistry.get()

    try:
        task_config = registry.get_task(args.task)
    except KeyError:
        available = ", ".join(registry.list_tasks())
        print(f"✗ Unknown task '{args.task}'. Available: {available}", file=sys.stderr)
        return 1

    job_id = args.job_id or f"job-{uuid4().hex[:8]}"
    print(f"▶ Job ID:   {job_id}")
    print(f"  Task:     {args.task}")
    print(f"  Input:    {args.input}")
    print(f"  Output:   {args.output}")
    print()

    graph = build_graph()

    initial_state: dict = {
        "job_id": job_id,
        "task_config": task_config.model_dump(mode="json"),
        "data_path": args.input,
        "output_path": args.output,
        "quality_report": None,
        "cleaning_scripts": [],
        "execution_results": [],
        "status": "pending",
        "retry_count": 0,
        "max_retries": task_config.max_retries,
        "circuit_breaker_triggered": False,
        "audit_log": [],
        "error_messages": [],
    }

    try:
        final_state = await graph.ainvoke(initial_state)
    except KeyboardInterrupt:
        print("\n⚠ Interrupted by user.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"✗ Pipeline error: {exc}", file=sys.stderr)
        return 1

    final_status = final_state.get("status", "unknown")
    exec_results = final_state.get("execution_results", [])
    last = exec_results[-1] if exec_results else {}

    print(f"{'─' * 50}")
    print(f"Status:       {final_status.upper()}")

    if final_status == "complete":
        print(f"Rows before:  {last.get('rows_before', 'n/a')}")
        print(f"Rows after:   {last.get('rows_after', 'n/a')}")
        print(f"Flagged:      {last.get('flagged_record_count', 0)}")
        print(f"Time:         {last.get('execution_time_seconds', 0):.1f}s")
        print(f"Output:       {args.output}")
        rc = 0

    elif final_status == "human_review":
        print("⚠  Human review required.")
        print(f"Reason: {last.get('stderr_excerpt', 'circuit breaker triggered')}")
        rc = 2

    else:
        print(f"✗ Job failed: {final_state.get('error_messages', [])}")
        rc = 1

    if args.dump_audit:
        print(f"\n{'─' * 50}")
        print("Audit log:")
        for entry in final_state.get("audit_log", []):
            print(f"  [{entry.get('node', '?'):20s}] {entry.get('status'):10s} {entry.get('detail', '')}")

    return rc


def cli() -> None:
    parser = argparse.ArgumentParser(
        prog="dataflow-run",
        description="Run a DataFlow-Agent cleaning job",
    )
    parser.add_argument("--task",       required=True, help="Task name (e.g. deduplication)")
    parser.add_argument("--input",      required=True, help="Input data file (.parquet/.csv)")
    parser.add_argument("--output",     required=True, help="Output file path (.parquet)")
    parser.add_argument("--job-id",     default=None,  help="Custom job ID (auto-generated if omitted)")
    parser.add_argument("--dump-audit", action="store_true", help="Print full audit log after completion")
    args = parser.parse_args()

    rc = asyncio.run(_run(args))
    sys.exit(rc)


if __name__ == "__main__":
    cli()
