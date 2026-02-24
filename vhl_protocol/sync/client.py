import os
import logging
from typing import Optional, Dict, Any
from ..client.client import VHLWebSocketClient
from ..models import BaseEvent, EventType, EventSource, SyncPayload
from ..utils.hashing import compute_file_hash, compute_directory_hash
from ..utils.minio import get_minio_client
from ..utils.zip import compress_directory, decompress_zip, atomic_replace_directory, atomic_replace_file
import tempfile
from pathlib import Path
import asyncio
import uuid, shutil
from workspace.manager import WorkspaceManager

logger = logging.getLogger(__name__)

class SyncClient:
    def __init__(self, ws_client: VHLWebSocketClient, workspace_manager: WorkspaceManager):
        self.ws_client = ws_client
        self.workspace_manager = workspace_manager
        self.base_dir = str(workspace_manager.workspace_root)
        self.minio = get_minio_client()
        self.ws_client.add_subscriber(self.handle_runtime_message)

    def get_resource_path(self, project_id: str, resource_type: str, iteration_id: Optional[str] = None) -> str:
        """Resolve the local filesystem path for a resource using standard workspace conventions."""
        return str(self.workspace_manager.resolve_resource_path(project_id, resource_type, iteration_id))

    async def handle_runtime_message(self, event: BaseEvent):
        if event.type not in [EventType.HASH_REQUEST, EventType.DOWNLOAD_REQUEST, EventType.UPLOAD_REQUEST]:
            return

        try:
            payload = SyncPayload.model_validate(event.payload)
            if event.type == EventType.HASH_REQUEST:
                await self.handle_hash_request(payload)
            elif event.type == EventType.DOWNLOAD_REQUEST:
                await self.handle_download_request(payload)
            elif event.type == EventType.UPLOAD_REQUEST:
                await self.propose_upload(
                    payload.project_id, 
                    payload.resource_type, 
                    payload.iteration_id, 
                    payload.intent
                )
        except Exception as e:
            logger.error(f"[SyncClient.handle_runtime_message] Error handling sync message {event.type}: {e}", exc_info=True)
            # We should probably send a SYNC_ERROR here if we have a sync_id
            if hasattr(event.payload, "sync_id"):
                 await self.send_sync_error(event.payload["sync_id"], event.payload["project_id"], str(e))

    async def handle_hash_request(self, payload: SyncPayload):
        logger.info(f"[SyncClient.handle_hash_request] Handling HASH_REQUEST for {payload.resource_type} (sync_id={payload.sync_id}); Payload:{payload}")
        path = self.get_resource_path(payload.project_id, payload.resource_type, payload.iteration_id)
        
        hash_val = None
        if os.path.exists(path):
            if os.path.isdir(path):
                hash_val = compute_directory_hash(path)
            else:
                hash_val = compute_file_hash(path)
        else:
            logger.info(f"[SyncClient.handle_hash_request] Path doesn't exist: {path}")

        response_payload = SyncPayload(
            sync_id=payload.sync_id,
            project_id=payload.project_id,
            iteration_id=payload.iteration_id,
            resource_type=payload.resource_type,
            hash=hash_val,
            data={"circuit_name":self.workspace_manager.circuit_name}
        )
        
        await self.ws_client.emit(EventType.HASH_RESPONSE, response_payload)

    async def handle_download_request(self, payload: SyncPayload):
        logger.info(f"[SyncClient.handle_download_request] Handling DOWNLOAD_REQUEST for {payload.resource_type} (sync_id={payload.sync_id})")
        target_path = self.get_resource_path(payload.project_id, payload.resource_type, payload.iteration_id)
        #make sure target path exists
        os.makedirs(os.path.dirname(target_path), exist_ok=True)

        scratch_dir = Path(self.base_dir) / ".sync_scratch" / str(uuid.uuid4())
        scratch_dir.mkdir(parents=True, exist_ok=True)

        try:
            tmp_file = scratch_dir / "downloaded_blob"
            await asyncio.to_thread(self.minio.download_file, payload.blob_id, str(tmp_file))

            if payload.resource_type in ["Library", "Evaluation"]:
                extract_dir = scratch_dir / "extracted"
                extract_dir.mkdir(parents=True, exist_ok=True)
                decompress_zip(str(tmp_file), str(extract_dir))
                computed_hash = compute_directory_hash(str(extract_dir))
                logger.info(f"[SyncClient.handle_download_request] Computed hash: {computed_hash}, Declared hash: {payload.hash}")
                if computed_hash != payload.hash:
                    raise ValueError(f"Hash mismatch! Expected {payload.hash}, got {computed_hash}")
                
                atomic_replace_directory(str(extract_dir), str(target_path))
            else:
                computed_hash = compute_file_hash(str(tmp_file))
                logger.info(f"[SyncClient.handle_download_request] Computed hash: {computed_hash}, Declared hash: {payload.hash}")
                if computed_hash != payload.hash:
                    raise ValueError(f"Hash mismatch! Expected {payload.hash}, got {computed_hash}")
                logger.info(f"[SyncClient.handle_download_request] Hash verified for {payload.resource_type}")
                atomic_replace_file(str(tmp_file), str(target_path))

            # Notify completion
            logger.info(f"[SyncClient.handle_download_request] Completed download for {payload.resource_type}")
            complete_payload = SyncPayload(
                sync_id=payload.sync_id,
                project_id=payload.project_id,
                iteration_id=payload.iteration_id,
                resource_type=payload.resource_type
            )
            await self.ws_client.emit(EventType.SYNC_COMPLETE, complete_payload)
        
        except Exception as e:
            logger.error(f"[SyncClient.handle_download_request] Error handling download request for {payload.resource_type}: {e}", exc_info=True)
            # We should probably send a SYNC_ERROR here if we have a sync_id
            if hasattr(payload, "sync_id"):
                await self.send_sync_error(payload.sync_id, payload.project_id, str(e))
        finally:
            # Clean up scratch directory
            if scratch_dir.exists():
                shutil.rmtree(str(scratch_dir))

    async def propose_upload(self, project_id: str, resource_type: str, iteration_id: Optional[str] = None, intent: Optional[str] = None):
        """Trigger an upload proposal from the agent side."""
        sync_id = str(uuid.uuid4())
        path = Path(self.get_resource_path(project_id, resource_type, iteration_id))

        if not path.exists():
            logger.warning(f"[SyncClient.propose_upload] Resource path does not exist: {path}")

        hash_val = None
        blob_to_upload = None
        temp_zip = None

        if path.is_dir():
            hash_val = compute_directory_hash(str(path))
            temp_zip = Path(tempfile.gettempdir()) / f"upload_{sync_id}.zip"
            compress_directory(str(path), str(temp_zip))
            blob_to_upload = str(temp_zip)
        else:
            hash_val = compute_file_hash(str(path))
            blob_to_upload = str(path)

        blob_id = f"{project_id}/{resource_type}/{path.name}"

        try:
            await asyncio.to_thread(self.minio.upload_file, blob_to_upload, blob_id)
            
            data = {"circuit_name":self.workspace_manager.circuit_name}
            proposal_payload = SyncPayload(
                sync_id=sync_id,
                project_id=project_id,
                iteration_id=iteration_id,
                resource_type=resource_type,
                intent=intent,
                hash=hash_val,
                blob_id=blob_id,
                data=data
            )
            
            await self.ws_client.emit(EventType.UPLOAD_PROPOSAL, proposal_payload)
        finally:
            if temp_zip and os.path.exists(temp_zip):
                os.remove(temp_zip)

    async def send_sync_error(self, sync_id: str, project_id: str, reason: str):
        error_payload = SyncPayload(
            sync_id=sync_id,
            project_id=project_id,
            resource_type="Unknown", # Or pull from context
            reason=reason
        )
        await self.ws_client.emit(EventType.SYNC_ERROR, error_payload)

