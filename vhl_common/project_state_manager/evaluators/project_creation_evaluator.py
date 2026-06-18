from typing import Tuple, List
from vhl_common.project_state_manager.evaluators.abstract_evaluator import AbstractEvaluator

AGENT_ID = "PROJECT_CREATION_EVALUATOR"
OPERATION_NAME = "CREATE_PROJECT_EVAL"

class ProjectCreationEvaluator(AbstractEvaluator):
    """
    Project Creation Operation Evaluator.
    Determines whether the project creation workflow completed successfully.
    """
    agent_id = AGENT_ID

    @property
    def operation_name(self) -> str:
        return OPERATION_NAME

    def check_rules(self) -> Tuple[str, str]:
        failures: List[str] = []

        # Rule 1: project_modules contains >= 1 entry
        try:
            modules = self.db.get_project_modules()
        except Exception:
            modules = []

        if not modules:
            failures.append("No entries found in project_modules")

        # Rule 2: Every active module has >= 1 resource in module_resources
        for mod in modules:
            mod_id = mod.get("id")
            mod_name = mod.get("module_name")
            try:
                resources = self.db.get_module_resources(mod_id)
            except Exception:
                resources = []
            
            if not resources:
                failures.append(f"Module {mod_id} has no associated resources")

        # Rule 3: Check that required operations have occurred
        # Operation 1: INITIALIZE by WORKSPACE_MANAGER
        try:
            init_op = self.db.conn.execute(
                "SELECT 1 FROM semantic_operations WHERE op_name = 'INITIALIZE' AND author = 'WORKSPACE_MANAGER'"
            ).fetchone()
        except Exception:
            init_op = None
        
        if not init_op:
            failures.append("INITIALIZE operation by WORKSPACE_MANAGER not found")

        # Operation 2: RUNTIME_INITIALIZATION by AOSM
        try:
            runtime_init_op = self.db.conn.execute(
                "SELECT 1 FROM semantic_operations WHERE op_name = 'RUNTIME_INITIALIZATION' AND author = 'AOSM'"
            ).fetchone()
        except Exception:
            runtime_init_op = None

        if not runtime_init_op:
            failures.append("RUNTIME_INITIALIZATION operation by AOSM not found")

        # Rule 4: artifact_snapshots contains >= 1 snapshot associated with the INITIALIZE operation
        try:
            init_snapshots = self.db.conn.execute(
                """
                SELECT count(*) FROM artifact_snapshots s
                JOIN semantic_operations o ON s.id = o.artifact_ref_id
                WHERE o.op_name = 'INITIALIZE'
                """
            ).fetchone()[0]
        except Exception:
            init_snapshots = 0

        if init_snapshots == 0:
            failures.append("No artifact snapshot found with INITIALIZE commit message")

        # Determine overall result
        if failures:
            result = "FAILURE"
            description = "; ".join(failures)
        else:
            result = "SUCCESS"
            description = "All criteria met"

        return result, description
