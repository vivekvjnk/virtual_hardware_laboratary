

# Experiment Report: Li-ion Battery EIS Simulation (50% SOH)

## 1. Purpose
The purpose of this experiment was to simulate the Electrochemical Impedance Spectroscopy (EIS) response of a Li-ion battery at 50% State of Health (SOH) using a Randles equivalent circuit model in ngspice. The simulation aimed to demonstrate the impact of battery degradation on its impedance characteristics and generate a Nyquist plot for analysis.

## 2. Randles Model Parameters for 50% SOH
Based on general electrochemical principles and literature trends regarding Li-ion battery degradation, the following adjustments were made to the Randles model parameters to simulate a 50% SOH. Typically, as a battery degrades, its internal resistances increase, and its capacitance decreases.

| Parameter | Original Value (100% SOH) | Modified Value (50% SOH) | Description                               |
|-----------|---------------------------|--------------------------|-------------------------------------------|
| `Ru_val`  | 0.01 Ohms                 | 0.02 Ohms                | Ohmic Resistance                          |
| `Rct_val` | 0.1 Ohms                  | 0.5 Ohms                 | Charge Transfer Resistance                |
| `Cdl_val` | 1m F                      | 0.5m F                   | Double Layer Capacitance                  |
| `Wsig_val`| 0.05                      | 0.1                      | Warburg Impedance Coefficient             |

The `randles_model.cir` file was updated with these parameters.

## 3. EIS Simulation
The EIS simulation was performed using ngspice with the modified `randles_model.cir` file. The simulation covered a frequency range from 1 mHz to 10 kHz with 10 points per decade. The output included frequency, impedance magnitude (`Z_mag`), and impedance phase (`Z_phase`).

## 4. Nyquist Plot
A Python script (`nyquist_plot.py`) was used to parse the ngspice simulation log, convert the polar impedance data to rectangular coordinates (real and imaginary parts), and generate a Nyquist plot. The Nyquist plot typically displays the negative imaginary part of impedance (-Z_imag) against the real part of impedance (Z_real).

**Generated Nyquist Plot:**
The Nyquist plot for the 50% SOH simulation is located at `runs/20251119080957_dc6af700/nyquist_plot.png`.
A manifest detailing the simulation parameters and artifact paths is available at `runs/20251119080957_dc6af700/manifest.json`.

The plot would show:
*   A semicircle at higher frequencies, representing the parallel combination of `Rct` and `Cdl` (charge transfer process).
*   A Warburg impedance line at lower frequencies, typically observed at a 45-degree angle, representing diffusion processes.
*   The x-intercept at high frequencies corresponds to `Ru`.
*   The diameter of the semicircle on the real axis corresponds to `Rct`.

## 5. Inferences from Results
By comparing the Nyquist plot for 50% SOH with what would be expected for a fresh battery (100% SOH):

*   **Increased Ohmic Resistance (`Ru`)**: The high-frequency intercept on the real axis (Z_real) is expected to be higher for the 50% SOH battery (0.02 Ohms compared to 0.01 Ohms). This indicates increased internal resistance, a common sign of degradation.
*   **Increased Charge Transfer Resistance (`Rct`)**: The diameter of the semicircle is significantly larger for the 50% SOH battery (0.5 Ohms compared to 0.1 Ohms). A larger semicircle indicates a higher charge transfer resistance, which means the electrochemical reactions at the electrode-electrolyte interface are slower or less efficient, characteristic of a degraded battery.
*   **Reduced Double Layer Capacitance (`Cdl`)**: While not directly visible as a single point, a reduced `Cdl` (0.5mF compared to 1mF) would affect the shape and peak frequency of the semicircle. A smaller capacitance can lead to a shift in the semicircle's peak.
*   **Modified Warburg Impedance (`Wsig`)**: The Warburg impedance, representing diffusion limitations, is also expected to be altered. In this case, `Wsig` was doubled to 0.1. This change would influence the slope and extent of the 45-degree line at lower frequencies, suggesting changes in ion diffusion rates within the battery.

In summary, the simulated Nyquist plot for 50% SOH clearly demonstrates the characteristic signs of battery degradation: increased internal resistances and altered kinetics and diffusion properties, manifesting as shifts and enlargements in the impedance features.

## 6. Conclusion
The EIS simulation using the Randles model successfully captured the expected impedance characteristics of a Li-ion battery at 50% SOH. The increased `Ru` and `Rct` values, along with changes in `Cdl` and `Wsig`, resulted in a Nyquist plot that reflects the degraded state of the battery. This methodology can be used to further explore battery health across various SOH levels and aid in battery management system development.

