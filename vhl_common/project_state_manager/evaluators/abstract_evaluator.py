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
    def evaluate(self) -> Tuple[str, str]:
        """
        Applies validation rules to the database state.
        
        Returns:
            Tuple[str, str]: (result, description)
                result: "SUCCESS" or "FAILURE"
                description: "All criteria met" on success, or list of failures on failure.
        """
        pass

    def run(self, snapshot_id: int) -> Tuple[str, str]:
        """
        Runs the evaluation and atomically records the semantic operation in the ledger.
        """
        result, description = self.evaluate()
        
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
