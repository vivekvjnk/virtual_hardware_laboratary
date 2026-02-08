import asyncio
import logging
import json
from typing import Optional, Dict, Any, List
from state_machine.states import AOSMState
from vhl_protocol.client.client import VHLWebSocketClient
from vhl_protocol.models import BaseEvent, EventType, EventSource

logger = logging.getLogger(__name__)

class AOSM:
    """
    Agentic Orchestration State Machine (AOSM)
    Always-on, time-aware control layer for VHL.
    """
    def __init__(self, ws_url: str = "ws://localhost:1080"):
        self.state = AOSMState.IDLE
        self.ws_client = VHLWebSocketClient(
            url=ws_url,
            role="agent",
            on_event_received=self._handle_ws_event
        )
        self.current_message: Dict[str, Any] = {
            "state_id": self.state,
            "observations": []
        }
        self.event_queue = asyncio.Queue()

    async def start(self):
        """Starts AOSM and the WebSocket client."""
        logger.info("Starting AOSM...")
        await self.ws_client.start()
        asyncio.create_task(self._main_loop())

    async def stop(self):
        """Stops AOSM and the WebSocket client."""
        logger.info("Stopping AOSM...")
        await self.ws_client.stop()

    async def _handle_ws_event(self, event: BaseEvent):
        """Callback for received WebSocket events."""
        logger.debug(f"AOSM received event: {event.type}")
        await self.event_queue.put(event)

    async def _main_loop(self):
        """Main loop that processes events and drives transitions."""
        while True:
            event = await self.event_queue.get()
            try:
                await self.process_event(event)
            except Exception as e:
                logger.error(f"Error processing event: {e}", exc_info=True)
            finally:
                self.event_queue.task_done()

    async def process_event(self, event: BaseEvent):
        """
        Processes a single event and triggers state transitions.
        """
        logger.info(f"Processing event: {event.type} in state: {self.state}")
        
        # Dispatch to handler based on current state and event
        handler_name = f"_handle_{self.state.name.lower()}"
        handler = getattr(self, handler_name, None)
        
        if handler:
            await handler(event)
        else:
            logger.warning(f"No handler defined for state {self.state}")

    async def transition_to(self, next_state: AOSMState, reason: str = ""):
        """Transitions to a new state and emits a state transition event."""
        from_state = self.state
        self.state = next_state
        logger.info(f"Transitioning: {from_state.name} -> {next_state.name} (Reason: {reason})")
        
        # Notify the UI/Protocol layer
        await self.ws_client.emit_state_transition(
            from_state=from_state.name,
            to_state=next_state.name,
            reason=reason
        )

    # --- State Handlers ---

    async def _handle_idle(self, event: BaseEvent):
        if event.type == EventType.REFERENCE_UPLOADED:
            await self.transition_to(AOSMState.BOOTSTRAP_PIPELINE, "New schematic uploaded")
            await self._run_bootstrap()
        elif event.type == EventType.HUMAN_INPUT:
            await self.transition_to(AOSMState.INTENT_CLASSIFY, "User message received")

    async def _handle_bootstrap_pipeline(self, event: BaseEvent):
        # Pipeline execution is asynchronous; we might receive internal signals or just wait
        pass

    async def _handle_wait_for_ana(self, event: BaseEvent):
        if event.type == EventType.EVALUATION_UPDATE:
            status = event.payload.get("status")
            if status in ["pass", "fail"]:
                await self.transition_to(AOSMState.PRESENT_RESULT, f"ANA finished with status: {status}")
        elif event.type == EventType.INTERRUPT_REQUEST:
            await self.transition_to(AOSMState.CANCEL_PIPELINE, "User interrupted execution")
        elif event.type == EventType.ERROR:
            await self.transition_to(AOSMState.ERROR_PRESENTED, f"System error: {event.payload.get('message')}")

    async def _handle_present_result(self, event: BaseEvent):
        if event.type == EventType.HUMAN_INPUT:
            await self.transition_to(AOSMState.INTENT_CLASSIFY, "User modification requested")
        elif event.type == EventType.REFERENCE_UPLOADED:
            await self.transition_to(AOSMState.BOOTSTRAP_PIPELINE, "New upload during review")

    async def _handle_intent_classify(self, event: BaseEvent):
        # In a real scenario, an agent would classify the intent here.
        # For the wireframe, we assume valid modification request.
        logger.info("[AOSM] Classifying intent...")
        # Transition to PREPARE_ANA_RUN or WAIT_FOR_USER if ambiguous
        await self.transition_to(AOSMState.PREPARE_ANA_RUN, "Intent classified as modification")

    async def _handle_prepare_ana_run(self, event: BaseEvent):
        logger.info("[AOSM] Preparing ANA run...")
        # TODO 
        # 1. Send message to workspace client to prepare and upload workspace
        # 2. Wait for confirmation that workspace zip is uploaded to object storage and get reference
        # 3. Download the workspace zip, extract it and prepare ANA workspace directory
        # 4. Transition to TRIGGER_ANA once workspace is ready
        
        # Translate message to structured observation
        await self.transition_to(AOSMState.TRIGGER_ANA, "ANA run prepared")

    async def _handle_trigger_ana(self, event: BaseEvent):
        logger.info("[AOSM] Triggering ANA-D...")
        # Start ANA-D process
        await self.transition_to(AOSMState.WAIT_FOR_ANA, "ANA-D started")

    async def _handle_cancel_pipeline(self, event: BaseEvent):
        logger.info("[AOSM] Cleaning up cancelled pipeline...")
        await self.transition_to(AOSMState.IDLE, "Cleanup complete")

    async def _handle_error_presented(self, event: BaseEvent):
        if event.type == EventType.HUMAN_INPUT:
            content = event.payload.get("content", "").lower()
            if "retry" in content:
                # Retry strategy would depend on previous state
                await self.transition_to(AOSMState.IDLE, "Retrying from IDLE")
            elif "abort" in content:
                await self.transition_to(AOSMState.IDLE, "User aborted after error")

    async def _handle_wait_for_user(self, event: BaseEvent):
        if event.type == EventType.HUMAN_INPUT:
             await self.transition_to(AOSMState.INTENT_CLASSIFY, "Clarification received")

    # --- High-level Orchestration Logic ---

    async def _run_bootstrap(self):
        """Logic for BOOTSTRAP_PIPELINE."""
        logger.info("Executing Bootstrap Pipeline...")
        # 1. Trigger Archy
        # 2. Trigger Librarian
        # 3. Trigger ANA-D
        await self.transition_to(AOSMState.WAIT_FOR_ANA, "Pipeline started")

def main():
    # Test stub
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    aosm = AOSM()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(aosm.start())
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Interrupt received, stopping AOSM...")
        loop.run_until_complete(aosm.stop())
    finally:
        loop.close()

if __name__ == "__main__":
    main()
