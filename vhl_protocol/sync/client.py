import os
import logging
from typing import Optional, Dict, Any
from ..client.client import VHLWebSocketClient
from ..models import BaseEvent, EventType, EventSource, SyncPayload
from ..utils.hashing import compute_file_hash, compute_directory_hash
from ..utils.minio import get_minio_client
from ..utils.zip import compress_directory, decompress_zip, atomic_replace_directory, atomic_replace_file
import tempfile
import shutil

logger = logging.getLogger(__name__)

class SyncClient:
    def __init__(self, ws_client: VHLWebSocketClient, base_dir: str):
        self.ws_client = ws_client
        self.base_dir = base_dir
        self.minio = get_minio_client()
        self.ws_client.add_subscriber(self.handle_runtime_message)

    def get_resource_path(self, project_id: str, resource_type: str, iteration_id: Optional[str] = None, data: Optional[Dict[str, Any]] = None) -> str:
        """Resolve the local filesystem path for a resource."""
        # This logic should match the WorkspaceManager's directory layout
        project_root = os.path.join(self.base_dir, project_id)
        
        if resource_type == "Library":
            return os.path.join(project_root, "lib/imports")
        elif resource_type == "Circuit":
            circuit_name = data.get("circuit_name") if data else "circuit"
            if iteration_id:
                return os.path.join(project_root, "iterations", iteration_id, f"{circuit_name}.tsx")
            return os.path.join(project_root, f"{circuit_name}.tsx")
        elif resource_type == "Evaluation":
            if iteration_id:
                return os.path.join(project_root, "iterations", iteration_id, "eval_results")
            return os.path.join(project_root, "eval_results")
        elif resource_type == "StableCircuit":
            circuit_name = data.get("circuit_name") if data else "circuit"
            return os.path.join(project_root, "Stable", f"{circuit_name}.tsx")
        
        raise ValueError(f"Unknown resource type: {resource_type}")

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
                    payload.intent, 
                    payload.data
                )
        except Exception as e:
            logger.error(f"Error handling sync message {event.type}: {e}", exc_info=True)
            # We should probably send a SYNC_ERROR here if we have a sync_id
            if hasattr(event.payload, "sync_id"):
                 await self.send_sync_error(event.payload["sync_id"], event.payload["project_id"], str(e))

    async def handle_hash_request(self, payload: SyncPayload):
        logger.info(f"Handling HASH_REQUEST for {payload.resource_type} (sync_id={payload.sync_id})")
        path = self.get_resource_path(payload.project_id, payload.resource_type, payload.iteration_id, payload.data)
        
        hash_val = None
        if os.path.exists(path):
            if os.path.isdir(path):
                hash_val = compute_directory_hash(path)
            else:
                hash_val = compute_file_hash(path)
        
        response_payload = SyncPayload(
            sync_id=payload.sync_id,
            project_id=payload.project_id,
            iteration_id=payload.iteration_id,
            resource_type=payload.resource_type,
            hash=hash_val
        )
        
        await self.ws_client.emit(EventType.HASH_RESPONSE, response_payload)

    async def handle_download_request(self, payload: SyncPayload):
        logger.info(f"Handling DOWNLOAD_REQUEST for {payload.resource_type} (sync_id={payload.sync_id})")
        target_path = self.get_resource_path(payload.project_id, payload.resource_type, payload.iteration_id, payload.data)
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_file = os.path.join(tmp_dir, "downloaded_blob")
            await asyncio.to_thread(self.minio.download_file, payload.blob_id, tmp_file)
            
            # Verify hash
            computed_hash = compute_file_hash(tmp_file) if payload.resource_type in ["Circuit", "StableCircuit"] else None
            # If it's a directory, we need to unzip first to compute directory hash? 
            # Or is the blob hash the directory hash?
            # The spec says "Verify computed hash matches declared hash". 
            # For directories, the blob is a zip of the directory, but the 'hash' in the payload is the directory hash.
            # So we MUST unzip to verify.
            
            if payload.resource_type in ["Library", "Evaluation"]:
                extract_dir = os.path.join(tmp_dir, "extracted")
                decompress_zip(tmp_file, extract_dir)
                computed_hash = compute_directory_hash(extract_dir)
                if computed_hash != payload.hash:
                    raise ValueError(f"Hash mismatch! Expected {payload.hash}, got {computed_hash}")
                
                atomic_replace_directory(extract_dir, target_path)
            else:
                if computed_hash != payload.hash:
                    raise ValueError(f"Hash mismatch! Expected {payload.hash}, got {computed_hash}")
                atomic_replace_file(tmp_file, target_path)

        # Notify completion
        complete_payload = SyncPayload(
            sync_id=payload.sync_id,
            project_id=payload.project_id,
            iteration_id=payload.iteration_id,
            resource_type=payload.resource_type
        )
        await self.ws_client.emit(EventType.SYNC_COMPLETE, complete_payload)

    async def propose_upload(self, project_id: str, resource_type: str, iteration_id: Optional[str] = None, intent: Optional[str] = None, data: Optional[Dict[str, Any]] = None):
        """Trigger an upload proposal from the agent side."""
        sync_id = str(uuid.uuid4())
        path = self.get_resource_path(project_id, resource_type, iteration_id, data)
        
        if not os.path.exists(path):
            raise FileNotFoundError(f"Resource path does not exist: {path}")

        hash_val = None
        blob_to_upload = None
        temp_zip = None

        if os.path.isdir(path):
            hash_val = compute_directory_hash(path)
            temp_zip = os.path.join(tempfile.gettempdir(), f"upload_{sync_id}.zip")
            compress_directory(path, temp_zip)
            blob_to_upload = temp_zip
        else:
            hash_val = compute_file_hash(path)
            blob_to_upload = path

        blob_id = f"{project_id}/{resource_type}/{hash_val}"
        
        try:
            await asyncio.to_thread(self.minio.upload_file, blob_to_upload, blob_id)
            
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

import asyncio
import uuid
