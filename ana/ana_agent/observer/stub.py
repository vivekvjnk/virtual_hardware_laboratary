import os
import logging
import json
from vhl_protocol.utils.mcp_utils import call_mcp_function

logger = logging.getLogger(__name__)

def run_observer_stub(mode: str, iteration_dir: str, mcp_url: str = "http://localhost:8081/mcp/observe"):
    """
    Mock replacement for ObserverAgent.observe.
    Commits an observation via MCP TOOL.
    """
    logger.info(f"[run_observer_stub] Mocking observation for {iteration_dir} in mode {mode}")
    
    # Heuristic/Stub logic: decide what to commit
    issue_kind = "NONE"
    observations = "Stub: No issues observed."
    
    if mode == "validation_error":
        # Check if there are actually errors in eval_results if we want to be fancy
        # For now, just commit LOCAL to allow the auto-fix loop to trigger once if needed
        # Or commit NONE if no real errors found
        eval_results_dir = os.path.join(iteration_dir, "eval_results")
        if os.path.exists(eval_results_dir) and any(os.listdir(eval_results_dir)):
             issue_kind = "LOCAL"
             observations = "Stub: Detected some local validation issues in eval_results."
        else:
             issue_kind = "NONE"
             observations = "Stub: validation_error mode triggered but no artifacts found. Treating as NONE."
    
    # Commit via MCP
    payload = {
        "issue_kind": issue_kind,
        "confidence": 0.95,
        "observations": observations
    }
    
    # The MCP server at :8081 expects the payload either flattened or in a 'payload' key
    # Based on server/main.py: arguments.get("payload", arguments)
    logger.info(f"[run_observer_stub] Committing observation: {payload}")
    try:
        # Note: the url in observer_agent is http://localhost:8081/mcp/observe
        # call_mcp_function takes a base URL for SSE. 
        # But wait, the ana-mcp-server/server/main.py uses a hybrid FastAPI.
        # It's an SSE server? 
        # Actually, ObserverAgent uses:
        # self.mcp_config = {"mcpServers": {"VHL_ANA_Observe": {"url": mcp_url}}}
        # OpenHands SDK MCPClient handles both SSE and StdIO.
        
        # If I use call_mcp_function, it uses SSE if the URL looks like it.
        # ana-mcp-server/server/main.py has @app.post("/mcp/{scope_endpoint:path}")
        # So the SSE endpoint is likely http://localhost:8081/mcp/observe
        
        # Correct URL for SSE in MCPInvoker/call_mcp_function
        result = call_mcp_function(mcp_url, "commit_observation", arguments=payload)
        logger.info(f"[run_observer_stub] Successfully committed observation. Result: {result}")
    except Exception as e:
        logger.error(f"[run_observer_stub] Failed to commit observation: {e}")
        # We don't raise here to avoid crashing the state machine if the MCP server isn't responsive in stub mode
        # But wait, ana_sm polls for it, so if we don't commit, it will wait forever.
        raise
