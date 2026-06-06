from abc import ABC, abstractmethod
from vhl_common.urp.data_types import LastTaskOutcome


class AbstractController(ABC):
    """Abstract base class for all workflow and system controllers."""

    @property
    @abstractmethod
    def controller_id(self) -> str:
        """The unique identifier for this controller plugin."""
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        """The priority of this controller's claims (higher wins arbitration)."""
        pass

    @abstractmethod
    async def on_acquired(self, agent_id: str) -> None:
        """Callback invoked when this controller acquires authority over an agent."""
        pass

    @abstractmethod
    async def on_released(self, agent_id: str) -> None:
        """Callback invoked when this controller releases authority over an agent."""
        pass

    @abstractmethod
    async def handle_outcome(self, agent_id: str, outcome: LastTaskOutcome) -> None:
        """Callback invoked when a managed agent publishes a task outcome."""
        pass
