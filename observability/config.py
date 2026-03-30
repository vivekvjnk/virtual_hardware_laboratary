"""
Observability configuration — reads environment variables for OTel setup.
"""

import os
from dataclasses import dataclass
from enum import Enum


class OtelBackend(Enum):
    """Supported observability backend modes."""
    LAMINAR = "laminar"
    GOOGLE_CLOUD = "google_cloud"
    NONE = "none"


@dataclass(frozen=True)
class ObservabilityConfig:
    """Configuration for the observability layer."""
    backend: OtelBackend
    service_name: str
    collector_endpoint: str

    @classmethod
    def from_env(cls) -> "ObservabilityConfig":
        """Build config from environment variables."""
        backend_raw = os.getenv("OTEL_BACKEND", "none").lower().strip()
        try:
            backend = OtelBackend(backend_raw)
        except ValueError:
            backend = OtelBackend.NONE

        return cls(
            backend=backend,
            service_name=os.getenv("OTEL_SERVICE_NAME", "vhl-agent-backend"),
            collector_endpoint=os.getenv(
                "OTEL_COLLECTOR_ENDPOINT", "http://localhost:4317"
            ),
        )
