import logging
import subprocess
import socket
import time
import os
import httpx
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class MCPManager:
    def __init__(self, endpoint: str = "http://localhost:8001"):
        self.mcp_process: Optional[subprocess.Popen] = None
        self.mcp_endpoint = endpoint
        self.last_commit_id: int = -1

    def ensure_server_running(self):
        """Starts the MCP server if it's not already running on port 8001."""
        try:
            # Check if something is already listening on port 8001
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect(("127.0.0.1", 8001))
            
            logger.info("[MCP Manager] MCP Server already running on port 8001. Syncing state...")
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
            return
        except (ConnectionRefusedError, socket.timeout):
            pass

        logger.info("[MCP Manager] Starting MCP Server process...")
        cwd = os.getcwd()
        
        # Use uv run to ensure all dependencies are available
        cmd = [
            "uv", "run",
            "--package", "ana-mcp-server", 
            "uvicorn", "server.main:app",
            "--port", "8001",
        ]
        
        self.mcp_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "PYTHONPATH": cwd},
            cwd=cwd,
            start_new_session=True
        )
        
        # Wait for server to start
        max_retries = 15
        for i in range(max_retries):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    s.connect(("127.0.0.1", 8001))
                    logger.info("[MCP Manager] MCP Server is running on port 8001.")
                return
            except (ConnectionRefusedError, socket.timeout):
                time.sleep(1)
        
        logger.error("[MCP Manager] Failed to start MCP Server.")

    def poll_for_observation(self) -> Optional[Dict[str, Any]]:
        """Polls MCP for an observation commit."""
        url = f"{self.mcp_endpoint}/mcp/commits"
        logger.info(f"[MCP Manager] Polling {url} for latest observation...")
        
        while True:
            try:
                with httpx.Client() as client:
                    response = client.get(url)
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
                logger.info(f"[MCP Manager] Polling error: {e}")
                time.sleep(2)

    def cleanup(self):
        """Shutting down MCP Server..."""
        if self.mcp_process:
            logger.info("[MCP Manager] Shutting down MCP Server...")
            self.mcp_process.terminate()
            try:
                self.mcp_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.info("[MCP Manager] MCP Server did not terminate, killing...")
                self.mcp_process.kill()
            self.mcp_process = None
            logger.info("[MCP Manager] MCP Server shut down.")
