import logging
import time
import httpx
import socket
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class MCPManager:
    """
    Manager for the ANA Commit MCP Server.
    The server itself is now managed by the VHL Runtime (Node.js implementation).
    This manager provides connectivity and polling logic.
    """
    def __init__(self, endpoint: str = "http://localhost:8081"):
        self.mcp_endpoint = endpoint
        self.last_commit_id: int = -1

    def ensure_server_running(self):
        """
        Verifies that the MCP server is up and running.
        Since it's managed by VHL Runtime, we just wait for it to become healthy.
        """
        logger.info(f"[MCP Manager] Verifying MCP Server at {self.mcp_endpoint}...")
        
        # Parse port from endpoint for socket check
        try:
            port = int(self.mcp_endpoint.split(":")[-1])
        except (ValueError, IndexError):
            port = 8081

        max_retries = 30
        for i in range(max_retries):
            try:
                # 1. Low-level socket check
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    s.connect(("127.0.0.1", port))
                
                # 2. HTTP health check
                with httpx.Client() as client:
                    response = client.get(f"{self.mcp_endpoint}/health", timeout=2.0)
                    if response.status_code == 200:
                        logger.info(f"[MCP Manager] MCP Server is healthy at {self.mcp_endpoint}")
                        self._sync_state()
                        return
            except (ConnectionRefusedError, socket.timeout, httpx.RequestError):
                if i % 5 == 0:
                    logger.info(f"[MCP Manager] Waiting for MCP Server... (attempt {i+1}/{max_retries})")
                time.sleep(1)
        
        logger.error(f"[MCP Manager] MCP Server at {self.mcp_endpoint} is not responding.")

    def _sync_state(self):
        """Syncs the internal commit ID with the server's current state to avoid processing old commits."""
        try:
            with httpx.Client() as client:
                response = client.get(f"{self.mcp_endpoint}/mcp/commits")
                if response.status_code == 200:
                    commits = response.json().get("commits", [])
                    obs_commits = [c for c in commits if c.get("tool_name") == "commit_observation"]
                    if obs_commits:
                        latest_commit = max(obs_commits, key=lambda x: x["commit_id"])
                        self.last_commit_id = latest_commit["commit_id"]
                        logger.info(f"[MCP Manager] Synced state. Last commit ID: {self.last_commit_id}")
        except Exception as e:
            logger.warning(f"[MCP Manager] Failed to sync state: {e}")

    def poll_for_observation(self) -> Optional[Dict[str, Any]]:
        """Polls MCP for a new observation commit."""
        url = f"{self.mcp_endpoint}/mcp/commits"
        logger.info(f"[MCP Manager] Polling {url} for latest observation...")
        
        while True:
            try:
                with httpx.Client() as client:
                    response = client.get(url, timeout=5.0)
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
                logger.debug(f"[MCP Manager] Polling error: {e}")
                time.sleep(2)

    def cleanup(self):
        """Cleanup handler. No process to kill anymore as it's managed externally."""
        logger.info("[MCP Manager] Cleaning up MCP Manager.")
