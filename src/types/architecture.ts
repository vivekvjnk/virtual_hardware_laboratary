export type NodeCategory =
  | 'root'
  | 'subsystem'
  | 'infrastructure'
  | 'agent'
  | 'feature'
  | 'storage'
  | 'protocol'
  | 'controller'
  | 'gate';

export interface DocumentationLink {
  title: string;
  path: string;
  description?: string;
}

export interface ArchitectureNode {
  id: string;
  title: string;
  shortDescription: string;
  purpose: string;
  category: NodeCategory;
  parentId: string | null;
  children: string[];
  repositoryPath?: string;
  documentation?: DocumentationLink[];
  tags?: string[];
  // Future extensibility fields
  metadata?: {
    techStack?: string[];
    authoritativeHost?: string;
    keyInterfaces?: string[];
    status?: 'stable' | 'active' | 'evolving' | 'experimental';
    runtimeEvents?: string[];
  };
}

export interface ArchitectureGraphData {
  rootId: string;
  nodes: Record<string, ArchitectureNode>;
}
