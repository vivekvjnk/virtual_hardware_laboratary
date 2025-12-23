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
import { searchLibrary } from "./tools/searchLibrary.js";

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
    return {
      tools: [
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
            "List components explicitly added to the local library.",
          inputSchema: {
            type: "object",
            properties: {},
          },
        },
        {
          name: "search_library",
          description:
            "Search local and global libraries for components.",
          inputSchema: {
            type: "object",
            properties: {
              query: {
                type: "string",
                description: "Search query",
              },
              mode: {
                type: "string",
                enum: ["fuzzy", "regex"],
              },
              depth: {
                type: "string",
                enum: ["surface", "deep"],
              },
            },
            required: ["query", "mode", "depth"],
          },
        },
      ],
    };
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

        return jsonResult({
          success: true,
          component: result,
        });
      }

      case "list_local_components": {
        const components = await listLocalComponents();

        return jsonResult({
          components,
          count: components.length,
        });
      }

      case "search_library": {
        const { query, mode, depth } = args as {
          query: string;
          mode: "fuzzy" | "regex";
          depth: "surface" | "deep";
        };

        const matches = await searchLibrary(query, mode, depth);

        return jsonResult({
          query,
          mode,
          depth,
          results: matches,
          count: matches.length,
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
