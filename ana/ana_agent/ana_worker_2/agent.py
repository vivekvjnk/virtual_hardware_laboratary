import os
import json
import uuid
import zipfile
import logging
from typing import Dict, Any, Optional

from openhands.sdk import get_logger
from ana_agent.ana_worker_2.utils.object_store import MinioObjectStore
from vhl_protocol.sync.client import SyncClient
from vhl_protocol.client.client import VHLWebSocketClient

from vhl_protocol.models import EventType, SyncPayload

# Configure logger
logger = get_logger(__name__)

class ANA_validation_agent:
    """
    ANA-W2 Agent: Deterministic workflow for circuit evaluation using VHL-VAP.
    
    Responsibilities:
    1. Upload circuit file to MinIO object store.
    2. Invoke VAP process via MCP.
    3. Poll for evaluation status.
    4. Collect and extract evaluation results.
    """
    def __init__(self, web_socket_client: VHLWebSocketClient, sync_client: Optional[SyncClient] = None, project_id: Optional[str] = None, minio_url: str = "http://127.0.0.1:9000"):
        self.web_socket_client = web_socket_client
        self.sync_client = sync_client
        self.project_id = project_id
        self.minio_url = minio_url
        self.object_store = MinioObjectStore(endpoint_url=minio_url)

    async def validate_circuit(self, circuit_name: str, workspace: str, iteration_id: str) -> Dict[str, Any]:
        """
        Process the circuit file: upload to object store, invoke VAP, poll for status, and collect results.
        """
        # Find path of the specified circuit file
        circuit_path = os.path.join(workspace, f"{circuit_name}.tsx")

        # 1. Sync the circuit tsx file to Runtime
        logger.info(f"[ANA_validation_agent.validate_circuit] Step 1: Syncing {circuit_path} to VHL Runtime...")
        if self.sync_client and self.project_id:
            # Workflow 1.2: Agent -> Runtime upload proposal for Circuit
            # This step synchronises the circuit code
            blob_id = await self.sync_client.propose_upload(
                project_id=self.project_id,
                resource_type="Circuit",
                iteration_id=iteration_id,
                intent="EVALUATION"
            )
        else:
            raise ValueError(f"[ANA_validation_agent.validate_circuit] SyncClient or ProjectID not available. SyncClient: {self.sync_client}, ProjectID: {self.project_id}")
        
        logger.info(f"[ANA_validation_agent.validate_circuit] Uploaded as blob_id: {blob_id}") 
        
        # 2. Invoke VAP with the circuit object id
        logger.info(f"[ANA_validation_agent.validate_circuit] Step 2: Invoking VAP for circuit: {circuit_name}")
        await self.web_socket_client.emit_vap_init(circuit_name, blob_id,iteration_id=iteration_id)
        
        # Wait for the initial VAP_STATUS to get task_id
        init_response = await self.web_socket_client.wait_for_event(
            EventType.VAP_INIT_COMPLETE,
            filter_func=lambda e: e.payload.get("task_id") is not None
        )
        
        task_id = init_response.payload.get("task_id")
        logger.info(f"[ANA_validation_agent.validate_circuit] VAP initialized with task_id: {task_id}")

        # 3. Poll for status of the evaluation
        logger.info(f"[ANA_validation_agent.validate_circuit] Step 3: Polling for status of task: {task_id}")
        results = None
        evaluation_metadata = {}
        status = "unknown"
        
        while True:
            status_event = await self.web_socket_client.wait_for_event(
                EventType.VAP_STATUS_REPORT,
                filter_func=lambda e: e.payload.get("task_id") == task_id
            )
            status_data = status_event.payload
            
            logger.info(f"[ANA_validation_agent.validate_circuit] Received status event: {status_data}")
            status = status_data.get("eval_status", "unknown")
            decision = status_data.get("decision", "N/A")
            
            logger.info(f"[ANA_validation_agent.validate_circuit] VAP decision for {task_id}: {decision}")
            logger.info(f"[ANA_validation_agent.validate_circuit] VAP status for {task_id}: {status}")
            
            evaluation_metadata = status_data.get("metadata", {})
            
            if decision == "ACCEPT":
                logger.info("[ANA_validation_agent.validate_circuit] VAP evaluation completed successfully.")
                results = status_data.get("results")
                break
            elif decision == "REJECT":
                error_msg = status_data.get("error", "Unknown error")
                logger.warning(f"[ANA_validation_agent.validate_circuit] VAP evaluation failed: {error_msg}")
                break
            elif decision == "UNDECIDED":
                logger.info("[ANA_validation_agent.validate_circuit] VAP evaluation still in progress. Waiting for next update...")
            else:
                logger.error(f"[ANA_validation_agent.validate_circuit] Unknown decision '{decision}' received.")
                raise RuntimeError(f"Unknown decision '{decision}' received from VAP.")

        # 4. Once evaluation is complete, sync evaluation results
        logger.info("[ANA_validation_agent.validate_circuit] Step 4: Syncing evaluation results...")
        output_dir = os.path.join(workspace, "eval_results")
        
        if self.sync_client and self.project_id:
             # Workflow 1.2: Runtime -> Agent download for Evaluation
             await self.sync_client.sync_evaluation(self.project_id, iteration_id)
        else:
            raise ValueError(f"[ANA_validation_agent.validate_circuit] Project id or sync client is not set. Project id : {self.project_id}, Sync client : {self.sync_client}")
            
        logger.info("[ANA_validation_agent.validate_circuit] Step 4: Sync complete.")

        # 5. Delegate back to ANA-D
        # The return value provides all necessary info for ANA-D to continue.
        logger.info("[ANA_validation_agent.validate_circuit] Step 5: Process complete. Returning results to orchestrator.")
        return {
            "task_id": task_id,
            "decision": decision,
            "results": results,
            "output_dir": output_dir,
            "metadata": evaluation_metadata
        }

    def close(self):
        """Cleanup resources."""
        pass

if __name__ == "__main__":
    # Simple CLI for testing
    import sys
    
    # Set logging to INFO for CLI usage
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1:
        circuit_name = sys.argv[1]
    else:
        # Default test file
        circuit_name = "bq79616_only_warnings.tsx"
        workspace = os.path.join(os.getcwd(), "ana_workspace")
    
        
    agent = ANA_validation_agent()
    try:
        result = agent.validate_circuit(circuit_name, workspace=workspace)
        print("\n--- Evaluation Results ---")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error during validation: {e}")
        logger.exception("[main] Full stack trace:")
        sys.exit(1)
    finally:
        agent.close()
