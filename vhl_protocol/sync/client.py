import os
import logging
from typing import Optional, Dict, Any
from ..client.client import VHLWebSocketClient
from ..models import BaseEvent, EventType, SyncPayload, EventSource
from ..utils.hashing import compute_file_hash, compute_directory_hash
from ..utils.object_storage import get_storage_client
from ..utils.zip import compress_directory, decompress_zip, atomic_replace_directory, atomic_replace_file
import tempfile
from pathlib import Path
import asyncio
import uuid, shutil
from workspace.manager import WorkspaceManager

logger = logging.getLogger(__name__)

class SyncClient:
    def __init__(self, web_socket_client: VHLWebSocketClient, workspace_manager: WorkspaceManager):
        self.web_socket_client = web_socket_client
        self.workspace_manager = workspace_manager
        self.base_dir = str(workspace_manager.workspace_root)
        self.storage_client = get_storage_client()
        self.web_socket_client.add_subscriber(self.handle_runtime_message)

    def get_resource_path(self, project_id: str, resource_type: str, iteration_id: Optional[str] = None) -> str:
        """Resolve the local filesystem path for a resource using standard workspace conventions."""
        return str(self.workspace_manager.resolve_resource_path(project_id, resource_type, iteration_id))

    async def handle_runtime_message(self, event: BaseEvent):
        if event.type not in [EventType.UPLOAD_REQUEST, EventType.DOWNLOAD_REQUEST]:
            return
        
        try:
            payload = SyncPayload.model_validate(event.payload)

            # Ignore events from self
            if payload.source in ["backend", EventSource.VHL_AGENT_BACKEND]:
                return    
            if event.type == EventType.UPLOAD_REQUEST:
                await self.handle_upload_request(payload)
            elif event.type == EventType.DOWNLOAD_REQUEST:
                await self.handle_download_request(payload)
            elif event.type == EventType.SYNC_ERROR:
                logger.error(f"[SyncClient] Received SYNC_ERROR: {payload.reason}")
            elif event.type == EventType.SYNC_COMPLETE:
                logger.info(f"[SyncClient] Received SYNC_COMPLETE for {payload.resource_type} (sync_id={payload.sync_id})")
        except Exception as e:
            logger.error(f"[SyncClient.handle_runtime_message] Error handling sync message {event.type}: {e}", exc_info=True)
            if isinstance(event.payload, dict) and "sync_id" in event.payload:
                await self.send_sync_error(event.payload["sync_id"], event.payload["project_id"], str(e))

    async def send_sync_error(self, sync_id: str, project_id: str, reason: str):
        error_payload = SyncPayload(
            sync_id=sync_id,
            project_id=project_id,
            resource_type="Unknown",
            reason=reason,
            source=EventSource.VHL_AGENT_BACKEND
        )
        await self.web_socket_client.emit(EventType.SYNC_ERROR, error_payload)

    # ─── Fundamental Sync Handlers ───────────────────────────────────────────────

    async def handle_upload_request(self, payload: SyncPayload):
        """
        Handle an UPLOAD_REQUEST: the sender wants us to upload our local artefact
        to the object store, then notify them with a DOWNLOAD_REQUEST so they can fetch it.

        Flow: local hash → [hash check] → compress (if dir) → [storage existence check] → upload → DOWNLOAD_REQUEST

        If payload.hash (the sender's local hash) is provided and matches our local hash,
        both sides already have the same content — emit SYNC_COMPLETE and skip the upload.

        The outgoing DOWNLOAD_REQUEST carries our local hash so the receiver can
        verify integrity after downloading.

        Can be called both in response to an incoming UPLOAD_REQUEST event, or
        directly (e.g. from sync_evaluation_output) to initiate a proactive push.
        """
        sync_id = payload.sync_id
        logger.info(f"[SyncClient.handle_upload_request] Handling UPLOAD_REQUEST for {payload.resource_type} (sync_id={sync_id})")

        path = Path(self.get_resource_path(payload.project_id, payload.resource_type, payload.iteration_id))
        if not path.exists():
            logger.warning(f"[SyncClient.handle_upload_request] Resource path does not exist: {path}")

        # Compute local hash
        hash_val = None
        if path.is_dir():
            hash_val = compute_directory_hash(str(path))
        else:
            hash_val = compute_file_hash(str(path))

        # Use hash-based blob ID (same as syncManager.ts)
        # format: {project_id}/{resource_type}/{hash}(.zip)
        if path.is_dir():
            blob_id = f"{payload.project_id}/{payload.resource_type}/{hash_val}.zip"
        else:
            blob_id = f"{payload.project_id}/{payload.resource_type}/{hash_val}"

        blob_to_upload = None
        temp_zip = None

        try:
            # Skip upload if blob already exists in storage
            logger.debug(f"[SyncClient.handle_upload_request] Checking storage for blob_id={blob_id}")
            blob_exists = await asyncio.to_thread(self.storage_client.object_exists, blob_id)
            
            if not blob_exists:
                if path.is_dir():
                    temp_zip = Path(tempfile.gettempdir()) / f"upload_{sync_id}.zip"
                    logger.debug(f"[SyncClient.handle_upload_request] Compressing directory {path} to {temp_zip}")
                    compress_directory(str(path), str(temp_zip))
                    blob_to_upload = str(temp_zip)
                else:
                    blob_to_upload = str(path)

                logger.info(f"[SyncClient.handle_upload_request] Uploading {payload.resource_type} to storage (blob_id={blob_id}, path={blob_to_upload})...")
                await asyncio.to_thread(self.storage_client.upload_file, blob_to_upload, blob_id)
                logger.debug(f"[SyncClient.handle_upload_request] Upload completed for blob_id={blob_id}")
            else:
                logger.info(f"[SyncClient.handle_upload_request] Blob {blob_id} already exists in storage. Skipping upload.")

            download_payload = SyncPayload(
                sync_id=sync_id,
                project_id=payload.project_id,
                iteration_id=payload.iteration_id,
                resource_type=payload.resource_type,
                intent=payload.intent,
                hash=hash_val,   # Our local hash — receiver uses this for integrity check
                blob_id=blob_id,
                data={"circuit_name": self.workspace_manager.circuit_name},
                source=EventSource.VHL_AGENT_BACKEND,
            )
            await self.web_socket_client.emit(EventType.DOWNLOAD_REQUEST, download_payload)
            logger.info(f"[SyncClient.handle_upload_request] Emitted DOWNLOAD_REQUEST (sync_id={sync_id})")

        except Exception as e:
            logger.error(f"[SyncClient.handle_upload_request] Failed to upload {payload.resource_type}: {e}")
            await self.send_sync_error(sync_id, payload.project_id, str(e))
            raise
        finally:
            if temp_zip and os.path.exists(temp_zip):
                os.remove(temp_zip)

        return blob_id

    async def handle_download_request(self, payload: SyncPayload):
        """
        Handle a DOWNLOAD_REQUEST: the sender wants us to download a previously uploaded
        artefact from the object store and apply it locally, then confirm with SYNC_COMPLETE.

        The payload carries the sender's local hash (set during upload) which we use
        to verify integrity after downloading.

        Flow: storage download → hash verify → decompress (if needed) → atomic apply → SYNC_COMPLETE
        """
        sync_id = payload.sync_id
        logger.info(f"[SyncClient.handle_download_request] Handling DOWNLOAD_REQUEST for {payload.resource_type} (sync_id={sync_id})")

        target_path = self.get_resource_path(payload.project_id, payload.resource_type, payload.iteration_id)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)

        scratch_dir = Path(self.base_dir) / ".sync_scratch" / str(uuid.uuid4())
        scratch_dir.mkdir(parents=True, exist_ok=True)

        try:
            tmp_file = scratch_dir / "downloaded_blob"
            logger.info(f"[SyncClient.handle_download_request] Downloading blob {payload.blob_id} from storage to {tmp_file}...")
            await asyncio.to_thread(self.storage_client.download_file, payload.blob_id, str(tmp_file))
            logger.debug(f"[SyncClient.handle_download_request] Download completed for blob {payload.blob_id}")

            if payload.resource_type in ["Library", "Evaluation", "EvaluationOutput"]:
                extract_dir = scratch_dir / "extracted"
                extract_dir.mkdir(parents=True, exist_ok=True)
                logger.debug(f"[SyncClient.handle_download_request] Decompressing {tmp_file} to {extract_dir}")
                decompress_zip(str(tmp_file), str(extract_dir))
                computed_hash = compute_directory_hash(str(extract_dir))
                logger.debug(f"[SyncClient.handle_download_request] Computed directory hash: {computed_hash}, expected: {payload.hash}")
                if computed_hash != payload.hash:
                    raise ValueError(f"Hash mismatch! Expected {payload.hash}, got {computed_hash}")
                logger.debug(f"[SyncClient.handle_download_request] Applying atomic directory replace: {extract_dir} -> {target_path}")
                atomic_replace_directory(str(extract_dir), str(target_path))
            else:
                computed_hash = compute_file_hash(str(tmp_file))
                logger.debug(f"[SyncClient.handle_download_request] Computed file hash: {computed_hash}, expected: {payload.hash}")
                if computed_hash != payload.hash:
                    raise ValueError(f"Hash mismatch! Expected {payload.hash}, got {computed_hash}")
                logger.debug(f"[SyncClient.handle_download_request] Applying atomic file replace: {tmp_file} -> {target_path}")
                atomic_replace_file(str(tmp_file), str(target_path))

            logger.info(f"[SyncClient.handle_download_request] Successfully applied {payload.resource_type}")
            complete_payload = SyncPayload(
                sync_id=sync_id,
                project_id=payload.project_id,
                iteration_id=payload.iteration_id,
                resource_type=payload.resource_type,
                source=EventSource.VHL_AGENT_BACKEND
            )
            await self.web_socket_client.emit(EventType.SYNC_COMPLETE, complete_payload)

        except Exception as e:
            logger.error(f"[SyncClient.handle_download_request] Error applying resource {payload.resource_type}: {e}", exc_info=True)
            await self.send_sync_error(sync_id, payload.project_id, str(e))
        finally:
            if scratch_dir.exists():
                shutil.rmtree(str(scratch_dir))

    # ─── Convenience Methods ──────────────────────────────────────────────────────

    async def sync_circuit_json(self, project_id: str, iteration_id: str):
        """
        Push local EvaluationOutput to the runtime.

        Uses the fundamental sync pattern: directly calls handle_upload_request,
        which uploads the artefact and emits DOWNLOAD_REQUEST to the receiver.
        No acknowledgement is awaited on our side — the receiver applies the artefact
        and emits SYNC_COMPLETE independently.
        """
        sync_id = str(uuid.uuid4())
        logger.info(f"[SyncClient.sync_evaluation_output] Syncing evaluation output for project {project_id}, iteration {iteration_id} (sync_id={sync_id})")

        local_path = self.get_resource_path(project_id, "EvaluationOutput", iteration_id)
        local_hash = compute_directory_hash(local_path) if os.path.exists(local_path) else None

        payload = SyncPayload(
            sync_id=sync_id,
            project_id=project_id,
            iteration_id=iteration_id,
            resource_type="EvaluationOutput",
            intent="RESULT",
            hash=local_hash,
            source=EventSource.VHL_AGENT_BACKEND,
        )

        await self.web_socket_client.emit(EventType.UPLOAD_REQUEST, payload)

        try:
            await self.web_socket_client.wait_for_event(
                EventType.SYNC_COMPLETE,
                filter_func=lambda e: e.payload.get("resource_type") == "EvaluationOutput" and e.payload.get("sync_id") == sync_id,
                timeout=60.0
            )
            logger.info(f"[SyncClient.sync_evaluation] Evaluation sync completed (sync_id={sync_id})")
        except asyncio.TimeoutError:
            logger.error(f"[SyncClient.sync_evaluation] Timeout waiting for evaluation sync (sync_id={sync_id})")
            raise

    async def sync_evaluation(self, project_id: str, iteration_id: str):
        """
        Pull Evaluation results from the runtime.

        Sends an UPLOAD_REQUEST to the runtime (asking it to upload its copy),
        then waits for our local DOWNLOAD_REQUEST handling + SYNC_COMPLETE.
        """
        sync_id = str(uuid.uuid4())
        logger.info(f"[SyncClient.sync_evaluation] Requesting evaluation sync for project {project_id}, iteration {iteration_id} (sync_id={sync_id})")

        local_path = self.get_resource_path(project_id, "Evaluation", iteration_id)
        local_hash = compute_directory_hash(local_path) if os.path.isdir(local_path) else (
            compute_file_hash(local_path) if os.path.exists(local_path) else None
        )

        payload = SyncPayload(
            sync_id=sync_id,
            project_id=project_id,
            iteration_id=iteration_id,
            resource_type="Evaluation",
            intent="RESULT",
            hash=local_hash,  # Let runtime skip upload if hashes already match
            source=EventSource.VHL_AGENT_BACKEND,
        )
        await self.web_socket_client.emit(EventType.UPLOAD_REQUEST, payload)

        try:
            await self.web_socket_client.wait_for_event(
                EventType.SYNC_COMPLETE,
                filter_func=lambda e: e.payload.get("resource_type") == "Evaluation" and e.payload.get("sync_id") == sync_id,
                timeout=60.0
            )
            logger.info(f"[SyncClient.sync_evaluation] Evaluation sync completed (sync_id={sync_id})")
        except asyncio.TimeoutError:
            logger.error(f"[SyncClient.sync_evaluation] Timeout waiting for evaluation sync (sync_id={sync_id})")
            raise

    async def sync_library(self, project_id: str):
        """
        Pull Library from the runtime.

        Sends an UPLOAD_REQUEST to the runtime, then waits for SYNC_COMPLETE.
        """
        sync_id = str(uuid.uuid4())
        logger.info(f"[SyncClient.sync_library] Requesting library sync for project {project_id} (sync_id={sync_id})")

        local_path = self.get_resource_path(project_id, "Library")
        local_hash = compute_directory_hash(local_path) if os.path.isdir(local_path) else (
            compute_file_hash(local_path) if os.path.exists(local_path) else None
        )

        payload = SyncPayload(
            sync_id=sync_id,
            project_id=project_id,
            resource_type="Library",
            hash=local_hash,  # Let runtime skip upload if hashes already match
            source=EventSource.VHL_AGENT_BACKEND,
        )
        await self.web_socket_client.emit(EventType.UPLOAD_REQUEST, payload)

        try:
            await self.web_socket_client.wait_for_event(
                EventType.SYNC_COMPLETE,
                filter_func=lambda e: e.payload.get("resource_type") == "Library" and e.payload.get("sync_id") == sync_id,
                timeout=60.0
            )
            logger.info(f"[SyncClient.sync_library] Library sync completed (sync_id={sync_id})")
        except asyncio.TimeoutError:
            logger.error(f"[SyncClient.sync_library] Timeout waiting for library sync (sync_id={sync_id})")
            raise

    async def sync_stable_circuit(self, project_id: str):
        """
        Pull StableCircuit from the runtime.

        Sends an UPLOAD_REQUEST to the runtime, then waits for SYNC_COMPLETE.
        """
        sync_id = str(uuid.uuid4())
        logger.info(f"[SyncClient.sync_stable_circuit] Requesting stable circuit sync for project {project_id} (sync_id={sync_id})")

        local_path = self.get_resource_path(project_id, "StableCircuit")
        local_hash = compute_file_hash(local_path) if os.path.exists(local_path) else None

        payload = SyncPayload(
            sync_id=sync_id,
            project_id=project_id,
            resource_type="StableCircuit",
            hash=local_hash,  # Let runtime skip upload if hashes already match
            data={"circuit_name": self.workspace_manager.circuit_name},
            source=EventSource.VHL_AGENT_BACKEND,
        )
        await self.web_socket_client.emit(EventType.UPLOAD_REQUEST, payload)

        try:
            await self.web_socket_client.wait_for_event(
                EventType.SYNC_COMPLETE,
                filter_func=lambda e: e.payload.get("resource_type") == "StableCircuit" and e.payload.get("sync_id") == sync_id,
                timeout=60.0
            )
            logger.info(f"[SyncClient.sync_stable_circuit] StableCircuit sync completed (sync_id={sync_id})")
        except asyncio.TimeoutError:
            logger.error(f"[SyncClient.sync_stable_circuit] Timeout waiting for stable circuit sync (sync_id={sync_id})")
            raise