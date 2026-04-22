"""
TaskRegistry – global singleton task registry.

Mirrors lm-evaluation-harness TaskManager:
  - Auto-loads all YAML configs from configs/tasks/ at first access.
  - Supports runtime registration of custom tasks.
  - Provides the CLI --tasks interface.
"""
from __future__ import annotations

import threading
from pathlib import Path

import yaml

from dataflow.schemas.task_config import TaskConfig


class TaskRegistry:
    _instance: TaskRegistry | None = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        self._tasks: dict[str, TaskConfig] = {}

    # ── Singleton ─────────────────────────────────────────────────────────────

    @classmethod
    def get(cls) -> TaskRegistry:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = cls()
                    inst._load_builtin_tasks()
                    cls._instance = inst
        return cls._instance

    # ── Loading ───────────────────────────────────────────────────────────────

    def _load_builtin_tasks(self) -> None:
        config_dir = Path(__file__).parent.parent.parent / "configs" / "tasks"
        if not config_dir.exists():
            return
        for yaml_file in sorted(config_dir.glob("*.yaml")):
            try:
                raw = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
                config = TaskConfig.model_validate(raw)
                self._tasks[config.task] = config
            except Exception as exc:  # noqa: BLE001
                import warnings
                warnings.warn(f"Failed to load task config {yaml_file}: {exc}")

    # ── Public API ────────────────────────────────────────────────────────────

    def get_task(self, name: str) -> TaskConfig:
        if name not in self._tasks:
            available = sorted(self._tasks.keys())
            raise KeyError(
                f"Task '{name}' not found in registry. "
                f"Available tasks: {available}"
            )
        return self._tasks[name]

    def list_tasks(self) -> list[str]:
        return sorted(self._tasks.keys())

    def register(self, config: TaskConfig, *, overwrite: bool = False) -> None:
        """Register a task at runtime (e.g. for custom / test tasks)."""
        if config.task in self._tasks and not overwrite:
            raise ValueError(
                f"Task '{config.task}' is already registered. "
                "Pass overwrite=True to replace it."
            )
        self._tasks[config.task] = config

    def resolve_task_names(self, spec: str) -> list[str]:
        """
        Resolve a comma-separated task spec like lm-eval --tasks.
        'all' returns every registered task.
        """
        if spec.strip().lower() == "all":
            return self.list_tasks()
        names = [t.strip() for t in spec.split(",") if t.strip()]
        for name in names:
            self.get_task(name)  # validate early
        return names
