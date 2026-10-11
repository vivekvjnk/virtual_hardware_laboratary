# Cypress Environment & Tool Troubleshooting Reference

This document provides guidance on execution environments, container setups, and troubleshooting rules for the Cypress GPU placement framework.

---

## 1. Execution Environment & Tool Integration

Cypress requires GPU acceleration (CUDA) and compiled C++/CUDA shared libraries (`dreamplace/ops/*.so`).

> **Crucial Rule**: Cypress MUST be executed inside its dedicated Docker container environment. Host machine builds or host Python virtual environments (`uv`/`venv`) will fail due to C++ ABI and library dependencies.

### Repository Context & Tool Developer Documentation
For full details on building container images, CMake setup, compilation steps, and ABI flags, refer to the Cypress repository operational documentation:
- Relative path from skill directory: `../../../../open-source-repos/Cypress/AGENTS.md` (or repo root `AGENTS.md` inside Cypress repository workspace).

---

## 2. Docker Execution Procedure

1. **Verify NVIDIA GPU Visibility**:
   ```bash
   nvidia-smi
   ```
2. **Launch & Attach Container** (from Cypress repo root):
   ```bash
   docker compose up -d
   docker exec -it <container_id_or_name> /bin/bash
   ```

---

## 3. Common Compilation & Runtime Troubleshooting

### A. Undefined Symbol / ABI Mismatch Errors
* **Symptom**: Import error when loading operators (e.g., `undefined symbol: _ZN3c106detail14torchCheckFail...`).
* **Root Cause**: PyTorch CXX11 ABI mismatch between host compiler flags and container PyTorch build.
* **Resolution**:
  1. Remove compiled shared libraries:
     ```bash
     find dreamplace/ops/ -name "*.so" -type f -delete
     ```
  2. Check PyTorch ABI inside container:
     ```bash
     python3 -c "import torch; print('PyTorch CXX11 ABI:', torch._C._GLIBCXX_USE_CXX11_ABI)"
     ```
  3. Rebuild inside container:
     ```bash
     rm -rf build && mkdir build && cd build
     cmake .. -DCMAKE_INSTALL_PREFIX=../
     make -j$(nproc) && make install
     ```

### B. Output Buffer Delays
* **Symptom**: `DREAMPlace.log` or execution log files remain empty during long runs.
* **Resolution**: Execute python with unbuffered output flag (`-u`):
  ```bash
  PYTHONUNBUFFERED=1 python3 -u dreamplace/Placer.py configs/your_config.json > run.log 2>&1
  ```
