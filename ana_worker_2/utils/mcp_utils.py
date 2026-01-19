import json
import re
from typing import Any, Dict, List, Optional, Union
from fastmcp.mcp_config import MCPConfig
from openhands.sdk.mcp import MCPClient, MCPToolObservation
from openhands.sdk.mcp.utils import log_handler
from openhands.sdk.logger import get_logger

# Configure logger
logger = get_logger(__name__)
import os
print(f"DEBUG: mcp_utils.py loaded from {os.path.abspath(__file__)}")

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

    text = mcp_observation.text.strip()
    
    # 1. Try to parse directly
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    # 2. Remove common MCP execution prefixes
    # Example: "[Tool 'VAP_init' executed.]"
    text = re.sub(r'^\[Tool \'.*?\' executed\.\]', '', text).strip()
    
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    # 3. Use Regex to find the largest JSON-like block (object or array)
    # We look for the first '{' or '[' and the last '}' or ']'
    obj_start = text.find('{')
    obj_end = text.rfind('}')
    arr_start = text.find('[')
    arr_end = text.rfind(']')
    
    candidates = []
    if obj_start != -1 and obj_end != -1 and obj_end > obj_start:
        candidates.append(text[obj_start:obj_end+1])
    if arr_start != -1 and arr_end != -1 and arr_end > arr_start:
        candidates.append(text[arr_start:arr_end+1])
        
    # Sort by length descending to find the most complete block
    candidates.sort(key=len, reverse=True)
    
    for cand in candidates:
        try:
            json.loads(cand)
            logger.debug(f"Sanitized MCP observation: {cand}")
            return cand
        except json.JSONDecodeError:
            continue
    
    raise ValueError(f"No valid JSON object or array found in the input string: {mcp_observation.text[:100]}...")
