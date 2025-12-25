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
import { resolveComponent } from "./tools/resolveComponent.js";

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
        name: "resolve_component",
        description:
          "Resolve a component into local imports. May require selection.",
        inputSchema: {
          type: "object",
          properties: {
            query: {
              type: "string",
              description: "Search query or full component name for selection. Always use approximate component name for search. Use specific component name only after verifying the search results. Eg: Search NE555(approximate query) --> System returns options [NE555, NE555P, NE555N] --> Import NE555P with specific query. NOTE: Never try to import standard passive components like R, C, L, etc.",
            },
          },
          required: ["query"],
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

      case "resolve_component": {
        const { query } = args as {
          query: string;
        };

        const result = await resolveComponent(query);
        console.log("resolveComponent Result:", result);
        return jsonResult(result);
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
