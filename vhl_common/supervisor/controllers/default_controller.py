from vhl_common.urp.data_types import LastTaskOutcome
from .abstract_controller import AbstractController
import logging
logger = logging.getLogger(__name__)

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
        logger.info(f"[{self.controller_id}] Acquired control of agent '{agent_id}'")
        pass

    async def on_released(self, agent_id: str) -> None:
        logger.info(f"[{self.controller_id}] Releasing control of agent '{agent_id}'")
        pass

    async def handle_outcome(self, agent_id: str, outcome: LastTaskOutcome) -> None:
        logger.info(f"[{self.controller_id}] Received outcome for agent '{agent_id}': {outcome}")
        pass
