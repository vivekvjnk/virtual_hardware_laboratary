import logging
import asyncio
import json
import uuid
from pathlib import Path
from typing import Optional, Dict, Any

from vhl_protocol.client.client import VHLWebSocketClient
from vhl_protocol.sync.client import SyncClient
from component_placement_agent.state_machine.states import CPAState
from component_placement_agent.agent.cpa_worker import run_cpa_agent

logger = logging.getLogger(__name__)

class CPASm:
    def __init__(self,
                 workspace_manager,
                 circuit_name: str,
                 web_socket_client: Optional[VHLWebSocketClient] = None,
                 sync_client: Optional[SyncClient] = None,
                 project_id: Optional[str] = None):
        logger.info(f"[CPASm.__init__] Initializing CPA State Machine for circuit: {circuit_name}")
        
        self.state = CPAState.INIT
        self.workspace_manager = workspace_manager
        self.circuit_name = circuit_name
        self.web_socket_client = web_socket_client
        self.sync_client = sync_client
        self.project_id = project_id
        
        self.current_message: Dict[str, Any] = {
            "state_id": CPAState.INIT,
            "last_decision": None,
            "task_id": None
        }

        # Transition Table
        self.transition_table = {
            CPAState.INIT: CPAState.EXECUTE,
            CPAState.EXECUTE: CPAState.VERIFY,
            CPAState.VERIFY: CPAState.FINALIZE,
            CPAState.FINALIZE: CPAState.EXIT_SUCCESS
        }

    async def step(self):
        """Executes one step of the CPA state machine."""
        logger.info(f"[CPASm.step] Current state: {self.state}")
        
        handlers = {
            CPAState.INIT: self._handle_init,
            CPAState.EXECUTE: self._handle_execute,
            CPAState.VERIFY: self._handle_verify,
            CPAState.FINALIZE: self._handle_finalize,
            CPAState.EXIT_SUCCESS: self._handle_exit_success,
            CPAState.EXIT_ERROR: self._handle_exit_error,
        }

        handler = handlers.get(self.state)
        if not handler:
            logger.error(f"[CPASm.step] No handler for state: {self.state}")
            return

        # Prepare message for handler
        message = self.current_message.copy()
        
        # Execute handler
        result_message = await handler(message)
        
        # Determine next state
        next_state = result_message.get("proposed_next_state", self.transition_table.get(self.state, self.state))
        
        # Update state
        self.state = next_state
        self.current_message = result_message
        self.current_message["state_id"] = self.state
        
        logger.info(f"[CPASm.step] Transitioned to: {self.state}")

    async def _handle_init(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("[CPASm._handle_init] Preparing iteration workspace...")
        
        iteration_id_suffix = str(uuid.uuid4()).split("-")[0][:8]
        
        # If it's first iteration, we can just create new. 
        # But usually ANA has run before, so we carry over the circuit code from Stable.
        is_stable_present = self.workspace_manager.get_circuit_path_from_stable().is_file()
        
        if is_stable_present:
            stable_circuit = self.workspace_manager.get_circuit_path_from_stable()
            iteration_path = self.workspace_manager.prepare_iteration_with_files(
                source_file=str(stable_circuit),
                iteration_id_suffix=iteration_id_suffix
            )
            logger.info(f"[CPASm._handle_init] Carried over stable circuit to {iteration_path}")
        else:
            iteration_path = self.workspace_manager.create_new_iteration(iteration_id_suffix)
            logger.info(f"[CPASm._handle_init] Created fresh iteration: {iteration_path}")

        result_msg = message.copy()
        result_msg.update({
            "iteration_dir": str(iteration_path),
            "iteration_id": self.workspace_manager.get_current_iteration_id()
        })
        return result_msg

    async def _handle_execute(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("[CPASm._handle_execute] Triggering CPA Agent...")
        iteration_dir = message.get("iteration_dir")
        
        try:
            # We assume synthesis mode if it's the first CPA run in this session, 
            # Or error correction if previous iterations in this project exist.
            # However, simpler is just checking if we have a previous_iteration_path from workspace_manager.
            prev_dir = self.workspace_manager.previous_iteration_path
            
            scud_path = self.workspace_manager.get_scud_path()
            
            # Run CPA Agent in a separate thread to avoid blocking loop
            await asyncio.to_thread(
                run_cpa_agent,
                workspace=iteration_dir,
                circuit_name=self.circuit_name,
                scud_path=str(scud_path),
                previous_iteration_dir=str(prev_dir) if prev_dir else None
            )
            
            return message.copy()
        except Exception as e:
            logger.exception(f"[CPASm._handle_execute] Error running CPA Agent: {e}")
            result_msg = message.copy()
            result_msg["proposed_next_state"] = CPAState.EXIT_ERROR
            result_msg["error"] = str(e)
            return result_msg

    async def _handle_verify(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("[CPASm._handle_verify] Verifying CPA results...")
        iteration_dir = message.get("iteration_dir")
        result_path = Path(iteration_dir) / "cpa_result.json"
        
        result_msg = message.copy()
        
        if not result_path.exists():
            logger.error(f"[CPASm._handle_verify] cpa_result.json not found in {iteration_dir}")
            result_msg["proposed_next_state"] = CPAState.EXIT_ERROR
            return result_msg
            
        try:
            with open(result_path, "r") as f:
                cpa_result = json.load(f)
            
            decision = cpa_result.get("decision", "REJECT")
            task_id = cpa_result.get("task_id")
            
            result_msg["last_decision"] = decision
            result_msg["task_id"] = task_id
            
            if decision == "ACCEPT" and task_id:
                logger.info(f"[CPASm._handle_verify] CPA Accepted with task_id: {task_id}. Reporting to runtime.")
                if self.web_socket_client:
                    await self.web_socket_client.emit_evaluation_update(task_id, "ACCEPT")
                return result_msg
            else:
                logger.warning(f"[CPASm._handle_verify] CPA Result was {decision}. Aborting sync.")
                result_msg["proposed_next_state"] = CPAState.EXIT_ERROR
                return result_msg
                
        except Exception as e:
            logger.exception(f"[CPASm._handle_verify] Failed to process cpa_result.json: {e}")
            result_msg["proposed_next_state"] = CPAState.EXIT_ERROR
            return result_msg

    async def _handle_finalize(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("[CPASm._handle_finalize] Synchronizing iteration contents to Stable directory...")
        iteration_dir = message.get("iteration_dir")
        
        try:
            # WorkspaceManager.populate_stable expects iteration_id
            # Our message has both
            iteration_id = message.get("iteration_id")
            self.workspace_manager.populate_stable(iteration_id)
            logger.info("[CPASm._handle_finalize] Stable directory updated.")
            return message.copy()
        except Exception as e:
            logger.exception(f"[CPASm._handle_finalize] Error in finalize: {e}")
            res = message.copy()
            res["proposed_next_state"] = CPAState.EXIT_ERROR
            return res

    async def _handle_exit_success(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("[CPASm._handle_exit_success] CPA Process completed successfully.")
        res = message.copy()
        res["proposed_next_state"] = CPAState.COMPLETED
        return res

    async def _handle_exit_error(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.error(f"[CPASm._handle_exit_error] CPA Process failed: {message.get('error')}")
        res = message.copy()
        res["proposed_next_state"] = CPAState.COMPLETED
        return res

    def is_terminal(self) -> bool:
        return self.state == CPAState.COMPLETED

    async def run(self):
        """Runs the state machine until completion."""
        while not self.is_terminal():
            await self.step()
        logger.info("[CPASm.run] CPA State Machine finished.")
