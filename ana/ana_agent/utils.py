import os
import asyncio
from typing import Dict, Any, Optional

from openhands.sdk import get_logger
from vhl_protocol.websocket_client.client import VHLWebSocketClient

from vhl_protocol.models import EventType

# Configure logger
logger = get_logger(__name__)

class ANA_CodeEvaluator:
    """
    ANA_CodeEvaluator: Deterministic workflow for circuit evaluation using VHL-VAP.
    
    Responsibilities:
    1. Invoke VAP process 
    2. Collect and extract evaluation results.
    """
    def __init__(self, web_socket_client: VHLWebSocketClient, project_id: Optional[str] = None, storage_url: Optional[str] = None, mcp_manager: Any = None):
        self.web_socket_client = web_socket_client
        
        self.project_id = project_id
        self.storage_url = storage_url
        self.mcp_manager = mcp_manager

    async def validate_circuit(self, circuit_name: str, workspace: str, module_name: str) -> Dict[str, Any]:
        """
        Process the circuit file: upload to object store, invoke VAP, poll for status, and collect results.
        """
        # Find path of the specified circuit file

        # 1. Invoke VAP and wait for completion
        logger.info(f"[ANA_validation_agent.validate_circuit] Step 2: Executing VAP for circuit: {circuit_name}")
        if self.mcp_manager:
            logger.info("[ANA_validation_agent.validate_circuit] Using MCP for VAP execution")
            status_data = await asyncio.to_thread(
                self.mcp_manager.call_tool,
                "evaluate_circuit",
                {
                    "circuit_name": circuit_name,
                    "workspace": workspace,
                }
            )
        else:
            logger.info("[ANA_validation_agent.validate_circuit] Using WebSockets for VAP execution")
            await self.web_socket_client.emit_vap_execute(circuit_name=circuit_name, workspace=workspace)
            
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

        output_dir = os.path.join(workspace, "eval_results")
            
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
