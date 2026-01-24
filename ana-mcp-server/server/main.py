


from asyncio import subprocess
import os
import socket
import time
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, Any, List

from server.core import MCPServer
from server.tool_code.registry import tool_registry
from server.exceptions import InvalidToolCall, ToolNotFound, ToolNotInScope, SchemaValidationError


app = FastAPI(
    title="MCP Server - Typed Commit Tool Framework",
    description="A generic, schema-driven commit framework for agents to submit structured messages.",
    version="1.0.0",
)

mcp_server = MCPServer(tool_registry=tool_registry)


class CommitRequest(BaseModel):
    tool_name: str = Field(..., description="The name of the commit tool to use.")
    payload: Dict[str, Any] = Field(..., description="The payload for the commit, validated against the tool's schema.")


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="A description of the error.")


@app.get("/mcp/commits", summary="Query the commit log.")
async def get_commits(
    since: int | None = None,
    endpoint: str | None = None
):
    """
    Retrieves committed messages from the MCP commit log.
    Supports filtering by 'since' (commit_id) and 'endpoint'.
    """
    commits = mcp_server.get_commits(since=since, endpoint=endpoint)
    return {"commits": commits}


@app.post("/mcp/{scope_endpoint:path}", summary="Commit structured messages via a typed commit tool.")
async def commit_message(scope_endpoint: str, request: CommitRequest):
    """
    Allows agents to submit structured messages using a specified commit tool.
    The tool and its payload are validated against predefined schemas and visibility scopes.
    """
    full_endpoint = f"/mcp/{scope_endpoint}"
    try:
        return mcp_server.commit(full_endpoint, request.tool_name, request.payload)
    except (InvalidToolCall, ToolNotFound, ToolNotInScope, SchemaValidationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal Server Error: {e}")


@app.get("/mcp/{scope_endpoint:path}/tools", response_model=List[Dict[str, Any]], summary="List available tools for a given endpoint.")
async def get_tools(scope_endpoint: str):
    """
    Retrieves a list of commit tools available for a specific MCP endpoint.
    """
    full_endpoint = f"/mcp/{scope_endpoint}"
    return mcp_server.get_available_tools(full_endpoint)


@app.get("/health", summary="Health check endpoint.")
async def health_check():
    """
    Returns a simple health check response.
    """
    return {"status": "ok"}


def wait_for_server(port=8001, timeout=15):
    """Wait for server to be ready."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect(("127.0.0.1", port))
            return True
        except (ConnectionRefusedError, socket.timeout):
            time.sleep(0.5)
    return False


# if __name__ == "__main__":
#     print("Starting MCP server...")
#     cwd = os.getcwd()
#     server_process = subprocess.Popen(
#         ["uv", "run", "uvicorn", "mcp_server.main:app", "--port", "8000"],
#         stdout=subprocess.PIPE,
#         stderr=subprocess.PIPE,
#         cwd=cwd
#     )
    
#     try:
#         # Wait for server to start
#         if not wait_for_server():
#             print("ERROR: Server failed to start")
#             # Print stderr for debugging
#             stderr_output = server_process.stderr.read().decode('utf-8')
#             print(f"Server stderr:\n{stderr_output}")
        
#         print("Server started successfully")
#     except Exception as e:
#         print(f"Error while starting server: {e}")
#     # Keep the server running
#     server_process.wait()