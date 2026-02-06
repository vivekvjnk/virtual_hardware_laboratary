#!/bin/bash
set -e

# Start Librarian (VHL Library) in background
echo "Starting VHL Library Server..."
node dist/index.js &
LIBRARY_PID=$!

# Start VAP Server in background
echo "Starting VAP Server..."
node dist/vap/vapIndex.js &
VAP_PID=$!

# Start Agent WebSocket Server in background
echo "Starting Agent WebSocket Server..."
node dist/server/wsIndex.js &
WS_SERVER_PID=$!

# Wait for any process to exit
wait -n $LIBRARY_PID $VAP_PID $WS_SERVER_PID

# Exit with status of process that exited first
exit $?
