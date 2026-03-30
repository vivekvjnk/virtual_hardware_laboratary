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

# ---------------------------------------------------------------------------
# Re-export Traceloop decorators for convenience.
# When tracing is disabled these are replaced with no-op passthrough
# decorators so call-sites never need to care about the state.
# ---------------------------------------------------------------------------

def _noop_decorator(name: str = "", **kwargs):
    """No-op decorator returned when tracing is disabled."""
    def decorator(fn):
        return fn
    return decorator

# Defaults — will be overwritten by init_observability() when tracing is on.
workflow = _noop_decorator
task = _noop_decorator


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

    # Expose real decorators now that tracing is initialised
    workflow = _wf
    task = _tk

    # Attach the OTel span log handler
    from observability.logging import attach_otel_log_handler
    attach_otel_log_handler()

    logger.info(
        "[observability] OpenLLMetry initialised — traces → %s",
        config.collector_endpoint,
    )
