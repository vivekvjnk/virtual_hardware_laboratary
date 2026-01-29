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
            logger.info("[MCP Manager] MCP Server already running on port 8001.")
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
                logger.info(f"[MCP Manager] MCP Server started on attempt {i+1}")
                return
            except (ConnectionRefusedError, socket.timeout):
                time.sleep(1)
        
        logger.error("[MCP Manager] Failed to start MCP Server.")

    def poll_for_observation(self) -> Optional[Dict[str, Any]]:
        """Polls MCP for an observation commit since last_commit_id."""
        url = f"{self.mcp_endpoint}/mcp/commits"
        params = {
            "since": self.last_commit_id,
            "endpoint": "/mcp/observe"
        }

        logger.info(f"[MCP Manager] Polling {url} with since={self.last_commit_id}...")
        
        while True:
            try:
                with httpx.Client() as client:
                    response = client.get(url, params=params)
                    if response.status_code == 200:
                        commits = response.json().get("commits", [])
                        for commit in commits:
                            if commit["tool_name"] == "commit_observation":
                                self.last_commit_id = commit["commit_id"]
                                return commit
                
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
