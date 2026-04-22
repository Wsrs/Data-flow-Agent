"""
EvaluationRunner – mirrors lm-evaluation-harness evaluator.py.

Usage (CLI):
    python scripts/evaluate.py --tasks deduplication,entity_resolution
    python scripts/evaluate.py --tasks all --min-score 0.85
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from dataflow.evaluation.metrics import METRIC_REGISTRY
from dataflow.graph.builder import build_graph
from dataflow.observability.logger import get_logger
from dataflow.schemas.task_config import TaskConfig
from dataflow.tasks.registry import TaskRegistry

logger = get_logger(__name__)


class EvaluationRunner:
    def __init__(self, task_names: list[str], benchmark_dir: str) -> None:
        self.registry = TaskRegistry.get()
        self.task_names = task_names
        self.benchmark_dir = Path(benchmark_dir)

    async def run(self) -> dict:
        results: dict[str, dict] = {}

        for task_name in self.task_names:
            logger.info("eval_task_start", task=task_name)
            task_config: TaskConfig = self.registry.get_task(task_name)

            dirty = self.benchmark_dir / task_name / f"{task_name}_dirty.parquet"
            output = self.benchmark_dir / task_name / "_eval_output.parquet"

            if not dirty.exists():
                logger.warning("benchmark_missing", task=task_name, path=str(dirty))
                results[task_name] = {"error": f"Benchmark not found: {dirty}"}
                continue

            graph = build_graph()
            job_id = f"eval-{task_name}-{uuid4().hex[:8]}"

            initial_state: dict = {
                "job_id": job_id,
                "task_config": task_config.model_dump(mode="json"),
                "data_path": str(dirty),
                "output_path": str(output),
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
            except Exception as exc:
                logger.error("eval_pipeline_error", task=task_name, error=str(exc))
                results[task_name] = {"error": str(exc)}
                continue

            if final_state["status"] not in ("complete", "human_review"):
                results[task_name] = {
                    "error": f"Pipeline ended with status: {final_state['status']}",
                    "error_messages": final_state.get("error_messages", []),
                }
                continue

            # Compute metrics from the last execution result
            exec_results = final_state.get("execution_results", [])
            last_result = exec_results[-1] if exec_results else {}

            task_metrics: dict[str, float] = {}
            for m_cfg in task_config.metric_list:
                metric = METRIC_REGISTRY.get(m_cfg.metric)
                if metric is None:
                    logger.warning("unknown_metric", metric=m_cfg.metric)
                    continue
                try:
                    value = metric.compute(last_result)
                    task_metrics[m_cfg.metric] = round(float(value), 4)
                except Exception as exc:
                    logger.warning("metric_compute_error", metric=m_cfg.metric, error=str(exc))
                    task_metrics[m_cfg.metric] = 0.0

            # Weighted score
            weighted = sum(
                task_metrics.get(m.metric, 0.0) * m.weight
                for m in task_config.metric_list
            )
            task_metrics["weighted_score"] = round(weighted, 4)

            results[task_name] = task_metrics
            logger.info("eval_task_done", task=task_name, weighted_score=weighted)

        overall = _compute_overall(results)
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "results": results,
            "overall_weighted_score": round(overall, 4),
        }


def _compute_overall(results: dict) -> float:
    scores = [
        v.get("weighted_score", 0.0)
        for v in results.values()
        if isinstance(v, dict) and "error" not in v
    ]
    return sum(scores) / len(scores) if scores else 0.0
