# app.py
import os
import logging
import time
from typing import Any, Dict, Optional, Callable, Union
from fastapi.responses import JSONResponse, FileResponse, Response

import uvicorn
from fastapi import (
    FastAPI,
    Body,
    Request,
    HTTPException,
    UploadFile,
    File,
)
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError, SecretStr

# Import your SimulationManager - adjust path if needed
from virtual_hardware_lab.simulation_manager import SimulationManager

# -------------------------
# Logging + basic settings
# -------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("virtual_hardware_lab")
logger.setLevel(logging.DEBUG)

HOST = "0.0.0.0"
PORT = int(os.getenv("MCP_SERVER_PORT", 53328))

# -------------------------
# Application and manager
# -------------------------
app = FastAPI(
    title="Virtual Hardware Lab MCP Server",
    description="API and JSON-RPC dispatcher for SPICE simulations (MCP-compatible).",
)

# allow cross-origin for convenience (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = SimulationManager()  # your SimulationManager instance

# -------------------------
# Pydantic models
# -------------------------
class RunExperimentRequest(BaseModel):
    model_name: str = Field(..., description="Model template file name (e.g., randles_cell.j2)")
    model_params: dict = Field(default_factory=dict)
    control_name: str = Field(..., description="Control template file name (e.g., eis_control.j2)")
    control_params: dict = Field(default_factory=dict)
    sim_id: Optional[str] = None


# JSON-RPC shapes (light, used internally)
class JSONRPCRequest(BaseModel):
    jsonrpc: str
    method: str
    params: Optional[Union[dict, list]] = None
    id: Optional[Union[int, str]] = None


# -------------------------
# JSON-RPC helpers & security
# -------------------------
def jsonrpc_success(result: Any, id_val: Any):
    return {"jsonrpc": "2.0", "result": result, "id": id_val}


def jsonrpc_error(code: int, message: str, id_val: Any = None, data: Any = None):
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "error": err, "id": id_val}


def safe_join(base_dir: str, *paths: str) -> str:
    # Avoid path traversal by resolving absolutes and ensuring prefix
    candidate = os.path.abspath(os.path.join(base_dir, *paths))
    base_dir_abs = os.path.abspath(base_dir)
    if not candidate.startswith(base_dir_abs):
        raise ValueError("Invalid path (possible path traversal).")
    return candidate


# -------------------------
# RPC implementations
# -------------------------



def rpc_initialize(params: Dict[str, Any]):
    protocol = params.get("protocolVersion", "2025-06-18")
    # Provide server info and any capabilities (extend as needed)
    return {
        "protocolVersion": protocol,
        "serverInfo": {
            "name": "virtual_hardware_lab",
            "version": "0.1.0",
            "description": "A Virtual Hardware Lab for deterministic and reproducible SPICE simulations, powered by ngspice.",
            "usage_guidance": (
                "Interact with this lab to list available SPICE models (circuit definitions) "
                "and control programs (experiment setups). Run simulations by combining these "
                "with specific parameters. Model and control files are separate for modularity "
                "and reuse. Retrieve detailed results and artifacts. Use 'get_documentation' "
                "for comprehensive details."
            ),
        },
        "capabilities": {
            "supportsNotifications": True,
            # Add more capability flags if you implement them:
            # "supportsFileUpload": True, "supportsStreaming": False, ...
        },
    }


def rpc_shutdown(params: Dict[str, Any]):
    # For safety, we only acknowledge. If you want to gracefully exit, implement a background task.
    return {"shutdown": True}


def rpc_list_tools(params: Dict[str, Any]):
    """
    Return tools metadata expected by MCP clients. If manager exposes tools, use it.
    Fallback: produce a small list derived from available REST endpoints.
    """
    # If your manager has a list_tools method, prefer it
    try:
        if hasattr(manager, "list_tools") and callable(manager.list_tools):
            return manager.list_tools()
    except Exception:
        logger.exception("manager.list_tools() failed; returning fallback tool list.")

    # Minimal fallback — adapt to the actual tool schema your client expects
    return [
        {"name": "list_models", "description": "List model templates", "input_schema": None},
        {"name": "list_controls", "description": "List control templates", "input_schema": None},
        {"name": "run_experiment", "description": "Run a SPICE simulation", "input_schema": RunExperimentRequest.schema()},
        {"name": "get_results", "description": "Get simulation results by sim_id", "input_schema": {"type": "object", "properties": {"sim_id": {"type": "string"}}}},
    ]


def rpc_list_models(params: Dict[str, Any]):
    return manager.list_models()


def rpc_list_controls(params: Dict[str, Any]):
    return manager.list_controls()


def rpc_get_results(params: Dict[str, Any]):
    sim_id = None
    if isinstance(params, dict):
        sim_id = params.get("sim_id") or params.get("id") or params.get("simId")
    if not sim_id:
        return None
    return manager.read_results(sim_id)


def rpc_get_documentation(params: Dict[str, Any]):
    try:
        with open("/workspace/ngspice_simulator/docs/VIRTUAL_HARDWARE_LAB_DOCUMENTATION.md", "r") as f:
            return f.read()
    except FileNotFoundError:
        return "Documentation file not found."
    except Exception as e:
        logger.exception("Failed to read documentation")
        return f"Error retrieving documentation: {str(e)}"

def rpc_run_experiment(params: Dict[str, Any]):
    """
    Strict validation: use RunExperimentRequest.parse_obj to raise pydantic errors with helpful info.
    """
    # Allow positional params (list) by making a conversion here
    if isinstance(params, list):
        # map to expected positional order - be careful: define a canonical order
        # [model_name, model_params, control_name, control_params, sim_id]
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

    req = RunExperimentRequest.parse_obj(params_obj)
    # manager.start_sim should return a manifest dict serializable to JSON
    return manager.start_sim(
        model_name=req.model_name,
        model_params=req.model_params,
        control_name=req.control_name,
        control_params=req.control_params,
        sim_id=req.sim_id,
    )


# RPC method registry - map client method names to handler callables
RPC_METHODS: Dict[str, Callable[[Any], Any]] = {
    "initialize": lambda params: rpc_initialize(params),
    "shutdown": lambda params: rpc_shutdown(params),
    "list_tools": lambda params: rpc_list_tools(params),
    "list_models": lambda params: rpc_list_models(params),
    "list_controls": lambda params: rpc_list_controls(params),
    "run_experiment": lambda params: rpc_run_experiment(params),
    "get_results": lambda params: rpc_get_results(params),
    "get_documentation": lambda params: rpc_get_documentation(params),
}



def _obj_schema():
    """Generic permissive object schema for outputs."""
    return {"type": "object", "additionalProperties": True}

def rpc_tools_list(params: Dict[str, Any]):
    """
    Return tools manifest in the shape expected by fastmcp/mcp ListToolsResult.
    Key differences vs earlier attempt:
      - use `inputSchema` and `outputSchema` keys (client expects these exact names)
      - return an object as result: {"tools": [...]}
    """
    # Use pydantic v2 method to produce JSON Schema for RunExperimentRequest
    try:
        run_exp_schema = RunExperimentRequest.model_json_schema()
    except Exception:
        # fallback safe schema if model_json_schema isn't available for some reason
        run_exp_schema = {
            "type": "object",
            "properties": {
                "model_name": {"type": "string"},
                "model_params": {"type": "object"},
                "control_name": {"type": "string"},
                "control_params": {"type": "object"},
                "sim_id": {"type": ["string", "null"]},
            },
            "required": ["model_name", "control_name"]
        }

    tools = [
        {
            "id": "list_models",
            "name": "list_models",
            "title": "List Models",
            "description": "List available NGSpice model templates (GET /models).",
            "inputSchema": {"type": "object", "properties": {}},  # no inputs
            "outputSchema": _obj_schema(),
            "version": "1.0",
        },
        {
            "id": "list_controls",
            "name": "list_controls",
            "title": "List Controls",
            "description": "List available control templates (GET /controls).",
            "inputSchema": {"type": "object", "properties": {}},
            "outputSchema": _obj_schema(),
            "version": "1.0",
        },
        {
            "id": "run_experiment",
            "name": "run_experiment",
            "title": "Run Experiment",
            "description": "Start a SPICE simulation (POST /run_experiment).",
            "inputSchema": run_exp_schema,
            "outputSchema": _obj_schema(),
            "version": "1.0",
        },
        {
            "id": "get_results",
            "name": "get_results",
            "title": "Get Results",
            "description": "Get simulation manifest for a given sim_id (GET /results/{sim_id}).",
            "inputSchema": {
                "type": "object",
                "properties": {"sim_id": {"type": "string"}},
                "required": ["sim_id"],
            },
            "outputSchema": _obj_schema(),
            "version": "1.0",
        },
        {
            "id": "upload_model",
            "name": "upload_model",
            "title": "Upload Model Template",
            "description": "Upload a new NGSpice model template (POST /upload_model).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                    "content_base64": {"type": "string", "description": "Base64-encoded file contents"},
                },
                "required": ["filename", "content_base64"],
            },
            "outputSchema": {"type": "object", "properties": {"filename": {"type": "string"}}},
            "version": "1.0",
        },
        {
            "id": "upload_control",
            "name": "upload_control",
            "title": "Upload Control Template",
            "description": "Upload a new NGSpice control template (POST /upload_control).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                    "content_base64": {"type": "string"},
                },
                "required": ["filename", "content_base64"],
            },
            "outputSchema": {"type": "object", "properties": {"filename": {"type": "string"}}},
            "version": "1.0",
        },
        {
            "id": "get_artifact_link",
            "name": "get_artifact_link",
            "title": "Get Artifact Link",
            "description": "Get a downloadable link for a simulation artifact.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "sim_id": {"type": "string"},
                    "artifact_filename": {"type": "string"},
                },
                "required": ["sim_id", "artifact_filename"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "uri": {"type": "string"},
                    "mimeType": {"type": "string"},
                    "name": {"type": "string"},
                },
                "required": ["uri"],
            },
            "version": "1.0",
        },
        {
            "id": "get_documentation",
            "name": "get_documentation",
            "title": "Get Virtual Hardware Lab Documentation",
            "description": "Retrieve the comprehensive documentation for the Virtual Hardware Lab.",
            "inputSchema": {"type": "object", "properties": {}},
            "outputSchema": {"type": "string"},
            "version": "1.0",
        },
    ]

    # The mcp client expected the JSON-RPC result to be an object, so wrap into {"tools": tools}
    return {"tools": tools}

# Register the exact MCP method name expected by fastmcp clients:
RPC_METHODS["tools/list"] = lambda params: rpc_tools_list(params)
# (Optionally keep RPC_METHODS["list_tools"] pointing to the same handler)
RPC_METHODS["list_tools"] = lambda params: rpc_tools_list(params)

from fastapi.responses import JSONResponse, FileResponse, Response
from pydantic import ValidationError

# --- Dispatcher that returns either Response (bodyless) or (status_code, dict_content) ---
async def dispatch_jsonrpc(payload: dict):
    """
    Handle a single JSON-RPC request object.
    Returns either:
      - a fastapi Response (e.g. Response(status_code=204)) to be returned directly by the endpoint, OR
      - a tuple (status_code: int, content: dict) where content is JSON-serializable (for JSONResponse).
    """
    try:
        # Use model_validate (Pydantic v2)
        req = JSONRPCRequest.model_validate(payload)
    except ValidationError as e:
        logger.warning("Invalid JSON-RPC request payload: %s", e)
        return 400, jsonrpc_error(-32600, "Invalid Request", None, data=e.errors())

    method = req.method
    params = req.params or {}
    id_val = req.id
    is_notification = id_val is None

    # Unknown method handling
    if method not in RPC_METHODS:
        if is_notification:
            logger.info("Received unknown notification method='%s' — ignoring", method)
            return Response(status_code=204)  # return Response directly (no body)
        return 404, jsonrpc_error(-32601, f"Method not found: {method}", id_val)

    try:
        handler = RPC_METHODS[method]
        # Handler may raise ValidationError for bad params (caught below)
        result = handler(params)

        # If it's a notification, we must not return a JSON-RPC envelope per spec.
        if is_notification:
            logger.debug("Processed notification '%s'", method)
            return Response(status_code=204)  # direct, bodyless response

        # Normal call: if result is None, treat as not found
        if result is None:
            return 404, jsonrpc_error(-32004, "Resource not found", id_val)

        # Success: return JSON-RPC success envelope content
        return 200, jsonrpc_success(result, id_val)

    except ValidationError as e:
        logger.warning("Invalid params for method %s: %s", method, e)
        return 400, jsonrpc_error(-32602, "Invalid params", id_val, data=e.errors())
    except TypeError as e:
        logger.exception("TypeError in RPC handler for %s", method)
        return 400, jsonrpc_error(-32602, "Invalid params", id_val, data=str(e))
    except Exception as e:
        logger.exception("Internal error in RPC handler for %s", method)
        return 500, jsonrpc_error(-32603, "Internal error", id_val, data=str(e))


# --- JSON-RPC endpoint (single object; no batch support here) ---
@app.post("/jsonrpc", summary="JSON-RPC 2.0 endpoint")
async def jsonrpc_endpoint(payload: Dict = Body(...)):
    status_or_resp = await dispatch_jsonrpc(payload)

    # If dispatch returned a Response instance, return it directly (bodyless or custom)
    if isinstance(status_or_resp, Response):
        return status_or_resp

    # Otherwise expect (status_code, content_dict)
    status, content = status_or_resp
    # If the status is 204, explicitly return a bodyless Response to avoid JSONResponse(None)
    if status == 204:
        return Response(status_code=204)
    return JSONResponse(status_code=status, content=content)


# --- Compatibility: accept JSON-RPC POSTs at root "/" too ---
@app.post("/", summary="Root POST (compat json-rpc)")
async def root_post(request: Request, payload: Dict = Body(None)):
    # If no JSON body -> regular REST behavior
    if not payload:
        return {"message": "Virtual Hardware Lab MCP Server received a POST request!"}

    # If looks like JSON-RPC, dispatch it
    if isinstance(payload, dict) and payload.get("jsonrpc") == "2.0" and payload.get("method"):
        status_or_resp = await dispatch_jsonrpc(payload)
        if isinstance(status_or_resp, Response):
            return status_or_resp
        status, content = status_or_resp
        if status == 204:
            return Response(status_code=204)
        return JSONResponse(status_code=status, content=content)

    # Not JSON-RPC: fallback
    return {"message": "Virtual Hardware Lab MCP Server received a POST request!"}


@app.get("/", summary="Root GET")
async def root_get():
    return {"message": "Virtual Hardware Lab MCP Server is running! (GET request)"}


# -------------------------
# REST endpoints (unchanged, but cleaned)
# -------------------------
@app.get("/models", summary="List all available model templates")
async def list_models():
    try:
        models = manager.list_models()
        return JSONResponse(content=models)
    except Exception as e:
        logger.exception("list_models failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/controls", summary="List all available control templates")
async def list_controls():
    try:
        controls = manager.list_controls()
        return JSONResponse(content=controls)
    except Exception as e:
        logger.exception("list_controls failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/run_experiment", summary="Run a new simulation experiment (REST)")
async def run_experiment(request: RunExperimentRequest):
    try:
        manifest = manager.start_sim(
            model_name=request.model_name,
            model_params=request.model_params,
            control_name=request.control_name,
            control_params=request.control_params,
            sim_id=request.sim_id,
        )
        return JSONResponse(content=manifest)
    except Exception as e:
        logger.exception("run_experiment failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/results/{sim_id}", summary="Get simulation results (manifest)")
@app.post("/results/{sim_id}", summary="Get simulation results (manifest) (POST request)")
async def get_results(sim_id: str):
    manifest = manager.read_results(sim_id)
    if manifest:
        return JSONResponse(content=manifest)
    raise HTTPException(status_code=404, detail=f"Simulation with ID '{sim_id}' not found.")


@app.get("/results/{sim_id}/artifact/{artifact_filename}", summary="Get a specific simulation artifact")
@app.post("/results/{sim_id}/artifact/{artifact_filename}", summary="Get a specific simulation artifact (POST request)")
async def get_artifact(sim_id: str, artifact_filename: str):
    artifact_path = safe_join(manager.runs_dir, sim_id, artifact_filename)
    if not os.path.exists(artifact_path):
        raise HTTPException(status_code=404, detail="Artifact not found.")
    return FileResponse(artifact_path)


# upload helpers
async def _save_and_validate_file(directory: str, file: UploadFile):
    if not file.filename.endswith(".j2"):
        raise HTTPException(status_code=400, detail="Invalid file type. Only .j2 files are allowed.")
    os.makedirs(directory, exist_ok=True)
    file_path = safe_join(directory, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())
    return {"filename": file.filename, "message": f"Successfully uploaded to {directory}"}


@app.post("/upload_model", summary="Upload a new model template")
async def upload_model(file: UploadFile = File(...)):
    try:
        return await _save_and_validate_file(manager.models_dir, file)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("upload_model failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload_control", summary="Upload a new control template")
async def upload_control(file: UploadFile = File(...)):
    try:
        return await _save_and_validate_file(manager.controls_dir, file)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("upload_control failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------
# Lifecycle & runner
# -------------------------
if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
