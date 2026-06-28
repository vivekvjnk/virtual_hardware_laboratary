## E2E Testing with Snapshot Replay

The VHL system supports deterministic E2E testing using a snapshot-replay mechanism. This allows running tests against recorded LLM interactions, ensuring stability and reducing costs during regression testing.

### Architecture

- **vhl_common.llm.ReplayLLM**: A specialized LLM class that replays recorded responses from a conversation snapshot. It supports path substitution to handle dynamic workspace paths across different test runs.
- **vhl_common.llm.get_llm_for_agent**: A factory function that returns either a `ReplayLLM` (if `VHL_E2E_REPLAY_DIR` is set) or a standard `LLM`.
- **Snapshots**: Located in `.conversation` directories within module folders (e.g., `bms-monitor-module/.conversation`).

### How to use Replay in Tests

1. Set `VHL_E2E_REPLAY_DIR` to the base directory containing your snapshots.
2. Ensure agents are initialized through the URP `initialize()` method, which calls `get_llm_for_agent()`.
3. In tests, you can also manually instantiate `ReplayLLM` using `ReplayLLM.from_persistence(path, current_workspace=...)` to enable path substitution.

### Path Substitution

`ReplayLLM` automatically detects the original workspace path from the snapshot and replaces it with the `current_workspace` path provided during initialization. This is crucial for tools like `FileEditorTool` which expect absolute paths.