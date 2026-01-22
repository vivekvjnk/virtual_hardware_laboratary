

class MCPException(Exception):
    """Base exception for MCP server errors."""
    pass


class InvalidToolCall(MCPException):
    """Raised when a tool call is malformed or invalid."""
    pass


class ToolNotFound(MCPException):
    """Raised when a requested tool is not found in the registry."""
    pass


class ToolNotInScope(MCPException):
    """Raised when a tool is called from the wrong endpoint/scope."""
    pass


class SchemaValidationError(MCPException):
    """Raised when data fails schema validation."""
    pass


