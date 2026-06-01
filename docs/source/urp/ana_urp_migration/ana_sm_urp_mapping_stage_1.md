# ANA URP — Stage 1 Walkthrough

## What was built

Two files implement Stage 1 — compressing the ANA state machine into URP pre/post conditions.

---

## New file: `ana_evaluator.py`

[ana_evaluator.py](file:///home/vivekv/Documents/VHL-System/vhl-agent-backend/ana/ana_agent/ana_evaluator.py)

| Constant | Value |
|---|---|
| `AGENT_ID` | `"ANA_EVALUATOR"` |
| `OPERATION_NAME` | `"CIRCUIT_SYNTHESIS"` |

`AnaEvaluator` extends `AbstractEvaluator`. Its `evaluate()` is called from
post-conditions after a VAP ACCEPT to write the canonical **"synthesis has
happened"** marker into `semantic_operations`. Pre-conditions query this marker
to decide operating mode on every new invocation.

---

## Modified file: `urp_ana.py`

[urp_ana.py](file:///home/vivekv/Documents/VHL-System/vhl-agent-backend/ana/ana_agent/ana_urp/urp_ana.py)

### State machine → URP mapping

| Legacy SM node | URP hook | Key logic |
|---|---|---|
| `handle_init` | `_check_preconditions` | DB query for prior synthesis; create/seed iteration dir |
| `handle_observe` | *(removed)* | Observer agent eliminated; ANA self-corrects |
| `handle_trigger_w1` | `process` | Invoke `run_ana_w1_agent` in synthesis or error-correction mode |
| `handle_trigger_w2` | `_check_postconditions` | Run `ANA_validation_agent` (W2) |
| `handle_authorize` | `_check_postconditions` | Act on VAP ACCEPT / REJECT |
| `handle_exit_success` | `_check_postconditions` | Promote Stable/, archive, record op, condense |
| `handle_prepare_hil` / `hil_wait` | *(removed)* | HIL replaced by URP POSTCONDITIONS_VIOLATED flow |

### Design decisions

**First-synthesis detection via DB (not flag)**
Pre-conditions query `semantic_operations` for an `ANA_EVALUATOR / CIRCUIT_SYNTHESIS / SUCCESS` row for the module. No `is_first_iteration` flag needed.

**No Observer agent**
Error analysis is folded directly into ANA-W1 via `_pending_error_message`. On
a REJECT, evaluation logs are read, summarised into a structured string, and
stashed on the agent. The next `process()` call injects them as observations —
ANA-W1 sees them as error-correction instructions and self-corrects.

**Condensation on every exit (ACCEPT and REJECT)**
`_condense_conversation()` is called at the end of both VAP paths. This
implements the "condensation approach" from the design discussion — every
error-correction iteration starts with a lean history, preventing context
explosion across many auto-fix cycles.

**Module-ID-aware WorkspaceManager**
All WorkspaceManager calls pass `module_name=self.module_name`, utilising the
module abstraction layer added in the `feat(workspacemanager ana support)` commit.

### Context dataclass additions

```python
@dataclass(frozen=True)
class AnaContext:
    module_name: str
    workspace: WorkspaceManager
    sqlite_manager: SQLiteManager
    web_socket_client: VHLWebSocketClient   # new — needed by W2
    sync_client: SyncClient                 # new — needed by W2
    project_id: str                         # new — needed by W2
    config: AnaConfig = field(default_factory=AnaConfig)
```

### Post-condition flow (VAP ACCEPT)

```
W2 validate_circuit()
  → ACCEPT
    → workspace_manager.populate_stable()
    → workspace_manager.move_iterations_to_archives()
    → workspace_manager.record_operation(CIRCUIT_SYNTHESIS, SUCCESS)
    → AnaEvaluator.evaluate()          ← stamps evaluator signature in DB
    → sync_client.sync_library()       ← sync with runtime
    → conversation.condense()          ← trim history
    → return (True, ...)
```

### Post-condition flow (VAP REJECT)

```
W2 validate_circuit()
  → REJECT
    → read eval_results/ logs
    → stash error summary in self._pending_error_message
    → conversation.condense()          ← fresh start for next iteration
    → return (False, reject_reason)    ← triggers TASK_POSTCONDITIONS_VIOLATED
      next invocation: process() injects pending_error_message as observations
```

---

## Verification

```
python -c "import ast; ast.parse(open('ana/ana_agent/ana_evaluator.py').read()); print('OK')"
python -c "import ast; ast.parse(open('ana/ana_agent/ana_urp/urp_ana.py').read()); print('OK')"
```

Both files parse cleanly. `AGENT_ID` and `OPERATION_NAME` import correctly from the venv.
