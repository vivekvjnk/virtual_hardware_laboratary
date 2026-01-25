

from typing import Literal, List, Optional, Dict, Any
from pydantic import BaseModel, Field, conint, confloat


class ObservationCommit(BaseModel):
    issue_kind: Literal[
        "NONE",
        "LOCAL",
        "NON_LOCAL",
        "INTENT_MISMATCH",
    ] = Field(
        ...,
        description=(
            "Classification of the observed issue. "
            "LOCAL denotes deterministic, isolated, unambiguous failures confined to a narrow scope. "
            "NON_LOCAL denotes all other failures, including structural, hub-centric, ripple effects, or cases with ambiguity or low confidence. "
            "INTENT_MISMATCH denotes contradiction or ambiguity against explicit SCUD guarantees. "
            "NONE denotes no detected issue."
        )
    )
    confidence: confloat(ge=0.0, le=1.0) = Field(..., description="Confidence level of the  classification (0.0 to 1.0).")
    notes: Optional[str] = Field(None, description="Additional notes for the observation.")


class FixProposalCommit(BaseModel):
    summary: str = Field(..., description="A summary of the proposed fix.")
    proposed_changes: Optional[List[Dict[str, Any]]] = Field(None, description="References to proposed changes (e.g., nets, components, SCUD sections).")
    confidence: confloat(ge=0.0, le=1.0) = Field(..., description="Confidence level of the fix proposal (0.0 to 1.0).")

