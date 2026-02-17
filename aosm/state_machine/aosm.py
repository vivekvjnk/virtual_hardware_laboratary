import asyncio
import logging
import json
import os
import zipfile
import tempfile
import shutil
import boto3
from typing import Optional, Dict, Any, List
from pathlib import Path
from state_machine.states import AOSMState
from vhl_protocol.client.client import VHLWebSocketClient
from vhl_protocol.models import BaseEvent, EventType, EventSource

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
        self.workspace_manager = WorkspaceManager("ana_workspace")
        self.project_root_info: Optional[Dict[str, Any]] = None
        self.active_ana_sm: Optional[ANADStateMachine] = None
        self.ana_inbox: Optional[asyncio.Queue] = None
        self._main_loop_task: Optional[asyncio.Task] = None
        
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
        """Transitions to a new state and emits a state transition event."""
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

    async def _handle_idle(self, event: BaseEvent):
        logger.info(f"[AOSM] In IDLE state... Event: {event}")
        if event.type == EventType.REFERENCE_UPLOADED:
            await self.transition_to(AOSMState.BOOTSTRAP_PIPELINE, "New schematic uploaded", payload=event.payload)
        elif event.type == EventType.HUMAN_INPUT:
            await self.transition_to(AOSMState.INTENT_CLASSIFY, "User message received", payload=event.payload)

    async def _handle_bootstrap_pipeline(self, event: BaseEvent):
        # We trigger the bootstrap logic upon entering this state.
        if event.type == EventType.STATE_TRANSITION:
            scud_path = await self._run_bootstrap(event)
            if scud_path:
                await self._run_librarian(scud_path)
                # Transition to TRIGGER_ANA to start the ANA-D state machine
                await self.transition_to(AOSMState.TRIGGER_ANA, "Bootstrap and Component resolution completed")

    
    async def _handle_present_result(self, event: BaseEvent):
        logger.info(f"[AOSM] Presenting results to user... Event: {event}")
        if event.type == EventType.HUMAN_INPUT:
            await self.transition_to(AOSMState.INTENT_CLASSIFY, "User modification requested")
        elif event.type == EventType.REFERENCE_UPLOADED:
            await self.transition_to(AOSMState.BOOTSTRAP_PIPELINE, "New upload during review")
        # elif event.type == EventType.STATE_TRANSITION:
        #     # Read the evaluation status from event payload. If it is pass, 
    async def _handle_intent_classify(self, event: BaseEvent):
        # In a real scenario, an agent would classify the intent here.
        # For the wireframe, we assume valid modification request.
        logger.info(f"[AOSM] Classifying intent...\n event: {event}")
        # Add user message to the current message observations
        self.current_message["observations"].append(event.payload.get("content", "No message provided"))
        logger.info(f"[AOSM] Current message: {self.current_message}")
        # Transition to PREPARE_ANA_RUN or WAIT_FOR_USER if ambiguous
        await self.transition_to(AOSMState.PREPARE_ANA_RUN, "Intent classified as modification", payload=event.payload)
        # Request workspace client to prepare and upload workspace
        await self.ws_client.emit_workspace_upload(message="Preparing workspace for modification run")

    async def _handle_prepare_ana_run(self, event: BaseEvent):
        logger.info("[AOSM] Preparing ANA run...")
        
        if event.type in [EventType.WORKSPACE_SYNC_COMPLETE]:
            logger.info(f"[AOSM] Received workspace upload confirmation: {event}")
            reference_id = event.artifact_id
            if not reference_id:
                logger.error("[AOSM] No artifact_id provided in WORKSPACE_UPLOAD event")
                await self.transition_to(AOSMState.ERROR_PRESENTED, "Missing workspace reference")
                return

            try:
                # 3. Download the workspace zip, extract and store circuit code under a predefined directory
                circuit_path = await self._download_and_extract_workspace(reference_id)
                logger.info(f"[AOSM] Circuit code extracted to: {circuit_path}")
                
                # Update current message with the circuit path for the next states
                self.current_message["circuit_code_path"] = str(circuit_path)
                
                # 4. Transition to TRIGGER_ANA once workspace is ready
                await self.transition_to(AOSMState.TRIGGER_ANA, "Workspace ready for ANA run", payload=event.payload)
            except Exception as e:
                logger.error(f"[AOSM] Failed to prepare workspace: {e}", exc_info=True)
                await self.transition_to(AOSMState.ERROR_PRESENTED, f"Workspace preparation failed: {str(e)}")
        else:
            logger.info(f"[AOSM] Still waiting for workspace upload (Received: {event.type})")

    async def _download_and_extract_workspace(self, reference_id: str) -> Path:
        """Downloads the workspace zip and extracts the circuit file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_zip = Path(temp_dir) / "workspace.zip"
            
            # Download from Minio
            logger.info(f"Downloading {reference_id} from bucket {self.bucket_name}...")
            await asyncio.to_thread(
                self.s3_client.download_file, 
                self.bucket_name, 
                reference_id, 
                str(temp_zip)
            )
            
            # Extract
            extract_dir = Path(temp_dir) / "extracted"
            extract_dir.mkdir()
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Find the circuit .tsx file
            # For now, we assume there's a .tsx file or we take the first one found
            tsx_files = list(extract_dir.glob("**/*.tsx"))
            if not tsx_files:
                raise FileNotFoundError("No .tsx circuit file found in workspace zip")
            
            # Pick the first one (or we could have more logic here)
            source_tsx = tsx_files[0]
            
            # Store in predefined directory
            dest_dir = self.workspace_manager.workspace_root / "current_run"
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_tsx = dest_dir / source_tsx.name
            
            shutil.copy2(source_tsx, dest_tsx)
            return dest_tsx

    async def _handle_trigger_ana(self, event: BaseEvent):
        if event.type == EventType.STATE_TRANSITION:
            logger.info(f"[AOSM] Triggering ANA-D on state entry.")
            # Create ANA-D state machine instance with the circuit code path 
            circuit_code_path = self.current_message.get("circuit_code_path")
            observations = self.current_message.get("observations", [])
            logger.info(f"[AOSM-TRIGGER ANA]: Circuit code path: {circuit_code_path}, observations: {observations}")

            if not circuit_code_path:
                logger.error("[AOSM] No circuit code path found in current message for ANA-D")
                await self.transition_to(AOSMState.ERROR_PRESENTED, "Missing circuit code for ANA run")
                return
            # Initialize inbox queue for bidirectional communication
            self.ana_inbox = asyncio.Queue()
            
            self.active_ana_sm = ANADStateMachine(
                circuit_code_path=circuit_code_path, 
                observations=observations,
                ws_client=self.ws_client,
                parent_notify=self._parent_notify,
                inbox_queue=self.ana_inbox
            )
            # Run the ANA-D state machine in a background task to keep AOSM responsive
            asyncio.create_task(self.active_ana_sm.run())
        else:
            raise ValueError(f"Unexpected event type in TRIGGER_ANA state: {event.type}")
        
        
        await self.transition_to(AOSMState.WAIT_FOR_ANA, "ANA-D started")

    async def _handle_wait_for_ana(self, event: BaseEvent):
        if event.type == EventType.EVALUATION_UPDATE:
            status = event.payload.get("status")
            if status in ["pass", "fail"]:
                await self.transition_to(AOSMState.PRESENT_RESULT, f"ANA finished with status: {status}")
        elif event.type == EventType.INTERRUPT_REQUEST:
            await self.transition_to(AOSMState.CANCEL_PIPELINE, "User interrupted execution")
        elif event.type == EventType.ERROR:
            await self.transition_to(AOSMState.ERROR_PRESENTED, f"System error: {event.payload.get('message')}")
            
        elif event.type == EventType.ANA_NOTIFY:
            # Handle notification from ANA (e.g., HIL_REQUEST)
            logger.info(f"[AOSM-WAIT_FOR_ANA] ANA notification: {event.payload}")
            
            ana_event = event.payload.get("reason")
            if ana_event == "ANA_HIL_REQUIRED":
                # Maybe notify UI that HIL is required
                await self.ws_client.emit_status_update(
                    status="waiting_for_input",
                    message=event.payload.get("message")
                )
            elif ana_event == "ANA_ERROR":
                await self.ws_client.emit_status_update(
                    status="ana_error",
                    message=event.payload.get("message")
                )
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
        image_id = f"{stem}_{uid}"

        # 1. Save image to project root under UserArtefacts/
        project_root = self.workspace_manager.project_root
        if not project_root:
            logger.error("[AOSM-BOOTSTRAP] Project root not set in workspace manager")
            await self.transition_to(AOSMState.ERROR_PRESENTED, "Bootstrap failed: Project not initialized")
            return

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
            self.current_message["circuit_code_path"] = str(scud_path)
            return scud_path
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
