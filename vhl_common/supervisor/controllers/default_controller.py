from vhl_common.urp.data_types import LastTaskOutcome
from .abstract_controller import AbstractController


class DefaultController(AbstractController):
    """The default controller plugin that manages idle or unclaimed agents."""

    def __init__(self, controller_id: str = "default_controller", priority: int = 0):
        self._controller_id = controller_id
        self._priority = priority

    @property
    def controller_id(self) -> str:
        return self._controller_id

    @property
    def priority(self) -> int:
        return self._priority

    async def on_acquired(self, agent_id: str) -> None:
        pass

    async def on_released(self, agent_id: str) -> None:
        pass

    async def handle_outcome(self, agent_id: str, outcome: LastTaskOutcome) -> None:
        pass
