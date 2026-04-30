import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timezone
import uuid

@dataclass
class AgentDescriptor:
    agent_id: str
    name: str
    version: str
    capabilities: List[str]
    accepted_message_types: List[str]

@dataclass
class MessageEnvelope:
    type: str
    payload: Any
    sender: str
    receiver: str
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class EventEnvelope:
    type: str
    payload: Any
    source_agent_id: str
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AgentState:
    # URP's tracking of the internal state/session. 
    # For LangGraph, we track the thread_id to maintain conversational state.
    session_id: str
    status: str = "INITIALIZED"
    internal_memory: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentContext:
    workspace_handle: Any = None
    tool_registry: Any = None
    llm_adapter: Any = None
    persistent_memory_handle: Any = None
    configuration: Dict[str, Any] = field(default_factory=dict)