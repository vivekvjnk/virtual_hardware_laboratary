# **BFS-DC — Breadth-First Search with Degree Centrality**

---

## **Skill ID**

`ANA-SKILL-BFS-DC`

---

## **Purpose**

Guide ANA to **build and refine a circuit coherently across multiple agentic iterations** by:

* Starting from **structurally important components or nets**
* Expanding connectivity **breadth-first**
* Growing the circuit **incrementally**, without destabilizing earlier structure
* Strictly **do not** finish circuit building in one agentic iteration. Follow multiple passes.
This skill exists to control *how* ANA thinks, not *what* ANA computes.

---

## **Core Intuition**

> **Some parts of a circuit matter more to global structure than others.
> Start there, then expand outward gradually.**

* “Degree Centrality” is used **qualitatively**, not numerically
* “Breadth-First Search” describes **expansion style**, not traversal code

---

## **Mental Model (Lightweight)**

ANA maintains a **rough internal picture** of the circuit as it evolves:

* Which components/nets are **structural anchors**
* Which parts are **adjacent** to those anchors
* Which parts are still **peripheral or undecided**

This picture is:

* incomplete
* approximate
* continuously refined
* never formalized as data structures

---

## **What “Degree Centrality” Means Here**

ANA uses *intuition*, not calculation.

High-centrality elements are those that:

* connect to many other things
* define domains or boundaries
* propagate constraints widely

Typical examples:

* Primary ICs
* Power and ground rails
* Shared buses
* Isolation boundaries

Low-centrality elements:

* decoupling caps
* pull-ups / pull-downs
* EMI / termination parts

---

## **Skill Behavior Across Iterations**

### **1. Initial Anchoring**

At the beginning of circuit construction, ANA:

* Identifies a **small set of structurally important anchors**
* Treats these as the **starting frontier**
* Avoids deep detail elsewhere

This choice is **sticky** — it does not change lightly.

---

### **2. Breadth-First Expansion**

ANA expands outward from the anchors by:

* Connecting **adjacent components or nets**
* Handling one “layer” of proximity at a time
* Prioritizing **interfaces and shared nets** over fine detail

ANA deliberately avoids:

* finishing one IC completely in isolation
* diving into secondary conditioning networks early

---

### **3. Incremental Graph Growth (Across Iterations)**

Across agentic iterations:

* New components or connections are **added around the existing structure**
* Earlier anchors remain stable reference points
* The circuit “grows” rather than being reshaped wholesale

Importantly:

* ANA does **not** rebuild its mental model from scratch each iteration
* Past structure constrains future reasoning

---

### **4. Late Peripheral Attachment**

Only after the main structure is stable does ANA:

* attach low-impact components
* refine conditioning networks
* complete secondary details

These changes are assumed to have **local impact only**.

---

## **Interaction with Evaluation Failures**

When evaluation fails:

* ANA interprets errors relative to **where it is in the expansion**
* Recent additions are questioned first
* Core anchors are reconsidered **only if failure clearly implicates them**

BFS-DC discourages global rewrites in response to local errors.

---

## **Operational Constraints**

This skill **must**:

* respect SCUD as the source of intent
* tolerate ambiguity without forcing resolution
* preserve continuity across retries

This skill **must not**:

* enforce strict ordering rules
* require numerical scoring
* behave like a fixed algorithm

---

## **Explicit Non-Goals**

This skill does **not**:

* guarantee correctness
* optimize performance
* compute graph metrics
* ensure convergence

It guarantees **reasoning stability**, not success.

