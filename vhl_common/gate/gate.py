from typing import Callable, Dict, List, Awaitable
import logging

from vhl_common.urp.data_types import MessageEnvelope

logger = logging.getLogger(__name__)

class Gate:
    """
    Global Asynchronous Transport Engine (GATE)
    A stateless transport layer that routes messages based on callables.
    It does not interpret payloads, maintain thread state, or block execution.
    """
    def __init__(self, context_id: str):
        self.context_id = context_id
        # Capability-based routing: stores delivery endpoints (callables)
        self.routes: Dict[str, Callable[[MessageEnvelope], Awaitable[None]]] = {}
        # Observability: Global log of all messages
        self.global_log: List[MessageEnvelope] = []

    def register(self, name: str, enqueue_fn: Callable[[MessageEnvelope], Awaitable[None]]) -> None:
        """
        Registers an endpoint (e.g., an agent's send() method or an HIL adapter)
        to receive messages under the given name.
        """
        if name in self.routes:
            logger.warning(f"Overwriting existing GATE route for '{name}' in context '{self.context_id}'")
        self.routes[name] = enqueue_fn
    def unregister(self, name: str) -> None:
        """
        Unregisters a previously registered endpoint.
        """
        if name in self.routes:
            del self.routes[name]
            
    async def send(self, message: MessageEnvelope) -> None:
        """
        The only message ingress point. Appends to the global log and
        routes the message to its destination's registered callable.
        Exceptions are bubbled up to the sender to maintain GATE's dumb transport invariant.
        """
        self.global_log.append(message)
        
        destination = message.receiver
        if destination not in self.routes:
            raise ValueError(f"No route registered for destination: {destination}")
            
        # GATE does not handle exceptions; bubbles up to sender
        await self.routes[destination](message)


class GateRegistry:
    """
    Registry-Factory model for context-bound Gate instances.
    Ensures that GATE is logically singleton per context but instantiated per context.
    """
    _gates: Dict[str, Gate] = {}

    @classmethod
    def get(cls, context_id: str) -> Gate:
        """
        Retrieves the Gate for a given context, creating it lazily if it does not exist.
        """
        if context_id not in cls._gates:
            cls._gates[context_id] = Gate(context_id)
        return cls._gates[context_id]
        
    @classmethod
    def cleanup(cls, context_id: str) -> None:
        """
        Explicitly removes the Gate instance for the given context.
        Should be called after a workflow is completed.
        """
        if context_id in cls._gates:
            del cls._gates[context_id]

    @classmethod
    def clear_all(cls) -> None:
        """
        Removes all Gate instances. Useful for testing.
        """
        cls._gates.clear()
