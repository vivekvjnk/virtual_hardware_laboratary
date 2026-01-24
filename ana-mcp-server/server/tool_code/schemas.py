

from typing import Literal, List, Optional, Dict, Any
from pydantic import BaseModel, Field, conint, confloat


class ObservationCommit(BaseModel):
    issue_kind: Literal[
        "NONE",
        "GENERIC",
        "LOCAL_MECHANICAL",
        "INTENT_MISMATCH",
    ] = Field(..., description="Kind of issue detected, if any.")
    confidence: confloat(ge=0.0, le=1.0) = Field(..., description="Confidence level of the observation (0.0 to 1.0).")
    evidence_refs: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Opaque references to evidence.")
    notes: Optional[str] = Field(None, description="Additional notes for the observation.")


class FixProposalCommit(BaseModel):
    summary: str = Field(..., description="A summary of the proposed fix.")
    proposed_changes: Optional[List[Dict[str, Any]]] = Field(None, description="References to proposed changes (e.g., nets, components, SCUD sections).")
    confidence: confloat(ge=0.0, le=1.0) = Field(..., description="Confidence level of the fix proposal (0.0 to 1.0).")

