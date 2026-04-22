"""BaseCleaningTask – abstract base class for all cleaning tasks."""
from __future__ import annotations

from abc import ABC, abstractmethod

from dataflow.schemas.task_config import TaskConfig
from dataflow.schemas.report import DataQualityReport
from dataflow.schemas.execution import ExecutionResult


class BaseCleaningTask(ABC):
    """
    Mirrors the lm-evaluation-harness Task base class.
    Each concrete task type corresponds to a YAML config + this base contract.
    """

    def __init__(self, config: TaskConfig) -> None:
        self.config = config

    @property
    def task_name(self) -> str:
        return self.config.task

    @property
    def version(self) -> int:
        return self.config.version

    @abstractmethod
    def validate_report(self, report: DataQualityReport) -> list[str]:
        """Return a list of warnings if the report indicates this task may be ill-suited."""
        ...

    @abstractmethod
    def score(self, result: ExecutionResult) -> float:
        """Compute a [0, 1] weighted score for the execution result."""
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(task={self.task_name!r}, version={self.version})"
