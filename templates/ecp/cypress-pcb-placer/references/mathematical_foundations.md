# Mathematical Foundations of Cypress Placement Engine

This reference details the mathematical modeling and formulation behind the continuous non-linear optimization used in Cypress (adapted from DREAMPlace).

---

## 1. Master Loss Objective

Component placement is modeled as a continuous optimization problem minimizing wirelength, density overflow, and net crossing penalties:

$$\min_{\mathbf{x}, \mathbf{y}, \mathbf{\Theta}} \quad \mathcal{L}(\mathbf{x}, \mathbf{y}, \mathbf{\Theta}) = W(\mathbf{x}, \mathbf{y}, \mathbf{\Theta}) + \lambda_D \cdot D(\mathbf{x}, \mathbf{y}) + \lambda_{NC} \cdot NC(\mathbf{x}, \mathbf{y}, \mathbf{\Theta})$$

Where:
- $\mathbf{x}, \mathbf{y}$: Component center coordinates.
- $\mathbf{\Theta}$: Continuous orientation angle logits (discrete angles $\{0^\circ, 90^\circ, 180^\circ, 270^\circ\}$ relaxed via Gumbel-Softmax).
- $W$: Differentiable wirelength cost.
- $D$: Electrostatic density potential penalty.
- $NC$: Pairwise segment net-crossing penalty score.
- $\lambda_D, \lambda_{NC}$: Dynamic Lagrange multipliers.

---

## 2. Smooth Wirelength Formulations

Since Half-Perimeter Wirelength (HPWL) is non-differentiable ($\max x_i - \min x_i$), smooth differentiable approximations are used:

### Weighted-Average (WA) Model
$$W_{WA}(\mathbf{x}) = \sum_{e \in E} \left( \frac{\sum_{i \in e} x_i e^{x_i / \gamma}}{\sum_{i \in e} e^{x_i / \gamma}} - \frac{\sum_{i \in e} x_i e^{-x_i / \gamma}}{\sum_{i \in e} e^{-x_i / \gamma}} \right)$$

### Log-Sum-Exp (LSE) Model
$$W_{LSE}(\mathbf{x}) = \gamma \sum_{e \in E} \left( \ln \sum_{i \in e} e^{x_i / \gamma} + \ln \sum_{i \in e} e^{-x_i / \gamma} \right)$$

- **$\gamma$ (Gamma)**: Smoothing parameter. Larger $\gamma$ distributes smooth gradients across wide areas; smaller $\gamma$ sharpens bounding box forces close to exact HPWL.

---

## 3. Electrostatic Density Model

Components are modeled as positively charged particles in a continuous electrostatic field. Density overflow $D(\mathbf{x}, \mathbf{y})$ is solved via Poisson's equation using 2D Fast Fourier Transforms (FFT):

$$\nabla^2 \Phi(x, y) = -\rho(x, y)$$

Where $\rho(x, y)$ is spatial cell density charge and $\Phi(x, y)$ is electrostatic potential. Density forces act as smooth repulsive vectors ($\mathbf{F}_D = -\nabla D$) pushing overlapping components apart.

---

## 4. Continuous Orientation Optimization (Gumbel-Softmax)

To optimize component orientations continuously, discrete orientation choices $\theta \in \{0^\circ, 90^\circ, 180^\circ, 270^\circ\}$ are relaxed using Gumbel-Softmax categorical probabilities:

$$p_k = \frac{\exp((\phi_k + g_k) / \tau)}{\sum_{j=0}^3 \exp((\phi_j + g_j) / \tau)}$$

Where $\phi_k$ are trainable orientation logits, $g_k \sim \text{Gumbel}(0, 1)$ is i.i.d. noise, and $\tau$ is the temperature parameter. During export, deterministic angle assignment selects $\theta = \arg\max_k(\phi_k)$.
