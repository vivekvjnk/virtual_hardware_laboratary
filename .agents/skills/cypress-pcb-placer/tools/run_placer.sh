#!/usr/bin/env bash
# Execution wrapper for Cypress Placer engine inside container environment
# Usage: ./tools/run_placer.sh <config_json_path>

set -e

CONFIG_FILE="${1:-configs/test_small1.json}"

echo "=========================================================="
echo "Starting Cypress Global Placement Optimization"
echo "Config File: ${CONFIG_FILE}"
echo "=========================================================="

# Ensure unbuffered python output for real-time telemetry streaming
export PYTHONUNBUFFERED=1

if [ -f "dreamplace/Placer.py" ]; then
    python3 -u dreamplace/Placer.py "${CONFIG_FILE}"
else
    echo "Error: dreamplace/Placer.py not found in current directory."
    echo "Ensure you are running inside the Cypress repository workspace."
    exit 1
fi
