import asyncio
import logging
import os
import sys
from typing import Optional, Dict, Any
from pathlib import Path
from state_machine.states import AOSMState
from vhl_protocol.client.client import VHLWebSocketClient
from vhl_protocol.models import BaseEvent, EventType, EventSource, SyncPayload, AgentStatus
from vhl_protocol.sync.client import SyncClient

import uuid
import base64
from ana_agent.state_machine.mcp_manager import MCPManager
from ana_agent.state_machine import ANADStateMachine
from workspace.manager import WorkspaceManager
from archy_agent.main import orchestrate_archy, _archy_build_scud_stub
from librarian_agent.agent import LibrarianAgent
from librarian_agent.stub import process_scud_stub
# from component_placement_agent.state_machine.cpa_sm import CPASm

logger = logging.getLogger(__name__)

class AOSM:
    """
    Agentic Orchestration State Machine (AOSM)
    Always-on, time-aware control layer for VHL.
    """
    def __init__(self, ws_url: str = "ws://localhost:1080"):
        logger.info(f"[AOSM.__init__] Initializing AOSM with ws_url: {ws_url}")
        self.state = AOSMState.STARTUP
        self.web_socket_client = VHLWebSocketClient(
            url=ws_url,
            role="agent"
        )
        self.current_message: Dict[str, Any] = {
            "state_id": self.state,
            "observations": []
        }
        self.event_queue = asyncio.Queue()
        self.workspace_manager = WorkspaceManager("vhl_workspace")
        self.project_root_info: Optional[Dict[str, Any]] = None
        self.active_ana_sm: Optional[ANADStateMachine] = None
        self.ana_inbox: Optional[asyncio.Queue] = None
        self._main_loop_task: Optional[asyncio.Task] = None
        self.project_id: Optional[str] = None
        self.sync_client = SyncClient(self.web_socket_client, self.workspace_manager)
        mcp_default = "http://localhost:8081/mcp/vap" if "K_SERVICE" in os.environ else "http://host.docker.internal:8081/mcp/vap"
        mcp_endpoint = os.getenv("MCP_ENDPOINT", mcp_default)
        lib_default = "http://localhost:8082/sse" if "K_SERVICE" in os.environ else "http://host.docker.internal:8082/sse"
        self.librarian_mcp_url = os.getenv("LIBRARIAN_MCP_URL", lib_default)
        self.mcp_manager = MCPManager(endpoint=mcp_endpoint)
        # self.mcp_manager = None
        self.agent_state = {
            "archy": AgentStatus.IDLE,
            "librarian": AgentStatus.IDLE,
            "ana": AgentStatus.IDLE,
            "aosm": AgentStatus.RUNNING
        }
        
        # Storage client is managed by SyncClient

    async def start(self):
        """Starts AOSM and the WebSocket client."""
        logger.info("[AOSM.start] Starting AOSM...")
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
        await self.web_socket_client.emit_agent_state(
            archy=self.agent_state["archy"],
            librarian=self.agent_state["librarian"],
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
        self.web_socket_client.remove_subscriber(self._handle_ws_event)
        if self._main_loop_task:
            self._main_loop_task.cancel()
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

        if event.type == EventType.TRIGGER_CPA_AGENT:
            if self.state == AOSMState.IDLE:
                logger.info(f"👉 [AOSM] Handling TRIGGER_CPA_AGENT in IDLE")
                await self.transition_to(AOSMState.TRIGGER_CPA, "Direct user trigger for CPA")
                return
            else:
                logger.warning(f"⚠️ [AOSM] TRIGGER_CPA_AGENT received but AOSM is in {self.state} (not IDLE)")

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
        
        if payload:
            payload.update({
                    "from": from_state.name,
                    "to": next_state.name,
                    "reason": reason
                })
        
        
        # Notify the UI/Protocol layer
        # await self.ws_client.emit_state_transition(
        #     from_state=from_state.name,
        #     to_state=next_state.name,
        #     reason=reason
        # )
        
        
        
        logger.info(f"[AOSM.transition_to] Transitioning: {from_state.name} -> {next_state.name} (Reason: {reason})\nPayload: {payload}")
        # Push an internal transition event to the queue to trigger any "on_enter" logic
        # or immediate next steps in the state machine loop.
        await self.event_queue.put(BaseEvent(
            type=EventType.STATE_TRANSITION,
            source=EventSource.BACKEND,
            payload=payload
        ))
        

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

    # --- State Handlers ---

    async def _handle_startup(self, event: BaseEvent):
        logger.info(f"[AOSM._handle_startup] In STARTUP state...")
        if event.type == EventType.CREATE_PROJECT:
            payload = event.payload or {}
            project_name = payload.get("project_name", "untitled")
            # Generate project_id with <project_name>_<UID>
            project_id = f"{project_name}_{uuid.uuid4().hex[:8]}"
            self.project_id = project_id
            
            logger.info(f"[AOSM._handle_startup] Creating new project: {project_id}")
            project_root = self.workspace_manager.create_project(project_id)
            
            # Store project root information in class variable
            self.project_root_info = self.workspace_manager.get_workspace_info()
            
            # Send back PROJECT_CREATED event to the runtime
            await self.web_socket_client.emit_event(BaseEvent(
                type=EventType.PROJECT_CREATED,
                source=EventSource.BACKEND,
                payload={
                    "project_id": project_id,
                    "project_root": str(project_root),
                    "workspace_info": self.project_root_info
                }
            ))
            
            # Transition to IDLE state
            await self.transition_to(AOSMState.IDLE, f"Project {project_id} created successfully")

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
                
                # Store project root information in class variable
                self.project_root_info = self.workspace_manager.get_workspace_info()
                
                # Send back PROJECT_LOADED event to the runtime
                await self.web_socket_client.emit_event(BaseEvent(
                    type=EventType.PROJECT_LOADED,
                    source=EventSource.BACKEND,
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
                    source=EventSource.BACKEND,
                    payload={
                        "message": f"Failed to load project: {str(e)}"
                    }
                ))
        
        elif event.type == EventType.LIST_PROJECTS:
            logger.info("[AOSM._handle_startup] Listing projects...")
            projects = self.workspace_manager.list_projects()
            await self.web_socket_client.emit_projects_list(projects)

    async def _handle_idle(self, event: BaseEvent):
        logger.info(f"[AOSM._handle_idle] In IDLE state...")
        if event.type == EventType.REFERENCE_UPLOADED:
            await self.transition_to(AOSMState.BOOTSTRAP_PIPELINE, "New schematic uploaded", payload=event.payload)
        elif event.type == EventType.HUMAN_INPUT:
            await self.transition_to(AOSMState.INTENT_CLASSIFY, "User message received", payload=event.payload)
        
        elif event.type == EventType.TRIGGER_CPA_AGENT:
             await self.transition_to(AOSMState.TRIGGER_CPA, "User triggered CPA")
        
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
                    source=EventSource.BACKEND,
                    payload={"message": "Project not ready for synthesis. Please upload schematic first."}
                ))
        
    async def _handle_bootstrap_pipeline(self, event: BaseEvent):
        logger.info(f"[AOSM._handle_idle] In BOOTSTRAP_PIPELINE state...")
        # We trigger the bootstrap logic upon entering this state.
        if event.type == EventType.STATE_TRANSITION:
            scud_path,image_id = await self._run_bootstrap(event)
            self.current_message["circuit_id"] = image_id
            if scud_path:
                self.current_message["scud_path"] = str(scud_path)
                await self._run_librarian(scud_path)
                
                # Workflow 1.1: Sync lib/imports from VHL runtime to Agent backend
                if self.project_id:
                    # Sync Library using centralized client
                    await self.sync_client.sync_library(self.project_id)
                    logger.info(f"[AOSM._handle_bootstrap_pipeline] Library sync completed. Transitioning to WAIT_FOR_LIBRARIAN_HIL")

                    # Transition to WAIT_FOR_LIBRARIAN_HIL to let human review librarian results
                    await self.transition_to(AOSMState.WAIT_FOR_LIBRARIAN_HIL, "Bootstrap and Component resolution completed. Waiting for HIL review.", payload={"scud_path": str(scud_path)})
                else:
                    raise ValueError(f"Project id is null : {self.project_id}")
            else:
                raise ValueError(f"scud_path is null. {scud_path}")
    
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

    async def _handle_intent_classify(self, event: BaseEvent):
        # In a real scenario, an agent would classify the intent here.
        # For the wireframe, we assume valid modification request.
        logger.info(f"[AOSM._handle_intent_classify] Classifying intent...")
        # Add user message to the current message observations
        self.current_message["observations"].append(event.payload.get("content", "No message provided"))
        logger.info(f"[AOSM._handle_intent_classify] Current message: {self.current_message}")
        
        # Transition to TRIGGER_ANA
        await self.transition_to(AOSMState.TRIGGER_ANA, "Intent classified as modification", payload=event.payload)
        
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
                asyncio.create_task(self._wait_and_transition(event, ana_task_id, ana_decision))

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
    
    async def _wait_and_transition(self, event, task_id, decision):
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
                    await self.web_socket_client.emit_evaluation_update(task_id=task_id, decision=decision)
                try:
                    await self.web_socket_client.wait_for_event(
                        EventType.DEV_SERVER_READY,
                        timeout=60.0
                    )
                    await self.transition_to(AOSMState.PRESENT_RESULT, payload=event.payload)
                except Exception as e:
                    logger.error(f"Background wait failed: {e}")
            
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
             await self.transition_to(AOSMState.INTENT_CLASSIFY, "Clarification received")

    async def _handle_wait_for_librarian_hil(self, event: BaseEvent):
        logger.info(f"[AOSM._handle_wait_for_librarian_hil] In WAIT_FOR_LIBRARIAN_HIL state...")
        
        if event.type == EventType.STATE_TRANSITION:
            # On entering state, notify user for review
            scud_path = event.payload.get("scud_path")
            scud_content = ""
            if scud_path and os.path.exists(scud_path):
                with open(scud_path, "r") as f:
                    scud_content = f.read()
            
            await self.web_socket_client.emit_event(BaseEvent(
                type=EventType.HIL_REQUEST,
                source=EventSource.BACKEND,
                payload={
                    "reason": "LIBRARIAN_REVIEW",
                    "message": "Librarian has finished component resolution. Please review the updated SCUD.",
                    "scud_content": scud_content
                }
            ))
            
        elif event.type == EventType.HUMAN_INPUT:
            payload = event.payload or {}
            action = payload.get("action")
            
            if action == "continue":
                instructions = payload.get("instructions", "")
                if instructions:
                    self.current_message.setdefault("observations", []).append(f"User instructions from Librarian HIL review: {instructions}")
                logger.info("[AOSM._handle_wait_for_librarian_hil] User chose CONTINUE. Transitioning to TRIGGER_ANA")
                await self.transition_to(AOSMState.TRIGGER_ANA, "User accepted librarian results")
                
            elif action == "retry":
                instructions = payload.get("instructions", "")
                logger.info(f"[AOSM._handle_wait_for_librarian_hil] User chose RETRY with instructions: {instructions}")
                
                # Re-run librarian
                scud_path = self.current_message.get("scud_path") # We should store this
                if not scud_path:
                    # Try to find it again? Or store it in transition
                    # For now, let's assume we can get it from workspace manager
                    project_root = self.workspace_manager.project_root
                    image_id = self.current_message.get("circuit_id")
                    scud_path = project_root / f"{image_id}.scud"

                await self._run_librarian(scud_path, instructions=instructions)
                
                # Wait for sync again?
                if self.project_id:
                     # Sync Library using centralized client
                     await self.sync_client.sync_library(self.project_id)
                
                # Re-emit HIL_REQUEST with updated content
                scud_content = ""
                if os.path.exists(scud_path):
                    with open(scud_path, "r") as f:
                        scud_content = f.read()
                
                await self.web_socket_client.emit_event(BaseEvent(
                    type=EventType.HIL_REQUEST,
                    source=EventSource.BACKEND,
                    payload={
                        "reason": "LIBRARIAN_REVIEW",
                        "message": "Librarian has finished retrying component resolution. Please review the updated SCUD.",
                        "scud_content": scud_content
                    }
                ))

    async def _handle_trigger_cpa(self, event: BaseEvent):
        logger.info(f"[AOSM._handle_trigger_cpa] In TRIGGER_CPA state...")
        if event.type == EventType.STATE_TRANSITION:
            logger.info(f"[AOSM._handle_trigger_cpa] Triggering CPA State Machine.")
            
            project_id = self.project_id
            circuit_id = self.current_message.get("circuit_id") or (self.project_root_info.get("circuit_name") if self.project_root_info else None)
            
            if not circuit_id:
                logger.error("[AOSM._handle_trigger_cpa] No circuit_id found. Cannot trigger CPA.")
                await self.transition_to(AOSMState.IDLE, "CPA trigger failed: No circuit ID")
                return

            # cpa_sm = CPASm(
            #     workspace_manager=self.workspace_manager,
            #     circuit_name=circuit_id,
            #     web_socket_client=self.web_socket_client,
            #     sync_client=self.sync_client,
            #     project_id=project_id,
            #     parent_notify=self._parent_notify
            # )
            
            # Update status to running
            # self.update_agent_status("ana", AgentStatus.RUNNING) # Maybe use a 'cpa' status?
            # For now AOSM status is RUNNING
            logger.warning("[AOSM._handle_trigger_cpa] CPA is not implemented yet. This is a placeholder for where CPA would be triggered.")
            # asyncio.create_task(cpa_sm.run())
            await self.transition_to(AOSMState.WAIT_FOR_CPA, "CPA-SM started")

    async def _handle_wait_for_cpa(self, event: BaseEvent):
        logger.info(f"[AOSM._handle_wait_for_cpa] In WAIT_FOR_CPA state...")
        if event.type == EventType.ANA_NOTIFY: # CPASm uses the same notification pattern
            logger.info(f"[AOSM._handle_wait_for_cpa] Notification from CPA: {event.payload}")
            
            reason = event.payload.get("reason")
            if reason == "EXIT":
                decision = event.payload.get("decision", "REJECT")
                # For CPA, if it's SUCCESS, we might want to PRESENT_RESULT
                # If it's ERROR, we might want to IDLE or ERROR_PRESENTED
                await self.transition_to(AOSMState.PRESENT_RESULT, payload=event.payload)
            elif reason == "ERROR":
                 await self.transition_to(AOSMState.ERROR_PRESENTED, payload=event.payload)

    # --- High-level Orchestration Logic ---

    async def _run_bootstrap(self, event: BaseEvent):
        """Logic for BOOTSTRAP_PIPELINE."""
        logger.info("[AOSM._run_bootstrap] Executing Bootstrap Pipeline...")
        
        payload = event.payload or {}
        filename = payload.get("filename", "unnamed.png")
        base64_img = payload.get("base64")
        
        if not base64_img:
            logger.error(f"[AOSM._run_bootstrap] Missing base64 in payload: {payload}")
            await self.transition_to(AOSMState.ERROR_PRESENTED, "Bootstrap failed: Missing image data")
            return
        
        # Generate image_id: <file_name_without_extension>_<5 digit uid>
        stem = Path(filename).stem
        uid = uuid.uuid4().hex[:5]
        image_id = f"{self.workspace_manager.project_id}_{stem}_{uid}"

        project_root = self.workspace_manager.project_root
        if not project_root:
            logger.error("[AOSM._run_bootstrap] Project root not set in workspace manager")
            await self.transition_to(AOSMState.ERROR_PRESENTED, "Bootstrap failed: Project not initialized")
            return


        # 1. Save image to project root under UserArtefacts/
        user_artefacts_dir = project_root / "UserArtefacts"
        user_artefacts_dir.mkdir(exist_ok=True)
        image_path = user_artefacts_dir / f"{image_id}.png"
        
        try:
            logger.info(f"[AOSM._run_bootstrap] Saving reference image to {image_path}")
            with open(image_path, "wb") as f:
                f.write(base64.b64decode(base64_img))
        except Exception as e:
            logger.error(f"[AOSM._run_bootstrap] Failed to save image: {e}")
            await self.transition_to(AOSMState.ERROR_PRESENTED, f"Bootstrap failed: Image save error: {str(e)}")
            return

        # 2. Trigger Archy
        logger.info(f"[AOSM._run_bootstrap] Triggering Archy orchestration for image: {image_id}")
        if os.environ.get("STUBS") == "true":
            logger.info("[AOSM._run_bootstrap] Running Archy in STUB mode")
            self.update_agent_status("archy", AgentStatus.RUNNING)
            scud_path = _archy_build_scud_stub(workspace_path=project_root, image_id=image_id)
            self.update_agent_status("archy", AgentStatus.IDLE)
        else:    
            try:
                # orchestrate_archy is CPU intensive/blocking, run in thread
                self.update_agent_status("archy", AgentStatus.RUNNING)
                scud_path = await asyncio.to_thread(
                    orchestrate_archy, 
                    workspace_path=project_root, 
                    image_id=image_id
                )
                self.update_agent_status("archy", AgentStatus.IDLE)
                logger.info(f"[AOSM._run_bootstrap] Archy completed successfully. SCUD generated at: {scud_path}")    
                # Update current message with the SCUD path for ANA trigger
                
            except Exception as e:
                self.update_agent_status("archy", AgentStatus.IDLE)
                logger.error(f"[AOSM._run_bootstrap] Archy orchestration failed: {e}")
                await self.transition_to(AOSMState.ERROR_PRESENTED, f"Archy failed: {str(e)}")
                return None
            
        return scud_path,image_id

    async def _run_librarian(self, scud_path: Path, instructions: str = None):
        """Logic for triggering Librarian Agent to resolve components."""
        logger.info(f"[AOSM._run_librarian] Triggering Librarian Agent for SCUD: {scud_path} (Instructions: {instructions})")
        try:
            if os.environ.get("STUBS") == "true":
                logger.info("[AOSM._run_librarian] Running Librarian in STUB mode")
                self.update_agent_status("librarian", AgentStatus.RUNNING)
                
                # Stub mode: Load deterministic component list from JSON
                components = None
                try:
                    mock_json_path =  Path("tests" / "Mock" / "components.json")
                    if mock_json_path.exists():
                        import json
                        with open(mock_json_path, "r") as f:
                            components = json.load(f)
                            logger.info(f"[AOSM._run_librarian] Stub mode: Loaded components from {mock_json_path}: {components}")
                    else:
                        logger.warning(f"[AOSM._run_librarian] Mock JSON not found at: {mock_json_path}")
                except Exception as e:
                    logger.warning(f"[AOSM._run_librarian] Failed to load mock components: {e}")

                await asyncio.to_thread(process_scud_stub, str(scud_path), components=components, instructions=instructions)
                self.update_agent_status("librarian", AgentStatus.IDLE)
            else:
                librarian = LibrarianAgent(mcp_url=self.librarian_mcp_url, working_dir=self.workspace_manager.project_root)
                # process_scud involves network/LLM, run in thread
                self.update_agent_status("librarian", AgentStatus.RUNNING)
                await asyncio.to_thread(librarian.process_scud, str(scud_path), instructions=instructions)
                self.update_agent_status("librarian", AgentStatus.IDLE)
            logger.info(f"[AOSM._run_librarian] Librarian Agent completed successfully")
        except Exception as e:
            self.update_agent_status("librarian", AgentStatus.IDLE)
            logger.error(f"[AOSM._run_librarian] Librarian Agent failed: {e}", exc_info=True)
            # We proceed even if Librarian fails, but log the error
            pass

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
        self.project_root_info = None
        self.current_message = {
            "state_id": AOSMState.STARTUP,
            "observations": []
        }
        
        # 4. Notify Runtime/UI
        await self.web_socket_client.emit_event(BaseEvent(
            type=EventType.PROJECT_CLOSED,
            source=EventSource.BACKEND,
            payload={}
        ))
        
        # 5. Transition to STARTUP
        await self.transition_to(AOSMState.STARTUP, "Project closed by user")

def main():
    # Test stub
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    
    ws_url = os.getenv("VHL_WS_URL", "ws://localhost:1080")
    aosm = AOSM(ws_url=ws_url)
    
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
