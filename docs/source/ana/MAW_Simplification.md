WorkspaceManager Migration: Iteration-Based MAW → Persistent Workspace MAW
1. Purpose

This document defines the architectural migration required to transition the ANA Mirrored Attempt Workspace (MAW) model from:

Copy-On-Write Iterations

to

Persistent Workspace + Snapshot Archives

The objective is to simplify ANA workspace management, align with skill-based agent architectures, reduce runtime state reconstruction, and preserve all historical attempts through snapshot archival.

2. Current Architecture
Current Workspace Layout
<Project>
│
├── lib/
│
├── <module>/
│   ├── Iterations/
│   │   ├── 0001_xxx/
│   │   ├── 0002_xxx/
│   │   └── ...
│   │
│   ├── Stable/
│   ├── Archives/
│   └── resources/
Current MAW Flow
Iteration N
    ↓
Create Iteration N+1
    ↓
Copy TSX from N
    ↓
Copy observations
    ↓
Run ANA
    ↓
Run VAP

WorkspaceManager maintains:

current_iteration_path
previous_iteration_path
current_iteration_id
_iteration_count
_session_iteration_count
_session_first_iteration

The active workspace changes every MAW cycle.

3. Target Architecture
New Workspace Layout
<Project>
│
├── lib/
│
├── <module>/
│   │
│   ├── Workspace/
│   │   ├── <circuit>.tsx
│   │   ├── eval_results/
│   │   ├── lib -> ../../../lib
│   │   ├── resources -> ../resources
│   │   ├── .skills/
│   │   └── <circuit>.scud
│   │
│   ├── Stable/
│   │
│   ├── Archives/
│   │   ├── 0001/
│   │   ├── 0002/
│   │   └── ...
│   │
│   └── resources/
4. New MAW Model
Previous Model
Workspace changes
Artifact copied forward
New Model
Workspace remains constant
Artifact evolves in-place
History captured via snapshots

MAW loop becomes:

Workspace
    ↓
Archive Snapshot
    ↓
Modify Workspace
    ↓
Evaluate
    ↓
Archive Snapshot

The active workspace never changes.

5. Conceptual Changes
Change #1

Replace:

current_iteration_path[module]

with:

workspace_path[module]
Rationale

Workspace becomes stable throughout ANA execution.

No path switching.

No iteration reconstruction.

Change #2

Remove:

previous_iteration_path
Rationale

History becomes filesystem history.

Archives/

becomes authoritative.

No runtime tracking required.

Change #3

Remove iteration counters

Delete:

_iteration_count
_session_iteration_count
_session_first_iteration
current_iteration_id
Rationale

Workspace lifecycle no longer depends on iteration creation.

Snapshot numbering belongs to archive management.

6. New WorkspaceManager Responsibilities
Create Workspace

New primitive:

create_workspace(module_name)

Creates:

Workspace/

and initializes symlinks.

Executed once.

Setup Workspace Links

Rename:

_setup_iteration_symlinks()

to:

_setup_workspace_links()

Executed once.

Links become persistent.

Archive Workspace

New primitive:

archive_workspace(module_name)

Behavior:

Workspace
    ↓
Archives/0001/

Snapshot contains:

tsx
eval_results
observations

No symlinks copied.

Prepare Workspace

Replace:

prepare_iteration_with_files()

with:

prepare_workspace()

Behavior:

overwrite workspace circuit

No directory creation.

7. Workspace Lifecycle
Synthesis Start
Create Workspace
Initialize Links
Copy Initial Circuit
MAW Correction Cycle
archive_workspace()

ANA modifies Workspace

VAP evaluates Workspace
Acceptance
populate_stable()

copies from:

Workspace

instead of:

Iteration
8. Functions Requiring Removal
Remove Entirely
create_new_iteration

Current responsibility:

create directory
copy previous files
switch workspace

No longer required.

_get_next_iteration_number

No longer required.

is_first_iteration

No longer required.

reset_first_iteration

No longer required.

get_iteration_count

No longer required.

get_session_iteration_count

No longer required.

move_iterations_to_archives

No longer required.

Archive becomes continuous operation.

get_current_iteration_path

Replace with:

get_workspace_path()
get_current_iteration_id

Remove.

9. Functions Requiring Refactor
load_project

Current behavior:

scan Iterations
restore latest
restore previous
restore counters

New behavior:

locate Workspace
set workspace_path

No reconstruction.

create_project

Must create:

Workspace/
Stable/
Archives/
resources/

instead of:

Iterations/
Stable/
Archives/
setup_modules

Replace:

Iterations/

with:

Workspace/
populate_stable

Current:

Stable ← Iteration

New:

Stable ← Workspace
get_circuit_tsx_path

Current:

current_iteration_path / file

New:

workspace_path / file
get_scud_path

Current:

current_iteration_path

New:

workspace_path
get_library_path

Current:

current_iteration_path/lib/imports

New:

workspace_path/lib/imports
get_workspace_info

Remove:

current_iteration_path
previous_iteration_path
iteration_count

Add:

workspace_path
archive_count

(optional)

resolve_resource_path

Current:

Iterations/<id>

New:

Workspace/

Affected resource types:

Circuit
Evaluation
10. New Runtime Invariant

Old invariant:

Latest iteration is current truth

New invariant:

Workspace is current truth

Archives are historical evidence only.

Stable remains accepted truth.

11. Dependency Analysis Targets

The following components are expected to contain direct dependencies on iteration semantics.

ANA State Machine (Outdated: No need to modify)

Potential usage:

create_new_iteration()
get_current_iteration_path()
get_current_iteration_id()
ANA Worker 1

Potential usage:

current_iteration_path

for TSX generation.

ANA Worker 2

Potential usage:

resolve_resource_path(
    resource_type="Circuit"
)
SyncClient

Potential usage:

iteration_id

in synchronization payloads.

VAP Protocol

Potential usage:

iteration_id

as artifact identifier.

AOSM

Potential usage:

workspace_info["iteration_count"]
workspace_info["current_iteration_path"]
Workspace Sync Logic

Potential usage:

Iterations/

hardcoded paths.

Runtime Workspace Manager

Potential usage:

Iterations/

directory assumptions.

Low Priority
UI

Potential usage:

current_iteration_path

display only.

12. Migration Strategy
Phase 1

Introduce:

workspace_path
archive_workspace()

without removing iteration code.

Maintain backward compatibility.

Phase 2

Refactor ANA-D to consume workspace APIs only.

No direct iteration access.

Phase 3

Remove iteration state variables.

Remove iteration directory creation.

Phase 4

Delete legacy iteration APIs.

Perform full dependency cleanup.

Final Architectural Position

The active design surface becomes:

Workspace/

The accepted design becomes:

Stable/

Historical attempts become:

Archives/

ANA continuously evolves a single workspace while WorkspaceManager records historical snapshots.

The MAW abstraction changes from:

Copy-On-Write Workspace Evolution

to:

Persistent Workspace + Snapshot History

while preserving all historical reasoning artifacts and VAP outputs.