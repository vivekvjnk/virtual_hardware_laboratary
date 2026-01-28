from enum import Enum, auto
from typing import Optional, Dict, Any, List
import logging
import subprocess
import time
import os
import socket
import httpx
import uuid
import json
import sys

from pathlib import Path

from ana_agent.observer import ObserverAgent
from ana_agent.observer import ObserverMode

from ana_agent.ana_worker_1 import run_ana_w1_agent
from ana_agent.ana_worker_2.agent import ANA_validation_agent

logger = logging.getLogger(__name__)

class State(Enum):
    INIT = auto()
    OBSERVE = auto()
    AUTHORIZE = auto()
    PREPARE_FIX = auto()
    TRIGGER_W1 = auto()
    WAIT_W1 = auto()
    TRIGGER_W2 = auto()
    WAIT_VAP = auto()
    PREPARE_HIL = auto()
    HIL_WAIT = auto()
    EXIT_SUCCESS = auto()
    EXIT_ABORT = auto()

class ANADStateMachine:
    def __init__(self, max_auto_fixes: int = 3):
        self.state = State.INIT
        self.max_auto_fixes = max_auto_fixes
        self.auto_fix_count = 0
        
        # Inputs/Observations
        self.vap_decision: Optional[str] = "UNDECIDED" # ACCEPT / REJECT ; Default to UNDECIDED
        self.error_class: Optional[str] = None # mechanical, hub, ripple, ambiguous, none
        self.intent_status: Optional[str] = None # satisfied, violated, ambiguous
        self.observation = None

        # Context/Data
        self.context: Dict[str, Any] = {}
        self.iteration_ids: List[str] = [] # List of all iteration ids
        self.circuit_name: str = "bq79616_eval_board"  # Default circuit name

        # Workspace
        self.workspace = Path(os.getcwd()) / "ana_workspace" / f"{self.circuit_name}_project"
        self.iteration_dir: str = None

        # MCP Integration
        self.mcp_process: Optional[subprocess.Popen] = None
        self.mcp_endpoint = "http://localhost:8001"
        self.last_commit_id: int = -1
        self.iteration_id: Optional[str] = None

        # Setup mcp server for observer agent
        self._ensure_mcp_server_running()

    def step(self, event: Optional[str] = None, data: Optional[Dict[str, Any]] = None):
        """
        Executes one step of the state machine.
        'event' and 'data' are used for external inputs (like human response).
        """
        logger.info(f"Stepping from state: {self.state}")
        if self.state == State.INIT:
            self._handle_init()
        elif self.state == State.OBSERVE:
            self._handle_observe()
        elif self.state == State.AUTHORIZE:
            self._handle_authorize()
        elif self.state == State.PREPARE_FIX:
            self._handle_prepare_fix()
        elif self.state == State.TRIGGER_W1:
            self._handle_trigger_w1()
        elif self.state == State.WAIT_W1:
            self._handle_wait_w1()
        elif self.state == State.TRIGGER_W2:
            self._handle_trigger_w2()
        elif self.state == State.WAIT_VAP:
            self._handle_wait_vap()
        elif self.state == State.PREPARE_HIL:
            self._handle_prepare_hil()
        elif self.state == State.HIL_WAIT:
            self._handle_hil_wait(event, data)
        
        logger.info(f"New state: {self.state}")

    def _handle_init(self):
        # S0 -> S1
        # Generate Iteration id (Start of new Loop)
        self.iteration_id = hex(int(time.time()))[2:]
        logger.info(f"[ANA-D SM] State: INIT. Started Iteration: {self.iteration_id}")
        # Append to iteration list
        self.iteration_ids.append(self.iteration_id)

        # Create iteration folder
        self.iteration_dir = os.path.join(self.workspace, "iterations", self.iteration_id)
        os.makedirs(self.iteration_dir, exist_ok=True)
        logger.info(f"[ANA-D SM] Created iteration directory: {self.iteration_dir}")
        
        # Prepare symbolic links to schematic_images/, .scud file and pin_mapping.md file
        # These files/folders are available under self.workspace. Just create a symbolic link inside iteration directory
        schematic_images_path = os.path.join(self.workspace, "schematic_images")
        scud_file_path = f"{self.circuit_name}.scud"
        pin_mapping_src = os.path.join(self.workspace, "component_pin_mapping.md")
        
        
        # This step ensures that the iteration directory has access to all necessary resources
        # No further checks on resource availability are required anywhere else in the SM
        # We keep this as the single source of truth for resource linking
        if os.path.exists(schematic_images_path):
            schematic_images_link = os.path.join(self.iteration_dir, "schematic_images")
            if not os.path.exists(schematic_images_link):
                os.symlink(schematic_images_path, schematic_images_link)
                logger.info(f"[ANA-D SM] Created symlink for schematic_images at: {schematic_images_link}")
        else:
            raise FileNotFoundError(f"[ANA-D SM] Schematic images directory not found at expected location: {schematic_images_path}")
        
        scud_src = os.path.join(self.workspace, scud_file_path)
        scud_link = os.path.join(self.iteration_dir, scud_file_path)
        if not os.path.exists(scud_link):
            os.symlink(scud_src, scud_link)
            logger.info(f"[ANA-D SM] Created symlink for SCUD file at: {scud_link}")
        else:
            raise FileNotFoundError(f"[ANA-D SM] SCUD file not found at expected location: {scud_src}")
        
        if os.path.exists(pin_mapping_src):
            pin_mapping_link = os.path.join(self.iteration_dir, "component_pin_mapping.md")
            if not os.path.exists(pin_mapping_link):
                os.symlink(pin_mapping_src, pin_mapping_link)
                logger.info(f"[ANA-D SM] Created symlink for pin mapping at: {pin_mapping_link}")
        else:
            raise FileNotFoundError(f"[ANA-D SM] Pin mapping file not found at expected location: {pin_mapping_src}")
        
        # In a real scenario, we would load VAP output here.
        self.state = State.OBSERVE

    def _handle_observe(self):
        # S1 -> S2
        logger.info(f"[ANA-D SM] State: OBSERVE. Hash={self.iteration_id}. Ensuring MCP Server is running...")
        

        logger.info("[ANA-D SM] Triggering Observer Agent...")

        # Step 1: Logic to check if this is iteration 0 or not
        #         If len of iteration_ids state variable < 2, first iteration
        # Step 1-A: If iteration 0, go to authorize node
        if len(self.iteration_ids) < 2:
            logger.info("[ANA-D SM] First iteration detected. Skipping observation of previous iteration.")
            # Directly move to AUTHORIZE
            self.state = State.AUTHORIZE
            return

        # Step 1-B: If not iteration 0, proceed to step 2

        # Step 2: Set current working directory to previous iteration directory
        #         Get the second last element of iteration_ids state variable list,
        #         this is the iteration id of previous iteration. iteration id is the folder name.
        # Proceed observe logic as usual
        previous_iteration_id = self.iteration_ids[-2]
        previous_iteration_dir = os.path.join(self.workspace, "iterations", previous_iteration_id)
        logger.info(f"[ANA-D SM] Changed working directory to previous iteration: {previous_iteration_dir}")
        
        # Agent setup
        # TODO: Observer mode parameter has to travel from ANA_W2 to here
        # For now, hardcoding to "validation_error". After validating iteration 0, design the logic to
        # choose appropriate observer mode based on VAP decision and error class.
        observer_mode = ObserverMode("validation_error")
        # Create and run observer
        observer = ObserverAgent()
        try:
            result = observer.observe(
                mode=observer_mode,
                iteration_dir=self.iteration_id,
            )
            print("\n--- Observation Result ---")
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"Error during observation: {e}")
            logger.exception("Full stack trace:")
            sys.exit(1)
        finally:
            observer.close()

        # For now, we assume the agent is triggered externally or will be implemented soon.
        logger.info("[ANA-D SM] Awaiting commit from Observer Agent via MCP...")

        # Poll for the observation commit
        observation = self._poll_for_observation()

        if observation:
            payload = observation["message"]["payload"]
            issue_kind = payload.get("issue_kind", "UNKNOWN")

            # Update SM internal state based on observation
            
            if issue_kind == "LOCAL":
                self.intent_status = "violated"
            elif issue_kind == "NON_LOCAL":
                self.intent_status = "ambiguous"
            elif issue_kind == "INTENT_MISMATCH":
                self.intent_status = "ambiguous"
            elif issue_kind == "NONE":
                self.intent_status = "satisfied"
            else:
                self.intent_status = "ambiguous"

            logger.info(f"[ANA-D SM] Observation received: error_class={self.error_class}, intent_status={self.intent_status}")
            self.observation = observation
            self.state = State.AUTHORIZE
        else:
            logger.info("[ANA-D SM] No observation received. Staying in OBSERVE.")

    def _handle_authorize(self):
        # S2 -> S3, S8, or S10
        logger.info(f"[ANA-D SM] State: AUTHORIZE. VAP={self.vap_decision}, Error={self.error_class}, Intent={self.intent_status}, FixCount={self.auto_fix_count}")
        
        # NOTE: Source of truth for vap_decision is the output from VAP agent
        # Source of truth for error_class and intent_status is the observation from Observer agent
        # Priority of transitions:
        # 1. vap_decision is high priority than observations
        # 2. intent_status is only relevant when vap_decision is ACCEPT, error_class is only relevant when vap_decision is REJECT
        # 3. auto_fix_count is high priority than error_class when vap_decision is REJECT. This is a fallback to avoid infinite loops.
        # NOTE: Above priority rules are designed to reduce reliance on observation accuracy. Observer agent may mis-classify error_class or intent_status.
        #       Hence vap_decision is given highest priority as it is directly from VAP agent
        #       Further, auto_fix_count is given higher priority than error_class to avoid infinite loops
        # HIL state is the safe fallback for any ambiguous or unknown situations
        if self.vap_decision == "REJECT":
            # Error class other than mechanical goes to HIL directly
            if self.error_class == "mechanical" and self.auto_fix_count < self.max_auto_fixes:
                logger.info("[ANA-D SM] Transitioning to PREPARE_FIX")
                self.state = State.PREPARE_FIX
            else:
                logger.info("[ANA-D SM] Transitioning to PREPARE_HIL")
                self.state = State.PREPARE_HIL
            
            # NOTE : Temporary re-routing for testing purpose
            self.state = State.PREPARE_FIX

        elif self.vap_decision == "ACCEPT":
            if self.intent_status == "satisfied":
                logger.info("[ANA-D SM] Transitioning to EXIT_SUCCESS")
                self.state = State.EXIT_SUCCESS
            else:
                logger.info("[ANA-D SM] Transitioning to PREPARE_HIL")
                self.state = State.PREPARE_HIL
        # Branch for the iteration 0 case
        # Instead of checking the length of iteration_ids, we can check if vap_decision is UNDECIDED
        # because in iteration 0, there is no prior VAP decision. 
        elif self.vap_decision == "UNDECIDED":
            logger.info("[ANA-D SM] VAP decision UNDECIDED. Very first iteration. Transitioning to TRIGGER_W1")
            self.state = State.TRIGGER_W1
        # Default fallback
        else:
            # Default to HIL if VAP decision is unknown or missing
            logger.info(f"[ANA-D SM] Unknown VAP decision:{self.vap_decision}. Transitioning to PREPARE_HIL")
            self.state = State.PREPARE_HIL


    def _handle_prepare_fix(self):
        # S3 -> S4
        logger.info("[ANA-D SM] State: PREPARE_FIX. Constructing fix instruction...")
        self.state = State.TRIGGER_W1
        return 

    def _handle_trigger_w1(self):
        # S4 -> S5
        logger.info(f"[ANA-D SM] State: TRIGGER_W1. Invoking ANA-W1 for iteration {self.iteration_id}...")
        self.auto_fix_count += 1
        # find scud file in iteration directory. make sure only one scud file is present
        scud_files = [f for f in os.listdir(self.iteration_dir) if f.endswith(".scud")]
        if not scud_files:
            logger.error(f"[ANA-D SM] No .scud file found in iteration directory: {self.iteration_dir}")
            self.state = State.PREPARE_HIL
            return
        elif len(scud_files) > 1:
            logger.error(f"[ANA-D SM] Multiple .scud files found in iteration directory: {self.iteration_dir}. Expected only one.")
            self.state = State.PREPARE_HIL
            return
        scud_path = os.path.join(self.iteration_dir, scud_files[0])
        schematic_images_path = os.path.join(self.iteration_dir, "schematic_images")

        # Call ANA-W1 agent 
        run_ana_w1_agent(schematic_images_path=schematic_images_path, scud_path=scud_path, circuit_name=self.circuit_name)

        # Inspect workspace for new circuit tsx file with self.circuit_name
        circuit_path = os.path.join(self.iteration_dir, f"{self.circuit_name}.tsx")
        if not os.path.exists(circuit_path):
            logger.error(f"[ANA-D SM] ANA-W1 did not produce expected circuit file: {circuit_path}")
            self.state = State.PREPARE_HIL
            return

        logger.info(f"[ANA-D SM] ANA-W1 produced circuit file: {circuit_path}")
        # NOTE: For now we don't enter into WAIT_W1 state, instead directly move to TRIGGER_W2
        # run_ana_w1_agent is blocking and will complete before moving to next state
        # Don't find any use case for WAIT_W1 state currently

        # self.state = State.WAIT_W1
        self.state = State.TRIGGER_W2
        
        # ASSUMPTION: Now iteration directory will have circuit tsx files from ANA-W1
        return
    
    # NOTE: Currently unused state
    def _handle_wait_w1(self):
        # S5 -> S6
        logger.info("[ANA-D SM] State: WAIT_W1. Awaiting ANA-W1 output...")
        # In a real scenario, this might be async or polled.
        self.state = State.TRIGGER_W2

    def _handle_trigger_w2(self):
        # S6 -> S7
        logger.info(f"[ANA-D SM] State: TRIGGER_W2. Invoking VHL-VAP for iteration {self.iteration_id}...")

        agent = ANA_validation_agent()
        try:
            result = agent.validate_circuit(self.circuit_name, workspace=self.iteration_dir)
            print("\n--- Evaluation Results ---")
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"Error during validation: {e}")
            logger.exception("Full stack trace:")
            raise e
        finally:
            agent.close()
        # `decision` key from result dictionary indicates VAP decision. "ACCEPT" | "REJECT" are the two possible values
        self.vap_decision = result.get("decision")
        logger.info(f"[ANA-D SM] VAP decision received: {self.vap_decision}")
        self.state = State.INIT

    # NOTE: Currently unused state
    def _handle_wait_vap(self):
        # S7 -> S0
        logger.info("[ANA-D SM] State: WAIT_VAP. Awaiting VAP results...")
        # Loop back to INIT with new VAP output
        self.state = State.INIT

    def _handle_prepare_hil(self):
        # S8 -> S9
        logger.info("[ANA-D SM] State: PREPARE_HIL. Escalating to human...")
        self.state = State.HIL_WAIT

    def _handle_hil_wait(self, event: Optional[str], data: Optional[Dict[str, Any]]):
        # S9 -> S0 or S11
        logger.info("[ANA-D SM] State: HIL_WAIT. Awaiting human authority...")
        if event == "human_response":
            logger.info("[ANA-D SM] Human responded. Transitioning to INIT.")
            # Update observations based on human input if needed
            self.state = State.INIT
        elif event == "abort":
            logger.info("[ANA-D SM] Process aborted by human. Transitioning to EXIT_ABORT.")
            self.state = State.EXIT_ABORT
        else:
            logger.info("[ANA-D SM] Still waiting for human input...")

    def is_terminal(self) -> bool:
        return self.state in [State.EXIT_SUCCESS, State.EXIT_ABORT]

    def cleanup(self):
        """Cleanup resources, including MCP server process."""
        if self.mcp_process:
            logger.info("[ANA-D SM] Shutting down MCP Server...")
            self.mcp_process.terminate()
            try:
                self.mcp_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.info("[ANA-D SM] MCP Server did not terminate, killing...")
                self.mcp_process.kill()
            self.mcp_process = None
            logger.info("[ANA-D SM] MCP Server shut down.")

    def _ensure_mcp_server_running(self):
        """Starts the MCP server if it's not already running on port 8000."""
        try:
            # Check if something is already listening on port 8000
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect(("127.0.0.1", 8001))
            logger.info("[ANA-D SM] MCP Server already running on port 8000.")
            return
        except (ConnectionRefusedError, socket.timeout):
            pass

        logger.info("[ANA-D SM] Starting MCP Server process...")
        # Find project root (assuming we are in ana_designer/)
        cwd = os.getcwd()
        
        # Use uv run to ensure all dependencies are available
        cmd = [
            "uv", "run",
            "--package", "ana-mcp-server", 
            "uvicorn", "server.main:app",
            "--port", "8001",
        ]
        
        self.mcp_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "PYTHONPATH": cwd},
            cwd=cwd,
            start_new_session=True
        )
        # Wait for server to start
        max_retries = 15
        for i in range(max_retries):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    s.connect(("127.0.0.1", 8001))
                logger.info(f"[ANA-D SM] MCP Server started on attempt {i+1}")
                return
            except (ConnectionRefusedError, socket.timeout):
                time.sleep(1)
        
        logger.info("[ANA-D SM] ERROR: Failed to start MCP Server.")

    def _poll_for_observation(self) -> Optional[Dict[str, Any]]:
        """Polls MCP for an observation commit since last_commit_id."""
        url = f"{self.mcp_endpoint}/mcp/commits"
        params = {
            "since": self.last_commit_id,
            "endpoint": "/mcp/observe"
        }

        logger.info(f"[ANA-D SM] Polling {url} with since={self.last_commit_id}...")
        
        # In a real scenario, this would have a timeout and potentially be non-blocking
        # For this implementation, we poll until we find a matching commit
        while True:
            try:
                with httpx.Client() as client:
                    response = client.get(url, params=params)
                    if response.status_code == 200:
                        commits = response.json().get("commits", [])
                        for commit in commits:
                            if commit["tool_name"] == "commit_observation":
                                # Found our commit
                                self.last_commit_id = commit["commit_id"]
                                return commit
                
                # If no commit yet, wait and try again
                time.sleep(2)
            except Exception as e:
                logger.info(f"[ANA-D SM] Polling error: {e}")
                time.sleep(2)

if __name__ == "__main__":
    # Simple test run
    sm = ANADStateMachine()
    
    
    logger.info("--- Starting State Machine ---")
    while not sm.is_terminal() and sm.state != State.HIL_WAIT:
        sm.step()


    
    if sm.state == State.EXIT_SUCCESS:
        logger.info("Simulation Finished: SUCCESS")
    