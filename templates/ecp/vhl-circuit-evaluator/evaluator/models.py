"""
Models module: Dataclasses and enums for VHL circuit evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class EvaluationDecision(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"


class EvaluationStatus(str, Enum):
    SUCCESS = "Success"
    ERROR = "Error"
    RUNNING_TIMEOUT_WARNING = "RUNNING_TIMEOUT_WARNING"


class ErrorCategory(str, Enum):
    SYNTAX_ERROR = "SYNTAX_ERROR"
    COMPONENT_PIN_MISMATCH = "COMPONENT_PIN_MISMATCH"
    UNRESOLVED_IMPORT = "UNRESOLVED_IMPORT"
    UNROUTED_PORT = "UNROUTED_PORT"
    FOOTPRINT_ERROR = "FOOTPRINT_ERROR"
    TYPE_ERROR = "TYPE_ERROR"
    BUILD_FAILURE = "BUILD_FAILURE"


@dataclass
class DiagnosticError:
    category: ErrorCategory
    message: str
    line_number: Optional[int] = None
    file_path: Optional[str] = None
    raw_line: str = ""


@dataclass
class EvaluationResult:
    decision: EvaluationDecision
    status: EvaluationStatus
    circuit_file: str
    elapsed_ms: int
    exit_code: Optional[int]
    timed_out: bool
    diagnostics: List[DiagnosticError] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    log_file: Optional[str] = None
    partial_logs: List[str] = field(default_factory=list)
    pid: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["decision"] = self.decision.value
        data["status"] = self.status.value
        data["diagnostics"] = [
            {**asdict(d), "category": d.category.value} for d in self.diagnostics
        ]
        return data
