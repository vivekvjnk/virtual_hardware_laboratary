import type { ArchitectureNode } from '../../types/architecture';

export const userProjectNodes: Record<string, ArchitectureNode> = {
  'user-project-model': {
    id: 'user-project-model',
    title: 'VHL User Project Model',
    shortDescription: 'Architectural model of a VHL user project.',
    purpose: 'Defines the structure, core abstractions (Modules and Assemblies), and key design artifacts of an electronic circuit design project within the VHL system.',
    category: 'subsystem',
    parentId: 'vhl-system',
    children: ['project-root', 'module-abstraction', 'design-artifacts'],
    repositoryPath: 'sample-projects/bms-experiments-milestone-1/bms-project_e0505ca9',
    documentation: [
      {
        title: 'VHL User Project Model Guide',
        path: 'docs/vhl-user-project-model.md',
        description: 'Detailed description of modules, assemblies, and project structure.'
      }
    ],
    tags: ['Project Model', 'Modules', 'Assemblies', 'SCUD'],
    metadata: {
      status: 'stable'
    }
  },
  'project-root': {
    id: 'project-root',
    title: 'Project Root Abstraction',
    shortDescription: 'The central coordination point for a VHL project.',
    purpose: 'Hosts system-level specifications, assembly definitions, project-wide configurations (package.json, tscircuit.config.json), and the authoritative System Boundary.',
    category: 'feature',
    parentId: 'user-project-model',
    children: ['system-boundary-doc', 'assembly-abstraction'],
    tags: ['Root', 'System Specs', 'Coordination'],
    metadata: {
      status: 'stable'
    }
  },
  'system-boundary-doc': {
    id: 'system-boundary-doc',
    title: 'System Boundary Document (system-boundary.md)',
    shortDescription: 'The "master" specification for the entire project.',
    purpose: 'Acts as the authoritative registry of all modules in the project, defining their roles, inter-dependencies, and high-level connectivity requirements.',
    category: 'protocol',
    parentId: 'project-root',
    children: [],
    repositoryPath: 'sample-projects/bms-experiments-milestone-1/bms-project_e0505ca9/bms-project_e0505ca9_root/system-boundary.md',
    tags: ['Specification', 'Master Registry', 'System Design'],
    metadata: {
      status: 'stable'
    }
  },
  'assembly-abstraction': {
    id: 'assembly-abstraction',
    title: 'Assembly Abstraction',
    shortDescription: 'Integration and interconnection of multiple functional modules.',
    purpose: 'Achieves a specific hardware design target by instantiating modules and defining the electrical connections (traces) between them via Assembly SCUD and .tsx code.',
    category: 'feature',
    parentId: 'project-root',
    children: ['assembly-scud', 'assembly-tsx'],
    tags: ['Integration', 'Assembly', 'Interconnect'],
    metadata: {
      status: 'stable'
    }
  },
  'assembly-scud': {
    id: 'assembly-scud',
    title: 'Assembly SCUD',
    shortDescription: 'Design intent for the integrated assembly.',
    purpose: 'Describes how modules are combined, the overall assembly intent, and the high-level routing requirements in a Markdown format.',
    category: 'feature',
    parentId: 'assembly-abstraction',
    children: [],
    tags: ['SCUD', 'Design Intent', 'Assembly'],
    metadata: {
      status: 'stable'
    }
  },
  'assembly-tsx': {
    id: 'assembly-tsx',
    title: 'Assembly Circuit Code (.tsx)',
    shortDescription: 'Executable tscircuit implementation of the assembly.',
    purpose: 'Imports validated module components and interconnects them to form the final hardware design.',
    category: 'feature',
    parentId: 'assembly-abstraction',
    children: [],
    tags: ['tscircuit', 'Code', 'Implementation'],
    metadata: {
      status: 'stable'
    }
  },
  'module-abstraction': {
    id: 'module-abstraction',
    title: 'Module Abstraction',
    shortDescription: 'Self-contained, isolated functional building block.',
    purpose: 'Represents a single engineering capability (e.g., Power Supply, MCU Core). Modules evolve independently with dedicated infrastructure and agents.',
    category: 'feature',
    parentId: 'user-project-model',
    children: ['module-boundary-doc', 'module-scud', 'module-tsx', 'module-worktree', 'module-agents'],
    tags: ['Module', 'Isolation', 'Building Block'],
    metadata: {
      status: 'stable'
    }
  },
  'module-boundary-doc': {
    id: 'module-boundary-doc',
    title: 'Module Boundary Document (module-boundary.md)',
    shortDescription: 'Detailed interface specification for a specific module.',
    purpose: 'Defines the module\'s ports, consumed/produced resources, and operational contracts. Extracted from the System Boundary for isolated development.',
    category: 'protocol',
    parentId: 'module-abstraction',
    children: [],
    tags: ['Interface', 'Contract', 'Port Spec'],
    metadata: {
      status: 'stable'
    }
  },
  'module-scud': {
    id: 'module-scud',
    title: 'Module SCUD',
    shortDescription: 'Shared Circuit Understanding Document for the module.',
    purpose: 'Captures the module\'s internal design intent, component inventory, and signal flow in a format understandable by both humans and AI agents.',
    category: 'feature',
    parentId: 'module-abstraction',
    children: [],
    tags: ['SCUD', 'Intent', 'Inventory'],
    metadata: {
      status: 'stable'
    }
  },
  'module-tsx': {
    id: 'module-tsx',
    title: 'Module Circuit Code (.tsx)',
    shortDescription: 'Independent tscircuit implementation of the module.',
    purpose: 'The executable source code for the module, authored and refined by the ANA agent based on SCUD and Boundary specs.',
    category: 'feature',
    parentId: 'module-abstraction',
    children: [],
    tags: ['tscircuit', 'Code', 'Implementation'],
    metadata: {
      status: 'stable'
    }
  },
  'module-worktree': {
    id: 'module-worktree',
    title: 'Module Git Worktree',
    shortDescription: 'Isolated development space for module evolution.',
    purpose: 'Each module is hosted in a dedicated Git worktree to ensure isolated file operations and prevent cross-module interference during synthesis.',
    category: 'storage',
    parentId: 'module-abstraction',
    children: [],
    tags: ['Git', 'Worktree', 'Isolation'],
    metadata: {
      status: 'stable'
    }
  },
  'module-agents': {
    id: 'module-agents',
    title: 'Dedicated Module Agents',
    shortDescription: 'Persistent URP agents assigned to a specific module.',
    purpose: 'Each module maintains its own context-aware instances of Archy, Librarian, and ANA agents, allowing the module to evolve independently.',
    category: 'agent',
    parentId: 'module-abstraction',
    children: [],
    tags: ['Agents', 'Archy', 'ANA', 'Librarian'],
    metadata: {
      status: 'stable'
    }
  },
  'design-artifacts': {
    id: 'design-artifacts',
    title: 'Design Artifacts & Validation',
    shortDescription: 'Documentation and feedback from the design loop.',
    purpose: 'Includes boundary alignment checks, evaluation results (VAP), and the shared specifications used by agents.',
    category: 'feature',
    parentId: 'user-project-model',
    children: ['boundary-alignment-doc', 'evaluation-results', 'scud-spec'],
    tags: ['Artifacts', 'Validation', 'Feedback'],
    metadata: {
      status: 'stable'
    }
  },
  'boundary-alignment-doc': {
    id: 'boundary-alignment-doc',
    title: 'Boundary Alignment Document',
    shortDescription: 'Verification of implementation against boundary specs.',
    purpose: 'Ensures that the current .tsx implementation correctly adheres to the defined Module Boundary and System Boundary requirements.',
    category: 'feature',
    parentId: 'design-artifacts',
    children: [],
    tags: ['Alignment', 'Verification', 'Quality'],
    metadata: {
      status: 'stable'
    }
  },
  'evaluation-results': {
    id: 'evaluation-results',
    title: 'Evaluation Results (VAP Logs)',
    shortDescription: 'Pass/Fail feedback from the Runtime execution engine.',
    purpose: 'Stores logs and diagnostic data from the VAP engine after running circuit evaluations, used by ANA for iterative refinement.',
    category: 'feature',
    parentId: 'design-artifacts',
    children: [],
    tags: ['VAP', 'Logs', 'Testing Feedback'],
    metadata: {
      status: 'stable'
    }
  },
  'scud-spec': {
    id: 'scud-spec',
    title: 'SCUD (Shared Circuit Understanding Document)',
    shortDescription: 'The "lingua franca" of VHL design intent.',
    purpose: 'A Markdown-based specification format that bridges the gap between human designers and AI agents, capturing high-level circuit semantics.',
    category: 'protocol',
    parentId: 'design-artifacts',
    children: [],
    tags: ['Protocol', 'Markdown', 'LLM-Friendly'],
    metadata: {
      status: 'stable'
    }
  }
};
