import type { ArchitectureNode } from '../../types/architecture';

export const systemNodes: Record<string, ArchitectureNode> = {
  'vhl-system': {
    id: 'vhl-system',
    title: 'VHL System',
    shortDescription: 'Integrated multi-agent electronic circuit design platform.',
    purpose: 'Coordinates frontend visualization, agent orchestration, and deterministic runtime execution to transform design intent into verified tscircuit code.',
    category: 'root',
    parentId: null,
    children: ['vhl-webui', 'vhl-agent-backend', 'vhl-runtime', 'user-project-model'],
    metadata: {
      status: 'stable'
    }
  },
  'vhl-webui': {
    id: 'vhl-webui',
    title: 'VHL WebUI',
    shortDescription: 'React-based frontend interface for circuit design and agent interaction.',
    purpose: 'Provides a visual workspace for engineers to define requirements, interact with agents, and inspect circuit layouts (Schematic/PCB/3D).',
    category: 'subsystem',
    parentId: 'vhl-system',
    children: ['ui-layouts', 'ui-features', 'ui-api'],
    repositoryPath: 'vhl-webui',
    tags: ['Frontend', 'React', 'Vite', 'TypeScript'],
    metadata: {
      techStack: ['React', 'Tailwind CSS', 'Radix UI', 'tscircuit'],
      status: 'stable'
    }
  },
  'vhl-agent-backend': {
    id: 'vhl-agent-backend',
    title: 'VHL Agent Backend',
    shortDescription: 'State-aware multi-agent orchestration layer ("The Brain") for electronic circuit design.',
    purpose: 'Orchestrates design perception, component resolution, code synthesis, evaluation, and project state persistence across specialized AI agents.',
    category: 'subsystem',
    parentId: 'vhl-system',
    children: ['urp-agent-layer', 'protocol-layer', 'workspace-subsystem', 'aosm'],
    repositoryPath: 'vhl-agent-backend',
    documentation: [
      {
        title: 'System AGENTS Overview',
        path: 'AGENTS.md',
        description: 'High-level platform guide and agent knowledge base.'
      },
      {
        title: 'Detailed Backend Architecture',
        path: 'vhl-agent-backend/docs/source/ARCHITECTURE.md',
        description: 'Deep dive into multi-agent orchestration and workflows.'
      },
      {
        title: 'Backend AGENTS Guide',
        path: 'vhl-agent-backend/AGENTS.md',
        description: 'Backend specific architecture details.'
      },
      {
        title: 'Architecture Blueprint',
        path: 'docs/architecture/architecture_diagram.md',
        description: 'Structural component breakdown.'
      }
    ],
    tags: ['Root', 'Orchestration', 'Multi-Agent', 'Python'],
    metadata: {
      techStack: ['Python 3.11', 'Asyncio', 'Pydantic', 'SQLite', 'Git'],
      authoritativeHost: 'Agent Backend Process',
      status: 'stable'
    }
  },
  'vhl-runtime': {
    id: 'vhl-runtime',
    title: 'VHL Runtime',
    shortDescription: 'Node.js execution environment and infrastructure bridge.',
    purpose: 'Bridges agents to the physical environment, manages project files, executes circuit evaluations (VAP), and hosts MCP servers.',
    category: 'subsystem',
    parentId: 'vhl-system',
    children: ['runtime-vap', 'runtime-mcp', 'runtime-ws-relay', 'runtime-webui-api', 'runtime-workspace'],
    repositoryPath: 'vhl-runtime',
    tags: ['Runtime', 'Node.js', 'VAP', 'MCP', 'WebSocket'],
    metadata: {
      techStack: ['Node.js', 'Express', 'TypeScript', 'Docker', 'tsci'],
      status: 'stable'
    }
  }
};
