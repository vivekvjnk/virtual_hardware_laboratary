#!/bin/bash
set -e

# Start Agent WebSocket Server in background
echo "Starting Agent WebSocket Server..."
node dist/server/wsIndex.js &
WS_SERVER_PID=$!

# Start Workspace WebSocket Client in background
echo "Starting Workspace WebSocket Client..."
# The VHLRuntime will automatically start 'tsci dev' on port 3020 
# during its connection sequence.
node dist/workspace/index.js &
WS_CLIENT_PID=$!


# Start Terminal MCP Server in background (SSE mode)
echo "Starting Terminal MCP Server..."
export VHL_TERMINAL_MCP_PORT=8082
/app/venv/bin/python3 src/mcp/python_servers/terminal_server.py &
TERMINAL_PID=$!

# Start UI Snapshot MCP Server in background
echo "Starting UI Snapshot MCP Server..."
export SNAPSHOT_PORT=8083
node dist/mcp/ui_snapshot/index.js &
SNAPSHOT_PID=$!

# Wait for any process to exit
# Note: TSCI_PID is not used here as tsci dev is now a child of the VHLRuntime
wait -n $WS_SERVER_PID $WS_CLIENT_PID $ANA_PID $TERMINAL_PID $SNAPSHOT_PID

# Exit with status of process that exited first
exit $?
