import asyncio
import logging
import os
import boto3
from typing import Optional, Dict, Any
from pathlib import Path
from state_machine.states import AOSMState
from vhl_protocol.client.client import VHLWebSocketClient
from vhl_protocol.models import BaseEvent, EventType, EventSource, SyncPayload
from vhl_protocol.sync.client import SyncClient

import uuid
import base64
from ana_agent.state_machine import ANADStateMachine
from workspace.manager import WorkspaceManager
from archy_agent.main import orchestrate_archy
from librarian_agent.agent import LibrarianAgent

logger = logging.getLogger(__name__)

class AOSM:
    """
    Agentic Orchestration State Machine (AOSM)
    Always-on, time-aware control layer for VHL.
    """
    def __init__(self, ws_url: str = "ws://localhost:1080"):
        self.state = AOSMState.STARTUP
        self.ws_client = VHLWebSocketClient(
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
        self.sync_client = SyncClient(self.ws_client, "vhl_workspace")
        
        # Minio configuration (should ideally be from env)
        self.s3_client = boto3.client(
            's3',
            endpoint_url=os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
            aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            aws_secret_access_key=os.getenv("MINIO_SECRET_KEY", "supersecretpassword"),
            config=boto3.session.Config(signature_version='s3v4')
        )
        self.bucket_name = os.getenv("MINIO_BUCKET", "vhl")

    async def start(self):
        """Starts AOSM and the WebSocket client."""
        logger.info("Starting AOSM...")
        self.ws_client.add_subscriber(self._handle_ws_event)
        await self.ws_client.start()
        self._main_loop_task = asyncio.create_task(self._main_loop())

    async def stop(self):
        """Stops AOSM and the WebSocket client."""
        logger.info("Stopping AOSM...")
        self.ws_client.remove_subscriber(self._handle_ws_event)
        if self._main_loop_task:
            self._main_loop_task.cancel()
        await self.ws_client.stop()

    async def _handle_ws_event(self, event: BaseEvent):
        """Callback for received WebSocket events."""
        logger.debug(f"AOSM received event: {event.type}")
        await self.event_queue.put(event)

    async def _main_loop(self):
        """Main loop that processes events and drives transitions."""
        while True:
            event = await self.event_queue.get()
            try:
                await self.process_event(event)
            except Exception as e:
                logger.error(f"Error processing event: {e}", exc_info=True)
            finally:
                self.event_queue.task_done()

    async def process_event(self, event: BaseEvent):
        """
        Processes a single event and triggers state transitions.
        """
        logger.info(f"Processing event: {event.type} in state: {self.state}\n Payload: {event.payload}")
        
        # Dispatch to handler based on current state and event
        handler_name = f"_handle_{self.state.name.lower()}"
        handler = getattr(self, handler_name, None)
        
        if handler:
            await handler(event)
        else:
            logger.warning(f"No handler defined for state {self.state}")

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
        
        
        
        logger.info(f"[transition_to] Transitioning: {from_state.name} -> {next_state.name} (Reason: {reason})\nPayload: {payload}")
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
        logger.info(f"[AOSM] Received parent notification with payload: {payload}")
        await self.event_queue.put(BaseEvent(
            type=EventType.ANA_NOTIFY,
            source=EventSource.ANA,
            payload=payload
        ))

    # --- State Handlers ---

    async def _handle_startup(self, event: BaseEvent):
        logger.info(f"[AOSM] In STARTUP state... Event: {event}")
        if event.type == EventType.CREATE_PROJECT:
            payload = event.payload or {}
            project_name = payload.get("project_name", "untitled")
            # Generate project_id with <project_name>_<UID>
            project_id = f"{project_name}_{uuid.uuid4().hex[:8]}"
            self.project_id = project_id
            
            logger.info(f"[AOSM] Creating new project: {project_id}")
            project_root = self.workspace_manager.create_project(project_id)
            
            # Store project root information in class variable
            self.project_root_info = self.workspace_manager.get_workspace_info()
            
            # Send back PROJECT_CREATED event to the runtime
            await self.ws_client.emit_event(BaseEvent(
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
                logger.error("[AOSM] Missing project_id in LOAD_PROJECT event")
                return

            logger.info(f"[AOSM] Loading project: {project_id}")
            try:
                project_root = self.workspace_manager.load_project(project_id)
                
                # Store project root information in class variable
                self.project_root_info = self.workspace_manager.get_workspace_info()
                
                # Send back PROJECT_LOADED event to the runtime
                await self.ws_client.emit_event(BaseEvent(
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
                    # Check if StableCircuit exists before proposing
                    stable_path = self.sync_client.get_resource_path(project_id, "StableCircuit")
                    if os.path.exists(stable_path):
                         await self.sync_client.propose_upload(project_id, "StableCircuit")
                    
                    # Check if Library exists before proposing
                    lib_path = self.sync_client.get_resource_path(project_id, "Library")
                    if os.path.exists(lib_path):
                        await self.sync_client.propose_upload(project_id, "Library")
                except Exception as e:
                    logger.warning(f"[AOSM] Auto-sync failed on project load (this is expected if project is empty): {e}")

                # Transition to IDLE state
                await self.transition_to(AOSMState.IDLE, f"Project {project_id} loaded successfully")
            except Exception as e:
                logger.error(f"[AOSM] Failed to load project {project_id}: {e}")
                await self.ws_client.emit_event(BaseEvent(
                    type=EventType.ERROR,
                    source=EventSource.BACKEND,
                    payload={
                        "message": f"Failed to load project: {str(e)}"
                    }
                ))
        
        elif event.type == EventType.LIST_PROJECTS:
            logger.info("[AOSM] Listing projects...")
            projects = self.workspace_manager.list_projects()
            await self.ws_client.emit_projects_list(projects)

    async def _handle_idle(self, event: BaseEvent):
        logger.info(f"[AOSM] In IDLE state... Event: {event}")
        if event.type == EventType.REFERENCE_UPLOADED:
            await self.transition_to(AOSMState.BOOTSTRAP_PIPELINE, "New schematic uploaded", payload=event.payload)
        elif event.type == EventType.HUMAN_INPUT:
            await self.transition_to(AOSMState.INTENT_CLASSIFY, "User message received", payload=event.payload)

    async def _handle_bootstrap_pipeline(self, event: BaseEvent):
        # We trigger the bootstrap logic upon entering this state.
        if event.type == EventType.STATE_TRANSITION:
            scud_path,image_id = await self._run_bootstrap(event)
            self.current_message["circuit_id"] = image_id
            if scud_path:
                await self._run_librarian(scud_path)
                
                # Workflow 1.1: Sync lib/imports from VHL runtime to Agent backend
                if self.project_id:
                    sync_payload = SyncPayload(
                        sync_id=str(uuid.uuid4()),
                        project_id=self.project_id,
                        resource_type="Library"
                    )
                    await self.ws_client.emit(EventType.SYNC_TRIGGER, sync_payload)
                    # Wait for SYNC_COMPLETE
                    logger.info(f"[AOSM] Waiting for Library sync to complete...")
                    await self.ws_client.wait_for_event(
                        EventType.SYNC_COMPLETE,
                        filter_func=lambda e: e.payload.get("resource_type") == "Library"
                    )
                
                # Transition to TRIGGER_ANA to start the ANA-D state machine
                await self.transition_to(AOSMState.TRIGGER_ANA, "Bootstrap and Component resolution completed")

    
    async def _handle_present_result(self, event: BaseEvent):
        logger.info(f"[AOSM] Presenting results to user... Event: {event}")
        if event.type == EventType.VAP_DECISION:
            decision = event.payload.get("decision")
            iteration_dir = event.payload.get("iteration_dir") 
            # if decision is ACCEPT copy current iteration directory to Stable directory
            if "ACCEPT" == decision:
                # Instruct workspace manager to move content from iteration_dir/ to Stable/ directory
                self.workspace_manager.populate_stable(iteration_dir)
            elif "REJECT" == decision:
                # Instruct workspace manager to move all iteration directories to archives/    
                self.workspace_manager.move_iterations_to_archives()
            else:
                raise ValueError(f"Unexpected decision: {decision}")
 
    async def _handle_intent_classify(self, event: BaseEvent):
        # In a real scenario, an agent would classify the intent here.
        # For the wireframe, we assume valid modification request.
        logger.info(f"[AOSM] Classifying intent...\n event: {event}")
        # Add user message to the current message observations
        self.current_message["observations"].append(event.payload.get("content", "No message provided"))
        logger.info(f"[AOSM] Current message: {self.current_message}")
        
        # Transition to PREPARE_ANA_RUN
        await self.transition_to(AOSMState.PREPARE_ANA_RUN, "Intent classified as modification", payload=event.payload)
        
        # Request workspace sync for StableCircuit and Library (Runtime to Agent)
        if self.project_id:
            logger.info("[AOSM] Triggering sync for StableCircuit and Library")
            await self.ws_client.emit(EventType.SYNC_TRIGGER, SyncPayload(
                sync_id=str(uuid.uuid4()),
                project_id=self.project_id,
                resource_type="StableCircuit"
            ))
            # Library sync will be handled in PREPARE_ANA_RUN or sequence

    async def _handle_prepare_ana_run(self, event: BaseEvent):
        logger.info("[AOSM] Preparing ANA run...")
        
        if event.type == EventType.SYNC_COMPLETE:
            resource_type = event.payload.get("resource_type")
            logger.info(f"[AOSM] Sync complete for {resource_type}")
            
            if resource_type == "StableCircuit":
                # Now sync Library
                await self.ws_client.emit(EventType.SYNC_TRIGGER, SyncPayload(
                    sync_id=str(uuid.uuid4()),
                    project_id=self.project_id,
                    resource_type="Library"
                ))
            elif resource_type == "Library":
                # Both synced, find the circuit file in Stable to set as circuit_code_path
                stable_dir = self.workspace_manager.project_root / "Stable"
                tsx_files = list(stable_dir.glob("*.tsx"))
                if tsx_files:
                    self.current_message["circuit_code_path"] = str(tsx_files[0])
                    await self.transition_to(AOSMState.TRIGGER_ANA, "Workspace synced and ready")
                else:
                    logger.error("[AOSM] No .tsx file found in Stable after sync")
                    await self.transition_to(AOSMState.ERROR_PRESENTED, "Missing circuit code in Stable")
        
        elif event.type == EventType.SYNC_ERROR:
            logger.error(f"[AOSM] Sync failed: {event.payload}")
            await self.transition_to(AOSMState.ERROR_PRESENTED, f"Sync failed: {event.payload.get('reason')}")


    async def _handle_trigger_ana(self, event: BaseEvent):
        if event.type == EventType.STATE_TRANSITION:
            logger.info(f"[AOSM] Triggering ANA-D on state entry.")
            # Create ANA-D state machine instance with the circuit code path 
            circuit_code_path = self.current_message.get("circuit_code_path",None)
            observations = self.current_message.get("observations", None)
            logger.info(f"[AOSM-TRIGGER ANA]: Circuit code path: {circuit_code_path}, observations: {observations}")

            project_root = self.workspace_manager.project_root
            circuit_id = self.current_message.get("circuit_id")

            if not project_root:
                logger.error("[AOSM-TRIGGER_ANA] Project root not set in workspace manager")
                await self.transition_to(AOSMState.ERROR_PRESENTED, "Bootstrap failed: Project not initialized")
                return
            
            # Initialize inbox queue for bidirectional communication
            self.ana_inbox = asyncio.Queue()
            
            self.active_ana_sm = ANADStateMachine(
                workspace_manager=self.workspace_manager,
                circuit_name=circuit_id,
                observations=observations,
                ws_client=self.ws_client,
                sync_client=self.sync_client,
                project_id=self.project_id,
                workspace=self.workspace_manager.project_root,
                parent_notify=self._parent_notify,
                inbox_queue=self.ana_inbox
            )
            # Run the ANA-D state machine in a background task to keep AOSM responsive
            asyncio.create_task(self.active_ana_sm.run())
        else:
            raise ValueError(f"Unexpected event type in TRIGGER_ANA state: {event.type}")
        
        
        await self.transition_to(AOSMState.WAIT_FOR_ANA, "ANA-D started")

    async def _handle_wait_for_ana(self, event: BaseEvent):

        if event.type == EventType.ANA_NOTIFY:
            # Handle notification from ANA (e.g., HIL_REQUEST)
            logger.info(f"[AOSM-WAIT_FOR_ANA] ANA notification: {event.payload}")
            
            ana_event = event.payload.get("reason")
            ana_task_id = event.payload.get("task_id")
            
            if ana_event == "HIL_REQUIRED":
                # Maybe notify UI that HIL is required
                await self.ws_client.emit_status_update(
                    status="waiting_for_input",
                    message=event.payload.get("message")
                )
            elif ana_event == "ERROR":
                await self.ws_client.emit_status_update(
                    status="ana_error",
                    message=event.payload.get("message")
                )
            elif ana_event == "EXIT":
                ana_decision = event.payload.get("decision")
                self.transition_to(AOSMState.PRESENT_RESULT)
                await self.ws_client.emit_evaluation_update(task_id=ana_task_id, decision=ana_decision)

            else:
                raise ValueError(f"Unknown ANA notification reason: {ana_event}")
            
        elif event.type == EventType.HUMAN_INPUT:
            # Relaying human input to ANA's inbox
            if self.ana_inbox:
                logger.info(f"[AOSM-WAIT_FOR_ANA] Relaying human input to ANA: {event.payload}")
                content = event.payload.get("content", "")
                
                # Check for abort command
                if content.lower() == "abort":
                    await self.ana_inbox.put({"event": "abort", "data": None})
                else:
                    await self.ana_inbox.put({"event": "human_response", "data": content})
            else:
                logger.warning("[AOSM-WAIT_FOR_ANA] Received human input but ANA inbox is not initialized")

    async def _handle_cancel_pipeline(self, event: BaseEvent):
        logger.info("[AOSM] Cleaning up cancelled pipeline...")
        await self.transition_to(AOSMState.IDLE, "Cleanup complete")

    async def _handle_error_presented(self, event: BaseEvent):
        if event.type == EventType.HUMAN_INPUT:
            content = event.payload.get("content", "").lower()
            if "retry" in content:
                # Retry strategy would depend on previous state
                await self.transition_to(AOSMState.IDLE, "Retrying from IDLE")
            elif "abort" in content:
                await self.transition_to(AOSMState.IDLE, "User aborted after error")

    async def _handle_wait_for_user(self, event: BaseEvent):
        if event.type == EventType.HUMAN_INPUT:
             await self.transition_to(AOSMState.INTENT_CLASSIFY, "Clarification received")

    # --- High-level Orchestration Logic ---

    async def _run_bootstrap(self, event: BaseEvent):
        """Logic for BOOTSTRAP_PIPELINE."""
        logger.info("Executing Bootstrap Pipeline...")
        
        payload = event.payload or {}
        filename = payload.get("filename", "unnamed.png")
        base64_img = payload.get("base64")
        
        if not base64_img:
            logger.error(f"[AOSM-BOOTSTRAP] Missing base64 in payload: {payload}")
            await self.transition_to(AOSMState.ERROR_PRESENTED, "Bootstrap failed: Missing image data")
            return

        # Generate image_id: <file_name_without_extension>_<5 digit uid>
        stem = Path(filename).stem
        uid = uuid.uuid4().hex[:5]
        image_id = f"{self.workspace_manager.project_id}_{stem}_{uid}"

        project_root = self.workspace_manager.project_root
        if not project_root:
            logger.error("[AOSM-BOOTSTRAP] Project root not set in workspace manager")
            await self.transition_to(AOSMState.ERROR_PRESENTED, "Bootstrap failed: Project not initialized")
            return


        # 1. Save image to project root under UserArtefacts/
        user_artefacts_dir = project_root / "UserArtefacts"
        user_artefacts_dir.mkdir(exist_ok=True)
        image_path = user_artefacts_dir / f"{image_id}.png"
        
        try:
            logger.info(f"[AOSM-BOOTSTRAP] Saving reference image to {image_path}")
            with open(image_path, "wb") as f:
                f.write(base64.b64decode(base64_img))
        except Exception as e:
            logger.error(f"[AOSM-BOOTSTRAP] Failed to save image: {e}")
            await self.transition_to(AOSMState.ERROR_PRESENTED, f"Bootstrap failed: Image save error: {str(e)}")
            return

        # 2. Trigger Archy
        logger.info(f"[AOSM-BOOTSTRAP] Triggering Archy orchestration for image: {image_id}")
        try:
            # orchestrate_archy is CPU intensive/blocking, run in thread
            scud_path = await asyncio.to_thread(
                orchestrate_archy, 
                workspace_path=project_root, 
                image_id=image_id
            )
            logger.info(f"[AOSM-BOOTSTRAP] Archy completed successfully. SCUD generated at: {scud_path}")
            
            # Update current message with the SCUD path for ANA trigger
            
            return scud_path,image_id
        except Exception as e:
            logger.error(f"[AOSM-BOOTSTRAP] Archy orchestration failed: {e}")
            await self.transition_to(AOSMState.ERROR_PRESENTED, f"Archy failed: {str(e)}")
            return None

    async def _run_librarian(self, scud_path: Path):
        """Logic for triggering Librarian Agent to resolve components."""
        logger.info(f"[AOSM-BOOTSTRAP] Triggering Librarian Agent for SCUD: {scud_path}")
        try:
            # LibrarianAgent defaults to http://localhost:8080/mcp
            librarian = LibrarianAgent()
            # process_scud involves network/LLM, run in thread
            await asyncio.to_thread(librarian.process_scud, str(scud_path))
            logger.info(f"[AOSM-BOOTSTRAP] Librarian Agent completed successfully")
        except Exception as e:
            logger.error(f"[AOSM-BOOTSTRAP] Librarian Agent failed: {e}")
            # We proceed even if Librarian fails, but log the error

def main():
    # Test stub
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    aosm = AOSM()
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
