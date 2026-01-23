# MCP Server Import Fixes

## Problem
The MCP server code was using relative imports (e.g., `from .core import ...`) which worked when the module was imported as a package, but failed when running scripts directly from the project root using `uv run python mcp_server/test_commit_log.py`.

## Solution
Changed all imports to use absolute imports with the `mcp_server` prefix, allowing the code to run from the project root.

## Files Modified

### 1. `mcp_server/main.py`
**Before:**
```python
from core import MCPServer
from tool_code.registry import tool_registry
from exceptions import InvalidToolCall, ToolNotFound, ToolNotInScope, SchemaValidationError
```

**After:**
```python
from mcp_server.core import MCPServer
from mcp_server.tool_code.registry import tool_registry
from mcp_server.exceptions import InvalidToolCall, ToolNotFound, ToolNotInScope, SchemaValidationError
```

### 2. `mcp_server/core.py`
**Before:**
```python
from exceptions import (...)
from tool import CommitTool
from tool_code.registry import ToolRegistry
```

**After:**
```python
from mcp_server.exceptions import (...)
from mcp_server.tool import CommitTool
from mcp_server.tool_code.registry import ToolRegistry
```

### 3. `mcp_server/tool_code/registry.py`
**Before:**
```python
from tool import CommitTool
from tool_code.schemas import ObservationCommit, FixProposalCommit
```

**After:**
```python
from mcp_server.tool import CommitTool
from mcp_server.tool_code.schemas import ObservationCommit, FixProposalCommit
```

### 4. `mcp_server/test_commit_log.py`
- Completely rewrote to use `httpx` and `subprocess` instead of `TestClient`
- Starts actual MCP server process for integration testing
- Properly cleans up server process after tests
- Added debug output for server startup failures

## Running Tests from Project Root

### MCP Server Tests
```bash
uv run python mcp_server/test_commit_log.py
```

### State Machine Integration Tests
```bash
uv run python ana_designer/test_sm_mcp_integration.py
```

## Test Results

Both test suites now pass when run from the project root:

✅ **MCP Server Tests** (8/8 passed)
- Commit observation
- Query all commits
- Commit fix proposal
- Query multiple commits
- Query with 'since' filter
- Query with 'endpoint' filter
- Query with combined filters
- Invalid tool call doesn't affect log

✅ **State Machine Integration Tests** (1/1 passed)
- MCP server auto-start
- Polling mechanism
- State transitions
- Cleanup

## Benefits

1. **Consistent execution**: All modules run from project root
2. **No path manipulation**: No need to modify `sys.path` or `PYTHONPATH`
3. **Works with uv**: Leverages uv's dependency management
4. **Clear module structure**: Explicit `mcp_server.` prefix shows module boundaries
