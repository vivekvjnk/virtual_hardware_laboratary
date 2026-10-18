---
name: cypress-pcb-placer
description: Systematically executes, diagnoses, and tunes Cypress GPU-accelerated PCB component placement optimization runs. Supports transparent cloud GPU delegation to Google Colab T4 runtimes via rclone, manages Bookshelf /FIXED anchor placement, resolves density and wirelength divergence, and applies the 4-regime diagnostic decision tree.
license: Apache-2.0
metadata:
  author: MOSAIC-Team
  version: "1.0"
  category: pcb-placement
  tags:
    - pcb-placement
    - cypress
    - colab-gpu
    - rclone
    - fixed-anchors
    - dreamplace
    - hyperparameter-tuning
---

# Cypress PCB Placer

This capability package provides operational knowledge and systematic diagnostic decision procedures to execute component placement optimization and hyperparameter tuning using the **Cypress PCB Placement Framework**. It supports transparent **cloud GPU delegation via Google Colab** (backed by NVIDIA T4 GPUs) over `rclone`, as well as local container execution.

---

## 1. Cloud GPU Delegation Architecture (Google Colab via rclone)

Because non-linear electrostatic PCB placement requires CUDA GPU acceleration (PyTorch + custom CUDA operators), the execution wrapper `tools/run_placer.sh` can delegate computation to a remote Google Colab GPU runtime via Google Drive:

```text
┌─────────────────────────────────┐
│ Host Workspace (run_placer.sh)  │
│  • Reads <design>.json & .aux   │
│  • Prepares job bundle          │
└───────────────┬─────────────────┘
                │ rclone copy
                ▼
┌─────────────────────────────────────────────────────────┐
│ Google Drive (CYPRESS_RCLONE_REMOTE)                    │
│   cypress_colab_runtime/queue/<job_name>/               │
│     ├── config.json, .nodes, .nets, .pl, .scl, .aux     │
│     └── READY                                           │
└───────────────┬─────────────────────────────────────────┘
                │ Polled by Colab worker
                ▼
┌─────────────────────────────────────────────────────────┐
│ Google Colab Cloud GPU Worker (T4 / A100)               │
│   Cypress_Colab_Runner.ipynb                            │
│     • Runs Cypress DREAMPlace GPU Placement             │
│     • Emits <design>.gp.pl, DREAMPlace.log, plots       │
│     • Moves bundle to completed/<job_name>/             │
└───────────────┬─────────────────────────────────────────┘
                │ Polled by host submit_job.py
                ▼
┌─────────────────────────────────┐
│ Host Workspace (run_placer.sh)  │
│  • Downloads completed results  │
│  • Consolidates .gp.pl & logs   │
│  • Hands off to back-annotation │
└─────────────────────────────────┘
```

---

## 2. Prerequisites for Cloud GPU Delegation

Before dispatching placement jobs to Google Colab, verify all three prerequisites:

### Prerequisite 1: Colab Worker Running in Cloud
1. Open the runner notebook **`Cypress_Colab_Runner.ipynb`** (located under `cypress-colab-runner/notebooks/`) in Google Colab.
2. Ensure the Colab runtime type is configured to **GPU (T4 or higher)** (`Runtime` $\rightarrow$ `Change runtime type` $\rightarrow$ `T4 GPU`).
3. Run all cells to initialize the Cypress SIF/Singularity environment and start the continuous queue worker:
   ```text
   [WORKER] Watching cypress_colab_runtime/queue/ for incoming jobs...
   ```

### Prerequisite 2: Host Machine rclone Authentication
1. `rclone` must be installed on the host machine (`which rclone`).
2. An rclone remote pointing to Google Drive must be configured (typically named `cypress_runtime:`):
   ```bash
   rclone listremotes
   # Output must contain: cypress_runtime:
   ```

### Prerequisite 3: Environment Variable Configured
Set the default remote target path in your shell or `.env`:
```bash
export CYPRESS_RCLONE_REMOTE="cypress_runtime:cypress_colab_runtime"
```

---

## 3. Operational Tool Usage

The core execution wrapper is bundled in `tools/run_placer.sh`:

```bash
tools/run_placer.sh [options] <config_json_path> [output_dir]
```

### Key Parameters:
- `<config_json_path>`: Path to Cypress placement configuration JSON.
- `[output_dir]`: Target directory to consolidate placement outputs (`.gp.pl`, `DREAMPlace.log`, plots). Defaults to the directory specified in config or `./results`.
- `--remote <rclone_target>`: Overrides rclone remote target (defaults to `$CYPRESS_RCLONE_REMOTE`).
- `--local`: Forces local container execution using `dreamplace/Placer.py`.
- `--dry-run`: Validates configuration and displays execution plan without dispatching.
- `--name <job_name>`: Explicit job identifier for queue tracking.

### Invocation Examples

1. **Standard Remote Colab Placement**:
   ```bash
   .agents/skills/cypress-pcb-placer/tools/run_placer.sh configs/power_circuit.json ./results
   ```

2. **Dry-Run Validation**:
   ```bash
   .agents/skills/cypress-pcb-placer/tools/run_placer.sh --dry-run configs/control_circuit.json
   ```

3. **Hyperparameter Tuning (MOTPE Search)**:
   ```bash
   tools/run_placer_tuner.sh <config_space_json> <aux_file_path> <ppa_json> <results_dir>
   ```

---

## 4. Telemetry Streaming & Back-Annotation Handoff

When a job is dispatched via `tools/run_placer.sh`:
1. The tool packages the configuration and all referenced Bookshelf files (`.aux`, `.nodes`, `.nets`, `.pl`, `.scl`).
2. Transmits the payload to `CYPRESS_RCLONE_REMOTE/queue/<job_name>` on Google Drive.
3. Automatically streams completion status and telemetry to the terminal.
4. Downloads the output package into `output_dir/` upon completion:
   - `<design_name>.gp.pl`: Placed coordinates file.
   - `DREAMPlace.log`: Convergence and density telemetry.
   - `summary.json`: Timing, HPWL, and overflow metrics.
   - Optimization curves and layout render images.

### Back-Annotation into Circuit TSX / Circuit JSON:
Once `<design_name>.gp.pl` is generated, hand off to `circuitjson-bookshelf-converter` to update coordinates:
```bash
python3 .agents/skills/circuitjson-bookshelf-converter/tools/matrix_converter.py from_bookshelf_pcb \
  path/to/original_circuit.json \
  results/<design_name>.gp.pl \
  path/to/placed_circuit.json
```

---

## 5. Bookshelf `/FIXED` Anchor Placement Protocol

In physical PCB layout synthesis, certain critical components must maintain immutable positions defined by external boundaries, mounting mechanics, or isolation zones:

### Locking Anchor Components:
In the Bookshelf placement file (`<design_name>.pl`), components designated as fixed anchors carry the `/FIXED` attribute:
```text
# Bookshelf .pl format with fixed anchors
U1 45000 35000 : N
U2 80000 35000 : N
J1 5000 5000 : N /FIXED
J2 95000 5000 : N /FIXED
MOUNTING_HOLE_1 2000 2000 : N /FIXED
MOUNTING_HOLE_2 98000 48000 : N /FIXED
```

### Invariants for Fixed Components:
1. **Perimeter Connectors & Edge Ports**: Must carry `/FIXED` at physical board perimeter coordinates to prevent the placer from dragging headers into the board interior.
2. **Thermal & High-Voltage Keep-outs**: High-voltage switching devices or isolated ground barriers can be anchored with `/FIXED` to enforce physical clearances.
3. **Movable Macros**: All standard ICs, discrete passives, and bypass capacitors omit `/FIXED` and are freely optimized by the non-linear electrostatic placer.

---

## 6. Four-Regime Diagnostic Decision Tree

When evaluating real-time placement runs, inspect `DREAMPlace.log` telemetry to identify the optimization regime and apply targeted parameter adjustments in your JSON configuration:

```text
                  Observe Optimization Telemetry
                               │
       ┌───────────────────────┼───────────────────────┐
       ▼                       ▼                       ▼
 Regime A: Divergence     Regime B: Clumping    Regime C: Wire Crossings
(Gradient Explosion)    (Overflow Stalled)     (Poor Routability)
       │                       │                       │
       ▼                       ▼                       ▼
• γ ↑ (4.0 → 10.0)      • λ_D ↑ (1e-6 → 8e-5)   • enable_rotation: 1
• lr ↓ (0.01 → 0.002)   • opt: nesterov         • net_crossing_flag: 1
• static weights        • enable_fillers: 0*    • Early orient trigger
```

### Regime A: Gradient Explosion & Divergence
* **Observable Symptoms**: Log reports `Obj INF`, `NaN` gradients, HPWL exploding ($> 10^7$), or components pushed far outside board boundaries.
* **Prescribed Adjustments**:
  1. **Increase Base Wirelength Scale ($\gamma$)**: Raise base `"gamma"` from `4.0` to `10.0` or `20.0` in the JSON config.
  2. **Disable Net Crossing During Initial Spreading**: Set `"net_crossing_flag": 0` during early global placement.
  3. **Reduce Learning Rate**: Lower `"learning_rate"` in `global_place_stages` from `0.01` to `0.002` or `0.005`.

### Regime B: Component Overlap & Stalled Overflow
* **Observable Symptoms**: Global placement terminates prematurely or stalls with high overflow ($\text{Overflow} > 0.1$), leaving cell clusters overlapping.
* **Prescribed Adjustments**:
  1. **Increase Initial Density Multiplier**: Boost `"density_weight"` from `1e-6` to `8e-5` or `1e-3`.
  2. **Switch Optimizer to Nesterov**: Set `"optimizer": "nesterov"` with `"learning_rate": 0.01`.
  3. **Disable Fillers for Macro-Only PCB Layouts**: Set `"enable_fillers": 0` if all components are movable macros on sparse PCB boards.

### Regime C: Excessive Net Crossings & Poor Routability
* **Observable Symptoms**: High net crossing penalties or trace congestion despite low density overflow.
* **Prescribed Adjustments**:
  1. **Enable Rotation Optimization**: Set `"enable_rotation": 1` to execute continuous orientation relaxation ($\theta \in \{0^\circ, 90^\circ, 180^\circ, 270^\circ\}$).
  2. **Two-Phase Net Crossing Strategy**: Phase 1 run with `"net_crossing_flag": 0`; Phase 2 enable `"net_crossing_flag": 1` once overflow drops below `0.10`.

### Regime D: Local Minima Trapping
* **Observable Symptoms**: Rapid convergence yielding high HPWL and asymmetric macro distribution.
* **Prescribed Adjustments**:
  1. Enable `"random_center_init_flag": 1` and increase `"gp_noise_ratio"` to `0.05`.

---

## 7. Verification

A placement run is verified and considered successful when all of the following criteria are met:

1. **Clean Optimization Convergence**: Optimization completes without `NaN` loss or floating-point exceptions in `DREAMPlace.log`.
2. **Target Density Overflow Reached**: Final normalized density overflow drops below the termination threshold ($\text{Overflow} \le 0.07$).
3. **Valid Bounding Box Constraints**: Final component coordinates lie strictly within the physical board outline $[0, W_{\text{board}}] \times [0, H_{\text{board}}]$.
4. **Anchor Invariant Preserved**: All `/FIXED` components maintain their exact initial coordinates without drift.
5. **Discrete Legal Angles**: Final exported component rotations are locked to valid discrete orientation angles $\theta \in \{0^\circ, 90^\circ, 180^\circ, 270^\circ\}$.
