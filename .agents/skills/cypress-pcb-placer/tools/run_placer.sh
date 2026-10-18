#!/usr/bin/env bash
# Execution wrapper for Cypress Placer engine supporting local & Google Colab GPU delegation
# Usage: ./tools/run_placer.sh [options] <config_json_path> [output_dir]

set -e

print_usage() {
    cat << EOF
Usage: $(basename "$0") [options] <config_json_path> [output_dir]

Executes Cypress PCB placement either locally or via cloud GPU worker on Google Colab.

Arguments:
  <config_json_path>        Path to Cypress placement JSON configuration file
  [output_dir]              Directory to store results (default: derived from config or ./results)

Options:
  --remote <rclone_target>  rclone remote target (e.g. 'cypress_runtime:cypress_colab_runtime')
                            Defaults to \$CYPRESS_RCLONE_REMOTE if set.
  --local                   Force local execution using dreamplace/Placer.py
  --name <job_name>         Explicit job name for queue tracking (default: auto-generated)
  --aux <aux_path>          Explicit path to Bookshelf .aux file (if not in config)
  --submit-script <path>    Path to submit_job.py script
  --dry-run                 Validate configuration and display execution plan without dispatching
  -h, --help                Show this help message

Environment Variables:
  CYPRESS_RCLONE_REMOTE     Default rclone remote target for Colab delegation
                            (e.g. 'cypress_runtime:cypress_colab_runtime')
  CYPRESS_SUBMIT_SCRIPT     Custom path to submit_job.py

Examples:
  # Remote Colab GPU execution using default remote:
  ./tools/run_placer.sh configs/power_circuit.json ./results

  # Explicit remote specification:
  ./tools/run_placer.sh --remote cypress_runtime:cypress_colab_runtime configs/control_circuit.json

  # Local container execution:
  ./tools/run_placer.sh --local configs/test_small1.json
EOF
}

CONFIG_FILE=""
OUT_DIR=""
JOB_NAME=""
AUX_FILE=""
REMOTE="${CYPRESS_RCLONE_REMOTE:-cypress_runtime:cypress_colab_runtime}"
FORCE_LOCAL=0
DRY_RUN=0
SUBMIT_SCRIPT="${CYPRESS_SUBMIT_SCRIPT:-/Users/vivek/Virtual_Labs/cypress-colab-runner/scripts/submit_job.py}"

# Parse command line options
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            print_usage
            exit 0
            ;;
        --remote)
            REMOTE="$2"
            shift 2
            ;;
        --local)
            FORCE_LOCAL=1
            REMOTE=""
            shift
            ;;
        --name)
            JOB_NAME="$2"
            shift 2
            ;;
        --aux)
            AUX_FILE="$2"
            shift 2
            ;;
        --submit-script)
            SUBMIT_SCRIPT="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        -*)
            echo "Error: Unknown option '$1'" >&2
            print_usage
            exit 1
            ;;
        *)
            if [ -z "$CONFIG_FILE" ]; then
                CONFIG_FILE="$1"
            elif [ -z "$OUT_DIR" ]; then
                OUT_DIR="$1"
            else
                echo "Error: Unexpected argument '$1'" >&2
                exit 1
            fi
            shift
            ;;
    esac
done

if [ -z "$CONFIG_FILE" ]; then
    echo "Error: Missing required <config_json_path> argument." >&2
    print_usage
    exit 1
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Configuration file not found: '$CONFIG_FILE'" >&2
    exit 1
fi

# Resolve output directory
if [ -z "$OUT_DIR" ]; then
    # Try reading result_dir from config json if python is available
    OUT_DIR=$(python3 -c "
import json, sys
try:
    with open('$CONFIG_FILE') as f:
        cfg = json.load(f)
    print(cfg.get('result_dir', cfg.get('output_dir', '')))
except:
    pass
" 2>/dev/null || true)
fi

if [ -z "$OUT_DIR" ]; then
    OUT_DIR="$(dirname "$CONFIG_FILE")/results"
fi

mkdir -p "$OUT_DIR"
OUT_DIR="$(cd "$OUT_DIR" && pwd)"

# Generate job name if not set
if [ -z "$JOB_NAME" ]; then
    CFG_BASE=$(basename "${CONFIG_FILE%.*}")
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    RAND_SUFFIX=$((RANDOM % 9000 + 1000))
    JOB_NAME="${CFG_BASE}_${TIMESTAMP}_${RAND_SUFFIX}"
fi

echo "=========================================================="
echo "       CYPRESS GLOBAL PLACEMENT OPTIMIZATION              "
echo "=========================================================="
echo "Config File:  $CONFIG_FILE"
echo "Job Name:     $JOB_NAME"
echo "Output Dir:   $OUT_DIR"

# Decide between Remote Colab GPU execution vs Local execution
if [ "$FORCE_LOCAL" -eq 1 ] || [ -z "$REMOTE" ]; then
    if [ -f "dreamplace/Placer.py" ]; then
        echo "Execution:    Local (dreamplace/Placer.py)"
        echo "=========================================================="
        if [ "$DRY_RUN" -eq 1 ]; then
            echo "[DRY-RUN] Would execute: python3 -u dreamplace/Placer.py '$CONFIG_FILE'"
            exit 0
        fi
        export PYTHONUNBUFFERED=1
        python3 -u dreamplace/Placer.py "$CONFIG_FILE"
        exit 0
    else
        echo "Error: Local dreamplace/Placer.py not found in current directory." >&2
        echo "To use Google Colab GPU delegation, set CYPRESS_RCLONE_REMOTE or provide --remote <rclone_target>." >&2
        exit 1
    fi
fi

# Remote Google Colab GPU Delegation
echo "Execution:    Remote Colab GPU Delegation via rclone"
echo "Remote:       $REMOTE"
echo "Submit Tool:  $SUBMIT_SCRIPT"
echo "=========================================================="

if [ "$DRY_RUN" -eq 1 ]; then
    echo "[DRY-RUN] Remote delegation configuration verified:"
    echo "  - Config:  $CONFIG_FILE"
    echo "  - Remote:  $REMOTE"
    echo "  - Script:  $SUBMIT_SCRIPT"
    echo "  - Job:     $JOB_NAME"
    echo "  - Out Dir: $OUT_DIR"
    exit 0
fi

if [ ! -f "$SUBMIT_SCRIPT" ]; then
    echo "Error: submit_job.py not found at '$SUBMIT_SCRIPT'" >&2
    echo "Ensure cypress-colab-runner repository is installed or set CYPRESS_SUBMIT_SCRIPT." >&2
    exit 1
fi

STAGING_DIR=$(mktemp -d -t "cypress_placer_out_XXXXXX")
trap 'rm -rf "$STAGING_DIR"' EXIT

SUBMIT_ARGS=(
    "$SUBMIT_SCRIPT"
    "--rclone" "$REMOTE"
    "--config" "$CONFIG_FILE"
    "--name" "$JOB_NAME"
    "--wait"
    "--out-dir" "$STAGING_DIR"
)

if [ -n "$AUX_FILE" ]; then
    SUBMIT_ARGS+=("--aux" "$AUX_FILE")
fi

echo "[PLACER] Dispatching job to Google Colab and streaming telemetry..."
python3 -u "${SUBMIT_ARGS[@]}"

# Copy downloaded artifacts from staging to requested OUT_DIR
JOB_RESULT_DIR="$STAGING_DIR/$JOB_NAME"
if [ -d "$JOB_RESULT_DIR" ]; then
    echo "[PLACER] Consolidating artifacts into '$OUT_DIR'..."
    cp -r "$JOB_RESULT_DIR"/* "$OUT_DIR/" 2>/dev/null || true
    
    # Copy DREAMPlace.log to current working directory if not already there
    if [ -f "$JOB_RESULT_DIR/DREAMPlace.log" ] && [ ! -f "./DREAMPlace.log" ]; then
        cp "$JOB_RESULT_DIR/DREAMPlace.log" "./DREAMPlace.log" 2>/dev/null || true
    fi

    echo "=========================================================="
    echo "✔ Placement Optimization Complete"
    echo "Results Directory: $OUT_DIR"
    if ls "$OUT_DIR"/*.gp.pl 1>/dev/null 2>&1; then
        echo "Placement Output:  $(ls "$OUT_DIR"/*.gp.pl)"
    fi
    echo "=========================================================="
else
    echo "Warning: No job result directory found at '$JOB_RESULT_DIR'" >&2
fi
