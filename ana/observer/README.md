# Observer Agent

The Observer Agent is a strictly observational component in the VHL ANA-D control architecture. It analyzes validation results and design intent compliance, then commits structured observations to the MCP server.

## Overview

The Observer agent **does NOT**:
- Decide next actions
- Choose retries
- Escalate to humans
- Fix errors
- Suggest solutions
- Optimize designs
- Infer missing intent

It **ONLY**:
- Observes artifacts (SCUD, validation logs, circuit code, schematics)
- Classifies errors and compliance status
- Reports findings via the `commit_observation` tool

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Observer Agent                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  System Prompt (Mode-Dependent)                      │  │
│  │  - VALIDATION_ERROR: Error classification            │  │
│  │  - NO_ERROR: Contract compliance check               │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Tools                                                │  │
│  │  - CommitObservationTool (MCP endpoint)              │  │
│  │  - FileEditorTool (for reading artifacts)            │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Agent SDK (openhands)                               │  │
│  │  - LLM integration                                    │  │
│  │  - Conversation management                            │  │
│  │  - Tool orchestration                                 │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP POST
                            ▼
            ┌───────────────────────────────┐
            │   MCP Server                  │
            │   /mcp/observe endpoint       │
            │   - commit_observation tool   │
            └───────────────────────────────┘
```

## Components

### 1. `observer_agent.py`
Main agent implementation using the openhands agent-sdk framework.

**Key Features:**
- Mode-based operation (VALIDATION_ERROR or NO_ERROR)
- Artifact-driven analysis
- Automatic observation commitment
- Error handling and validation

**Usage:**
```python
from ana.observer import ObserverAgent, ObserverMode

observer = ObserverAgent(mcp_url="http://localhost:8000/mcp/observe")

result = observer.observe(
    mode=ObserverMode.VALIDATION_ERROR,
    scud_path="/path/to/design.scud",
    validation_logs_path="/path/to/validation.log",
    circuit_code_path="/path/to/circuit.tsx",
    workspace="/path/to/workspace"
)

print(result["observation"])
observer.close()
```

### 2. `observer_system_prompt.py`
System prompt builder that generates mode-specific instructions.

**Modes:**
- `VALIDATION_ERROR`: Analyzes validation logs to classify errors
  - Error locality: local / hub-centric / ripple
  - Error nature: mechanical / structural / ambiguity-induced
  - Confidence level

- `NO_ERROR`: Performs contract compliance check against SCUD
  - Respects all explicit SCUD guarantees
  - Contradicts any explicit SCUD guarantee
  - Cannot be judged due to SCUD ambiguity

### 3. `observer_tool.py`
Custom tool wrapper for the MCP `commit_observation` endpoint.

**Schema:**
```python
{
    # For VALIDATION_ERROR mode
    "verdict": "ISSUE_DETECTED" | "NO_ISSUE" | "UNCERTAIN",
    "issue_kind": "LOCAL_MECHANICAL" | "HUB_CENTRIC" | "RIPPLE" | "STRUCTURAL" | "AMBIGUITY_INDUCED",
    
    # For NO_ERROR mode
    "contract_status": "COMPLIANT" | "VIOLATED" | "AMBIGUOUS",
    
    # Common fields
    "confidence": 0.0 to 1.0,
    "evidence_refs": [
        {
            "type": "log_line" | "image" | "code_snippet",
            "id": "identifier",
            "excerpt": "optional excerpt"
        }
    ],
    "notes": "Detailed explanation"
}
```

### 4. `test_observer.py`
Comprehensive test suite covering:
- Standalone tool testing
- VALIDATION_ERROR mode
- NO_ERROR mode
- Artifact creation and handling

## Integration with ANA-D State Machine

The Observer agent is invoked by the ANA-D state machine in the `OBSERVE` state:

```python
from ana.observer import ObserverAgent, ObserverMode

# In OBSERVE state
observer = ObserverAgent()

# Determine mode based on VAP decision
mode = (ObserverMode.VALIDATION_ERROR 
        if vap_decision == "REJECT" 
        else ObserverMode.NO_ERROR)

# Run observation
result = observer.observe(
    mode=mode,
    scud_path=scud_path,
    validation_logs_path=validation_logs_path,
    circuit_code_path=circuit_code_path,
    workspace=workspace
)

# State machine polls MCP server for committed observation
# and transitions to AUTHORIZE state
```

## MCP Server Integration

The Observer agent communicates with the MCP server via HTTP:

**Endpoint:** `http://localhost:8000/mcp/observe`

**Request Format:**
```json
{
    "tool_name": "commit_observation",
    "payload": {
        "verdict": "ISSUE_DETECTED",
        "issue_kind": "LOCAL_MECHANICAL",
        "confidence": 0.85,
        "evidence_refs": [
            {
                "type": "log_line",
                "id": "line_42",
                "excerpt": "ERROR: Pin mismatch at U1.FB"
            }
        ],
        "notes": "Feedback pin connection error detected..."
    }
}
```

**Response Format:**
```json
{
    "status": "ACK",
    "message": {
        "type": "observation",
        "payload": { ... },
        "metadata": {
            "timestamp": "2026-01-23T16:59:22+05:30",
            "tool": "commit_observation"
        }
    }
}
```

## Environment Variables

- `LLM_API_KEY`: API key for the LLM provider
- `LLM_MODEL`: Model to use (default: `anthropic/claude-sonnet-4-5-20250929`)
- `LLM_BASE_URL`: Base URL for LLM API (optional)

## Running Tests

```bash
# Ensure MCP server is running
cd /path/to/project
python -m ana.observer.test_observer
```

## Dependencies

- `openhands-sdk`: Agent framework
- `httpx`: HTTP client for MCP communication
- `pydantic`: Data validation

## Design Principles

1. **Strict Observational Role**: The agent never takes action, only observes and reports
2. **Mode-Based Operation**: Clear separation between error analysis and compliance checking
3. **Mandatory Commitment**: Agent MUST call `commit_observation` exactly once
4. **Evidence-Based**: All observations must reference specific evidence
5. **Uncertainty Tolerance**: "UNCERTAIN" and "AMBIGUOUS" are valid outcomes

## Error Handling

- If the agent fails to commit an observation, a `RuntimeError` is raised
- HTTP errors are logged and returned as JSON error messages
- Invalid payloads are caught during Pydantic validation
- All errors are logged for debugging

## Future Enhancements

- Support for image analysis (schematic comparison)
- Multi-modal evidence references
- Confidence calibration based on historical accuracy
- Streaming observations for long-running analyses
