#!/usr/bin/env bash
# Execution wrapper for Cypress MOTPE hyperparameter tuner
# Usage: ./tools/run_placer_tuner.sh <config_space_json> <aux_file_path> <ppa_json> <results_dir>

set -e

CONFIG_SPACE="${1:-test/tune/pcb-configspace.json}"
AUX_FILE="${2}"
PPA_JSON="${3:-test/tuner/tuner-ppa.json}"
RESULTS_DIR="${4:-./results/tuning_out}"

if [ -z "${AUX_FILE}" ]; then
    echo "Usage: $0 <config_space_json> <aux_file_path> <ppa_json> <results_dir>"
    exit 1
fi

echo "=========================================================="
echo "Starting Cypress MOTPE Hyperparameter Search"
echo "Aux File: ${AUX_FILE}"
echo "Results Dir: ${RESULTS_DIR}"
echo "=========================================================="

./tuner/run_tuner.sh 1 1 "${CONFIG_SPACE}" "${AUX_FILE}" "${PPA_JSON}" "" 100 4 0 0 10 ./tuner "${RESULTS_DIR}"
