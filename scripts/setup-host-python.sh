#!/usr/bin/env bash
set -euo pipefail

# Determine directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${RUNTIME_DIR}/.venv"
REQUIREMENTS_FILE="${RUNTIME_DIR}/requirements.txt"
OH_SDK_DIR="${RUNTIME_DIR}/packages/oh-sdk"
OH_TOOLS_DIR="${RUNTIME_DIR}/packages/oh-tools"

echo "=== VHL Runtime Host Python Setup ==="
echo "Runtime directory: ${RUNTIME_DIR}"
echo "Target venv:       ${VENV_DIR}"

# 1. Detect uv or Python 3 (>= 3.10)
UV_BIN=""
if command -v uv >/dev/null 2>&1; then
  UV_BIN="$(command -v uv)"
elif [ -x "${HOME}/.local/bin/uv" ]; then
  UV_BIN="${HOME}/.local/bin/uv"
elif [ -x "${HOME}/.cargo/bin/uv" ]; then
  UV_BIN="${HOME}/.cargo/bin/uv"
fi

check_python_version() {
  local py_bin="$1"
  if [ -x "$py_bin" ] || command -v "$py_bin" >/dev/null 2>&1; then
    if "$py_bin" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >/dev/null 2>&1; then
      return 0
    fi
  fi
  return 1
}

PYTHON_BIN=""
# Check user override first
if [ -n "${VHL_PYTHON_BIN:-}" ] && check_python_version "${VHL_PYTHON_BIN}"; then
  PYTHON_BIN="${VHL_PYTHON_BIN}"
fi

# If no user override or invalid, search candidates if uv is not available
if [ -z "${PYTHON_BIN}" ]; then
  for candidate in python3 python3.13 python3.12 python3.11 python3.10 python; do
    if check_python_version "$candidate"; then
      PYTHON_BIN="$(command -v "$candidate")"
      break
    fi
  done
fi

if [ -z "${UV_BIN}" ] && [ -z "${PYTHON_BIN}" ]; then
  echo "Error: Neither 'uv' nor a compatible Python 3 (>= 3.10) executable was found." >&2
  echo "Please install Python 3.10+ or uv (https://github.com/astral-sh/uv), or set VHL_PYTHON_BIN." >&2
  exit 1
fi

if [ -n "${UV_BIN}" ]; then
  echo "Found uv: ${UV_BIN} ($("${UV_BIN}" --version))"
fi
if [ -n "${PYTHON_BIN}" ]; then
  echo "Found Python: ${PYTHON_BIN} ($("${PYTHON_BIN}" --version 2>&1))"
fi

# 2. Create virtual environment if not present
if [ -d "${VENV_DIR}" ] && [ -x "${VENV_DIR}/bin/python" ]; then
  echo "Virtual environment already exists at ${VENV_DIR}"
else
  echo "Creating virtual environment at ${VENV_DIR}..."
  if [ -n "${UV_BIN}" ]; then
    if [ -n "${PYTHON_BIN}" ]; then
      "${UV_BIN}" venv "${VENV_DIR}" --python "${PYTHON_BIN}"
    else
      "${UV_BIN}" venv "${VENV_DIR}" --python ">=3.10"
    fi
  else
    "${PYTHON_BIN}" -m venv "${VENV_DIR}"
  fi
fi

VENV_PYTHON="${VENV_DIR}/bin/python"
if [ ! -x "${VENV_PYTHON}" ]; then
  echo "Error: Virtual environment python binary not found at ${VENV_PYTHON}" >&2
  exit 1
fi

# 3. Install dependencies
echo "Installing dependencies..."
if [ -n "${UV_BIN}" ]; then
  echo "--> Installing requirements from requirements.txt via uv..."
  "${UV_BIN}" pip install --python "${VENV_PYTHON}" -r "${REQUIREMENTS_FILE}"

  echo "--> Installing editable package: openhands-sdk via uv..."
  "${UV_BIN}" pip install --python "${VENV_PYTHON}" -e "${OH_SDK_DIR}"

  echo "--> Installing editable package: openhands-tools (--no-deps) via uv..."
  "${UV_BIN}" pip install --python "${VENV_PYTHON}" --no-deps -e "${OH_TOOLS_DIR}"
else
  echo "--> Upgrading pip..."
  "${VENV_PYTHON}" -m pip install --upgrade pip

  echo "--> Installing requirements from requirements.txt via pip..."
  "${VENV_PYTHON}" -m pip install -r "${REQUIREMENTS_FILE}"

  echo "--> Installing editable package: openhands-sdk via pip..."
  "${VENV_PYTHON}" -m pip install -e "${OH_SDK_DIR}"

  echo "--> Installing editable package: openhands-tools (--no-deps) via pip..."
  "${VENV_PYTHON}" -m pip install --no-deps -e "${OH_TOOLS_DIR}"
fi

# 4. Verify installation
echo "Verifying Python environment..."
"${VENV_PYTHON}" -c "import fastmcp, starlette, openhands.sdk, openhands.tools; print('Host Python environment verification: SUCCESS')"

echo "=== VHL Runtime Host Python Setup Complete ==="
