#!/bin/bash

# Configuration
PORT=${SNAPSHOT_PORT:-8083}
URL="http://0.0.0.0:$PORT/mcp"

echo "🚀 Starting MCP Server Validation on $URL"

# 1. List available tools
echo "--- Testing: List Tools ---"
curl -s -X POST "$URL" \
     -H "Content-Type: application/json" \
     -d '{
       "jsonrpc": "2.0",
       "id": 1,
       "method": "tools/list",
       "params": {}
     }' | jq .

# 2. Get Schematic Snapshot
echo -e "\n--- Testing: get_schematic_snapshot ---"
SCHEMATIC_RESPONSE=$(curl -s -X POST "$URL" \
     -H "Content-Type: application/json" \
     -d '{
       "jsonrpc": "2.0",
       "id": 2,
       "method": "tools/call",
       "params": {
         "name": "get_schematic_snapshot",
         "arguments": {}
       }
     }')

# Extract and save SVG if successful
if echo "$SCHEMATIC_RESPONSE" | jq -e '.result.content[0].text' > /dev/null; then
    # The text is double-encoded JSON because of your jsonResult helper
    echo "$SCHEMATIC_RESPONSE" | jq -r '.result.content[0].text' | jq -r '.content' > schematic.svg
    echo "✅ Schematic saved to schematic.svg"
else
    echo "❌ Failed to retrieve schematic"
    echo "$SCHEMATIC_RESPONSE" | jq .
fi

# 3. Get Layout Snapshot
echo -e "\n--- Testing: get_layout_snapshot ---"
LAYOUT_RESPONSE=$(curl -s -X POST "$URL" \
     -H "Content-Type: application/json" \
     -d '{
       "jsonrpc": "2.0",
       "id": 3,
       "method": "tools/call",
       "params": {
         "name": "get_layout_snapshot",
         "arguments": {}
       }
     }')

# Extract and save SVG if successful
if echo "$LAYOUT_RESPONSE" | jq -e '.result.content[0].text' > /dev/null; then
    echo "$LAYOUT_RESPONSE" | jq -r '.result.content[0].text' | jq -r '.content' > layout.svg
    echo "✅ Layout saved to layout.svg"
else
    echo "❌ Failed to retrieve layout"
    echo "$LAYOUT_RESPONSE" | jq .
fi