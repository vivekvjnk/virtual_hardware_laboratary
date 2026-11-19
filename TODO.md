1. AGENTS.md is outdated.
2. Merge "src/workspace/vhlWorkspaceManager.ts" and "src/workspace/workspaceManager.ts"
3. vhl_backend/src/workspace/vhlWebUI.ts:
  - getProjectModules : so many fallback paths. No need for them. Simply implement one right approach.
  - setupGatewayServer: No need for websocket gateway anymore. We should remove this
  - captureSnapshots: Do we use this API anywhere? if not remove this. We will implement screenshot feature later, when required.
  - generateManifest: 
    - Earlier, when we had `vhl-runtime` and `vhl-agent-backend`, we had manifest files to synchronize between these two modules. Do we still need to maintain this? I don't think, this interface is required any longer. We should remove it if there are no dependencies.
  - getFileHash: This function is used inside generateManifest. If there are no other dependencies, when we remove generateManifest, we should also remove getFileHash. 
  - getCircuitJson: Revisit implementation of this function. Make sure it aligns well with new user workspace assumptions
  - getProjectModules: Remove all redundant sqlite db path checks. There should be only one authoritative location for state.db
  - isValidVhlProject: Entire logic is flawed; This function should validate if the Project directory aligns with the VHL user project assumptions; For which we should first design the ground rules for the VHL user project; 
4. vhl_backend/src/workspace/projectContext.ts: 
  - ProjectState
    - Remove circuit_name, backend_status, runtime_status
    - Create an object incorporating synthesis status
      - is_synthesizable
      - is_synthesis_completed

5. vhl_backend/src/workspace/fileOperations.ts: Outdated file; Remove it 
