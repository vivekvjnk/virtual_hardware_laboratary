import os
import asyncio
import shutil
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field

from pydantic import SecretStr

from openhands.sdk import (
    LLM,
    Agent,
    Conversation,
    LargeFileSurgicalCondenser,
    LLMSummarizingCondenser,
    Event,
    LLMConvertibleEvent,
    PipelineCondenser,
    Tool,
    Message,
    TextContent,
    AgentContext as OpenHandsAgentContext,
    get_logger,
)
from openhands.tools.file_editor import FileEditorTool

from openhands.sdk.conversation.state import (
    ConversationExecutionStatus,
    ConversationState,
)

from vhl_common.urp.abstract_urp import AbstractURPAgent
from vhl_common.urp.data_types import AgentDescriptor, MessageEnvelope
from vhl_common.utils import setup_dedicated_logger
from vhl_common.workspace_manager.manager import WorkspaceManager
from vhl_common.project_state_manager import SQLiteManager
from vhl_protocol.sync.client import SyncClient
from vhl_protocol.client.client import VHLWebSocketClient
from vhl_common.urp.data_types import ProcessResult, ProcessResultPayload, LastTaskOutcome, FailureCategory

from ana_agent.ana_worker_1 import run_ana_w1_agent
from ana_agent.ana_worker_2.agent import ANA_validation_agent
from ana_agent.ana_evaluator import AGENT_ID as ANA_AGENT_ID, OPERATION_NAME as ANA_OPERATION_NAME, AnaEvaluator

from vhl_common.llm import get_llm_for_agent

# Dedicated logger for ANA URP agent
logger = setup_dedicated_logger("ana_urp_agent", "ana_urp_agent.log")


# ---------------------------------------------------------------------------
# Configuration & Context dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AnaConfig:
    """
    Configuration for ANA URP agent.
    conversation_persistence: Whether to persist conversation across iterations.
    """
    conversation_persistence: bool = field(default=True)


@dataclass(frozen=True)
class AnaContext:
    """
    Runtime context injected into ANA URP at initialize time.

    module_name       : The module being synthesised (maps to module_id concept).
    workspace         : Shared WorkspaceManager instance for the project.
    sqlite_manager    : SQLite DB handle for semantic_operations queries.
    web_socket_client : WebSocket client for VAP execution (W2).
    sync_client       : Sync client for circuit / evaluation syncing (W2).
    project_id        : Project identifier used by sync / W2.
    config            : Optional agent-level config overrides.
    """
    module_name: str
    workspace: WorkspaceManager
    sqlite_manager: SQLiteManager
    web_socket_client: VHLWebSocketClient
    sync_client: SyncClient
    config: AnaConfig = field(default_factory=AnaConfig)


# ---------------------------------------------------------------------------
# ANA URP Agent
# ---------------------------------------------------------------------------

class AnaURPAgent(AbstractURPAgent):
    """
    ANA URP Agent — Virtual Hardware Laboratory circuit synthesis agent.

    This agent consolidates the legacy ANADStateMachine into URP pre/post
    condition hooks, eliminating the Observer agent and the first-iteration
    flag in favour of semantic_operations DB queries.

    Operating modes
    ---------------
    Synthesis mode
        No prior successful VAP exists for this module.
        ANA-W1 is invoked to synthesise the circuit from scratch.

    Error-correction mode
        A prior successful VAP exists (detected via ANA_EVALUATOR entry in
        semantic_operations).  The stable circuit is seeded into the new
        iteration directory and ANA-W1 is invoked in error-correction mode.
        ANA analyses the evaluation logs from the previous iteration and
        produces a corrected circuit without a separate Observer agent.

    VAP cycle (post-conditions)
    ---------------------------
    After ANA-W1 finishes, post-conditions run ANA-W2 (validation agent).
    - ACCEPT  → promote to Stable/, archive iterations, record operation,
                condense conversation history.
    - REJECT  → save evaluation logs, condense conversation history, attach
                error payload to next process() call so ANA can self-correct.
    """

    def __init__(self, descriptor: Optional[AgentDescriptor] = None,
                 llm: Optional[LLM] = None):
        if not descriptor:
            descriptor = AgentDescriptor(
                agent_id="vhl.ana.v1",
                name="ANA Circuit Generator",
                version="1.0",
                capabilities=["CIRCUIT_SYNTHESIS", "CIRCUIT_ERROR_CORRECTION"],
                accepted_message_types=["CIRCUIT_GENERATE", "CIRCUIT_ERROR_CORRECT"],
            )
        super().__init__(descriptor=descriptor)

        # Injected from context in _on_initialize
        self.llm: Optional[LLM] = llm
        self.agent: Optional[Agent] = None
        self.conversation: Optional[Conversation] = None
        self.llm_messages = []

        self.workspace_manager: Optional[WorkspaceManager] = None
        self.sqlite_manager: Optional[SQLiteManager] = None
        self.module_name: Optional[str] = None
        self.web_socket_client: Optional[VHLWebSocketClient] = None
        self.sync_client: Optional[SyncClient] = None

        # Iteration state — set fresh in pre-conditions each invocation
        self._workspace_dir: Optional[Path] = None
        

        # Error payload forwarded from a REJECT post-condition into the next
        # process() call so ANA-W1 can self-correct.
        self._pending_error_message: Optional[str] = None
        
        # Runtime info like MAW paths. Populated by pre-condition 
        self._runtime_info: dict[str,any] = None
    # ------------------------------------------------------------------
    # Lifecycle: _on_initialize
    # ------------------------------------------------------------------

    def _on_initialize(self, context: AnaContext) -> None:
        """
        Responsibilities
        - Parse and validate AnaContext.
        - Initialise LLM, condenser, Agent, and Conversation objects.
        - Bind WorkspaceManager, SQLiteManager, and protocol clients.
        - MAW (Mirrored-Attempt-Workspace) setup.
        - The Conversation is opened with persistence so that condensation
          across error-correction iterations is possible.
        """
        # Accept both raw dict (from URP runtime) and AnaContext instance
        if not isinstance(context, AnaContext):
            raise ValueError(f"Invalid configuration for AnaURPAgent. context is not an instance of AnaContext")

        self.workspace_manager = context.workspace
        self.sqlite_manager = context.sqlite_manager
        self.module_name = context.module_name
        self.web_socket_client = context.web_socket_client
        self.sync_client = context.sync_client
        config = context.config

        # ------- Workspace configuration ----
        self._workspace_dir = self.workspace_manager.create_workspace(module_name=self.module_name)
        logger.info(
            f"[AnaURPAgent._on_initialize] Initialized for module='{self.module_name}', "
        )

        module_path = self.workspace_manager.module_paths[self.module_name] /  "Workspace"
        # ---- LLM setup ----
        if not self.llm:
            self.llm = get_llm_for_agent(
                agent_id=f"{self.module_name}.ana",
                module_name= self.module_name,
                workspace_path=str(self.workspace_manager.project_root),
            )

        # ---- Condenser pipeline (mirrors ANA-W1 pattern) ----
        # LargeFileSurgicalCondenser keeps file-editor events compact.
        surgical_condenser = LargeFileSurgicalCondenser(
            threshold_bytes=10240,
            target_tool="file_editor",
        )
        pipeline = PipelineCondenser(condensers=[
            surgical_condenser,
            LLMSummarizingCondenser(
                llm=self.llm.model_copy(update={"usage_id": "ana_urp_condenser"}),
                max_size=80,
            ),
        ])

        # ---- Agent ----
        submodule_root = Path(__file__).resolve().parent
        tools = [
            Tool(name=FileEditorTool.name),
        ]
        submodule_root = Path(__file__).resolve().parent
        sys_prompt_path = os.path.join(submodule_root, "ana_prompt.j2")

        sys_prompt_kwargs = self.workspace_manager.get_maw_workspace_info(self.module_name)

        self.agent = Agent(
            llm=self.llm,
            tools=tools,
            condenser=pipeline,
            system_prompt_filename=sys_prompt_path,
            system_prompt_kwargs=sys_prompt_kwargs,
        )

        # ---- Conversation (persistence enables condensation across iterations) ----
        
        self.conversation = Conversation(
            agent=self.agent,
            workspace=str(module_path),
            callbacks=[self._conversation_callback],
            persistence_dir=str(module_path / ".conversation") if config.conversation_persistence else None,
        )


    def _conversation_callback(self, event: Event):
        if isinstance(event, LLMConvertibleEvent):
            self.llm_messages.append(event.to_llm_message())

    # ------------------------------------------------------------------
    # Pre-conditions  (maps: handle_init logic)
    # ------------------------------------------------------------------

    async def _check_preconditions(self, message: MessageEnvelope) -> tuple[bool, str]:
        """
        Pre-condition hook — executed before every process() call.

        Mapped from: handle_init in ANADStateMachine.

        Logic
        -----
        1. Query semantic_operations for a prior ANA_EVALUATOR / CIRCUIT_SYNTHESIS
           SUCCESS entry for this module.
           - If found  → synthesis has happened before. This is either an
             error-correction or user-triggered improvement iteration.
             Copy Stable/ circuit into the workspace directory.
           - If not found → first-time synthesis. Circuit is yet to be synthesised 
        2. Create new iteration directory via WorkspaceManager.
        3. Stash iteration paths on self for use by process() and post-conditions.
        """
        logger.info(
            f"[AnaURPAgent._check_preconditions] module='{self.module_name}'"
        )

        try:
            # ---- 1. Check for prior successful synthesis ----
            prior_synthesis = self.sqlite_manager.conn.execute(
                """
                SELECT so.status
                FROM semantic_operations so
                JOIN artifact_snapshots sn ON so.artifact_ref_id = sn.id
                WHERE so.author = ? AND so.op_name = ? AND sn.module_name = ?
                  AND so.status = 'SUCCESS'
                ORDER BY so.id DESC LIMIT 1
                """,
                (ANA_AGENT_ID, ANA_OPERATION_NAME, self.module_name),
            ).fetchone()

            # First synthesis — Do nothing..
            if not prior_synthesis:
                logger.info(
                    "[AnaURPAgent._check_preconditions] No prior synthesis found. "
                    "Operating in first-synthesis mode."
                )
            # ---- 2. If prior synthesis exists, prepare workspace with stable circuit ----
            else:
                logger.info(
                    "[AnaURPAgent._check_preconditions] Prior synthesis detected. "
                    "Operating in error-correction / improvement mode."
                )         
                stable_circuit_path = self.workspace_manager.get_circuit_path_from_stable(
                    module_name=self.module_name
                )
                if not stable_circuit_path.is_file():
                    msg = (
                        f"[AnaURPAgent._check_preconditions] Prior synthesis recorded but "
                        f"stable circuit not found at {stable_circuit_path}. "
                        "Cannot proceed with error-correction iteration."
                    )
                    logger.error(msg)
                    return False, msg

                # prepare_workspace: snapshots current truth and copies stable circuit into Workspace/
                self.workspace_manager.prepare_workspace(
                    module_name=self.module_name,
                )
                
            if not self._workspace_dir:
                return False, "[AnaURPAgent] Pre-conditions failed. Failed to setup workspace directory."

            logger.info(
                f"[AnaURPAgent._check_preconditions] Workspace ready: "
                f"{self._workspace_dir}"
            )
            
            return True, "Pre-conditions satisfied. Iteration directory created."

        except Exception as e:
            msg = f"[AnaURPAgent._check_preconditions] Exception: {e}"
            logger.exception(msg)
            return False, msg

    # ------------------------------------------------------------------
    # Process  (maps: handle_trigger_w1 / W1 invocation)
    # ------------------------------------------------------------------

    async def process(self, message: MessageEnvelope) -> Any:
        """
        Core execution — invokes ANA-W1 (circuit synthesis / error-correction).

        Mapped from: handle_trigger_w1 in ANADStateMachine.

        Paths configured
        ----------------
        - scud_path              : .scud file from current iteration (symlinked by WorkspaceManager)
        - circuit_file_path      : expected output .tsx path
        - schematic_images_path  : schematic images directory (symlinked)
        - library_path           : lib/imports directory (symlinked)
        - observations           : pulled from message payload OR from pending
                                   error message set by previous post-condition REJECT

        ANA-W1 operating mode is determined by whether previous_iteration_dir
        is set (error-correction) or not (synthesis).  No branch on observation
        list alone — this aligns with the URP design discussion outcome.
        """
        logger.info(
            f"[AnaURPAgent.process] Starting ANA-W1 for module='{self.module_name}', "
            f"iteration='{self._workspace_dir}'"
        )

        self._pending_error_message = None  #NOTE: orchestrator should consume last error message before calling process again

        user_message = message.payload["text"]
        
        
        logger.info(
            f"[AnaURPAgent.process] Sending messsage: {user_message}"
        )

        self.conversation.send_message(
            Message(
                role="user",
                content=[TextContent(text=user_message)],
            )
        )

        # Run conversation in thread as it is synchronous
        await asyncio.to_thread(self.conversation.run)
        
    
        if self.conversation.state.execution_status == ConversationExecutionStatus.PAUSED:
            process_outcome = LastTaskOutcome.WAITING_FOR_USER_INPUT
        elif self.conversation.state.execution_status == ConversationExecutionStatus.FINISHED: # Conversation has completed current task. last task outcome is success
            process_outcome = LastTaskOutcome.TASK_COMPLETED
        elif self.conversation.state.execution_status in [ConversationExecutionStatus.STUCK, ConversationExecutionStatus.ERROR]:
            process_outcome = LastTaskOutcome.TASK_FAILED
        elif self.conversation.state.execution_status == ConversationExecutionStatus.IDLE:
            logger.error(f"[ArchyURPAgent:process]Conversation status is ConversationExecutionStatus.IDLE after running the conversation. This should never happen!!!")
            process_outcome = LastTaskOutcome.NONE
        else:
            process_outcome = LastTaskOutcome.NONE
        
        response = str(self.llm_messages[-1]) if self.llm_messages else "No response generated"
        payload = ProcessResultPayload(text=response)
        return ProcessResult(outcome=process_outcome, payload=payload)

    # ------------------------------------------------------------------
    # Post-conditions  (maps: handle_trigger_w2 + handle_authorize + handle_exit_success)
    # ------------------------------------------------------------------

    async def _check_postconditions(
        self, message: MessageEnvelope, process_result: ProcessResult
    ) -> tuple[bool, str]:
        """
        Post-condition hook — runs after process() succeeds.

        Mapped from:
        - handle_trigger_w2    : run ANA-W2 validation agent (VAP)
        - handle_authorize     : act on VAP decision (ACCEPT / REJECT)
        - handle_exit_success  : promote to Stable/, archive, record op, condense

        VAP ACCEPT path
        ---------------
        1. Promote iteration directory contents to Stable/.
        2. Move all iteration directories to Archives/.
        3. Record CIRCUIT_SYNTHESIS operation via WorkspaceManager.
        4. Run AnaEvaluator to write the evaluator signature into semantic_operations.
        5. Sync project with runtime.
        6. Condense conversation history (avoids context bloat next iteration).
        7. Return (True, ...).

        VAP REJECT path
        ---------------
        1. Collect evaluation logs from the iteration's eval_results/ directory.
        2. Save them for the next ANA invocation (stash in self._pending_error_message).
        3. Condense conversation history.
        4. Return (False, reject_reason) — URP framework will emit TASK_POSTCONDITIONS_VIOLATED
           which triggers a new corrective invocation with ANA in error-correction mode.
        """
        if not self._workspace_dir:
            process_result.category = FailureCategory.INFRASTRUCTURE_FAILURE
            return False, "Iteration directory not set — cannot run W2 validation."
        
        # Confirm ANA-W1 produced the expected circuit file
        circuit_tsx_path = self.workspace_manager.get_maw_workspace_circuit_path(
            module_name=self.module_name
        )
        if not circuit_tsx_path.exists():
            process_result.category = FailureCategory.AGENTIC_FAILURE
            return False,f"ANA-W1 did not produce a circuit .tsx file in {self._workspace_dir}."
        logger.info(
            f"[AnaURPAgent._check_postconditions] module='{self.module_name}', iteration='{self._workspace_dir}', circuit_tsx_path='{circuit_tsx_path}"
        )


        iteration_dir = self._workspace_dir
        circuit_name = self.workspace_manager.circuit_name.get(self.module_name)
        iteration_id = "workspace"

        # ---- Step 1: Run ANA-W2 (VAP) ----
        logger.info("[AnaURPAgent._check_postconditions] Launching ANA-W2 validation agent.")
        try:
            w2_agent = ANA_validation_agent(
                web_socket_client=self.web_socket_client,
                sync_client=self.sync_client,
                project_id=self.workspace_manager.project_name,
            )
            vap_result = await w2_agent.validate_circuit(
                circuit_name=circuit_name,
                workspace=str(iteration_dir),
                iteration_id=iteration_id,
                module_name=self.module_name
            )
        except Exception as e:
            msg = f"[AnaURPAgent._check_postconditions] ANA-W2 raised exception: {e}"
            logger.exception(msg)
            process_result.category = FailureCategory.INFRASTRUCTURE_FAILURE
            return False, msg
        finally:
            try:
                w2_agent.close()
            except Exception:
                pass

        vap_decision = vap_result.get("decision", "UNKNOWN").upper()
        logger.info(
            f"[AnaURPAgent._check_postconditions] VAP decision: {vap_decision}"
        )

        # ---- Step 2: Act on VAP decision ----
        # NOTE: following handlers update the process_result.category if any failures occur.
        try:
            if vap_decision == "ACCEPT":
                    return await self._handle_vap_accept(vap_result=vap_result) 

            elif vap_decision == "REJECT":
                process_result.category = FailureCategory.VALIDATION_FAILURE
                return await self._handle_vap_reject(vap_result=vap_result)
            else:
                msg = (
                    f"[AnaURPAgent._check_postconditions] Unexpected VAP decision: "
                    f"'{vap_decision}'. Treating as REJECT."
                )
                logger.error(msg)
                process_result.category = FailureCategory.VALIDATION_FAILURE
                return False, msg
        except e:
            msg = (f"[AnaURPAgent._handle_vap_accept] Failed: {e}")
            logger.error(msg)
            process_result.category = FailureCategory.INFRASTRUCTURE_FAILURE
            return False, msg

    # ------------------------------------------------------------------
    # Internal helpers — VAP ACCEPT / REJECT handlers
    # ------------------------------------------------------------------

    async def _handle_vap_accept(
        self, vap_result: dict,
    ) -> tuple[bool, str]:
        """
        Handle VAP ACCEPT:
        1. Promote iteration → Stable/
        2. Archive all iterations
        3. Record CIRCUIT_SYNTHESIS operation (Git commit + SQLite)
        4. Run AnaEvaluator to write evaluator signature
        5. Sync project with runtime
        6. Condense conversation history
        """
        logger.info("[AnaURPAgent._handle_vap_accept] VAP ACCEPTED — promoting to Stable/.")

        # 1. Promote circuit to Stable/
        self.workspace_manager.populate_stable(
            module_name=self.module_name,
        )
        logger.info(
            f"[AnaURPAgent._handle_vap_accept] Stable/ populated from Workspace/"
        )

        # 2. Move current workspace to Archives/
        self.workspace_manager.archive_workspace(
            module_name=self.module_name
        )
        logger.info("[AnaURPAgent._handle_vap_accept] Workspace archived.")
    

        # 3. Record CIRCUIT_SYNTHESIS operation
        snapshot_id = self.workspace_manager.record_operation(
            module_name=self.module_name,
            op_name=ANA_OPERATION_NAME,
            author=self.descriptor.agent_id,
            status="SUCCESS",
            payload={
                "vap_decision": vap_result.get("decision"),
                "task_id": vap_result.get("task_id"),
                "circuit_name": self.workspace_manager.circuit_name.get(self.module_name),
            },
            commit_message=f"CIRCUIT_SYNTHESIS: Module '{self.module_name}' validated successfully",
        )
        logger.info(
            f"[AnaURPAgent._handle_vap_accept] CIRCUIT_SYNTHESIS recorded. "
            f"Snapshot ID: {snapshot_id}"
        )

        # 4. Sync project with runtime
        await self.sync_client.sync_compiled_circuit(project_id=self.workspace_manager.project_name, iteration_id="workspace",module_name=self.module_name)
        logger.info(f"[AnaURPAgent._handle_vap_accept] StableCircuit and CompiledCircuit sync completed successfully")

        # 5. Send evaluation update to the runtime 
        await self.web_socket_client.emit_evaluation_update(task_id=vap_result.get("task_id"), decision=vap_result.get("decision"))
        logger.info(f"[AnaURPAgent._handle_vap_accept] Sent evaluation update to vhl-runtime")
        
        # 6. Condense conversation history to prevent context bloat on next iteration
        self.conversation.condense()
        logger.info("[AnaURPAgent._handle_vap_accept] Condensed conversation")

        return (
            True,
            f"VAP ACCEPTED. Circuit for module '{self.module_name}' promoted to Stable/.",
        )
        
    async def _handle_vap_reject(
        self, vap_result: dict,
    ) -> tuple[bool, str]:
        """
        Handle VAP REJECT:
        1. Collect evaluation logs from eval_results/
        2. Build a structured error message and stash it for the next iteration
        3. Condense conversation history (fresh-start feel for error correction)
        4. Return (False, reject_reason) to signal TASK_POSTCONDITIONS_VIOLATED
        """
        logger.info(
            "[AnaURPAgent._handle_vap_reject] VAP REJECTED — preparing error-correction "
            "context for next iteration."
        )

        eval_results_dir = self.workspace_manager.workspace_path.get(self.module_name) / "eval_results"
        error_summary_parts = [
            "The circuit failed VAP evaluation. Please analyse the following evaluation "
            "output file and correct the circuit accordingly.(first 4000 characters of the output log files are attached here for your reference)\n"
        ]

        if eval_results_dir.exists():
            log_files = list(eval_results_dir.glob("*"))
            if log_files:
                for log_file in log_files[:3]:  # limit to first 3 files
                    try:
                        content = log_file.read_text(encoding="utf-8", errors="replace")
                        error_summary_parts.append(
                            f"\n--- {log_file.resolve()} ---\n{content[:4000]}"  # cap per file
                        )
                    except Exception as e:
                        logger.warning(
                            f"[AnaURPAgent._handle_vap_reject] Could not read log "
                            f"{log_file}: {e}"
                        )
            else:
                error_summary_parts.append(
                    "\nEvaluation results directory is empty. "
                    "No detailed logs available."
                )
        else:
            error_summary_parts.append(
                "\nNo eval_results/ directory found in iteration. "
                "No detailed logs available."
            )

        # Stash the error message — process() will inject it into observations
        # on the next invocation so ANA-W1 sees it as an error-correction task.
        self._pending_error_message = "".join(error_summary_parts)

        logger.info(
            "[AnaURPAgent._handle_vap_reject] Error message stashed for next iteration."
        )

        # Condense conversation history — 
        # every error-correction iteration starts with a condensed history
        self.conversation.condense()
        logger.info("[AnaURPAgent._handle_vap_reject] Condensed conversation")

        reject_reason = (
            f"VAP REJECTED for module '{self.module_name}'. "
            "Error-correction iteration will be triggered. "
            f"Task ID: {vap_result.get('task_id', 'N/A')}"
        )
        return False, reject_reason


    # VAP iteration handling 
    @property
    async def pending_error(self):
        return self._pending_error_message
    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    async def _on_shutdown(self) -> None:
        """Clean up resources on graceful shutdown."""
        logger.info(
            f"[AnaURPAgent._on_shutdown] Shutting down ANA URP agent for "
            f"module='{self.module_name}'"
        )
        self.conversation = None
        self.agent = None