from enum import Enum, auto

class CPAState(Enum):
    INIT = auto()
    TRIGGER_SYNTHESISER = auto()
    TRIGGER_VALIDATOR = auto()
    FINALIZE = auto()
    EXIT_SUCCESS = auto()
    EXIT_ERROR = auto()
    COMPLETED = auto()
