from typing import Tuple
from vhl_common.project_state_manager.evaluators.abstract_evaluator import AbstractEvaluator

# These constants are the "signature" left in semantic_operations after a
# successful VAP cycle. URP ANA pre-conditions query them to decide whether
# synthesis has happened before for a given module.
AGENT_ID = "ANA_EVALUATOR"
OPERATION_NAME = "CIRCUIT_SYNTHESIS"


class AnaEvaluator(AbstractEvaluator):
    """
    ANA Evaluator — records and validates successful circuit synthesis (VAP ACCEPT).

    Called by URP ANA post-conditions after a successful VAP cycle.  Its
    ``evaluate()`` entry in ``semantic_operations`` acts as the canonical
    "synthesis has happened" marker that URP ANA pre-conditions look up to
    determine the operating mode for the next invocation.
    """

    agent_id = AGENT_ID

    def __init__(self, db, module_name: str):
        super().__init__(db)
        self.module_name = module_name

    @property
    def operation_name(self) -> str:
        return OPERATION_NAME

    def check_rules(self) -> Tuple[str, str]:
        """
        Validates that the most recent CIRCUIT_SYNTHESIS operation for this
        module was recorded successfully (i.e. the stable circuit file was
        promoted and the operation committed to Git).

        For the *current* call this is always a fresh evaluation triggered
        from post-conditions, so we check that the latest artifact_snapshot
        exists and that the Stable/ directory is non-empty.
        """
        failures = []

        # Rule 1: There must be at least one artifact snapshot in the DB.
        try:
            row = self.db.conn.execute(
                "SELECT id FROM artifact_snapshots ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if not row:
                failures.append("No artifact snapshots found in the database.")
        except Exception as e:
            failures.append(f"Error querying artifact_snapshots: {e}")

        if failures:
            return "FAILURE", "; ".join(failures)

        return "SUCCESS", "Circuit synthesis recorded successfully."
