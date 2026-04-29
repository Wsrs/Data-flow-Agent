"""
Memory module – long/short-term memory with template matching.

Storage: JSON files in MEMORY_DIR (default: ./data/memory/).
Short-term entries expire after SESSION_TTL_HOURS (default 24 h).
Long-term entries are persistent.
Template matching uses TF-IDF-like tag intersection scoring.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Optional

MEMORY_DIR = Path(os.getenv("MEMORY_DIR", "./data/memory"))
SESSION_TTL_HOURS = int(os.getenv("SESSION_TTL_HOURS", "24"))

MEMORY_FILE   = MEMORY_DIR / "memories.json"
TEMPLATE_FILE = MEMORY_DIR / "templates.json"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(path: Path, data: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


# ── Memory CRUD ───────────────────────────────────────────────────────────────

def add_memory(
    *,
    type: str,                    # "short" | "long"
    category: str,
    task_name: str,
    summary: str,
    tags: list[str],
    score: float = 0.0,
    job_id: Optional[str] = None,
) -> dict:
    entries = _load(MEMORY_FILE)
    entry = {
        "id":         str(uuid.uuid4()),
        "type":       type,
        "category":   category,
        "task_name":  task_name,
        "summary":    summary,
        "tags":       tags,
        "score":      round(score, 4),
        "created_at": _now_iso(),
        "last_used":  _now_iso(),
        "use_count":  0,
        "job_id":     job_id,
    }
    entries.append(entry)
    _save(MEMORY_FILE, entries)
    return entry


def list_memories(type_filter: Optional[str] = None) -> list[dict]:
    entries = _load(MEMORY_FILE)
    now = datetime.now(UTC)
    result = []
    for e in entries:
        if type_filter and e.get("type") != type_filter:
            continue
        # Expire short-term entries
        if e.get("type") == "short":
            created = datetime.fromisoformat(e["created_at"])
            if (now - created) > timedelta(hours=SESSION_TTL_HOURS):
                continue
        result.append(e)
    return sorted(result, key=lambda x: x.get("score", 0), reverse=True)


def search_memories(query: str) -> list[dict]:
    q = query.lower().split()
    entries = list_memories()
    def score(e: dict) -> float:
        text = (e.get("summary", "") + " " + " ".join(e.get("tags", []))).lower()
        return sum(1 for w in q if w in text) / max(len(q), 1)
    ranked = [(e, score(e)) for e in entries if score(e) > 0]
    return [e for e, _ in sorted(ranked, key=lambda x: x[1], reverse=True)]


def delete_memory(memory_id: str) -> bool:
    entries = _load(MEMORY_FILE)
    new = [e for e in entries if e["id"] != memory_id]
    if len(new) == len(entries):
        return False
    _save(MEMORY_FILE, new)
    return True


def mark_used(memory_id: str) -> None:
    entries = _load(MEMORY_FILE)
    for e in entries:
        if e["id"] == memory_id:
            e["use_count"] = e.get("use_count", 0) + 1
            e["last_used"]  = _now_iso()
    _save(MEMORY_FILE, entries)


# ── Templates ─────────────────────────────────────────────────────────────────

def add_template(
    *,
    name: str,
    task_name: str,
    description: str,
    tags: list[str],
    config_snippet: dict,
    score: float = 0.0,
) -> dict:
    templates = _load(TEMPLATE_FILE)
    tmpl = {
        "id":             str(uuid.uuid4()),
        "name":           name,
        "task_name":      task_name,
        "description":    description,
        "tags":           tags,
        "config_snippet": config_snippet,
        "score":          round(score, 4),
        "use_count":      0,
        "created_at":     _now_iso(),
    }
    templates.append(tmpl)
    _save(TEMPLATE_FILE, templates)
    return tmpl


def list_templates(task_filter: Optional[str] = None) -> list[dict]:
    templates = _load(TEMPLATE_FILE)
    if task_filter:
        templates = [t for t in templates if t.get("task_name") == task_filter]
    return sorted(templates, key=lambda t: t.get("score", 0), reverse=True)


def get_template(template_id: str) -> Optional[dict]:
    for t in _load(TEMPLATE_FILE):
        if t["id"] == template_id:
            # Increment use_count
            templates = _load(TEMPLATE_FILE)
            for tmpl in templates:
                if tmpl["id"] == template_id:
                    tmpl["use_count"] = tmpl.get("use_count", 0) + 1
            _save(TEMPLATE_FILE, templates)
            return t
    return None


def find_similar_templates(task_name: str, tags: list[str]) -> list[dict]:
    """Return templates ordered by tag-overlap score."""
    tag_set = set(tags)
    results = []
    for t in list_templates(task_filter=task_name):
        overlap = len(tag_set & set(t.get("tags", [])))
        if overlap > 0:
            results.append((t, overlap))
    return [t for t, _ in sorted(results, key=lambda x: x[1], reverse=True)]


# ── Auto-seed demo data if empty ──────────────────────────────────────────────

def _seed_demo() -> None:
    if _load(MEMORY_FILE) or _load(TEMPLATE_FILE):
        return
    add_memory(type="long", category="pattern", task_name="entity_resolution",
               summary="企业名称字段常含括号缩写，模糊匹配阈值建议 0.85 以上。",
               tags=["entity", "fuzzy", "company"], score=0.92)
    add_memory(type="long", category="pattern", task_name="deduplication",
               summary="订单表按 order_id + customer_id 组合键去重，可保留 99.8% 有效行。",
               tags=["dedup", "order", "composite-key"], score=0.88)
    add_memory(type="short", category="session", task_name="format_standardization",
               summary="本次 session 处理电话号码格式，统一为 +86-xxx-xxxx-xxxx。",
               tags=["phone", "format", "cn"], score=0.75)
    add_template(name="企业实体消歧 · 高精度", task_name="entity_resolution",
                 description="适合企业数据库中公司名称消歧，pair-F1 目标 ≥ 0.88。",
                 tags=["company", "fuzzy", "high-precision"],
                 config_snippet={"fuzzy_threshold": 0.85, "block_key": "company_prefix", "max_candidates": 10},
                 score=4.8)
    add_template(name="订单去重 · 复合键", task_name="deduplication",
                 description="以 order_id + customer_id 为复合主键，精确去重。",
                 tags=["order", "composite-key", "exact"],
                 config_snippet={"key_columns": ["order_id", "customer_id"], "strategy": "exact"},
                 score=4.5)
    add_template(name="缺失值统计插补 · 中位数", task_name="missing_value_imputation",
                 description="数值型字段用列中位数插补，分类字段用众数。",
                 tags=["imputation", "median", "mode"],
                 config_snippet={"numeric_strategy": "median", "categorical_strategy": "mode"},
                 score=4.2)


_seed_demo()
