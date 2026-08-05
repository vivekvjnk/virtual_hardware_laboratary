import type { ArchitectureNode } from '../../types/architecture';

export const runtimeNodes: Record<string, ArchitectureNode> = {
  'runtime-vap': {
    id: 'runtime-vap',
    title: 'VAP (Validation/Agent/Prototyping)',
    shortDescription: 'Stateful circuit execution and evaluation engine.',
    purpose: 'Runs \'tsci eval\' on generated code, performs process isolation, and returns pass/fail validation logs to agents.',
    category: 'infrastructure',
    parentId: 'vhl-runtime',
    children: [],
    repositoryPath: 'vhl-runtime/src/vap',
    tags: ['Evaluation', 'Validation', 'Process Isolation'],
    metadata: {
      status: 'stable'
    }
  },
  'runtime-mcp': {
    id: 'runtime-mcp',
    title: 'MCP Infrastructure',
    shortDescription: 'Model Context Protocol servers exposing system tools.',
    purpose: 'Provides agents with capabilities like terminal execution, library resolution, and UI snapshotting through standardized MCP interfaces.',
    category: 'infrastructure',
    parentId: 'vhl-runtime',
    children: [],
    repositoryPath: 'vhl-runtime/src/mcp',
    tags: ['MCP', 'Agent Tools'],
    metadata: {
      status: 'stable'
    }
  },
  'runtime-ws-relay': {
    id: 'runtime-ws-relay',
    title: 'WebSocket Agent Proxy (VAP Relay)',
    shortDescription: 'Real-time message broker for backend-frontend-agent sync.',
    purpose: 'Routes messages between Python Orchestration, WebUI, and URP agents across process boundaries.',
    category: 'gate',
    parentId: 'vhl-runtime',
    children: [],
    repositoryPath: 'vhl-runtime/src/server',
    documentation: [
      {
        title: 'WebSocket Agent Proxy Relay',
        path: 'vhl-runtime/docs/websocket-agent-proxy.md',
        description: 'Detailed specification of the WebSocket relay mechanism.'
      }
    ],
    tags: ['WebSocket', 'Relay', 'Async Messaging'],
    metadata: {
      status: 'stable'
    }
  },
  'runtime-webui-api': {
    id: 'runtime-webui-api',
    title: 'WebUI Backend API',
    shortDescription: 'Express API server (Port 3022) for WebUI interaction.',
    purpose: 'Handles project management, module creation, circuit synchronization, and agent message history.',
    category: 'infrastructure',
    parentId: 'vhl-runtime',
    children: [],
    repositoryPath: 'vhl-runtime/src/workspace/vhlWebUI.ts',
    tags: ['REST API', 'Express'],
    metadata: {
      status: 'stable'
    }
  },
  'runtime-workspace': {
    id: 'runtime-workspace',
    title: 'Runtime Workspace Controller',
    shortDescription: 'High-level project state and filesystem manager.',
    purpose: 'Integrates VAP, WebSocket relay, and SQLite state management to maintain a synchronized single source of truth.',
    category: 'storage',
    parentId: 'vhl-runtime',
    children: [],
    repositoryPath: 'vhl-runtime/src/workspace',
    tags: ['Workspace', 'Project State'],
    metadata: {
      status: 'stable'
    }
  }
};
