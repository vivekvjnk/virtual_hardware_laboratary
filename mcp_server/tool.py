

from typing import Type, Literal, Dict, Any
from pydantic import BaseModel


class CommitTool:
    def __init__(
        self,
        name: str,
        schema: Type[BaseModel],
        target_channel: str,
        visibility_scope: Literal["/mcp/observe", "/mcp/prepare_fix"]
    ):
        self.name = name
        self.schema = schema
        self.target_channel = target_channel
        self.visibility_scope = visibility_scope

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "schema": self.schema.model_json_schema(),
            "target_channel": self.target_channel,
            "visibility_scope": self.visibility_scope,
        }

