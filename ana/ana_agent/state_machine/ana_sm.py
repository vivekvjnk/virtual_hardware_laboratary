import logging
import asyncio
import shutil
import time
import os
import json
import sys
from typing import Optional, Dict, Any, List
from pathlib import Path
import uuid

from ana_agent.observer import ObserverAgent, ObserverMode
from ana_agent.ana_worker_1 import run_ana_w1_agent
from ana_agent.ana_worker_2.agent import ANA_validation_agent

from ana_agent.state_machine.states import State
from ana_agent.state_machine.mcp_manager import MCPManager
from vhl_protocol.client.client import VHLWebSocketClient

logger = logging.getLogger(__name__)

class ANADStateMachine:
    def __init__(self,
                 workspace_manager,
                 circuit_name:str, 
                 max_auto_fixes: int = 3, 
                 observations: List[str] = None, 
                 ws_client: Optional[VHLWebSocketClient] = None,
                 parent_notify: Optional[callable] = None,
                 inbox_queue: Optional[asyncio.Queue] = None):
        '''
        circuit_name: Name of the circuit without any extensions
        '''

        self.state = State.INIT
        # Inputs/Observations - Now handled via current_message for transparency
        self.max_auto_fixes = max_auto_fixes
        self.ws_client = ws_client
        self.parent_notify = parent_notify
        self.inbox_queue = inbox_queue if inbox_queue is not None else asyncio.Queue()
        
        # Project Info
        self.circuit_name = circuit_name # NOTE : circuit_name should never contain extension
        self.workspace_manager = workspace_manager
        self.workspace_manager.set_circuit_name(self.circuit_name)

        # Managers
        self.mcp_manager = MCPManager(endpoint="http://localhost:8001")

        # Initial Message
        self.current_message: Dict[str, Any] = {
            "state_id": State.INIT,
            "from_state_id": None,
            "auto_fix_count": 0,
            "observations": observations if observations else []
        }

        # State Transition Table
        self.transition_table = {
            State.INIT: State.OBSERVE,
            State.OBSERVE: State.AUTHORIZE,
            State.PREPARE_FIX: State.TRIGGER_W1,
            State.TRIGGER_W1: State.TRIGGER_W2,
            State.TRIGGER_W2: State.INIT,
            State.PREPARE_HIL: State.HIL_WAIT,
            State.HIL_WAIT: State.HIL_WAIT
        }

        # MCP Setup
        self.mcp_manager.ensure_server_running()

    async def step(self, event: Optional[str] = None, data: Optional[Dict[str, Any]] = None):
        """Executes one step of the state machine using message passing framework."""
        logger.info(f"Stepping from state: {self.state}")
        
        # Inject external inputs into a copy of current message
        message = self.current_message.copy()
        if event:
            message["event"] = event
        if data:
            message["data"] = data

        handlers = {
            State.INIT: self._handle_init,
            State.OBSERVE: self._handle_observe,
            State.AUTHORIZE: self._handle_authorize,
            State.PREPARE_FIX: self._handle_prepare_fix,
            State.TRIGGER_W1: self._handle_trigger_w1,
            State.TRIGGER_W2: self._handle_trigger_w2,
            State.PREPARE_HIL: self._handle_prepare_hil,
            State.HIL_WAIT: self._handle_hil_wait,
        }

        handler = handlers.get(self.state)
        if not handler:
            logger.error(f"No handler for state: {self.state}")
            return

        # Execute handler and get result message describing the CURRENT node's execution
        # All handlers now receive and return the message for transparency
        result_message = await handler(message)
        
        # Explicit logic to decide the transition
        next_state = self._get_next_state(self.state, result_message)
        
        # Prepare the message for the next state
        next_message = result_message.copy()
        next_message["from_state_id"] = self.state
        next_message["state_id"] = next_state
        
        # Remove event and data once processed by the handler
        next_message.pop("event", None)
        next_message.pop("data", None)
        
        # Remove proposal once it has been processed
        next_message.pop("proposed_next_state", None)

        # Update global/internal state
        self.state = next_state
        self.current_message = next_message
        
        logger.info(f"New state: {self.state} (Triggered from: {next_message['from_state_id']})")

    def _get_next_state(self, current_state: State, message: Dict[str, Any]) -> State:
        """Determines the next state. Gives preference to proposed_next_state if present."""
        
        # 1. Check if the node proposed a specific next state
        if "proposed_next_state" in message:
            return message["proposed_next_state"]
        
        # 2. Default explicit transitions logic
        return self.transition_table.get(current_state, current_state)

    async def _handle_init(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[ANA-D SM] State: INIT. Triggered from: {message.get('from_state_id')}\n{"*"*30}\n{message}\n{"*"*30}")
        result_msg = message.copy()
        

        observations = message.get("observations",[])
        
        if self.workspace_manager.is_first_iteration() and (num_iterations := self.workspace_manager.get_session_iteration_count() > 0):
            logger.warning(f"[ANA-D SM INIT] Iteration_{self.workspace_manager.get_session_iteration_count()}: Resetting first iteration flag. Current session iteration count: {num_iterations}")
            self.workspace_manager.reset_first_iteration()

        # Check how many iterations are present in session
        if (self.workspace_manager.is_first_iteration()) and (len(observations)>0):
            last_iteration_id_suffix = str(uuid.uuid4()).split("-")[0][:8] # First 8 characters of UUID
            logger.info(f"[ANA-D SM INIT] First iteration with user-provided circuit code and observations. Preparing iteration directory with provided circuit code. Suffix: {last_iteration_id_suffix}")

            # get the circuit code path from Stable/ directory. Pass to prepare_iteration_with_files
            # NOTE: Assumption: Before reaching init, workspace sync is carried out between VHL Runtime and Agent backend. Hence Stable/ directory contents are in sync with VHL runtime.
            circuit_code_path = self.workspace_manager.get_circuit_path_from_stable()
            self.workspace_manager.prepare_iteration_with_files(source_file=str(circuit_code_path), iteration_id_suffix=last_iteration_id_suffix)
            
        else: # Debug observability
            logger.info(f"[ANA-D SM INIT] Starting new iteration without user-provided circuit code. Observations: {observations}, First Iteration: {self.workspace_manager.is_first_iteration()}")
        
        iteration_id_suffix = str(uuid.uuid4()).split("-")[0][:8]
        iteration_path = self.workspace_manager.create_new_iteration(iteration_id_suffix)
        
        # INIT handler is responsible for clearing the iteration-specific state
        result_msg.update({
            "state_id": State.INIT,
            "iteration_id": iteration_id_suffix,
            "iteration_dir": str(iteration_path)
        })
                
        return result_msg

    async def _handle_observe(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[ANA-D SM Observe] State: OBSERVE. Triggered from: {message.get('from_state_id')}\n{"*"*30}\n{message}\n{"*"*30}")
        result_msg = message.copy()
        result_msg["state_id"] = State.OBSERVE
        
        observations = result_msg.get("observations", [])
        
        if self.workspace_manager.is_first_iteration():
            logger.info("[ANA-D SM Observe] First iteration. Skipping observation of previous iteration.")
            
            # Check if result message contain intent_status or error_class. If not, observe is triggered from user message
            if (len(observations)>0) and ("intent_status" not in result_msg and "error_class" not in result_msg): # Triggered directly through user message
                result_msg.update({
                    "intent_status": "violated",
                    "observations": observations,
                    "error_class" : "LOCAL"
                })
                logger.info(f"[ANA-D SM Observe] First iteration through user message. Observations: {observations}")
            return result_msg
        
        if("ACCEPT"== result_msg.get("vap_decision")):
            logger.info(f"[ANA-D SM Observe] Previous iteration had vap_decision status: {result_msg.get("vap_decision")}.")
            # For now we don't implement intent level analysis on the circuit code. Instead let the user decide if intent is satisfied or not.
            result_msg.update({
                    "intent_status": "satisfied",
                    "observations": observations,
                })
            return result_msg


        previous_dir = self.workspace_manager.previous_iteration_path
        if previous_dir:
            previous_dir = str(previous_dir)
        logger.info(f"[ANA-D SM Observe] Observing previous iteration: {previous_dir}")
        
        observer = ObserverAgent()
        try:
            result = await asyncio.to_thread(
                observer.observe,
                mode=ObserverMode("validation_error"),
                iteration_dir=previous_dir,
            )
            logger.info(f"[ANA-D SM Observe] Observation Result: {json.dumps(result, indent=2)}")
        except Exception as e:
            logger.exception(f"Error during observation: {e}")
            sys.exit(1)
        finally:
            observer.close()
        
        logger.info("[ANA-D SM Observe] Awaiting commit from Observer Agent via MCP...")
        observation_mcp = await asyncio.to_thread(self.mcp_manager.poll_for_observation)

        if observation_mcp:
            payload = observation_mcp["message"]["payload"]
            issue_kind = payload.get("issue_kind", "UNKNOWN")
            notes = payload.get("observations", "")
            
            mapping = {
                "LOCAL": "violated",
                "NON_LOCAL": "ambiguous",
                "INTENT_MISMATCH": "ambiguous",
                "NONE": "satisfied"
            }
            intent_status = mapping.get(issue_kind, "ambiguous")
            error_class = issue_kind
            # Create simple string observation
            observation_str =  notes if notes else f"[{issue_kind}]"
            
            # Update observations list
            observations = result_msg.get("observations", [])
            observations.append(observation_str)
            
            # Enrich message
            result_msg.update({
                "intent_status": intent_status,
                "observations": observations,
                "error_class" : error_class
            })
            logger.info(f"[ANA-D SM Observe] Added observation: {observation_str}")
        else:
            # Clear status if no observation found
            result_msg.pop("intent_status", None)
        
        return result_msg

    async def _handle_authorize(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[ANA-D SM] State: AUTHORIZE. Triggered from: {message.get('from_state_id')}\n{"*"*30}\n{message}\n{"*"*30}")
        
        result_msg = message.copy()
        result_msg["state_id"] = State.AUTHORIZE
        
        vap_decision = result_msg.get("vap_decision", "UNDECIDED")
        error_class = result_msg.get("error_class")
        intent_status = result_msg.get("intent_status")
        auto_fix_count = result_msg.get("auto_fix_count", 0)

        logger.info(f"[ANA-D SM] State: AUTHORIZE. VAP={vap_decision}, Error={error_class}, Intent={intent_status}, Auto-fix Count={auto_fix_count}")
        logger.info(f"[ANA-D SM] Triggered by: {message.get('from_state_id')}")

        # Propose next state based on logic
        proposed_next = State.PREPARE_HIL 

        if vap_decision == "REJECT":
            if error_class == "LOCAL" and auto_fix_count < self.max_auto_fixes:
                proposed_next = State.PREPARE_FIX
            else:
                err_msg = "VAP detected non-local error" if error_class != "LOCAL" else "VAP failed repeated auto-fix attempts for local error"
                result_msg["hil_wait_packet"] = {"reason":"ANA_HIL_REQUIRED", "message": err_msg}
                proposed_next = State.PREPARE_HIL
            
        elif vap_decision == "ACCEPT":
            if intent_status == "satisfied":
                result_msg["iteration_dir"] = str(self.workspace_manager.previous_iteration_path)
                proposed_next = State.EXIT_SUCCESS
            else:
                result_msg["hil_wait_packet"] = {"reason":"ANA_HIL_REQUIRED", "message": "VAP accepted the circuit but intent is not fully satisfied. Human intervention required to decide if intent violation is acceptable or not."}
                proposed_next = State.PREPARE_HIL

        elif vap_decision == "UNDECIDED":
            proposed_next = State.TRIGGER_W1
        
        # Clear control state variables. They are consumed here in authorize
        result_msg.pop("vap_decision", None)
        result_msg.pop("intent_status", None)
        result_msg.pop("error_class", None)
        
        
        result_msg["proposed_next_state"] = proposed_next
        return result_msg

    async def _handle_prepare_fix(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[ANA-D SM] State: PREPARE_FIX. Triggered from: {message.get('from_state_id')}\n{"*"*30}\n{message}\n{"*"*30}")
        
        result_msg = message.copy()
        result_msg["state_id"] = State.PREPARE_FIX
        return result_msg

    async def _handle_trigger_w1(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[ANA-D SM] State: TRIGGER_W1. Triggered from: {message.get('from_state_id')}\n{"*"*30}\n{message}\n{"*"*30}")
        
        result_msg = message.copy()
        result_msg["state_id"] = State.TRIGGER_W1
        
        # Update auto_fix_count in message
        auto_fix_count = result_msg.get("auto_fix_count", 0) + 1
        result_msg["auto_fix_count"] = auto_fix_count
        
        try:
            scud_path = self.workspace_manager.get_scud_path()
            current_iter_dir = self.workspace_manager.current_iteration_path
            schematic_images_path = os.path.join(current_iter_dir, "schematic_images")
            observations = result_msg.get("observations", [])



            # NOTE: Instead of "previous state" based conditional branching, lets use observation list for decision making
            # If there are any observations in the observation list, this is definitely an error correction iteration
            # It is the responsibility of previous states to ensure existence of previous iteration directory and its contents.
            # There are perceivably two operating modes for ANA-W1. Error correction and Synthesis. 
            # If observations are present and previous iteration directory is not none, 
            # ANA-W1 is triggered in Error Correction mode. Otherwise Synthesis mode
            previous_iter_dir = self.workspace_manager.previous_iteration_path
            if len(observations)>0 and previous_iter_dir:
                logger.info("[ANA-D SM] ANA-W1 in error correction mode (triggered from PREPARE_FIX).")
                await asyncio.to_thread(
                    run_ana_w1_agent,
                    workspace=str(current_iter_dir),
                    schematic_images_path=schematic_images_path,
                    scud_path=str(scud_path),
                    circuit_name=self.circuit_name,
                    observations=observations,
                    previous_iteration_dir=str(previous_iter_dir),
                )
            else:
                logger.info("[ANA-D SM] ANA-W1 in synthesis mode (not triggered from PREPARE_FIX).")
                await asyncio.to_thread(
                    run_ana_w1_agent,
                    workspace=str(current_iter_dir),
                    schematic_images_path=schematic_images_path,
                    scud_path=str(scud_path),
                    circuit_name=self.circuit_name,
                    observations=observations
                )
            
            if not os.path.exists(self.workspace_manager.get_circuit_tsx_path()):
                logger.error(f"[ANA-D SM] ANA-W1 did not produce circuit file")
                result_msg["hil_wait_packet"] = {"reason":"ANA_ERROR", "message": "ANA-W1 did not produce circuit file"}
                result_msg["proposed_next_state"] = State.PREPARE_HIL
                return result_msg
            # Now clear the observation list. ana_w1 successfully consumed observations
            result_msg["observations"] = []
            return result_msg
        except Exception as e:
            logger.error(f"Error in TRIGGER_W1: {e}")
            result_msg["hil_wait_packet"] = {"reason":"ANA_ERROR", "message": f"Error in TRIGGER_W1: {e}"}
            result_msg["proposed_next_state"] = State.PREPARE_HIL
            return result_msg

    async def _handle_trigger_w2(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[ANA-D SM] State: TRIGGER_W2. Triggered from: {message.get('from_state_id')}\n{"*"*30}\n{message}\n{"*"*30}")
        result_msg = message.copy()
        result_msg["state_id"] = State.TRIGGER_W2
        
        agent = ANA_validation_agent(ws_client=self.ws_client)
        try:
            result = await agent.validate_circuit(
                self.circuit_name, 
                workspace=str(self.workspace_manager.current_iteration_path)
            )
            vap_decision = result.get("decision")
            result_msg["vap_decision"] = vap_decision
            result_msg["task_id"] = result.get("task_id")
            logger.info(f"[ANA-D SM] VAP decision: {vap_decision}")
            return result_msg
        except Exception as e:
            logger.exception(f"Error during validation: {e}")
            # Clear decision on failure
            result_msg.pop("vap_decision", None)
            raise e
        finally:
            agent.close()

    async def _handle_prepare_hil(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[ANA-D SM] State: PREPARE_HIL. Triggered from: {message.get('from_state_id')}\n{"*"*30}\n{message}\n{"*"*30}")
        result_msg = message.copy()
        result_msg["state_id"] = State.PREPARE_HIL
        hil_packet = result_msg.get("hil_wait_packet", None)
        if not hil_packet:
            logger.warning("[ANA-D SM] No HIL packet found in message. Using default packet.")
            hil_packet = {"reason":"HIL_REQUIRED", "message": "Unknown reason. Human intervention required."}

        if self.parent_notify:
            logger.info(f"[ANA-D SM] Notifying parent of HIL requirement. HIL packet content: {hil_packet}")
            
            await self.parent_notify(
                payload={
                    "from_state": message.get("from_state_id"),
                    **hil_packet
                }
            )
        result_msg["proposed_next_state"] = State.HIL_WAIT
        return result_msg

    async def _handle_hil_wait(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[ANA-D SM] State: HIL_WAIT. Triggered from: {message.get('from_state_id')}\n{"*"*30}\n{message}\n{"*"*30}")
        result_msg = message.copy()
        result_msg["state_id"] = State.HIL_WAIT
        
        logger.info("[ANA-D SM] Waiting for message in inbox queue...")
        # Wait for message from AOSM via inbox queue
        inbox_message = await self.inbox_queue.get()
        logger.info(f"[ANA-D SM] Received message from inbox queue: {inbox_message}")
        
        event = inbox_message.get("event")
        data = inbox_message.get("data")
        
        if event == "human_response":
            logger.info(f"[ANA-D SM] Human responded: {data}")
            # Add human response to observations
            observations = result_msg.get("observations", [])
            observations.append(f"[HIL] {data}")
            result_msg["observations"] = observations
            
            result_msg["proposed_next_state"] = State.AUTHORIZE
            return result_msg
        elif event == "abort":
            logger.info("[ANA-D SM] Process aborted by human. Transitioning to EXIT_ABORT.")
            result_msg["proposed_next_state"] = State.EXIT_ABORT
            return result_msg
        
        # If unknown message, stay in HIL_WAIT (but actually we just consumed one item)
        # Maybe we should put it back or handle it. For now, assume it's one of these.
        return result_msg

    def is_terminal(self) -> bool:
        return self.state in [State.EXIT_SUCCESS, State.EXIT_ABORT]

    def cleanup(self):
        self.mcp_manager.cleanup()

    async def run(self):
        """Runs the state machine loop until a terminal state is reached."""
        logger.info("--- Starting State Machine ---")
        try:
            while not self.is_terminal():
                await self.step()
        except Exception as e:
            task_id = self.current_message.get("task_id", None)
            logger.exception(f"Unexpected error in ANA-D SM run loop: {e}")    
            payload = {"reason":"ERROR","task_id":task_id, "decision":"ERROR", "message": str(e)}
            self.parent_notify(payload)
            return
        
        task_id = self.current_message.get("task_id", None)
        if self.state == State.EXIT_SUCCESS:
            logger.info("Simulation Finished: SUCCESS")
            payload = {"reason":"EXIT",
                       "task_id":task_id, 
                       "decision":"ACCEPT", 
                       "iteration_dir":self.current_message.get("iteration_dir"),
                       "from_state":self.current_message.get("from_state_id")}
            self.parent_notify(payload)
            
        elif self.state == State.EXIT_ABORT:
            logger.info("Simulation Finished: ABORTED")
            payload = {"reason":"EXIT","task_id":task_id, "decision":"REJECT", "from_state":self.current_message.get("from_state_id")}
            self.parent_notify(payload)
            
if __name__ == "__main__":
    sm = ANADStateMachine(max_auto_fixes=5)
    asyncio.run(sm.run())