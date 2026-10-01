#!/usr/bin/env bash
set -e

# ==============================================================================
# Virtual Hardware Laboratory (VHL) Unified Startup Orchestrator
# ==============================================================================

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ANSI styling
BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Ensure standard tools (uv, pnpm, node) are in PATH
export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${HOME}/Library/pnpm:${HOME}/.local/share/pnpm:/opt/homebrew/bin:${PATH}"

# Source .env if present in root workspace (do not override explicitly passed env)
if [ -f "${REPO_ROOT}/.env" ]; then
  while IFS='=' read -r key value || [ -n "$key" ]; do
    [[ "$key" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${key// }" ]] && continue
    key="$(echo "$key" | xargs)"
    value="$(echo "$value" | xargs)"
    if [ -z "${!key:-}" ]; then
      export "$key=$value"
    fi
  done < "${REPO_ROOT}/.env"
fi

# ------------------------------------------------------------------------------
# 1. Argument & Workspace Directory Handling
# ------------------------------------------------------------------------------
DRY_RUN=false
TARGET_INPUT=""

for arg in "$@"; do
  if [ "$arg" = "--dry-run" ]; then
    DRY_RUN=true
  elif [ -z "$TARGET_INPUT" ]; then
    TARGET_INPUT="$arg"
  fi
done

if [ -z "$TARGET_INPUT" ]; then
  TARGET_INPUT="${VHL_WORKSPACE_DIR:-}"
fi

if [ -n "${TARGET_INPUT}" ]; then
  if [ -d "${TARGET_INPUT}" ]; then
    RESOLVED_TARGET="$(cd "${TARGET_INPUT}" && pwd)"
  else
    mkdir -p "${TARGET_INPUT}"
    RESOLVED_TARGET="$(cd "${TARGET_INPUT}" && pwd)"
  fi
else
  DEFAULT_WORKSPACE="${REPO_ROOT}/workspace"
  mkdir -p "${DEFAULT_WORKSPACE}"
  RESOLVED_TARGET="${DEFAULT_WORKSPACE}"
fi

# Smart Project vs. Workspace Detection
is_single_project() {
  local dir="$1"
  # Standard project marker files
  if [ -f "${dir}/index.circuit.tsx" ] || [ -f "${dir}/tscircuit.config.json" ]; then
    return 0
  fi
  # VHL state database
  if [ -f "${dir}/.vhl/state.db" ]; then
    return 0
  fi
  # Project root module directory (*_root)
  if ls -d "${dir}"/*_root >/dev/null 2>&1; then
    return 0
  fi
  # Direct presence of circuit TSX or SCUD files
  if ls "${dir}"/*.circuit.tsx >/dev/null 2>&1 || ls "${dir}"/*.scud >/dev/null 2>&1; then
    return 0
  fi
  # Package with tscircuit dependency
  if [ -f "${dir}/package.json" ] && grep -q "tscircuit" "${dir}/package.json" 2>/dev/null; then
    return 0
  fi
  return 1
}

WORKSPACE_BASE="${REPO_ROOT}/workspace"

if [ "${RESOLVED_TARGET}" != "${WORKSPACE_BASE}" ] && is_single_project "${RESOLVED_TARGET}"; then
  PROJECT_NAME="$(basename "${RESOLVED_TARGET}")"
  mkdir -p "${WORKSPACE_BASE}"

  # Prune broken symlinks in workspace
  for f in "${WORKSPACE_BASE}"/*; do
    if [ -L "$f" ] && [ ! -e "$f" ]; then
      echo -e "${YELLOW}[VHL] Pruning broken symlink: ${f}${NC}"
      rm -f "$f"
    fi
  done

  # Remove any empty directories matching the project name that might have been created without contents
  TARGET_LINK="${WORKSPACE_BASE}/${PROJECT_NAME}"
  if [ -d "${TARGET_LINK}" ] && [ ! -L "${TARGET_LINK}" ]; then
    has_project_contents=false
    if ls -d "${TARGET_LINK}"/*_root >/dev/null 2>&1 || \
       ls "${TARGET_LINK}"/*.circuit.tsx >/dev/null 2>&1 || \
       ls "${TARGET_LINK}"/*.tsx >/dev/null 2>&1 || \
       ls "${TARGET_LINK}"/*.scud >/dev/null 2>&1 || \
       [ -f "${TARGET_LINK}/package.json" ]; then
      has_project_contents=true
    fi

    if [ "$has_project_contents" = false ]; then
      echo -e "${YELLOW}[VHL] Removing empty directory matching project name: ${TARGET_LINK}${NC}"
      rm -rf "${TARGET_LINK}"
    fi
  fi

  ln -sfn "${RESOLVED_TARGET}" "${TARGET_LINK}"
  export VHL_WORKSPACE_DIR="${WORKSPACE_BASE}"
  echo -e "${CYAN}[VHL] Single project detected ('${PROJECT_NAME}').${NC}"
  echo -e "${CYAN}[VHL] Symlinked into workspace: ${TARGET_LINK}${NC}"
else
  export VHL_WORKSPACE_DIR="${RESOLVED_TARGET}"
  echo -e "${CYAN}[VHL] Workspace directory configured: ${VHL_WORKSPACE_DIR}${NC}"
fi

export VHL_WS_URL="${VHL_WS_URL:-ws://localhost:1080}"

# Dry run exit after workspace and parameter validation
if [ "$DRY_RUN" = true ]; then
  echo ""
  echo -e "${YELLOW}=== DRY RUN MODE: Startup sequence simulation ===${NC}"
  echo -e "  Target input:       ${TARGET_INPUT}"
  echo -e "  Resolved workspace: ${VHL_WORKSPACE_DIR}"
  echo -e "  WebSocket URL:      ${VHL_WS_URL}"
  echo -e "  Step 1: (cd vhl-runtime && ./start.sh) [Poll ports 1080 & 3022]"
  echo -e "  Step 2: (cd vhl-agent-backend && uv run aosm) [Wait 2.5s]"
  echo -e "  Step 3: (cd vhl-webui && pnpm run dev) [Serve port 5173]"
  echo -e "${GREEN}[VHL] Dry run completed successfully.${NC}"
  exit 0
fi

# ------------------------------------------------------------------------------
# 2. Lifecycle & Teardown Management
# ------------------------------------------------------------------------------
RUNTIME_PID=""
BACKEND_PID=""
WEBUI_PID=""

cleanup() {
  local exit_code=$?
  trap - SIGINT SIGTERM EXIT
  echo ""
  echo -e "${YELLOW}[VHL] Shutting down Virtual Hardware Laboratory...${NC}"

  for pid in "${RUNTIME_PID:-}" "${BACKEND_PID:-}" "${WEBUI_PID:-}"; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill -TERM "$pid" 2>/dev/null || true
    fi
  done

  # Brief pause to allow graceful termination
  sleep 1.5

  for pid in "${RUNTIME_PID:-}" "${BACKEND_PID:-}" "${WEBUI_PID:-}"; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill -KILL "$pid" 2>/dev/null || true
    fi
  done

  # Guarantee ports (1080, 3022, 5173, 8082, 8083) are completely freed
  if command -v lsof >/dev/null 2>&1; then
    for port in 1080 3022 5173 8082 8083; do
      local pids
      pids="$(lsof -ti :${port} 2>/dev/null || true)"
      if [ -n "$pids" ]; then
        kill -9 $pids 2>/dev/null || true
      fi
    done
  fi
  pkill -9 -f "bin/aosm" 2>/dev/null || true
  pkill -9 -f "wsIndex.js" 2>/dev/null || true
  pkill -9 -f "terminal_server.py" 2>/dev/null || true

  echo -e "${GREEN}[VHL] All VHL services stopped cleanly.${NC}"
  exit "$exit_code"
}

trap cleanup SIGINT SIGTERM EXIT

# Release any stale processes on VHL ports before starting
if command -v lsof >/dev/null 2>&1; then
  for port in 1080 3022 5173 8082 8083; do
    stale_pids="$(lsof -ti :${port} 2>/dev/null || true)"
    if [ -n "$stale_pids" ]; then
      echo -e "${YELLOW}[VHL] Releasing occupied port ${port} (PID: ${stale_pids})...${NC}"
      kill -9 $stale_pids 2>/dev/null || true
    fi
  done
fi
pkill -9 -f "bin/aosm" 2>/dev/null || true
pkill -9 -f "wsIndex.js" 2>/dev/null || true
pkill -9 -f "terminal_server.py" 2>/dev/null || true

# Port check helper
wait_for_port() {
  local port="$1"
  local desc="$2"
  local timeout="${3:-30}"
  local start_time
  start_time="$(date +%s)"

  echo -n -e "${BLUE}[VHL] Waiting for ${desc} on port ${port}...${NC} "
  while true; do
    if python3 -c "import socket; s = socket.socket(); s.settimeout(0.5); exit(0 if s.connect_ex(('127.0.0.1', ${port})) == 0 else 1)" 2>/dev/null; then
      echo -e "${GREEN}READY${NC}"
      return 0
    fi

    # Abort early if runtime crashed
    if [ -n "${RUNTIME_PID:-}" ] && ! kill -0 "${RUNTIME_PID}" 2>/dev/null; then
      echo -e "${RED}FAILED (Runtime process ${RUNTIME_PID} exited unexpectedly)${NC}"
      return 1
    fi

    local current_time
    current_time="$(date +%s)"
    if [ $((current_time - start_time)) -ge "$timeout" ]; then
      echo -e "${RED}TIMEOUT after ${timeout}s${NC}"
      echo -e "${RED}Error: ${desc} on port ${port} did not start within ${timeout} seconds.${NC}" >&2
      return 1
    fi
    sleep 0.5
  done
}

# ------------------------------------------------------------------------------
# 3. Strict Module Startup Sequence
# ------------------------------------------------------------------------------

# Step 1: Start vhl-runtime
echo -e "${BOLD}${BLUE}=== Step 1: Starting vhl-runtime ===${NC}"
(cd "${REPO_ROOT}/vhl-runtime" && ./start.sh) &
RUNTIME_PID=$!

wait_for_port 1080 "Agent WebSocket Relay" 30
wait_for_port 3022 "Express WebUI API" 30

# Step 2: Start vhl-agent-backend
echo -e "${BOLD}${BLUE}=== Step 2: Starting vhl-agent-backend (AOSM) ===${NC}"
UV_CMD="uv"
if ! command -v uv >/dev/null 2>&1; then
  if [ -x "${HOME}/.local/bin/uv" ]; then
    UV_CMD="${HOME}/.local/bin/uv"
  elif [ -x "${HOME}/.cargo/bin/uv" ]; then
    UV_CMD="${HOME}/.cargo/bin/uv"
  else
    echo -e "${RED}Error: 'uv' is required to run vhl-agent-backend but was not found in PATH or ~/.local/bin.${NC}" >&2
    exit 1
  fi
fi

(cd "${REPO_ROOT}/vhl-agent-backend" && "${UV_CMD}" run aosm) &
BACKEND_PID=$!
echo -e "${BLUE}[VHL] Waiting 2.5s for AOSM connection to settle...${NC}"
sleep 2.5

if ! kill -0 "${BACKEND_PID}" 2>/dev/null; then
  echo -e "${RED}Error: vhl-agent-backend exited unexpectedly.${NC}" >&2
  exit 1
fi
echo -e "${GREEN}[VHL] vhl-agent-backend connected to relay successfully.${NC}"

# Step 3: Start vhl-webui
echo -e "${BOLD}${BLUE}=== Step 3: Starting vhl-webui ===${NC}"
PNPM_CMD="pnpm"
if ! command -v pnpm >/dev/null 2>&1; then
  if [ -x "${HOME}/Library/pnpm/pnpm" ]; then
    PNPM_CMD="${HOME}/Library/pnpm/pnpm"
  elif [ -x "${HOME}/.local/share/pnpm/pnpm" ]; then
    PNPM_CMD="${HOME}/.local/share/pnpm/pnpm"
  fi
fi

(cd "${REPO_ROOT}/vhl-webui" && "${PNPM_CMD}" run dev) &
WEBUI_PID=$!
sleep 2

# ------------------------------------------------------------------------------
# 4. Service Dashboard Banner
# ------------------------------------------------------------------------------
echo ""
echo -e "${GREEN}==============================================================================${NC}"
echo -e "${GREEN}${BOLD}       Virtual Hardware Laboratory (VHL) Services Active${NC}"
echo -e "${GREEN}==============================================================================${NC}"
echo -e "  ${BOLD}Workspace Directory:${NC}  ${VHL_WORKSPACE_DIR}"
echo -e "  ${BOLD}WebUI Cockpit:${NC}        ${CYAN}http://localhost:5173${NC}"
echo -e "  ${BOLD}Runtime Express API:${NC}  ${CYAN}http://localhost:3022${NC}"
echo -e "  ${BOLD}Agent WS Relay Hub:${NC}   ${CYAN}ws://localhost:1080${NC}"
echo -e "  ${BOLD}Terminal MCP Server:${NC}  ${CYAN}http://localhost:8082/sse${NC}"
echo -e "  ${BOLD}UI Snapshot Server:${NC}   ${CYAN}http://localhost:8083${NC}"
echo -e "${GREEN}==============================================================================${NC}"
echo -e "${YELLOW}Press [Ctrl+C] to gracefully stop all VHL services.${NC}"
echo ""

# ------------------------------------------------------------------------------
# 5. Portable Wait Loop
# ------------------------------------------------------------------------------
# On Bash >= 4.3, 'wait -n' awaits the first process exit.
# On macOS /bin/bash (v3.2), poll process health every second.
if [ "${BASH_VERSINFO[0]}" -gt 4 ] || { [ "${BASH_VERSINFO[0]}" -eq 4 ] && [ "${BASH_VERSINFO[1]}" -ge 3 ]; }; then
  wait -n "$RUNTIME_PID" "$BACKEND_PID" "$WEBUI_PID"
else
  while kill -0 "$RUNTIME_PID" 2>/dev/null && \
        kill -0 "$BACKEND_PID" 2>/dev/null && \
        kill -0 "$WEBUI_PID" 2>/dev/null; do
    sleep 1
  done
fi

exit $?
