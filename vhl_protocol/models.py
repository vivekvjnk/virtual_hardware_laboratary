from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
import uuid

VHL_PROTOCOL_VERSION = "0.1"

class EventSource(str, Enum):
    RUNTIME = "runtime"
    BACKEND = "backend"
    WORKSPACE = "vhl_workspace"
    ANA = "ana"

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
    HIL_REQUEST = "HIL_REQUEST"

    # Project Management
    # Runtime -> Backend
    CREATE_PROJECT = "CREATE_PROJECT"
    LOAD_PROJECT = "LOAD_PROJECT"
    LIST_PROJECTS = "LIST_PROJECTS"
    SYNTHESIZE_CIRCUIT = "SYNTHESIZE_CIRCUIT"
    CLOSE_PROJECT = "CLOSE_PROJECT"
    # Backend -> Runtime
    PROJECT_CREATED = "PROJECT_CREATED"
    PROJECT_LOADED = "PROJECT_LOADED"
    PROJECT_CLOSED = "PROJECT_CLOSED"
    PROJECTS_LIST = "PROJECTS_LIST"

    # Workspace Management
    WORKSPACE_DOWNLOAD = "WORKSPACE_DOWNLOAD"
    WORKSPACE_UPLOAD = "WORKSPACE_UPLOAD"
    WORKSPACE_SYNC_COMPLETE = "WORKSPACE_SYNC_COMPLETE"
    
    # Transport-Only (Relay Layer)
    IDENTIFY = "IDENTIFY"
    AGENT_CONNECTED = "AGENT_CONNECTED"
    AGENT_DISCONNECTED = "AGENT_DISCONNECTED"
    WORKSPACE_CONNECTED = "WORKSPACE_CONNECTED"
    WORKSPACE_DISCONNECTED = "WORKSPACE_DISCONNECTED"

    # VAP Orchestration
    VAP_INIT = "VAP_INIT"
    VAP_INIT_COMPLETE = "VAP_INIT_COMPLETE"
    VAP_STATUS_REPORT = "VAP_STATUS_REPORT"
    VAP_DECISION = "VAP_DECISION"
    
    # ANA Communication
    ANA_NOTIFY = "ANA_NOTIFY"

    # System State
    GET_SYSTEM_STATE = "GET_SYSTEM_STATE"
    SYSTEM_STATE = "SYSTEM_STATE"
    PROJECT_STATE = "PROJECT_STATE"
    AGENT_STATE = "AGENT_STATE"

    # Sync Protocol
    HASH_REQUEST = "HASH_REQUEST"
    HASH_RESPONSE = "HASH_RESPONSE"
    UPLOAD_REQUEST = "UPLOAD_REQUEST"
    UPLOAD_PROPOSAL = "UPLOAD_PROPOSAL"
    DOWNLOAD_REQUEST = "DOWNLOAD_REQUEST"
    SYNC_TRIGGER = "SYNC_TRIGGER"
    SYNC_COMPLETE = "SYNC_COMPLETE"
    SYNC_ERROR = "SYNC_ERROR"

class BaseEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType
    artifact_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z") # ISO-8601
    source: EventSource
    payload: Optional[Dict[str, Any]] = Field(default_factory=dict)

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
    task_id: str 
    decision: str # running | ACCEPT | REJECT

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

class WorkspacePayload(BaseModel):
    reference_id: Optional[str] = None
    storage_path: Optional[str] = None
    filename: Optional[str] = None
    message: Optional[str] = None

class AgentPresencePayload(BaseModel):
    agent_id: Optional[str] = None
    status: str # connected | disconnected

class VAPInitPayload(BaseModel):
    circuit_name: str
    blob_id: str
    iteration_id: str

class VAPStatusPayload(BaseModel):
    task_id: str
    eval_status: Optional[str] = None
    decision: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ProjectsListPayload(BaseModel):
    projects: List[str]

class HILRequestPayload(BaseModel):
    reason: str
    message: Optional[str] = None

class SyncPayload(BaseModel):
    sync_id: str
    project_id: str
    iteration_id: Optional[str] = None
    resource_type: str # Library | Circuit | Evaluation | StableCircuit
    intent: Optional[str] = None # EVALUATION | ALIGNMENT | RESULT
    hash: Optional[str] = None
    blob_id: Optional[str] = None
    reason: Optional[str] = None # For SYNC_ERROR
    data: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ProjectStatus(str, Enum):
    INITIALIZED = "initialized"
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"

class AgentStatus(str, Enum):
    RUNNING = "Running"
    IDLE = "Idle"

class ProjectStatePayload(BaseModel):
    backend_status: ProjectStatus
    runtime_status: ProjectStatus

class AgentStatePayload(BaseModel):
    archy: AgentStatus
    librarian: AgentStatus
    ana: AgentStatus
    aosm: AgentStatus