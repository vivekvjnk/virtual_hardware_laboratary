import asyncio
import json
import logging
from typing import Optional, Callable, Dict, Any, Awaitable, List
from pydantic import BaseModel
import websockets
from ..models import (
    BaseEvent, EventType, EventSource,
    HumanInputPayload, StateTransitionPayload,
    EvaluationUpdatePayload, ArtifactUpdatedPayload,
    AuthorityRequiredPayload, ErrorPayload,
    IdentifyPayload, WorkspacePayload,
    VAPInitPayload, VAPStatusPayload
)

logger = logging.getLogger(__name__)

class VHLWebSocketClient:
    """
    WebSocket client for the VHL Runtime <-> Agent Framework protocol.
    Handles connection, identification, and event sending/receiving.
    """
    def __init__(
        self,
        url: str,
        role: str = "agent",  # "agent" or "ui"
        on_event_received: Optional[Callable[[BaseEvent], Awaitable[None]]] = None
    ):
        self.url = url
        self.role = role
        self.on_event_received = on_event_received
        self._ws = None
        self._is_running = False
        self._send_queue = asyncio.Queue()
        self._connect_task = None
        self._subscribers: List[Callable[[BaseEvent], Awaitable[None]]] = []
        if on_event_received:
            self._subscribers.append(on_event_received)

    async def start(self):
        """Starts the client and identification loop in a background task."""
        if self._is_running:
            return
        self._is_running = True
        self._connect_task = asyncio.create_task(self._run())
        logger.info(f"VHL WebSocket Client (role={self.role}) starting background loop...")

    async def stop(self):
        """Stops the client and closes the connection."""
        self._is_running = False
        if self._ws:
            await self._ws.close()
        if self._connect_task:
            self._connect_task.cancel()
            try:
                await self._connect_task
            except asyncio.CancelledError:
                pass
        logger.info("VHL WebSocket Client stopped.")

    async def _run(self):
        """Internal main loop for connecting and processing messages."""
        while self._is_running:
            try:
                async with websockets.connect(self.url) as ws:
                    self._ws = ws
                    logger.info(f"Connected to VHL Relay at {self.url}")
                    
                    # 1. Identify ourselves to the relay
                    await self._send_identify()
                    
                    # 2. Start message loops
                    receive_task = asyncio.create_task(self._receive_loop())
                    send_task = asyncio.create_task(self._send_loop())
                    
                    done, pending = await asyncio.wait(
                        [receive_task, send_task],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    for task in pending:
                        task.cancel()
                        
            except (websockets.ConnectionClosed, ConnectionRefusedError) as e:
                if self._is_running:
                    logger.warning(f"Connection lost or failed: {e}. Retrying in 5 seconds...")
                    self._ws = None
                    await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._is_running:
                    logger.error(f"Unexpected error in VHL WebSocket Client: {e}", exc_info=True)
                    self._ws = None
                    await asyncio.sleep(5)

    async def _send_identify(self):
        """Sends the INITIAL identify message to the relay."""
        identify_event = BaseEvent(
            type=EventType.IDENTIFY,
            source=EventSource.BACKEND if self.role == "agent" else EventSource.RUNTIME,
            payload={"role": self.role}
        )
        await self._ws.send(identify_event.model_dump_json(by_alias=True))
        logger.info(f"Sent IDENTIFY as {self.role}")

    async def _notify_subscribers(self, event: BaseEvent):
        """Notifies all registered subscribers of an event."""
        for subscriber in self._subscribers:
            try:
                await subscriber(event)
            except Exception as e:
                logger.error(f"Error in subscriber callback: {e}")

    async def _receive_loop(self):
        """Listens for messages from the WebSocket."""
        try:
            async for message in self._ws:
                try:
                    data = json.loads(message)
                    event = BaseEvent.model_validate(data)
                    logger.debug(f"Received event: {event.type}")
                    
                    # Notify all subscribers
                    await self._notify_subscribers(event)
                except Exception as e:
                    logger.error(f"Error parsing received event: {e}. Data: {message}")
        except websockets.ConnectionClosed:
            logger.info("Receive loop stopped due to connection close.")

    async def _send_loop(self):
        """Sends messages from the internal queue."""
        try:
            while True:
                event = await self._send_queue.get()
                try:
                    if self._ws and (self._ws.state == websockets.protocol.State.OPEN):
                        await self._ws.send(event.model_dump_json(by_alias=True))
                        logger.debug(f"Sent event: {event.type}")
                    else:
                        logger.warning(f"WS not open, dropping event: {event.type}")
                except Exception as e:
                    logger.error(f"Error sending event {event.type}: {e}")
                    raise e # Trigger reconnection
                finally:
                    self._send_queue.task_done()
        except asyncio.CancelledError:
            pass

    async def emit_event(self, event: BaseEvent):
        """
        Manually emit a fully formed event.
        Suitable for replaying or custom events.
        """
        await self._send_queue.put(event)
        # Also notify local subscribers
        await self._notify_subscribers(event)

    async def emit(self, event_type: EventType, payload: BaseModel, artifact_id: Optional[str] = None):
        """Creates and enqueues an event for delivery."""
        source = EventSource.BACKEND if self.role == "agent" else EventSource.RUNTIME
        event = BaseEvent(
            type=event_type,
            source=source,
            artifact_id=artifact_id,
            payload=payload.model_dump(by_alias=True)
        )
        await self._send_queue.put(event)
        # Also notify local subscribers
        await self._notify_subscribers(event)
        return event

    def add_subscriber(self, callback: Callable[[BaseEvent], Awaitable[None]]):
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def remove_subscriber(self, callback: Callable[[BaseEvent], Awaitable[None]]):
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    async def wait_for_event(
        self, 
        event_type: EventType, 
        filter_func: Optional[Callable[[BaseEvent], bool]] = None, 
        timeout: float = 300.0
    ) -> BaseEvent:
        """Utility to wait for a specific event to occur."""
        queue = asyncio.Queue()
        
        async def subscriber(event: BaseEvent):
            if event.type == event_type:
                if filter_func is None or filter_func(event):
                    await queue.put(event)
        
        self.add_subscriber(subscriber)
        try:
            return await asyncio.wait_for(queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.error(f"Timed out waiting for event {event_type}")
            raise
        finally:
            self.remove_subscriber(subscriber)

    # --- Helper methods for Backend -> Runtime events ---

    async def emit_state_transition(self, from_state: str, to_state: str, reason: str):
        payload = StateTransitionPayload(from_state=from_state, to_state=to_state, reason=reason)
        await self.emit(EventType.STATE_TRANSITION, payload)

    async def emit_evaluation_update(self, task_id: str, decision: str ):
        payload = EvaluationUpdatePayload(task_id=task_id, decision=decision)
        await self.emit(EventType.VAP_DECISION, payload)

    async def emit_artifact_updated(self, artifact_type: str, artifact_version: str, summary: str, artifact_id: str):
        payload = ArtifactUpdatedPayload(artifact_type=artifact_type, artifact_version=artifact_version, summary=summary)
        await self.emit(EventType.ARTIFACT_UPDATED, payload, artifact_id=artifact_id)

    async def emit_authority_required(self, question: str, options: List[str] = None, blocking: bool = True):
        payload = AuthorityRequiredPayload(question=question, options=options or [], blocking=blocking)
        await self.emit(EventType.AUTHORITY_REQUIRED, payload)

    async def emit_error(self, scope: str, severity: str, message: str):
        payload = ErrorPayload(scope=scope, severity=severity, message=message)
        await self.emit(EventType.ERROR, payload)

    async def emit_workspace_upload(self, message: str = "Requesting workspace upload"):
        payload = WorkspacePayload(message=message)
        await self.emit(EventType.WORKSPACE_UPLOAD, payload)

    async def emit_workspace_download(self, reference_id: str, storage_path: str, filename: str):
        payload = WorkspacePayload(reference_id=reference_id, storage_path=storage_path, filename=filename)
        await self.emit(EventType.WORKSPACE_DOWNLOAD, payload)

    # --- Helper methods for Runtime -> Backend events ---

    async def emit_human_input(self, content: str, intent: str = "freeform", context_refs: List[str] = None):
        payload = HumanInputPayload(content=content, intent=intent, context_refs=context_refs or [])
        await self.emit(EventType.HUMAN_INPUT, payload)

    # --- VAP Helpers ---

    async def emit_vap_init(self, circuit_name: str, blob_id: str):
        payload = VAPInitPayload(circuit_name=circuit_name, blob_id=blob_id)
        return await self.emit(EventType.VAP_INIT, payload)
