#!/bin/bash
set -e

# Start Librarian (VHL Library) in background
echo "Starting VHL Library Server..."
node dist/index.js &
LIBRARY_PID=$!


# Start Agent WebSocket Server in background
echo "Starting Agent WebSocket Server..."
node dist/server/wsIndex.js &
WS_SERVER_PID=$!


# Start Workspace WebSocket Client in background
echo "Starting Workspace WebSocket Client..."
node dist/workspace/index.js &
WS_CLIENT_PID=$!

# Start ANA MCP Server in background (HTTP mode)
echo "Starting ANA Commit MCP Server..."
export ANA_TRANSPORT=http
export ANA_PORT=8081
node dist/mcp/ana/index.js &
ANA_PID=$!

# Wait for any process to exit
wait -n $LIBRARY_PID $WS_SERVER_PID $WS_CLIENT_PID $ANA_PID

# Exit with status of process that exited first
exit $?
