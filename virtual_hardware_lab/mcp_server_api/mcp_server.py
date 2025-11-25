# app.py
import os
import logging
import inspect
from typing import Any, Dict, Union
from fastapi.responses import JSONResponse, Response

import uvicorn
from fastapi import (
    FastAPI,
    Body,
    Request,
    HTTPException,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from virtual_hardware_lab.simulation_core.simulation_manager import SimulationManager
from virtual_hardware_lab.mcp_server_api.schemas import RunExperimentRequest, JSONRPCRequest
from virtual_hardware_lab.mcp_server_api import rpc_methods


# -------------------------
# Logging + basic settings
# -------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("virtual_hardware_lab")
logger.setLevel(logging.DEBUG)

HOST = "0.0.0.0"
PORT = int(os.getenv("MCP_SERVER_PORT", 53328))
BASE_URL = os.getenv("BASE_URL", f"http://localhost:{PORT}")

# -------------------------
# Application and manager
# -------------------------
app = FastAPI(
    title="Virtual Hardware Lab MCP Server",
    description="API and JSON-RPC dispatcher for SPICE simulations (MCP-compatible).",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = SimulationManager()
rpc_methods.set_rpc_globals(manager, BASE_URL)


# -------------------------
# Endpoints
# -------------------------

@app.post("/jsonrpc", summary="JSON-RPC 2.0 endpoint")
async def jsonrpc_endpoint(payload: Dict = Body(...)):
    status_or_resp = await rpc_methods.dispatch_jsonrpc(payload)
    if isinstance(status_or_resp, Response):
        return status_or_resp
    status, content = status_or_resp
    if status == 204:
        return Response(status_code=204)
    return JSONResponse(status_code=status, content=content)

@app.post("/", summary="Root POST (compat json-rpc)")
async def root_post(request: Request, payload: Dict = Body(None)):
    if not payload:
        return {"message": "Virtual Hardware Lab MCP Server received a POST request!"}
    if isinstance(payload, dict) and payload.get("jsonrpc") == "2.0" and payload.get("method"):
        status_or_resp = await rpc_methods.dispatch_jsonrpc(payload)
        if isinstance(status_or_resp, Response):
            return status_or_resp
        status, content = status_or_resp
        if status == 204:
            return Response(status_code=204)
        return JSONResponse(status_code=status, content=content)
    return {"message": "Virtual Hardware Lab MCP Server received a POST request!"}

@app.get("/", summary="Root GET")
async def root_get():
    return {"message": "Virtual Hardware Lab MCP Server is running!"}

