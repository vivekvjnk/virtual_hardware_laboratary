# Cypress Telemetry Metrics Reference

This document provides detailed breakdowns of telemetry log fields output by the Cypress / DREAMPlace placement solver during execution (`DREAMPlace.log` / `run.log`).

---

## 1. Sample Log Telemetry Entry

```text
[INFO   ] DREAMPlace - iteration 2711, (2711,  0,  0), Obj 1.173403E+37, NetCrossing 1.805E+03, NetCrossingWeight 0.000000E+00, DensityWeight 5.399523E+34, HPWL 8.318736E+04, Overflow 7.420439E-03, MaxDensity 1.638E+00, gamma 6.443016E+00, time 7.787ms
```

---

## 2. Telemetry Field Definitions

| Field Name | Source Module | Description & Metric Grounding |
| :--- | :--- | :--- |
| `iteration` | `NonLinearPlace.py` | Overall global placement iteration index. |
| `(Lgamma, Llambda, Lsub)` | `NonLinearPlace.py` | 3-nested loop stage indices:<br>• $L_\gamma$: Outer loop step index for wirelength parameter updates.<br>• $L_\lambda$: Middle loop step index for density multiplier updates.<br>• $L_{\text{sub}}$: Inner loop step index for Nesterov spatial coordinate descent. |
| `Obj` | `PlaceObj.py` | Total scalar loss value evaluated by objective function:<br>$\mathcal{L} = WL + \lambda_D D + \lambda_{NC} NC$. |
| `NetCrossing` | `net_crossing_op` | Total estimated pairwise wire segment crossing cost score across active nets. |
| `NetCrossingWeight` | `PlaceObj.py` | Current multiplier weight ($\lambda_{NC}$) applied to net crossing penalty. |
| `DensityWeight` | `PlaceObj.py` | Current electrostatic density Lagrange multiplier ($\lambda_D$). |
| `HPWL` | `EvalMetrics.py` | Exact Half-Perimeter Wirelength evaluated across all non-masked nets ($2 \le \text{degree} < 100$). |
| `Overflow` | `EvalMetrics.py` | Normalized density overflow ratio:<br>$\text{Overflow} = \frac{\text{overflow\_area}}{\text{total\_movable\_node\_area}}$.<br>Global placement terminates when $\text{Overflow} < \text{stop\_overflow}$ (typically `0.07`). |
| `MaxDensity` | `EvalMetrics.py` | Peak local bin density occupancy ratio $\max(\rho_{\text{bin}})$ across all spatial bin grids. |
| `gamma` | `NonLinearPlace.py` | Runtime smoothness parameter $\gamma$ for LSE/WA wirelength approximation:<br>$\gamma = \gamma_{\text{base}} \cdot 10^{\frac{20}{9}(\text{overflow} - 0.1) - 1}$. |
| `time` | `EvalMetrics.py` | Per-iteration evaluation delay in milliseconds. |
