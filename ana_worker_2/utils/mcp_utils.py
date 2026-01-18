import json
import re
from typing import Any, Dict, List, Optional, Union
from fastmcp.mcp_config import MCPConfig
from openhands.sdk.mcp import MCPClient, MCPToolObservation
from openhands.sdk.mcp.utils import log_handler
from openhands.sdk.logger import get_logger

# Configure logger
logger = get_logger(__name__)

class MCPInvoker:
    """
    A standalone invoker for MCP tools, independent of the Agent framework.
    This class allows you to connect to an MCP server via a URL (SSE) and 
    invoke its tools synchronously or asynchronously.
    """
    def __init__(self, url_or_config: Union[str, Dict[str, Any]]):
        """
        Initialize the invoker.
        
        Args:
            url_or_config: Either a string URL (for SSE) or a full MCP configuration dictionary.
        """
        if isinstance(url_or_config, str):
            # If it's a string, assume it's an SSE URL
            config_dict = {
                "mcpServers": {
                    "remote_server": {
                        "url": url_or_config
                    }
                }
            }
        else:
            config_dict = url_or_config

        self.config = MCPConfig.model_validate(config_dict)
        # Initialize the MCPClient with the configuration
        # MCPClient handles the background event loop via AsyncExecutor
        self.client = MCPClient(self.config, log_handler=log_handler)

    async def _list_tools_async(self) -> List[Dict[str, Any]]:
        """
        Internal async method to list tools.
        """
        async with self.client:
            tools = await self.client.list_tools()
            return [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                }
                for tool in tools
            ]

    async def _call_tool_async(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> MCPToolObservation:
        """
        Internal async method to call a tool.
        """
        if arguments is None:
            arguments = {}
        
        async with self.client:
            # call_tool_mcp is the underlying method in fastmcp.Client used by openhands-sdk
            result = await self.client.call_tool_mcp(name=tool_name, arguments=arguments)
            # Process the result into a standard MCPToolObservation
            return MCPToolObservation.from_call_tool_result(tool_name=tool_name, result=result)

    def list_tools(self, timeout: float = 30.0) -> List[Dict[str, Any]]:
        """
        Synchronously list all tools available on the MCP server.
        """
        return self.client.call_async_from_sync(
            self._list_tools_async,
            timeout=timeout
        )

    def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None, timeout: float = 300.0) -> MCPToolObservation:
        """
        Synchronously call a specific tool on the MCP server.
        """
        json_results = sanitize_mcp_tool_observation(
            self.client.call_async_from_sync(
                self._call_tool_async, 
                tool_name=tool_name, 
                arguments=arguments, 
                timeout=timeout
            )
        )
        return json_results

    def close(self):
        """
        Close the client and cleanup resources.
        """
        self.client.sync_close()

def call_mcp_function(url: str, tool_name: str, arguments: Optional[Dict[str, Any]] = None, timeout: float = 300.0) -> MCPToolObservation:
    """
    Convenience function to call an MCP tool from a given URL.
    
    Example:
        result = call_mcp_function("http://localhost:8081/mcp", "VAP_status", {"id": "123"})
        print(result.text)
    """
    invoker = MCPInvoker(url)
    try:
        return invoker.call_tool(tool_name, arguments, timeout)
    finally:
        invoker.close()

def list_mcp_tools(url: str, timeout: float = 30.0) -> List[Dict[str, Any]]:
    """
    Convenience function to list MCP tools from a given URL.
    """
    invoker = MCPInvoker(url)
    try:
        return invoker.list_tools(timeout)
    finally:
        invoker.close()

def sanitize_mcp_tool_observation(mcp_observation: MCPToolObservation) -> str:
    """
    Extracts and parses JSON from a string that may contain 
    extra text, logs, or tool execution headers.
    """
    if not mcp_observation:
        return None

    # 2. If it fails, use Regex to find the JSON block
    # re.DOTALL allows '.' to match newlines
    match = re.search(r'(\{.*\}|\[.*\])', mcp_observation.text, re.DOTALL)
    logger.debug(f"Sanitized MCP observation: {match.group(0) if match else 'No match found'}")
    if match:
        sanitized_json = mcp_observation.text.replace(match.group(0), '').strip()   
        return sanitized_json
    raise ValueError(f"No JSON object or array found in the input string: {mcp_observation.text}...")
