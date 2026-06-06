from typing import Any, Dict
from datetime import datetime
from vhl_common.urp.abstract_urp import AbstractURPAgent
from .controllers.abstract_controller import AbstractController
from .controllers.default_controller import DefaultController
from .data_types import AgentRecord, ControlClaim
from .exceptions import (
    AgentNotFoundError,
    AgentAlreadyExistsError,
    ControllerNotFoundError,
    ControllerAlreadyExistsError,
    ControlClaimError,
)


class Supervisor:
    """The persistent control plane for all active URP agent instances."""

    def __init__(self) -> None:
        self._agents: Dict[str, AgentRecord] = {}
        self._controllers: Dict[str, AbstractController] = {}
        # Mapping from agent_id -> controller_id -> ControlClaim
        self._claims: Dict[str, Dict[str, ControlClaim]] = {}

        # Invariant 5: DefaultController governs every unclaimed agent.
        # This controller is automatically attached during Supervisor initialization.
        self._default_controller = DefaultController()
        self.register_controller(self._default_controller)

    def attach_agent(self, agent: AbstractURPAgent) -> None:
        """Attach an active agent to the Supervisor registry."""
        if agent is None:
            return
        agent_id = agent.descriptor.agent_id
        if agent_id in self._agents:
            raise AgentAlreadyExistsError(f"Agent with ID '{agent_id}' is already registered.")

        # Every newly attached agent is unclaimed and thus governed by the DefaultController
        self._agents[agent_id] = AgentRecord(
            agent=agent,
            descriptor=agent.descriptor,
            active_controller=self._default_controller.controller_id,
            registered_at=datetime.now()
        )

        # Initialize claim list with the DefaultController's claim at priority 0
        self._claims[agent_id] = {
            self._default_controller.controller_id: ControlClaim(
                controller_id=self._default_controller.controller_id,
                agent_id=agent_id,
                priority=self._default_controller.priority
            )
        }

    def detach_agent(self, agent_id: str) -> None:
        """Detach an agent from the Supervisor registry."""
        if agent_id not in self._agents:
            raise AgentNotFoundError(f"Agent with ID '{agent_id}' not found.")
        del self._agents[agent_id]
        if agent_id in self._claims:
            del self._claims[agent_id]

    def get_agent(self, agent_id: str) -> AbstractURPAgent:
        """Get the active agent instance by its ID."""
        if agent_id not in self._agents:
            raise AgentNotFoundError(f"Agent with ID '{agent_id}' not found.")
        return self._agents[agent_id].agent

    def register_controller(self, controller: AbstractController) -> None:
        """Register a controller plugin with the Supervisor."""
        if controller is None:
            return
        controller_id = controller.controller_id
        if controller_id in self._controllers:
            raise ControllerAlreadyExistsError(f"Controller with ID '{controller_id}' is already registered.")
        
        self._controllers[controller_id] = controller

    def unregister_controller(self, controller_id: str) -> None:
        """Unregister a controller plugin from the Supervisor."""
        if controller_id not in self._controllers:
            raise ControllerNotFoundError(f"Controller with ID '{controller_id}' not found.")
        
        if controller_id == self._default_controller.controller_id:
            raise ControlClaimError("Cannot unregister the default controller.")

        # Check if the controller currently governs any agent
        for agent_id, record in self._agents.items():
            if record.active_controller == controller_id:
                raise ControlClaimError(
                    f"Cannot unregister controller '{controller_id}' because it is currently governing agent '{agent_id}'."
                )

        # Remove the controller from registry
        del self._controllers[controller_id]

        # Clean up any inactive claims
        for agent_id in list(self._claims.keys()):
            if controller_id in self._claims[agent_id]:
                del self._claims[agent_id][controller_id]

    def get_controller(self, controller_id: str) -> AbstractController:
        """Get a registered controller by its ID."""
        if controller_id not in self._controllers:
            raise ControllerNotFoundError(f"Controller with ID '{controller_id}' not found.")
        return self._controllers[controller_id]

    async def claim(self, controller_id: str, agent_id: str) -> bool:
        """Request authority over a specific agent for a controller.
        
        Returns True if authority was acquired, False otherwise.
        """
        if agent_id not in self._agents:
            raise AgentNotFoundError(f"Agent with ID '{agent_id}' not found.")
        if controller_id not in self._controllers:
            raise ControllerNotFoundError(f"Controller with ID '{controller_id}' not found.")

        controller = self._controllers[controller_id]
        record = self._agents[agent_id]
        old_active_id = record.active_controller

        # Upsert the claim for this controller
        claim = ControlClaim(
            controller_id=controller_id,
            agent_id=agent_id,
            priority=controller.priority
        )
        self._claims[agent_id][controller_id] = claim

        # Arbitration rule: Highest Priority Claim Wins.
        # Deterministic tie-breaker: alphabetical order of controller_id
        winning_claim = max(
            self._claims[agent_id].values(),
            key=lambda c: (c.priority, c.controller_id)
        )

        if winning_claim.controller_id == controller_id:
            if old_active_id != controller_id:
                # Trigger callback on the old controller
                if old_active_id:
                    old_controller = self._controllers.get(old_active_id)
                    if old_controller:
                        await old_controller.on_released(agent_id)
                
                record.active_controller = controller_id
                await controller.on_acquired(agent_id)
            return True
        else:
            return False

    async def release(self, controller_id: str, agent_id: str) -> None:
        """Release authority over a specific agent for a controller."""
        if agent_id not in self._agents:
            raise AgentNotFoundError(f"Agent with ID '{agent_id}' not found.")
        if controller_id not in self._controllers:
            raise ControllerNotFoundError(f"Controller with ID '{controller_id}' not found.")

        if agent_id not in self._claims or controller_id not in self._claims[agent_id]:
            raise ControlClaimError(f"No active claim found for controller '{controller_id}' on agent '{agent_id}'.")

        if controller_id == self._default_controller.controller_id:
            raise ControlClaimError("Cannot release the default controller's fallback claim.")

        record = self._agents[agent_id]
        old_active_id = record.active_controller

        # Remove the claim
        del self._claims[agent_id][controller_id]

        # Determine the new winning claim
        winning_claim = max(
            self._claims[agent_id].values(),
            key=lambda c: (c.priority, c.controller_id)
        )
        new_active_id = winning_claim.controller_id

        if old_active_id == controller_id:
            old_controller = self._controllers.get(old_active_id)
            if old_controller:
                await old_controller.on_released(agent_id)

            record.active_controller = new_active_id
            new_controller = self._controllers.get(new_active_id)
            if new_controller:
                await new_controller.on_acquired(agent_id)

    def get_agent_state(self, agent_id: str) -> dict:
        """Get the read-only state of a specific agent."""
        if agent_id not in self._agents:
            raise AgentNotFoundError(f"Agent with ID '{agent_id}' not found.")
        return self._agents[agent_id].agent.state

    def get_active_controller(self, agent_id: str) -> str:
        """Get the ID of the active controller governing the agent."""
        if agent_id not in self._agents:
            raise AgentNotFoundError(f"Agent with ID '{agent_id}' not found.")
        return self._agents[agent_id].active_controller

    def acknowledge_outcome(self, agent_id: str) -> None:
        """Allows external systems or the supervisor to acknowledge that they've processed the last task outcome."""
        if agent_id not in self._agents:
            raise AgentNotFoundError(f"Agent with ID '{agent_id}' not found.")
        self._agents[agent_id].agent.acknowledge_outcome()

    async def send(self, agent_id: str, message: Any) -> None:
        """Route a message to an agent on behalf of its active controller."""
        pass

    def get_system_state(self) -> dict:
        """Get the system-wide operational state telemetry."""
        return {}
