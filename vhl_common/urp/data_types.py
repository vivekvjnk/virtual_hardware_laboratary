from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timezone
import uuid
from enum import Enum

class AgentStatus(Enum):
    """Strict state machine enforcement per URP Section 2."""
    UNINITIALIZED = "UNINITIALIZED"
    INITIALIZED = "INITIALIZED"
    WAITING = "WAITING"
    PROCESSING = "PROCESSING"
    ERROR = "ERROR"
    TERMINATED = "TERMINATED"

class LastTaskOutcome(Enum):
    """"""
    NONE = "NONE"
    WAITING_FOR_USER_INPUT = "WAITING_FOR_USER_INPUT"
    TASK_FAILED = "TASK_FAILED"
    TASK_COMPLETED = "TASK_COMPLETED"

@dataclass
class ProcessResultPayload:
    text: str

@dataclass
class ProcessResult:
    outcome: LastTaskOutcome
    payload: ProcessResultPayload | None = field(default=None)

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
    receiver: str = field(default="HIL")
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AgentState:
    # URP's tracking of the internal state/session. 
    # For LangGraph, we track the thread_id to maintain conversational state.
    session_id: str
    status: AgentStatus = AgentStatus.INITIALIZED
    # Execution outcome of last processed message
    last_task_outcome: LastTaskOutcome = LastTaskOutcome.NONE
    outcome_acknowledged: bool = True
    internal_memory: Dict[str, Any] = field(default_factory=dict)
        
@dataclass
class AgentContext:
    workspace_handle: Any = None
    tool_registry: Any = None
    llm_adapter: Any = None
    persistent_memory_handle: Any = None
    configuration: Dict[str, Any] = field(default_factory=dict)