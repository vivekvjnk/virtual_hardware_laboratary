# Abstract Operation Evaluator — Technical Design

## 1. Purpose

Defines a **standard framework** to evaluate a single operation using recorded facts and produce a **semantic judgment**.

Core transformation:

```text
SQLite (facts) → Evaluator → SQLite (semantic judgment)
```

---

## 2. Core Model

Each evaluator follows a fixed pattern:

```text
[1] Read facts from SQLite  
[2] Apply deterministic validation rules  
[3] Aggregate failures  
[4] Decide: SUCCESS or FAILURE  
[5] Generate description  
[6] Persist semantic operation  
```

---

## 3. Input & Output Contract

### Input

* Only **SQLite state**
* No runtime, filesystem, or agent dependencies

---

### Output (`semantic_operations` entry)

```text
operation: <OPERATION>_EVAL  
result: SUCCESS | FAILURE  
description: str  
author: EVALUATOR  
timestamp: auto  
```

---

### Description Rules

* SUCCESS → `"All criteria met"`
* FAILURE → explicit list of violated conditions
* Must be human-readable and LLM-interpretable

---

## 4. Extension Points (Subclass Responsibilities)

Each evaluator must define:

* **Fact Scope**
  What data to read from SQLite

* **Validation Rules**
  Deterministic criteria for success

* **Failure Messages**
  Clear, specific explanations per rule

* **Operation Name**
  `<OPERATION>_EVAL`

---

## 5. Execution Constraints

* **Deterministic**: same DB state → same result
* **Atomic**: exactly one outcome per evaluation
* **Idempotent**: repeated runs produce identical results
* **Complete**: all failures must be reported (no early exit)

---

## 6. Design Boundaries

Evaluator must NOT:

* execute operations
* modify artifacts
* infer beyond recorded facts
* depend on external/runtime state

Evaluator MUST:

* treat SQLite as the **only source of truth**
* produce **semantic judgment only (not raw data)**

---

## 7. Summary

The evaluator layer enforces a system-wide rule:

> **Operations are not considered successful until semantically evaluated and recorded.**

It provides:

* deterministic validation
* explicit failure reasoning
* consistent semantic output

