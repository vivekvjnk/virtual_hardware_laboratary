import type { ArchitectureGraphData } from '../types/architecture';
import { systemNodes } from './architecture/systemNodes';
import { backendNodes } from './architecture/backendNodes';
import { runtimeNodes } from './architecture/runtimeNodes';
import { webuiNodes } from './architecture/webuiNodes';
import { userProjectNodes } from './architecture/userProjectNodes';

export const backendArchitectureData: ArchitectureGraphData = {
  rootId: 'vhl-system',
  nodes: {
    ...systemNodes,
    ...backendNodes,
    ...runtimeNodes,
    ...webuiNodes,
    ...userProjectNodes,
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
