"""Utility for loading and processing conversation snapshots."""

import os
import uuid
from typing import Any

from openhands.sdk.conversation.event_store import EventLog
from openhands.sdk.conversation.persistence_const import EVENTS_DIR
from openhands.sdk.event import ActionEvent, Event, MessageEvent, ObservationEvent
from openhands.sdk.io import LocalFileStore
from openhands.sdk.llm.message import Message
from openhands.sdk.logger import get_logger

logger = get_logger(__name__)


class SnapshotLoader:
    """Helper class to discover and load events from persistence snapshots."""

    @staticmethod
    def resolve_path(base_path: str, conversation_id: str | None = None) -> str:
        """Resolve the actual conversation directory from a base path.

        Args:
            base_path: Base directory containing snapshots.
            conversation_id: Optional UUID or folder name for a specific session.

        Returns:
            The resolved absolute path to the conversation directory.
        """
        from openhands.sdk.conversation.base import BaseConversation

        if conversation_id:
            try:
                conv_id = uuid.UUID(conversation_id)
                return BaseConversation.get_persistence_dir(base_path, conv_id)
            except ValueError:
                # Fallback if ID is not a valid UUID string
                return os.path.join(base_path, conversation_id)

        # Discovery logic: check if base_path is a direct conversation dir
        if os.path.exists(os.path.join(base_path, EVENTS_DIR)):
            return base_path

        # Scan subdirectories for the first one containing an events/ folder
        try:
            subdirs = [
                d
                for d in os.listdir(base_path)
                if os.path.isdir(os.path.join(base_path, d))
            ]
            for d in subdirs:
                potential = os.path.join(base_path, d)
                if os.path.exists(os.path.join(potential, EVENTS_DIR)):
                    logger.debug(f"Resolved snapshot subdirectory: {potential}")
                    return potential
        except Exception as e:
            logger.debug(f"Error scanning subdirectories in {base_path}: {e}")

        return base_path

    @staticmethod
    def load_events(path: str) -> list[Event]:
        """Load all events from a resolved persistence path."""
        try:
            fs = LocalFileStore(path)
            return list(EventLog(fs))
        except Exception as e:
            logger.warning(f"Failed to load snapshot from {path}: {e}")
            return []

    @staticmethod
    def extract_messages(events: list[Event]) -> list[Message]:
        """Extract assistant responses from events for re-injection into TestLLM."""
        messages: list[Message] = []
        for event in events:
            if isinstance(event, ActionEvent) and event.source == "agent":
                if event.tool_call:
                    # Construct a message containing the tool call
                    messages.append(
                        Message(
                            role="assistant",
                            content=event.thought if event.thought else [],
                            tool_calls=[event.tool_call],
                        )
                    )
            elif isinstance(event, MessageEvent) and event.source == "agent":
                messages.append(event.llm_message)
        return messages

    @staticmethod
    def extract_expected_observations(
        events: list[Event],
    ) -> dict[str, list[ObservationEvent]]:
        """Map tool_call_ids to their recorded observations."""
        observations: dict[str, list[ObservationEvent]] = {}
        for event in events:
            if isinstance(event, ObservationEvent) and event.tool_call_id:
                if event.tool_call_id not in observations:
                    observations[event.tool_call_id] = []
                observations[event.tool_call_id].append(event)
        return observations
