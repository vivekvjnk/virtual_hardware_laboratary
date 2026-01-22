
import json
from fastapi.testclient import TestClient
from mcp_server.main import app

client = TestClient(app)

def test_commit_and_query():
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
    response = client.post("/mcp/observe", json=commit_payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ACK"

    # 2. Query commit log
    response = client.get("/mcp/commits")
    assert response.status_code == 200
    commits = response.json()["commits"]
    assert len(commits) == 1
    assert commits[0]["commit_id"] == 0
    assert commits[0]["tool_name"] == "commit_observation"
    assert commits[0]["endpoint"] == "/mcp/observe"

    # 3. Commit another one
    commit_payload_2 = {
        "tool_name": "commit_fix_proposal",
        "payload": {
            "summary": "Tighten the screw.",
            "confidence": 1.0
        }
    }
    response = client.post("/mcp/prepare_fix", json=commit_payload_2)
    assert response.status_code == 200

    # 4. Query all commits
    response = client.get("/mcp/commits")
    commits = response.json()["commits"]
    assert len(commits) == 2
    assert commits[1]["commit_id"] == 1

    # 5. Query with 'since' filter
    response = client.get("/mcp/commits?since=0")
    commits = response.json()["commits"]
    assert len(commits) == 1
    assert commits[0]["commit_id"] == 1

    # 6. Query with 'endpoint' filter
    response = client.get("/mcp/commits?endpoint=/mcp/observe")
    commits = response.json()["commits"]
    assert len(commits) == 1
    assert commits[0]["endpoint"] == "/mcp/observe"

    # 7. Query with both filters
    response = client.get("/mcp/commits?since=0&endpoint=/mcp/observe")
    commits = response.json()["commits"]
    assert len(commits) == 0

    # 8. Verify invalid tool call does not add to log
    response = client.get("/mcp/commits")
    initial_count = len(response.json()["commits"])
    
    invalid_payload = {
        "tool_name": "non_existent_tool",
        "payload": {}
    }
    response = client.post("/mcp/observe", json=invalid_payload)
    assert response.status_code == 400
    
    response = client.get("/mcp/commits")
    assert len(response.json()["commits"]) == initial_count

    print("All tests passed!")

if __name__ == "__main__":
    test_commit_and_query()
