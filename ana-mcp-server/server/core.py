
from typing import Any, Dict, List, Optional
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from server.tool_code.schemas import ObservationCommit, FixProposalCommit

# Initialize FastMCP Server
# This object handles MCP protocol details automatically (initialization, tool listing, etc.)
mcp = FastMCP("ANA Process Server")

# Internal storage for the commit log
_commit_log: List[Dict[str, Any]] = []
_commit_counter: int = 0

def _add_commit(endpoint: str, tool_name: str, payload: Dict[str, Any], target_channel: str) -> Dict[str, Any]:
    """Internal helper to append to the commit log."""
    global _commit_counter
    
    message = {
        "type": target_channel,
        "payload": payload,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
        },
    }

    commit_entry = {
        "commit_id": _commit_counter,
        "timestamp": datetime.now().isoformat(),
        "endpoint": endpoint,
        "tool_name": tool_name,
        "message": message,
    }
    
    _commit_log.append(commit_entry)
    _commit_counter += 1
    
    return {"status": "ACK", "message": message}

@mcp.tool()
def commit_observation(payload: ObservationCommit) -> Dict[str, Any]:
    """
    Commit an observation found during analysis.
    The payload corresponds to an observation of an issue or a confirmation of correctness.
    """
    # FastMCP automatically validates 'payload' against the Pydantic model
    return _add_commit("/mcp/observe", "commit_observation", payload.model_dump(), "OBSERVATION_MESSAGE")

def get_commits(since: int | None = None, endpoint: str | None = None) -> List[Dict[str, Any]]:
    """Retrieve commits from the log with optional filtering."""
    commits = _commit_log
    if since is not None:
        commits = [c for c in commits if c["commit_id"] > since]
    if endpoint is not None:
        commits = [c for c in commits if c["endpoint"] == endpoint]
    return commits
