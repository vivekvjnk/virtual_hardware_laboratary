import asyncio
import logging
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
from .data_types import SupervisorState
from vhl_common.gate.gate import GateRegistry
from vhl_common.urp.data_types import MessageEnvelope
from vhl_common.urp.data_types import LastTaskOutcome, ProcessResult

# Initialize logger for this module
logger = logging.getLogger(__name__)

class Supervisor:
    """The persistent control plane for all active URP agent instances."""

    def __init__(self, context_id: str = "aosm_gate") -> None:
        self._agents: Dict[str, AgentRecord] = {}
        self._controllers: Dict[str, AbstractController] = {}
        # Mapping from agent_id -> controller_id -> ControlClaim
        self._claims: Dict[str, Dict[str, ControlClaim]] = {}
        
        self.state = SupervisorState.NORMAL
        self.gate = GateRegistry.get(context_id)

        # Background supervision & outcome routing task state
        self._routing_agents = set()
        self._monitor_task = None
        self._monitor_interval = 0.1

        # Invariant 5: DefaultController governs every unclaimed agent.
        # This controller is automatically attached during Supervisor initialization.
        self._default_controller = DefaultController()
        self.register_controller(self._default_controller)
        
        from vhl_common.gate.hil import HILTerminal
        self.hil_terminal = HILTerminal(self.gate)
        logger.info("Supervisor initialized successfully in context '%s'.", context_id)

    def start(self, interval: float = 0.1) -> None:
        """Start the background outcome monitoring loop."""
        self._monitor_interval = interval
        import os
        if os.environ.get("VHL_DISABLE_HIL_TERMINAL") != "true":
            logger.info("[Supervisor] Starting HIL Terminal...")
            self.hil_terminal.start()
        else:
            logger.warning("HIL Terminal initialization skipped (VHL_DISABLE_HIL_TERMINAL is set).")
            
        if self._monitor_task is None or self._monitor_task.done():
            logger.info("[Supervisor] Starting background outcome monitoring loop (interval: %s s)...", interval)
            self._monitor_task = asyncio.create_task(self._run_monitoring_loop())

    async def stop(self) -> None:
        """Stop the background outcome monitoring loop and HIL terminal."""
        logger.info("[Supervisor] Stopping Supervisor operations...")
        await self.hil_terminal.stop()
        
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                logger.debug("[Supervisor] Background monitoring loop task cancelled successfully.")
        self._monitor_task = None
        logger.info("[Supervisor] Supervisor stopped.")

    async def _run_monitoring_loop(self) -> None:
        while True:
            try:
                await self.process_outcomes()
            except Exception as e:
                logger.exception("Unexpected exception encountered during the outcome monitoring loop execution: %s", e)
            await asyncio.sleep(self._monitor_interval)

    async def process_outcomes(self) -> None:
        """Inspect all registered agents and route any pending outcomes to their active controllers."""
        if self.state == SupervisorState.SHUTDOWN:
            logger.debug("[Supervisor] Skipping outcome processing: Supervisor is in SHUTDOWN state.")
            return

        for agent_id, record in list(self._agents.items()):
            if agent_id in self._routing_agents:
                continue

            try:
                state = record.agent.state
                last_process_result:ProcessResult = state.get("last_process_result")
                
                acknowledged = state.get("outcome_acknowledged")

                if last_process_result.outcome is not LastTaskOutcome.NONE and not acknowledged:
                    logger.debug("[Supervisor] Detected pending, unacknowledged outcome for agent '%s'. Scheduling routing...", agent_id)
                    self._routing_agents.add(agent_id)
                    asyncio.create_task(self._route_and_acknowledge(agent_id, record, last_process_result))
            except Exception as e:
                logger.error("Failed to inspect metrics for agent '%s' during outcome processing: %s", agent_id, e, exc_info=True)

    async def _route_and_acknowledge(self, agent_id: str, record: AgentRecord, last_process_result: Any) -> None:
        try:
            active_controller_id = record.active_controller
            controller = self._controllers.get(active_controller_id)
            
            if controller:
                logger.info("[Supervisor] Routing agent '%s' outcome to active controller '%s'.", agent_id, active_controller_id)
                await controller.handle_outcome(agent_id, last_process_result)
            else:
                logger.warning("Active controller '%s' for agent '%s' was not found in registry. Dropping outcome routing.", active_controller_id, agent_id)
                
            self.acknowledge_outcome(agent_id)
        except Exception as e:
            logger.error("Exception occurred while routing or acknowledging outcome for agent '%s': %s", agent_id, e, exc_info=True)
        finally:
            self._routing_agents.discard(agent_id)

    def attach_agent(self, agent: AbstractURPAgent) -> None:
        """Attach an active agent to the Supervisor registry."""
        if agent is None:
            logger.warning("Attempted to attach a None agent reference. Ignoring request.")
            return
            
        agent_id = agent.descriptor.agent_id
        if agent_id in self._agents:
            logger.error("Failed to attach agent: ID '%s' is already registered.", agent_id)
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
        # Register agent ingress via Gate
        self.gate.register(agent_id, lambda msg, aid=agent_id: asyncio.create_task(self.send(aid, msg)))
        
        # Enforce agent egress via Supervisor -> Gate
        agent.set_callback(lambda msg: asyncio.create_task(self.route_egress(msg)))
        logger.info("[Supervisor] Agent '%s' successfully attached and bound to default controller '%s'.", agent_id, self._default_controller.controller_id)

    def detach_agent(self, agent_id: str) -> None:
        """Detach an agent from the Supervisor registry."""
        if agent_id not in self._agents:
            logger.error("Failed to detach agent: ID '%s' not found.", agent_id)
            raise AgentNotFoundError(f"Agent with ID '{agent_id}' not found.")
        del self._agents[agent_id]
        if agent_id in self._claims:
            del self._claims[agent_id]
        self._routing_agents.discard(agent_id)

        self.gate.unregister(agent_id)
        logger.info("[Supervisor] Agent '%s' has been successfully detached and cleaned up from Supervisor.", agent_id)
    def get_agent(self, agent_id: str) -> AbstractURPAgent:
        """Get the active agent instance by its ID."""
        if agent_id not in self._agents:
            logger.error("Lookup failed: Agent '%s' not found.", agent_id)
            raise AgentNotFoundError(f"Agent with ID '{agent_id}' not found.")
        return self._agents[agent_id].agent

    def register_controller(self, controller: AbstractController) -> None:
        """Register a controller plugin with the Supervisor."""
        if controller is None:
            logger.warning("Attempted to register a None controller reference. Ignoring request.")
            return
        controller_id = controller.controller_id
        if controller_id in self._controllers:
            logger.error("Failed to register controller: ID '%s' already exists.", controller_id)
            raise ControllerAlreadyExistsError(f"Controller with ID '{controller_id}' is already registered.")
        
        self._controllers[controller_id] = controller
        logger.info("[Supervisor] Controller plugin '%s' (Priority: %s) registered successfully.", controller_id, controller.priority)

    def unregister_controller(self, controller_id: str) -> None:
        """Unregister a controller plugin from the Supervisor."""
        if controller_id not in self._controllers:
            logger.error("Failed to unregister: Controller '%s' not found.", controller_id)
            raise ControllerNotFoundError(f"Controller with ID '{controller_id}' not found.")
        
        if controller_id == self._default_controller.controller_id:
            logger.error("Unregister denied: The system fallback DefaultController cannot be unregistered.")
            raise ControlClaimError("Cannot unregister the default controller.")

        # Check if the controller currently governs any agent
        for agent_id, record in self._agents.items():
            if record.active_controller == controller_id:
                logger.error("Unregister denied: Controller '%s' actively governs agent '%s'.", controller_id, agent_id)
                raise ControlClaimError(
                    f"Cannot unregister controller '{controller_id}' because it is currently governing agent '{agent_id}'."
                )

        # Remove the controller from registry
        del self._controllers[controller_id]

        # Clean up any inactive claims
        for agent_id in list(self._claims.keys()):
            if controller_id in self._claims[agent_id]:
                del self._claims[agent_id][controller_id]      
        logger.info("[Supervisor] Controller plugin '%s' successfully unregistered.", controller_id)

    def get_controller(self, controller_id: str) -> AbstractController:
        """Get a registered controller by its ID."""
        if controller_id not in self._controllers:
            logger.error("Lookup failed: Controller '%s' not found.", controller_id)
            raise ControllerNotFoundError(f"Controller with ID '{controller_id}' not found.")
        return self._controllers[controller_id]

    async def claim(self, controller_id: str, agent_id: str) -> bool:
        """Request authority over a specific agent for a controller.
        
        Returns True if authority was acquired, False otherwise.
        """
        if self.state in (SupervisorState.MAINTENANCE, SupervisorState.SHUTDOWN):
            logger.error("Claim rejected: System state is '%s' (Claims blocked).", self.state.name)
            raise ControlClaimError(f"Cannot claim agents while supervisor is in {self.state.name} state.")

        if agent_id not in self._agents:
            logger.error("Claim rejected: Target agent '%s' not found.", agent_id)
            raise AgentNotFoundError(f"Agent with ID '{agent_id}' not found.")
        if controller_id not in self._controllers:
            logger.error("Claim rejected: Requesting controller '%s' not found.", controller_id)
            raise ControllerNotFoundError(f"Controller with ID '{controller_id}' not found.")

        logger.debug("[Supervisor] Processing control claim request by '%s' over agent '%s'...", controller_id, agent_id)
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
                        logger.debug("[Supervisor] Notifying controller '%s' that it has been unseated from agent '%s'.", old_active_id, agent_id)
                        await old_controller.on_released(agent_id)
                
                record.active_controller = controller_id
                logger.info("[Supervisor]: Controller '%s' has successfully ACQUIRED control over agent '%s' (Unseated: '%s').", controller_id, agent_id, old_active_id)
                await controller.on_acquired(agent_id)
            return True
        else:
            logger.info("[Supervisor]: Claim request by '%s' over agent '%s' DENIED. Controller '%s' retains higher precedence.", controller_id, agent_id, winning_claim.controller_id)
            return False

    async def release(self, controller_id: str, agent_id: str) -> None:
        """Release authority over a specific agent for a controller."""
        if agent_id not in self._agents:
            logger.error("Release failed: Agent '%s' not found.", agent_id)
            raise AgentNotFoundError(f"Agent with ID '{agent_id}' not found.")
        if controller_id not in self._controllers:
            logger.error("Release failed: Controller '%s' not found.", controller_id)
            raise ControllerNotFoundError(f"Controller with ID '{controller_id}' not found.")

        if agent_id not in self._claims or controller_id not in self._claims[agent_id]:
            logger.error("Release failed: No active claim found for controller '%s' on agent '%s'.", controller_id, agent_id)
            raise ControlClaimError(f"No active claim found for controller '{controller_id}' on agent '{agent_id}'.")

        if controller_id == self._default_controller.controller_id:
            logger.error("Release rejected: Fallback claim for '%s' cannot be released.", self._default_controller.controller_id)
            raise ControlClaimError("Cannot release the default controller's fallback claim.")

        logger.debug("[Supervisor] Processing control release request by '%s' over agent '%s'...", controller_id, agent_id)
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
            logger.info("[Supervisor]: Controller '%s' RELEASED control of agent '%s'. New active controller fallback: '%s'.", controller_id, agent_id, new_active_id)
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
            logger.error("Acknowledgment failed: Agent '%s' not found.", agent_id)
            raise AgentNotFoundError(f"Agent with ID '{agent_id}' not found.")
        logger.debug("[Supervisor] Acknowledging processing result outcome for agent '%s'.", agent_id)
        self._agents[agent_id].agent.acknowledge_outcome()

    async def send(self, agent_id: str, message: Any) -> None:
        """Route a message to an agent on behalf of its active controller."""
        if self.state == SupervisorState.SHUTDOWN:
            logger.error("Ingress message drop: Refusing routing to agent '%s' during SHUTDOWN state.", agent_id)
            raise ControlClaimError("Cannot send messages while supervisor is in SHUTDOWN state.")

        if agent_id not in self._agents:
            logger.error("Ingress message drop: Target agent '%s' not found.", agent_id)
            raise AgentNotFoundError(f"Agent with ID '{agent_id}' not found.")
            
        logger.debug("[Supervisor] Routing ingress message to agent '%s' through Supervisor.", agent_id)
        agent = self._agents[agent_id].agent
        await agent.send(message)

    def get_system_state(self) -> dict:
        """Get the system-wide operational state telemetry."""
        system_view = {}
        for agent_id, record in self._agents.items():
            state = record.agent.state
            status = state.get("status", "UNKNOWN")
            if hasattr(status, "name"):
                status = status.name
            system_view[agent_id] = {
                "status": status,
                "active_controller": record.active_controller
            }
        return {"agents": system_view, "supervisor_state": self.state.name}

    async def route_egress(self, message: MessageEnvelope) -> None:
        """Route a message originating from an agent to its destination via Gate."""
        if self.state == SupervisorState.SHUTDOWN:
            logger.error("Egress message drop: Refusing routing during SHUTDOWN state.")
            raise ControlClaimError("Cannot route egress messages while supervisor is in SHUTDOWN state.")
        logger.debug("[Supervisor] Routing egress message originating from agent via Gate Registry.")
        await self.gate.send(message)

    def register_hil_handler(self, handler) -> None:
        """Register the HIL communication handler."""
        logger.info("[Supervisor] Registering modern HIL handling logic with context Gate.")
        self.gate.register("HIL", handler)

    def has_agent(self, agent_id: str) -> bool:
        """Check if an agent is registered in the supervisor."""
        return agent_id in self._agents