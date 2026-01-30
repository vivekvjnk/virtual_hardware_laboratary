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
        # Inputs/Observations - Now handled via current_message for transparency
        self.max_auto_fixes = max_auto_fixes
        
        # Project Info
        self.circuit_name: str = "bq79616_eval_board"
        self.workspace = Path(os.getcwd()) / "ana_workspace" / f"{self.circuit_name}_project"

        # Managers
        self.iteration_manager = IterationManager(self.workspace, self.circuit_name)
        self.mcp_manager = MCPManager(endpoint="http://localhost:8001")

        # Initial Message
        self.current_message: Dict[str, Any] = {
            "state_id": State.INIT,
            "from_state_id": None,
            "auto_fix_count": 0
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
        # All handlers now receive and return the message for transparency
        result_message = handler(message)
        
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

    def _handle_init(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[ANA-D SM] State: INIT. Triggered from: {message.get('from_state_id')}")
        result_msg = message.copy()
        
        iteration_id = hex(int(time.time()))[2:]
        self.iteration_manager.start_new_iteration(iteration_id)
        
        # INIT handler is responsible for clearing the iteration-specific state
        result_msg.update({
            "state_id": State.INIT,
            "iteration_id": iteration_id,
        })
        
        # Clear states from previous iteration
        result_msg.pop("vap_decision", None)
        result_msg.pop("intent_status", None)
        result_msg.pop("observation", None)
        result_msg.pop("error_class", None)
        
        return result_msg

    def _handle_observe(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[ANA-D SM] State: OBSERVE. Triggered from: {message.get('from_state_id')}")
        result_msg = message.copy()
        result_msg["state_id"] = State.OBSERVE
        
        if len(self.iteration_manager.iteration_ids) < 2:
            logger.info("[ANA-D SM] First iteration. Skipping observation.")
            return result_msg

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

        if observation:
            payload = observation["message"]["payload"]
            issue_kind = payload.get("issue_kind", "UNKNOWN")
            
            mapping = {
                "LOCAL": "violated",
                "NON_LOCAL": "ambiguous",
                "INTENT_MISMATCH": "ambiguous",
                "NONE": "satisfied"
            }
            intent_status = mapping.get(issue_kind, "ambiguous")
            
            # Enrich message - OBSERVE handler is responsible for setting/clearing its data
            result_msg.update({
                "intent_status": intent_status,
                "observation": observation
            })
            logger.info(f"[ANA-D SM] Observation: intent_status={intent_status}")
        else:
            # Clear if not found
            result_msg.pop("intent_status", None)
            result_msg.pop("observation", None)
        
        return result_msg

    def _handle_authorize(self, message: Dict[str, Any]) -> Dict[str, Any]:
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
            if error_class == "mechanical" and auto_fix_count < self.max_auto_fixes:
                proposed_next = State.PREPARE_FIX
            else:
                proposed_next = State.PREPARE_HIL
            
            # NOTE : Temporary re-routing for testing purpose (Matches original code)
            proposed_next = State.PREPARE_FIX

        elif vap_decision == "ACCEPT":
            if intent_status == "satisfied":
                proposed_next = State.EXIT_SUCCESS
            else:
                proposed_next = State.PREPARE_HIL

        elif vap_decision == "UNDECIDED":
            proposed_next = State.TRIGGER_W1
        
        result_msg["proposed_next_state"] = proposed_next
        return result_msg

    def _handle_prepare_fix(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("[ANA-D SM] State: PREPARE_FIX. Constructing fix instruction...")
        result_msg = message.copy()
        result_msg["state_id"] = State.PREPARE_FIX
        return result_msg

    def _handle_trigger_w1(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[ANA-D SM] State: TRIGGER_W1. Invoking ANA-W1...")
        result_msg = message.copy()
        result_msg["state_id"] = State.TRIGGER_W1
        
        # Update auto_fix_count in message
        auto_fix_count = result_msg.get("auto_fix_count", 0) + 1
        result_msg["auto_fix_count"] = auto_fix_count
        
        try:
            scud_path = self.iteration_manager.get_scud_path()
            schematic_images_path = os.path.join(self.iteration_manager.current_iteration_dir, "schematic_images")
            
            run_ana_w1_agent(
                workspace=str(self.iteration_manager.current_iteration_dir),
                schematic_images_path=schematic_images_path,
                scud_path=scud_path,
                circuit_name=self.circuit_name
            )

            if not os.path.exists(self.iteration_manager.get_circuit_tsx_path()):
                logger.error(f"[ANA-D SM] ANA-W1 did not produce circuit file")
                result_msg["proposed_next_state"] = State.PREPARE_HIL
                return result_msg

            return result_msg
        except Exception as e:
            logger.error(f"Error in TRIGGER_W1: {e}")
            result_msg["proposed_next_state"] = State.PREPARE_HIL
            return result_msg

    def _handle_wait_w1(self, message: Dict[str, Any]) -> Dict[str, Any]:
        result_msg = message.copy()
        result_msg["state_id"] = State.WAIT_W1
        return result_msg

    def _handle_trigger_w2(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[ANA-D SM] State: TRIGGER_W2. Invoking VHL-VAP...")
        result_msg = message.copy()
        result_msg["state_id"] = State.TRIGGER_W2
        
        agent = ANA_validation_agent()
        try:
            result = agent.validate_circuit(
                self.circuit_name, 
                workspace=self.iteration_manager.current_iteration_dir
            )
            vap_decision = result.get("decision")
            result_msg["vap_decision"] = vap_decision
            logger.info(f"[ANA-D SM] VAP decision: {vap_decision}")
            return result_msg
        except Exception as e:
            logger.exception(f"Error during validation: {e}")
            # Clear decision on failure
            result_msg.pop("vap_decision", None)
            raise e
        finally:
            agent.close()

    def _handle_wait_vap(self, message: Dict[str, Any]) -> Dict[str, Any]:
        result_msg = message.copy()
        result_msg["state_id"] = State.WAIT_VAP
        return result_msg

    def _handle_prepare_hil(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("[ANA-D SM] State: PREPARE_HIL. Escalating to human...")
        result_msg = message.copy()
        result_msg["state_id"] = State.PREPARE_HIL
        return result_msg

    def _handle_hil_wait(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("[ANA-D SM] State: HIL_WAIT. Awaiting human authority...")
        result_msg = message.copy()
        result_msg["state_id"] = State.HIL_WAIT
        
        event = message.get("event")
        data = message.get("data")
        
        if event == "human_response":
            logger.info("[ANA-D SM] Human responded. Transitioning to INIT.")
            result_msg["proposed_next_state"] = State.INIT
            return result_msg
        elif event == "abort":
            logger.info("[ANA-D SM] Process aborted by human. Transitioning to EXIT_ABORT.")
            result_msg["proposed_next_state"] = State.EXIT_ABORT
            return result_msg
        
        return result_msg

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