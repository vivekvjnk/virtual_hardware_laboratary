import asyncio
import uuid
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, Optional

from .data_types import AgentDescriptor, AgentContext, AgentState, MessageEnvelope
MAILBOX_POLL_INTERVAL = 0.5  # seconds

class AgentStatus(Enum):
    """Strict state machine enforcement per URP Section 2."""
    UNINITIALIZED = "UNINITIALIZED"
    INITIALIZED = "INITIALIZED"
    WAITING = "WAITING"
    PROCESSING = "PROCESSING"
    ERROR = "ERROR"
    TERMINATING = "TERMINATING"
    TERMINATED = "TERMINATED"

class PostconditionsViolatedError(Exception):
    """Raised when post-condition verification fails."""
    def __init__(self,result,message):
        """
        result: Agent execution result
        message: Error message
        """
        self.result = result
        super().__init__(message)

class PreconditionsViolatedError(Exception):
    """Raised when pre-condition verification fails."""
    pass

class StartPreconditionsViolatedError(Exception):
    """Raised when agent start precondition verification fails."""
    pass

class AbstractURPAgent(ABC):
    """
    Abstract Unified Runtime Primitive (URP).
    Enforces the lifecycle, mailbox, and state invariants.
    """

    def __init__(self, descriptor: 'AgentDescriptor'):
        # 1. Addressable Identity
        self.descriptor = descriptor
        
        # 3. Persistent State (initialized to baseline)
        self._state = AgentState(
            session_id=str(uuid.uuid4()), 
            status=AgentStatus.UNINITIALIZED.value
        )
        
        # 4. Mailbox
        self.mailbox: asyncio.Queue['MessageEnvelope'] = asyncio.Queue()
        
        # Internal Runtime hooks
        self.context: Optional['AgentContext'] = None
        self._emit_callback: Optional[Callable[['MessageEnvelope'], None]] = None
        self._shutdown_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None

    # ---------------------------------------------------------
    # LIFECYCLE CONTRACT (URP Section 4)
    # ---------------------------------------------------------

    def initialize(self, context, emit_callback: Callable[['MessageEnvelope'], None]) -> None:
        """Runs exactly once. Binds dependencies and event bus."""
        # Invariant 1: Initialize exactly once
        if self._state.status != AgentStatus.UNINITIALIZED.value:
            raise RuntimeError(f"Cannot initialize agent in state: {self._state.status}")
        
        self.context = context
        self.set_callback(emit_callback)
        
        # Allow child classes to perform specific initialization (e.g., loading prompts)
        self._on_initialize(context)
        
        self._state.status = AgentStatus.INITIALIZED.value
    
    def set_callback(self,emit_callback: Callable[['MessageEnvelope'], None]) -> None:
        """Allows resetting the emit callback, useful for testing or dynamic rebinding."""
        self._emit_callback = emit_callback

    async def start(self) -> None:
        """Makes agent runnable. Enters WAITING state."""
        if self._state.status != AgentStatus.INITIALIZED.value:
            raise RuntimeError(f"Agent must be INITIALIZED to start. Current: {self._state.status}")
        
        # Check start preconditions
        precond_res = await self._check_start_preconditions()
        if isinstance(precond_res, tuple):
            start_ok, result = precond_res
        else:
            start_ok = precond_res
            result = "Start preconditions check failed" if not start_ok else "Start precondition check successful"
            
        if not start_ok:
            await self.emit(MessageEnvelope(
                type="AGENT_START_PRECONDITIONS_VIOLATED",
                payload={"reason": result,"text": result},
                sender=self.descriptor.agent_id
            ))
            raise StartPreconditionsViolatedError(f"Start preconditions check failed: {result}")
            
        self._state.status = AgentStatus.WAITING.value
        self._task = asyncio.create_task(self._lifecycle_loop())
        
        await self.emit(MessageEnvelope(
            type="AGENT_STARTED",
            payload={"session_id": self._state.session_id, "text": "Agent has started successfully."},
            sender=self.descriptor.agent_id
        ))

    async def send(self, message: 'MessageEnvelope') -> None:
        """Asynchronous mailbox delivery. Invariant 3: Messages enter only through mailbox."""
        if self._state.status in (AgentStatus.TERMINATING.value, AgentStatus.TERMINATED.value):
            raise RuntimeError("Cannot send message to a terminating/terminated agent.")
            
        await self.mailbox.put(message)

    async def emit(self, event: 'MessageEnvelope') -> None:
        """Pushes output to runtime bus. Invariant 4: Outputs leave only through emit."""
        if self._emit_callback:
            res = self._emit_callback(event)
            if res is not None and asyncio.iscoroutine(res):
                await res

    async def shutdown(self) -> None:
        """Graceful termination."""
        self._state.status = AgentStatus.TERMINATING.value
        self._shutdown_event.set()
        
        # Allow child classes to clean up resources
        await self._on_shutdown()
        
        if self._task:
            await self._task
            
        self._state.status = AgentStatus.TERMINATED.value
        await self.emit(MessageEnvelope(
            type="AGENT_TERMINATED",
            payload={   "text": "Agent has terminated successfully."},
            sender=self.descriptor.agent_id
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
                self._state.status = AgentStatus.WAITING.value

                # set last_task_outcome to None before getting a new message. 
                while not self._state.outcome_acknowledged:
                    await asyncio.sleep(0.3)  # Wait for acknowledgment before processing next message

                # 0.5s timeout to check mailbox periodically. If no messages, loop continues.
                message = await asyncio.wait_for(self.mailbox.get(), timeout=MAILBOX_POLL_INTERVAL)
                

                self._state.last_task_outcome = None  # Reset last task outcome at the start of each loop iteration

                try:
                    # Pre-condition Check: After a message is popped from the mailbox, call _check_preconditions.
                    precond_res = await self._check_preconditions(message)
                    if isinstance(precond_res, tuple):
                        pre_ok, pre_response = precond_res
                    else:
                        pre_ok = precond_res
                        pre_response = "Preconditions check failed" if not pre_ok else "Precondition check successful"
                    
                    # If it returns False, do not transition to PROCESSING.
                    # Instead, emit an event of type TASK_PRECONDITIONS_VIOLATED, mark the task as done, and return the agent to the WAITING loop.
                    if not pre_ok:
                        raise PreconditionsViolatedError(pre_response)
                    
                    # 2. PROCESSING
                    self._state.status = AgentStatus.PROCESSING.value
                    
                    # Capture the return value from the implementation
                    result = await self.process(message)
                    
                    # Post-condition Check: Inside the successful block of process(), right before emitting TASK_COMPLETED, invoke _check_postconditions.
                    postcond_res = await self._check_postconditions(message, result)
                    if isinstance(postcond_res, tuple):
                        post_ok, post_response = postcond_res
                    else:
                        post_ok = postcond_res
                        post_response = "Postconditions check failed" if not post_ok else "Postcondition check successful"
                    if not post_ok:
                        raise PostconditionsViolatedError(result=result,message=f"Postconditions check failed: {post_response}")
                    
                    # 3. AUTO-EMIT FINAL RESULT
                    # If process() returns data, we treat it as a successful task completion.
                    if result is not None:
                        self._state.last_task_outcome = "TASK_COMPLETED"
                        self._state.outcome_acknowledged = False
                        
                        if (isinstance(result, dict) and 
                            "content" in result and 
                            isinstance(result["content"], list) and 
                            len(result["content"]) > 0 and 
                            hasattr(result["content"][0], "text")):
                            text_output = result["content"][0].text
                        else:
                            text_output = "Task completed successfully."

                        await self.emit(MessageEnvelope(
                            type="TASK_COMPLETED",
                            payload={
                                "result": result,
                                "text": text_output
                            },
                            sender=self.descriptor.agent_id,
                            correlation_id=message.correlation_id,
                            message_id=message.message_id
                        ))
                        
                except PostconditionsViolatedError as e:
                    self._state.last_task_outcome = "TASK_POSTCONDITIONS_VIOLATED"
                    self._state.outcome_acknowledged = False
                    await self.emit(MessageEnvelope(
                        type="TASK_POSTCONDITIONS_VIOLATED",
                        payload={
                            "result": e.result,
                            "error": str(e),
                            "text": str(e)
                        },
                        sender=self.descriptor.agent_id,
                        message_id= message.message_id,
                        correlation_id= message.correlation_id
                    ))
                except PreconditionsViolatedError as e:
                    self._state.last_task_outcome = "TASK_PRECONDITIONS_VIOLATED"
                    self._state.outcome_acknowledged = False
                    await self.emit(MessageEnvelope(
                        type="TASK_PRECONDITIONS_VIOLATED",
                        payload={
                            "error": str(e),
                            "reason": str(e),
                            "text": str(e)
                        },
                        sender=self.descriptor.agent_id,
                        message_id= message.message_id,
                        correlation_id= message.correlation_id
                    ))

                except Exception as e:
                    self._state.last_task_outcome = "TASK_FAILED"
                    self._state.outcome_acknowledged = False
                    await self.emit(MessageEnvelope(
                        type="TASK_FAILED",
                        payload={
                            "error": str(e),
                            "text": str(e)
                        },
                        sender=self.descriptor.agent_id,
                        message_id= message.message_id,
                        correlation_id= message.correlation_id
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

    async def _check_start_preconditions(self) -> bool:
        """
        Asynchronous verification hook executed before the agent starts.
        By default, it should return True. Child classes can override this to check
        essential environment readiness or dependencies before starting.
        """
        return True, "Start precondition check successful"

    async def _check_preconditions(self, message: 'MessageEnvelope') -> tuple[bool,str]:
        """
        Asynchronous verification hook executed before a message is allowed to process.
        By default, it should return True. Child classes will override this to query
        database entries, check file-system matrices, or verify upstream dependencies.
        """
        return True, "Precondition check successful"

    async def _check_postconditions(self, message: 'MessageEnvelope', result: Any) -> tuple[bool,str]:
        """
        Asynchronous verification hook executed after process() completes successfully
        but before the final output state is committed or emitted.
        By default, it should return True.
        """
        return True, "Postcondition check successful"

    async def _on_shutdown(self) -> None:
        """Optional hook for child classes during shutdown."""
        pass

    # ---------------------------------------------------------
    # INSPECTION INTERFACES (URP Section 6)
    # ---------------------------------------------------------
    @property
    def state(self) -> Dict[str, Any]:
        """Returns a safe, read-only view of the agent's current state."""
        return {
            "agent_id": self.descriptor.agent_id,
            "status": self._state.status,
            "session_id": self._state.session_id,
            "mailbox_size": self.mailbox.qsize(),
            "last_task_outcome": self._state.last_task_outcome,
            "outcome_acknowledged": self._state.outcome_acknowledged
        }
    def acknowledge_outcome(self) -> None:
        """Allows external systems (e.g., AOSM) to acknowledge that they've processed the last task outcome."""
        self._state.outcome_acknowledged = True