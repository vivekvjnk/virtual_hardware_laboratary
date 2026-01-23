"""
Test script for the Observer Agent.

This script tests the Observer agent's ability to:
1. Analyze validation errors and classify them
2. Perform contract compliance checks
3. Commit observations to the MCP server
"""

import os
import sys
import json
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ana.observer import ObserverAgent, ObserverMode


def create_test_artifacts(test_dir: str, scenario: str):
    """
    Create test artifacts for different scenarios.
    
    Args:
        test_dir: Directory to create artifacts in
        scenario: Test scenario ('validation_error' or 'no_error')
    
    Returns:
        Dict with paths to created artifacts
    """
    artifacts = {}
    
    # Create SCUD document
    scud_path = os.path.join(test_dir, "test.scud")
    scud_content = """
# SCUD: Test Circuit

## Components
- U1: Voltage Regulator (TI TPS54360)
- C1: Input Capacitor (10uF, ceramic)
- C2: Output Capacitor (22uF, ceramic)
- R1: Feedback Resistor (10kΩ)
- R2: Feedback Resistor (2.2kΩ)

## Connections
- U1.VIN connects to VCC
- U1.GND connects to GND
- C1 connects between VCC and GND
- C2 connects between U1.VOUT and GND
- R1 connects between U1.VOUT and U1.FB
- R2 connects between U1.FB and GND

## Requirements
- Input voltage: 12V
- Output voltage: 5V
- Maximum load current: 3A
"""
    with open(scud_path, "w") as f:
        f.write(scud_content)
    artifacts["scud_path"] = scud_path
    
    # Create validation logs based on scenario
    logs_path = os.path.join(test_dir, "validation.log")
    
    if scenario == "validation_error":
        logs_content = """
[2026-01-23 16:30:00] INFO: Starting circuit validation
[2026-01-23 16:30:01] INFO: Checking component connections
[2026-01-23 16:30:02] ERROR: Pin mismatch detected at U1.FB
[2026-01-23 16:30:02] ERROR: Expected connection to feedback network, found floating pin
[2026-01-23 16:30:03] WARNING: Capacitor C1 value may be insufficient for input ripple
[2026-01-23 16:30:04] INFO: Checking power supply connections
[2026-01-23 16:30:05] ERROR: Ground connection missing for C2
[2026-01-23 16:30:06] INFO: Validation completed with 2 errors, 1 warning
[2026-01-23 16:30:06] RESULT: REJECT
"""
    else:  # no_error
        logs_content = """
[2026-01-23 16:30:00] INFO: Starting circuit validation
[2026-01-23 16:30:01] INFO: Checking component connections
[2026-01-23 16:30:02] INFO: All component pins properly connected
[2026-01-23 16:30:03] INFO: Checking power supply connections
[2026-01-23 16:30:04] INFO: Power supply connections verified
[2026-01-23 16:30:05] INFO: Checking feedback network
[2026-01-23 16:30:06] INFO: Feedback network configured correctly
[2026-01-23 16:30:07] INFO: Validation completed with 0 errors, 0 warnings
[2026-01-23 16:30:07] RESULT: ACCEPT
"""
    
    with open(logs_path, "w") as f:
        f.write(logs_content)
    artifacts["validation_logs_path"] = logs_path
    
    # Create circuit code
    circuit_path = os.path.join(test_dir, "circuit.tsx")
    circuit_content = """
import { Circuit } from "@tscircuit/core"

export default () => (
  <Circuit>
    <chip name="U1" footprint="SOT23-5" />
    <capacitor name="C1" capacitance="10uF" />
    <capacitor name="C2" capacitance="22uF" />
    <resistor name="R1" resistance="10k" />
    <resistor name="R2" resistance="2.2k" />
    
    <trace from="U1.VIN" to="VCC" />
    <trace from="U1.GND" to="GND" />
    <trace from="C1.pos" to="VCC" />
    <trace from="C1.neg" to="GND" />
    <trace from="C2.pos" to="U1.VOUT" />
    <trace from="C2.neg" to="GND" />
    <trace from="R1.pin1" to="U1.VOUT" />
    <trace from="R1.pin2" to="U1.FB" />
    <trace from="R2.pin1" to="U1.FB" />
    <trace from="R2.pin2" to="GND" />
  </Circuit>
)
"""
    with open(circuit_path, "w") as f:
        f.write(circuit_content)
    artifacts["circuit_code_path"] = circuit_path
    
    return artifacts


def test_validation_error_mode():
    """Test Observer agent in VALIDATION_ERROR mode."""
    print("\n" + "=" * 80)
    print("TEST 1: Observer Agent - VALIDATION_ERROR Mode")
    print("=" * 80)
    
    with tempfile.TemporaryDirectory() as test_dir:
        # Create test artifacts
        artifacts = create_test_artifacts(test_dir, "validation_error")
        
        # Create observer agent
        observer = ObserverAgent(mcp_url="http://localhost:8000/mcp/observe")
        
        try:
            # Run observation
            result = observer.observe(
                mode=ObserverMode.VALIDATION_ERROR,
                scud_path=artifacts["scud_path"],
                validation_logs_path=artifacts["validation_logs_path"],
                circuit_code_path=artifacts["circuit_code_path"],
                workspace=test_dir,
            )
            
            print("\n--- Observation Result ---")
            print(json.dumps(result, indent=2))
            
            # Verify observation was committed
            observation = result.get("observation")
            assert observation is not None, "No observation was committed"
            assert "verdict" in observation or "contract_status" in observation, "Missing verdict/contract_status"
            assert "confidence" in observation, "Missing confidence"
            assert "notes" in observation, "Missing notes"
            
            print("\n✓ TEST PASSED: Observer successfully classified validation errors")
            
        except Exception as e:
            print(f"\n✗ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            observer.close()
    
    return True


def test_no_error_mode():
    """Test Observer agent in NO_ERROR mode."""
    print("\n" + "=" * 80)
    print("TEST 2: Observer Agent - NO_ERROR Mode")
    print("=" * 80)
    
    with tempfile.TemporaryDirectory() as test_dir:
        # Create test artifacts
        artifacts = create_test_artifacts(test_dir, "no_error")
        
        # Create observer agent
        observer = ObserverAgent(mcp_url="http://localhost:8000/mcp/observe")
        
        try:
            # Run observation
            result = observer.observe(
                mode=ObserverMode.NO_ERROR,
                scud_path=artifacts["scud_path"],
                validation_logs_path=artifacts["validation_logs_path"],
                circuit_code_path=artifacts["circuit_code_path"],
                workspace=test_dir,
            )
            
            print("\n--- Observation Result ---")
            print(json.dumps(result, indent=2))
            
            # Verify observation was committed
            observation = result.get("observation")
            assert observation is not None, "No observation was committed"
            assert "verdict" in observation or "contract_status" in observation, "Missing verdict/contract_status"
            assert "confidence" in observation, "Missing confidence"
            assert "notes" in observation, "Missing notes"
            
            print("\n✓ TEST PASSED: Observer successfully performed contract compliance check")
            
        except Exception as e:
            print(f"\n✗ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            observer.close()
    
    return True


def test_tool_only():
    """Test the CommitObservationTool in isolation."""
    print("\n" + "=" * 80)
    print("TEST 3: CommitObservationTool - Standalone")
    print("=" * 80)
    
    from ana.observer.observer_tool import CommitObservationTool
    
    tool = CommitObservationTool(mcp_url="http://localhost:8000/mcp/observe")
    
    try:
        # Test committing an observation
        result = tool(
            verdict="ISSUE_DETECTED",
            issue_kind="LOCAL_MECHANICAL",
            confidence=0.85,
            evidence_refs=[
                {"type": "log_line", "id": "line_5", "excerpt": "ERROR: Ground connection missing for C2"}
            ],
            notes="Ground connection missing for output capacitor C2. This is a local mechanical error."
        )
        
        print("\n--- Tool Result ---")
        print(result)
        
        result_data = json.loads(result)
        assert result_data.get("status") == "success", "Tool call failed"
        
        # Verify last observation
        last_obs = tool.get_last_observation()
        assert last_obs is not None, "No observation stored"
        assert last_obs["verdict"] == "ISSUE_DETECTED", "Incorrect verdict"
        
        print("\n✓ TEST PASSED: CommitObservationTool works correctly")
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        tool.close()
    
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("OBSERVER AGENT TEST SUITE")
    print("=" * 80)
    print("\nNOTE: These tests require the MCP server to be running at http://localhost:8000")
    print("Please ensure the server is started before running these tests.")
    
    input("\nPress Enter to continue with tests...")
    
    results = []
    
    # Run tests
    results.append(("Tool Standalone Test", test_tool_only()))
    results.append(("Validation Error Mode", test_validation_error_mode()))
    results.append(("No Error Mode", test_no_error_mode()))
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
