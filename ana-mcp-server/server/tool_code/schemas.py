

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
    observations: str = Field(None, description="All observations on the error/s in simple string format.")

