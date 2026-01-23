"""
Test script for ANA-D State Machine with MCP integration.

This script simulates the Observer agent by making a commit to the MCP server,
and verifies that the state machine correctly polls and processes the observation.
"""

import time
import httpx
import subprocess
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ana_designer.ana_sm import ANADStateMachine, State


def simulate_observer_commit(delay_seconds: int = 3):
    """
    Simulates an observer agent by making a commit to the MCP server after a delay.
    
    Args:
        delay_seconds: How long to wait before making the commit
    """
    print(f"[SIMULATOR] Waiting {delay_seconds} seconds before making observation commit...")
    time.sleep(delay_seconds)
    
    # Make a commit to the MCP server
    url = "http://localhost:8000/mcp/observe"
    payload = {
        "tool_name": "commit_observation",
        "payload": {
            "verdict": "ISSUE_DETECTED",
            "issue_kind": "LOCAL_MECHANICAL",
            "confidence": 0.85,
            "evidence_refs": [{"type": "image", "id": "test_img_001"}],
            "notes": "Test observation from simulator"
        }
    }
    
    try:
        with httpx.Client() as client:
            response = client.post(url, json=payload)
            if response.status_code == 200:
                print(f"[SIMULATOR] Successfully committed observation: {response.json()}")
            else:
                print(f"[SIMULATOR] Failed to commit: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[SIMULATOR] Error making commit: {e}")


def test_state_machine_with_mcp():
    """
    Test the state machine with MCP integration.
    """
    print("=" * 80)
    print("Testing ANA-D State Machine with MCP Integration")
    print("=" * 80)
    
    # Create state machine
    sm = ANADStateMachine()
    
    # Set initial conditions
    sm.vap_decision = "REJECT"  # Simulate VAP rejection
    
    try:
        # Start in INIT state
        print(f"\n[TEST] Initial state: {sm.state}")
        
        # Step to OBSERVE
        sm.step()
        print(f"[TEST] After INIT step: {sm.state}")
        
        # Start a background thread to simulate observer agent
        import threading
        observer_thread = threading.Thread(target=simulate_observer_commit, args=(5,))
        observer_thread.daemon = True
        observer_thread.start()
        
        # This will block until observation is received
        print(f"[TEST] Stepping through OBSERVE (will poll for commit)...")
        sm.step()
        
        print(f"[TEST] After OBSERVE step: {sm.state}")
        print(f"[TEST] Error class: {sm.error_class}")
        print(f"[TEST] Intent status: {sm.intent_status}")
        
        # Verify we transitioned to AUTHORIZE
        assert sm.state == State.AUTHORIZE, f"Expected AUTHORIZE, got {sm.state}"
        assert sm.error_class == "mechanical", f"Expected 'mechanical', got {sm.error_class}"
        assert sm.intent_status == "violated", f"Expected 'violated', got {sm.intent_status}"
        
        print("\n" + "=" * 80)
        print("✓ Test PASSED: State machine successfully integrated with MCP!")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n[TEST] Interrupted by user")
    except Exception as e:
        print(f"\n[TEST] ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        sm.cleanup()
        print("[TEST] Cleanup complete")


if __name__ == "__main__":
    test_state_machine_with_mcp()
