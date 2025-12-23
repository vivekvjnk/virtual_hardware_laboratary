import { jest } from "@jest/globals";

// Mock paths to use isolated directories for this test suite
jest.mock("../../src/config/paths.js", () => {
    const original = jest.requireActual("../../src/config/paths.js") as any;
    const path = require("path");

    // Create a unique ID for this test suite run
    const TEST_ID = "protocol_fix_" + Math.random().toString(36).substring(7);
    const TEST_ROOT = path.join(original.PROJECT_ROOT, ".test_env", TEST_ID);

    return {
        ...original,
        LOCAL_LIBRARY_DIR: path.join(TEST_ROOT, "library", "local"),
        TEMP_DIR: path.join(TEST_ROOT, ".tmp"),
    };
});

import { server } from "../../src/mcp/server.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";

describe("MCP Protocol Conformance", () => {
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

    test("tools/list returns a dictionary (object map), not an array", async () => {
        const responsePromise = nextMessage();

        await clientTransport.send({
            jsonrpc: "2.0",
            id: 1,
            method: "tools/list",
            params: {},
        });

        const response = await responsePromise;
        const tools = response.result.tools;

        // User requirement: tools must be an object map
        expect(typeof tools).toBe("object");
        expect(Array.isArray(tools)).toBe(false);

        // Verify keys exist
        expect(tools).toHaveProperty("add_component");
        expect(tools).toHaveProperty("list_local_components");
        expect(tools).toHaveProperty("resolve_component");

        // Verify structure of a tool
        expect(tools["list_local_components"]).toHaveProperty("name", "list_local_components");
    });
});
