"""
Observability initialisation for VHL Agent Backend.

The app always exports OTLP/gRPC to the OTel Collector sidecar.
Backend routing (Laminar, Google Cloud) is handled by the collector config,
keeping this layer deliberately thin.

Public API::

    from observability import init_observability, workflow, task
"""

import logging

from observability.config import ObservabilityConfig, OtelBackend

logger = logging.getLogger(__name__)

import functools
import asyncio
from typing import Any, Callable, Optional, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

class DecoratorProxy:
    """
    A late-binding proxy for Traceloop decorators.
    
    This allows modules to import @workflow and @task at import time (before
    init_observability() is called). When the decorated functions are eventually
    called, they will use the real Traceloop decorators if they have been
    initialized, otherwise they will fall back to a no-op.
    """
    def __init__(self, type_name: str):
        self._type_name = type_name
        self._real_decorator: Optional[Callable] = None

    def __call__(self, name: Optional[str] = None, **kwargs) -> Callable[[F], F]:
        def decorator(fn: F) -> F:
            # Cache the decorated version once initialized
            decorated_fn_cached = None

            if asyncio.iscoroutinefunction(fn):
                @functools.wraps(fn)
                async def async_wrapper(*fargs, **fkwargs):
                    nonlocal decorated_fn_cached
                    if self._real_decorator:
                        if decorated_fn_cached is None:
                            decorated_fn_cached = self._real_decorator(name=name, **kwargs)(fn)
                        return await decorated_fn_cached(*fargs, **fkwargs)
                    return await fn(*fargs, **fkwargs)
                return async_wrapper # type: ignore
            else:
                @functools.wraps(fn)
                def sync_wrapper(*fargs, **fkwargs):
                    nonlocal decorated_fn_cached
                    if self._real_decorator:
                        if decorated_fn_cached is None:
                            decorated_fn_cached = self._real_decorator(name=name, **kwargs)(fn)
                        return decorated_fn_cached(*fargs, **fkwargs)
                    return fn(*fargs, **fkwargs)
                return sync_wrapper # type: ignore
        return decorator

# Proxies — these are what modules import
workflow = DecoratorProxy("workflow")
task = DecoratorProxy("task")

def inject_context(carrier: dict) -> None:
    """Inject current OTel context into a dictionary carrier."""
    try:
        from opentelemetry import propagate
        propagate.inject(carrier)
    except ImportError:
        pass

def extract_context(carrier: dict):
    """Extract OTel context from a dictionary carrier."""
    try:
        from opentelemetry import propagate
        return propagate.extract(carrier)
    except ImportError:
        return None

def attach_context(ctx):
    """Attach a previously extracted context to the current task."""
    if ctx:
        try:
            from opentelemetry import context
            return context.attach(ctx)
        except ImportError:
            pass
    return None

def detach_context(token):
    """Detach a context token."""
    if token:
        try:
            from opentelemetry import context
            context.detach(token)
        except ImportError:
            pass


def init_observability() -> None:
    """
    Initialise OpenLLMetry tracing.

    - Reads configuration from environment variables.
    - If OTEL_BACKEND is ``none``, tracing is silently disabled.
    - Otherwise, creates an OTLP/gRPC span exporter pointing at the
      collector sidecar and passes it to ``Traceloop.init()``.
    - Attaches an OTel log handler so existing ``logger.info()`` calls
      are captured as span events.
    - Re-exports ``workflow`` and ``task`` decorators from Traceloop.
    """
    global workflow, task

    config = ObservabilityConfig.from_env()

    if config.backend is OtelBackend.NONE:
        logger.info("[observability] OTEL_BACKEND=none — tracing disabled.")
        return

    # ------------------------------------------------------------------
    # Lazy imports so that these packages are only required when tracing
    # is actually enabled.
    # ------------------------------------------------------------------
    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from traceloop.sdk import Traceloop
        from traceloop.sdk.decorators import workflow as _wf, task as _tk
    except ImportError as exc:
        logger.warning(
            "[observability] Required packages not installed (%s). "
            "Tracing will be disabled.",
            exc,
        )
        return

    logger.info(
        "[observability] Initialising OpenLLMetry — backend=%s, "
        "collector=%s, service=%s",
        config.backend.value,
        config.collector_endpoint,
        config.service_name,
    )

    exporter = OTLPSpanExporter(
        endpoint=config.collector_endpoint,
        insecure=True,  # Collector sidecar runs on the same host / pod
    )

    Traceloop.init(
        app_name=config.service_name,
        exporter=exporter,
        disable_batch=False,  # Let the SDK batch before sending to collector
    )

    # Expose real decorators now that tracing is initialised by setting them 
    # on the proxy objects.
    workflow._real_decorator = _wf
    task._real_decorator = _tk

    # Attach the OTel span log handler
    from observability.logging import attach_otel_log_handler
    attach_otel_log_handler()

    logger.info(
        "[observability] OpenLLMetry initialised — traces → %s",
        config.collector_endpoint,
    )
