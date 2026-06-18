import asyncio
import time
import logging
from pathlib import Path
import json
import os
from typing import Optional, Dict
from contextlib import asynccontextmanager

from fastmcp import FastMCP, Context
from starlette.types import ASGIApp, Scope, Receive, Send

from openhands.tools.terminal.impl import TerminalExecutor
from openhands.tools.terminal.definition import TerminalAction

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("terminal_server")

# 1. Path Configurations consistent with VHL_runtime/src/config/paths.ts
PROJECT_ROOT = os.environ.get("VHL_PROJECT_ROOT", "/app")
STATE_FILE = os.path.join(PROJECT_ROOT, ".tmp", "active_project.json")
DEFAULT_DIR = PROJECT_ROOT

def get_active_project_dir() -> str:
    """Reads the active project directory from the shared JSON state file."""
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
                return data.get("projectDir") or DEFAULT_DIR
    except Exception as e:
        logger.warning(f"Failed to read state file: {e}")
    return DEFAULT_DIR

# 2. State Management for Multi-Agent Session Isolation
class SessionTerminalRegistry:
    def __init__(self, idle_timeout: int = 300):
        self._sessions: Dict[str, TerminalExecutor] = {}
        self._last_access: Dict[str, float] = {}
        self.idle_timeout = idle_timeout

    def get_terminal(self, session_id: str) -> TerminalExecutor:
        self._last_access[session_id] = time.time()
        if session_id not in self._sessions:
            logger.info(f"Creating new terminal for session: {session_id}")
            active_dir = get_active_project_dir()
            self._sessions[session_id] = TerminalExecutor(working_dir=active_dir)
        return self._sessions[session_id]

    def remove_session(self, session_id: str):
        if session_id in self._sessions:
            logger.info(f"Removing terminal for session: {session_id}")
            terminal = self._sessions.pop(session_id)
            self._last_access.pop(session_id, None)
            # Force cleanup if possible
            try:
                del terminal
            except Exception as e:
                logger.error(f"Error cleaning up terminal for session {session_id}: {e}")

    async def reaper_loop(self):
        """Periodically clean up idle sessions."""
        while True:
            await asyncio.sleep(60)
            now = time.time()
            idle_sessions = [
                sid for sid, last in self._last_access.items()
                if now - last > self.idle_timeout
            ]
            for sid in idle_sessions:
                logger.info(f"Session {sid} idle for {self.idle_timeout}s, reaping...")
                self.remove_session(sid)

registry = SessionTerminalRegistry()

class SessionCleanupMiddleware:
    """Middleware to catch DELETE /mcp and clean up sessions."""
    def __init__(self, app: ASGIApp, registry: SessionTerminalRegistry):
        self.app = app
        self.registry = registry

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "http" and scope["method"] == "DELETE" and scope["path"] == "/mcp":
            # Extract session ID from headers
            headers = dict(scope.get("headers", []))
            session_id = None
            for k, v in headers.items():
                if k.lower() == b"mcp-session-id":
                    session_id = v.decode("utf-8")
                    break
            
            if session_id:
                logger.info(f"Intercepted DELETE for session {session_id}, cleaning up...")
                self.registry.remove_session(session_id)
        
        await self.app(scope, receive, send)

# 3. Initialize MCP Server with lifespan
@asynccontextmanager
async def lifespan(app: FastMCP):
    reaper_task = asyncio.create_task(registry.reaper_loop())
    try:
        yield
    finally:
        reaper_task.cancel()
        try:
            await reaper_task
        except asyncio.CancelledError:
            pass

mcp = FastMCP("VHL-Runtime-Terminal", lifespan=lifespan)

# 4. Tool Definitions
@mcp.tool(name="run_terminal_command")
async def run_terminal_command(
    command: str,
    cwd: str,
    ctx: Context,
    is_input: bool = False,
    timeout: Optional[float] = None,
    reset: bool = False
) -> str:
    """
    Execute a bash command in the terminal within a persistent shell session.
    The terminal automatically tracks the active VHL project directory.
    This is an interactive tool.

    * Soft timeout: Commands have a soft timeout of 10 seconds, once that's reached, you have the option to continue or interrupt the command (see section below for details)

    * If a bash command returns exit code `-1`, this means the process hit the soft timeout and is not yet finished. By setting `is_input` to `true`, you can:
        - Send empty `command` to retrieve additional logs
        - Send text (set `command` to the text) to STDIN of the running process
        - Send control commands like `C-c` (Ctrl+C), `C-d` (Ctrl+D), or `C-z` (Ctrl+Z) to interrupt the process
        - If you do C-c, you can re-start the process with a longer "timeout" parameter to let it run to completion

    ### Interactive Input & Special Keys
    * When sending input to a process (using `is_input=True`), you can use special key names:
        - `ENTER`, `TAB`, `BS` (Backspace), `ESC`
        - `UP`, `DOWN`, `LEFT`, `RIGHT`
        - `HOME`, `END`, `PGUP`, `PGDN`
        - `C-L` (Clear screen), `C-D` (EOF)
    * Ctrl Sequences: You can send Ctrl combinations using the `C-` prefix (e.g., `C-c` for SIGINT, `C-z` for SIGTSTP).

    Args:
        command: The bash command to execute. Use "C-c" to interrupt.
        cwd: Absolute path to the working directory from which command needs to be executed. 
        is_input: Set to True if sending input to a process.
        timeout: Maximum time in seconds to wait for output.
        reset: Set to True to clear session state if the terminal hangs.
    """
    # Context injection gives us the session ID, fallback to "default" if not provided
    session_id = ctx.session_id if ctx.session_id else "default"
    
    logger.info(f"Running command for session {session_id}: {command} from directory: {cwd}")
    
    terminal = registry.get_terminal(session_id)
    # active_dir = Path(get_active_project_dir()) / "lib"
    active_dir = Path(cwd)

    # Create lib/ directory in active project directory if it doesn't exist
    os.makedirs(active_dir, exist_ok=True)
    
    # If the active project directory in the state file has changed since the terminal started,
    # we automatically 'cd' the session into the new folder before running the command.
    # Note: terminal.session._cwd tracks the actual shell directory.
    current_shell_dir = getattr(terminal.session, "_cwd", None)
    
    loop = asyncio.get_running_loop()
    
    if not is_input and not reset and active_dir and current_shell_dir != active_dir:
        # Synchronize directory
        sync_action = TerminalAction(command=f"cd {active_dir}")
        await loop.run_in_executor(None, terminal, sync_action)

    action = TerminalAction(
        command=command,
        is_input=is_input,
        timeout=timeout,
        reset=reset
    )
    
    # TerminalExecutor.__call__ is synchronous, so we run it in an executor
    observation = await loop.run_in_executor(None, terminal, action)
    
    # Return terminal output
    result = observation.text
    
    if hasattr(observation, 'exit_code') and observation.exit_code is not None:
        if observation.exit_code != 0:
            result += f"\n[Process exited with code {observation.exit_code}]"
            
    return result

if __name__ == "__main__":
    # Check if we should run in HTTP mode (which handles streamable-http and SSE)
    port_env = os.environ.get("VHL_TERMINAL_MCP_PORT")
    if port_env:
        print(f"[TerminalServer] Starting server on 0.0.0.0:{port_env}")
        try:
            transport = os.environ.get("VHL_TERMINAL_TRANSPORT", "sse")
            starlette_app = mcp.http_app(transport=transport)
            wrapped_app = SessionCleanupMiddleware(starlette_app, registry)
            import uvicorn
            uvicorn.run(wrapped_app, host="0.0.0.0", port=int(port_env))
        except Exception as e:
            print(f"[TerminalServer] CRITICAL: Failed to start server: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("[TerminalServer] Starting stdio server")
        mcp.run()
