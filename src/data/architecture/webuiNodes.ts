import type { ArchitectureNode } from '../../types/architecture';

export const webuiNodes: Record<string, ArchitectureNode> = {
  'ui-layouts': {
    id: 'ui-layouts',
    title: 'Layout & Navigation',
    shortDescription: 'Structural UI components for system-wide navigation.',
    purpose: 'Manages the sidebar, mission feed, and top-level navigation between different design views.',
    category: 'feature',
    parentId: 'vhl-webui',
    children: [],
    repositoryPath: 'vhl-webui/src/components',
    tags: ['UI', 'Layout'],
    metadata: {
      status: 'stable'
    }
  },
  'ui-features': {
    id: 'ui-features',
    title: 'Core Design Features',
    shortDescription: 'Interactive tools for circuit editing and agent communication.',
    purpose: 'Composes the Code Editor, Circuit Canvas, and Agent Chat into a unified design environment.',
    category: 'feature',
    parentId: 'vhl-webui',
    children: [],
    repositoryPath: 'vhl-webui/src/components',
    tags: ['UI', 'Features'],
    metadata: {
      status: 'stable'
    }
  },
  'ui-api': {
    id: 'ui-api',
    title: 'Frontend API Client',
    shortDescription: 'Communication layer with the VHL Runtime backend.',
    purpose: 'Handles asynchronous requests to the runtime API server for project state, file operations, and agent messaging.',
    category: 'protocol',
    parentId: 'vhl-webui',
    children: [],
    repositoryPath: 'vhl-webui/src/api',
    tags: ['API', 'Fetch', 'RPC'],
    metadata: {
      status: 'stable'
    }
  }
};
