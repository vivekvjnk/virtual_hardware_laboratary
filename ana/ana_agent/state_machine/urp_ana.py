from vhl_common.urp.abstract_urp import AbstractURPAgent
from vhl_common.urp.data_types import AgentDescriptor, MessageEnvelope
from workspace.manager import WorkspaceManager

class AnaURPAgent(AbstractURPAgent):
    """
    Ana URP Agent for Virtual Hardware Laboratory.
    Handles project creation, iteration management, and symbolic link setup specific to Ana.
    """
    def __init__(self, workspace_manager: WorkspaceManager, debug: bool = False):
        super().__init__(workspace_manager, debug)