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

        # Rule 3: The last entry in semantic_operations before this evaluation must be:
        # operation == "INITIALIZE" and author == "WORKSPACE_MANAGER" (or "WORKSPACE_MANAER" due to typo)
        try:
            last_op = self.db.conn.execute(
                "SELECT op_name, author FROM semantic_operations ORDER BY id DESC LIMIT 1"
            ).fetchone()
        except Exception:
            last_op = None

        if not last_op:
            failures.append("Last semantic operation is not INITIALIZE by WORKSPACE_MANAGER")
        else:
            op_name = last_op["op_name"]
            author = last_op["author"]
            if op_name != "INITIALIZE" or author not in ("WORKSPACE_MANAGER", "WORKSPACE_MANAER"):
                failures.append("Last semantic operation is not INITIALIZE by WORKSPACE_MANAGER")

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
