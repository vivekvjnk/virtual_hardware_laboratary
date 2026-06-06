from typing import Any, Dict
from vhl_common.urp.abstract_urp import AbstractURPAgent
from .controllers.abstract_controller import AbstractController


class Supervisor:
    """The persistent control plane for all active URP agent instances."""

    def __init__(self) -> None:
        pass

    def attach_agent(self, agent: AbstractURPAgent) -> None:
        """Attach an active agent to the Supervisor registry."""
        pass

    def detach_agent(self, agent_id: str) -> None:
        """Detach an agent from the Supervisor registry."""
        pass

    def register_controller(self, controller: AbstractController) -> None:
        """Register a controller plugin with the Supervisor."""
        pass

    async def claim(self, controller_id: str, agent_id: str) -> bool:
        """Request authority over a specific agent for a controller."""
        return False

    async def release(self, controller_id: str, agent_id: str) -> None:
        """Release authority over a specific agent for a controller."""
        pass

    def get_agent_state(self, agent_id: str) -> dict:
        """Get the read-only state of a specific agent."""
        return {}

    def get_active_controller(self, agent_id: str) -> str:
        """Get the ID of the active controller governing the agent."""
        return ""

    async def send(self, agent_id: str, message: Any) -> None:
        """Route a message to an agent on behalf of its active controller."""
        pass

    def get_system_state(self) -> dict:
        """Get the system-wide operational state telemetry."""
        return {}
