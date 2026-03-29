import logging
import time
import httpx
import socket
from typing import Optional, Dict, Any
import urllib.parse

logger = logging.getLogger(__name__)

class MCPManager:
    """
    Manager for the ANA Commit MCP Server.
    The server itself is now managed by the VHL Runtime (Node.js implementation).
    This manager provides connectivity and polling logic.
    """
    def __init__(self, endpoint: str = "http://localhost:8081/mcp"):
        """
        Initialize the MCP Manager.
        
        Args:
            endpoint: The full MCP endpoint URL (e.g., "http://localhost:8081/mcp/vap")
        """
        self.tool_endpoint = endpoint
        self.last_commit_id: int = -1
        
        # Parse base URL for health checks and commit logs
        parsed = urllib.parse.urlparse(endpoint)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Extract port for socket check
        try:
            self.port = parsed.port if parsed.port else (80 if parsed.scheme == "http" else 443)
        except (ValueError, AttributeError):
            self.port = 8081

        logger.info(f"[MCPManager] Initialized with tool_endpoint: {self.tool_endpoint}, base_url: {self.base_url}, port: {self.port}")

    def ensure_server_running(self):
        """
        Verifies that the MCP server is up and running.
        Since it's managed by VHL Runtime, we just wait for it to become healthy.
        """
        health_url = f"{self.base_url}/health"
        logger.info(f"[MCPManager.ensure_server_running] Verifying MCP Server at {self.base_url} (port {self.port})...")
        
        max_retries = 30
        for i in range(max_retries):
            try:
                # 1. Low-level socket check
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    # We check 127.0.0.1 for local services, or host from URL
                    host = urllib.parse.urlparse(self.base_url).hostname or "127.0.0.1"
                    logger.debug(f"[MCPManager.ensure_server_running] Attempting socket connection to {host}:{self.port}...")
                    s.connect((host, self.port))
                
                # 2. HTTP health check
                with httpx.Client() as client:
                    response = client.get(health_url, timeout=2.0)
                    if response.status_code == 200:
                        logger.info(f"[MCPManager.ensure_server_running] MCP Server is healthy at {self.base_url}")
                        self._sync_state()
                        return
            except (ConnectionRefusedError, socket.timeout, httpx.RequestError):
                if i % 5 == 0:
                    logger.info(f"[MCPManager.ensure_server_running] Waiting for MCP Server... (attempt {i+1}/{max_retries})")
                time.sleep(1)
        
        logger.error(f"[MCPManager.ensure_server_running] MCP Server at {self.base_url} is not responding.")

    def _sync_state(self):
        """Syncs the internal commit ID with the server's current state to avoid processing old commits."""
        commit_url = f"{self.base_url}/mcp/commits"
        try:
            with httpx.Client() as client:
                response = client.get(commit_url)
                if response.status_code == 200:
                    commits = response.json().get("commits", [])
                    obs_commits = [c for c in commits if c.get("tool_name") == "commit_observation"]
                    if obs_commits:
                        latest_commit = max(obs_commits, key=lambda x: x["commit_id"])
                        self.last_commit_id = latest_commit["commit_id"]
                        logger.info(f"[MCPManager._sync_state] Synced state. Last commit ID: {self.last_commit_id}")
        except Exception as e:
            logger.warning(f"[MCPManager._sync_state] Failed to sync state: {e}")

    def poll_for_observation(self) -> Optional[Dict[str, Any]]:
        """Polls MCP for a new observation commit."""
        commit_url = f"{self.base_url}/mcp/commits"
        logger.info(f"[MCPManager.poll_for_observation] Polling {commit_url} for latest observation...")
        
        while True:
            try:
                with httpx.Client() as client:
                    response = client.get(commit_url, timeout=5.0)
                    if response.status_code == 200:
                        commits = response.json().get("commits", [])
                        # Filter for observation commits
                        obs_commits = [c for c in commits if c.get("tool_name") == "commit_observation"]
                        if obs_commits:
                            # Get the latest commit based on commit_id
                            latest_commit = max(obs_commits, key=lambda x: x["commit_id"])
                            if latest_commit["commit_id"] > self.last_commit_id:
                                self.last_commit_id = latest_commit["commit_id"]
                                return latest_commit
                time.sleep(2)
            except Exception as e:
                logger.debug(f"[MCPManager.poll_for_observation] Polling error: {e}")
                time.sleep(2)
        
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Calls an MCP tool on the server via HTTP."""
        logger.info(f"[MCPManager.call_tool] Calling tool '{tool_name}' at {self.tool_endpoint}...")
        
        # Use JSON-RPC 2.0 format as supported by the Node.js MCP server
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": int(time.time() * 1000)
        }
        
        try:
            with httpx.Client() as client:
                # VAP can take minutes, so we set a long timeout
                response = client.post(self.tool_endpoint, json=payload, timeout=310.0)
                if response.status_code == 200:
                    result = response.json()
                    if "error" in result:
                        error_data = result["error"]
                        error_msg = error_data.get("message", str(error_data))
                        raise RuntimeError(f"MCP Tool Error '{tool_name}': {error_msg}")
                    return result.get("result", {})
                else:
                    raise RuntimeError(f"Failed to call MCP tool '{tool_name}': Status {response.status_code}, {response.text}")
        except Exception as e:
            logger.error(f"[MCPManager.call_tool] Error calling MCP tool '{tool_name}': {e}")
            raise

    def cleanup(self):
        """Cleanup handler. No process to kill anymore as it's managed externally."""
        logger.info("[MCPManager.cleanup] Cleaning up MCP Manager.")
