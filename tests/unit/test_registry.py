"""Unit tests for TaskRegistry."""
import pytest

from dataflow.schemas.task_config import (
    CleaningStrategyConfig,
    TaskConfig,
)
from dataflow.tasks.registry import TaskRegistry


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset the registry singleton between tests."""
    TaskRegistry._instance = None
    yield
    TaskRegistry._instance = None


def _make_config(name: str) -> TaskConfig:
    return TaskConfig(
        task=name,
        version=1,
        description="Test task",
        cleaning_strategy=CleaningStrategyConfig(type="deduplication"),
    )


class TestTaskRegistry:
    def test_singleton(self):
        r1 = TaskRegistry.get()
        r2 = TaskRegistry.get()
        assert r1 is r2

    def test_loads_builtin_tasks(self):
        registry = TaskRegistry.get()
        tasks = registry.list_tasks()
        assert "deduplication" in tasks
        assert "entity_resolution" in tasks
        assert "format_standardization" in tasks
        assert "missing_value_imputation" in tasks
        assert "type_coercion" in tasks

    def test_get_existing_task(self):
        registry = TaskRegistry.get()
        cfg = registry.get_task("deduplication")
        assert cfg.task == "deduplication"
        assert cfg.version >= 1

    def test_get_missing_task_raises(self):
        registry = TaskRegistry.get()
        with pytest.raises(KeyError, match="not found"):
            registry.get_task("nonexistent_task_xyz")

    def test_register_custom_task(self):
        registry = TaskRegistry.get()
        custom = _make_config("custom_clean")
        registry.register(custom)
        assert "custom_clean" in registry.list_tasks()
        assert registry.get_task("custom_clean").task == "custom_clean"

    def test_register_duplicate_raises(self):
        registry = TaskRegistry.get()
        custom = _make_config("custom_clean")
        registry.register(custom)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(custom, overwrite=False)

    def test_register_overwrite(self):
        registry = TaskRegistry.get()
        custom_v1 = _make_config("custom_clean")
        custom_v2 = _make_config("custom_clean")
        custom_v2 = custom_v2.model_copy(update={"version": 2})
        registry.register(custom_v1)
        registry.register(custom_v2, overwrite=True)
        assert registry.get_task("custom_clean").version == 2

    def test_resolve_task_names_all(self):
        registry = TaskRegistry.get()
        names = registry.resolve_task_names("all")
        assert set(names) == set(registry.list_tasks())

    def test_resolve_task_names_csv(self):
        registry = TaskRegistry.get()
        names = registry.resolve_task_names("deduplication, entity_resolution")
        assert "deduplication" in names
        assert "entity_resolution" in names
        assert len(names) == 2

    def test_resolve_invalid_task_raises(self):
        registry = TaskRegistry.get()
        with pytest.raises(KeyError):
            registry.resolve_task_names("deduplication,bad_task_xyz")
