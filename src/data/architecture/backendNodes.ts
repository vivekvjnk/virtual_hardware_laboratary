import type { ArchitectureNode } from '../../types/architecture';

export const backendNodes: Record<string, ArchitectureNode> = {
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
    purpose: 'Delegates agent authority to workflow controllers via claim/release semantics and maintains active agent states. Acts as the sole authority for agent instance management and arbitration.',
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
      keyInterfaces: [
        'claim_agent()', 
        'release_agent()', 
        'register_agent()', 
        'attach_agent()', 
        'detach_agent()', 
        'process_outcomes()', 
        'send()'
      ],
      status: 'stable'
    }
  },
  'workflow-controllers': {
    id: 'workflow-controllers',
    title: 'Workflow Controllers',
    shortDescription: 'Specialized orchestration controllers executing multi-step workflows.',
    purpose: 'Claims agents from Supervisor, assigns design tasks, manages retry/escalation logic, and advances workflow state. Includes specialized and default controllers.',
    category: 'controller',
    parentId: 'urp-infrastructure',
    children: ['workflow-1-controller', 'default-controller'],
    repositoryPath: 'vhl-agent-backend/vhl_common/supervisor/controllers',
    documentation: [
      {
        title: 'Workflow 1 Design (ANA Orchestration)',
        path: 'vhl-agent-backend/docs/source/ana/workflow1_orchestration.md',
        description: 'Schematic-to-circuit workflow controller and synthesis loop.'
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
    purpose: 'Coordinates standard sequential pipeline: Archy (perception) -> Librarian (resolution) -> ANA (synthesis).',
    category: 'controller',
    parentId: 'workflow-controllers',
    children: [],
    repositoryPath: 'vhl-agent-backend/vhl_common/supervisor/controllers/workflow1_controller.py',
    tags: ['Workflow 1', 'Schematic Flow', 'Orchestrator'],
    metadata: {
      status: 'stable'
    }
  },
  'default-controller': {
    id: 'default-controller',
    title: 'Default Controller',
    shortDescription: 'Fallback controller for unclaimed agent instances.',
    purpose: 'Automatically assigned by the Supervisor to manage agents that are not claimed by specialized workflow controllers, preventing zombie processes.',
    category: 'controller',
    parentId: 'workflow-controllers',
    children: [],
    repositoryPath: 'vhl-agent-backend/vhl_common/supervisor/controllers/default_controller.py',
    tags: ['Fallback', 'Lifecycle', 'Supervisor'],
    metadata: {
      status: 'stable'
    }
  },
  'gate-hil': {
    id: 'gate-hil',
    title: 'GATE & HIL Terminal',
    shortDescription: 'Global Asynchronous Transport Engine and HIL Terminal interface.',
    purpose: 'Decouples inter-agent message delivery and provides a terminal interface for human observation/interaction.',
    category: 'gate',
    parentId: 'urp-infrastructure',
    children: ['gate-engine', 'hil-terminal'],
    repositoryPath: 'vhl-agent-backend/vhl_common/gate',
    documentation: [
      {
        title: 'Global Asynchronous Transport Engine Spec',
        path: 'docs/architecture/urp-agent-layer/Global_Asynchronous_Transport_Engine.md',
        description: 'Asynchronous transport and mailbox buffering specification.'
      }
    ],
    tags: ['GATE', 'Async Transport', 'HIL Terminal'],
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
  'hil-terminal': {
    id: 'hil-terminal',
    title: 'HIL Terminal',
    shortDescription: 'TCP Socket Terminal interface to GATE.',
    purpose: 'Analogous to serial debug lines. Allows engineers to observe GATE traffic and manually interact with agents as a regular GATE participant.',
    category: 'gate',
    parentId: 'gate-hil',
    children: [],
    repositoryPath: 'vhl-agent-backend/vhl_common/gate/hil.py',
    tags: ['Terminal', 'Debug', 'GATE Participant'],
    metadata: {
      techStack: ['Python', 'asyncio TCP server'],
      status: 'stable'
    }
  },
  'agent-registry': {
    id: 'agent-registry',
    title: 'Agent Registry',
    shortDescription: 'State-aware interface over persistent URP agents.',
    purpose: 'Enables discovery, inspection, and readiness determination of agents. Transforms agents from function calls into long-lived processes.',
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
    tags: ['Registry', 'Discovery', 'Persistence'],
    metadata: {
      keyInterfaces: [
        'register()',
        'get_or_create()',
        'list_agents()',
        'snapshot()'
      ],
      status: 'stable'
    }
  },
  'abstract-urp': {
    id: 'abstract-urp',
    title: 'Abstract URP Base Class',
    shortDescription: 'Python reference implementation of Unified Runtime Primitive.',
    purpose: 'Base class for URP agents providing standard initialization, mailbox handlers, and conversation persistence. Defines the core lifecycle of VHL agents.',
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
      keyInterfaces: [
        'initialize()',
        'start()',
        'process()',
        'emit()',
        'shutdown()'
      ],
      status: 'stable'
    }
  },
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
    title: 'ANA Agent (Synthesis & Refinement)',
    shortDescription: 'Persistent agent for circuit synthesis and iterative refinement.',
    purpose: 'Iteratively authors .tsx circuit code, stages code for runtime evaluation, and performs reflective refinement based on VAP results.',
    category: 'agent',
    parentId: 'urp-agents',
    children: [],
    repositoryPath: 'vhl-agent-backend/ana/ana_agent',
    documentation: [
      {
        title: 'ANA Agent Design',
        path: 'vhl-agent-backend/docs/source/ana/workflow1_orchestration.md',
        description: 'Synthesis loop and reflective refinement design.'
      }
    ],
    tags: ['Synthesis', 'Code Generator', 'Refinement Loop', 'Persistent Agent'],
    metadata: {
      status: 'active'
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
  'protocol-layer': {
    id: 'protocol-layer',
    title: 'Protocol Layer',
    shortDescription: 'Canonical event protocol and shared communication utilities.',
    purpose: 'The "lingua franca" for communication between Backend, Runtime, and WebUI. Ensures authority separation, deterministic state transitions, and auditability.',
    category: 'subsystem',
    parentId: 'vhl-agent-backend',
    children: ['websocket-client', 'protocol-models', 'protocol-utils'],
    repositoryPath: 'vhl-agent-backend/vhl_protocol',
    documentation: [
      {
        title: 'Protocol Layer README',
        path: 'docs/architecture/protocol-layer/README.md',
        description: 'Protocol specification and client overview.'
      },
      {
        title: 'Protocol Layer AGENTS Guide',
        path: 'docs/architecture/protocol-layer/AGENTS.md',
        description: 'Protocol component and development guide.'
      }
    ],
    tags: ['Subsystem', 'Protocol', 'WebSocket', 'Pydantic'],
    metadata: {
      techStack: ['Python', 'Pydantic v2', 'WebSockets'],
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
    shortDescription: 'Strongly typed Pydantic models for WebSocket payloads.',
    purpose: 'Enforces type safety and serializes events (Observation, Orchestration, Project Mgmt) transmitted across the ecosystem.',
    category: 'protocol',
    parentId: 'protocol-layer',
    children: [],
    repositoryPath: 'vhl-agent-backend/vhl_protocol/models.py',
    tags: ['Pydantic', 'Schemas', 'Types', 'Event Protocol'],
    metadata: {
      techStack: ['Pydantic v2'],
      status: 'stable'
    }
  },
  'protocol-utils': {
    id: 'protocol-utils',
    title: 'Utility Tools (MCP, Hashing, Zip)',
    shortDescription: 'Helpers for MCP invocation, deterministic hashing, and safe zip operations.',
    purpose: 'Provides standalone MCPInvoker, object storage abstraction (MinIO/GCS), and atomic directory replacement.',
    category: 'protocol',
    parentId: 'protocol-layer',
    children: [],
    repositoryPath: 'vhl-agent-backend/vhl_protocol/utils',
    tags: ['MCP Invoker', 'Hashing', 'Zip', 'Object Storage'],
    metadata: {
      keyInterfaces: [
        'MCPInvoker',
        'compute_directory_hash()',
        'atomic_replace_directory()',
        'get_storage_client()'
      ],
      status: 'stable'
    }
  },
  'workspace-subsystem': {
    id: 'workspace-subsystem',
    title: 'Workspace Subsystem',
    shortDescription: 'Multi-worktree Git versioning and SQLite project state database.',
    purpose: 'Manages local workspace isolation via Git worktrees and persists project metadata/artifacts in SQLite.',
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
    tags: ['Subsystem', 'Workspace', 'Git', 'SQLite', 'Versioning'],
    metadata: {
      techStack: ['SQLite', 'Git Worktree', 'Python Pathlib'],
      authoritativeHost: 'Backend Local Workspace',
      status: 'stable'
    }
  },
  'workspace-manager': {
    id: 'workspace-manager',
    title: 'Workspace Manager',
    shortDescription: 'Core manager for file operations, git worktrees, and project state.',
    purpose: 'Orchestrates project creation, module setup, and directory synchronization across isolated Git worktrees.',
    category: 'storage',
    parentId: 'workspace-subsystem',
    children: [],
    repositoryPath: 'vhl-agent-backend/vhl_common/workspace_manager/manager.py',
    documentation: [
      {
        title: 'Workspace Manager Specification',
        path: 'vhl-agent-backend/docs/source/workspace_manager.md',
        description: 'Module and archive lifecycle management.'
      }
    ],
    tags: ['Filesystem', 'Git Worktree', 'Isolation'],
    metadata: {
      status: 'stable'
    }
  },
  'git-wrapper': {
    id: 'git-wrapper',
    title: 'Git & Worktree Manager',
    shortDescription: 'Multi-worktree Git version control integration.',
    purpose: 'Implements the "trunk branch approach" where modules have dedicated worktrees. Handles consolidation of modules into assemblies via Git merges.',
    category: 'storage',
    parentId: 'workspace-subsystem',
    children: [],
    repositoryPath: 'vhl-agent-backend/vhl_common/project_state_manager/git_wrapper.py',
    tags: ['Git', 'Worktree', 'Trunk Merge', 'Consolidation'],
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
  'aosm': {
    id: 'aosm',
    title: 'AOSM (Orchestration Engine)',
    shortDescription: 'High-level Agent Orchestration State Machine.',
    purpose: 'The top-level orchestrator of the system. It delegates specific multi-agent workflows to specialized controllers (e.g., Workflow 1 Controller) and manages the high-level project lifecycle.',
    category: 'subsystem',
    parentId: 'vhl-agent-backend',
    children: ['aosm-state-machine'],
    repositoryPath: 'vhl-agent-backend/aosm',
    documentation: [
      {
        title: 'Detailed Backend Architecture',
        path: 'vhl-agent-backend/docs/source/ARCHITECTURE.md',
        description: 'AOSM orchestration and supervisor-controller pattern.'
      }
    ],
    tags: ['Subsystem', 'AOSM', 'Orchestrator', 'Control Loop'],
    metadata: {
      techStack: ['Python', 'Asyncio'],
      status: 'stable'
    }
  },
  'aosm-state-machine': {
    id: 'aosm-state-machine',
    title: 'AOSM State Machine Engine',
    shortDescription: 'State machine for high-level system orchestration.',
    purpose: 'Governs high-level system states and transitions project lifecycle phases, delegating execution to the Supervisor and specialized controllers.',
    category: 'subsystem',
    parentId: 'aosm',
    children: [],
    repositoryPath: 'vhl-agent-backend/aosm/state_machine/aosm.py',
    tags: ['FSM', 'State Transitions', 'Control Loop', 'High-level Orchestrator'],
    metadata: {
      status: 'stable'
    }
  }
};
