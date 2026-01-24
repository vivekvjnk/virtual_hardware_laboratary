
import os
import time
import socket
from typing import Dict, Any, List, Optional, Union

from fastapi import FastAPI, HTTPException, status, Request
from pydantic import BaseModel, Field, ValidationError

# Import the core logic
from server.core import get_commits, commit_observation, commit_fix_proposal
from server.tool_code.schemas import ObservationCommit, FixProposalCommit

# Create standard FastAPI app
app = FastAPI(
    title="MCP Server - Typed Commit Tool Framework",
    description="A generic, schema-driven commit framework for agents to submit structured messages.",
    version="1.0.0",
)

# --- MCP JSON-RPC 2.0 Implementation ---

class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any] | None = None
    id: int | str | None = None

class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: int | str | None = None
    result: Any | None = None
    error: Dict[str, Any] | None = None

async def process_mcp_request(request: JSONRPCRequest) -> JSONRPCResponse:
    """
    Core logic for handling an MCP JSON-RPC 2.0 request.
    Handles 'initialize', 'tools/list', and 'tools/call'.
    """
    if request.method == "initialize":
        return JSONRPCResponse(
            id=request.id,
            result={
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "ana-process-server",
                    "version": "1.0.0"
                }
            }
        )

    if request.method == "notifications/initialized":
        if request.id is not None:
             return JSONRPCResponse(id=request.id, result=True)
        return  # No response for notification, effectively None, but caller should handle

    if request.method == "tools/list":
        tools = [
            {
                "name": "commit_observation",
                "description": "Commit an observation found during analysis. The payload corresponds to an observation of an issue or a confirmation of correctness.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        # We specifically nest the payload here to match existing practice
                        "payload": ObservationCommit.model_json_schema()
                    },
                    "required": ["payload"]
                }
            },
            {
                "name": "commit_fix_proposal",
                "description": "Commit a proposal for a fix to a detected issue.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "payload": FixProposalCommit.model_json_schema()
                    },
                    "required": ["payload"]
                }
            }
        ]
        return JSONRPCResponse(
            id=request.id,
            result={
                "tools": tools
            }
        )

    if request.method == "tools/call":
        if not request.params:
             raise HTTPException(status_code=400, detail="Missing params")
        
        tool_name = request.params.get("name")
        arguments = request.params.get("arguments", {})

        try:
            if tool_name == "commit_observation":
                if "payload" in arguments:
                     raw_payload = arguments["payload"]
                else:
                     raw_payload = arguments
                
                payload_obj = ObservationCommit(**raw_payload)
                result = commit_observation(payload_obj)
                
                return JSONRPCResponse(
                    id=request.id,
                    result={
                        "content": [{"type": "text", "text": str(result)}]
                    }
                )

            elif tool_name == "commit_fix_proposal":
                if "payload" in arguments:
                     raw_payload = arguments["payload"]
                else:
                     raw_payload = arguments

                payload_obj = FixProposalCommit(**raw_payload)
                result = commit_fix_proposal(payload_obj)

                return JSONRPCResponse(
                    id=request.id,
                    result={
                        "content": [{"type": "text", "text": str(result)}]
                    }
                )
            
            else:
                 return JSONRPCResponse(
                    id=request.id,
                    error={"code": -32601, "message": f"Tool '{tool_name}' not found."}
                )

        except Exception as e:
            return JSONRPCResponse(
                id=request.id,
                error={"code": -32603, "message": f"Tool execution failed: {str(e)}"}
            )

    return JSONRPCResponse(
        id=request.id,
        error={"code": -32601, "message": f"Method '{request.method}' not found."}
    )


@app.post("/mcp", response_model=JSONRPCResponse)
async def mcp_handler(request: JSONRPCRequest):
    """
    Standard MCP JSON-RPC 2.0 endpoint.
    """
    res = await process_mcp_request(request)
    if res is None:
         # Should technically return 204 No Content for notifications, but FastAPI helpers expect model
         # Just return an empty success for now if forced
         return JSONRPCResponse(jsonrpc="2.0", result=True)
    return res


# --- Hybrid Legacy/REST + Dynamic MCP Endpoints ---

class CommitRequest(BaseModel):
    tool_name: str = Field(..., description="The name of the commit tool to use.")
    payload: Dict[str, Any] = Field(..., description="The payload for the commit.")

@app.get("/mcp/commits", summary="Query the commit log.")
async def get_commits_endpoint(
    since: int | None = None,
    endpoint: str | None = None
):
    return {"commits": get_commits(since=since, endpoint=endpoint)}


@app.post("/mcp/{scope_endpoint:path}")
async def dynamic_mcp_or_commit(scope_endpoint: str, raw_request: Request):
    """
    Hybrid endpoint that accepts either:
    1. A JSON-RPC 2.0 request (acting as an MCP endpoint/transport).
    2. A legacy CommitRequest (tool_name, payload).
    """
    try:
        body = await raw_request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # 1. Check for JSON-RPC 2.0
    if isinstance(body, dict) and body.get("jsonrpc") == "2.0":
        try:
            rpc_req = JSONRPCRequest(**body)
            # Process as MCP request
            response = await process_mcp_request(rpc_req)
            if response is None:
                return {} # Notification ack
            return response
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON-RPC request: {e}")

    # 2. Fallback to Legacy CommitRequest
    # We manually validate against CommitRequest schema
    try:
        request = CommitRequest(**body)
    except ValidationError:
        # If it matches neither, we return 422 explaining both failed
        raise HTTPException(
            status_code=422, 
            detail="Unprocessable Content. Expected either a JSON-RPC 2.0 request OR a legacy CommitRequest (tool_name, payload)."
        )

    # Legacy Logic
    full_endpoint = f"/mcp/{scope_endpoint}"
    
    try:
        if request.tool_name == "commit_observation":
            if full_endpoint != "/mcp/observe":
                raise HTTPException(status_code=400, detail=f"Tool '{request.tool_name}' is not visible in endpoint '{full_endpoint}'.")
            try:
                data = ObservationCommit(**request.payload)
            except Exception as e:
                 raise HTTPException(status_code=400, detail=f"Schema validation failed: {e}")
            return commit_observation(data)

        elif request.tool_name == "commit_fix_proposal":
            if full_endpoint != "/mcp/prepare_fix":
                raise HTTPException(status_code=400, detail=f"Tool '{request.tool_name}' is not visible in endpoint '{full_endpoint}'.")
            try:
                data = FixProposalCommit(**request.payload)
            except Exception as e:
                 raise HTTPException(status_code=400, detail=f"Schema validation failed: {e}")
            return commit_fix_proposal(data)
        
        else:
            raise HTTPException(status_code=400, detail=f"Tool '{request.tool_name}' not found.")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")


@app.get("/mcp/{scope_endpoint:path}/tools", summary="List available tools for a given endpoint.")
async def get_tools_endpoint(scope_endpoint: str):
    """
    Legacy tool listing.
    """
    full_endpoint = f"/mcp/{scope_endpoint}"
    tools = []
    if full_endpoint == "/mcp/observe":
        tools.append({
            "name": "commit_observation",
            "schema": ObservationCommit.model_json_schema(),
            "target_channel": "OBSERVATION_MESSAGE",
            "visibility_scope": "/mcp/observe"
        })
    elif full_endpoint == "/mcp/prepare_fix":
         tools.append({
            "name": "commit_fix_proposal",
            "schema": FixProposalCommit.model_json_schema(),
            "target_channel": "FIX_PROPOSAL_MESSAGE",
            "visibility_scope": "/mcp/prepare_fix"
        })
        
    return tools


@app.get("/health", summary="Health check endpoint.")
async def health_check():
    return {"status": "ok"}