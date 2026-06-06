import asyncio
import logging
import os
import sys
import json
from typing import Optional, Dict, Any, Union, Tuple
from pathlib import Path
from state_machine.states import AOSMState
from vhl_protocol.client.client import VHLWebSocketClient
from vhl_protocol.models import BaseEvent, EventType, EventSource, SyncPayload, AgentStatus
from vhl_protocol.sync.client import SyncClient

import uuid
from ana_agent.state_machine.mcp_manager import MCPManager
from ana_agent.state_machine import ANADStateMachine
from workspace.manager import WorkspaceManager

from vhl_common.urp.data_types import AgentContext, MessageEnvelope, AgentDescriptor
from vhl_common.urp.agent_registry import register_agent_if_absent, get_agent_factory

from archy_agent.main import orchestrate_archy, prepare_archy_workspace
from archy_agent.urp_archy import ArchyURPAgent, ArchyConfig

from librarian_agent.urp_librarian import LibrarianURPAgent, LibrarianConfig
from librarian_agent.stub import process_scud_stub
from vhl_common.utils import handle_errors
from vhl_common.project_state_manager.evaluators.project_creation_evaluator import ProjectCreationEvaluator
from archy.archy_agent.archy_evaluator import ArchyEvaluator
from librarian.librarian_agent.librarian_evaluator import LibrarianEvaluator


from vhl_common.urp.data_types import LastTaskOutcome
from vhl_common.supervisor import Supervisor, AgentNotFoundError
from vhl_common.supervisor.controllers import Workflow1Controller

logger = logging.getLogger(__name__)


class AOSM:
    """
    Agentic Orchestration State Machine (AOSM)
    Always-on, time-aware control layer for VHL.
    """
    def __init__(self, ws_url: str = "ws://localhost:1080", workspace_path:Path = Path("vhl_workspace").resolve()):
        logger.info(f"[AOSM.__init__] Initializing AOSM with ws_url: {ws_url}")
        self.state = AOSMState.STARTUP
        self.web_socket_client = VHLWebSocketClient(
            url=ws_url,
            role="vhl_agent_backend"
        )
        self.current_message: Dict[str, Any] = {
            "state_id": self.state,
            "observations": []
        }
        self.event_queue = asyncio.Queue()
        self.workspace_manager = WorkspaceManager(workspace_path)
        self.project_root_info: Optional[Dict[str, Any]] = None
        self.active_ana_sm: Optional[ANADStateMachine] = None
        self.ana_inbox: Optional[asyncio.Queue] = None
        self._main_loop_task: Optional[asyncio.Task] = None
        self.project_id = None
        self._init_supervisor()
        lib_default = "http://localhost:8082/sse"
        self.librarian_mcp_url = os.getenv("LIBRARIAN_MCP_URL", lib_default)
        self.mcp_manager = None
        self.agent_state = {
            "archy": AgentStatus.IDLE,
            "librarian": AgentStatus.IDLE,
            "ana": AgentStatus.IDLE,
            "aosm": AgentStatus.RUNNING
        }
        
        # Enable following configuration for VAP over MCP server
        # mcp_default = "http://localhost:8081/mcp/vap"
        self.sync_client = SyncClient(self.web_socket_client, self.workspace_manager)
        # mcp_endpoint = os.getenv("MCP_ENDPOINT", mcp_default)
        # self.mcp_manager = MCPManager(endpoint=mcp_endpoint)
        # HIL is now managed by Supervisor
        
    def _init_supervisor(self):
        self.supervisor = Supervisor()
        self.workflow_controller = Workflow1Controller(
            supervisor=self.supervisor,
            workspace_manager=self.workspace_manager,
            on_status_update=self.update_agent_status
        )
        self.supervisor.register_controller(self.workflow_controller)
        
    async def start(self):
        """Starts AOSM and the WebSocket client."""
        logger.info("[AOSM.start] Starting AOSM...")
        self.supervisor.start()
        self.web_socket_client.add_subscriber(self._handle_ws_event)
        await self.web_socket_client.start()
        # Verify MCP server is running (it's managed by VHL Runtime)
        if self.mcp_manager:
            await asyncio.to_thread(self.mcp_manager.ensure_server_running)
        self._main_loop_task = asyncio.create_task(self._main_loop())
        asyncio.create_task(self._heartbeat_loop())
        await self.broadcast_agent_state()

    async def broadcast_agent_state(self):
        """Broadcasts the current state of all agents."""
        
        # Merge local AOSM/ANA states with Supervisor URP agent states
        system_view = self.supervisor.get_system_state()
        
        archy_status = self.agent_state["archy"]
        librarian_status = self.agent_state["librarian"]
        
        for agent_id, data in system_view.items():
            if "archy" in agent_id:
                archy_status = data["status"]
                self.agent_state["archy"] = archy_status
            elif "librarian" in agent_id:
                librarian_status = data["status"]
                self.agent_state["librarian"] = librarian_status
                
        await self.web_socket_client.emit_agent_state(
            archy=archy_status,
            librarian=librarian_status,
            ana=self.agent_state["ana"],
            aosm=self.agent_state["aosm"]
        )

    def update_agent_status(self, agent_name: str, status: AgentStatus):
        """Updates internal agent status and triggers broadcast."""
        if agent_name in self.agent_state:
            self.agent_state[agent_name] = status
            asyncio.create_task(self.broadcast_agent_state())

    async def stop(self):
        """Stops AOSM and the WebSocket client."""
        logger.info("[AOSM.stop] Stopping AOSM...")
        await self.supervisor.stop()
        self.web_socket_client.remove_subscriber(self._handle_ws_event)
        if self._main_loop_task:
            self._main_loop_task.cancel()
            
        # Stop HIL Terminal input loop
        # HIL is stopped by Supervisor
        
        await self.web_socket_client.stop()

    async def _handle_ws_event(self, event: BaseEvent):
        """Callback for received WebSocket events."""
        logger.debug(f"[AOSM._handle_ws_event] AOSM received event: {event.type}")
        await self.event_queue.put(event)

    async def _main_loop(self):
        """Main loop that processes events and drives transitions."""
        while True:
            event = await self.event_queue.get()
            try:
                await self.process_event(event)
            except Exception as e:
                logger.error(f"[AOSM._main_loop] Error processing event: {e}", exc_info=True)
            finally:
                self.event_queue.task_done()

    async def _heartbeat_loop(self):
        """Loop that emits AGENT_HEALTH telemetry back to VHL_runtime."""
        logger.info("[AOSM._heartbeat_loop] started.")
        while True:
            try:
                mcp_status = "initialized" if self.mcp_manager else "not_initialized"
                system_view = self.supervisor.get_system_state()
                for agent_id, data in system_view.items():
                    if "archy" in agent_id:
                        self.agent_state["archy"] = data["status"]
                    elif "librarian" in agent_id:
                        self.agent_state["librarian"] = data["status"]
                        
                agent_states = {k: v.name if hasattr(v, 'name') else str(v) for k, v in self.agent_state.items()}
                
                await self.web_socket_client.emit_agent_health(
                    mcp_manager_status=mcp_status,
                    librarian_mcp_url=self.librarian_mcp_url,
                    agent_states=agent_states
                )
            except Exception as e:
                logger.error(f"[AOSM._heartbeat_loop] Error emitting heartbeat: {e}")
            finally:
                await asyncio.sleep(15)

    async def process_event(self, event: BaseEvent):
        """
        Processes a single event and triggers state transitions.
        """
        # Pretty log the event for visual validation
        separator = "═" * 100
        event_json = event.model_dump_json(indent=2)
        logger.debug(
            f"\n{separator}\n"
            f"📥 [AOSM] INCOMING EVENT: {event.type}\n"
            f"{'─' * 100}\n"
            f"{event_json}\n"
            f"{separator}"
        )
        
        if event.type == EventType.CLOSE_PROJECT:
            logger.info(f"👉 [AOSM] Handling CLOSE_PROJECT")
            await self._handle_close_project(event)
            return

        # Dispatch to handler based on current state and event
        handler_name = f"_handle_{self.state.name.lower()}"
        handler = getattr(self, handler_name, None)
        
        if handler:
            # logger.info(f"👉 [AOSM] Dispatching to handler: {handler_name}")
            await handler(event)
        else:
            logger.warning(f"⚠️ [AOSM] No handler defined for state {self.state} to process {event.type}")

    async def transition_to(self, next_state: AOSMState, reason: str = "", payload: Optional[Dict[str, Any]] = None):
        """Transitions to a new state and emits a state transition event.
            This transition function is internal to AOSM
        """
        from_state = self.state
        self.state = next_state
        
        # Update current message
        self.current_message["state_id"] = next_state
        logger.info(f"[AOSM.transition_to] Incoming payload for {next_state.name}: {payload}")
        
        if payload is None:
            payload = {}
        else:
            payload = dict(payload) # Ensure it's a mutable dict
            
        payload.update({
                "from": from_state.name,
                "to": next_state.name,
                "reason": reason
            })
        
        
        # Notify the UI/Protocol layer
        extra_fields = {k: v for k, v in payload.items() if k not in ["from", "to", "reason"]}
        await self.web_socket_client.emit_state_transition(
            from_state=from_state.name,
            to_state=next_state.name,
            reason=reason,
            **extra_fields
        )
        
        
        
        logger.info(f"[AOSM.transition_to] Transitioning: {from_state.name} -> {next_state.name} (Reason: {reason})\nPayload: {payload}")
        # Push an internal transition event to the queue to trigger any "on_enter" logic
        # or immediate next steps in the state machine loop.
        await self.event_queue.put(BaseEvent(
            type=EventType.STATE_TRANSITION,
            source=EventSource.VHL_AGENT_BACKEND,
            payload=payload
        ))
    
    async def _aosm_error_transition(self, event: BaseEvent, **kwargs):
        """Common error handler for aosm."""
        error = kwargs.get("error")
        logger.error(f"[AOSM._aosm_error_transition] Agent failure: {error}")
        await self.transition_to(AOSMState.ERROR_PRESENTED, f"Agent execution failed: {error}")
    

    async def _parent_notify(self, payload: Dict[str, Any]):
        """
        Callback passed to child state machines (like ANA) to notify AOSM of events.
        """
        logger.info(f"[AOSM._parent_notify] Received parent notification with payload: {payload}")
        await self.event_queue.put(BaseEvent(
            type=EventType.ANA_NOTIFY,
            source=EventSource.ANA,
            payload=payload
        ))

    # --- State Handlers --- BEGIN

    async def _handle_startup(self, event: BaseEvent):
        """
        Handles PROJECT_CREATE, PROJECT_LOAD, and LIST_PROJECTS events to manage project lifecycle.
        PROJECT_CREATE: Creates a new project with a unique ID, sets up workspace, and transitions to IDLE.
        PROJECT_LOAD: Loads an existing project by ID, sets up workspace, and transitions to IDLE.
        LIST_PROJECTS: Lists all available projects in the workspace and emits them back to the UI.
        """
        logger.info(f"[AOSM._handle_startup] In STARTUP state...")
        if event.type == EventType.CREATE_PROJECT:
            payload = event.payload or {}
            project_name = payload.get("project_name", "untitled")
            project_zip_blob_id = payload.get("zip_blob_id")

            zip_present = False
            if project_zip_blob_id:
                logger.info(f"[AOSM._handle_startup] Downloading project zip: {project_zip_blob_id}")
                sync_payload = SyncPayload(
                    sync_id=str(uuid.uuid4()),
                    project_id="",
                    resource_type="ProjectZip",
                    blob_id=f"uploads/{project_zip_blob_id}",
                    source=EventSource.VHL_AGENT_BACKEND,
                )
                await self.sync_client.handle_download_request(sync_payload)
                zip_present = True
            

            # Generate project_id with <project_name>_<UID>
            project_id = f"{project_name}_{uuid.uuid4().hex[:8]}"
            self.project_id = project_id
            
            logger.info(f"[AOSM._handle_startup] Creating new project: {project_id}")
            project_root = self.workspace_manager.create_project(project_id, zip_present=zip_present)

            # Evaluate project creation success and update semantic db with the result. 
            self.project_semantic_db = self.workspace_manager.sqlite_db
            project_creation_evaluator = ProjectCreationEvaluator(db=self.project_semantic_db) # Module name is not relevant for project creation evaluator as of now since it only checks for the presence of a baseline snapshot in the db which is created during project creation workflow. We can consider refactoring this later to remove the module_name dependency from the evaluator if it continues to be irrelevant for its logic.
            project_creation_evaluator.evaluate() # With this step, evaluator will commit a semantic operation to the semantic db. Based on the status of this operation, agent registry should compute the readiness of the Archy agent.
            # TODO: 
            # Current implementation of ProjectCreationEvaluator uses hardcoded Agent ID and Operation Name(defined in the evaluator implementation code), so we can directly use those values in the Archy agent readiness function to check the status of the project creation workflow. Later, depending on the evolution of the evaluators, we can consider a standardized way to define and query these values.
            

            # Now initialize all the agents
            await self.register_agents(workspace_manager=self.workspace_manager)
            
            # Store project root information in class variable
            self.project_root_info = self.workspace_manager.get_workspace_info()
            
            # Send back PROJECT_CREATED event to the runtime
            await self.web_socket_client.emit_event(BaseEvent(
                type=EventType.PROJECT_CREATED,
                source=EventSource.VHL_AGENT_BACKEND,
                payload={
                    "project_id": project_id,
                    "project_root": str(project_root),
                    "workspace_info": self.project_root_info
                }
            ))
            
            # Transition to IDLE state
            await self.transition_to(AOSMState.IDLE, f"Project {project_id} created successfully")

        # TODO : Outdated. Needs to be refactored to align with new project structure
        elif event.type == EventType.LOAD_PROJECT:
            payload = event.payload or {}
            project_id = payload.get("project_id")
            
            if not project_id:
                logger.error("[AOSM._handle_startup] Missing project_id in LOAD_PROJECT event")
                return

            logger.info(f"[AOSM._handle_startup] Loading project: {project_id}")
            try:
                project_root = self.workspace_manager.load_project(project_id)
                self.project_id = project_id
                self.project_semantic_db = self.workspace_manager.sqlite_db
                
                # Initialize all the agents
                await self.register_agents(workspace_manager=self.workspace_manager)
                
                # Setup HIL GATE routes for the agents

                # Store project root information in class variable
                self.project_root_info = self.workspace_manager.get_workspace_info()
                
                # Send back PROJECT_LOADED event to the runtime
                await self.web_socket_client.emit_event(BaseEvent(
                    type=EventType.PROJECT_LOADED,
                    source=EventSource.VHL_AGENT_BACKEND,
                    payload={
                        "project_id": project_id,
                        "project_root": str(project_root),
                        "workspace_info": self.project_root_info
                    }
                ))
                
                # Trigger sync for StableCircuit and Library (Agent to Runtime)
                try:
                    # Push StableCircuit from Agent to Runtime if it exists
                    stable_path = self.sync_client.get_resource_path(project_id, "StableCircuit")
                    if os.path.exists(stable_path):
                        await self.sync_client.handle_upload_request(SyncPayload(
                            sync_id=str(uuid.uuid4()),
                            project_id=project_id,
                            resource_type="StableCircuit",
                            data={"circuit_name": self.workspace_manager.circuit_name}
                        ))

                    # Push Library from Agent to Runtime if it exists
                    lib_path = self.sync_client.get_resource_path(project_id, "Library")
                    if os.path.exists(lib_path):
                        await self.sync_client.handle_upload_request(SyncPayload(
                            sync_id=str(uuid.uuid4()),
                            project_id=project_id,
                            resource_type="Library"
                        ))
                except Exception as e:
                    logger.warning(f"[AOSM._handle_startup] Auto-sync failed on project load (this is expected if project is empty): {e}")

                # Transition to IDLE state
                await self.transition_to(AOSMState.IDLE, f"Project {project_id} loaded successfully")
            except Exception as e:
                logger.error(f"[AOSM._handle_startup] Failed to load project {project_id}: {e}")
                await self.web_socket_client.emit_event(BaseEvent(
                    type=EventType.ERROR,
                    source=EventSource.VHL_AGENT_BACKEND,
                    payload={
                        "message": f"Failed to load project: {str(e)}"
                    }
                ))
        
        elif event.type == EventType.LIST_PROJECTS:
            logger.info("[AOSM._handle_startup] Listing projects...")
            projects = self.workspace_manager.list_projects()
            await self.web_socket_client.emit_projects_list(projects)

    async def register_agents(self, workspace_manager: WorkspaceManager):
        """Registers Archy and Librarian agents for each module in the project."""

        for module_name in workspace_manager.module_names:
            archy_agent_id = f"{module_name}.archy"
            librarian_agent_id = f"{module_name}.librarian"
            # ----Archy setup----
            archy_descriptor = AgentDescriptor(
                agent_id=archy_agent_id,
                name=f"{module_name} Archy",
                version="1.0",
                capabilities=["SCUD_GENERATION", "SCUD_REFINEMENT"],
                accepted_message_types=["BUILD_SCUD"]
            )
            register_agent_if_absent(descriptor=archy_descriptor,factory_func=ArchyURPAgent,name=archy_agent_id)
            
            # Step 2: Get archy agent from factory                                                                      
            factory = get_agent_factory(name=archy_agent_id)
            archy_agent = factory.factory_func(descriptor=factory.descriptor) 
            # Step 3: Prepare context and initialize Archy agent
            context = {
                "config": ArchyConfig(conversation_persistence=True),
                "workspace": self.workspace_manager,
                "sqlite_manager": self.project_semantic_db,
                "module_name": module_name
            }
            # Initial callback is a no-op; Supervisor will enforce egress routing
            archy_agent.initialize(context=context, emit_callback=lambda msg: None)

            logger.info("Starting Archy agent")
            # Step 4: Start Archy agent (enters WAITING state)
            await archy_agent.start()
            # Store the instantiated agent for subsequent state retrieval
            self.supervisor.attach_agent(archy_agent)

            archy_state = self.supervisor.get_agent_state(archy_agent_id)
            self.update_agent_status("archy", archy_state["status"])

            # ----Librarian setup----
            librarian_descriptor = AgentDescriptor(
                agent_id=librarian_agent_id,
                name=f"{module_name} Librarian",
                version="1.0",
                capabilities=["LIBRARY_COMPONENT_RESOLUTION"],
                accepted_message_types=["IMPORT_COMPONENTS", "FIND_COMPONENTS"]
            )
            register_agent_if_absent(descriptor=librarian_descriptor,factory_func=LibrarianURPAgent,name=librarian_agent_id)

            # # Step 2: Configure librarian agent
            factory = get_agent_factory(name=f"{module_name}.librarian")
            # # Step 3: Prepare context and initialize librarian agent
            context = {
                "config": LibrarianConfig(conversation_persistence=True),
                "workspace": self.workspace_manager,
                "sqlite_manager": self.project_semantic_db,
                "module_name": module_name,
                "sync_manager": self.sync_client
            }
            librarian = factory.factory_func(descriptor=factory.descriptor)             
            librarian.initialize(context=context, emit_callback=lambda msg: None)

            logger.info("Starting librarian agent")
            # Step 4: Start librarian agent (enters WAITING state)
            await librarian.start()
            # # Step 5: Register Gate with Supervisor wrapper for message routing
            self.supervisor.attach_agent(librarian)
            librarian_state = self.supervisor.get_agent_state(librarian_agent_id)
            self.update_agent_status("librarian", librarian_state["status"])

    
    async def _handle_idle(self, event: BaseEvent):
        """
        Default state of the system. Handles following events:
        - REFERENCE_UPLOADED: Transition to ARCHY to prepare assets for Archy.
        - HUMAN_INPUT: Transition to INTENT_CLASSIFY to classify user intent (modification vs synthesis)
        - SYNTHESIZE_CIRCUIT: User trigger to start circuit synthesis. Check if project is synthesizable and transition to TRIGGER_ANA if yes, otherwise emit error.
        """
        logger.info(f"[AOSM._handle_idle] In IDLE state...")

        # TODO: Outdated event type. Remove in next refactor
        if event.type == EventType.REFERENCE_UPLOADED:
            logger.info(f"[AOSM._handle_idle] Received REFERENCE_UPLOADED: {event.payload}")
            payload = json.loads(json.dumps(event.payload)) if event.payload else {}
            module_name = payload.get("reference_id", "default_module")
            # Start parallel workflow sequential execution task
            asyncio.create_task(self.run_workflow_1(module_name, payload))
        elif event.type == EventType.HUMAN_INPUT:
            await self.transition_to(AOSMState.INTENT_CLASSIFY, "User message received", payload=event.payload)
        
        elif event.type == EventType.SYNTHESIZE_CIRCUIT:
            info = self.workspace_manager.get_workspace_info()
            if info.get("is_synthesizable"):
                logger.info(f"[AOSM._handle_idle] Circuit is synthesizable. Transitioning to TRIGGER_ANA")
                self.current_message["circuit_id"] = info.get("circuit_name")
                await self.transition_to(AOSMState.TRIGGER_ANA, "User triggered synthesis")
            else:
                logger.warning("[AOSM._handle_idle] SYNTHESIZE_CIRCUIT received but project not synthesizable")
                await self.web_socket_client.emit_event(BaseEvent(
                    type=EventType.ERROR,
                    source=EventSource.VHL_AGENT_BACKEND,
                    payload={"message": "Project not ready for synthesis. Please upload schematic first."}
                ))
        
        elif event.type == EventType.MESSAGE_TO_AGENT:
            logger.info(f"[AOSM._handle_idle] Received MESSAGE_TO_AGENT: {event.payload}")
            # Expected structure of payload: {"target_agent": "agent_id", "message": MessageEnvelope}
            # Typical example for message from webui:
            # {"target_agent": "module1.librarian", "message": {"type": "RESOLVE_COMPONENTS", "payload": {"text": "Import all components related to power supply"}}}
            payload = event.payload or {}
            target_agent = payload.get("target_agent")
            message_data = payload.get("message", {})
            if target_agent and message_data:
                msg_payload = {"text": message_data}

                message = MessageEnvelope(type="MESSAGE_TO_AGENT", payload=msg_payload,sender="vhl_webui",receiver=target_agent)
                await self.supervisor.route_egress(message=message)
            else:
                logger.error("[AOSM._handle_idle] Invalid MESSAGE_TO_AGENT payload: missing target_agent or message")
                await self.web_socket_client.emit_event(BaseEvent(
                    type=EventType.ERROR,
                    source=EventSource.VHL_AGENT_BACKEND,
                    payload={"message": "Invalid MESSAGE_TO_AGENT payload: missing target_agent or message"}
                ))
    
    async def _handle_present_result(self, event: BaseEvent):
        logger.info(f"[AOSM._handle_present_result] Presenting results to user...")
        
        # Handle state transition which carries the ANA results from WAIT_FOR_ANA
        if event.type == EventType.STATE_TRANSITION:
            payload = event.payload or {}
            decision = payload.get("decision")
            iteration_dir = payload.get("iteration_dir")
            
            if not decision:
                logger.error("[AOSM._handle_present_result] No decision found in payload. Returning to IDLE.")
                await self.transition_to(AOSMState.IDLE, "No decision in result")
                return

            # if decision is ACCEPT copy current iteration directory to Stable directory
            if "ACCEPT" == decision:
                # Sync StableCircuit and EvaluationOutput
                if self.project_id:
                    try:
                        # 2. Trigger sync for evaluation output (Agent to Runtime)
                        # We need the iteration_id that was accepted.
                        # iteration_dir looks like .../iteration_<uuid>
                        iteration_id = Path(iteration_dir).name.replace("iteration_", "")
                        await self.sync_client.sync_circuit_json(self.project_id, iteration_id)
                        
                        logger.info(f"[AOSM._handle_present_result] StableCircuit and EvaluationOutput sync completed successfully")
                        
                    except Exception as e:
                        logger.warning(f"[AOSM._handle_present_result] StableCircuit sync failed or timed out: {e}")

            elif "REJECT" == decision:
                # Instruct workspace manager to move all iteration directories to archives/    
                logger.info("[AOSM._handle_present_result] Decision was REJECT. Archiving iterations.")
            
            # Move all iterations to archives
            self.workspace_manager.move_iterations_to_archives()
            
            # After presenting/handling, transition back to IDLE
            await self.transition_to(AOSMState.IDLE, f"Finished processing ANA result: {decision}")


    # --- Agent nodes begin--- #    
    # ANA
    @handle_errors(on_error="_aosm_error_transition")
    async def _handle_trigger_ana(self, event: BaseEvent):

        if event.type == EventType.STATE_TRANSITION:
            logger.info(f"[AOSM._handle_trigger_ana] Triggering ANA-D on state entry.")
            # Check, under which condition ANA is triggered. Circuit synthesis or circuit correction
            observations = self.current_message.get("observations", None)
            circuit_id = self.current_message.get("circuit_id")

            logger.info(f"[AOSM._handle_trigger_ana] Circuit name/id: {circuit_id}, observations: {observations}")
            
            if not observations:
                logger.info(f"[AOSM._handle_trigger_ana] Ana is in synthesis mode. Observations is None")
            
            
            # Initialize inbox queue for bidirectional communication
            self.ana_inbox = asyncio.Queue()
            
            self.active_ana_sm = ANADStateMachine(
                workspace_manager=self.workspace_manager,
                circuit_name=circuit_id,
                observations=observations,
                web_socket_client=self.web_socket_client,
                sync_client=self.sync_client,
                project_id=self.project_id,
                max_auto_fixes=5,
                parent_notify=self._parent_notify,
                inbox_queue=self.ana_inbox
            )
            # Run the ANA-D state machine in a background task to keep AOSM responsive
            self.update_agent_status("ana", AgentStatus.RUNNING)
            asyncio.create_task(self.active_ana_sm.run())
            await self.transition_to(AOSMState.WAIT_FOR_ANA, "ANA-D started")
        else:
            logger.info(f"[AOSM._handle_trigger_ana] Received event: {event.type}")
    
    # --- Agent nodes end--- #
    async def _handle_wait_for_ana(self, event: BaseEvent):

        if event.type == EventType.ANA_NOTIFY:
            # Handle notification from ANA (e.g., HIL_REQUEST)
            logger.info(f"[AOSM._handle_wait_for_ana] ANA notification: {event.payload}")
            
            ana_event = event.payload.get("reason")
            ana_task_id = event.payload.get("task_id")
            
            if ana_event == "HIL_REQUIRED":
                # Maybe notify UI that HIL is required
                await self.web_socket_client.emit_status_update(
                    status="waiting_for_input",
                    message=event.payload.get("message")
                )
            elif ana_event == "ERROR":
                await self.web_socket_client.emit_status_update(
                    status="ana_error",
                    message=event.payload.get("message")
                )
            elif ana_event == "EXIT":
                # Start the wait in the background so the main loop can continue 
                # to process incoming events (like DEV_SERVER_READY)
                ana_decision = event.payload.get("decision")
                asyncio.create_task(self._ana_deicsion_wait_and_transition(event, ana_task_id, ana_decision))

            else:
                raise ValueError(f"Unknown ANA notification reason: {ana_event}")

            
        elif event.type == EventType.HUMAN_INPUT:
            # Relaying human input to ANA's inbox
            if self.ana_inbox:
                logger.info(f"[AOSM._handle_wait_for_ana] Relaying human input to ANA: {event.payload}")
                content = event.payload.get("content", "")
                
                # Check for abort command
                if content.lower() == "abort":
                    await self.ana_inbox.put({"event": "abort", "data": None})
                else:
                    await self.ana_inbox.put({"event": "human_response", "data": content})
            else:
                logger.warning("[AOSM._handle_wait_for_ana] Received human input but ANA inbox is not initialized")
    
    async def _handle_cancel_pipeline(self, event: BaseEvent):
        logger.info("[AOSM._handle_cancel_pipeline] Cleaning up cancelled pipeline...")
        await self.transition_to(AOSMState.IDLE, "Cleanup complete")
    
    async def _handle_error_presented(self, event: BaseEvent):
        logger.info(f"[AOSM._handle_error_presented] In ERROR_PRESENTED state...")
        if event.type == EventType.HUMAN_INPUT:
            content = event.payload.get("content", "").lower()
            if "retry" in content:
                # Retry strategy would depend on previous state
                await self.transition_to(AOSMState.IDLE, "Retrying from IDLE")
            elif "abort" in content:
                await self.transition_to(AOSMState.IDLE, "User aborted after error")

    async def _handle_wait_for_user(self, event: BaseEvent):
        logger.info(f"[AOSM._handle_wait_for_user] In WAIT_FOR_USER state... ")
        if event.type == EventType.HUMAN_INPUT:
             await self.transition_to(AOSMState.TRIGGER_ANA, "Clarification received")

    # --- State Handlers --- END

    async def _ana_deicsion_wait_and_transition(self, event, task_id, decision):
        # This runs independently of the main loop
        if self.mcp_manager:
            logger.info(f"[AOSM._wait_and_transition] Applying VAP decision via MCP: {decision} for task {task_id}")
            try:
                await asyncio.to_thread(
                    self.mcp_manager.call_tool,
                    "apply_vap_decision",
                    {"task_id": task_id, "decision": decision}
                )
            except Exception as e:
                logger.error(f"[AOSM._wait_and_transition] Failed to apply VAP decision via MCP: {e}")
                # Fallback to websocket if MCP fails
                await self.web_socket_client.emit_evaluation_update(task_id=task_id, decision=decision)
        else:
            logger.info(f"[AOSM._wait_and_transition] No MCP manager available. Emitting evaluation update via WebSocket for task {task_id} with decision: {decision}")
            await self.web_socket_client.emit_evaluation_update(task_id=task_id, decision=decision)
        try:
            await self.web_socket_client.wait_for_event(
                EventType.DEV_SERVER_READY,
                timeout=60.0
            )
            await self.transition_to(AOSMState.PRESENT_RESULT, payload=event.payload)
        except Exception as e:
            logger.error(f"Background wait failed: {e}")
    async def _handle_close_project(self, event: BaseEvent):
        """Global handler for closing the current project."""
        logger.info(f"[AOSM._handle_close_project] Closing project {self.project_id}")
        
        # 1. Stop any active agent state machines
        if self.active_ana_sm:
            # We don't have a formal stop(), but we can clear the reference
            self.active_ana_sm = None
            self.ana_inbox = None
            self.update_agent_status("ana", AgentStatus.IDLE)
        
        self.update_agent_status("archy", AgentStatus.IDLE)
        self.update_agent_status("librarian", AgentStatus.IDLE)

        # 2. Reset Workspace Manager
        self.workspace_manager.close_project()
        
        # 3. Reset AOSM internal state
        self.project_id = None
        await self.supervisor.stop()
        self._init_supervisor()
        self.supervisor.start()
        self.project_root_info = None
        self.current_message = {
            "state_id": AOSMState.STARTUP,
            "observations": []
        }
        
        # 4. Notify Runtime/UI
        await self.web_socket_client.emit_event(BaseEvent(
            type=EventType.PROJECT_CLOSED,
            source=EventSource.VHL_AGENT_BACKEND,
            payload={}
        ))
        
        # 5. Transition to STARTUP
        await self.transition_to(AOSMState.STARTUP, "Project closed by user")

    async def run_workflow_1(self, module_name: str, payload: Dict[str, Any]):
        """
        Asynchronous sequential execution of Workflow 1.
        Calls handle_archy, handle_librarian, and handle_ana in sequence.
        """
        logger.info(f"[AOSM.run_workflow_1] Starting sequential Workflow 1 for module: {module_name}")
        try:
            # 1. Step 1: Archy
            await self.workflow_controller.handle_archy(module_name=module_name)
            archy_evaluator = ArchyEvaluator(self.project_semantic_db, module_name=module_name)
            archy_evaluator.evaluate() # This will commit an operation to the semantic db which can            
            
            # 2. Step 2: Librarian
            await self.workflow_controller.handle_librarian(module_name=module_name)
            librarian_evaluator = LibrarianEvaluator(self.project_semantic_db, module_name=module_name)
            librarian_evaluator.evaluate()
            # 3. Step 3: ANA-D
            await self.handle_ana()
            # send workflow 1 completion event to UI/runtime
            await self.web_socket_client.emit_event(BaseEvent(
                type=EventType.WORKFLOW_COMPLETED,
                source=EventSource.VHL_AGENT_BACKEND,
                payload={"workflow": "workflow_1", "module": module_name}
            ))
            logger.info(f"[AOSM.run_workflow_1] Sequential Workflow 1 completed successfully for module: {module_name}")
        except Exception as e:
            logger.error(f"[AOSM.run_workflow_1] Sequential Workflow 1 failed: {e}", exc_info=True)


    async def handle_ana(self) -> None:
        """
        Sequential member of Workflow 1: ANA-D.
        1. Initializes and runs the ANA-D state machine in a waitable manner.
        2. Evaluates the generated circuit code and applies decisions.
        """
        logger.info(f"[AOSM.handle_ana] Starting ANA-D processing...")
        logger.info(f"[AOSM.handle_ana] Finished ANA-D")

def main():
    # Test stub
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    
    ws_url = os.getenv("VHL_WS_URL", "ws://localhost:1080")
    workspace_arg = sys.argv[1] if len(sys.argv) > 1 else None
    workspace_path = Path(workspace_arg).expanduser().resolve() if workspace_arg else Path("vhl_workspace").resolve()
    aosm = AOSM(ws_url=ws_url, workspace_path=workspace_path)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(aosm.start())
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Interrupt received, stopping AOSM...")
        loop.run_until_complete(aosm.stop())
    finally:
        loop.close()

if __name__ == "__main__":
    main()
