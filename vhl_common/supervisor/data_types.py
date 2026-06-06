from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from vhl_common.urp.abstract_urp import AbstractURPAgent
from vhl_common.urp.data_types import AgentDescriptor


class SupervisorState(Enum):
    """System-wide operational policies/states for the Supervisor."""
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    MAINTENANCE = "MAINTENANCE"
    SHUTDOWN = "SHUTDOWN"


@dataclass
class AgentRecord:
    """The authoritative representation of a running agent managed by the Supervisor."""
    agent: AbstractURPAgent
    descriptor: AgentDescriptor
    active_controller: str
    registered_at: datetime


@dataclass
class ControlClaim:
    """Represents a controller's claim of authority over an agent."""
    controller_id: str
    agent_id: str
    priority: int
