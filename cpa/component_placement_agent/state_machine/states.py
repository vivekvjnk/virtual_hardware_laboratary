from enum import Enum, auto

class CPAState(Enum):
    INIT = auto()
    EXECUTE = auto()
    VERIFY = auto()
    FINALIZE = auto()
    EXIT_SUCCESS = auto()
    EXIT_ERROR = auto()
    COMPLETED = auto()
