# User Project Model in VHL

The Virtual Hardware Laboratory (VHL) utilizes a structured project model designed for multi-agent orchestration and deterministic hardware design. This model centers on the decomposition of hardware systems into isolated, verifiable units.

## Core Abstractions

### Modules
A **Module** is the fundamental unit of engineering capability in VHL. It is a self-contained functional block (e.g., a "BMS Monitor Module" or a "Current Sensing Module") that encapsulates a specific set of components and logic.

Key characteristics of Modules:
- **Independent Development**: Each module is maintained in a dedicated **Git Worktree**, allowing for parallel evolution and versioning without impacting other parts of the system.
- **Dedicated Agent Context**: Every module has a dedicated set of persistent **URP Agents** (Archy, Librarian, and ANA) that maintain the module's state and design history.
- **Strict Boundary Definition**: Modules are defined by a **Module Boundary Document**, which specifies the electrical and logical ports, consumed/produced resources, and operational contracts.
- **Internal Specification**: The module's internal design is captured in a **Shared Circuit Understanding Document (SCUD)**, serving as a bridge between high-level intent and implementation.

### Assemblies
An **Assembly** is a high-level abstraction that represents the interconnection of multiple Modules to achieve a broader hardware design target.

Key characteristics of Assemblies:
- **Interconnection Logic**: Assemblies import module definitions and define the connectivity (traces) between them.
- **System Authority**: The **System Boundary Document** acts as the authoritative registry for all modules within an assembly, defining their roles and inter-dependencies.
- **Compositional Implementation**: Like modules, assemblies have their own SCUD and `.tsx` circuit code, but their implementation primarily involves instantiating and wiring together modules.

## Project Structure

A typical VHL user project follows a hierarchical structure:

- **Project Root**: Contains assembly definitions, the global `system-boundary.md`, and project-wide configuration (e.g., `package.json`, `tscircuit.config.json`).
- **Module Worktrees**: Subdirectories (often managed as git worktrees) containing the module's `Workspace/`. This includes the module's implementation (`.tsx`), specification (`.scud`), interface boundary (`-boundary.md`), and research resources.

## Design Workflow

The VHL orchestration layer (AOSM) drives the design process through these abstractions:

1.  **System Specification**: The user or a supervisor agent defines the `system-boundary.md`.
2.  **Module Initialization**: For each module defined, a worktree is created, and URP agents are assigned.
3.  **Iterative Synthesis**:
    - **Archy** generates the SCUD from requirements and reference materials.
    - **Librarian** manages component imports.
    - **ANA** implements the circuit code in `.tsx`.
4.  **Verification**: The VHL Evaluation (VAP) engine validates the module implementation against its boundary and the SCUD.
5.  **Integration**: Validated modules are integrated into the final assembly.
