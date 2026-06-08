import asyncio
import logging
from typing import Any, Dict, Callable, Optional
from vhl_common.urp.data_types import LastTaskOutcome, MessageEnvelope, ProcessResult
from vhl_protocol.models import AgentStatus
from archy_agent.main import prepare_archy_workspace
from ..exceptions import AgentNotFoundError
from .abstract_controller import AbstractController

logger = logging.getLogger(__name__)

OUTCOME_WAIT_TIMEOUT = 600

class Workflow1Controller(AbstractController):
    """Controller responsible for orchestrating Workflow 1 (Archy -> Librarian -> ANA-D)
    by claiming agents, sending work, waiting for outcomes, and advancing the workflow.
    """

    def __init__(
        self,
        supervisor,
        workspace_manager,
        on_status_update: Optional[Callable[[str, AgentStatus], None]] = None,
        controller_id: str = "workflow1_controller",
        priority: int = 100,
        poll_interval: float = 1.0
    ) -> None:
        self._supervisor = supervisor
        self._workspace_manager = workspace_manager
        self._on_status_update = on_status_update
        self._controller_id = controller_id
        self._priority = priority
        self.poll_interval = poll_interval
        
        # Track pending outcomes for routed agents
        self._outcome_queues: Dict[str, asyncio.Queue] = {}

    @property
    def controller_id(self) -> str:
        return self._controller_id

    @property
    def priority(self) -> int:
        return self._priority

    async def on_acquired(self, agent_id: str) -> None:
        logger.info(f"[{self.controller_id}] Acquired authority over agent: {agent_id}")
        if agent_id not in self._outcome_queues:
            self._outcome_queues[agent_id] = asyncio.Queue()

    async def on_released(self, agent_id: str) -> None:
        logger.info(f"[{self.controller_id}] Released authority over agent: {agent_id}")
        self._outcome_queues.pop(agent_id, None)

    async def handle_outcome(self, agent_id: str, last_process_result: ProcessResult) -> None:
        logger.info(f"[{self.controller_id}] Received outcome for agent '{agent_id}': {last_process_result}")
        if agent_id not in self._outcome_queues:
            self._outcome_queues[agent_id] = asyncio.Queue()
        await self._outcome_queues[agent_id].put(last_process_result)

    async def wait_for_outcome(self, agent_id: str, timeout: float = OUTCOME_WAIT_TIMEOUT) -> ProcessResult:
        """Asynchronously waits for an outcome from a specific agent."""
        if agent_id not in self._outcome_queues:
            self._outcome_queues[agent_id] = asyncio.Queue()
        
        queue = self._outcome_queues[agent_id]
        try:
            return await asyncio.wait_for(queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Outcome waiting timed out for agent {agent_id}")

    async def handle_archy(self, module_name: str, timeout: float = 600) -> None:
        """Sequential member of Workflow 1: Archy."""
        logger.info(f"[{self.controller_id}.handle_archy] Starting Archy processing for module: {module_name}")
        archy_agent_id = f"{module_name}.archy"

        # 1. Prepare workspace and assets for Archy
        success = await asyncio.to_thread(
            prepare_archy_workspace,
            workspace_manager=self._workspace_manager,
        )
        if not success:
            raise RuntimeError("Failed to prepare workspace for Archy. Check logs for details.")

        # 2. Claim Agent
        try:
            acquired = await self._supervisor.claim(self.controller_id, archy_agent_id)
        except AgentNotFoundError:
            raise RuntimeError(f"Archy agent '{archy_agent_id}' was not initialized at startup.")
        if not acquired:
            raise RuntimeError(f"Workflow1Controller failed to claim agent {archy_agent_id}")

        try:
            # 3. Send Work (via Supervisor)
            message = MessageEnvelope(
                type="BUILD_SCUD",
                payload={"text": "Please prepare the scud document."},
                sender="orchestrator",
                receiver=archy_agent_id
            )
            await self._supervisor.send(archy_agent_id, message)

            # Update initial status
            status = self._supervisor.get_agent_state(archy_agent_id).get("status")
            if self._on_status_update:
                self._on_status_update("archy", status)

            # 4. Wait For Outcome & Advance Workflow
            start_time = asyncio.get_event_loop().time()
            found_completion = False

            while (asyncio.get_event_loop().time() - start_time) < timeout:
                current_state = self._supervisor.get_agent_state(archy_agent_id)
                logger.info(f"[{self.controller_id}.handle_archy] Waiting for Archy to complete... Current status: {current_state.get('status')}")

                # Wait for outcome routed by supervisor
                process_result = await self.wait_for_outcome(archy_agent_id, timeout=timeout - (asyncio.get_event_loop().time() - start_time))

                # TODO : Elaborate decision logic needs to be implemented
                # 1. If outcome is TASK_COMPLETED:
                #       - Check status of the agent. If AgentStatus.WAITING ==> Agent successfully completed last task. Waiting for next task
                #       - If AgentStatus.PROCESSING ==> Last task was successful. Processing new user message. Since only one controller is allowed to own the agent, AgentStatus.PROCESSING with a previous task outcome TASK_COMPLETED means, user(HIL) has sent a new message to agent before Workflow1Controller acknowledge the previous outcome. 
                # 2. If outcome is TASK_FAILED:
                #       - If AgentStatus.WAITING ==> Waiting for HIL user to interact with agent to resolve the problem
                #       - If AgentStatus.PROCESSING ==> HIL user has sent some message 
                # Decision logic
                if process_result.outcome is LastTaskOutcome.TASK_COMPLETED:
                    found_completion = True
                    break
                elif process_result.outcome.value is LastTaskOutcome.TASK_FAILED:
                    logger.warning(
                        f"[{self.controller_id}.handle_archy] Archy returned {process_result}. Waiting for HIL resolution..."
                    )
                    await asyncio.sleep(self.poll_interval)
                    continue

            if not found_completion:
                raise TimeoutError("Archy did not reach SUCCESS within timeout")

            # Update final status
            final_status = self._supervisor.get_agent_state(archy_agent_id).get("status")
            if self._on_status_update:
                self._on_status_update("archy", final_status)

        finally:
            # Release Agent
            await self._supervisor.release(self.controller_id, archy_agent_id)

    async def handle_librarian(self, module_name: str, timeout: float = 900) -> None:
        """Sequential member of Workflow 1: Librarian."""
        logger.info(f"[{self.controller_id}.handle_librarian] Starting Librarian processing for module: {module_name}")
        librarian_agent_id = f"{module_name}.librarian"

        # 1. Claim Agent
        try:
            acquired = await self._supervisor.claim(self.controller_id, librarian_agent_id)
        except AgentNotFoundError:
            raise RuntimeError(f"Librarian agent '{librarian_agent_id}' was not initialized at startup.")
        if not acquired:
            raise RuntimeError(f"Workflow1Controller failed to claim agent {librarian_agent_id}")

        try:
            # 2. Send Work (via Supervisor)
            message = MessageEnvelope(
                type="RESOLVE_COMPONENTS",
                payload={"text": "Hello Librarian, project is set up! Please read the .scud document and import non trivial components."},
                sender="orchestrator",
                receiver=librarian_agent_id
            )
            # Use Supervisor to send
            await self._supervisor.send(librarian_agent_id, message)

            # Update initial status
            status = self._supervisor.get_agent_state(librarian_agent_id).get("status")
            if self._on_status_update:
                self._on_status_update("librarian", status)

            # 3. Wait For Outcome & Advance Workflow
            start_time = asyncio.get_event_loop().time()
            found_completion = False

            while (asyncio.get_event_loop().time() - start_time) < timeout:
                current_state = self._supervisor.get_agent_state(librarian_agent_id)
                logger.info(f"[{self.controller_id}.handle_librarian] Waiting for Librarian to complete... Current status: {current_state.get('status')}")

                # Wait for outcome routed by supervisor
                process_result = await self.wait_for_outcome(librarian_agent_id, timeout=timeout - (asyncio.get_event_loop().time() - start_time))


                # TODO : Elaborate decision logic needs to be implemented
                # 1. If outcome is TASK_COMPLETED:
                #       - Check status of the agent. If AgentStatus.WAITING ==> Agent successfully completed last task. Waiting for next task
                #       - If AgentStatus.PROCESSING ==> Last task was successful. Processing new user message. Since only one controller is allowed to own the agent, AgentStatus.PROCESSING with a previous task outcome TASK_COMPLETED means, user(HIL) has sent a new message to agent before Workflow1Controller acknowledge the previous outcome. 
                # 2. If outcome is TASK_FAILED:
                #       - If AgentStatus.WAITING ==> Waiting for HIL user to interact with agent to resolve the problem
                #       - If AgentStatus.PROCESSING ==> HIL user has sent some message 
                # Decision logic
                if process_result.outcome is LastTaskOutcome.TASK_COMPLETED:
                    found_completion = True
                    break
                elif process_result.outcome is LastTaskOutcome.TASK_FAILED:
                    logger.warning(
                        f"[{self.controller_id}.handle_librarian] Librarian returned {process_result}. Waiting for HIL resolution..."
                    )
                    await asyncio.sleep(self.poll_interval)
                    continue

            if not found_completion:
                raise TimeoutError("Librarian did not reach SUCCESS within timeout")

            # Update final status
            final_status = self._supervisor.get_agent_state(librarian_agent_id).get("status")
            if self._on_status_update:
                self._on_status_update("librarian", final_status)

        finally:
            # Release Agent
            await self._supervisor.release(self.controller_id, librarian_agent_id)
