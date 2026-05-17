"""
Agent Registry
==============

State-aware control surface over persistent URP agents.

The registry enables an orchestrator (AOSM) to:
  * discover agents
  * inspect their state
  * determine readiness
  * communicate via mailbox handles

It is intentionally **passive** — it tracks agents and exposes state,
but does NOT trigger agents or decide workflows.

Design alignment:
  - "Systems decide; agents propose"
  - No authority leakage
  - No hidden state
  - No implicit assumptions

See: docs/source/mas/agent_registry/agent_registry_design.md
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from .abstract_urp import AbstractURPAgent, AgentStatus
from .agent_key import AgentKey, AgentReadiness, AgentEntry, AgentHandle
from .data_types import EventEnvelope

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Central registry for persistent URP agent instances.

    Lifecycle:
      1. AOSM creates the registry once (e.g., in __init__)
      2. As the pipeline progresses, AOSM calls get_or_create() to
         obtain handles for agents it needs
      3. Agents persist across AOSM state transitions
      4. On project close, AOSM calls shutdown_all()

    Thread safety:
      The registry is designed for single-threaded async usage
      (asyncio event loop). No internal locking is provided.
    """

    def __init__(self):
        self._agents: Dict[AgentKey, AgentEntry] = {}
        logger.info("[AgentRegistry] Initialized (empty)")

    # -----------------------------------------------------------------
    # Registration
    # -----------------------------------------------------------------

    def register(
        self,
        key: AgentKey,
        agent: AbstractURPAgent,
        emit_callback: Optional[Callable[['EventEnvelope'], None]] = None,
    ) -> AgentHandle:
        """
        Registers a pre-created agent under the given key.

        The agent must already be initialized (status == INITIALIZED or later).
        If an emit_callback is provided, it is wired into the agent.

        Raises:
            ValueError: If an agent is already registered under this key.
        """
        if key in self._agents:
            raise ValueError(
                f"Agent already registered for key {key}. "
                f"Use get() to retrieve or shutdown_agent() first."
            )

        entry = AgentEntry(key=key, agent=agent)
        self._agents[key] = entry
        logger.info(f"[AgentRegistry] Registered agent: {key} (runtime_id={entry.runtime_id})")

        return AgentHandle(entry=entry, readiness_fn=self._compute_readiness)

    def get(self, key: AgentKey) -> Optional[AgentHandle]:
        """
        Retrieves the handle for a registered agent.

        Returns None if no agent is registered under this key.
        """
        entry = self._agents.get(key)
        if entry is None:
            return None
        return AgentHandle(entry=entry, readiness_fn=self._compute_readiness)

    def get_or_create(
        self,
        key: AgentKey,
        factory: Callable[[AgentKey], AbstractURPAgent],
        context: Any = None,
        emit_callback: Optional[Callable[['EventEnvelope'], None]] = None,
    ) -> AgentHandle:
        """
        Primary interaction pattern for AOSM.

        If an agent exists for the key, returns its handle (factory is NOT called).
        If not, invokes the factory to create a new agent, initializes it with
        the provided context and emit_callback, registers it, and returns the handle.

        This enables **progressive initialization** — agents are not globally
        created at startup but materialized on demand.

        Args:
            key: The semantic identity (agent_type, module_name)
            factory: Callable that receives the AgentKey and returns
                     a new (UNINITIALIZED) AbstractURPAgent instance
            context: Context dict/object passed to agent.initialize()
            emit_callback: Event callback wired into the agent

        Returns:
            AgentHandle for the (possibly new) agent
        """
        existing = self.get(key)
        if existing is not None:
            logger.debug(f"[AgentRegistry] Reusing existing agent for {key}")
            return existing

        # Create new agent via factory
        logger.info(f"[AgentRegistry] Creating new agent for {key} via factory")
        agent = factory(key)

        # Initialize with context and emit callback
        if context is not None or emit_callback is not None:
            agent.initialize(
                context=context,
                emit_callback=emit_callback or (lambda e: None),
            )

        return self.register(key=key, agent=agent)

    # -----------------------------------------------------------------
    # Discovery & Inspection
    # -----------------------------------------------------------------

    def list_agents(self, agent_type: Optional[str] = None) -> List[AgentEntry]:
        """
        Lists all registered agents, optionally filtered by agent_type.

        Returns:
            List of AgentEntry objects (internal records).
        """
        if agent_type is None:
            return list(self._agents.values())
        return [
            entry for entry in self._agents.values()
            if entry.key.agent_type == agent_type
        ]

    def get_agents_by_type(self, agent_type: str) -> Dict[str, AgentHandle]:
        """
        Returns a dict of module_name -> AgentHandle for all agents of a given type.

        Useful for AOSM to discover all archy agents across modules, for example.
        """
        return {
            entry.key.module_name: AgentHandle(entry=entry, readiness_fn=self._compute_readiness)
            for entry in self._agents.values()
            if entry.key.agent_type == agent_type
        }

    def contains(self, key: AgentKey) -> bool:
        """Checks if an agent is registered under this key."""
        return key in self._agents

    @property
    def size(self) -> int:
        """Number of agents currently registered."""
        return len(self._agents)

    # -----------------------------------------------------------------
    # Lifecycle Management
    # -----------------------------------------------------------------

    async def shutdown_agent(self, key: AgentKey) -> None:
        """
        Gracefully shuts down and deregisters a single agent.

        Calls the URP agent's shutdown() method, then removes it
        from the registry.

        No-op if the key is not registered.
        """
        entry = self._agents.get(key)
        if entry is None:
            logger.warning(f"[AgentRegistry] shutdown_agent called for unregistered key: {key}")
            return

        logger.info(f"[AgentRegistry] Shutting down agent: {key}")
        try:
            await entry.agent.shutdown()
        except Exception as e:
            logger.error(f"[AgentRegistry] Error during shutdown of {key}: {e}", exc_info=True)
        finally:
            del self._agents[key]
            logger.info(f"[AgentRegistry] Agent deregistered: {key}")

    async def shutdown_all(self) -> None:
        """
        Gracefully shuts down all registered agents.

        Iterates over a snapshot of keys to avoid mutation during iteration.
        """
        keys = list(self._agents.keys())
        logger.info(f"[AgentRegistry] Shutting down all agents ({len(keys)} total)")
        for key in keys:
            await self.shutdown_agent(key)
        logger.info("[AgentRegistry] All agents shut down")

    # -----------------------------------------------------------------
    # Readiness Computation (Section 5 of design doc)
    # -----------------------------------------------------------------

    def _compute_readiness(self, entry: AgentEntry) -> AgentReadiness:
        """
        Computes system-level readiness for an agent.

        This is the **single point of readiness logic**.  Currently derives
        readiness purely from the agent's URP lifecycle state.  When external
        dependency checks are needed (e.g., SCUD existence, library availability),
        extend this method — all readiness logic is concentrated here.

        Readiness mapping (V1 — lifecycle-only):
            WAITING     -> READY       (agent is idle, can accept messages)
            PROCESSING  -> NOT_READY   (agent is busy)
            INITIALIZED -> NOT_READY   (agent not yet started)
            UNINITIALIZED -> NOT_READY
            ERROR       -> NOT_READY
            TERMINATING -> TERMINATED
            TERMINATED  -> TERMINATED
        """
        status_str = entry.agent.state.get("status", AgentStatus.UNINITIALIZED.value)

        if status_str == AgentStatus.WAITING.value:
            # --- Future extension point ---
            # When external dependency checks are added, they go here:
            #   if not self._check_external_dependencies(entry):
            #       return AgentReadiness.DEGRADED
            return AgentReadiness.READY

        if status_str in (AgentStatus.TERMINATING.value, AgentStatus.TERMINATED.value):
            return AgentReadiness.TERMINATED

        # All other states: agent exists but can't accept work
        return AgentReadiness.NOT_READY

    # -----------------------------------------------------------------
    # Observability
    # -----------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        """
        Returns a serializable snapshot of the entire registry state.

        Useful for heartbeat/telemetry emission.
        """
        return {
            "agent_count": self.size,
            "agents": {
                str(key): {
                    "runtime_id": entry.runtime_id,
                    "status": entry.agent.state.get("status", "UNKNOWN"),
                    "readiness": self._compute_readiness(entry).value,
                    "mailbox_size": entry.agent.mailbox.qsize(),
                    "created_at": entry.created_at.isoformat(),
                }
                for key, entry in self._agents.items()
            },
        }

    def __repr__(self) -> str:
        agents_str = ", ".join(str(k) for k in self._agents.keys())
        return f"AgentRegistry(size={self.size}, agents=[{agents_str}])"
