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
          "Add or update a TSX component in the local library. Validation is automatic.",
        inputSchema: {
          type: "object",
          properties: {
            component_name: {
              type: "string",
              description: "Logical name of the component",
            },
            file_content: {
              type: "string",
              description: "Complete TSX file content",
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

      const result = await addComponent(
        component_name,
        file_content
      );

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(result, null, 2),
          },
        ],
      };
    }

    case "list_local_components": {
      const result = await listLocalComponents();

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(result, null, 2),
          },
        ],
      };
    }

    case "search_library": {
      const { query, mode, depth } = args as {
        query: string;
        mode: "fuzzy" | "regex";
        depth: "surface" | "deep";
      };

      const result = await searchLibrary(
        query,
        mode,
        depth
      );

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(result, null, 2),
          },
        ],
      };
    }

    default:
      throw new Error(`Unknown tool: ${name}`);
  }
});

export async function runServer() {
  const transport =
    process.stdin.isTTY
      ? undefined
      : new (await import(
          "@modelcontextprotocol/sdk/server/stdio.js"
        )).StdioServerTransport();

  if (!transport) {
    throw new Error("Failed to initialize MCP transport");
  }

  await server.connect(transport);
}

export { server };
