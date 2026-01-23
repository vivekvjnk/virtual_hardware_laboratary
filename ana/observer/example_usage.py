"""
Example usage of the Observer Agent.

This script demonstrates how to use the Observer agent in both modes:
1. VALIDATION_ERROR mode - for analyzing validation errors
2. NO_ERROR mode - for contract compliance checking
"""

import os
import sys
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ana.observer import ObserverAgent, ObserverMode


def example_validation_error_mode():
    """
    Example: Using Observer agent to analyze validation errors.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Validation Error Analysis")
    print("=" * 80)
    
    # Initialize the observer agent
    observer = ObserverAgent(mcp_url="http://localhost:8000/mcp/observe")
    
    # Define artifact paths
    # These should point to actual files in your workspace
    scud_path = "/path/to/design.scud"
    validation_logs_path = "/path/to/validation.log"
    circuit_code_path = "/path/to/circuit.tsx"
    workspace = "/path/to/workspace"
    
    try:
        # Run observation in VALIDATION_ERROR mode
        result = observer.observe(
            mode=ObserverMode.VALIDATION_ERROR,
            scud_path=scud_path,
            validation_logs_path=validation_logs_path,
            circuit_code_path=circuit_code_path,
            workspace=workspace,
        )
        
        # Print the observation
        print("\n--- Observation Result ---")
        print(json.dumps(result, indent=2))
        
        # Access specific fields
        observation = result["observation"]
        print(f"\nVerdict: {observation.get('verdict')}")
        print(f"Issue Kind: {observation.get('issue_kind')}")
        print(f"Confidence: {observation.get('confidence')}")
        print(f"Notes: {observation.get('notes')}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        observer.close()


def example_no_error_mode():
    """
    Example: Using Observer agent for contract compliance checking.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Contract Compliance Check")
    print("=" * 80)
    
    # Initialize the observer agent
    observer = ObserverAgent(mcp_url="http://localhost:8000/mcp/observe")
    
    # Define artifact paths
    scud_path = "/path/to/design.scud"
    validation_logs_path = "/path/to/validation.log"
    circuit_code_path = "/path/to/circuit.tsx"
    schematic_images_path = "/path/to/schematics"  # Optional
    workspace = "/path/to/workspace"
    
    try:
        # Run observation in NO_ERROR mode
        result = observer.observe(
            mode=ObserverMode.NO_ERROR,
            scud_path=scud_path,
            validation_logs_path=validation_logs_path,
            circuit_code_path=circuit_code_path,
            schematic_images_path=schematic_images_path,
            workspace=workspace,
        )
        
        # Print the observation
        print("\n--- Observation Result ---")
        print(json.dumps(result, indent=2))
        
        # Access specific fields
        observation = result["observation"]
        print(f"\nContract Status: {observation.get('contract_status')}")
        print(f"Confidence: {observation.get('confidence')}")
        print(f"Notes: {observation.get('notes')}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        observer.close()


def example_integration_with_state_machine():
    """
    Example: How the Observer agent integrates with the ANA-D state machine.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Integration with State Machine")
    print("=" * 80)
    
    # Simulated state machine context
    vap_decision = "REJECT"  # Could be "ACCEPT" or "REJECT"
    scud_path = "/path/to/design.scud"
    validation_logs_path = "/path/to/validation.log"
    circuit_code_path = "/path/to/circuit.tsx"
    workspace = "/path/to/workspace"
    
    # Initialize observer
    observer = ObserverAgent(mcp_url="http://localhost:8000/mcp/observe")
    
    try:
        # Determine mode based on VAP decision
        if vap_decision == "REJECT":
            mode = ObserverMode.VALIDATION_ERROR
            print("\nVAP Decision: REJECT - Running error analysis...")
        else:
            mode = ObserverMode.NO_ERROR
            print("\nVAP Decision: ACCEPT - Running compliance check...")
        
        # Run observation
        result = observer.observe(
            mode=mode,
            scud_path=scud_path,
            validation_logs_path=validation_logs_path,
            circuit_code_path=circuit_code_path,
            workspace=workspace,
        )
        
        print("\n--- Observation Committed ---")
        print(json.dumps(result["observation"], indent=2))
        
        # State machine would now poll MCP server for this observation
        # and transition to AUTHORIZE state
        print("\n[State Machine] Observation received, transitioning to AUTHORIZE state...")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        observer.close()


def example_standalone_tool():
    """
    Example: Using the CommitObservationTool directly without the agent.
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Standalone Tool Usage")
    print("=" * 80)
    
    from ana.observer.observer_tool import CommitObservationTool
    
    # Create the tool
    tool = CommitObservationTool(mcp_url="http://localhost:8000/mcp/observe")
    
    try:
        # Commit an observation directly
        result = tool(
            verdict="ISSUE_DETECTED",
            issue_kind="LOCAL_MECHANICAL",
            confidence=0.92,
            evidence_refs=[
                {
                    "type": "log_line",
                    "id": "line_15",
                    "excerpt": "ERROR: Pin U1.FB not connected"
                },
                {
                    "type": "code_snippet",
                    "id": "circuit.tsx:42",
                    "excerpt": "<chip name=\"U1\" />"
                }
            ],
            notes="Feedback pin U1.FB is not connected to the feedback network. "
                  "This is a local mechanical error that can be fixed by adding "
                  "the missing trace connection."
        )
        
        print("\n--- Tool Result ---")
        print(result)
        
        # Retrieve the last observation
        last_obs = tool.get_last_observation()
        print("\n--- Last Observation ---")
        print(json.dumps(last_obs, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        tool.close()


def main():
    """
    Run all examples.
    """
    print("\n" + "=" * 80)
    print("OBSERVER AGENT - USAGE EXAMPLES")
    print("=" * 80)
    print("\nNOTE: Update the file paths in this script to point to actual artifacts.")
    print("Also ensure the MCP server is running at http://localhost:8000")
    
    print("\nAvailable examples:")
    print("1. Validation Error Analysis")
    print("2. Contract Compliance Check")
    print("3. Integration with State Machine")
    print("4. Standalone Tool Usage")
    
    choice = input("\nSelect example to run (1-4, or 'all'): ").strip()
    
    if choice == "1":
        example_validation_error_mode()
    elif choice == "2":
        example_no_error_mode()
    elif choice == "3":
        example_integration_with_state_machine()
    elif choice == "4":
        example_standalone_tool()
    elif choice.lower() == "all":
        example_validation_error_mode()
        example_no_error_mode()
        example_integration_with_state_machine()
        example_standalone_tool()
    else:
        print("Invalid choice. Exiting.")


if __name__ == "__main__":
    main()
