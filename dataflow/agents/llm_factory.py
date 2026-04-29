"""
LLM factory – resolves the correct ChatOpenAI-compatible client from env vars.

Supports:
  - OpenAI / any OpenAI-compatible cloud API (default)
  - Ollama local models  (LLM_PROVIDER=ollama)

Environment variables
─────────────────────
  LLM_PROVIDER   : "openai" | "ollama"  (default: openai)
  LLM_MODEL      : model name           (default: gpt-4o / qwen3-vl:8b)
  LLM_BASE_URL   : override API base URL
  LLM_API_KEY    : API key (use "ollama" as dummy for Ollama)
  LLM_TEMPERATURE: sampling temperature (default: 0)
  LLM_TIMEOUT    : request timeout in seconds (default: 120)
"""
from __future__ import annotations

import os

from langchain_openai import ChatOpenAI

_OLLAMA_BASE_URL = "http://localhost:11434/v1"
_OLLAMA_DEFAULT_MODEL = "qwen3-vl:8b"
_OPENAI_DEFAULT_MODEL = "gpt-4o"


def build_llm(
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    temperature: float | None = None,
    timeout: int | None = None,
) -> ChatOpenAI:
    """
    Return a ChatOpenAI instance configured from env vars,
    with optional per-call overrides.
    """
    provider = os.getenv("LLM_PROVIDER", "openai").lower()

    # ── Resolve defaults per provider ─────────────────────────────────────────
    if provider == "ollama":
        resolved_base_url = base_url or os.getenv("LLM_BASE_URL", _OLLAMA_BASE_URL)
        resolved_model    = model    or os.getenv("LLM_MODEL",    _OLLAMA_DEFAULT_MODEL)
        resolved_api_key  = api_key  or os.getenv("LLM_API_KEY",  "ollama")
    else:
        resolved_base_url = base_url or os.getenv("LLM_BASE_URL") or None
        resolved_model    = model    or os.getenv("LLM_MODEL",    _OPENAI_DEFAULT_MODEL)
        resolved_api_key  = api_key  or os.getenv("LLM_API_KEY")  or None

    resolved_temp    = temperature if temperature is not None else float(os.getenv("LLM_TEMPERATURE", "0"))
    resolved_timeout = timeout     if timeout     is not None else int(os.getenv("LLM_TIMEOUT",      "120"))

    kwargs: dict = dict(
        model       = resolved_model,
        temperature = resolved_temp,
        timeout     = resolved_timeout,
    )
    if resolved_base_url:
        kwargs["base_url"] = resolved_base_url
    if resolved_api_key:
        kwargs["api_key"] = resolved_api_key

    return ChatOpenAI(**kwargs)


def get_provider_info() -> dict:
    """Return current LLM configuration for observability."""
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    model    = os.getenv("LLM_MODEL", _OLLAMA_DEFAULT_MODEL if provider == "ollama" else _OPENAI_DEFAULT_MODEL)
    base_url = os.getenv("LLM_BASE_URL", _OLLAMA_BASE_URL if provider == "ollama" else "https://api.openai.com/v1")
    return {"provider": provider, "model": model, "base_url": base_url}
