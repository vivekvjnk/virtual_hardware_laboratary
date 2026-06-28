from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any, Optional
from vhl_common.project_state_manager.sqlite_manager import SQLiteManager

class AbstractEvaluator(ABC):
    """
    Abstract base class for all VHL Operation Evaluators.
    Enforces the pattern: SQLite (facts) -> Evaluator -> SQLite (semantic judgment).
    """

    def __init__(self, db: SQLiteManager):
        self.db = db

    @property
    @abstractmethod
    def operation_name(self) -> str:
        """
        The name of the semantic operation being evaluated, e.g., 'CREATE_PROJECT_EVAL'.
        """
        pass

    @property
    @abstractmethod
    def agent_id(self) -> str:
        """The ID of the agent performing the evaluation."""
        pass

    @abstractmethod
    def check_rules(self) -> Tuple[str, str]:
        """
        Applies validation rules to the database state.
        
        Returns:
            Tuple[str, str]: (result, description)
                result: "SUCCESS" or "FAILURE"
                description: "All criteria met" on success, or list of failures on failure.
        """
        pass

    def evaluate(self, snapshot_id: Optional[int] = None) -> Tuple[str, str]:
        """
        Executes the evaluation rules and commits the semantic operation judgment
        into the database under the given or latest snapshot ID.
        """
        result, description = self.check_rules()

        # Find latest snapshot if not provided
        if snapshot_id is None:
            row = self.db.conn.execute("SELECT id FROM artifact_snapshots ORDER BY id DESC LIMIT 1").fetchone()
            if not row:
                # If no snapshot exists, we can't link the semantic operation.
                # In this case, we return the result but don't persist it.
                # This prevents a total crash while still reporting the failure.
                return "FAILURE", f"No artifact snapshots found in database. Evaluation could not be recorded. Original result: {result}, {description}"
            snapshot_id = row["id"]

        # Atomically write semantic operation
        try:
            self.db.begin()
            self.db.insert_semantic_operation(
                snapshot_id=snapshot_id,
                op_name=self.operation_name,
                author=self.agent_id,
                status=result,
                payload={"description": description}
            )
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e

        return result, description
