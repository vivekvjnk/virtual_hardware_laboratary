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

from vhl_common.urp.abstract_urp import AbstractURPAgent
from vhl_common.urp.data_types import AgentDescriptor, MessageEnvelope
from vhl_common.utils import setup_dedicated_logger
from workspace.manager import WorkspaceManager
from vhl_common.project_state_manager import SQLiteManager
from vhl_protocol.sync.client import SyncClient
from vhl_protocol.client.client import VHLWebSocketClient

from ana_agent.ana_worker_1 import run_ana_w1_agent
from ana_agent.ana_worker_2.agent import ANA_validation_agent
from ana_agent.ana_evaluator import AGENT_ID as ANA_AGENT_ID, OPERATION_NAME as ANA_OPERATION_NAME, AnaEvaluator

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
    project_id: str
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
        self.project_id: Optional[str] = None

        # Iteration state — set fresh in pre-conditions each invocation
        self._iteration_dir: Optional[Path] = None
        self._previous_iteration_dir: Optional[Path] = None

        # Error payload forwarded from a REJECT post-condition into the next
        # process() call so ANA-W1 can self-correct.
        self._pending_error_message: Optional[str] = None

    # ------------------------------------------------------------------
    # Lifecycle: _on_initialize
    # ------------------------------------------------------------------

    def _on_initialize(self, context: AnaContext) -> None:
        """
        MAW (Model–Agent–Workspace) setup.

        Responsibilities (mapped from state machine initialisation):
        - Parse and validate AnaContext.
        - Initialise LLM, condenser, Agent, and Conversation objects.
        - Bind WorkspaceManager, SQLiteManager, and protocol clients.
        - The Conversation is opened with persistence so that condensation
          across error-correction iterations is possible.
        """
        # Accept both raw dict (from URP runtime) and AnaContext instance
        try:
            if isinstance(context, dict):
                context = AnaContext(**context)
        except Exception as e:
            logger.error(f"[AnaURPAgent._on_initialize] Failed to parse AnaContext: {e}")
            raise ValueError(f"Invalid configuration for AnaURPAgent: {e}")

        self.workspace_manager = context.workspace
        self.sqlite_manager = context.sqlite_manager
        self.module_name = context.module_name
        self.web_socket_client = context.web_socket_client
        self.sync_client = context.sync_client
        self.project_id = context.project_id
        config = context.config

        # ---- LLM setup ----
        if not self.llm:
            api_key = os.getenv("LLM_API_KEY", "dummy_key")
            if api_key == "dummy_key":
                logger.warning("[AnaURPAgent._on_initialize] LLM_API_KEY not set. Using dummy key.")
            base_url = os.getenv("LLM_BASE_URL")
            model = os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929")
            self.llm = LLM(
                usage_id="ana_urp_agent",
                model=model,
                base_url=base_url,
                api_key=SecretStr(api_key),
            )

        # ---- Condenser pipeline (mirrors ANA-W1 pattern) ----
        # LargeFileSurgicalCondenser keeps file-editor events compact.
        # LLMSummarizingCondenser provides a rolling summary window for the
        # broader conversation so context does not blow up across iterations.
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
        # ANA-W1 prompt files are used directly; URP ANA delegates to run_ana_w1_agent
        # for the actual LLM work (W1 path), so no separate system prompt is needed
        # here for the outer agent.  The Conversation below serves as the
        # persistence/condensation container across iterations.
        tools = [
            Tool(name=FileEditorTool.name),
        ]
        self.agent = Agent(
            llm=self.llm,
            tools=tools,
            condenser=pipeline,
        )

        # ---- Conversation (persistence enables condensation across iterations) ----
        persistence_dir = None
        if config.conversation_persistence and self.workspace_manager.project_root:
            persistence_dir = str(
                self.workspace_manager.project_root / self.module_name / ".conversation"
            )

        self.conversation = Conversation(
            agent=self.agent,
            workspace=str(self.workspace_manager.project_root / self.module_name)
            if self.workspace_manager.project_root else ".",
            callbacks=[self._conversation_callback],
            persistence_dir=persistence_dir,
        )

        logger.info(
            f"[AnaURPAgent._on_initialize] Initialized for module='{self.module_name}', "
            f"project='{self.project_id}', persistence_dir='{persistence_dir}'"
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
             Copy Stable/ circuit into the new iteration directory.
           - If not found → first-time synthesis. Create a bare iteration directory.
        2. Create new iteration directory via WorkspaceManager.
        3. Stash iteration paths on self for use by process() and post-conditions.

        NOTE: The first-iteration flag from the legacy SM is intentionally
        dropped — DB state is the single source of truth.
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

            is_first_synthesis = prior_synthesis is None

            if is_first_synthesis:
                logger.info(
                    "[AnaURPAgent._check_preconditions] No prior synthesis found. "
                    "Operating in first-synthesis mode."
                )
            else:
                logger.info(
                    "[AnaURPAgent._check_preconditions] Prior synthesis detected. "
                    "Operating in error-correction / improvement mode."
                )

            # ---- 2. If prior synthesis exists, prepare iteration with stable circuit ----
            if not is_first_synthesis:
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

                # Derive suffix for iteration ID inside WorkspaceManager
                import uuid
                iteration_id_suffix = str(uuid.uuid4()).split("-")[0][:8]

                # Collect observations/user instructions from message payload
                observations = message.payload.get("observations", []) if message.payload else []

                # prepare_iteration_with_files: creates iteration dir + copies stable circuit
                iteration_path = self.workspace_manager.prepare_iteration_with_files(
                    source_file=str(stable_circuit_path),
                    iteration_id_suffix=iteration_id_suffix,
                    module_name=self.module_name,
                    observations=observations if observations else None,
                )
                # Track previous iteration (the one that was active before this call)
                self._previous_iteration_dir = self.workspace_manager.previous_iteration_path[
                    self.module_name
                ]
                self._iteration_dir = iteration_path

            else:
                # ---- 3. First synthesis — create a bare iteration directory ----
                import uuid
                iteration_id_suffix = str(uuid.uuid4()).split("-")[0][:8]
                iteration_path = self.workspace_manager.create_new_iteration(
                    hash_val=iteration_id_suffix,
                    module_name=self.module_name,
                )
                self._previous_iteration_dir = None
                self._iteration_dir = iteration_path

            logger.info(
                f"[AnaURPAgent._check_preconditions] Iteration directory ready: "
                f"{self._iteration_dir}"
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
            f"iteration='{self._iteration_dir}'"
        )

        if not self._iteration_dir:
            raise RuntimeError(
                "[AnaURPAgent.process] Iteration directory not set. "
                "Pre-conditions must run before process()."
            )

        try:
            scud_path: Path = self.workspace_manager.get_scud_path(
                module_name=self.module_name
            )
            library_path: Path = self.workspace_manager.get_library_path(
                module_name=self.module_name
            )
            circuit_name = self.workspace_manager.circuit_name[self.module_name]
            current_iter_dir = self._iteration_dir
            schematic_images_path = str(current_iter_dir / "schematic_images")

            # Observations: prefer pending error from previous REJECT, then message payload
            observations: list = []
            if self._pending_error_message:
                logger.info(
                    "[AnaURPAgent.process] Injecting pending error message from previous "
                    "REJECT into observations for error-correction."
                )
                observations.append(self._pending_error_message)
                self._pending_error_message = None  # consumed

            payload_observations = (
                message.payload.get("observations", []) if message.payload else []
            )
            observations.extend(payload_observations)

            previous_iter_dir = self._previous_iteration_dir

            logger.info(
                f"[AnaURPAgent.process] Mode: "
                f"{'error-correction' if previous_iter_dir else 'synthesis'}, "
                f"observations={len(observations)}, "
                f"circuit_name='{circuit_name}'"
            )

            await asyncio.to_thread(
                run_ana_w1_agent,
                workspace=str(current_iter_dir),
                schematic_images_path=schematic_images_path,
                scud_path=str(scud_path),
                circuit_name=circuit_name,
                observations=observations if observations else None,
                previous_iteration_dir=str(previous_iter_dir) if previous_iter_dir else None,
                library_path=library_path,
            )

            # Confirm ANA-W1 produced the expected circuit file
            circuit_tsx_path = self.workspace_manager.get_circuit_tsx_path(
                module_name=self.module_name
            )
            if not circuit_tsx_path.exists():
                # Try to find any .tsx file and rename it (defensive handling from SM)
                tsx_files = list(Path(str(current_iter_dir)).glob("*.tsx"))
                if tsx_files:
                    logger.warning(
                        f"[AnaURPAgent.process] Expected circuit file not found at "
                        f"{circuit_tsx_path}. Renaming {tsx_files[0]} to match."
                    )
                    shutil.move(str(tsx_files[0]), str(circuit_tsx_path))
                else:
                    raise FileNotFoundError(
                        f"ANA-W1 did not produce a circuit .tsx file in {current_iter_dir}."
                    )

            logger.info(
                f"[AnaURPAgent.process] ANA-W1 completed. Circuit at: {circuit_tsx_path}"
            )

            return {
                "status": "W1_COMPLETE",
                "circuit_tsx_path": str(circuit_tsx_path),
                "iteration_dir": str(current_iter_dir),
                "module_name": self.module_name,
            }

        except Exception as e:
            logger.exception(f"[AnaURPAgent.process] Error during ANA-W1 execution: {e}")
            raise

    # ------------------------------------------------------------------
    # Post-conditions  (maps: handle_trigger_w2 + handle_authorize + handle_exit_success)
    # ------------------------------------------------------------------

    async def _check_postconditions(
        self, message: MessageEnvelope, result: Any
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
        logger.info(
            f"[AnaURPAgent._check_postconditions] module='{self.module_name}', "
            f"iteration='{self._iteration_dir}'"
        )

        if not self._iteration_dir:
            return False, "Iteration directory not set — cannot run W2 validation."

        iteration_dir = self._iteration_dir
        circuit_name = self.workspace_manager.circuit_name.get(self.module_name)
        iteration_id = self.workspace_manager.get_current_iteration_id(
            module_name=self.module_name
        )

        # ---- Step 1: Run ANA-W2 (VAP) ----
        logger.info("[AnaURPAgent._check_postconditions] Launching ANA-W2 validation agent.")
        try:
            w2_agent = ANA_validation_agent(
                web_socket_client=self.web_socket_client,
                sync_client=self.sync_client,
                project_id=self.project_id,
            )
            vap_result = await w2_agent.validate_circuit(
                circuit_name=circuit_name,
                workspace=str(iteration_dir),
                iteration_id=iteration_id,
            )
        except Exception as e:
            msg = f"[AnaURPAgent._check_postconditions] ANA-W2 raised exception: {e}"
            logger.exception(msg)
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
        if vap_decision == "ACCEPT":
            return await self._handle_vap_accept(vap_result, iteration_dir)
        elif vap_decision == "REJECT":
            return await self._handle_vap_reject(vap_result, iteration_dir)
        else:
            msg = (
                f"[AnaURPAgent._check_postconditions] Unexpected VAP decision: "
                f"'{vap_decision}'. Treating as REJECT."
            )
            logger.error(msg)
            return False, msg

    # ------------------------------------------------------------------
    # Internal helpers — VAP ACCEPT / REJECT handlers
    # ------------------------------------------------------------------

    async def _handle_vap_accept(
        self, vap_result: dict, iteration_dir: Path
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
        try:
            self.workspace_manager.populate_stable(
                iteration_id=str(iteration_dir),
                module_name=self.module_name,
            )
            logger.info(
                f"[AnaURPAgent._handle_vap_accept] Stable/ populated from {iteration_dir}"
            )
        except Exception as e:
            msg = f"[AnaURPAgent._handle_vap_accept] Failed to populate Stable/: {e}"
            logger.error(msg)
            return False, msg

        # 2. Move all iteration directories to Archives/
        try:
            self.workspace_manager.move_iterations_to_archives(
                module_name=self.module_name
            )
            logger.info("[AnaURPAgent._handle_vap_accept] Iterations archived.")
        except Exception as e:
            logger.warning(
                f"[AnaURPAgent._handle_vap_accept] Failed to archive iterations: {e}"
            )

        # 3. Record CIRCUIT_SYNTHESIS operation
        try:
            snapshot_id = self.workspace_manager.record_operation(
                module_name=self.module_name,
                op_name=ANA_OPERATION_NAME,
                author=self.descriptor.agent_id,
                status="SUCCESS",
                payload={
                    "vap_decision": "ACCEPT",
                    "task_id": vap_result.get("task_id"),
                    "circuit_name": self.workspace_manager.circuit_name.get(self.module_name),
                },
                commit_message=f"CIRCUIT_SYNTHESIS: Module '{self.module_name}' validated successfully",
            )
            logger.info(
                f"[AnaURPAgent._handle_vap_accept] CIRCUIT_SYNTHESIS recorded. "
                f"Snapshot ID: {snapshot_id}"
            )
        except Exception as e:
            msg = (
                f"[AnaURPAgent._handle_vap_accept] Failed to record CIRCUIT_SYNTHESIS "
                f"operation: {e}"
            )
            logger.error(msg)
            return False, msg

        # 4. Run AnaEvaluator to stamp the canonical "synthesis done" marker
        try:
            evaluator = AnaEvaluator(db=self.sqlite_manager, module_name=self.module_name)
            eval_result, eval_desc = evaluator.evaluate(snapshot_id=snapshot_id)
            logger.info(
                f"[AnaURPAgent._handle_vap_accept] AnaEvaluator: {eval_result} — {eval_desc}"
            )
        except Exception as e:
            logger.warning(
                f"[AnaURPAgent._handle_vap_accept] AnaEvaluator failed (non-fatal): {e}"
            )

        # 5. Sync project with runtime
        if self.sync_client and self.project_id:
            try:
                await self.sync_client.sync_library(self.project_id)
                logger.info("[AnaURPAgent._handle_vap_accept] Project synced with runtime.")
            except Exception as e:
                logger.warning(
                    f"[AnaURPAgent._handle_vap_accept] Runtime sync failed (non-fatal): {e}"
                )

        # 6. Condense conversation history to prevent context bloat on next iteration
        self._condense_conversation()

        return (
            True,
            f"VAP ACCEPTED. Circuit for module '{self.module_name}' promoted to Stable/.",
        )

    async def _handle_vap_reject(
        self, vap_result: dict, iteration_dir: Path
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

        eval_results_dir = iteration_dir / "eval_results"
        error_summary_parts = [
            "The circuit failed VAP evaluation. Please analyse the following evaluation "
            "output and correct the circuit accordingly.\n"
        ]

        if eval_results_dir.exists():
            log_files = list(eval_results_dir.glob("*"))
            if log_files:
                for log_file in log_files[:3]:  # limit to first 3 files
                    try:
                        content = log_file.read_text(encoding="utf-8", errors="replace")
                        error_summary_parts.append(
                            f"\n--- {log_file.name} ---\n{content[:4000]}"  # cap per file
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

        # Condense conversation history — every error-correction iteration starts
        # with a condensed history (design discussion: "condensation approach")
        self._condense_conversation()

        reject_reason = (
            f"VAP REJECTED for module '{self.module_name}'. "
            "Error-correction iteration will be triggered. "
            f"Task ID: {vap_result.get('task_id', 'N/A')}"
        )
        return False, reject_reason

    def _condense_conversation(self):
        """
        Trigger conversation condensation to prevent context bloat.
        Called after both ACCEPT and REJECT VAP outcomes so that every new
        iteration starts with a lean history (design principle from discussion).
        """
        if self.conversation:
            try:
                # Conversation.condense() triggers the registered condenser pipeline
                # (surgical + LLM summarising).  This is the "condensation" step
                # discussed in the design chat to avoid context explosion across
                # error-correction iterations.
                self.conversation.condense()
                logger.info(
                    "[AnaURPAgent._condense_conversation] Conversation history condensed."
                )
            except AttributeError:
                # condense() may not exist in all SDK versions; log and continue
                logger.warning(
                    "[AnaURPAgent._condense_conversation] conversation.condense() not "
                    "available in current SDK. Skipping condensation."
                )
            except Exception as e:
                logger.warning(
                    f"[AnaURPAgent._condense_conversation] Condensation failed: {e}"
                )

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