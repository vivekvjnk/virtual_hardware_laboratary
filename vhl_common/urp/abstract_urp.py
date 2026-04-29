import asyncio
import uuid
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, Optional

from .data_types import AgentDescriptor, AgentContext, AgentState, MessageEnvelope, EventEnvelope

class AgentStatus(Enum):
    """Strict state machine enforcement per URP Section 2."""
    UNINITIALIZED = "UNINITIALIZED"
    INITIALIZED = "INITIALIZED"
    WAITING = "WAITING"
    PROCESSING = "PROCESSING"
    ERROR = "ERROR"
    TERMINATING = "TERMINATING"
    TERMINATED = "TERMINATED"

class AbstractURPAgent(ABC):
    """
    Abstract Unified Runtime Primitive (URP).
    Enforces the lifecycle, mailbox, and state invariants.
    """

    def __init__(self, descriptor: 'AgentDescriptor'):
        # 1. Addressable Identity
        self.descriptor = descriptor
        
        # 3. Persistent State (initialized to baseline)
        self.state = AgentState(
            session_id=str(uuid.uuid4()), 
            status=AgentStatus.UNINITIALIZED.value
        )
        
        # 4. Mailbox
        self.mailbox: asyncio.Queue['MessageEnvelope'] = asyncio.Queue()
        
        # Internal Runtime hooks
        self.context: Optional['AgentContext'] = None
        self._emit_callback: Optional[Callable[['EventEnvelope'], None]] = None
        self._shutdown_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None

    # ---------------------------------------------------------
    # LIFECYCLE CONTRACT (URP Section 4)
    # ---------------------------------------------------------

    def initialize(self, context, emit_callback: Callable[['EventEnvelope'], None]) -> None:
        """Runs exactly once. Binds dependencies and event bus."""
        # Invariant 1: Initialize exactly once
        if self.state.status != AgentStatus.UNINITIALIZED.value:
            raise RuntimeError(f"Cannot initialize agent in state: {self.state.status}")
        
        self.context = context
        self._emit_callback = emit_callback
        
        # Allow child classes to perform specific initialization (e.g., loading prompts)
        self._on_initialize(context)
        
        self.state.status = AgentStatus.INITIALIZED.value

    async def start(self) -> None:
        """Makes agent runnable. Enters WAITING state."""
        if self.state.status != AgentStatus.INITIALIZED.value:
            raise RuntimeError(f"Agent must be INITIALIZED to start. Current: {self.state.status}")
        
        self.state.status = AgentStatus.WAITING.value
        self._task = asyncio.create_task(self._lifecycle_loop())
        
        self.emit(EventEnvelope(
            type="AGENT_STARTED",
            payload={"session_id": self.state.session_id},
            source_agent_id=self.descriptor.agent_id
        ))

    async def send(self, message: 'MessageEnvelope') -> None:
        """Asynchronous mailbox delivery. Invariant 3: Messages enter only through mailbox."""
        if self.state.status in (AgentStatus.TERMINATING.value, AgentStatus.TERMINATED.value):
            raise RuntimeError("Cannot send message to a terminating/terminated agent.")
            
        await self.mailbox.put(message)

    def emit(self, event: 'EventEnvelope') -> None:
        """Pushes output to runtime bus. Invariant 4: Outputs leave only through emit."""
        if self._emit_callback:
            self._emit_callback(event)

    async def shutdown(self) -> None:
        """Graceful termination."""
        self.state.status = AgentStatus.TERMINATING.value
        self._shutdown_event.set()
        
        # Allow child classes to clean up resources
        await self._on_shutdown()
        
        if self._task:
            await self._task
            
        self.state.status = AgentStatus.TERMINATED.value
        self.emit(EventEnvelope(
            type="AGENT_TERMINATED",
            payload=None,
            source_agent_id=self.descriptor.agent_id
        ))

    # ---------------------------------------------------------
    # SCHEDULER CONTRACT (URP Section 5)
    # ---------------------------------------------------------

    async def _lifecycle_loop(self) -> None:
        """
        The mandated single invariant loop:
        WAITING -> receive message -> PROCESSING -> emit events -> WAITING
        """
        while not self._shutdown_event.is_set():
            try:
                # 1. WAITING
                self.state.status = AgentStatus.WAITING.value
                
                message = await asyncio.wait_for(self.mailbox.get(), timeout=0.5)
                
                # 2. PROCESSING
                self.state.status = AgentStatus.PROCESSING.value
                
                try:
                    # Capture the return value from the implementation (e.g., LangGraph result)
                    result = await self.process(message)
                    
                    # 3. AUTO-EMIT FINAL RESULT
                    # If process() returns data, we treat it as a successful task completion.
                    if result is not None:
                        self.emit(EventEnvelope(
                            type="TASK_COMPLETED",
                            payload={
                                "result": result, 
                                "message_id": message.message_id,
                                "correlation_id": message.correlation_id
                            },
                            source_agent_id=self.descriptor.agent_id
                        ))
                        
                except Exception as e:
                    self.emit(EventEnvelope(
                        type="TASK_FAILED",
                        payload={
                            "error": str(e), 
                            "message_id": message.message_id,
                            "correlation_id": message.correlation_id
                        },
                        source_agent_id=self.descriptor.agent_id
                    ))
                finally:
                    self.mailbox.task_done()
                    
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break


    # ---------------------------------------------------------
    # ABSTRACT METHODS (To be implemented by specific agents)
    # ---------------------------------------------------------

    @abstractmethod
    async def process(self, message: 'MessageEnvelope') -> Any:
        """
        Core execution primitive.
        Must invoke LLM, tools, mutate state, and emit events without violating invariants.
        """
        pass

    @abstractmethod
    def _on_initialize(self, context) -> None:
        """Hook for child classes during initialization."""
        pass

    # ---------------------------------------------------------
    # OPTIONAL EXTENSION HOOKS
    # ---------------------------------------------------------

    async def _on_shutdown(self) -> None:
        """Optional hook for child classes during shutdown."""
        pass

    # ---------------------------------------------------------
    # OPTIONAL INSPECTION INTERFACES (URP Section 6)
    # ---------------------------------------------------------

    def inspect_state(self) -> Dict[str, Any]:
        """Returns a safe, read-only view of the agent's current state."""
        return {
            "agent_id": self.descriptor.agent_id,
            "status": self.state.status,
            "session_id": self.state.session_id,
            "mailbox_size": self.mailbox.qsize()
        }