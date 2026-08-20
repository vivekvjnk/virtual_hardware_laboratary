import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from vhl_common.urp.abstract_urp import AbstractURPAgent
from vhl_common.urp.data_types import (
    AgentDescriptor,
    AgentContext,
    FailureCategory,
    LastTaskOutcome,
    MessageEnvelope,
    ProcessResult,
    ProcessResultPayload,
)
from vhl_common.utils import setup_dedicated_logger
from .pi_rpc_client import PiRpcClient
from .rpc_types import RpcEvent, PiRpcError

logger = setup_dedicated_logger("pi_urp_agent", "pi_urp_agent.log")


class PiURPAgent(AbstractURPAgent):
    """
    Base URP Agent backed by the Pi Agent Harness via PiRpcClient.

    Combines URP state machine lifecycle, mailbox-driven execution loop, precondition/postcondition
    hooks, and outcome acknowledgment controls with Pi's high-performance RPC execution engine.
    """

    def __init__(self, descriptor: AgentDescriptor):
        super().__init__(descriptor)
        self.pi_client: Optional[PiRpcClient] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _on_initialize(self, context: AgentContext) -> None:
        """URP Initialization Hook: Configures and instantiates PiRpcClient."""
        logger.info(f"[{self.descriptor.agent_id}] Initializing PiURPAgent context...")
        config = getattr(context, "configuration", {}) or {}

        workspace_dir = (
            config.get("workspace_dir")
            or getattr(context, "workspace_path", None)
            or os.getcwd()
        )
        model = config.get("model") or os.getenv("LLM_MODEL")
        provider = config.get("provider") or os.getenv("LLM_PROVIDER")
        session_dir = config.get("session_dir")
        no_session = config.get("no_session", False)
        system_prompt = config.get("system_prompt")
        name = config.get("name") or self.descriptor.name
        extra_args = config.get("extra_args")
        env = config.get("env")

        self.pi_client = PiRpcClient(
            workspace_dir=workspace_dir,
            model=model,
            provider=provider,
            session_dir=session_dir,
            no_session=no_session,
            system_prompt=system_prompt,
            name=name,
            extra_args=extra_args,
            env=env,
        )

        # Register wildcard telemetry event forwarder
        self.pi_client.on_any_event(self._handle_pi_telemetry_event)

    def _handle_pi_telemetry_event(self, rpc_evt: RpcEvent) -> None:
        """Schedules async forwarding of Pi RPC events to the URP event bus."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._forward_telemetry_event(rpc_evt))
        except RuntimeError:
            pass

    async def _forward_telemetry_event(self, rpc_evt: RpcEvent) -> None:
        """Maps Pi RPC events to URP telemetry envelopes and emits them."""
        msg_type_map = {
            "message_update": "AGENT_PROGRESS_UPDATE",
            "tool_execution_start": "AGENT_TOOL_START",
            "tool_execution_end": "AGENT_TOOL_END",
            "compaction_start": "AGENT_COMPACTION_START",
            "compaction_end": "AGENT_COMPACTION_END",
            "error": "AGENT_ERROR_LOG",
        }

        urp_event_type = msg_type_map.get(rpc_evt.type)
        if urp_event_type:
            envelope = MessageEnvelope(
                type=urp_event_type,
                payload=rpc_evt.data,
                sender=self.descriptor.agent_id,
                receiver="SUPERVISOR",
            )
            await self.emit(envelope)

    async def _check_start_preconditions(self) -> tuple[bool, str]:
        """URP Start Precondition Hook: Starts PiRpcClient subprocess and verifies state."""
        if not self.pi_client:
            return False, "PiRpcClient instance not initialized"

        try:
            logger.info(f"[{self.descriptor.agent_id}] Starting PiRpcClient subprocess...")
            await self.pi_client.start()

            state_resp = await self.pi_client.get_state()
            if not state_resp.success:
                return False, f"Pi RPC initial state check failed: {state_resp.error}"

            return True, "PiRpcClient started and verified successfully"
        except Exception as e:
            logger.error(f"[{self.descriptor.agent_id}] Failed starting PiRpcClient: {e}")
            return False, f"Failed starting PiRpcClient subprocess: {e}"

    async def process(self, message: MessageEnvelope) -> ProcessResult:
        """
        Core URP execution primitive.
        Translates MessageEnvelope payload into a Pi prompt, monitors streaming events,
        and constructs ProcessResult outcome.
        """
        if not self.pi_client or not self.pi_client.is_running:
            logger.error(f"[{self.descriptor.agent_id}] Cannot process: PiRpcClient is not running.")
            return ProcessResult(
                outcome=LastTaskOutcome.TASK_FAILED,
                category=FailureCategory.INFRASTRUCTURE_FAILURE,
                payload=ProcessResultPayload(text="Pi RPC client subprocess is not running.")
            )

        # 1. Parse prompt text and attachments from envelope payload
        user_text = ""
        images = None

        if isinstance(message.payload, dict):
            user_text = message.payload.get("text") or message.payload.get("prompt") or str(message.payload)
            images = message.payload.get("images") or message.metadata.get("images")
        elif isinstance(message.payload, str):
            user_text = message.payload
        elif hasattr(message.payload, "text"):
            user_text = getattr(message.payload, "text", str(message.payload))
        else:
            user_text = str(message.payload)

        # 2. Setup settlement listener
        settled_event = asyncio.Event()

        def on_settle_evt(evt: RpcEvent):
            if evt.type in ("agent_settled", "agent_end"):
                settled_event.set()

        self.pi_client.on_any_event(on_settle_evt)

        logger.info(f"[{self.descriptor.agent_id}] Sending prompt to Pi RPC client: {user_text[:100]}...")

        # 3. Issue prompt to Pi harness
        try:
            prompt_resp = await self.pi_client.send_prompt(user_text, images=images)
            if not prompt_resp.success:
                logger.error(f"[{self.descriptor.agent_id}] Prompt command failed: {prompt_resp.error}")
                return ProcessResult(
                    outcome=LastTaskOutcome.TASK_FAILED,
                    category=FailureCategory.INFRASTRUCTURE_FAILURE,
                    payload=ProcessResultPayload(text=prompt_resp.error or "Pi prompt command failed")
                )

            # Wait for execution turn settlement
            try:
                await asyncio.wait_for(settled_event.wait(), timeout=120.0)
            except asyncio.TimeoutError:
                logger.warning(f"[{self.descriptor.agent_id}] Timed out waiting for agent settlement.")

            # 4. Fetch last assistant response
            text_resp = await self.pi_client.get_last_assistant_text()
            assistant_text = text_resp.data.get("text") if text_resp.success else ""

            return ProcessResult(
                outcome=LastTaskOutcome.TASK_COMPLETED,
                category=FailureCategory.NONE,
                payload=ProcessResultPayload(text=assistant_text or "")
            )

        except Exception as e:
            logger.error(f"[{self.descriptor.agent_id}] Exception during process execution: {e}", exc_info=True)
            return ProcessResult(
                outcome=LastTaskOutcome.TASK_FAILED,
                category=FailureCategory.INFRASTRUCTURE_FAILURE,
                payload=ProcessResultPayload(text=f"Execution error: {str(e)}")
            )

    async def _on_shutdown(self) -> None:
        """URP Shutdown Hook: Closes PiRpcClient subprocess."""
        if self.pi_client:
            logger.info(f"[{self.descriptor.agent_id}] Shutting down PiRpcClient...")
            await self.pi_client.close()
