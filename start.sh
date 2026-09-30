#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Add local node_modules/.bin to PATH
export PATH="${SCRIPT_DIR}/node_modules/.bin:$PATH"

# Dynamically detect Python executable
# Priority: VHL_PYTHON_BIN -> $(dirname "$0")/.venv/bin/python3 -> /app/venv/bin/python3 -> python3
PYTHON_BIN=""
if [ -n "${VHL_PYTHON_BIN:-}" ] && [ -x "${VHL_PYTHON_BIN}" ]; then
  PYTHON_BIN="${VHL_PYTHON_BIN}"
elif [ -x "${SCRIPT_DIR}/.venv/bin/python3" ]; then
  PYTHON_BIN="${SCRIPT_DIR}/.venv/bin/python3"
elif [ -x "/app/venv/bin/python3" ]; then
  PYTHON_BIN="/app/venv/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
fi

if [ -z "${PYTHON_BIN}" ]; then
  echo "Error: Python executable not found." >&2
  echo "Checked locations:" >&2
  echo "  1. VHL_PYTHON_BIN (${VHL_PYTHON_BIN:-not set})" >&2
  echo "  2. ${SCRIPT_DIR}/.venv/bin/python3" >&2
  echo "  3. /app/venv/bin/python3" >&2
  echo "  4. python3 in PATH" >&2
  echo "Action required: Run 'bash scripts/setup-host-python.sh' (or 'pnpm run setup:python') to create the host Python environment," >&2
  echo "or set VHL_PYTHON_BIN to point to a valid Python 3 (>= 3.10) binary." >&2
  exit 1
fi

# Verify required Python modules are available
if ! "${PYTHON_BIN}" -c "import fastmcp, starlette, openhands.tools.terminal, uvicorn" >/dev/null 2>&1; then
  echo "Error: Python executable found at '${PYTHON_BIN}', but required modules (fastmcp, starlette, openhands.tools, uvicorn) are missing." >&2
  echo "Action required: Run 'bash scripts/setup-host-python.sh' (or 'pnpm run setup:python') to install dependencies." >&2
  exit 1
fi

# Track child PIDs for graceful lifecycle management
WS_SERVER_PID=""
WS_CLIENT_PID=""
TERMINAL_PID=""
SNAPSHOT_PID=""

cleanup() {
  local exit_code=$?
  trap - SIGINT SIGTERM EXIT
  echo "Shutting down VHL Runtime services..."

  for pid in "${WS_SERVER_PID}" "${WS_CLIENT_PID}" "${TERMINAL_PID}" "${SNAPSHOT_PID}"; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill -TERM "$pid" 2>/dev/null || true
    fi
  done

  # Give child processes a moment to gracefully release ports (1080, 3022, 8082, 8083)
  sleep 0.5

  for pid in "${WS_SERVER_PID}" "${WS_CLIENT_PID}" "${TERMINAL_PID}" "${SNAPSHOT_PID}"; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill -KILL "$pid" 2>/dev/null || true
    fi
  done

  exit "$exit_code"
}

trap cleanup SIGINT SIGTERM EXIT

# Start Agent WebSocket Server in background (Port 1080)
echo "Starting Agent WebSocket Server..."
node dist/server/wsIndex.js &
WS_SERVER_PID=$!

# Start Workspace WebSocket Client in background (Port 3022)
echo "Starting Workspace WebSocket Client..."
# The VHLRuntime will automatically start 'tsci dev' on port 3020 
# during its connection sequence.
node dist/workspace/index.js &
WS_CLIENT_PID=$!

# Start Terminal MCP Server in background (SSE mode, Port 8082)
echo "Starting Terminal MCP Server with ${PYTHON_BIN}..."
export VHL_TERMINAL_MCP_PORT=8082
"${PYTHON_BIN}" src/mcp/python_servers/terminal_server.py &
TERMINAL_PID=$!

# Start UI Snapshot MCP Server in background (Port 8083)
echo "Starting UI Snapshot MCP Server..."
export SNAPSHOT_PORT=8083
node dist/mcp/ui_snapshot/index.js &
SNAPSHOT_PID=$!

# Wait for any process to exit
# Note: TSCI_PID is not used here as tsci dev is now a child of the VHLRuntime
# On Bash >= 4.3 (Linux container/modern host), 'wait -n' waits for the first process to exit.
# On macOS /bin/bash (v3.2), 'wait -n' is unsupported, so we poll process health every second.
if [ "${BASH_VERSINFO[0]}" -gt 4 ] || { [ "${BASH_VERSINFO[0]}" -eq 4 ] && [ "${BASH_VERSINFO[1]}" -ge 3 ]; }; then
  wait -n $WS_SERVER_PID $WS_CLIENT_PID $TERMINAL_PID $SNAPSHOT_PID
else
  while kill -0 "$WS_SERVER_PID" 2>/dev/null && \
        kill -0 "$WS_CLIENT_PID" 2>/dev/null && \
        kill -0 "$TERMINAL_PID" 2>/dev/null && \
        kill -0 "$SNAPSHOT_PID" 2>/dev/null; do
    sleep 1
  done
fi

# Exit with status of process that exited first
exit $?
