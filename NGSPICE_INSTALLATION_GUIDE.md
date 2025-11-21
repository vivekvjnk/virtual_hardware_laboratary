
# ngspice Installation Guide

This document outlines the steps to install and test ngspice on a Debian-based system, such as the one used in the workspace environment.

## 1. Update Package List

First, update the package list to ensure you get the latest versions of software.

```bash
sudo apt update
```

## 2. Install ngspice

Install ngspice using the `apt` package manager.

```bash
sudo apt install ngspice
```

## 3. Verify Installation

After installation, you can verify that ngspice is installed and accessible by checking its version or running a simple test.

```bash
which ngspice
ngspice --version
```

## 4. Test ngspice with a Simple Circuit Simulation

Create a test circuit file (e.g., `test_circuit.cir`) with the following content:

```
* Simple RC circuit
V1 1 0 DC 5V
R1 1 2 1k
C1 2 0 1uF

.control
tran 10u 10m
print V(1) V(2)
.endc

.end
```

Run the simulation using ngspice:

```bash
ngspice -b test_circuit.cir
```

If the simulation runs successfully and outputs transient analysis data for V(1) and V(2), then ngspice is correctly installed and configured.

## 5. Parameterized Subcircuits and Impedance Extraction

When dealing with parameterized subcircuits in ngspice, direct parameter passing in the subcircuit instantiation line (`X_cell 100 0 RandlesCell 0.01 0.1 1m 0.05`) can sometimes be problematic and lead to "Too few parameters" or "unknown subckt" errors, depending on the ngspice version or specific syntax requirements.

A robust workaround is to define global parameters using the `.param` directive *outside* the subcircuit definitions, and then reference these parameters within the subcircuit using curly braces `{}`.

### Example for Randles Cell:

```spice
.param Ru_val = 0.01
.param Rct_val = 0.1
.param Cdl_val = 1m
.param Wsig_val = 0.05

.subckt RandlesCell P N
R_u P 1 {Ru_val}
C_dl 1 2 {Cdl_val}
R_ct 2 3 {Rct_val}
X_warburg 3 N Warburg
.ends
```

To extract impedance data from an AC analysis, you can use a `.control` block. Remember to use `ph(Z)` for phase calculation, as `pha(Z)` might not be supported in some ngspice versions.

### Example for Impedance Extraction:

```spice
V_source 100 0 AC 1V
X_cell 100 0 RandlesCell

.ac dec 10 1m 10k

.control
  run
  set units = si
  let freq = frequency
  let Z = V(100)/I(V_source)
  let Z_mag = abs(Z)
  let Z_phase = ph(Z) ; Use ph(Z) for phase, not pha(Z)
  print freq Z_mag Z_phase
.endc
```

## 6. Usage in Docker Container

To use ngspice in a Docker container, you can add the installation commands to your Dockerfile:

```dockerfile
# Use a Debian-based image
FROM debian:bookworm-slim

# Update package list and install ngspice
RUN apt update && \
    apt install -y ngspice && \
    rm -rf /var/lib/apt/lists/*

# Set working directory (optional)
WORKDIR /app

# Copy your circuit files (if any)
# COPY . /app

# Command to run ngspice (example)
# CMD ["ngspice", "-b", "your_circuit.cir"]
```
