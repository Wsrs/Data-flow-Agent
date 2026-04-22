"""OpenTelemetry tracing setup and node decorator."""
from __future__ import annotations

import os
from functools import wraps
from typing import Any, Callable

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def _setup_tracer() -> trace.Tracer:
    service_name = os.getenv("OTEL_SERVICE_NAME", "dataflow-agent")
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")

    provider = TracerProvider(
        resource=Resource.create({"service.name": service_name})
    )

    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        except Exception:
            pass  # Tracing is best-effort; never crash the agent

    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)


_tracer = _setup_tracer()


def trace_node(span_name: str | None = None) -> Callable:
    """
    Decorator for LangGraph node functions.
    Wraps the async call in an OTel span and attaches job_id as an attribute.
    """
    def decorator(fn: Callable) -> Callable:
        name = span_name or fn.__name__

        @wraps(fn)
        async def wrapper(state: dict, *args: Any, **kwargs: Any) -> Any:
            with _tracer.start_as_current_span(name) as span:
                job_id = state.get("job_id", "unknown")
                span.set_attribute("job_id", job_id)
                span.set_attribute("node", name)
                try:
                    result = await fn(state, *args, **kwargs)
                    span.set_attribute("status", result.get("status", ""))
                    return result
                except Exception as exc:
                    span.record_exception(exc)
                    raise

        return wrapper
    return decorator


def get_tracer() -> trace.Tracer:
    return _tracer
