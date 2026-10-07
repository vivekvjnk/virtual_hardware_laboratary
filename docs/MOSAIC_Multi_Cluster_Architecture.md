# MOSAIC Multi-Cluster Agent Architecture for VHL

> **Document Version:** 1.0.0  
> **Date:** 2026-10-06  
> **Status:** Approved Architectural Specification  
> **Target Module:** `vhl-runtime-mosaic` (`feature/mosaic-runtime-migration`)  
> **Authors:** Wise Turtle (WT) & Crazy Orca (CO)

---

## 1. Executive Summary & Architectural Paradigm

The Virtual Hardware Laboratory (VHL) automated circuit design platform utilizes a **Federated Multi-Cluster Multi-Agent Architecture** powered by the **MOSAIC Hosting Framework (MOSAIC HF)**.

Rather than running all agents in a single monolithic container or using a rigid Python state machine (`AOSM`), the system organizes multi-agent execution into **isolated Agent Clusters** corresponding directly to Git worktrees:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              VHL RUNTIME EXPRESS (Port 3022)                           │
│                      Deterministic Platform, Substrate & Cluster Supervisor            │
│               • Assigns cluster ports: Root (8000), Modules (8001..8050)               │
│               • Generates project-wide cluster_roster.json address book                │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
        ┌───────────────────────────────────┼───────────────────────────────────┐
        ▼                                   ▼                                   ▼
┌───────────────────────────────┐ ┌───────────────────────────────┐ ┌───────────────────────────────┐
│     MODULE CLUSTER 1 (8001)   │ │     MODULE CLUSTER 2 (8002)   │ │     ROOT CLUSTER (Port 8000)  │
│  bms-monitor-module/          │ │  communication-bridge/        │ │  bms-project_root/            │
│                               │ │                               │ │                               │
│  [archy] (Lead Orchestrator)  │ │  [archy] (Lead Orchestrator)  │ │  [control_archy] (Lead)       │
│     │        ▲                │ │     │        ▲                │ │     ├─► [control_ana]         │
│     ├─► [librarian] (Worker)  │ │     ├─► [librarian] (Worker)  │ │     └─► [control_layout]      │
│     └─► [ana]       (Worker)  │ │     └─► [ana]       (Worker)  │ │                               │
│                               │ │                               │ │  [power_archy] (Lead)         │
│                               │ │                               │ │     ├─► [power_ana]           │
│                               │ │                               │ │     └─► [power_layout]        │
└───────────────▲───────────────┘ └───────────────▲───────────────┘ └───────────────▲───────────────┘
                │                                 │                                 │
                └═══════════════ Federated A2A Archy-to-Archy Bus ══════════════════┘
                               (Inter-Module Boundary Alignment)
```

### Core Principles
1. **Cognitive Isolation by Worktree**: Each hardware module is maintained in a dedicated Git worktree. A dedicated MOSAIC server instance runs inside each worktree as an **Agent Cluster**.
2. **Orchestrator-Worker Hierarchy**: Within each cluster, **Archy** is the lead orchestrator; **Librarian** and **ANA-D** are specialized domain workers. Workers never see outside files or external agents.
3. **Federated Archy Gateway**: Archies act as diplomatic gateways between modules, collaborating across clusters over standard **Agent2Agent (A2A)** protocol to align interface boundaries.
4. **Single-Server Main Worktree for Assemblies**: The root worktree hosts top-level assemblies using flat, prefixed agent triads (`<assembly>_archy`, `<assembly>_ana`, `<assembly>_layout`) under a single MOSAIC instance, preventing filesystem lock conflicts.

---

## 2. Module Worktree Agent Clusters

### 2.1 The Module Triad
Every module worktree (e.g., `bms-project_e0505ca9_bms-monitor-module/`) hosts an independent MOSAIC instance running on a dedicated port (e.g. `8001`):

| Agent Name | Role | Primary Responsibilities | Allowed Skills |
| :--- | :--- | :--- | :--- |
| **`archy`** | **Lead Orchestrator** | Ingests reference schematics and boundary specs; writes `circuit_design.scud`; delegates tasks to Librarian and ANA; communicates with sibling Archies. | `vhl-workspace-ops`, `a2a-peer-dialing` |
| **`librarian`** | **Worker** | Resolves BOM components into footprints; queries registries; writes verified TSX chips into module `imports/`. | `vhl-component-resolver`, `vhl-workspace-ops`, `a2a-peer-dialing` |
| **`ana`** | **Worker** | Synthesizes `tscircuit` TSX code from SCUD netlists; invokes VAP evaluation; rectifies compiler errors. | `vhl-circuit-evaluator`, `vhl-workspace-ops`, `a2a-peer-dialing` |

### 2.2 In-Cluster Communication Mechanics
- Within a module cluster, all agents are registered under the local `.agents/well_known/` directory.
- Peer discovery occurs natively through MOSAIC’s local instance lock (`.mosaic.lock`).
- Intra-cluster delegation requires no external URLs:
  ```bash
  # Archy delegates footprint resolution to Librarian
  a2a_peer_call send --peer librarian --message "Resolve JLCPCB footprints for C2040 and BQ79616"
  
  # Archy delegates TSX synthesis to ANA
  a2a_peer_call send --peer ana --message "Synthesize circuit TSX matching circuit_design.scud"
  ```
- Workers report task outcomes back to Archy via causal execution traces (`.agents/tasks/`), protecting context windows from bloat.

### 2.3 Directory Scaffolding per Module Worktree
```text
<project_id>_<module_name>/
├── .agents/
│   ├── well_known/
│   │   ├── archy.json           # Module-specific prompt & capabilities
│   │   ├── librarian.json
│   │   └── ana.json
│   ├── skills/                  # Standalone ECP skill directories (manually updated / registry)
│   │   ├── a2a-peer-dialing -> <runtime>/skills/a2a-peer-dialing
│   │   ├── vhl-circuit-evaluator -> <runtime>/skills/vhl-circuit-evaluator
│   │   ├── vhl-component-resolver -> <runtime>/skills/vhl-component-resolver
│   │   └── vhl-workspace-ops -> <runtime>/skills/vhl-workspace-ops
│   ├── workflows/
│   │   └── module_synthesis.md  # Stage contracts & Definitions of Done
│   ├── sessions/                # Persistent conversation memory
│   └── cluster_roster.json      # Address book of peer clusters in project
│
├── <module_name>/
│   └── Workspace/
│       ├── AGENTS.md
│       ├── <module_name>.scud
│       ├── <module_name>.tsx
│       ├── imports/
│       └── resources/
└── .git                         # Worktree gitdir pointer
```

---

## 3. Federated Inter-Cluster Communication (Archy-to-Archy Network)

### 3.1 The `cluster_roster.json` Address Book
When a project is loaded, VHL Runtime inspects all module worktrees and generates an address book `cluster_roster.json` injected into every cluster's `.agents/` folder:

```json
{
  "project_id": "bms-project_e0505ca9",
  "project_root": "/Users/vivek/Virtual_Labs/bms-project_e0505ca9",
  "clusters": {
    "root": {
      "name": "Assembly Root",
      "url": "http://127.0.0.1:8000",
      "worktree": "/Users/vivek/Virtual_Labs/bms-project_e0505ca9/bms-project_e0505ca9_root",
      "type": "assembly"
    },
    "bms-monitor-module": {
      "name": "BMS Monitor Module",
      "url": "http://127.0.0.1:8001",
      "worktree": "/Users/vivek/Virtual_Labs/bms-project_e0505ca9/bms-project_e0505ca9_bms-monitor-module",
      "type": "module",
      "lead": "archy"
    },
    "communication-bridge": {
      "name": "Communication Bridge",
      "url": "http://127.0.0.1:8002",
      "worktree": "/Users/vivek/Virtual_Labs/bms-project_e0505ca9/bms-project_e0505ca9_communication-bridge",
      "type": "module",
      "lead": "archy"
    }
  }
}
```

### 3.2 Cross-Cluster Delegation Flow
When `bms-monitor-module.archy` needs to verify signal polarity with `communication-bridge.archy`:
1. Archy queries `cluster_roster.json` and locates `communication-bridge` at `http://127.0.0.1:8002`.
2. Archy executes `a2a_peer_call` specifying the target URL:
   ```bash
   a2a_peer_call send \
     --url http://127.0.0.1:8002 \
     --peer archy \
     --message "Confirm UART TX/RX pin polarity connecting to BQ79616 digital isolator U2"
   ```
3. The remote MOSAIC cluster on port `8002` receives the request, dispatches it to its local `archy`, executes the reasoning, and emits an asynchronous callback envelope.
4. `bms-monitor-module.archy` updates its SCUD Section 1 (Signal Flow) with the confirmed contract.

### 3.3 Bounded Inter-Cluster Recursion & Anti-Loop Safeguards
To uphold **Invariant 5**:
- Cross-cluster requests include a header `x-vhl-hop-count: <N>`.
- **Maximum Hop Budget**: `2` (e.g. Module A $\rightarrow$ Module B $\rightarrow$ Module A).
- If negotiations do not reach consensus within 2 exchanges:
  - The ambiguity is logged into **SCUD Section 4 (Semantic Uncertainties)**.
  - The workflow halts and raises a **Human-in-the-Loop (HIL)** notification on the WebUI.
  - This prevents infinite inter-agent token/spend loops.

---

## 4. Main Worktree: Assembly-Level Flat Cluster

### 4.1 The Single-Server Constraint on Root
- MOSAIC enforces `WorkspaceLockManager`: **Only one MOSAIC instance is permitted per workspace directory**.
- Because assemblies (`control-circuit`, `power-circuit`, `index.circuit.tsx`) all reside within the root worktree (`bms-project_e0505ca9_root`), the root worktree runs **one MOSAIC server instance** on Port `8000`.

### 4.2 Namespaced Assembly Triads
To support multiple assemblies concurrently without collisions, assembly agents are namespaced by assembly identifier:

```text
Root Worktree Cluster (Port 8000)
├── control_circuit Assembly
│   ├── control_archy      (Lead Assembly Architect)
│   ├── control_ana        (Assembly TSX Wiring & Bus Router)
│   └── control_layout     (Board Sizing & Layout Engineer)
│
└── power_circuit Assembly
    ├── power_archy        (Lead High-Current Architect)
    ├── power_ana          (High-Current Bus Router & TSX Synthesizer)
    └── power_layout       (Thermal Isolation & Placement Specialist)
```

- **Assembly Archies** inspect `system-boundary.md` and communicate with underlying module Archies (via A2A to ports 8001..8007) to pull in sub-circuit definitions.
- **Assembly ANA** instantiates and connects submodules into top-level board code.
- **Assembly Layout Engineer** tunes Cypress autorouter parameters, computes board dimensions, and enforces thermal/isolation gaps.

---

## 5. VHL Runtime Cluster Supervisor (`ClusterSupervisor`)

### 5.1 Responsibilities
Rather than requiring developers to manually spawn 8 background terminal processes, `vhl-runtime-mosaic` acts as the **Cluster Supervisor**:

1. **Port Allocation**:
   - `Port 3022`: VHL Runtime Express API & WebUI
   - `Port 8000`: Root Assembly Cluster
   - `Port 8001..8050`: Dynamically allocated to module clusters based on SQLite `project_modules`.
2. **Lifecycle Management**:
   - **On `POST /api/load-project`**:
     * Detects project modules and worktree paths via `VHLWorkspaceManager`.
     * Scaffolds `.agents/` and provisions canonical ECP skills if not present.
     * Writes updated `cluster_roster.json` into each worktree.
     * Spawns the Root Cluster and active Module Clusters via `mosaic host`.
   - **On `POST /api/close-project` or Server Shutdown**:
     * Sends `SIGTERM` followed by `SIGKILL` to all spawned cluster process trees.
     * Guarantees all allocated ports (8000..8050) are freed.
3. **Lazy vs. Eager Activation Policy**:
   - **Eager (Small Projects $\le 4$ modules)**: Spawns root + all module clusters on project load.
   - **Lazy (Large Projects $> 4$ modules)**:
     * Spawns Root Cluster immediately.
     * Module clusters remain dormant until the user navigates to the module in the WebUI or triggers synthesis (`POST /api/trigger-workflow`).
     * Cluster boots in $<1.5\text{s}$, preserving memory and CPU.
     * Dormant clusters spin down after 30 minutes of inactivity.

---

## 6. Shared Engineering Capability Packages (ECPs)

All clusters share canonical tools maintained by `vhl-runtime-mosaic`:

```text
vhl-runtime-mosaic/.agents/skills/
├── a2a-peer-dialing/           # Inter-agent task delegation tool
├── vhl-circuit-evaluator/      # POST /api/vap/evaluate caller
├── vhl-component-resolver/     # JLCPCB/EasyEDA footprint search & generator
└── vhl-workspace-ops/          # Git worktree commit & SQLite state logger
```

During worktree initialization:
- `ClusterSupervisor` provisions standalone skill directories in `<worktree>/.agents/skills/<skill>` from canonical skills in `vhl-runtime-mosaic/.agents/skills/`. ECPs remain independent directories for manual updates or future registry distribution without symlinks.

---

## 7. Concrete Walkthrough: BMS Project (`bms-project_e0505ca9`)

| Component | Filesystem Location | MOSAIC Cluster Role | Port | Active Agents |
| :--- | :--- | :--- | :---: | :--- |
| **Project Root** | `bms-project_e0505ca9_root` | Root Assembly Cluster | **`8000`** | `control_archy`, `control_ana`, `control_layout`, `power_archy`, `power_ana`, `power_layout` |
| **BMS Monitor** | `bms-project_e0505ca9_bms-monitor-module` | Dedicated Module Cluster | **`8001`** | `archy`, `librarian`, `ana` |
| **Comm Bridge** | `bms-project_e0505ca9_communication-bridge` | Dedicated Module Cluster | **`8002`** | `archy`, `librarian`, `ana` |
| **Current Sensing**| `bms-project_e0505ca9_current-sensing` | Dedicated Module Cluster | **`8003`** | `archy`, `librarian`, `ana` |
| **HV Power Supply**| `bms-project_e0505ca9_high-voltage-power-supply` | Dedicated Module Cluster | **`8004`** | `archy`, `librarian`, `ana` |
| **LV Power Supply**| `bms-project_e0505ca9_low-voltage-power-supply` | Dedicated Module Cluster | **`8005`** | `archy`, `librarian`, `ana` |
| **MCU Module** | `bms-project_e0505ca9_microcontroller-module` | Dedicated Module Cluster | **`8006`** | `archy`, `librarian`, `ana` |
| **Switching Ckt** | `bms-project_e0505ca9_switching_circuit` | Dedicated Module Cluster | **`8007`** | `archy`, `librarian`, `ana` |

When synthesis is initiated on `bms-monitor-module`:
1. `bms-monitor-module.archy` (Port 8001) analyzes `segment_0.png` $\rightarrow$ outputs `bms-monitor-module.scud`.
2. Archy dials `bms-monitor-module.librarian` (Port 8001) $\rightarrow$ imports BQ79616 footprint.
3. Archy dials `bms-monitor-module.ana` (Port 8001) $\rightarrow$ writes `bms-monitor-module.tsx`.
4. ANA runs `vhl_evaluate_circuit` $\rightarrow$ VAP passes on Port 3022.
5. In root (Port 8000), `control_archy` dials `bms-monitor-module.archy` (Port 8001) over A2A $\rightarrow$ imports the verified module into `control-circuit.tsx`.
6. Full assembly synthesis completes deterministically and autonomously.
