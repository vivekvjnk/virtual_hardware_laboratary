

from typing import Dict, List
from ..tool import CommitTool
from .schemas import ObservationCommit, FixProposalCommit


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, CommitTool] = {}
        self._scoped_tools: Dict[str, List[CommitTool]] = {
            "/mcp/observe": [],
            "/mcp/prepare_fix": [],
        }
        self.register_tools()

    def register(self, tool: CommitTool):
        if tool.name in self._tools:
            raise ValueError(f"Tool with name {tool.name} already registered.")
        self._tools[tool.name] = tool
        self._scoped_tools[tool.visibility_scope].append(tool)

    def get_tool(self, name: str) -> CommitTool:
        return self._tools.get(name)

    def get_tools_for_scope(self, scope: str) -> List[CommitTool]:
        return self._scoped_tools.get(scope, [])

    def register_tools(self):
        # Commit Tool 1 — Observation
        self.register(
            CommitTool(
                name="commit_observation",
                schema=ObservationCommit,
                target_channel="OBSERVATION_MESSAGE",
                visibility_scope="/mcp/observe",
            )
        )

        # Commit Tool 2 — Prepare Fix (Proposal Only)
        self.register(
            CommitTool(
                name="commit_fix_proposal",
                schema=FixProposalCommit,
                target_channel="FIX_PROPOSAL_MESSAGE",
                visibility_scope="/mcp/prepare_fix",
            )
        )

tool_registry = ToolRegistry()

