

import json
from datetime import datetime
from typing import Any, Dict, List
from pydantic import ValidationError

from .exceptions import (
    InvalidToolCall,
    ToolNotFound,
    ToolNotInScope,
    SchemaValidationError,
)
from .tool import CommitTool
from .tool_code.registry import ToolRegistry


class MCPServer:
    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry

    def _validate_tool_call(
        self, endpoint: str, tool_name: str, payload: Dict[str, Any]
    ) -> CommitTool:
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            raise ToolNotFound(f"Tool '{tool_name}' not found.")

        if tool.visibility_scope != endpoint:
            raise ToolNotInScope(
                f"Tool '{tool_name}' is not visible in endpoint '{endpoint}'."
            )

        try:
            tool.schema(**payload)  # Validate payload against the tool's schema
        except ValidationError as e:
            raise SchemaValidationError(f"Schema validation failed for tool '{tool_name}': {e}")

        return tool

    def commit(self, endpoint: str, tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            tool = self._validate_tool_call(endpoint, tool_name, payload)
            
            # Emit immutable message
            message = {
                "type": tool.target_channel,
                "payload": payload,
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "tool": tool.name,
                },
            }
            return {"status": "ACK", "message": message}
        except (ToolNotFound, ToolNotInScope, SchemaValidationError) as e:
            raise InvalidToolCall(str(e))
        except Exception as e:
            raise MCPException(f"An unexpected error occurred: {e}")

    def get_available_tools(self, endpoint: str) -> List[Dict[str, Any]]:
        tools = self.tool_registry.get_tools_for_scope(endpoint)
        return [tool.to_dict() for tool in tools]

