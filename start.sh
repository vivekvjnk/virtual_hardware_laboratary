#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export VHL_WORKSPACE_DIR="${VHL_WORKSPACE_DIR:-${REPO_ROOT}/workspace}"

# Add local node_modules/.bin to PATH
export PATH="${SCRIPT_DIR}/node_modules/.bin:$PATH"

# Default ECP repository configuration for MOSAIC
export MOSAIC_ECP_REPO_URL="${MOSAIC_ECP_REPO_URL:-git@github.com:vivekvjnk/ECP_VHL.git}"
export MOSAIC_ECP_REF="${MOSAIC_ECP_REF:-main}"
export MOSAIC_ECP_PROVIDER="${MOSAIC_ECP_PROVIDER:-git}"

# Default Cypress Colab GPU delegation remote via rclone
export CYPRESS_RCLONE_REMOTE="${CYPRESS_RCLONE_REMOTE:-cypress_runtime:cypress_colab_runtime}"

# Pre-flight check and release of runtime ports (3022, 8083) and module cluster ports (8100..8150)
# CRITICAL: Never touch ports 8000 or 8001 (workspace MESH host).
if command -v lsof >/dev/null 2>&1; then
  for port in 3022 8083 $(seq 8100 8150); do
    stale_pids="$(lsof -ti :${port} 2>/dev/null || true)"
    if [ -n "$stale_pids" ]; then
      echo "[start.sh] Port ${port} is occupied by existing process (PID: ${stale_pids}). Gracefully releasing..."
      kill -TERM $stale_pids 2>/dev/null || true
      sleep 0.2
      remaining_pids="$(lsof -ti :${port} 2>/dev/null || true)"
      if [ -n "$remaining_pids" ]; then
        echo "[start.sh] Port ${port} still held by PID: ${remaining_pids}. Force killing..."
        kill -KILL $remaining_pids 2>/dev/null || true
      fi
    fi
  done
fi

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

  # Terminate child clusters on ports 8100..8150 (CRITICAL: preserve 8000 and 8001)
  if command -v lsof >/dev/null 2>&1; then
    for port in $(seq 8100 8150); do
      local cpids
      cpids="$(lsof -ti :${port} 2>/dev/null || true)"
      if [ -n "$cpids" ]; then
        kill -TERM $cpids 2>/dev/null || true
      fi
    done
  fi

  # Give child processes a moment to gracefully release ports
  sleep 0.5

  for pid in "${WS_SERVER_PID}" "${SNAPSHOT_PID}"; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill -KILL "$pid" 2>/dev/null || true
    fi
  done

  if command -v lsof >/dev/null 2>&1; then
    for port in 3022 8083 $(seq 8100 8150); do
      local kpids
      kpids="$(lsof -ti :${port} 2>/dev/null || true)"
      if [ -n "$kpids" ]; then
        kill -KILL $kpids 2>/dev/null || true
      fi
    done
  fi

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

# Disable immediate exit so we can inspect and log terminating process
set +e

EXIT_CODE=0
# Portable wait loop for background processes
if [ "${BASH_VERSINFO[0]}" -gt 4 ] || { [ "${BASH_VERSINFO[0]}" -eq 4 ] && [ "${BASH_VERSINFO[1]}" -ge 3 ]; }; then
  wait -n $WS_SERVER_PID $SNAPSHOT_PID
  EXIT_CODE=$?
else
  while kill -0 "$WS_SERVER_PID" 2>/dev/null && \
        kill -0 "$SNAPSHOT_PID" 2>/dev/null; do
    sleep 1
  done
fi

# Identify and log which process exited and its code
if [ -n "$WS_SERVER_PID" ] && ! kill -0 "$WS_SERVER_PID" 2>/dev/null; then
  wait "$WS_SERVER_PID" 2>/dev/null || EXIT_CODE=$?
  echo "[start.sh] Workspace WebUI process (PID: ${WS_SERVER_PID}) terminated with exit code ${EXIT_CODE}."
elif [ -n "$SNAPSHOT_PID" ] && ! kill -0 "$SNAPSHOT_PID" 2>/dev/null; then
  wait "$SNAPSHOT_PID" 2>/dev/null || EXIT_CODE=$?
  echo "[start.sh] UI Snapshot MCP Server process (PID: ${SNAPSHOT_PID}) terminated with exit code ${EXIT_CODE}."
fi

exit "$EXIT_CODE"
