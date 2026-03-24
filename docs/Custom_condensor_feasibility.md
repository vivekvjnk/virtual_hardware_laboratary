# Feasibility Study: Selective Condensation for FileEditorTool Outputs

## Overview
This document analyzes the feasibility of implementing a selective masking mechanism for `FileEditorTool` outputs (specifically images and large text files) within the `agent-sdk` to prevent context bloat.

## 1. Existing Condensation Logic

### 1.1 Trigger Points
The primary trigger logic for automatic condensation is implemented in `openhands.sdk.context.condenser.llm_summarizing_condenser.LLMSummarizingCondenser.get_condensation_reasons`.

```python
# openhands-sdk/openhands/sdk/context/condenser/llm_summarizing_condenser.py:111-112
if len(view) > self.max_size:
    reasons.add(Reason.EVENTS)
```

The `max_size` attribute (defaulting to 240 events) serves as the "automatic condensation trigger logic" mentioned in the requirements.

### 1.2 Calling Mechanism
The `Agent.step` method triggers condensation indirectly via `prepare_llm_messages`:

1.  **Step Execution**: `Agent.step` (in `agent.py`) is called for each iteration.
2.  **Message Preparation**: It calls `prepare_llm_messages(state.events, condenser=self.condenser, llm=self.llm)`.
3.  **Condensation Call**: `prepare_llm_messages` calls `condenser.condense(view, agent_llm=llm)`.
4.  **Requirement Check**: `RollingCondenser.condense` calls `condensation_requirement()`, which in `LLMSummarizingCondenser` checks the event count and token limits.

## 2. FileEditorTool Observation Structure

The `FileEditorTool` returns a `FileEditorObservation`, which encapsulates its output in a `content` field:

- **Type**: `list[TextContent | ImageContent]`
- **Images**: When viewing an image, the tool returns `ImageContent` containing a base64-encoded data URL.
- **Large Files**: Text files are currently truncated by `MAX_RESPONSE_LEN_CHAR` (16,000 characters by default), which still adds significant token overhead.

## 3. Proposed Selective Masking Design

### 3.1 New Condenser Component
A new `SelectiveMaskingCondenser` should be implemented, inheriting from `CondenserBase`.

```python
class SelectiveMaskingCondenser(CondenserBase):
    def condense(self, view: View, agent_llm: LLM | None = None) -> View:
        modified_events = []
        for event in view.events:
            if self._should_mask(event):
                modified_events.append(self._mask_event(event))
            else:
                modified_events.append(event)
        return view.model_copy(update={"events": modified_events})
```

### 3.2 Masking Logic
- **Identification**: Target `ObservationEvent` where `tool_name == "file_editor"`.
- **Threshold**: Check if any `ImageContent` is present or if `TextContent` exceeds 1KB (1024 bytes).
- **Transformation**: Replace the content with a descriptive string: `read/viewed <file_name>`. The `path` attribute is already available in `FileEditorObservation`.

### 3.3 Integration via Pipeline
The `PipelineCondenser` class can be used to chain the `SelectiveMaskingCondenser` with the existing `LLMSummarizingCondenser`.

```python
condenser = PipelineCondenser(condensers=[
    SelectiveMaskingCondenser(threshold_kb=1.0),
    LLMSummarizingCondenser(llm=condenser_llm, max_size=240)
])
```

## 4. Feasibility Analysis

### 4.1 Technical Feasibility
**Rating: High**
- The architecture already supports returning a modified `View` from a condenser without triggering a full history-collapsing `Condensation` event.
- `prepare_llm_messages` handles the `View` return type by using the updated event list for message conversion.

### 4.2 Performance Overhead
**Rating: Minimal**
- **Computation**: Linear scan of the `View` events (max ~240).
- **Memory**: O(N) where N is the number of events. Since we are replacing large content with small strings, this actually *reduces* memory pressure in the agent loop.
- **Token Counting**: Calculating the byte size of strings is extremely cheap. Full tokenization via the LLM (for precise token-based masking) would add more overhead but is likely unnecessary given the 1KB requirement.

### 4.3 Risks and Considerations
- **Loss of Information**: Once masked, the LLM cannot "see" the image content in subsequent turns unless it calls the tool again. This is acceptable as the primary goal is to avoid context bloat.
- **Tool Differentiation**: Logic must carefully distinguish between `view` command (which can be safely masked) and other commands like `str_replace` or `insert` where the content might be critical for the agent's logic (though these usually return diffs, not full files).

## 5. Conclusion
Implementing a selective masking condenser is highly feasible and aligns perfectly with the current `agent-sdk` architecture. It provides a robust solution to context pollution caused by large file tool outputs while maintaining the flexibility of the existing condensation system.
