from pathlib import Path
import json
import os
from typing import Optional, Dict, Any
from fastmcp import FastMCP
from openhands.tools.terminal.impl import TerminalExecutor
from openhands.tools.terminal.definition import TerminalAction

# 1. Initialize MCP Server
# We name it OpenHands-Terminal. In the future, this can serve multiple tools.
mcp = FastMCP("VHL-Library-Terminal")

# 2. Path Configurations consistent with VHL_runtime/src/config/paths.ts
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
        print(f"[TerminalServer] Warning: Failed to read state file: {e}")
    return DEFAULT_DIR

# 3. State Management for Extensibility
class ToolRegistry:
    def __init__(self):
        self._executors: Dict[str, Any] = {}

    def get_executor(self, name: str, factory, **kwargs):
        if name not in self._executors:
            self._executors[name] = factory(**kwargs)
        return self._executors[name]

registry = ToolRegistry()

def get_terminal() -> TerminalExecutor:
    # Always pull the current active project dir
    active_dir = get_active_project_dir()
    
    # Initialize executor if it doesn't exist
    return registry.get_executor(
        "terminal", 
        TerminalExecutor, 
        working_dir=active_dir
    )

# 4. Tool Definitions
@mcp.tool(name="run_terminal_command")
def run_terminal_command(
    command: str,
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
        is_input: Set to True if sending input to a process.
        timeout: Maximum time in seconds to wait for output.
        reset: Set to True to clear session state if the terminal hangs.
    """
    terminal = get_terminal()
    active_dir = Path(get_active_project_dir()) / "lib"

    # Create lib/ directory in active project directory if it doesn't exist
    os.makedirs(active_dir,exist_ok=True)
    
    # If the active project directory in the state file has changed since the terminal started,
    # we automatically 'cd' the session into the new folder before running the command.
    # Note: terminal.session._cwd tracks the actual shell directory.
    current_shell_dir = getattr(terminal.session, "_cwd", None)
    
    if not is_input and not reset and active_dir and current_shell_dir != active_dir:
        # Synchronize directory
        sync_action = TerminalAction(command=f"cd {active_dir}")
        terminal(sync_action)

    action = TerminalAction(
        command=command,
        is_input=is_input,
        timeout=timeout,
        reset=reset
    )
    
    observation = terminal(action)
    
    # Return terminal output
    # We can also include exit_code if helpful, but usually text is enough for an agent.
    result = observation.text
    
    if hasattr(observation, 'exit_code') and observation.exit_code is not None:
        if observation.exit_code != 0:
            result += f"\n[Process exited with code {observation.exit_code}]"
            
    return result

if __name__ == "__main__":
    # Check if we should run in SSE mode
    port_env = os.environ.get("VHL_TERMINAL_MCP_PORT")
    if port_env:
        print(f"[TerminalServer] Starting SSE server on 0.0.0.0:{port_env}")
        try:
            mcp.run(transport="sse", host="0.0.0.0", port=int(port_env))
        except Exception as e:
            print(f"[TerminalServer] CRITICAL: Failed to start SSE server: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("[TerminalServer] Starting stdio server")
        mcp.run()
