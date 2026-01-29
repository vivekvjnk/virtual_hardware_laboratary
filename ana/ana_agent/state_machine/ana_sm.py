import logging
import time
import os
import json
import sys
from typing import Optional, Dict, Any, List
from pathlib import Path

from ana_agent.observer import ObserverAgent, ObserverMode
from ana_agent.ana_worker_1 import run_ana_w1_agent
from ana_agent.ana_worker_2.agent import ANA_validation_agent

from .states import State
from .mcp_manager import MCPManager
from .iteration_manager import IterationManager

logger = logging.getLogger(__name__)

class ANADStateMachine:
    def __init__(self, max_auto_fixes: int = 3):
        self.state = State.INIT
        self.max_auto_fixes = max_auto_fixes
        self.auto_fix_count = 0
        
        # Inputs/Observations (Keep for now to avoid logic changes, but framework supports message passing)
        self.vap_decision: Optional[str] = "UNDECIDED"
        self.error_class: Optional[str] = None
        self.intent_status: Optional[str] = None
        self.observation = None

        # Project Info
        self.circuit_name: str = "bq79616_eval_board"
        self.workspace = Path(os.getcwd()) / "ana_workspace" / f"{self.circuit_name}_project"

        # Managers
        self.iteration_manager = IterationManager(self.workspace, self.circuit_name)
        self.mcp_manager = MCPManager(endpoint="http://localhost:8001")

        # Initial Message
        self.current_message: Dict[str, Any] = {
            "state_id": State.INIT,
            "from_state_id": None
        }

        # State Transition Table
        self.transition_table = {
            State.INIT: State.OBSERVE,
            State.OBSERVE: State.AUTHORIZE,
            State.PREPARE_FIX: State.TRIGGER_W1,
            State.TRIGGER_W1: State.TRIGGER_W2,
            State.WAIT_W1: State.TRIGGER_W2,
            State.TRIGGER_W2: State.INIT,
            State.WAIT_VAP: State.INIT,
            State.PREPARE_HIL: State.HIL_WAIT,
            # HIL_WAIT defaults to itself if no proposal (waiting for input)
            State.HIL_WAIT: State.HIL_WAIT
        }

        # MCP Setup
        self.mcp_manager.ensure_server_running()

    def step(self, event: Optional[str] = None, data: Optional[Dict[str, Any]] = None):
        """Executes one step of the state machine using message passing framework."""
        logger.info(f"Stepping from state: {self.state}")
        
        # Inject external inputs into current message
        if event:
            self.current_message["event"] = event
        if data:
            self.current_message["data"] = data

        handlers = {
            State.INIT: self._handle_init,
            State.OBSERVE: self._handle_observe,
            State.AUTHORIZE: self._handle_authorize,
            State.PREPARE_FIX: self._handle_prepare_fix,
            State.TRIGGER_W1: self._handle_trigger_w1,
            State.WAIT_W1: self._handle_wait_w1,
            State.TRIGGER_W2: self._handle_trigger_w2,
            State.WAIT_VAP: self._handle_wait_vap,
            State.PREPARE_HIL: self._handle_prepare_hil,
            State.HIL_WAIT: self._handle_hil_wait,
        }

        handler = handlers.get(self.state)
        if not handler:
            logger.error(f"No handler for state: {self.state}")
            return

        # Execute handler and get result message describing the CURRENT node's execution
        # Handlers must return their own state_id as per user instruction
        result_message = handler(self.current_message)
        
        # Explicit logic to decide the transition
        next_state = self._get_next_state(self.state, result_message)
        
        # Prepare the message for the next state
        next_message = result_message.copy()
        next_message["from_state_id"] = self.state
        next_message["state_id"] = next_state
        
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

    def _handle_init(self, message: Dict[str, Any]) -> Dict[str, Any]:
        iteration_id = hex(int(time.time()))[2:]
        self.iteration_manager.start_new_iteration(iteration_id)
        
        # Return current state and data; transition logic is now in step()
        return {
            "state_id": State.INIT,
            "iteration_id": iteration_id
        }

    def _handle_observe(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[ANA-D SM] State: OBSERVE. Triggered from: {message.get('from_state_id')}")
        
        if len(self.iteration_manager.iteration_ids) < 2:
            logger.info("[ANA-D SM] First iteration. Skipping observation.")
            return {"state_id": State.OBSERVE}

        previous_dir = self.iteration_manager.get_previous_iteration_dir()
        logger.info(f"[ANA-D SM] Observing previous iteration: {previous_dir}")
        
        observer = ObserverAgent()
        try:
            result = observer.observe(
                mode=ObserverMode("validation_error"),
                iteration_dir=previous_dir,
            )
            logger.info(f"Observation Result: {json.dumps(result, indent=2)}")
        except Exception as e:
            logger.exception(f"Error during observation: {e}")
            sys.exit(1)
        finally:
            observer.close()

        logger.info("[ANA-D SM] Awaiting commit from Observer Agent via MCP...")
        observation = self.mcp_manager.poll_for_observation()

        result_msg = {"state_id": State.OBSERVE}
        if observation:
            payload = observation["message"]["payload"]
            issue_kind = payload.get("issue_kind", "UNKNOWN")
            
            mapping = {
                "LOCAL": "violated",
                "NON_LOCAL": "ambiguous",
                "INTENT_MISMATCH": "ambiguous",
                "NONE": "satisfied"
            }
            self.intent_status = mapping.get(issue_kind, "ambiguous")
            self.observation = observation
            
            # Enrich message
            result_msg.update({
                "intent_status": self.intent_status,
                "observation": observation
            })
            logger.info(f"[ANA-D SM] Observation: intent_status={self.intent_status}")
        
        return result_msg

    def _handle_authorize(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[ANA-D SM] State: AUTHORIZE. VAP={self.vap_decision}, Error={self.error_class}, Intent={self.intent_status}")
        logger.info(f"[ANA-D SM] Triggered by: {message.get('from_state_id')}")

        # Propose next state based on logic
        proposed_next = State.PREPARE_HIL 

        if self.vap_decision == "REJECT":
            if self.error_class == "mechanical" and self.auto_fix_count < self.max_auto_fixes:
                proposed_next = State.PREPARE_FIX
            else:
                proposed_next = State.PREPARE_HIL
            
            # NOTE : Temporary re-routing for testing purpose (Matches original code)
            proposed_next = State.PREPARE_FIX

        elif self.vap_decision == "ACCEPT":
            if self.intent_status == "satisfied":
                proposed_next = State.EXIT_SUCCESS
            else:
                proposed_next = State.PREPARE_HIL

        elif self.vap_decision == "UNDECIDED":
            proposed_next = State.TRIGGER_W1
        
        return {
            "state_id": State.AUTHORIZE,
            "proposed_next_state": proposed_next
        }

    def _handle_prepare_fix(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("[ANA-D SM] State: PREPARE_FIX. Constructing fix instruction...")
        return {"state_id": State.PREPARE_FIX}

    def _handle_trigger_w1(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[ANA-D SM] State: TRIGGER_W1. Invoking ANA-W1...")
        self.auto_fix_count += 1
        
        try:
            scud_path = self.iteration_manager.get_scud_path()
            schematic_images_path = os.path.join(self.iteration_manager.current_iteration_dir, "schematic_images")
            
            run_ana_w1_agent(
                schematic_images_path=schematic_images_path, 
                scud_path=scud_path, 
                circuit_name=self.circuit_name
            )

            if not os.path.exists(self.iteration_manager.get_circuit_tsx_path()):
                logger.error(f"[ANA-D SM] ANA-W1 did not produce circuit file")
                return {
                    "state_id": State.TRIGGER_W1,
                    "proposed_next_state": State.PREPARE_HIL
                }

            return {"state_id": State.TRIGGER_W1}
        except Exception as e:
            logger.error(f"Error in TRIGGER_W1: {e}")
            return {
                "state_id": State.TRIGGER_W1,
                "proposed_next_state": State.PREPARE_HIL
            }

    def _handle_wait_w1(self, message: Dict[str, Any]) -> Dict[str, Any]:
        return {"state_id": State.WAIT_W1}

    def _handle_trigger_w2(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[ANA-D SM] State: TRIGGER_W2. Invoking VHL-VAP...")
        agent = ANA_validation_agent()
        try:
            result = agent.validate_circuit(
                self.circuit_name, 
                workspace=self.iteration_manager.current_iteration_dir
            )
            self.vap_decision = result.get("decision")
            logger.info(f"[ANA-D SM] VAP decision: {self.vap_decision}")
            return {"state_id": State.TRIGGER_W2}
        except Exception as e:
            logger.exception(f"Error during validation: {e}")
            raise e
        finally:
            agent.close()

    def _handle_wait_vap(self, message: Dict[str, Any]) -> Dict[str, Any]:
        return {"state_id": State.WAIT_VAP}

    def _handle_prepare_hil(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("[ANA-D SM] State: PREPARE_HIL. Escalating to human...")
        return {"state_id": State.PREPARE_HIL}

    def _handle_hil_wait(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("[ANA-D SM] State: HIL_WAIT. Awaiting human authority...")
        
        event = message.get("event")
        data = message.get("data")
        
        if event == "human_response":
            logger.info("[ANA-D SM] Human responded. Transitioning to INIT.")
            return {
                "state_id": State.HIL_WAIT,
                "proposed_next_state": State.INIT
            }
        elif event == "abort":
            logger.info("[ANA-D SM] Process aborted by human. Transitioning to EXIT_ABORT.")
            return {
                "state_id": State.HIL_WAIT,
                "proposed_next_state": State.EXIT_ABORT
            }
        
        return {"state_id": State.HIL_WAIT}

    def is_terminal(self) -> bool:
        return self.state in [State.EXIT_SUCCESS, State.EXIT_ABORT]

    def cleanup(self):
        self.mcp_manager.cleanup()

if __name__ == "__main__":
    sm = ANADStateMachine()
    logger.info("--- Starting State Machine ---")
    while not sm.is_terminal() and sm.state != State.HIL_WAIT:
        sm.step()
    
    if sm.state == State.EXIT_SUCCESS:
        logger.info("Simulation Finished: SUCCESS")