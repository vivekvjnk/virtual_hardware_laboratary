from enum import Enum, auto

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
