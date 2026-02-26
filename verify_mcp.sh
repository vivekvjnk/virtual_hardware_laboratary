#!/bin/bash

# Configuration
MCP_URL="http://127.0.0.1:8082"
TOOL_NAME="run_terminal_command"

echo "=== VHL-Library-Terminal Health Check ==="

echo -n "Checking connectivity to $MCP_URL/sse... "
# For SSE streams, curl will hang waiting for more data. 
# We use --max-time to capture the initial response code quickly.
STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 "$MCP_URL/sse")

if [ "$STATUS" -eq 200 ] || [ "$STATUS" -eq 307 ] || [ "$STATUS" -eq 000 ]; then
    # Note: status 000 is expected if curl times out after receiving the headers but before the stream "ends"
    if [ "$STATUS" -eq 000 ]; then
        # Check if the port is actually open since 000 might mean no response
        if nc -z 127.0.0.1 8082; then
            echo "OK (Stream Active)"
        else
            echo "FAILED (Link Down)"
            exit 1
        fi
    else
        echo "OK ($STATUS)"
    fi
else
    echo "FAILED ($STATUS)"
    echo "Error: Could not reach MCP server. Status code was $STATUS."
    exit 1
fi

# 2. Extract Session ID from SSE connection
echo -n "Initializing session... "
# The SSE endpoint returns an 'endpoint' query param in the first event usually, 
# but fastmcp/sse specifically provides a message endpoint.
# Let's try to just get the SSE stream start to see if it's active.
SSE_INIT=$(curl -s -N --max-time 2 "$MCP_URL/sse")
if [[ -z "$SSE_INIT" ]]; then
    # Some implementations wait for a message. Let's look for the session ID if it's in the URL
    # In many SSE MCP implementations, you hit /sse to get a redirect or session ID.
    echo "Stream started."
else
    echo "Stream data received."
fi

# 3. List Tools (JSON-RPC)
# Note: For SSE MCP, we usually POST to /messages or similar. 
# fastmcp uses /messages with a sessionId.
echo "Listing tools via JSON-RPC..."
curl -s -X POST "$MCP_URL/messages" \
     -H "Content-Type: application/json" \
     -d '{
       "jsonrpc": "2.0",
       "id": 1,
       "method": "tools/list"
     }' | python3 -m json.tool

# 4. Test Terminal Command
echo "Executing 'whoami' via terminal tool..."
curl -s -X POST "$MCP_URL/messages" \
     -H "Content-Type: application/json" \
     -d '{
       "jsonrpc": "2.0",
       "id": 2,
       "method": "tools/call",
       "params": {
         "name": "'"$TOOL_NAME"'",
         "arguments": {
           "command": "whoami"
         }
       }
     }' | python3 -m json.tool

echo "=== Verification Complete ==="
