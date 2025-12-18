import { server } from "../../src/mcp/server.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";

describe("MCP Server (via MCP InMemoryTransport)", () => {
  let clientTransport: InMemoryTransport;
  let serverTransport: InMemoryTransport;
  
  function nextMessage(): Promise<any> {
    return new Promise((resolve) => {
      clientTransport.onmessage = (message) => {
        resolve(message);
      };
    });
  }

  beforeEach(async () => {
    [clientTransport, serverTransport] =
      InMemoryTransport.createLinkedPair();
      
    await server.connect(serverTransport);
    await serverTransport.start();
    

  });
    
  async function flush() {
    await Promise.resolve();
  }

  test("lists all expected tools", async () => {
    const responsePromise = nextMessage();

    await clientTransport.send({
      jsonrpc: "2.0",
      id: 1,
      method: "tools/list",
      params: {},
    });

    const response = await responsePromise;

    const toolNames = response.result.tools.map(
      (t: any) => t.name
    );

    expect(toolNames).toEqual(
      expect.arrayContaining([
        "add_component",
        "list_local_components",
        "search_library",
      ])
    );
  });

  test("routes add_component tool call", async () => {
    const responsePromise = nextMessage();

    await clientTransport.send({
      jsonrpc: "2.0",
      id: 2,
      method: "tools/call",
      params: {
        name: "add_component",
        arguments: {
          component_name: "MCPTestComponent",
          file_content: `export const MCPTestComponent = () => null;`,
        },
      },
    });

    const response = await responsePromise;
    const content = response.result.content[0];

    expect(content.type).toBe("text");

    const payload = JSON.parse(content.text);
    expect(payload.success).toBe(true);
  });

  test("routes list_local_components tool call", async () => {
    const responsePromise = nextMessage();

    await clientTransport.send({
      jsonrpc: "2.0",
      id: 3,
      method: "tools/call",
      params: {
        name: "list_local_components",
        arguments: {},
      },
    });

    const response = await responsePromise;
    const payload = JSON.parse(response.result.content[0].text);

    expect(Array.isArray(payload)).toBe(true);
  });

  test("routes search_library tool call", async () => {
    const responsePromise = nextMessage();

    await clientTransport.send({
      jsonrpc: "2.0",
      id: 4,
      method: "tools/call",
      params: {
        name: "search_library",
        arguments: {
          query: "res",
          mode: "fuzzy",
          depth: "surface",
        },
      },
    });

    const response = await responsePromise;
    const payload = JSON.parse(response.result.content[0].text);
    expect(Array.isArray(payload)).toBe(true);
  });
});