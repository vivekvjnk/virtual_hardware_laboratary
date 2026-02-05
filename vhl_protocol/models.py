from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
import uuid

VHL_PROTOCOL_VERSION = "0.1"

class EventSource(str, Enum):
    RUNTIME = "runtime"
    BACKEND = "backend"

class EventType(str, Enum):
    # Runtime -> Backend (Observation Events)
    HUMAN_INPUT = "HUMAN_INPUT"
    REFERENCE_UPLOADED = "REFERENCE_UPLOADED"
    INTERRUPT_REQUEST = "INTERRUPT_REQUEST"
    
    # Backend -> Runtime (System Events)
    STATE_TRANSITION = "STATE_TRANSITION"
    EVALUATION_UPDATE = "EVALUATION_UPDATE"
    ARTIFACT_UPDATED = "ARTIFACT_UPDATED"
    AUTHORITY_REQUIRED = "AUTHORITY_REQUIRED"
    ERROR = "ERROR"
    
    # Transport-Only (Relay Layer)
    IDENTIFY = "IDENTIFY"
    AGENT_CONNECTED = "AGENT_CONNECTED"
    AGENT_DISCONNECTED = "AGENT_DISCONNECTED"

class BaseEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType
    artifact_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    source: EventSource
    payload: Dict[str, Any] = Field(default_factory=dict)

# Payload models

class HumanInputPayload(BaseModel):
    content: str
    intent: str # freeform | authority_response | acknowledgement
    context_refs: List[str] = Field(default_factory=list)

class ReferenceUploadedPayload(BaseModel):
    reference_id: str
    reference_type: str # schematic | datasheet | image | pdf
    filename: str

class InterruptRequestPayload(BaseModel):
    reason: str

class StateTransitionPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    from_state: str = Field(alias="from")
    to_state: str = Field(alias="to")
    reason: str

class EvaluationUpdatePayload(BaseModel):
    phase: str # validation | compilation
    status: str # running | pass | fail
    evidence_refs: List[str] = Field(default_factory=list)

class ArtifactUpdatedPayload(BaseModel):
    artifact_type: str # code | changelog | report
    artifact_version: str
    summary: str

class AuthorityRequiredPayload(BaseModel):
    question: str
    options: List[str] = Field(default_factory=list)
    blocking: bool = True

class ErrorPayload(BaseModel):
    scope: str # validation | generation | runtime
    severity: str # warning | error | fatal
    message: str

class IdentifyPayload(BaseModel):
    role: str # ui | agent

class AgentPresencePayload(BaseModel):
    agent_id: Optional[str] = None
    status: str # connected | disconnected
