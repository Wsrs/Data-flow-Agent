"""YAML → TaskConfig loader with profile overlay support."""
from __future__ import annotations

from pathlib import Path

import yaml

from dataflow.schemas.task_config import TaskConfig


def load_task_from_file(yaml_path: str | Path) -> TaskConfig:
    """Load a single TaskConfig from a YAML file."""
    path = Path(yaml_path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return TaskConfig.model_validate(raw)


def apply_profile(config: TaskConfig, profile_path: str | Path) -> TaskConfig:
    """
    Overlay a runtime profile (e.g. production.yaml) onto an existing TaskConfig.
    Only top-level scalar fields present in the profile are overridden.
    """
    path = Path(profile_path)
    profile: dict = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    # Allowed profile overrides
    overrideable = {"llm_model", "max_retries"}
    overrides: dict = {k: v for k, v in profile.items() if k in overrideable}

    if not overrides:
        return config

    return config.model_copy(update=overrides)
