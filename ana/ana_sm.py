from enum import Enum, auto
from typing import Optional, Dict, Any, List
import logging
import subprocess
import time
import os
import socket
import httpx
import uuid

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
        self.vap_decision: Optional[str] = None # ACCEPT / REJECT
        self.error_class: Optional[str] = None # mechanical, hub, ripple, ambiguous, none
        self.intent_status: Optional[str] = None # satisfied, violated, ambiguous
        
        # Context/Data
        self.context: Dict[str, Any] = {}

        # MCP Integration
        self.mcp_process: Optional[subprocess.Popen] = None
        self.mcp_endpoint = "http://localhost:8000"
        self.last_commit_id: int = -1
        self.iteration_hash: Optional[str] = None

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
        # Generate Iteration Hash (Start of new Loop)
        self.iteration_hash = uuid.uuid4().hex
        print(f"[ANA-D SM] State: INIT. Started Iteration: {self.iteration_hash}")
        
        # Create iteration folder
        iteration_dir = os.path.join(os.getcwd(), "iterations", self.iteration_hash)
        os.makedirs(iteration_dir, exist_ok=True)
        print(f"[ANA-D SM] Created iteration directory: {iteration_dir}")

        print("[ANA-D SM] Received VAP output.")
        # In a real scenario, we would load VAP output here.
        self.state = State.OBSERVE

    def _handle_observe(self):
        # S1 -> S2
        print(f"[ANA-D SM] State: OBSERVE. Hash={self.iteration_hash}. Ensuring MCP Server is running...")
        self._ensure_mcp_server_running()

        print("[ANA-D SM] Triggering Observer Agent...")
        # TODO: Implement actual agent trigger here
        # For now, we assume the agent is triggered externally or will be implemented soon.
        print("[ANA-D SM] Awaiting commit from Observer Agent via MCP...")

        # Poll for the observation commit
        observation = self._poll_for_observation()

        if observation:
            payload = observation["message"]["payload"]
            verdict = payload.get("verdict")
            issue_kind = payload.get("issue_kind", "UNKNOWN")

            # Update SM internal state based on observation
            self.error_class = issue_kind.lower().replace("local_", "").replace("_structural", "").replace("_centric", "")
            
            if verdict == "NO_ISSUE":
                self.intent_status = "satisfied"
            elif verdict == "ISSUE_DETECTED":
                self.intent_status = "violated"
            else:
                self.intent_status = "ambiguous"

            print(f"[ANA-D SM] Observation received: verdict={verdict}, error_class={self.error_class}, intent_status={self.intent_status}")
            self.state = State.AUTHORIZE
        else:
            print("[ANA-D SM] No observation received. Staying in OBSERVE.")

    def _ensure_mcp_server_running(self):
        """Starts the MCP server if it's not already running on port 8000."""
        try:
            # Check if something is already listening on port 8000
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect(("127.0.0.1", 8000))
            print("[ANA-D SM] MCP Server already running on port 8000.")
            return
        except (ConnectionRefusedError, socket.timeout):
            pass

        print("[ANA-D SM] Starting MCP Server process...")
        # Find project root (assuming we are in ana_designer/)
        cwd = os.getcwd()
        
        # Use uv run to ensure all dependencies are available
        cmd = [
            "uv", "run",
            "--with", "fastapi",
            "--with", "uvicorn",
            "--with", "pydantic",
            "uvicorn", "mcp_server.main:app",
            "--port", "8000",
            "--log-level", "warning"
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
                    s.connect(("127.0.0.1", 8000))
                print(f"[ANA-D SM] MCP Server started on attempt {i+1}")
                return
            except (ConnectionRefusedError, socket.timeout):
                time.sleep(1)
        
        print("[ANA-D SM] ERROR: Failed to start MCP Server.")

    def _poll_for_observation(self) -> Optional[Dict[str, Any]]:
        """Polls MCP for an observation commit since last_commit_id."""
        url = f"{self.mcp_endpoint}/mcp/commits"
        params = {
            "since": self.last_commit_id,
            "endpoint": "/mcp/observe"
        }

        print(f"[ANA-D SM] Polling {url} with since={self.last_commit_id}...")
        
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
                print(f"[ANA-D SM] Polling error: {e}")
                time.sleep(2)

    def _handle_authorize(self):
        # S2 -> S3, S8, or S10
        print(f"[ANA-D SM] State: AUTHORIZE. VAP={self.vap_decision}, Error={self.error_class}, Intent={self.intent_status}, FixCount={self.auto_fix_count}")
        
        if self.vap_decision == "REJECT":
            if self.error_class == "mechanical" and self.auto_fix_count < self.max_auto_fixes:
                print("[ANA-D SM] Transitioning to PREPARE_FIX")
                self.state = State.PREPARE_FIX
            else:
                print("[ANA-D SM] Transitioning to PREPARE_HIL")
                self.state = State.PREPARE_HIL
        elif self.vap_decision == "ACCEPT":
            if self.intent_status == "satisfied":
                print("[ANA-D SM] Transitioning to EXIT_SUCCESS")
                self.state = State.EXIT_SUCCESS
            else:
                print("[ANA-D SM] Transitioning to PREPARE_HIL")
                self.state = State.PREPARE_HIL
        else:
            # Default to HIL if VAP decision is unknown or missing
            print("[ANA-D SM] Unknown VAP decision. Transitioning to PREPARE_HIL")
            self.state = State.PREPARE_HIL

    def _handle_prepare_fix(self):
        # S3 -> S4
        print("[ANA-D SM] State: PREPARE_FIX. Constructing fix instruction...")
        self.state = State.TRIGGER_W1

    def _handle_trigger_w1(self):
        # S4 -> S5
        print(f"[ANA-D SM] State: TRIGGER_W1. Invoking ANA-W1 for iteration {self.iteration_hash}...")
        self.auto_fix_count += 1
        self.state = State.WAIT_W1

    def _handle_wait_w1(self):
        # S5 -> S6
        print("[ANA-D SM] State: WAIT_W1. Awaiting ANA-W1 output...")
        # In a real scenario, this might be async or polled.
        self.state = State.TRIGGER_W2

    def _handle_trigger_w2(self):
        # S6 -> S7
        print(f"[ANA-D SM] State: TRIGGER_W2. Invoking VHL-VAP for iteration {self.iteration_hash}...")
        self.state = State.WAIT_VAP

    def _handle_wait_vap(self):
        # S7 -> S0
        print("[ANA-D SM] State: WAIT_VAP. Awaiting VAP results...")
        # Loop back to INIT with new VAP output
        self.state = State.INIT

    def _handle_prepare_hil(self):
        # S8 -> S9
        print("[ANA-D SM] State: PREPARE_HIL. Escalating to human...")
        self.state = State.HIL_WAIT

    def _handle_hil_wait(self, event: Optional[str], data: Optional[Dict[str, Any]]):
        # S9 -> S0 or S11
        print("[ANA-D SM] State: HIL_WAIT. Awaiting human authority...")
        if event == "human_response":
            print("[ANA-D SM] Human responded. Transitioning to INIT.")
            # Update observations based on human input if needed
            self.state = State.INIT
        elif event == "abort":
            print("[ANA-D SM] Process aborted by human. Transitioning to EXIT_ABORT.")
            self.state = State.EXIT_ABORT
        else:
            print("[ANA-D SM] Still waiting for human input...")

    def is_terminal(self) -> bool:
        return self.state in [State.EXIT_SUCCESS, State.EXIT_ABORT]

    def cleanup(self):
        """Cleanup resources, including MCP server process."""
        if self.mcp_process:
            print("[ANA-D SM] Shutting down MCP Server...")
            self.mcp_process.terminate()
            try:
                self.mcp_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("[ANA-D SM] MCP Server did not terminate, killing...")
                self.mcp_process.kill()
            self.mcp_process = None
            print("[ANA-D SM] MCP Server shut down.")

if __name__ == "__main__":
    # Simple test run
    sm = ANADStateMachine()
    
    # Simulate a mechanical failure that gets fixed
    sm.vap_decision = "REJECT"
    sm.error_class = "mechanical"
    
    print("--- Starting Simulation: Mechanical Fix ---")
    while not sm.is_terminal() and sm.state != State.HIL_WAIT:
        sm.step()
        if sm.state == State.WAIT_VAP:
            # Simulate VAP success after fix
            sm.step() # Move to INIT
            sm.vap_decision = "ACCEPT"
            sm.intent_status = "satisfied"
            sm.error_class = "none"
    
    if sm.state == State.EXIT_SUCCESS:
        print("Simulation Finished: SUCCESS")
    
    # Simulate an ambiguous failure that goes to HIL
    print("\n--- Starting Simulation: Ambiguous HIL ---")
    sm = ANADStateMachine()
    sm.vap_decision = "REJECT"
    sm.error_class = "ambiguous"
    
    while not sm.is_terminal() and sm.state != State.HIL_WAIT:
        sm.step()
    
    if sm.state == State.HIL_WAIT:
        print("Simulation Paused: HIL_WAIT")
        sm.step(event="human_response")
        print(f"After human response, state is: {sm.state}")
