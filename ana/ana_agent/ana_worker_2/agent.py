import os
import json
import time
import zipfile
import logging
from typing import Dict, Any

from openhands.sdk import get_logger
from ana_worker_2.utils.object_store import MinioObjectStore
from ana_worker_2.utils.mcp_utils import MCPInvoker

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
    def __init__(self, mcp_url: str = "http://localhost:8081/mcp", minio_url: str = "http://127.0.0.1:9000"):
        self.mcp_url = mcp_url
        self.minio_url = minio_url
        self.object_store = MinioObjectStore(endpoint_url=minio_url)
        self.invoker = MCPInvoker(mcp_url)

    def validate_circuit(self, circuit_name: str,workspace: str) -> Dict[str, Any]:
        """
        Process the circuit file: upload to object store, invoke VAP, poll for status, and collect results.
        """
        logger.info(f"Identified circuit for validation: {circuit_name}")

        # Find path of the specified circuit file
        # If circuit_name ends with .tsx, use it directly; otherwise, append .tsx
        if circuit_name.endswith('.tsx'):
            circuit_path = os.path.join(workspace, circuit_name)
        else:
            circuit_path = os.path.join(workspace, f"{circuit_name}.tsx")
        
        # Check if the circuit file exists
        # NOTE: Observe if this block is ever hit during normal operation. If not, consider removing it.
        if not os.path.exists(circuit_path):
            # capture warning 
            logger.warning(f"Circuit file {circuit_name} not found in workspace: {workspace}")
            logger.info(f"Attempting to find any .tsx file in workspace: {workspace}")
            # Find all .tsx files in the workspace directory
            tsx_files = [f for f in os.listdir(workspace) if f.endswith('.tsx')]
            if not tsx_files:
                raise FileNotFoundError(f"No .tsx circuit files found in workspace: {workspace}")
            # Use the first .tsx file found
            circuit_path = os.path.join(workspace, tsx_files[0])
            circuit_name = os.path.splitext(os.path.basename(circuit_path))[0]
        
        logger.info(f"Using circuit file: {circuit_path}")

        # 1. Upload the circuit tsx file to Object store
        logger.info(f"Step 1: Uploading {circuit_path} to object store...")
        blob_id = self.object_store.upload_file(circuit_path)
        logger.info(f"Uploaded as blob_id: {blob_id}")

        # 2. Invoke VAP with the circuit object id
        logger.info(f"Step 2: Invoking VAP for circuit: {circuit_name}")
        init_result = self.invoker.call_tool("VAP_init", {
            "circuit_name": circuit_name,
            "blob_id": blob_id
        })
        
        try:
            init_data = json.loads(init_result)
        except json.JSONDecodeError:
            raise RuntimeError(f"Failed to parse VAP_init response: {init_result}")
        
        #TODO: task id should be input to mcp server
        task_id = init_data.get("task_id")
        if not task_id:
            raise RuntimeError(f"Failed to initialize VAP: {init_result}")
        
        logger.info(f"VAP initialized with task_id: {task_id}")

        # 3. Poll for status of the evaluation
        logger.info(f"Step 3: Polling for status of task: {task_id}")
        results = None
        evaluation_metadata = {}
        status = "unknown"
        
        while True:
            status_result = self.invoker.call_tool("VAP_status", {"task_id": task_id})
            try:
                status_data = json.loads(status_result)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse VAP_status response: {status_result}")
                time.sleep(2)
                continue
            
            logger.info(f"Polled status: {status_data}")
            status = status_data.get("eval_status", "unknown")
            logger.info(f"VAP status for {task_id}: {status}")
            
            if status == "Success":
                logger.info("VAP evaluation completed successfully.")
                results = status_data.get("results")
                evaluation_metadata = status_data.get("metadata", {})
                break
            elif (status == "failed") or (status == "Error"):
                error_msg = status_data.get("error", "Unknown error")
                logger.error(f"VAP evaluation failed: {error_msg}")
                evaluation_metadata = status_data.get("metadata", {})
                break
            
            time.sleep(2)

        # 4. Once evaluation is complete, collect evaluation results
        logger.info("Step 4: Collecting evaluation results...")

        #TODO: path refinement
        # output_dir = os.path.join(os.getcwd(), "ana_worker_2", "results", task_id)
        # Set output directory to workspace/evaluation_results
        output_dir = os.path.join(workspace, "evaluation_results")
        download_dir = os.path.join(workspace, "downloads")

        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(download_dir, exist_ok=True)
        
        downloaded_files = []
        # Download and extract results from the blob_id in metadata
        results_blob_id = evaluation_metadata.get("results_blob_id")
        if results_blob_id:
            logger.info(f"Downloading results from blob_id: {results_blob_id}")
            zip_path = os.path.join(download_dir, "evaluation_results.zip")
            try:
                self.object_store.download_file(results_blob_id, zip_path)
                logger.info(f"Downloaded results to {zip_path}")
                
                # Extract the zip file
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(output_dir)
                    logger.info(f"Extracted results to {output_dir}")

                downloaded_files.append(zip_path)
                downloaded_files.extend([os.path.join(output_dir, f) for f in os.listdir(output_dir)])
            except Exception as e:
                logger.error(f"Failed to download/extract results ({results_blob_id}): {e}")
        else:
            logger.warning("No results_blob_id found in evaluation metadata")

        # 5. Delegate back to ANA-D
        # The return value provides all necessary info for ANA-D to continue.
        logger.info("Step 5: Process complete. Returning results to orchestrator.")
        return {
            "task_id": task_id,
            "status": status,
            "results": results,
            "output_dir": output_dir,
            "downloaded_files": downloaded_files,
            "metadata": evaluation_metadata
        }

    def close(self):
        """Cleanup resources."""
        if hasattr(self, 'invoker'):
            self.invoker.close()

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
        logger.exception("Full stack trace:")
        sys.exit(1)
    finally:
        agent.close()
