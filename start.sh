#!/bin/bash
set -e

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
export ANA_PORT=${VAP_PORT:-8081}
node dist/mcp/ana/index.js &
ANA_PID=$!

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

# Start tscircuit-cli server in background (Primary UI and Proxy)
echo "Starting tscircuit-cli server..."
export TSCI_SKIP_CLI_UPDATE=true
tsci dev /app/workspace/index.tsx --port 3020 &
TSCI_PID=$!

# Wait for any process to exit
wait -n $WS_SERVER_PID $WS_CLIENT_PID $ANA_PID $TERMINAL_PID $SNAPSHOT_PID $TSCI_PID

# Exit with status of process that exited first
exit $?
