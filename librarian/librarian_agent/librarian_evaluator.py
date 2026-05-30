from typing import Tuple
from vhl_common.project_state_manager.evaluators.abstract_evaluator import AbstractEvaluator

AGENT_ID = "LIBRARIAN_EVALUATOR"
OPERATION_NAME = "LIBRARIAN_EVAL"


class LibrarianEvaluator(AbstractEvaluator):
    """
    Librarian Operation Evaluator.
    Determines whether the librarian workflow completed successfully.

    Steps to determine success:
    1. Fetch the last operation in ``semantic_operations`` committed by
       ``<module_name>.librarian`` (the agent ID used in AOSM.register_agents).
    2. Check if the operation status is ``SUCCESS``.
    3. Return ``SUCCESS`` if the condition above is met, otherwise return
       ``FAILURE`` with a descriptive message.
    """

    @property
    def operation_name(self) -> str:
        return OPERATION_NAME

    @property
    def agent_id(self) -> str:
        return AGENT_ID

    def __init__(self, db, module_name: str):
        super().__init__(db)
        self.module_name = module_name

    def check_rules(self) -> Tuple[str, str]:
        # The agent ID follows the convention established in AOSM.register_agents:
        #   "{module_name}.librarian"
        agent_id = f"{self.module_name}.librarian"
        try:
            last_op = self.db.conn.execute(
                "SELECT op_name, author, status FROM semantic_operations "
                "WHERE author = ? ORDER BY id DESC LIMIT 1",
                (agent_id,)
            ).fetchone()
        except Exception as e:
            return "FAILURE", f"Failed to query semantic_operations: {e}"

        if not last_op:
            return "FAILURE", f"No semantic operations found for agent '{agent_id}'."

        status = last_op["status"]

        if status != "SUCCESS":
            return "FAILURE", (
                f"Last operation by '{agent_id}' (op_name={last_op['op_name']}) "
                f"did not complete successfully. Status: {status}."
            )

        return "SUCCESS", f"Librarian workflow completed successfully for module '{self.module_name}'."
