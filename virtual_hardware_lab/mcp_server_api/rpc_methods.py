import os
import logging
import json
import inspect
from typing import Any, Dict, Optional, Callable, Union

from fastapi import HTTPException, Response
from pydantic import ValidationError

from virtual_hardware_lab.simulation_core.simulation_manager import SimulationManager
from virtual_hardware_lab.mcp_server_api.schemas import RunExperimentRequest
from virtual_hardware_lab.mcp_server_api.utils import safe_join, save_and_validate_template_file
from virtual_hardware_lab.mcp_server_api.schemas import RunExperimentRequest, JSONRPCRequest
from virtual_hardware_lab.mcp_server_api.utils import jsonrpc_success, jsonrpc_error, safe_join, save_and_validate_template_file
from virtual_hardware_lab.mcp_server_api.tool_definitions import TOOLS
import asyncio

logger = logging.getLogger("virtual_hardware_lab")

# Initialize manager and BASE_URL (these will be passed from mcp_server.py)
manager: SimulationManager = None
BASE_URL: str = ""

def set_rpc_globals(mgr: SimulationManager, base_url: str):
    global manager, BASE_URL
    manager = mgr
    BASE_URL = base_url

def rpc_initialize(params: Dict[str, Any]):
    protocol = params.get("protocolVersion", "2025-06-18")
    return {
        "protocolVersion": protocol,
        "serverInfo": {
            "name": "virtual_hardware_lab",
            "version": "0.1.0",
            "description": "A Virtual Hardware Lab for deterministic and reproducible SPICE simulations.",
        },
        "capabilities": {
            "supportsNotifications": True,
        },
    }

def rpc_shutdown(params: Dict[str, Any]):
    return {"shutdown": True}

def rpc_list_models(params: Dict[str, Any]):
    try:
        models = manager.list_models()
        return {"models": models}
    except Exception as e:
        logger.exception("Error in rpc_list_models")
        raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")

def rpc_list_controls(params: Dict[str, Any]):
    try:
        controls = manager.list_controls()
        return {"controls": controls}
    except Exception as e:
        logger.exception("Error in rpc_list_controls")
        raise HTTPException(status_code=500, detail=f"Failed to list controls: {str(e)}")

def rpc_get_results(params: Dict[str, Any]):
    sim_id = None
    if isinstance(params, dict):
        sim_id = params.get("sim_id") or params.get("id") or params.get("simId")
    if not sim_id:
        return None
    return manager.read_results(sim_id)

def rpc_get_documentation(params: Dict[str, Any]):
    try:
        doc_path = "docs/VIRTUAL_HARDWARE_LAB_DOCUMENTATION.md"
        if not os.path.exists(doc_path):
            return {"error": "Documentation file not found."}
        with open(doc_path, "r") as f:
            return {"documentation": f.read()}
    except Exception as e:
        logger.exception("Failed to read documentation")
        return {"error": f"Error retrieving documentation: {str(e)}"}

def rpc_run_experiment(params: Dict[str, Any]):
    if isinstance(params, list):
        try:
            params_obj = {
                "model_name": params[0],
                "model_params": params[1] if len(params) > 1 else {},
                "control_name": params[2] if len(params) > 2 else None,
                "control_params": params[3] if len(params) > 3 else {},
                "sim_id": params[4] if len(params) > 4 else None,
            }
        except Exception:
            params_obj = {}
    else:
        params_obj = params or {}

    req = RunExperimentRequest.model_validate(params_obj)
    return manager.start_sim(
        model_name=req.model_name,
        model_params=req.model_params,
        control_name=req.control_name,
        control_params=req.control_params,
        sim_id=req.sim_id,
    )

async def rpc_upload_model(params: Dict[str, Any]):
    filename = params.get("filename")
    content = params.get("content")
    if not filename or not content:
        return {"error": "Missing filename or content"}
    logger.info(f"Uploading model: {filename}\nContent:\n{content}")
    result = await save_and_validate_template_file(manager.models_dir, filename, content)
    print(f"DEBUG: Result from save_and_validate_template_file (model): {result}") # Debug print
    return result

async def rpc_upload_control(params: Dict[str, Any]):
    filename = params.get("filename")
    content = params.get("content")
    if not filename or not content:
        return {"error": "Missing filename or content"}
    logger.info(f"Uploading model: {filename}\nContent:\n{content}")
    result = await save_and_validate_template_file(manager.controls_dir, filename, content)
    print(f"DEBUG: Result from save_and_validate_template_file (control): {result}") # Debug print
    return result

def rpc_get_artifact_link(params: Dict[str, Any]):
    sim_id = params.get("sim_id")
    artifact_filename = params.get("artifact_filename")
    if not sim_id or not artifact_filename:
        raise HTTPException(status_code=400, detail="Missing sim_id or artifact_filename")
    try:
        artifact_path = safe_join(manager.runs_dir, sim_id, artifact_filename)
        if not os.path.exists(artifact_path):
             raise HTTPException(status_code=404, detail="Artifact not found")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")

    uri = f"{BASE_URL}/results/{sim_id}/artifact/{artifact_filename}"
    mime_type = "application/octet-stream"
    if artifact_filename.endswith(".json"): mime_type = "application/json"
    elif artifact_filename.endswith(".txt") or artifact_filename.endswith(".log"): mime_type = "text/plain"
    elif artifact_filename.endswith(".png"): mime_type = "image/png"

    return {
        "uri": uri,
        "mimeType": mime_type,
        "name": artifact_filename
    }

def rpc_tools_list(params: Dict[str, Any]):
    return {"tools": TOOLS}

async def rpc_tools_call(params: Dict[str, Any]):
    """
    Handles 'tools/call' method.
    Returns standard MCP CallToolResult structure: { "content": [ { "type": "text", "text": "..." } ] }
    """
    method_name = params.get("name")
    arguments = params.get("arguments", {})

    if method_name not in RPC_METHODS:
        logger.warning("tools/call: Unknown method %s", method_name)
        raise HTTPException(status_code=404, detail=f"Method '{method_name}' not found.")

    handler = RPC_METHODS[method_name]
    
    if inspect.iscoroutinefunction(handler):
        result = await handler(arguments)
    else:
        result = handler(arguments)

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(result, indent=2)
            }
        ]
    }


RPC_METHODS: Dict[str, Callable] = {
    "initialize": rpc_initialize,
    "shutdown": rpc_shutdown,
    "list_tools": rpc_tools_list,
    "tools/list": rpc_tools_list,
    "list_models": rpc_list_models,
    "list_controls": rpc_list_controls,
    "run_experiment": rpc_run_experiment,
    "get_results": rpc_get_results,
    "get_documentation": rpc_get_documentation,
    "upload_model": rpc_upload_model,
    "upload_control": rpc_upload_control,
    "get_artifact_link": rpc_get_artifact_link,
    "tools/call": rpc_tools_call,
}



# -------------------------
# Dispatcher
# -------------------------
async def dispatch_jsonrpc_old(payload: dict):
    try:
        req = JSONRPCRequest.model_validate(payload)
    except ValidationError as e:
        logger.warning("Invalid JSON-RPC request payload: %s", e)
        return 400, jsonrpc_error(-32600, "Invalid Request", None, data=e.errors())

    method = req.method
    params = req.params or {}
    id_val = req.id
    is_notification = id_val is None

    if method not in RPC_METHODS:
        if is_notification:
            return Response(status_code=204)
        return 404, jsonrpc_error(-32601, f"Method not found: {method}", id_val)

    try:
        handler = RPC_METHODS[method]
        
        if inspect.iscoroutinefunction(handler):
            result = await handler(params)
        else:
            result = handler(params)

        if is_notification:
            return Response(status_code=204)

        if result is None:
            return 200, jsonrpc_success(None, id_val)

        return 200, jsonrpc_success(result, id_val)
    
    except HTTPException as http_exc:
        return http_exc.status_code, jsonrpc_error(
            -32000 - http_exc.status_code, 
            http_exc.detail, 
            id_val
        )
    except ValidationError as e:
        return 400, jsonrpc_error(-32602, "Invalid params", id_val, data=e.errors())
    except Exception as e:
        logger.exception("Internal error in RPC handler for %s", method)
        return 500, jsonrpc_error(-32603, "Internal error", id_val, data=str(e))

async def dispatch_jsonrpc(payload: dict):
    try:
        req = JSONRPCRequest.model_validate(payload)
    except ValidationError as e:
        logger.warning("Invalid JSON-RPC request payload: %s", e)
        return 400, jsonrpc_error(-32600, "Invalid Request", None, data=e.errors())

    method = req.method
    params = req.params or {}
    id_val = req.id
    is_notification = id_val is None

    if method not in RPC_METHODS:
        if is_notification:
            return Response(status_code=204)
        return 404, jsonrpc_error(-32601, f"Method not found: {method}", id_val)

    try:
        handler = RPC_METHODS[method]
        
        if inspect.iscoroutinefunction(handler):
            result = await handler(params)
        else:
            result = handler(params)

        if is_notification:
            return Response(status_code=204)



        # Check if the result contains an error from the RPC method itself
        if isinstance(result, dict) and "error" in result:
            return 200, jsonrpc_error(-32000, result["error"], id_val)


        if result is None:
            return 200, jsonrpc_success(None, id_val)

        return 200, jsonrpc_success(result, id_val)
    
    except ValidationError as e:
        return 400, jsonrpc_error(-32602, "Invalid params", id_val, data=e.errors())
    except Exception as e:
        logger.exception("Internal error in RPC handler for %s", method)
        return 500, jsonrpc_error(-32603, "Internal error", id_val, data=str(e))

