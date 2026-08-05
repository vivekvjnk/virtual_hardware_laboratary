import type { ArchitectureGraphData } from '../types/architecture';

export const backendArchitectureData: ArchitectureGraphData = {
  rootId: 'vhl-agent-backend',
  nodes: {
    'vhl-agent-backend': {
      id: 'vhl-agent-backend',
      title: 'VHL Agent Backend',
      shortDescription: 'State-aware multi-agent orchestration layer ("The Brain") for electronic circuit design.',
      purpose: 'Orchestrates design perception, component resolution, code synthesis, evaluation, and project state persistence across specialized AI agents.',
      category: 'root',
      parentId: null,
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

    // 1. URP AGENT LAYER
    'urp-agent-layer': {
      id: 'urp-agent-layer',
      title: 'URP Agent Layer',
      shortDescription: 'Unified Runtime Primitive framework aligned with Linux Foundation A2A protocol.',
      purpose: 'Standardizes agent identity, persistence, mailbox transport, control plane supervisor, and specialized engineering agents.',
      category: 'subsystem',
      parentId: 'vhl-agent-backend',
      children: ['urp-infrastructure', 'urp-agents', 'urp-features'],
      repositoryPath: 'vhl-agent-backend/vhl_common/urp',
      documentation: [
        {
          title: 'URP Specification',
          path: 'docs/architecture/urp-agent-layer/URP.md',
          description: 'Unified Runtime Primitive specification for agent communication.'
        },
        {
          title: 'Architecture Diagram - URP Layer',
          path: 'docs/architecture/architecture_diagram.md',
          description: 'Subsystem component breakdown.'
        }
      ],
      tags: ['Subsystem', 'A2A Protocol', 'Agents', 'Control Plane'],
      metadata: {
        techStack: ['Python', 'URP Spec', 'OpenHands SDK'],
        status: 'active'
      }
    },

    // 1.1 Infrastructure
    'urp-infrastructure': {
      id: 'urp-infrastructure',
      title: 'URP Infrastructure',
      shortDescription: 'Control plane primitives: Supervisor, Controllers, GATE, and Agent Registry.',
      purpose: 'Manages agent lifecycle, task authority delegation, mailbox messaging, and capability registration.',
      category: 'infrastructure',
      parentId: 'urp-agent-layer',
      children: ['supervisor', 'workflow-controllers', 'gate-hil', 'agent-registry', 'abstract-urp'],
      repositoryPath: 'vhl-agent-backend/vhl_common',
      tags: ['Infrastructure', 'Control Plane'],
      metadata: {
        status: 'stable'
      }
    },
    'supervisor': {
      id: 'supervisor',
      title: 'Supervisor & Control Plane',
      shortDescription: 'Central authority managing agent registration, lifecycle, and authority delegation.',
      purpose: 'Delegates agent authority to workflow controllers via claim/release semantics and maintains active agent states.',
      category: 'infrastructure',
      parentId: 'urp-infrastructure',
      children: [],
      repositoryPath: 'vhl-agent-backend/vhl_common/supervisor/supervisor.py',
      documentation: [
        {
          title: 'Supervisor Design Document',
          path: 'docs/architecture/urp-agent-layer/supervisor-design-document.md',
          description: 'Central authority design and control plane mechanics.'
        },
        {
          title: 'Supervisor Implementation',
          path: 'docs/architecture/urp-agent-layer/supervisor-implementation.md',
          description: 'Implementation breakdown for agent allocation.'
        }
      ],
      tags: ['Supervisor', 'Authority Delegation', 'Lifecycle'],
      metadata: {
        keyInterfaces: ['claim_agent()', 'release_agent()', 'register_agent()'],
        status: 'stable'
      }
    },
    'workflow-controllers': {
      id: 'workflow-controllers',
      title: 'Workflow Controllers',
      shortDescription: 'Specialized orchestration controllers executing multi-step workflows.',
      purpose: 'Claims agents from Supervisor, assigns design tasks, manages retry/escalation logic, and advances workflow state.',
      category: 'controller',
      parentId: 'urp-infrastructure',
      children: ['workflow-1-controller'],
      repositoryPath: 'vhl-agent-backend/vhl_common/supervisor/controllers',
      documentation: [
        {
          title: 'Workflow 1 Orchestration',
          path: 'vhl-agent-backend/docs/source/ana/workflow1_orchestration.md',
          description: 'Schematic-to-circuit workflow controller.'
        }
      ],
      tags: ['Controller', 'Workflows'],
      metadata: {
        status: 'active'
      }
    },
    'workflow-1-controller': {
      id: 'workflow-1-controller',
      title: 'Workflow 1 Controller',
      shortDescription: 'Controller executing schematic-to-verified-circuit synthesis.',
      purpose: 'Coordinates multi-agent handoffs across Archy (perception), Librarian (components), and ANA (synthesis).',
      category: 'controller',
      parentId: 'workflow-controllers',
      children: [],
      repositoryPath: 'vhl-agent-backend/vhl_common/supervisor/controllers/workflow_1_controller.py',
      tags: ['Workflow 1', 'Schematic Flow'],
      metadata: {
        status: 'stable'
      }
    },
    'gate-hil': {
      id: 'gate-hil',
      title: 'GATE & Human-In-The-Loop',
      shortDescription: 'Global Asynchronous Transport Engine and HIL interaction gate.',
      purpose: 'Decouples inter-agent message delivery with async mailboxes and handles user clarification requests.',
      category: 'gate',
      parentId: 'urp-infrastructure',
      children: ['gate-engine', 'hil-gate'],
      repositoryPath: 'vhl-agent-backend/vhl_common/gate',
      documentation: [
        {
          title: 'Global Asynchronous Transport Engine Spec',
          path: 'docs/architecture/urp-agent-layer/Global_Asynchronous_Transport_Engine.md',
          description: 'Asynchronous transport and mailbox buffering specification.'
        }
      ],
      tags: ['GATE', 'Async Transport', 'HIL'],
      metadata: {
        status: 'stable'
      }
    },
    'gate-engine': {
      id: 'gate-engine',
      title: 'GATE Transport Engine',
      shortDescription: 'Asynchronous message bus engine for URP agents.',
      purpose: 'Routes messages between agent mailboxes across system boundaries with guaranteed async delivery.',
      category: 'gate',
      parentId: 'gate-hil',
      children: [],
      repositoryPath: 'vhl-agent-backend/vhl_common/gate/gate.py',
      tags: ['Async Bus', 'Mailbox Router'],
      metadata: {
        status: 'stable'
      }
    },
    'hil-gate': {
      id: 'hil-gate',
      title: 'HIL Gate Manager',
      shortDescription: 'Human-In-The-Loop interaction handler.',
      purpose: 'Pauses workflow execution when ambiguity is detected, prompts user via WebUI, and resumes upon input.',
      category: 'gate',
      parentId: 'gate-hil',
      children: [],
      repositoryPath: 'vhl-agent-backend/vhl_common/gate/hil.py',
      tags: ['Human in Loop', 'Approval Gate'],
      metadata: {
        status: 'stable'
      }
    },
    'agent-registry': {
      id: 'agent-registry',
      title: 'Agent Registry',
      shortDescription: 'Global registry tracking available agents and capabilities.',
      purpose: 'Enables dynamic agent discovery, capability mapping, and runtime lookup for supervisors and controllers.',
      category: 'infrastructure',
      parentId: 'urp-infrastructure',
      children: [],
      repositoryPath: 'vhl-agent-backend/vhl_common/urp/agent_registry.py',
      documentation: [
        {
          title: 'Agent Registry Design',
          path: 'docs/architecture/urp-agent-layer/agent-registry-design.md',
          description: 'Registry design and capability resolution.'
        }
      ],
      tags: ['Registry', 'Discovery'],
      metadata: {
        status: 'stable'
      }
    },
    'abstract-urp': {
      id: 'abstract-urp',
      title: 'Abstract URP Base Class',
      shortDescription: 'Python reference implementation of Unified Runtime Primitive.',
      purpose: 'Base class for URP agents providing standard initialization, mailbox handlers, and conversation persistence.',
      category: 'infrastructure',
      parentId: 'urp-infrastructure',
      children: [],
      repositoryPath: 'vhl-agent-backend/vhl_common/urp/abstract_urp.py',
      documentation: [
        {
          title: 'URP Specification',
          path: 'docs/architecture/urp-agent-layer/URP.md',
          description: 'Primitive specification and standards.'
        }
      ],
      tags: ['Base Class', 'URP Core'],
      metadata: {
        status: 'stable'
      }
    },

    // 1.2 Agents
    'urp-agents': {
      id: 'urp-agents',
      title: 'Specialized Agents',
      shortDescription: 'Domain-specific URP agents for perception, resolution, and code synthesis.',
      purpose: 'Autonomous AI agents specialized in vision analysis, component resolution, and tscircuit synthesis.',
      category: 'agent',
      parentId: 'urp-agent-layer',
      children: ['archy-agent', 'ana-agent', 'librarian-agent'],
      repositoryPath: 'vhl-agent-backend',
      tags: ['Agents', 'LLM reasoning'],
      metadata: {
        status: 'active'
      }
    },
    'archy-agent': {
      id: 'archy-agent',
      title: 'Archy Agent (Perception)',
      shortDescription: 'Vision and perception agent parsing schematic images into SCUD.',
      purpose: 'Translates uploaded circuit diagrams into structured Shared Circuit Understanding Documents (SCUD).',
      category: 'agent',
      parentId: 'urp-agents',
      children: ['archy-scud-generator'],
      repositoryPath: 'vhl-agent-backend/archy/archy_agent',
      documentation: [
        {
          title: 'Archy Agent Design & SCUD Generation',
          path: 'vhl-agent-backend/docs/source/urp/archy_urp.md',
          description: 'Vision segmentation and SCUD parsing pipeline.'
        }
      ],
      tags: ['Perception', 'SCUD', 'Vision'],
      metadata: {
        status: 'stable'
      }
    },
    'archy-scud-generator': {
      id: 'archy-scud-generator',
      title: 'SCUD Generator',
      shortDescription: 'Core image-to-text specification engine in Archy.',
      purpose: 'Extracts components, connectivity nets, and functional descriptions from visual input.',
      category: 'agent',
      parentId: 'archy-agent',
      children: [],
      repositoryPath: 'vhl-agent-backend/archy/archy_agent/',
      tags: ['SCUD', 'Parser'],
      metadata: {
        status: 'stable'
      }
    },
    'ana-agent': {
      id: 'ana-agent',
      title: 'ANA-D Agent (Synthesis & Refinement)',
      shortDescription: 'Circuit synthesis agent generating and refining tscircuit code.',
      purpose: 'Iteratively authors .tsx circuit code, stages code for runtime evaluation, and performs reflective refinement.',
      category: 'agent',
      parentId: 'urp-agents',
      children: ['ana-w1-generator', 'ana-w2-validator', 'observer-agent'],
      repositoryPath: 'vhl-agent-backend/ana/ana_agent',
      documentation: [
        {
          title: 'ANA Workflow 1 Orchestration',
          path: 'vhl-agent-backend/docs/source/ana/workflow1_orchestration.md',
          description: 'Synthesis loop and reflective refinement design.'
        }
      ],
      tags: ['Synthesis', 'Code Generator', 'Refinement Loop'],
      metadata: {
        status: 'active'
      }
    },
    'ana-w1-generator': {
      id: 'ana-w1-generator',
      title: 'ANA-W1 Code Generator',
      shortDescription: 'LLM synthesis engine writing tscircuit React components.',
      purpose: 'Generates valid TSX code based on SCUD specifications and previous observer feedback.',
      category: 'agent',
      parentId: 'ana-agent',
      children: [],
      repositoryPath: 'vhl-agent-backend/ana/ana_agent/',
      tags: ['Code Generation', 'TSX'],
      metadata: {
        status: 'active'
      }
    },
    'ana-w2-validator': {
      id: 'ana-w2-validator',
      title: 'ANA-W2 Deterministic Validator',
      shortDescription: 'Evaluation pipeline trigger interfacing with runtime VAP.',
      purpose: 'Submits code to runtime evaluation engine and collects pass/fail results.',
      category: 'agent',
      parentId: 'ana-agent',
      children: [],
      repositoryPath: 'vhl-agent-backend/ana/ana_agent/',
      tags: ['Validation Trigger', 'VAP Interface'],
      metadata: {
        status: 'stable'
      }
    },
    'observer-agent': {
      id: 'observer-agent',
      title: 'Observer Agent',
      shortDescription: 'Reflective agent analyzing VAP evaluation logs.',
      purpose: 'Parses compilation and check failures, posting structured observations to AnaMCP for ANA-W1.',
      category: 'agent',
      parentId: 'ana-agent',
      children: [],
      repositoryPath: 'vhl-agent-backend/ana/ana_agent/',
      tags: ['Log Observer', 'Refinement'],
      metadata: {
        status: 'stable'
      }
    },
    'librarian-agent': {
      id: 'librarian-agent',
      title: 'Librarian Agent (Resolution)',
      shortDescription: 'Component resolution agent fetching libraries via MCP.',
      purpose: 'Maps SCUD inventory components to verified tscircuit component packages (JLCPCB/EasyEDA).',
      category: 'agent',
      parentId: 'urp-agents',
      children: ['mcp-library-resolver'],
      repositoryPath: 'vhl-agent-backend/librarian/librarian_agent',
      tags: ['Library Resolution', 'MCP Client'],
      metadata: {
        status: 'stable'
      }
    },
    'mcp-library-resolver': {
      id: 'mcp-library-resolver',
      title: 'MCP Library Resolver',
      shortDescription: 'Interfacing module with Library MCP Server.',
      purpose: 'Queries library search tools via MCP and imports package dependencies into the workspace.',
      category: 'agent',
      parentId: 'librarian-agent',
      children: [],
      repositoryPath: 'vhl-agent-backend/librarian/librarian_agent/',
      tags: ['MCP Search', 'Importer'],
      metadata: {
        status: 'stable'
      }
    },

    // 1.3 Features
    'urp-features': {
      id: 'urp-features',
      title: 'URP Features & Validation',
      shortDescription: 'Replay snapshot engine and state evaluation tools.',
      purpose: 'Enables deterministic end-to-end testing, LLM snapshot replay, and project state validation.',
      category: 'feature',
      parentId: 'urp-agent-layer',
      children: ['replay-snapshot', 'evaluators-integration'],
      repositoryPath: 'vhl-agent-backend/vhl_common',
      tags: ['Features', 'Testing'],
      metadata: {
        status: 'stable'
      }
    },
    'replay-snapshot': {
      id: 'replay-snapshot',
      title: 'Replay-Snapshot Testing Engine',
      shortDescription: 'Deterministic test framework utilizing recorded LLM conversation snapshots.',
      purpose: 'Replays LLM responses during tests with dynamic workspace path substitution.',
      category: 'feature',
      parentId: 'urp-features',
      children: [],
      repositoryPath: 'vhl-agent-backend/vhl_common/llm',
      documentation: [
        {
          title: 'Snapshot Replay Agent Spec',
          path: 'docs/architecture/urp-agent-layer/snapshot_replay_agent.md',
          description: 'Snapshot recording and replay framework.'
        },
        {
          title: 'E2E Testing Documentation',
          path: 'docs/test/end_2_end_test/e2e_test_documentation.md',
          description: 'End-to-end testing guide.'
        }
      ],
      tags: ['ReplayLLM', 'Snapshot', 'Testing'],
      metadata: {
        status: 'stable'
      }
    },
    'evaluators-integration': {
      id: 'evaluators-integration',
      title: 'State Evaluators',
      shortDescription: 'System evaluation helpers for project state validation.',
      purpose: 'Checks project state integrity and rule compliance across workspace artifacts.',
      category: 'feature',
      parentId: 'urp-features',
      children: [],
      repositoryPath: 'vhl-agent-backend/vhl_common/project_state_manager/evaluators',
      tags: ['Evaluators', 'Integrity'],
      metadata: {
        status: 'evolving'
      }
    },

    // 2. PROTOCOL LAYER
    'protocol-layer': {
      id: 'protocol-layer',
      title: 'Protocol Layer',
      shortDescription: 'Event-driven protocol layer connecting Agent Backend with Runtime.',
      purpose: 'Provides WebSocket client messaging, shared Pydantic data models, and protocol utilities.',
      category: 'subsystem',
      parentId: 'vhl-agent-backend',
      children: ['websocket-client', 'protocol-models', 'protocol-utils'],
      repositoryPath: 'vhl-agent-backend/vhl_protocol',
      documentation: [
        {
          title: 'Protocol Layer Documentation',
          path: 'docs/architecture/protocol-layer/README.md',
          description: 'Protocol specification and client overview.'
        },
        {
          title: 'Protocol AGENTS Guide',
          path: 'docs/architecture/protocol-layer/AGENTS.md',
          description: 'Protocol message flow definitions.'
        }
      ],
      tags: ['Subsystem', 'Protocol', 'WebSocket', 'Models'],
      metadata: {
        techStack: ['Python', 'WebSockets', 'Pydantic'],
        status: 'stable'
      }
    },
    'websocket-client': {
      id: 'websocket-client',
      title: 'WebSocket Client Infrastructure',
      shortDescription: 'Async WebSocket client connecting backend to Runtime Relay Server.',
      purpose: 'Maintains bidirectional real-time connection for event synchronization and command relay.',
      category: 'protocol',
      parentId: 'protocol-layer',
      children: [],
      repositoryPath: 'vhl-agent-backend/vhl_protocol/websocket_client',
      documentation: [
        {
          title: 'WebSocket Agent Proxy Relay',
          path: 'vhl-runtime/docs/websocket-agent-proxy.md',
          description: 'Runtime relay server integration.'
        }
      ],
      tags: ['WebSocket', 'Client', 'Asyncio'],
      metadata: {
        runtimeEvents: ['PROJECT_CREATED', 'REFERENCE_UPLOADED', 'SYNC_TRIGGER', 'ANA_NOTIFY', 'HIL_REQUEST'],
        status: 'stable'
      }
    },
    'protocol-models': {
      id: 'protocol-models',
      title: 'Protocol Models & Schemas',
      shortDescription: 'Strongly typed Pydantic models for WebSocket payloads and state contracts.',
      purpose: 'Enforces type safety and serializes events transmitted across backend, runtime, and UI.',
      category: 'protocol',
      parentId: 'protocol-layer',
      children: [],
      repositoryPath: 'vhl-agent-backend/vhl_protocol/models.py',
      tags: ['Pydantic', 'Schemas', 'Types'],
      metadata: {
        status: 'stable'
      }
    },
    'protocol-utils': {
      id: 'protocol-utils',
      title: 'Utility Tools (MCP & Storage)',
      shortDescription: 'Infrastructure helpers for MCP invocation, ZIP archives, and MinIO storage.',
      purpose: 'Facilitates object store blob synchronization, MCP tool execution, and zip archive packing.',
      category: 'protocol',
      parentId: 'protocol-layer',
      children: [],
      repositoryPath: 'vhl-agent-backend/vhl_protocol/utils',
      tags: ['MCP Invoker', 'ZIP Tool', 'MinIO Client'],
      metadata: {
        status: 'stable'
      }
    },

    // 3. WORKSPACE SUBSYSTEM
    'workspace-subsystem': {
      id: 'workspace-subsystem',
      title: 'Workspace Subsystem',
      shortDescription: 'Copy-on-Write workspace, multi-worktree Git versioning, and SQLite database.',
      purpose: 'Manages local workspace isolation, iteration directories, module worktrees, and project state persistence.',
      category: 'subsystem',
      parentId: 'vhl-agent-backend',
      children: ['workspace-manager', 'git-wrapper', 'sqlite-manager', 'zip-restore'],
      repositoryPath: 'vhl-agent-backend/vhl_common/workspace_manager',
      documentation: [
        {
          title: 'Persistent Project State Management',
          path: 'vhl-agent-backend/docs/source/project_state_management/Project_state_management.md',
          description: 'Git and SQLite persistent state architecture.'
        },
        {
          title: 'Stable Circuit Synchronization Protocol',
          path: 'docs/SyncArchitectureAnalysis.md',
          description: 'Synchronization analysis across layers.'
        }
      ],
      tags: ['Subsystem', 'Workspace', 'Git', 'SQLite', 'CoW'],
      metadata: {
        techStack: ['SQLite', 'Git Worktree', 'Python Pathlib'],
        authoritativeHost: 'Backend Local Workspace',
        status: 'stable'
      }
    },
    'workspace-manager': {
      id: 'workspace-manager',
      title: 'Workspace Manager (CoW)',
      shortDescription: 'Copy-on-Write workspace manager handling iteration lifecycle.',
      purpose: 'Isolates synthesis in iteration directories before promoting accepted designs to the main branch.',
      category: 'storage',
      parentId: 'workspace-subsystem',
      children: [],
      repositoryPath: 'vhl-agent-backend/vhl_common/workspace_manager/manager.py',
      documentation: [
        {
          title: 'Workspace Manager Specification',
          path: 'vhl-agent-backend/docs/source/workspace_manager.md',
          description: 'CoW iteration and archive lifecycle.'
        }
      ],
      tags: ['CoW', 'Iteration', 'Isolation'],
      metadata: {
        status: 'stable'
      }
    },
    'git-wrapper': {
      id: 'git-wrapper',
      title: 'Git & Worktree Manager',
      shortDescription: 'Multi-worktree Git version control integration.',
      purpose: 'Creates dedicated Git worktrees per module and handles trunk-based consolidation for assemblies.',
      category: 'storage',
      parentId: 'workspace-subsystem',
      children: [],
      repositoryPath: 'vhl-agent-backend/vhl_common/project_state_manager/git_wrapper.py',
      tags: ['Git', 'Worktree', 'Trunk Merge'],
      metadata: {
        status: 'stable'
      }
    },
    'sqlite-manager': {
      id: 'sqlite-manager',
      title: 'SQLite Project State Store',
      shortDescription: 'Per-project SQLite database manager (.vhl/state.db).',
      purpose: 'Persists active project state, module boundaries, SCUD specifications, and execution history.',
      category: 'storage',
      parentId: 'workspace-subsystem',
      children: [],
      repositoryPath: 'vhl-agent-backend/vhl_common/project_state_manager/sqlite_manager.py',
      tags: ['SQLite', 'State DB', 'Persistence'],
      metadata: {
        status: 'stable'
      }
    },
    'zip-restore': {
      id: 'zip-restore',
      title: 'ZIP Restore Utility',
      shortDescription: 'Project archive unpacking and workspace initializer.',
      purpose: 'Extracts uploaded ZIP project archives and initializes workspace directories, Git, and SQLite.',
      category: 'storage',
      parentId: 'workspace-subsystem',
      children: [],
      repositoryPath: 'vhl-agent-backend/vhl_common/workspace_manager/zip_restore.py',
      tags: ['ZIP', 'Archive', 'Restore'],
      metadata: {
        status: 'stable'
      }
    },

    // 4. AOSM
    'aosm': {
      id: 'aosm',
      title: 'AOSM (Orchestration Engine)',
      shortDescription: 'Top-level Agent Orchestration State Machine hosting vhl-agent-backend.',
      purpose: 'Central control loop governing high-level project lifecycle phases and multi-agent transitions.',
      category: 'subsystem',
      parentId: 'vhl-agent-backend',
      children: ['aosm-state-machine'],
      repositoryPath: 'vhl-agent-backend/aosm',
      documentation: [
        {
          title: 'Detailed Backend Architecture',
          path: 'vhl-agent-backend/docs/source/ARCHITECTURE.md',
          description: 'AOSM state machine diagram and transition details.'
        }
      ],
      tags: ['Subsystem', 'AOSM', 'State Machine', 'Control Loop'],
      metadata: {
        techStack: ['Python', 'FSM'],
        status: 'stable'
      }
    },
    'aosm-state-machine': {
      id: 'aosm-state-machine',
      title: 'AOSM State Machine Engine',
      shortDescription: 'Finite state machine implementing system orchestration phases.',
      purpose: 'Executes transitions: STARTUP → IDLE → BOOTSTRAP_PIPELINE → TRIGGER_ARCHY → TRIGGER_LIBRARIAN → TRIGGER_ANA → PRESENT_RESULT.',
      category: 'subsystem',
      parentId: 'aosm',
      children: [],
      repositoryPath: 'vhl-agent-backend/aosm/state_machine/aosm.py',
      tags: ['FSM', 'State Transitions', 'Control Loop'],
      metadata: {
        runtimeEvents: ['STARTUP', 'IDLE', 'BOOTSTRAP_PIPELINE', 'TRIGGER_ARCHY', 'TRIGGER_LIBRARIAN', 'TRIGGER_ANA', 'PRESENT_RESULT'],
        status: 'stable'
      }
    }
  }
};

/**
 * Helper functions to query the graph data model
 */
export function getNode(graph: ArchitectureGraphData, id: string) {
  return graph.nodes[id] || null;
}

export function getChildrenNodes(graph: ArchitectureGraphData, id: string) {
  const node = getNode(graph, id);
  if (!node) return [];
  return node.children.map((childId) => graph.nodes[childId]).filter(Boolean);
}

export function getAncestors(graph: ArchitectureGraphData, id: string) {
  const ancestors: string[] = [];
  let currentId: string | null = id;
  while (currentId) {
    const node = getNode(graph, currentId);
    if (node && node.parentId) {
      ancestors.unshift(node.parentId);
      currentId = node.parentId;
    } else {
      break;
    }
  }
  return ancestors;
}

export function searchNodes(graph: ArchitectureGraphData, query: string) {
  if (!query.trim()) return [];
  const q = query.toLowerCase();
  return Object.values(graph.nodes).filter(
    (node) =>
      node.title.toLowerCase().includes(q) ||
      node.shortDescription.toLowerCase().includes(q) ||
      node.purpose.toLowerCase().includes(q) ||
      (node.repositoryPath && node.repositoryPath.toLowerCase().includes(q)) ||
      (node.tags && node.tags.some((t) => t.toLowerCase().includes(q)))
  );
}
