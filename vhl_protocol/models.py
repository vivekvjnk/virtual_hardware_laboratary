from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
import uuid

VHL_PROTOCOL_VERSION = "0.1"

class EventSource(str, Enum):
    VHL_WEBUI = "vhl_webui"
    VHL_AGENT_BACKEND = "vhl_agent_backend"
    VHL_RUNTIME = "vhl_runtime"
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
    TRIGGER_CPA_AGENT = "TRIGGER_CPA_AGENT"
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
    VAP_EXECUTE = "VAP_EXECUTE"
    VAP_COMPLETE = "VAP_COMPLETE"
    VAP_DECISION = "VAP_DECISION"
    
    # ANA Communication
    ANA_NOTIFY = "ANA_NOTIFY"

    # System State
    GET_SYSTEM_STATE = "GET_SYSTEM_STATE"
    SYSTEM_STATE = "SYSTEM_STATE"
    PROJECT_STATE = "PROJECT_STATE"
    AGENT_STATE = "AGENT_STATE"
    AGENT_HEALTH = "AGENT_HEALTH"

    # Sync Protocol
    UPLOAD_REQUEST = "UPLOAD_REQUEST"
    DOWNLOAD_REQUEST = "DOWNLOAD_REQUEST"
    SYNC_COMPLETE = "SYNC_COMPLETE"
    SYNC_ERROR = "SYNC_ERROR"

    # Dev Server
    DEV_SERVER_READY = "DEV_SERVER_READY"

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
    model_config = ConfigDict(populate_by_name=True, extra='allow')
    
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
    role: str # vhl_webui | vhl_agent_backend | vhl_runtime

class WorkspacePayload(BaseModel):
    reference_id: Optional[str] = None
    storage_path: Optional[str] = None
    filename: Optional[str] = None
    message: Optional[str] = None

class AgentPresencePayload(BaseModel):
    agent_id: Optional[str] = None
    status: str # connected | disconnected

class VAPExecutePayload(BaseModel):
    circuit_name: str
    blob_id: str
    iteration_id: str

class VAPCompletePayload(BaseModel):
    task_id: str
    eval_status: Optional[str] = None
    decision: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ProjectsListPayload(BaseModel):
    projects: List[str]

class HILRequestPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra='allow')
    reason: str
    message: Optional[str] = None
    scud_content: Optional[str] = None
    scud_path: Optional[str] = None

class SyncPayload(BaseModel):
    project_id: str
    sync_id: str = None
    iteration_id: Optional[str] = None
    resource_type: str # Library | Circuit | Evaluation | StableCircuit
    intent: Optional[str] = None # EVALUATION | ALIGNMENT | RESULT
    hash: Optional[str] = None
    blob_id: Optional[str] = None
    reason: Optional[str] = None # For SYNC_ERROR
    data: Optional[Dict[str, Any]] = Field(default_factory=dict)
    source: str = None
    
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

class AgentHealthPayload(BaseModel):
    mcp_manager_status: str
    librarian_mcp_url: Optional[str] = None
    agent_states: Dict[str, str] = Field(default_factory=dict)