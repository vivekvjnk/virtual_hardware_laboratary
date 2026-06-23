import asyncio
import logging
from typing import Any, Dict, Callable, Optional
from vhl_common.urp.data_types import LastTaskOutcome, MessageEnvelope, ProcessResult, FailureCategory
from vhl_protocol.models import AgentStatus
from archy_agent.utils import prepare_archy_workspace
from ..exceptions import AgentNotFoundError, InfrastructureError
from .abstract_controller import AbstractController

logger = logging.getLogger(__name__)

OUTCOME_WAIT_TIMEOUT = 600
MAX_VALIDATION_FAILURES = 5
MAX_AGENT_FAILURES = 10

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
                self._on_status_update(archy_agent_id, status)

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
                if process_result.outcome is LastTaskOutcome.TASK_COMPLETED: # Success case
                    if process_result.category is FailureCategory.NONE:
                        found_completion = True
                        # Move the scud file to module root
                        self._workspace_manager.move_scud_to_stable(module_name)
                        # Commit changes 
                        self._workspace_manager.commit_workspace(op_name="SCUD_GENERATION", author=f"{module_name}.archy",payload={"desc.":"Finished SCUD generation successfully"},commit_msg=f"Generate .scud for {module_name}",status="SUCCESS",cwd=self._workspace_manager.worktree.get(module_name),module_name=module_name)
                        break
                    elif process_result.category is FailureCategory.AGENTIC_FAILURE:
                        logger.warning(f"[{self.controller_id}.handle_archy] Archy returned {process_result}. Waiting for HIL resolution...")
                        await asyncio.sleep(self.poll_interval)
                        continue
                    else:
                        raise ValueError(f"Last task is in un-attainable state.. Something is seriously wrong dude... Last_task_result: {process_result}")

                    
                elif process_result.outcome in [LastTaskOutcome.TASK_FAILED,LastTaskOutcome.WAITING_FOR_USER_INPUT]:
                    logger.warning(
                        f"[{self.controller_id}.handle_archy] Archy returned {process_result}. Waiting for HIL resolution..."
                    )
                    await asyncio.sleep(self.poll_interval)
                    continue
                else:
                    raise ValueError(f"Last task outcome is in un-attainable state.. Something is seriously wrong dude... Last_task_outcome: {process_result.outcome}")

            if not found_completion:
                raise TimeoutError("Archy did not reach SUCCESS within timeout")

            # Update final status
            final_status = self._supervisor.get_agent_state(archy_agent_id).get("status")
            if self._on_status_update:
                self._on_status_update(archy_agent_id, final_status)

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
                self._on_status_update(librarian_agent_id, status)

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
                    if process_result.category is FailureCategory.NONE:
                        # Commit changes 
                        self._workspace_manager.commit_workspace(op_name="LIBRARY_RESOLUTION", author=f"{module_name}.librarian",payload={"desc.":"Finished library resolution"},commit_msg=f"Imported libraries for {module_name} and updated scud file",status="SUCCESS",cwd=self._workspace_manager.worktree.get(module_name),module_name=module_name)
                        
                        found_completion = True
                        break
                    elif process_result.category is FailureCategory.AGENTIC_FAILURE:
                        logger.warning(f"[{self.controller_id}.handle_libraian] Librarian returned {process_result}. Waiting for HIL resolution...")
                        await asyncio.sleep(self.poll_interval)
                        continue
                    else:
                        raise ValueError(f"Last task is in un-attainable state.. Something is seriously wrong dude... Last_task_result: {process_result}")

                elif process_result.outcome in [LastTaskOutcome.TASK_FAILED,LastTaskOutcome.WAITING_FOR_USER_INPUT]:
                    logger.warning(
                        f"[{self.controller_id}.handle_librarian] Librarian returned {process_result}. Waiting for HIL resolution..."
                    )
                    await asyncio.sleep(self.poll_interval)
                    continue
                else:
                    raise ValueError(f"Last task outcome is in un-attainable state.. Something is seriously wrong dude... Last_task_outcome: {process_result.outcome}")

            if not found_completion:
                raise TimeoutError("Librarian did not reach SUCCESS within timeout")

            # Update final status
            final_status = self._supervisor.get_agent_state(librarian_agent_id).get("status")
            if self._on_status_update:
                self._on_status_update(librarian_agent_id, final_status)

        finally:
            # Release Agent
            await self._supervisor.release(self.controller_id, librarian_agent_id)

    async def handle_ana(self, module_name: str, timeout: float = 1200) -> None:
        """Sequential member of Workflow 1: ANA-D."""
        logger.info(f"[{self.controller_id}.handle_ana] Starting ANA-D processing for module: {module_name}")
        ana_agent_id = f"{module_name}.ana"
        
        # Internal counters
        validation_failure_count = 0
        agent_failure_count = 0

        # 1. Claim Agent
        try:
            acquired = await self._supervisor.claim(self.controller_id, ana_agent_id)
        except AgentNotFoundError:
            raise RuntimeError(f"ANA agent '{ana_agent_id}' was not initialized at startup.")
        if not acquired:
            raise RuntimeError(f"Workflow1Controller failed to claim agent {ana_agent_id}")

        try:
            # 2. Send Initial Synthesis Request
            message = MessageEnvelope(
                type="SYNTHESIZE_CIRCUIT",
                payload={"text": "Please synthesize the circuit based on the SCUD and imported components."},
                sender="orchestrator",
                receiver=ana_agent_id
            )
            await self._supervisor.send(ana_agent_id, message)

            # Update initial status
            status = self._supervisor.get_agent_state(ana_agent_id).get("status")
            if self._on_status_update:
                self._on_status_update(ana_agent_id, status)

            # 3. Wait for outcomes and handle them
            start_time = asyncio.get_event_loop().time()
            found_completion = False
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                process_result = await self.wait_for_outcome(
                    ana_agent_id, 
                    timeout=timeout - (asyncio.get_event_loop().time() - start_time)
                )
                
                outcome = process_result.outcome
                category = process_result.category
                
                logger.info(f"[{self.controller_id}.handle_ana] Received outcome: {outcome}, category: {category}")

                # Case 1 — Success
                if outcome == LastTaskOutcome.TASK_COMPLETED and category == FailureCategory.NONE:
                    logger.info(f"[{self.controller_id}.handle_ana] ANA-D successfully completed synthesis.")
                    # Move circuit code to stable location and commit changes
                    self._workspace_manager.move_circuit_to_stable(module_name)
                    # Commit changes
                    self._workspace_manager.commit_workspace(
                        op_name="ANA_CIRCUIT_SYNTHESIS",
                        author=f"{module_name}.ana",
                        payload={"desc.":"Finished circuit synthesis successfully", "outcome": str(outcome), "category": str(category)},
                        commit_msg=f"Completed circuit synthesis for {module_name}",
                        status="SUCCESS",
                        cwd=self._workspace_manager.worktree.get(module_name),
                        module_name=module_name
                    )
                    found_completion = True
                    break

                # Case 5 — Infrastructure Failure
                elif category == FailureCategory.INFRASTRUCTURE_FAILURE:
                    logger.error(f"[{self.controller_id}.handle_ana] Infrastructure failure detected: {process_result}")
                    raise InfrastructureError(f"Infrastructure failure during ANA-D execution: {process_result}")

                # Case 6 — HIL Required
                elif outcome == LastTaskOutcome.WAITING_FOR_USER_INPUT:
                    logger.warning(f"[{self.controller_id}.handle_ana] ANA-D waiting for user input. Entering wait mode.")
                    continue

                # Case 2 — Validation Failure
                elif outcome == LastTaskOutcome.TASK_COMPLETED and category == FailureCategory.VALIDATION_FAILURE:
                    validation_failure_count += 1
                    if validation_failure_count > MAX_VALIDATION_FAILURES:
                        logger.warning(f"[{self.controller_id}.handle_ana] Max validation failures reached ({MAX_VALIDATION_FAILURES}). Escalating to HIL.")
                        continue
                    
                    logger.info(f"[{self.controller_id}.handle_ana] Validation failure #{validation_failure_count}. Retrying ANA.")
                    retry_message = MessageEnvelope(
                        type="RETRY_SYNTHESIS",
                        payload={"text": "Please analyze latest validation results and correct the circuit."},
                        sender="orchestrator",
                        receiver=ana_agent_id
                    )
                    await self._supervisor.send(ana_agent_id, retry_message)

                # Case 3 — Agent Failed To Produce Artifact (Missing Artifact)
                elif outcome == LastTaskOutcome.TASK_COMPLETED and category == FailureCategory.AGENTIC_FAILURE:
                    agent_failure_count += 1
                    if agent_failure_count > MAX_AGENT_FAILURES:
                        logger.warning(f"[{self.controller_id}.handle_ana] Max agent failures reached ({MAX_AGENT_FAILURES}). Escalating to HIL.")
                        continue
                    
                    logger.info(f"[{self.controller_id}.handle_ana] Agentic failure (missing artifact) #{agent_failure_count}. Retrying ANA.")
                    retry_message = MessageEnvelope(
                        type="RETRY_SYNTHESIS",
                        payload={"text": "Previous task completed without producing the required circuit artifact.\n\nPlease generate the missing .tsx file."},
                        sender="orchestrator",
                        receiver=ana_agent_id
                    )
                    await self._supervisor.send(ana_agent_id, retry_message)

                # Case 4 — Agent Stuck Mid-Execution
                elif outcome == LastTaskOutcome.TASK_FAILED and category == FailureCategory.AGENTIC_FAILURE:
                    agent_failure_count += 1
                    if agent_failure_count > MAX_AGENT_FAILURES:
                        logger.warning(f"[{self.controller_id}.handle_ana] Max agent failures reached ({MAX_AGENT_FAILURES}). Escalating to HIL.")
                        continue
                    
                    logger.info(f"[{self.controller_id}.handle_ana] Agentic failure (stuck) #{agent_failure_count}. Sending 'Continue'.")
                    continue_message = MessageEnvelope(
                        type="CONTINUE",
                        payload={"text": "Continue"},
                        sender="orchestrator",
                        receiver=ana_agent_id
                    )
                    await self._supervisor.send(ana_agent_id, continue_message)
                
                else:
                    logger.warning(f"[{self.controller_id}.handle_ana] Received unhandled outcome/category: {outcome}/{category}. Waiting for HIL.")
                    continue
            if not found_completion:
                raise TimeoutError("ANA-D did not reach terminal SUCCESS state within timeout")

        finally:
            # Update final status
            try:
                final_status = self._supervisor.get_agent_state(ana_agent_id).get("status")
                if self._on_status_update:
                    self._on_status_update(ana_agent_id, final_status)
            except Exception:
                pass
            # Release Agent
            await self._supervisor.release(self.controller_id, ana_agent_id)
