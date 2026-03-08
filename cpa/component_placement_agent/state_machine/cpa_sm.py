import logging
import asyncio
import json
import uuid
import os
from pathlib import Path
from typing import Optional, Dict, Any

from vhl_protocol.client.client import VHLWebSocketClient
from vhl_protocol.sync.client import SyncClient
from component_placement_agent.state_machine.states import CPAState
from component_placement_agent.agent.cpa_worker import run_cpa_agent
from component_placement_agent.state_machine.mcp_manager import MCPManager
from component_placement_agent.cpa_worker_2.agent import CPA_validation_agent

logger = logging.getLogger(__name__)

class CPASm:
    def __init__(self,
                 workspace_manager,
                 circuit_name: str,
                 max_auto_fixes: int = 3,
                 web_socket_client: Optional[VHLWebSocketClient] = None,
                 sync_client: Optional[SyncClient] = None,
                 project_id: Optional[str] = None,
                 parent_notify: Optional[callable] = None):
        logger.info(f"[CPASm.__init__] Initializing CPA State Machine for circuit: {circuit_name}")
        
        self.state = CPAState.INIT
        self.workspace_manager = workspace_manager
        self.circuit_name = circuit_name
        self.max_auto_fixes = max_auto_fixes
        self.web_socket_client = web_socket_client
        self.sync_client = sync_client
        self.project_id = project_id
        self.parent_notify = parent_notify
        
        # Snapshot MCP Manager (Managed by VHL Runtime)
        self.snapshot_mcp = MCPManager(endpoint="http://localhost:8083/mcp")
        
        self.current_message: Dict[str, Any] = {
            "state_id": CPAState.INIT,
            "last_decision": None,
            "task_id": None,
            "auto_fix_count": 0
        }

        # Transition Table
        self.transition_table = {
            CPAState.INIT: CPAState.TRIGGER_SYNTHESISER,
            CPAState.TRIGGER_SYNTHESISER: CPAState.TRIGGER_VALIDATOR,
            CPAState.TRIGGER_VALIDATOR: CPAState.FINALIZE,
            CPAState.FINALIZE: CPAState.EXIT_SUCCESS
        }

    async def step(self):
        """Executes one step of the CPA state machine."""
        logger.info(f"[CPASm.step] Current state: {self.state}")
        
        handlers = {
            CPAState.INIT: self._handle_init,
            CPAState.TRIGGER_SYNTHESISER: self._handle_trigger_synthesiser,
            CPAState.TRIGGER_VALIDATOR: self._handle_trigger_validator,
            CPAState.FINALIZE: self._handle_finalize,
            CPAState.EXIT_SUCCESS: self._handle_exit_success,
            CPAState.EXIT_ERROR: self._handle_exit_error,
        }

        handler = handlers.get(self.state)
        if not handler:
            logger.error(f"[CPASm.step] No handler for state: {self.state}")
            return

        # Prepare message for handler
        message = self.current_message.copy()
        
        # Execute handler
        result_message = await handler(message)
        
        # Determine next state
        next_state = result_message.get("proposed_next_state", self.transition_table.get(self.state, self.state))
        
        # If proposed next state is consumed from result_message, remove it to avoid confusion in next handler
        if "proposed_next_state" in result_message:
            del result_message["proposed_next_state"]
        
        # Update state
        self.state = next_state
        self.current_message = result_message
        self.current_message["state_id"] = self.state
        
        logger.info(f"[CPASm.step] Transitioned to: {self.state}")

    async def _handle_init(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("[CPASm._handle_init] Preparing iteration workspace...")
        
        iteration_id_suffix = str(uuid.uuid4()).split("-")[0][:8]
        
        is_stable_present = self.workspace_manager.get_circuit_path_from_stable().is_file()
        
        # Setup __snapshots__ directory
        workspace_info = self.workspace_manager.get_workspace_info()
        project_dir = Path(workspace_info.get("project_root_path"))
        if hasattr(project_dir, 'is_dir'):
            project_dir = Path(str(project_dir))
            
        snapshots_dir = project_dir / "__snapshots__"
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        
        # Collect snapshots from runtime via MCP
        logger.info(f"[CPASm._handle_init] Collecting snapshots via MCP from {self.snapshot_mcp.tool_endpoint}...")
        try:
            # Ensure server is running (short timeout as it should be ready if we are here)
            # await asyncio.to_thread(self.snapshot_mcp.ensure_server_running)
            
            schematic_res = await asyncio.to_thread(
                self.snapshot_mcp.call_tool,
                "get_schematic_snapshot",
                {}
            )
            layout_res = await asyncio.to_thread(
                self.snapshot_mcp.call_tool,
                "get_layout_snapshot",
                {}
            )
            logger.info(f"[CPASm._handle_init] Collected snapshots from MCP. Processing and saving to {snapshots_dir}..."
                        f" Schematic tool call response: {schematic_res}, Layout tool call response: {layout_res}")
            # Assuming the tool returns a dictionary with 'svg' or 'content' field
            # If it's a direct string, adjust accordingly. 
            # Given standard MCP tool call returns, we check common fields.
            
            def save_snapshot(res, filename):
                if not res:
                    logger.warning(f"[CPASm._handle_init] Received empty response for {filename}")
                    return
                
                content = None
                if isinstance(res, dict):
                    # Handle the specific MCP Response structure: {'content': [{'type': 'text', 'text': '{"content": "..."}'}]}
                    mcp_content_list = res.get("content", [])
                    if isinstance(mcp_content_list, list):
                        for item in mcp_content_list:
                            if isinstance(item, dict) and item.get("type") == "text":
                                text_data = item.get("text")
                                try:
                                    parsed_json = json.loads(text_data)
                                    content = parsed_json.get("content")
                                    if content:
                                        break
                                except (json.JSONDecodeError, TypeError):
                                    continue

                    # Fallback to legacy structure if new structure parsing failed
                    if not content:
                        content = res.get("svg") or res.get("content") or res.get("data")
                        # Ensure we don't accidentally use the list as the 'content' string
                        if isinstance(content, list):
                            content = None

                    # Final fallback: if there's only one key and it contains SVG, use it
                    if not content and len(res) == 1:
                        val = next(iter(res.values()))
                        if isinstance(val, str) and "<svg" in val:
                            content = val
                
                if isinstance(res, str):
                    content = res
                
                if content:
                    with open(snapshots_dir / filename, "w") as f:
                        f.write(content)
                    logger.info(f"[CPASm._handle_init] Saved snapshot to {filename}")
                else:
                    logger.error(f"[CPASm._handle_init] Could not extract SVG content from MCP response for {filename}. Response: {res}")

            save_snapshot(schematic_res, "schematic.svg")
            save_snapshot(layout_res, "layout.svg")
            
        except Exception as e:
            logger.error(f"[CPASm._handle_init] Failed to collect snapshots: {e}")

        logger.info(f"[CPASm._handle_init] Ensured __snapshots__ directory exists at {snapshots_dir}")
        
        if is_stable_present:
            stable_circuit = self.workspace_manager.get_circuit_path_from_stable()
            iteration_path = self.workspace_manager.prepare_iteration_with_files(
                source_file=str(stable_circuit),
                iteration_id_suffix=iteration_id_suffix
            )
            iteration_path = Path(str(iteration_path))
            logger.info(f"[CPASm._handle_init] Carried over stable circuit to {iteration_path}")
        else:
            iteration_path = self.workspace_manager.create_new_iteration(iteration_id_suffix)
            iteration_path = Path(str(iteration_path))
            logger.info(f"[CPASm._handle_init] Created fresh iteration: {iteration_path}")

        # Create softlink to __snapshots__
        iter_snapshots_link = iteration_path / "__snapshots__"
        if not iter_snapshots_link.exists():
            os.symlink(str(snapshots_dir), str(iter_snapshots_link))
            logger.info(f"[CPASm._handle_init] Created symlink to __snapshots__ at {iter_snapshots_link}")

        result_msg = message.copy()
        result_msg.update({
            "iteration_dir": str(iteration_path),
            "iteration_id": self.workspace_manager.get_current_iteration_id()
        })
        return result_msg

    async def _handle_trigger_synthesiser(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("[CPASm._handle_trigger_synthesiser] Triggering CPA Synthesiser...")
        iteration_dir = message.get("iteration_dir")
        
        try:
            prev_dir = self.workspace_manager.previous_iteration_path
            scud_path = self.workspace_manager.get_scud_path()
            
            # Run CPA Agent in a separate thread to avoid blocking loop
            await asyncio.to_thread(
                run_cpa_agent,
                workspace=iteration_dir,
                circuit_name=self.circuit_name,
                scud_path=str(scud_path),
                previous_iteration_dir=str(prev_dir) if prev_dir else None
            )
            
            return message.copy()
        except Exception as e:
            logger.exception(f"[CPASm._handle_trigger_synthesiser] Error running CPA Agent: {e}")
            result_msg = message.copy()
            result_msg["proposed_next_state"] = CPAState.EXIT_ERROR
            result_msg["error"] = str(e)
            return result_msg

    async def _handle_trigger_validator(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("[CPASm._handle_trigger_validator] Triggering CPA Validator...")
        iteration_dir = message.get("iteration_dir")
        iteration_id = message.get("iteration_id")
        
        result_msg = message.copy()
        
        try:
            validator = CPA_validation_agent(
                web_socket_client=self.web_socket_client,
                sync_client=self.sync_client,
                project_id=self.project_id
            )
            
            val_result = await validator.validate_circuit(
                circuit_name=self.circuit_name,
                workspace=iteration_dir,
                iteration_id=iteration_id
            )
            
            decision = val_result.get("decision", "REJECT")
            task_id = val_result.get("task_id")
            
            result_msg["last_decision"] = decision
            result_msg["task_id"] = task_id
            
            if decision == "ACCEPT":
                logger.info(f"[CPASm._handle_trigger_validator] Verification Accepted task_id: {task_id}.")
                if self.web_socket_client and task_id:
                    await self.web_socket_client.emit_evaluation_update(task_id, "ACCEPT")
                result_msg["proposed_next_state"] = CPAState.FINALIZE
            else:
                auto_fix_count = message.get("auto_fix_count", 0)
                if auto_fix_count < self.max_auto_fixes:
                    logger.warning(f"[CPASm._handle_trigger_validator] Verification Failed. Retrying (Attempt {auto_fix_count + 1}).")
                    result_msg["auto_fix_count"] = auto_fix_count + 1
                    result_msg["proposed_next_state"] = CPAState.INIT
                else:
                    logger.error(f"[CPASm._handle_trigger_validator] Verification Failed. Max auto-fixes reached.")
                    if self.web_socket_client and task_id:
                        await self.web_socket_client.emit_evaluation_update(task_id, "REJECT")
                    result_msg["proposed_next_state"] = CPAState.EXIT_ERROR

            return result_msg
                
        except Exception as e:
            logger.exception(f"[CPASm._handle_trigger_validator] Failed to validate circuit: {e}")
            result_msg["proposed_next_state"] = CPAState.EXIT_ERROR
            return result_msg

    async def _handle_finalize(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("[CPASm._handle_finalize] Synchronizing iteration contents to Stable directory...")
        
        try:
            iteration_id = message.get("iteration_id")
            self.workspace_manager.populate_stable(iteration_id)
            logger.info("[CPASm._handle_finalize] Stable directory updated.")
            return message.copy()
        except Exception as e:
            logger.exception(f"[CPASm._handle_finalize] Error in finalize: {e}")
            res = message.copy()
            res["proposed_next_state"] = CPAState.EXIT_ERROR
            return res

    async def _handle_exit_success(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("[CPASm._handle_exit_success] CPA Process completed successfully.")
        res = message.copy()
        res["proposed_next_state"] = CPAState.COMPLETED
        return res

    async def _handle_exit_error(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.error(f"[CPASm._handle_exit_error] CPA Process failed: {message.get('error')}")
        res = message.copy()
        res["proposed_next_state"] = CPAState.COMPLETED
        return res

    def is_terminal(self) -> bool:
        return self.state == CPAState.COMPLETED

    async def run(self):
        """Runs the state machine until completion."""
        while not self.is_terminal():
            await self.step()
        
        if self.parent_notify:
            payload = {
                "reason": "EXIT",
                "decision": self.current_message.get("last_decision", "REJECT"),
                "iteration_dir": self.current_message.get("iteration_dir"),
                "error": self.current_message.get("error")
            }
            await self.parent_notify(payload)
            
        logger.info("[CPASm.run] CPA State Machine finished.")
