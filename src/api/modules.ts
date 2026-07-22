import type { CreateModuleRequest, CreateModuleResponse } from '../types/module';

const API_BASE = 'http://localhost:3022/api';

export async function createModule(payload: CreateModuleRequest): Promise<CreateModuleResponse> {
  const formData = new FormData();
  formData.append('name', payload.name);
  formData.append('description', payload.description);
  
  const resourceDescriptions = payload.resources.map(r => r.description);
  formData.append('resource_descriptions', JSON.stringify(resourceDescriptions));
  
  payload.resources.forEach((resource) => {
    formData.append('files', resource.file);
  });

  const response = await fetch(`${API_BASE}/projects/${payload.projectId}/modules`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.message || `Failed to create module: ${response.statusText}`);
  }

  return await response.json();
}
