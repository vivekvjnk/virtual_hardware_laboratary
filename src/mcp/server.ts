// NOTE: `Server` is deprecated in MCP SDK typings.
// This is the current stable API; migration will be trivial
// once the replacement is finalized.

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

import { addComponent } from "./tools/addComponent.js";
import { listLocalComponents } from "./tools/listLocal.js";
import {
  resolveComponentStart,
  resolveComponentStatus,
  resolveComponentSelect
} from "./tools/resolveComponent.js";
import { getComponent } from "./tools/getComponent.js";

import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { HttpServerTransport } from "./transport/HttpServerTransport.js";

/**
 * Helper: always return structured JSON for OpenHands
 */
function jsonResult(value: unknown) {
  let text: string;

  try {
    text = JSON.stringify(value, null, 2);
  } catch {
    text = String(value);
  }
  console.log("Tool result:", text);
  return {
    content: [
      {
        type: "text",
        text,
      },
    ],
  };
}

/**
 * Create and configure the VHL Library MCP Server.
 * This function isolates the server core from the transport.
 */
export function createLibraryServer(): Server {
  const server = new Server(
    {
      name: "vhl-library",
      version: "0.1.0",
    },
    {
      capabilities: {
        tools: {},
      },
    }
  );

  /**
   * Tool inventory
   */
  server.setRequestHandler(ListToolsRequestSchema, async () => {
    const tools = [
      {
        name: "add_component",
        description:
          "Add or update a TSX component or KiCAD footprint (.kicad_mod) in the local library. Validation is automatic.",
        inputSchema: {
          type: "object",
          properties: {
            component_name: {
              type: "string",
              description:
                "Logical name of the component (e.g. 'MyResistor') or filename with extension (e.g. 'footprint.kicad_mod')",
            },
            file_content: {
              type: "string",
              description:
                "Complete file content (TSX or KiCAD footprint)",
            },
          },
          required: ["component_name", "file_content"],
        },
      },
      {
        name: "list_local_components",
        description:
          "List components available in the local library.",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
      {
        name: "resolve_component_start",
        description: "PROCESS STEP 1: Start a component resolution process. This is a NON-BLOCKING operation that initiates a background process to resolve a hardware component. The process first checks the local library, then attempts to import from the global registry if not found. Returns immediately with a task_id and initial state 'checking_local'. You MUST poll resolve_component_status to monitor progress. Only ONE resolution task can be active at a time - attempting to start a second task will fail. Use this when you need to resolve/import a component that may not exist locally.",
        inputSchema: {
          type: "object",
          properties: {
            component_name: {
              type: "string",
              description: "Name of the component to resolve.",
            },
          },
          required: ["component_name"],
        },
      },
      {
        name: "resolve_component_status",
        description: "PROCESS STEP 2: Poll the current state of an active resolution task. Returns a status object with 'state' field that can be: 'checking_local' (searching local library), 'checking_global' (searching global registry), 'trying_import' (importing component), 'selection_required' (waiting for your selection - see resolve_component_select), 'finished' (success - contains 'location' and 'source' fields), or 'failed' (error - contains 'reason' field). When state is 'selection_required', the response includes a 'selection' object with 'selection_id', 'prompt', and 'options' array. You MUST poll this repeatedly (with delays) until the state changes from transient states. CRITICAL: Always check the state before taking action. NOTE: Tasks are automatically cleaned up when they reach 'finished' or 'failed' states, freeing the task slot for new resolutions.",
        inputSchema: {
          type: "object",
          properties: {
            task_id: {
              type: "string",
              description: "The task ID returned by resolve_component_start.",
            },
          },
          required: ["task_id"],
        },
      },
      {
        name: "resolve_component_select",
        description: "PROCESS STEP 3 (CONDITIONAL): Respond to an interactive prompt when status shows state='selection_required'. Use the 'selection_id' from the status response. For 'selected_option', provide a string that matches one of the options (substring matching is used). This is NON-BLOCKING - it returns immediately with state 'trying_import'. After calling this, you MUST resume polling resolve_component_status to monitor the import progress. ONLY call this when the current state is 'selection_required', otherwise it will fail. Example: if options are ['[jlcpcb] NE555DR (C7593),[jlcpcb] NE555DR (C695838), [jlcpcb] NE555 (C5125085)], you can select '[jlcpcb] NE555 (C5125085)' or the full string.",
        inputSchema: {
          type: "object",
          properties: {
            task_id: {
              type: "string",
              description: "The task ID.",
            },
            selection_id: {
              type: "string",
              description: "The selection ID from the status payload.",
            },
            selected_option: {
              type: "string",
              description: "The option string to select.",
            },
          },
          required: ["task_id", "selection_id", "selected_option"],
        },
      },
      {
        name: "get_component",
        description: "Get pinout details of a device available under local library directory in VHL Librarian. Returns a list of 'pin:label' mappings in text format.",
        inputSchema: {
          type: "object",
          properties: {
            device_name: {
              type: "string",
              description: "Name of the device (e.g. 'BQ79616PAPR')",
            },
          },
          required: ["device_name"],
        },
      },
    ];

    // Convert to dictionary for protocol conformance
    const toolsMap = tools.reduce((acc, tool) => {
      acc[tool.name] = tool;
      return acc;
    }, {} as Record<string, any>);

    // return {
    //   tools: toolsMap,
    // } as any;
    return {
      tools: tools,
    }
  });

  /**
   * Tool dispatcher
   */
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    console.log("Tool request:", { name, args });

    switch (name) {
      case "add_component": {
        const { component_name, file_content } = args as {
          component_name: string;
          file_content: string;
        };

        const result = await addComponent(component_name, file_content);
        console.log("addComponent Result:", result);
        return jsonResult({
          success: true,
          component: result,
        });
      }

      case "list_local_components": {
        const components = await listLocalComponents();
        console.log("listLocalComponents Result:", components);
        return jsonResult({
          components,
          count: components.length,
        });
      }

      case "resolve_component_start": {
        const { component_name } = args as { component_name: string };
        const result = await resolveComponentStart(component_name);
        return jsonResult(result);
      }

      case "resolve_component_status": {
        const { task_id } = args as { task_id: string };
        const result = await resolveComponentStatus(task_id);
        return jsonResult(result);
      }

      case "resolve_component_select": {
        const { task_id, selection_id, selected_option } = args as {
          task_id: string;
          selection_id: string;
          selected_option: string;
        };
        const result = await resolveComponentSelect(task_id, selection_id, selected_option);
        return jsonResult(result);
      }

      case "get_component": {
        const { device_name } = args as { device_name: string };
        const result = await getComponent(device_name);
        return jsonResult({
          pinout_details: result,
        });
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  });

  return server;
}

// Export a singleton for backward compatibility
export const server = createLibraryServer();

export async function runServer() {
  const transportType = process.env.VHL_TRANSPORT || "stdio";
  const serverInstance = createLibraryServer();

  if (transportType === "http") {
    const port = parseInt(process.env.PORT || "8080", 10);
    const transport = new HttpServerTransport(port);
    await serverInstance.connect(transport);
    console.error(`VHL Library Server running on HTTP port ${port}`);
  } else {
    if (process.stdin.isTTY) {
      throw new Error(
        "MCP stdio server cannot run in TTY mode.\n" +
        "Start this server from an MCP client or pipe stdin."
      );
    }

    const transport = new StdioServerTransport();
    await serverInstance.connect(transport);
  }
}
