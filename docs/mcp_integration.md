# ANA-D State Machine MCP Integration

## Overview

The ANA-D State Machine has been successfully integrated with the MCP (Model Context Protocol) server to support **out-of-band commit observation**. This allows the state machine to observe committed messages independently of agent execution.

## Architecture

```
┌─────────────────────┐
│  ANA-D State        │
│  Machine            │
│                     │
│  ┌──────────────┐   │
│  │   OBSERVE    │   │──┐
│  │   State      │   │  │ 1. Start MCP Server
│  └──────────────┘   │  │
└─────────────────────┘  │
                         │
                         ▼
              ┌──────────────────────┐
              │   MCP Server         │
              │   (Port 8000)        │
              │                      │
              │  /mcp/observe        │◄──── 2. Observer Agent commits
              │  /mcp/commits        │
              └──────────────────────┘
                         │
                         │ 3. State machine polls
                         ▼
              ┌──────────────────────┐
              │   Commit Log         │
              │   (In-memory)        │
              └──────────────────────┘
```

## Key Components

### 1. MCP Server (`mcp_server/`)

- **`core.py`**: Contains `MCPServer` class with commit log storage
- **`main.py`**: FastAPI application with endpoints:
  - `POST /mcp/{endpoint}`: Commit structured messages
  - `GET /mcp/commits`: Query commit log with filtering
  - `GET /mcp/{endpoint}/tools`: List available tools

### 2. State Machine (`ana_designer/ana_d_sm.py`)

The `ANADStateMachine` class now includes:

- **MCP Server Management**:
  - `_ensure_mcp_server_running()`: Starts MCP server if not already running
  - `cleanup()`: Properly shuts down MCP server process

- **Polling Logic**:
  - `_poll_for_observation()`: Polls MCP commit log for new observations
  - Uses `last_commit_id` cursor to track processed commits

- **State Transitions**:
  - `OBSERVE` state now triggers MCP server, waits for observer agent, and polls for commits
  - Automatically extracts `verdict`, `issue_kind`, and updates internal state

## Workflow

### OBSERVE State Flow

1. **MCP Server Startup**
   - State machine checks if MCP server is running on port 8000
   - If not, starts it using `uv run` with required dependencies
   - Waits up to 15 seconds for server to be ready

2. **Observer Agent Trigger**
   - State machine triggers observer agent (placeholder for now)
   - Agent analyzes circuit/design and makes observations

3. **Commit to MCP**
   - Observer agent commits observation using `commit_observation` tool
   - Payload includes: `verdict`, `issue_kind`, `confidence`, `evidence_refs`, `notes`

4. **Polling for Commit**
   - State machine polls `GET /mcp/commits?since={last_commit_id}&endpoint=/mcp/observe`
   - Continues polling every 2 seconds until a commit is found
   - Extracts observation data from commit

5. **State Update**
   - Updates `error_class` based on `issue_kind`
   - Updates `intent_status` based on `verdict`
   - Transitions to `AUTHORIZE` state

## Commit Log Schema

Each commit entry in the log contains:

```json
{
  "commit_id": 0,
  "timestamp": "2026-01-22T22:47:10.602715",
  "endpoint": "/mcp/observe",
  "tool_name": "commit_observation",
  "message": {
    "type": "OBSERVATION_MESSAGE",
    "payload": {
      "verdict": "ISSUE_DETECTED",
      "issue_kind": "LOCAL_MECHANICAL",
      "confidence": 0.85,
      "evidence_refs": [...],
      "notes": "..."
    },
    "metadata": {
      "timestamp": "...",
      "tool": "commit_observation"
    }
  }
}
```

## Testing

### Unit Test: MCP Server

```bash
uv run --with fastapi --with uvicorn --with pydantic --with httpx \
  env PYTHONPATH=. python3 mcp_server/test_commit_log.py
```

Tests verify:
- Commit log growth on valid commits
- Monotonic `commit_id`
- Filtering by `since` and `endpoint`
- Invalid tool calls don't affect log

### Integration Test: State Machine + MCP

```bash
uv run --with httpx env PYTHONPATH=. \
  python3 ana_designer/test_sm_mcp_integration.py
```

Tests verify:
- MCP server starts automatically
- State machine polls for commits
- Observation data is correctly extracted
- State transitions work as expected
- Cleanup properly shuts down server

## API Usage

### Querying Commits

**Get all commits:**
```bash
curl http://localhost:8000/mcp/commits
```

**Get commits since ID 5:**
```bash
curl http://localhost:8000/mcp/commits?since=5
```

**Filter by endpoint:**
```bash
curl http://localhost:8000/mcp/commits?endpoint=/mcp/observe
```

### Making a Commit

```bash
curl -X POST http://localhost:8000/mcp/observe \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "commit_observation",
    "payload": {
      "verdict": "ISSUE_DETECTED",
      "issue_kind": "LOCAL_MECHANICAL",
      "confidence": 0.9,
      "evidence_refs": [],
      "notes": "Test observation"
    }
  }'
```

## Design Principles

### 1. **Polling Over Push**
- State machine actively polls for commits
- No callbacks, webhooks, or event listeners
- Mirrors VAP status polling model

### 2. **Agent-SDK Independence**
- MCP responses are not control signals
- State machine observes committed state via read APIs
- No dependency on agent execution flow

### 3. **Immutability**
- Commit log is append-only
- No deletion or mutation of entries
- Each commit has a monotonic ID

### 4. **Deterministic Behavior**
- Polling logic is deterministic
- State transitions based on observable data
- No race conditions or timing dependencies

## Future Enhancements

1. **Observer Agent Implementation**
   - Replace placeholder with actual agent invocation
   - Agent should use MCP tools to commit observations

2. **Timeout Handling**
   - Add configurable timeout for polling
   - Handle cases where observer never commits

3. **Persistent Storage**
   - Move commit log from in-memory to persistent storage
   - Enable recovery after crashes

4. **Multiple Observers**
   - Support multiple concurrent observer agents
   - Handle commit ordering and conflicts

## Troubleshooting

### MCP Server Won't Start

- Check if port 8000 is already in use: `lsof -i :8000`
- Verify `uv` is installed: `uv --version`
- Check dependencies are available

### Polling Never Completes

- Verify MCP server is running: `curl http://localhost:8000/health`
- Check observer agent is actually making commits
- Review MCP server logs for errors

### State Machine Hangs

- Polling is blocking by design
- Use Ctrl+C to interrupt
- Cleanup will properly shut down MCP server
