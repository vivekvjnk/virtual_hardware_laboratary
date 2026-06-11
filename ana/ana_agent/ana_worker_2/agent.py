import os
import json
import uuid
import zipfile
import logging
import asyncio
from typing import Dict, Any, Optional, Union

from openhands.sdk import get_logger
from vhl_protocol.sync.client import SyncClient
from vhl_protocol.client.client import VHLWebSocketClient

from vhl_protocol.models import EventType, SyncPayload, EventSource

# Configure logger
logger = get_logger(__name__)

class ANA_validation_agent:
    """
    ANA-W2 Agent: Deterministic workflow for circuit evaluation using VHL-VAP.
    
    Responsibilities:
    1. Sync circuit file to object store.
    2. Invoke VAP process via MCP.
    3. Poll for evaluation status.
    4. Collect and extract evaluation results.
    """
    def __init__(self, web_socket_client: VHLWebSocketClient, sync_client: Optional[SyncClient] = None, project_id: Optional[str] = None, storage_url: Optional[str] = None, mcp_manager: Any = None):
        self.web_socket_client = web_socket_client
        self.sync_client = sync_client
        self.project_id = project_id
        self.storage_url = storage_url
        self.mcp_manager = mcp_manager

    async def validate_circuit(self, circuit_name: str, workspace: str, iteration_id: str, module_name: str) -> Dict[str, Any]:
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
            blob_id = await self.sync_client.handle_upload_request(SyncPayload(
                sync_id=str(uuid.uuid4()),
                project_id=self.project_id,
                module_name=module_name,
                resource_type="Circuit",
                iteration_id=iteration_id,
                intent="EVALUATION",
                source = EventSource.VHL_AGENT_BACKEND
            ))
        else:
            raise ValueError(f"[ANA_validation_agent.validate_circuit] SyncClient or ProjectID not available. SyncClient: {self.sync_client}, ProjectID: {self.project_id}")
        
        logger.info(f"[ANA_validation_agent.validate_circuit] Uploaded as blob_id: {blob_id}") 
        
        # 2. Invoke VAP and wait for completion
        logger.info(f"[ANA_validation_agent.validate_circuit] Step 2: Executing VAP for circuit: {circuit_name}")
        if self.mcp_manager:
            logger.info("[ANA_validation_agent.validate_circuit] Using MCP for VAP execution")
            status_data = await asyncio.to_thread(
                self.mcp_manager.call_tool,
                "evaluate_circuit",
                {
                    "circuit_name": circuit_name,
                    "blob_id": blob_id,
                    "iteration_id": iteration_id,
                    "module_name": module_name
                }
            )
        else:
            logger.info("[ANA_validation_agent.validate_circuit] Using WebSockets for VAP execution")
            await self.web_socket_client.emit_vap_execute(circuit_name, blob_id, iteration_id=iteration_id, module_name=module_name)
            
            # Wait for the VAP_COMPLETE event
            response = await self.web_socket_client.wait_for_event(
                EventType.VAP_COMPLETE,
                filter_func=lambda e: e.payload.get("task_id") is not None
            )
        
            status_data = response.payload
        task_id = status_data.get("task_id")
        logger.info(f"[ANA_validation_agent.validate_circuit] VAP completed for task_id: {task_id}")

        decision = status_data.get("decision", "unknown")
        results = status_data.get("results")
        evaluation_metadata = status_data.get("metadata", {})
        
        logger.info(f"[ANA_validation_agent.validate_circuit] VAP decision for {task_id}: {decision}")
        
        if decision == "ACCEPT":
            logger.info("[ANA_validation_agent.validate_circuit] VAP evaluation completed successfully.")
        elif decision == "REJECT":
            error_msg = status_data.get("error", "Unknown error")
            logger.warning(f"[ANA_validation_agent.validate_circuit] VAP evaluation failed: {error_msg}")
        else:
            logger.error(f"[ANA_validation_agent.validate_circuit] Unexpected decision '{decision}' received.")
            raise RuntimeError(f"Unexpected decision '{decision}' received from VAP.")

        # 4. Once evaluation is complete, sync evaluation results
        logger.info("[ANA_validation_agent.validate_circuit] Step 4: Syncing evaluation results...")
        output_dir = os.path.join(workspace, "eval_results")
        
        try:
            # Workflow 1.2: Runtime -> Agent download for Evaluation
            await self.sync_client.sync_evaluation(self.project_id, module_name, iteration_id)
        except Exception as e:
            raise ValueError(f"[ANA_validation_agent.validate_circuit] Failed to synchronize evalution results. Error: {e}")
            
        # 5. Delegate back to ANA-D
        # The return value provides all necessary info for ANA-D to continue.
        logger.info("[ANA_validation_agent.validate_circuit] Step 5: Sync complete. Process complete. Returning results to orchestrator.")
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
