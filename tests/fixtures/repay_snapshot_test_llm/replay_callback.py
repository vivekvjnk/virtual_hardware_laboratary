"""Callback for monitoring observation drift during replay."""

import json

from openhands.sdk.event import Event, ObservationEvent
from openhands.sdk.logger import get_logger

logger = get_logger(__name__)


class ObservationDriftCallback:
    """Interceptor that compares live observations with recorded ones.

    Logs any discrepancies (drift) to a JSONL file.
    """

    def __init__(
        self,
        expected_observations: dict[str, list[ObservationEvent]],
        drift_log_path: str | None = None,
    ) -> None:
        """Initialize the callback.

        Args:
            expected_observations: Map of tool_call_id -> list of recorded observations.
            drift_log_path: Optional path to write drift logs.
        """
        self.expected_observations = expected_observations
        self.drift_log_path = drift_log_path

    def __call__(self, event: Event) -> None:
        """Intercept ObservationEvents and check for drift."""
        if not isinstance(event, ObservationEvent) or not event.tool_call_id:
            return

        expected = self.expected_observations.get(event.tool_call_id, [])
        # Find the matching observation by index or content
        # For simplicity in this implementation, we assume 1:1 matching by tool_call_id
        # if multiple observations exist for one tool call.
        # In a more robust version, we could use a counter per tool_call_id.

        if self.drift_log_path:
            drift = "No drift"
            if not expected:
                drift = "Drift detected: No expected observation found for this tool call."
            else:
                # Basic drift check logic
                if self._check_drift([event], expected):
                    drift = {
                        "Drift Present": True,
                        "Expected": [obs.model_dump(mode="json") for obs in expected],
                    }

            log_entry = {
                "Tool": event.tool_name,
                "ToolCallID": event.tool_call_id,
                "Actual Observation": event.model_dump(mode="json"),
                "Drift from expected observation": drift,
            }

            try:
                with open(self.drift_log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry) + "\n")
            except Exception as e:
                logger.error(f"Failed to write drift log: {e}")

    def _check_drift(
        self, actual: list[ObservationEvent], expected: list[ObservationEvent]
    ) -> bool:
        """Compare lists of observations for drift, ignoring metadata."""
        if len(actual) != len(expected):
            return True

        for a, e in zip(actual, expected):
            a_dict = a.model_dump(mode="json")
            e_dict = e.model_dump(mode="json")

            # Ignore standard metadata fields that differ between runs
            ignore_keys = {"id", "timestamp", "action_id", "tool_call_id"}
            for key in ignore_keys:
                a_dict.pop(key, None)
                e_dict.pop(key, None)

            if a_dict != e_dict:
                return True

        return False
