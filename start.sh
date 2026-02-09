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


# Start Workspace WebSocket Client in background
echo "Starting Workspace WebSocket Client..."
node dist/workspace/index.js &
WS_CLIENT_PID=$!

# Start tscircuit in background
echo "Starting tscircuit..."



cd workspace/
# Use expect to handle the interactive prompts
expect <<DONE
  set timeout -1
  spawn tsci init
  
  # 1. Handle the update prompt
  expect {
    "Would you like to update now?" {
      send "n\r"
      exp_continue
    }
    # 2. Handle the initialization prompt
    "Do you want to initialize a new project in the current directory?" {
      send "y\r"
      exp_continue
    }
    # 3. Handle the package name (Enter for default)
    "Package name" {
      send "\r"
      exp_continue
    }
    # 4. AI assistance
    "Would you like to set up tscircuit AI skill for enhanced AI assistance?" {
      send "n\r"
    }

  }
  expect eof
DONE

echo "Starting tsci dev..."

tsci dev bq79616_eval_board.tsx &
TSCI_PID=$!

cd ../
# Wait for any process to exit
wait -n $LIBRARY_PID $VAP_PID $WS_SERVER_PID $WS_CLIENT_PID $TSCI_PID

# Exit with status of process that exited first
exit $?
