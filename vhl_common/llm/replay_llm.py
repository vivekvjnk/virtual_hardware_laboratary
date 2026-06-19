"""ReplayLLM - A mock LLM specialized for replaying conversation snapshots."""

from typing import Any

from .snapshot import SnapshotLoader
from openhands.sdk.testing.test_llm import TestLLM
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ReplayLLM(TestLLM):
    """A mock LLM that loads scripted responses from a conversation snapshot.

    Extends TestLLM by adding a factory method for loading messages directly
    from a persistence directory.
    """

    @classmethod
    def from_persistence(
        cls,
        persistence_dir: Path,
        conversation_id: str | None = None,
        *,
        model: str = "test-model",
        usage_id: str = "test-llm",
        current_workspace_root: str | None = None,
        **kwargs: Any,
    ) -> "ReplayLLM":
        """Create a ReplayLLM from a conversation persistence snapshot.

        Args:
            persistence_dir: Path to the persistence directory.
            conversation_id: Optional ID to filter for a specific session.
            model: Model name (default: "test-model")
            usage_id: Usage ID for metrics (default: "test-llm")
            current_workspace: Dynamic workspace path to substitute into replay data
            **kwargs: Additional LLM configuration options

        Returns:
            A ReplayLLM instance pre-populated with messages from the snapshot.
        """
        resolved_path = SnapshotLoader.resolve_path(persistence_dir, conversation_id)
        events = SnapshotLoader.load_events(resolved_path)
        messages = SnapshotLoader.extract_messages(events)
        
        # Dynamically replace the old workspace path with the current workspace in tool call arguments
        if current_workspace_root:
            import re
            # Matches various /tmp/ paths used in tests, including vhl_e2e_workspace and pytest

            # 1. Clean the new workspace path to ensure no accidental trailing slash
            clean_workspace = current_workspace_root.rstrip('/')
            
            # 2. Match everything from /tmp/ up to /Workspace (including an optional trailing slash)
            pattern = re.compile(r'/tmp/(?:vhl_e2e_workspace_[^/]+|pytest-of-[^/]+/pytest-[^/]+)/[^/]+/')
            
            for msg in messages:
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        if hasattr(tc, 'arguments') and tc.arguments:
                            logger.info(f"[ReplayLLM.from_persistence] tc.arguments before modification: {tc.arguments}")             
                            tc.arguments = pattern.sub(f"{clean_workspace}/", tc.arguments)
                            logger.info(f"[ReplayLLM.from_persistence] modified tc.arguments: {tc.arguments}")                  
        return cls(
            model=model,
            usage_id=usage_id,
            scripted_responses=messages,
            **kwargs,
        )
