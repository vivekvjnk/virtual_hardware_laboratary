# URP & Pi Agent Harness Integration Analysis

## Executive Summary

The Virtual Hardware Laboratory (VHL) backend is built on top of the **Unified Runtime Primitive (URP)** architecture. Currently, concrete URP agents (`ana`, `archy`, `librarian`) use **`openhands-agent-sdk`** as their execution harness.

Our audit reveals that **`vhl_common/urp/abstract_urp.py` (the URP lifecycle core) has ZERO direct dependencies on OpenHands**. URP itself is clean, stateful, and transport/harness-agnostic. However, **concrete agents, LLM factory utilities, and snapshot-replay test suites are heavily coupled to `openhands.sdk`**.

To replace or complement OpenHands with the **`pi` agent harness**, we need to construct a **`PiRpcClient` bridge and a `PiURPAgent` base class**. Because `pi` runs as a high-performance Node.js process exposing an RPC interface via stdio JSONL, this abstraction layer will bridge Python `asyncio` code with Pi's RPC stream.

---

## 1. Deep Dive: OpenHands SDK Coupling Assessment

### A. Summary of Coupling Levels

| Subsystem / Module | Coupling Level | Description & Key OpenHands Classes Used |
| :--- | :--- | :--- |
| **`vhl_common/urp/abstract_urp.py`** | **0% (None)** | Pure abstract lifecycle contract (`initialize`, `process`, `_check_preconditions`, `_check_postconditions`). No OpenHands imports. |
| **`vhl_common/urp/agent_registry.py`** | **0% (None)** | Factory registry for instantiating agents. Harness-agnostic. |
| **Concrete URP Agents**<br>(`urp_ana.py`, `urp_archy.py`, `urp_librarian.py`) | **85% (High)** | Instantiates and drives `openhands.sdk.Agent`, `Conversation`, `Message`, `TextContent`, `PipelineCondenser`, `FileEditorTool`, `TerminalTool`. |
| **LLM Management**<br>(`vhl_common/llm/llm_utils.py`) | **75% (High)** | Factory `get_llm_for_agent()` returns an `openhands.sdk.LLM` configured with LiteLLM. |
| **Testing & Snapshot Replay**<br>(`vhl_common/llm/replay_llm.py`, `snapshot.py`) | **90% (High)** | `ReplayLLM` inherits from `openhands.sdk.testing.TestLLM` and uses `SnapshotLoader` to parse OpenHands `.eventlog` directories. |
| **MCP Integration**<br>(`vhl_protocol/utils/mcp_utils.py`) | **50% (Medium)** | Uses `openhands.sdk.mcp.MCPClient` to invoke fastmcp tools. |

---

### B. Detailed Code-Level Coupling Points

1. **Conversation Execution Loop:**
   In concrete agents (`urp_ana.py`, etc.), task execution is tied to OpenHands synchronous conversation execution:
   ```python
   self.conversation.send_message(Message(role="user", content=[TextContent(text=user_message)]))
   await asyncio.to_thread(self.conversation.run)
   ```
   Status tracking relies on `self.conversation.state.execution_status` (`ConversationExecutionStatus.FINISHED`, `PAUSED`, `STUCK`, `ERROR`).

2. **Context Window & Compaction:**
   Agents explicitly configure OpenHands condensers:
   ```python
   surgical_condenser = LargeFileSurgicalCondenser(...)
   pipeline = PipelineCondenser(condensers=[LLMSummarizingCondenser(llm=...)])
   ```

3. **Tool Definition:**
   Agents define capabilities using OpenHands tool wrappers:
   ```python
   tools = [Tool(name=FileEditorTool.name), Tool(name=TerminalTool.name)]
   ```

4. **Event & Message Formats:**
   Conversation callbacks inspect `openhands.sdk.event.LLMConvertibleEvent` and `Message`.

5. **LLM Factory & Snapshot Replay:**
   - `get_llm_for_agent()` constructs `openhands.sdk.LLM(model=..., base_url=..., api_key=...)`.
   - `ReplayLLM` extends `openhands.sdk.testing.TestLLM`, feeding scripted OpenHands messages parsed from snapshot event logs (`.eventlog.lock` / `.eventlog`).

---

## 2. OpenHands SDK vs. Pi Agent Harness: Key Mappings & Differences

| Feature / Domain | OpenHands SDK (Current) | Pi Agent Harness (Target) |
| :--- | :--- | :--- |
| **Runtime Process** | In-process Python library (`openhands.sdk`) | Subprocess / RPC Daemon (`pi --mode rpc`) communicating via JSONL stdio |
| **Agent State & Persistence** | OpenHands `.conversation` event logs | Pi session files (`.pi/agent/sessions/`) / SQLite / headless session management |
| **Execution Command** | `conversation.run()` | Send `{"type": "prompt", "message": "..."}` over stdin and stream stdout events |
| **Execution Outcomes** | `ConversationExecutionStatus` (`FINISHED`, `PAUSED`, `STUCK`, `ERROR`) | Streamed RPC events (`agent_end`, `error`, `paused` / user input request) |
| **Context Compaction** | `PipelineCondenser` (`LLMSummarizingCondenser`) | Native Pi Auto-Compaction & `/compact` RPC command |
| **System Prompts** | OpenHands Jinja2 renderer (`system_prompt_filename`, `system_prompt_kwargs`) | Pi system prompt options / prompt templates / instructions |
| **Tool Execution** | `FileEditorTool`, `TerminalTool` in Python | Pi native built-in tools (`read`, `write`, `edit`, `bash`) + Extension tools + MCP servers |
| **MCP Integration** | OpenHands `MCPClient` wrapper | Pi native MCP server support via extension / config |

---

## 3. Recommended Abstraction Architecture for Pi under URP

Because `AbstractURPAgent` is already clean, we can create a **Harness Abstraction Layer** without breaking existing Supervisor or Controller code.

### Proposed Architecture Diagram

```
+---------------------------------------------------------------------------------+
|                               Supervisor / Controller                           |
+---------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------+
|                           AbstractURPAgent (URP Core)                           |
+---------------------------------------------------------------------------------+
                                           |
                  +------------------------+------------------------+
                  |                                                 |
                  v                                                 v
+-----------------------------------+             +-----------------------------------+
|       OpenHandsURPAgent           |             |           PiURPAgent              |
|   (Existing Python In-Process)    |             |       (New Pi Harness Base)       |
+-----------------------------------+             +-----------------------------------+
| - openhands.sdk.Agent             |             | - PiRpcClient (async subprocess)  |
| - openhands.sdk.Conversation      |             | - JSONL stdio transport           |
| - OpenHands Condensers            |             | - Pi Native Compaction & Tools    |
+-----------------------------------+             +-----------------------------------+
```

---

## 4. Key Implementation Components for `PiURPAgent`

### A. Python Async `PiRpcClient` Bridge
A dedicated Python class (`vhl_common/pi_harness/pi_rpc_client.py`) that manages the lifecycle of the Node.js `pi --mode rpc` process via `asyncio.create_subprocess_exec`.

**Key Responsibilities:**
- **Spawn & Lifecycle**: Launch `pi --mode rpc --session-dir <module_workspace>` with desired model/provider options.
- **JSONL Streaming**: Send JSON commands (`prompt`, `steer`, `set_model`, `abort`) to `stdin` and parse lines from `stdout`.
- **Event Handling**: Dispatch streamed events (`text_delta`, `tool_use`, `tool_result`, `agent_end`, `error`) to URP loggers and callbacks.
- **Outcome Mapping**:
  * `agent_end` with no pending input $\rightarrow$ `LastTaskOutcome.TASK_COMPLETED`
  * Request for user input / steering $\rightarrow$ `LastTaskOutcome.WAITING_FOR_USER_INPUT`
  * Subprocess error / timeout / stuck $\rightarrow$ `LastTaskOutcome.TASK_FAILED`

---

### B. `PiURPAgent` Subclassing `AbstractURPAgent`

Create a base class or direct concrete implementations (`PiAnaURPAgent`, `PiArchyURPAgent`, `PiLibrarianURPAgent`) that inherit from `AbstractURPAgent`.

```python
class PiURPAgent(AbstractURPAgent):
    """Base URP Agent backed by Pi Agent Harness via RPC."""
    
    def _on_initialize(self, context: Any) -> None:
        self.workspace_path = context.workspace.get_module_workspace(self.module_name)
        
        # Initialize Pi RPC client targeting the module workspace
        self.pi_client = PiRpcClient(
            workspace_dir=str(self.workspace_path),
            model=os.getenv("LLM_MODEL", "anthropic/claude-3-7-sonnet"),
            system_prompt=self._get_rendered_system_prompt(context),
        )

    async def process(self, message: MessageEnvelope) -> ProcessResult:
        user_text = message.payload["text"]
        
        # Send prompt over JSONL RPC stream
        response_event = await self.pi_client.send_prompt(user_text)
        
        outcome = self._map_pi_event_to_outcome(response_event)
        return ProcessResult(
            outcome=outcome,
            payload=ProcessResultPayload(text=response_event.get("text", ""))
        )
```

---

### C. Context Compaction & System Prompt Strategy

1. **System Prompts**: Pi allows setting system prompts or standard instructions via configuration or initial session settings. We can render existing Jinja2 templates (`ana_prompt.j2`, `archy_prompt.j2`) in Python and pass the result to `PiRpcClient`.
2. **Context Window Management**: Instead of configuring OpenHands Python condensers (`LLMSummarizingCondenser`), delegate compaction directly to Pi's built-in **Auto-Compaction** (`reserveTokens` threshold) or trigger `/compact` explicitly via RPC when needed.

---

### D. Testing & Replay Strategy for Pi

To maintain deterministic E2E testing without calling external LLM APIs:
- **`PiReplayRpcClient`**: Replace the live `pi` subprocess with a mock RPC server that reads recorded JSONL event logs from previous test runs and streams them back line-by-line over `stdout`.
- **Path Substitution**: Apply dynamic path replacement on recorded tool call arguments (matching the pattern used by `ReplayLLM`).

---

## 5. Phased Integration Roadmap

| Phase | Task | Target Deliverables |
| :--- | :--- | :--- |
| **Phase 1** | **`PiRpcClient` Protocol Bridge** | Python async wrapper managing `pi --mode rpc` stdio JSONL communication, command formatting, and event parsing. |
| **Phase 2** | **`PiURPAgent` Base Implementation** | Refactor/extend agent base layer so URP agents can run on top of `PiRpcClient`. |
| **Phase 3** | **Concrete Agent Adaptation** | Adapt `archy`, `librarian`, and `ana` to run using Pi harness options (tools, system prompts, worktree path). |
| **Phase 4** | **Replay & Testing Integration** | Build `PiReplayRpcClient` to support snapshot replay testing with path substitution. |
| **Phase 5** | **E2E Validation & Benchmarking** | Validate full pipeline (`Archy` $\rightarrow$ `Librarian` $\rightarrow$ `ANA`) under `Workflow1Controller` with `pi` harness. |
