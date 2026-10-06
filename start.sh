#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Add local node_modules/.bin to PATH
export PATH="${SCRIPT_DIR}/node_modules/.bin:$PATH"

# Track child PIDs for graceful lifecycle management
WS_SERVER_PID=""
SNAPSHOT_PID=""

cleanup() {
  local exit_code=$?
  trap - SIGINT SIGTERM EXIT
  echo "Shutting down VHL Runtime services..."

  for pid in "${WS_SERVER_PID}" "${SNAPSHOT_PID}"; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill -TERM "$pid" 2>/dev/null || true
    fi
  done

  # Give child processes a moment to gracefully release ports (3022, 8083)
  sleep 0.5

  for pid in "${WS_SERVER_PID}" "${SNAPSHOT_PID}"; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill -KILL "$pid" 2>/dev/null || true
    fi
  done

  exit "$exit_code"
}

trap cleanup SIGINT SIGTERM EXIT

# Start Native Workspace WebUI / Substrate in background (Port 3022)
echo "Starting Native Workspace WebUI..."
node dist/workspace/index.js &
WS_SERVER_PID=$!

# Start UI Snapshot MCP Server in background (Port 8083)
echo "Starting UI Snapshot MCP Server..."
export SNAPSHOT_PORT=8083
node dist/mcp/ui_snapshot/index.js &
SNAPSHOT_PID=$!

# Portable wait loop for background processes
if [ "${BASH_VERSINFO[0]}" -gt 4 ] || { [ "${BASH_VERSINFO[0]}" -eq 4 ] && [ "${BASH_VERSINFO[1]}" -ge 3 ]; }; then
  wait -n $WS_SERVER_PID $SNAPSHOT_PID
else
  while kill -0 "$WS_SERVER_PID" 2>/dev/null && \
        kill -0 "$SNAPSHOT_PID" 2>/dev/null; do
    sleep 1
  done
fi

# Exit with status of process that exited first
exit $?
