from enum import Enum, auto

class AOSMState(Enum):
    IDLE = auto()
    BOOTSTRAP_PIPELINE = auto()
    WAIT_FOR_ANA = auto()
    PRESENT_RESULT = auto()
    INTENT_CLASSIFY = auto()
    PREPARE_ANA_RUN = auto()
    TRIGGER_ANA = auto()
    CANCEL_PIPELINE = auto()
    ERROR_PRESENTED = auto()
    WAIT_FOR_USER = auto()
