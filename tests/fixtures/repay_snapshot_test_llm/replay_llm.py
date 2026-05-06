"""ReplayLLM - A mock LLM specialized for replaying conversation snapshots."""

from typing import Any

from .snapshot import SnapshotLoader
from openhands.sdk.testing.test_llm import TestLLM


class ReplayLLM(TestLLM):
    """A mock LLM that loads scripted responses from a conversation snapshot.

    Extends TestLLM by adding a factory method for loading messages directly
    from a persistence directory.
    """

    @classmethod
    def from_persistence(
        cls,
        persistence_dir: str,
        conversation_id: str | None = None,
        *,
        model: str = "test-model",
        usage_id: str = "test-llm",
        **kwargs: Any,
    ) -> "ReplayLLM":
        """Create a ReplayLLM from a conversation persistence snapshot.

        Args:
            persistence_dir: Path to the persistence directory.
            conversation_id: Optional ID to filter for a specific session.
            model: Model name (default: "test-model")
            usage_id: Usage ID for metrics (default: "test-llm")
            **kwargs: Additional LLM configuration options

        Returns:
            A ReplayLLM instance pre-populated with messages from the snapshot.
        """
        resolved_path = SnapshotLoader.resolve_path(persistence_dir, conversation_id)
        events = SnapshotLoader.load_events(resolved_path)
        messages = SnapshotLoader.extract_messages(events)
        return cls(
            model=model,
            usage_id=usage_id,
            scripted_responses=messages,
            **kwargs,
        )
