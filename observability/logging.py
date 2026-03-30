"""
OpenTelemetry log bridge — attaches Python log records as span events.

When enabled, every log record emitted via the standard ``logging`` module
is also recorded as an event on the currently-active OTel span, so that
existing ``logger.info(...)`` calls appear in distributed traces without
any code changes at call sites.
"""

import logging

from opentelemetry import trace


class OTelSpanLogHandler(logging.Handler):
    """Logging handler that records log records as OTel span events."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            span = trace.get_current_span()
            if span is None or not span.is_recording():
                return

            span.add_event(
                name="log",
                attributes={
                    "log.level": record.levelname,
                    "log.message": self.format(record),
                    "log.logger": record.name,
                },
            )
        except Exception:
            # Never let telemetry break the application
            pass


def attach_otel_log_handler(level: int = logging.INFO) -> None:
    """Attach the OTel span log handler to the root logger."""
    handler = OTelSpanLogHandler()
    handler.setLevel(level)
    logging.getLogger().addHandler(handler)
