export const ROLE_WEBUI = "vhl_webui";
export const ROLE_AGENT_BACKEND = "vhl_agent_backend";
export const ROLE_RUNTIME = "vhl_runtime";

export type VHLRole = typeof ROLE_WEBUI | typeof ROLE_AGENT_BACKEND | typeof ROLE_RUNTIME;
