from typing import Tuple, List
from vhl_common.project_state_manager.evaluators.abstract_evaluator import AbstractEvaluator

AGENT_ID = "ARCHY_EVALUATOR"
OPERATION_NAME = "ARCHY_EVAL"

class ArchyEvaluator(AbstractEvaluator):
    """
    Archy Operation Evaluator.
    Determines whether the archy workflow completed successfully.
    Steps to determine success:
    1. Check if last recorded operation in semantic_operations is authord by "ARCHY" and has op_name "SCUD_GENERATION"
    2. Check if last recorded semantic operation has status "SUCCESS"
    3. If both conditions above are met, return True. Otherwise, return False with a message indicating the reason for failure.
    """
    @property
    def operation_name(self) -> str:
        return OPERATION_NAME
    @property
    def agent_id(self) -> str:
        return AGENT_ID

    def check_rules(self) -> Tuple[bool, str]:
        # Check if last recorded operation in semantic_operations is authord by "ARCHY" and has op_name "SCUD_GENERATION"
        try:
            last_op = self.db.conn.execute(
                "SELECT op_name, author, status FROM semantic_operations ORDER BY id DESC LIMIT 1"
            ).fetchone()
        except Exception:
            return False, "No semantic operations found in the database."

        if not last_op:
            return False, "No semantic operations found in the database."
        
        op_name = last_op["op_name"]
        author = last_op["author"]
        status = last_op["status"]

        if author != "ARCHY" or op_name != "SCUD_GENERATION":
            return False, f"Last operation is not SCUD_GENERATION by ARCHY. Found op_name={op_name}, author={author}."

        if status != "SUCCESS":
            return False, f"Last SCUD_GENERATION operation by ARCHY did not complete successfully. Status: {status}."

        return True, "Archy workflow completed successfully."