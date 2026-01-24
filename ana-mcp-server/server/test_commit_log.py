import httpx
import subprocess
import time
import socket
import sys
import os

# This test is designed to be run from the project root:
# uv run python mcp_server/test_commit_log.py

def wait_for_server(port=8000, timeout=15):
    """Wait for server to be ready."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect(("127.0.0.1", port))
            return True
        except (ConnectionRefusedError, socket.timeout):
            time.sleep(0.5)
    return False

def test_commit_and_query():
    # Start the MCP server
    print("Starting MCP server...")
    cwd = os.getcwd()
    server_process = subprocess.Popen(
        ["uv", "run", "uvicorn", "server.main:app", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd
    )
    
    try:
        # Wait for server to start
        if not wait_for_server():
            print("ERROR: Server failed to start")
            # Print stderr for debugging
            stderr_output = server_process.stderr.read().decode('utf-8')
            print(f"Server stderr:\n{stderr_output}")
            return False
        
        print("Server started successfully")
        
        base_url = "http://localhost:8000"
        
        with httpx.Client() as client:
            # 1. Commit an observation
            commit_payload = {
                "tool_name": "commit_observation",
                "payload": {
                    "verdict": "ISSUE_DETECTED",
                    "issue_kind": "LOCAL_MECHANICAL",
                    "confidence": 0.9,
                    "evidence_refs": [{"id": "img_123"}],
                    "notes": "Found a loose screw in the image."
                }
            }
            response = client.post(f"{base_url}/mcp/observe", json=commit_payload)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            assert response.json()["status"] == "ACK"
            print("✓ Test 1: Commit observation - PASSED")

            # 2. Query commit log
            response = client.get(f"{base_url}/mcp/commits")
            assert response.status_code == 200
            commits = response.json()["commits"]
            assert len(commits) == 1
            assert commits[0]["commit_id"] == 0
            assert commits[0]["tool_name"] == "commit_observation"
            assert commits[0]["endpoint"] == "/mcp/observe"
            print("✓ Test 2: Query all commits - PASSED")

            # 3. Commit another one
            commit_payload_2 = {
                "tool_name": "commit_fix_proposal",
                "payload": {
                    "summary": "Tighten the screw.",
                    "confidence": 1.0
                }
            }
            response = client.post(f"{base_url}/mcp/prepare_fix", json=commit_payload_2)
            assert response.status_code == 200
            print("✓ Test 3: Commit fix proposal - PASSED")

            # 4. Query all commits
            response = client.get(f"{base_url}/mcp/commits")
            commits = response.json()["commits"]
            assert len(commits) == 2
            assert commits[1]["commit_id"] == 1
            print("✓ Test 4: Query multiple commits - PASSED")

            # 5. Query with 'since' filter
            response = client.get(f"{base_url}/mcp/commits?since=0")
            commits = response.json()["commits"]
            assert len(commits) == 1
            assert commits[0]["commit_id"] == 1
            print("✓ Test 5: Query with 'since' filter - PASSED")

            # 6. Query with 'endpoint' filter
            response = client.get(f"{base_url}/mcp/commits?endpoint=/mcp/observe")
            commits = response.json()["commits"]
            assert len(commits) == 1
            assert commits[0]["endpoint"] == "/mcp/observe"
            print("✓ Test 6: Query with 'endpoint' filter - PASSED")

            # 7. Query with both filters
            response = client.get(f"{base_url}/mcp/commits?since=0&endpoint=/mcp/observe")
            commits = response.json()["commits"]
            assert len(commits) == 0
            print("✓ Test 7: Query with combined filters - PASSED")

            # 8. Verify invalid tool call does not add to log
            response = client.get(f"{base_url}/mcp/commits")
            initial_count = len(response.json()["commits"])
            
            invalid_payload = {
                "tool_name": "non_existent_tool",
                "payload": {}
            }
            response = client.post(f"{base_url}/mcp/observe", json=invalid_payload)
            assert response.status_code == 400
            
            response = client.get(f"{base_url}/mcp/commits")
            assert len(response.json()["commits"]) == initial_count
            print("✓ Test 8: Invalid tool call doesn't affect log - PASSED")

        print("\n" + "="*60)
        print("All tests passed!")
        print("="*60)
        while(True):
            print("Server is running... Press Ctrl+C to stop.")
            time.sleep(60)

        return True
        
    except AssertionError as e:
        print(f"\n✗ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        print("\nShutting down server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
        print("Server shut down")

if __name__ == "__main__":
    success = test_commit_and_query()
    sys.exit(0 if success else 1)
