from enum import Enum, auto
from typing import Optional, Dict, Any
import logging

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
        print("[ANA-D SM] State: INIT. Received VAP output.")
        # In a real scenario, we would load VAP output here.
        self.state = State.OBSERVE

    def _handle_observe(self):
        # S1 -> S2
        print("[ANA-D SM] State: OBSERVE. Running LLM classifier...")
        # Placeholder for LLM classifier output
        # For now, we'll assume some defaults or wait for modular attachment
        if self.error_class is None:
            self.error_class = "ambiguous"
        if self.intent_status is None:
            self.intent_status = "ambiguous"
            
        self.state = State.AUTHORIZE

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
        print("[ANA-D SM] State: TRIGGER_W1. Invoking ANA-W1...")
        self.auto_fix_count += 1
        self.state = State.WAIT_W1

    def _handle_wait_w1(self):
        # S5 -> S6
        print("[ANA-D SM] State: WAIT_W1. Awaiting ANA-W1 output...")
        # In a real scenario, this might be async or polled.
        self.state = State.TRIGGER_W2

    def _handle_trigger_w2(self):
        # S6 -> S7
        print("[ANA-D SM] State: TRIGGER_W2. Invoking VHL-VAP...")
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
