export interface ModuleResource {
  file: File;
  description: string;
}

export interface CreateModuleRequest {
  projectId: string;
  name: string;
  description: string;
  resources: ModuleResource[];
}

export interface CreateModuleResponse {
  success: boolean;
  moduleId: string;
  worktreePath: string;
  message?: string;
}

export interface Module {
  id: string;
  name: string;
  description: string;
  status: string;
  last_updated: string;
}
