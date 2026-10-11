# Circuit JSON to Bookshelf Matrix Transformation Derivation

## 1. Overview & Mathematical Formulation

This document details the mathematical transformation between the **Circuit JSON** PCB representation and the VLSI **Bookshelf** format (`.aux`, `.nodes`, `.nets`, `.pl`, `.scl`) used by Cypress / DREAMPlace.

The translation handled in `circuitjson_to_bookshelf_utils/converter.py` maps continuous 2D CAD coordinates in millimeters ($\text{mm}$) into discrete placement grid coordinates in database units ($\mu\text{m}$). This transformation is a 2D affine map (scaling, translation, and origin shift) that can be fully expressed using homogeneous matrix operations.

---

## 2. Coordinate Systems & Variables

### Circuit JSON Coordinate System
* **Board Dimensions**: Width $W_{\text{board}}$, Height $H_{\text{board}}$, centered at $(x_{\text{center\_board}}, y_{\text{center\_board}})$.
* **Board Bottom-Left Corner**:
  $$x_{\text{min\_board}} = x_{\text{center\_board}} - \frac{W_{\text{board}}}{2}$$
  $$y_{\text{min\_board}} = y_{\text{center\_board}} - \frac{H_{\text{board}}}{2}$$
* **Scale Factor**: $S$ (default $S = 1000.0$ to convert $\text{mm} \to \mu\text{m}$).
* **Component $i$**:
  * Center coordinate: $\mathbf{c}_i = [x_{c,i}, y_{c,i}]^T$
  * Dimensions: $w_i, h_i$
* **Pin/Port $k$**: Absolute coordinate $\mathbf{p}_k = [x_{\text{pin}, k}, y_{\text{pin}, k}]^T$.

### Bookshelf Coordinate System
* **Grid Origin $(0, 0)$**: Placed at the **bottom-left corner** of the board boundary.
* **Component $i$ (`.pl`)**: Specified by its **bottom-left corner** coordinate $\mathbf{b}_i = [x_{\text{bl},i}, y_{\text{bl},i}]^T$.
* **Component $i$ (`.nodes`)**: Specified by its integer scaled width and height $(W_i, H_i)$.
* **Pin/Port $k$ (`.nets`)**: Specified as a relative offset $[\Delta x_k, \Delta y_k]^T$ from the component center.

---

## 3. Forward Transformation: Circuit JSON $\longrightarrow$ Bookshelf

### 3.1 Board Normalization Matrix ($\mathbf{T}_{\text{board}}$)

To map any point $\mathbf{x} = [x, y]^T$ on the board from Circuit JSON coordinates to Bookshelf board coordinates (origin at bottom-left, scaled by $S$):

$$\begin{bmatrix} x^{\text{BS}} \\ y^{\text{BS}} \\ 1 \end{bmatrix} = \mathbf{T}_{\text{board}} \begin{bmatrix} x^{\text{JSON}} \\ y^{\text{JSON}} \\ 1 \end{bmatrix}$$

$$\mathbf{T}_{\text{board}} = \begin{bmatrix} 
S & 0 & -S \cdot x_{\text{min\_board}} \\ 
0 & S & -S \cdot y_{\text{min\_board}} \\ 
0 & 0 & 1 
\end{bmatrix} = \begin{bmatrix} 
S & 0 & -S \left(x_{\text{center\_board}} - \frac{W_{\text{board}}}{2}\right) \\ 
0 & S & -S \left(y_{\text{center\_board}} - \frac{H_{\text{board}}}{2}\right) \\ 
0 & 0 & 1 
\end{bmatrix}$$

---

### 3.2 5D State Vector Transformation Matrix ($\mathbf{M}_{\text{JSON} \to \text{BS}}$)

For component $i$, Bookshelf requires:
- Bottom-left position: $x_{\text{bl}, i} = S \left(x_{c, i} - \frac{w_i}{2} - x_{\text{min\_board}}\right)$
- Bottom-left position: $y_{\text{bl}, i} = S \left(y_{c, i} - \frac{h_i}{2} - y_{\text{min\_board}}\right)$
- Size: $W_i = S \cdot w_i, \quad H_i = S \cdot h_i$

We express this as a linear transformation operating on a 5D component state vector:

$$\mathbf{v}_i^{\text{BS}} = \mathbf{M}_{\text{JSON} \to \text{BS}} \; \mathbf{v}_i^{\text{JSON}}$$

Where:
$$\mathbf{v}_i^{\text{JSON}} = \begin{bmatrix} x_{c,i} \\ y_{c,i} \\ w_i \\ h_i \\ 1 \end{bmatrix}, \quad \mathbf{v}_i^{\text{BS}} = \begin{bmatrix} x_{\text{bl},i} \\ y_{\text{bl},i} \\ W_i \\ H_i \\ 1 \end{bmatrix}$$

$$\mathbf{M}_{\text{JSON} \to \text{BS}} = \begin{bmatrix} 
S & 0 & -\frac{S}{2} & 0 & -S \cdot x_{\text{min\_board}} \\ 
0 & S & 0 & -\frac{S}{2} & -S \cdot y_{\text{min\_board}} \\ 
0 & 0 & S & 0 & 0 \\ 
0 & 0 & 0 & S & 0 \\ 
0 & 0 & 0 & 0 & 1 
\end{bmatrix}$$

---

## 4. Reverse Transformation (Back-Annotation): Bookshelf $\longrightarrow$ Circuit JSON

After global placement completes, updated bottom-left coordinates $(x_{\text{bl}}^{\text{new}}, y_{\text{bl}}^{\text{new}})$ are output in `<design>.gp.pl`.

To back-annotate updated component center positions into Circuit JSON, we multiply by the inverse matrix $\mathbf{M}_{\text{BS} \to \text{JSON}} = \mathbf{M}_{\text{JSON} \to \text{BS}}^{-1}$:

$$\mathbf{v}_i^{\text{JSON, new}} = \mathbf{M}_{\text{BS} \to \text{JSON}} \; \mathbf{v}_i^{\text{BS, new}}$$

$$\mathbf{M}_{\text{BS} \to \text{JSON}} = \begin{bmatrix} 
\frac{1}{S} & 0 & \frac{1}{2S} & 0 & x_{\text{min\_board}} \\ 
0 & \frac{1}{S} & 0 & \frac{1}{2S} & y_{\text{min\_board}} \\ 
0 & 0 & \frac{1}{S} & 0 & 0 \\ 
0 & 0 & 0 & \frac{1}{S} & 0 \\ 
0 & 0 & 0 & 0 & 1 
\end{bmatrix}$$

Expanding the first two rows gives the exact denormalization equations implemented in `_apply_placement_updates`:
$$x_{c, i}^{\text{new}} = \frac{x_{\text{bl}, i}^{\text{new}}}{S} + \frac{W_i}{2S} + x_{\text{min\_board}} = \frac{x_{\text{bl}, i}^{\text{new}}}{S} + \frac{w_i}{2} + x_{\text{min\_board}}$$
$$y_{c, i}^{\text{new}} = \frac{y_{\text{bl}, i}^{\text{new}}}{S} + \frac{H_i}{2S} + y_{\text{min\_board}} = \frac{y_{\text{bl}, i}^{\text{new}}}{S} + \frac{h_i}{2} + y_{\text{min\_board}}$$

---

## 5. Auxiliary Transformations

### 5.1 Pin/Port Relative Offset Matrix ($\mathbf{M}_{\text{pin}}$)
In `.nets`, pin offset relative to the component center is calculated as:
$$\begin{bmatrix} \Delta x_{\text{pin}} \\ \Delta y_{\text{pin}} \end{bmatrix} = \mathbf{M}_{\text{pin}} \begin{bmatrix} x_{\text{pin}} - x_{c,i} \\ y_{\text{pin}} - y_{c,i} \end{bmatrix} = \begin{bmatrix} S & 0 \\ 0 & S \end{bmatrix} \begin{bmatrix} x_{\text{pin}} - x_{c,i} \\ y_{\text{pin}} - y_{c,i} \end{bmatrix}$$

### 5.2 Component Displacement & Child Element Shift Matrix ($\mathbf{T}_{\Delta}$)
When component $i$ is moved by global placement, its center shifts by:
$$\begin{bmatrix} \Delta x_c \\ \Delta y_c \end{bmatrix} = \begin{bmatrix} x_{c,i}^{\text{new}} - x_{c,i}^{\text{old}} \\ y_{c,i}^{\text{new}} - y_{c,i}^{\text{old}} \end{bmatrix} = \begin{bmatrix} \frac{1}{S} & 0 \\ 0 & \frac{1}{S} \end{bmatrix} \begin{bmatrix} x_{\text{bl},i}^{\text{new}} - x_{\text{bl},i}^{\text{old}} \\ y_{\text{bl},i}^{\text{new}} - y_{\text{bl},i}^{\text{old}} \end{bmatrix}$$

Any associated sub-element (pad, port, silkscreen vertex, trace vertex $[x_p, y_p]^T$) is shifted recursively via translation matrix $\mathbf{T}_{\Delta}$:

$$\begin{bmatrix} x_p^{\text{new}} \\ y_p^{\text{new}} \\ 1 \end{bmatrix} = \mathbf{T}_{\Delta} \begin{bmatrix} x_p^{\text{old}} \\ y_p^{\text{old}} \\ 1 \end{bmatrix} = \begin{bmatrix} 1 & 0 & \Delta x_c \\ 0 & 1 & \Delta y_c \\ 0 & 0 & 1 \end{bmatrix} \begin{bmatrix} x_p^{\text{old}} \\ y_p^{\text{old}} \\ 1 \end{bmatrix}$$

---

## 6. Concrete Example (`power_circuit/circuit.json`)

For `power_circuit/circuit.json`:
* $W_{\text{board}} = 100\text{ mm}$, $H_{\text{board}} = 100\text{ mm}$, board center $(0,0) \implies x_{\text{min\_board}} = -50$, $y_{\text{min\_board}} = -50$
* Scale factor $S = 1000.0$

### Forward Transformation Matrix:
$$\mathbf{M}_{\text{JSON} \to \text{BS}} = \begin{bmatrix} 
1000 & 0 & -500 & 0 & 50000 \\ 
0 & 1000 & 0 & -500 & 50000 \\ 
0 & 0 & 1000 & 0 & 0 \\ 
0 & 0 & 0 & 1000 & 0 \\ 
0 & 0 & 0 & 0 & 1 
\end{bmatrix}$$

### Reverse Transformation Matrix:
$$\mathbf{M}_{\text{BS} \to \text{JSON}} = \begin{bmatrix} 
0.001 & 0 & 0.0005 & 0 & -50 \\ 
0 & 0.001 & 0 & 0.0005 & -50 \\ 
0 & 0 & 0.001 & 0 & 0 \\ 
0 & 0 & 0 & 0.001 & 0 \\ 
0 & 0 & 0 & 0 & 1 
\end{bmatrix}$$

---

## 7. Mapping to Code Implementation (`converter.py`)

| Mathematical Concept | Matrix Representation | Method in `converter.py` |
| :--- | :--- | :--- |
| Board Normalization | $\mathbf{T}_{\text{board}}$ | `_get_normalization()` |
| Component Conversion (JSON $\to$ BS) | $\mathbf{M}_{\text{JSON} \to \text{BS}}$ | `_generate_bookshelf_files()` |
| Pin Relative Offsets | $\mathbf{M}_{\text{pin}}$ | `to_bookshelf_pcb()` / `to_bookshelf_schematic()` |
| Component Back-Annotation (BS $\to$ JSON) | $\mathbf{M}_{\text{BS} \to \text{JSON}}$ | `_apply_placement_updates()` |
| Recursive Child Shifts | $\mathbf{T}_{\Delta}$ | `shift_recursive()` in `_apply_placement_updates()` |
