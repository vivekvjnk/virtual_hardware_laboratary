import { jest } from "@jest/globals";

// Mock paths
jest.unstable_mockModule("../../src/config/paths.js", () => ({
  LOCAL_LIBRARY_DIR: "/tmp/vhl-test/library/local",
  TEMP_DIR: "/tmp/vhl-test/.tmp",
  PROJECT_ROOT: process.cwd(),
  IMPORTS_DIR: "/tmp/vhl-test/imports",
}));

// Mock the resolveComponent tool
jest.unstable_mockModule("../../src/mcp/tools/resolveComponent.js", () => ({
  resolveComponent: (query: string, depth: string) => {
    return Promise.resolve({
      status: "resolved",
      component: "MockResistor",
      path: "/mock/path/MockResistor.tsx"
    });
  },
  clearSessions: () => { },
}));

// Now import the modules
const { createLibraryServer } = await import("../../src/mcp/server.js");
const { InMemoryTransport } = await import("@modelcontextprotocol/sdk/inMemory.js");

describe("MCP Server (via MCP InMemoryTransport)", () => {
  let clientTransport: any;
  let serverTransport: any;
  let server: any;
  let messages: any[] = [];

  beforeEach(async () => {
    messages = [];
    [clientTransport, serverTransport] =
      InMemoryTransport.createLinkedPair();

    clientTransport.onmessage = (msg: any) => {
      messages.push(msg);
    };

    server = createLibraryServer();
    await server.connect(serverTransport);
    await serverTransport.start();
  });

  async function waitForResponse(id: number, timeout = 2000): Promise<any> {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      const found = messages.find(m => m.id === id);
      if (found) return found;
      await new Promise(r => setTimeout(r, 50));
    }
    throw new Error(`Timeout waiting for response id ${id}. Messages: ${JSON.stringify(messages, null, 2)}`);
  }

  test("lists all expected tools", async () => {
    await clientTransport.send({
      jsonrpc: "2.0",
      id: 1,
      method: "tools/list",
      params: {},
    });

    const response = await waitForResponse(1);
    const toolNames = Object.values(response.result.tools).map(
      (t: any) => t.name
    );

    expect(toolNames).toEqual(
      expect.arrayContaining([
        "add_component",
        "list_local_components",
        "resolve_component",
      ])
    );
  });

  test("routes add_component tool call", async () => {
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

    const response = await waitForResponse(2);
    expect(response.result).toBeDefined();
    const content = response.result.content[0];
    expect(content.type).toBe("text");
    const payload = JSON.parse(content.text);
    expect(payload.success).toBe(true);
  });

  test("routes list_local_components tool call", async () => {
    await clientTransport.send({
      jsonrpc: "2.0",
      id: 3,
      method: "tools/call",
      params: {
        name: "list_local_components",
        arguments: {},
      },
    });

    const response = await waitForResponse(3);
    expect(response.result).toBeDefined();
    const payload = JSON.parse(response.result.content[0].text);
    expect(payload.components).toBeDefined();
  });

  test("routes resolve_component tool call", async () => {
    await clientTransport.send({
      jsonrpc: "2.0",
      id: 4,
      method: "tools/call",
      params: {
        name: "resolve_component",
        arguments: {
          query: "resistor",
          depth: "surface"
        },
      },
    });

    const response = await waitForResponse(4);
    expect(response.result).toBeDefined();
    const result = JSON.parse(response.result.content[0].text);
    expect(result.status).toBe("resolved");
    expect(result.component).toBe("MockResistor");
  });
});