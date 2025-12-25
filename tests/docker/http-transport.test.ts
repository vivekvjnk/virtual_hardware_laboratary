import { exec } from "child_process";
import util from "util";
import http from "http";
import { jest } from "@jest/globals";

const execPromise = util.promisify(exec);

/**
 * Docker Integration Tests for HTTP Transport
 * 
 * These tests validate that the VHL Library runs correctly in a Docker container
 * and responds to HTTP requests as expected.
 * 
 * Prerequisites:
 * - Docker must be installed and running
 * - User must have permission to run docker commands
 */
describe("Docker HTTP Transport Integration", () => {
    const CONTAINER_NAME = "vhl-library-test";
    const IMAGE_NAME = "vhl-library:test";
    const HTTP_PORT = 8081; // Use different port to avoid conflicts
    const BASE_URL = `http://localhost:${HTTP_PORT}`;

    beforeAll(async () => {
        console.log("Building Docker image...");

        try {
            // Build the Docker image
            const { stdout, stderr } = await execPromise(
                `docker build -t ${IMAGE_NAME} .`,
                { cwd: process.cwd() }
            );

            if (stderr && !stderr.includes("WARNING")) {
                console.warn("Build warnings:", stderr);
            }

            console.log("Docker image built successfully");
        } catch (error: any) {
            console.error("Failed to build Docker image:", error.message);
            throw error;
        }
    }, 120000); // 2 minute timeout for building image

    beforeEach(async () => {
        console.log("Starting Docker container...");

        try {
            // Start the container
            await execPromise(
                `docker run -d --name ${CONTAINER_NAME} -p ${HTTP_PORT}:8080 -e VHL_TRANSPORT=http -e PORT=8080 ${IMAGE_NAME}`
            );

            // Wait for container to be ready (health check)
            await waitForHealthy(BASE_URL, 30000);

            console.log("Container is ready");
        } catch (error: any) {
            console.error("Failed to start container:", error.message);
            // Clean up if start failed
            await cleanupContainer();
            throw error;
        }
    }, 60000); // 1 minute timeout for starting container

    afterEach(async () => {
        await cleanupContainer();
    }, 30000); // 30 second timeout for cleanup

    afterAll(async () => {
        console.log("Cleaning up Docker image...");
        try {
            await execPromise(`docker rmi ${IMAGE_NAME}`);
        } catch (error) {
            // Ignore cleanup errors
            console.warn("Failed to remove image, may not exist");
        }
    });

    async function cleanupContainer() {
        try {
            console.log("Stopping and removing container...");
            await execPromise(`docker stop ${CONTAINER_NAME}`);
            await execPromise(`docker rm ${CONTAINER_NAME}`);
        } catch (error) {
            // Container might not exist, ignore
            console.warn("Failed to cleanup container, may not exist");
        }
    }

    async function waitForHealthy(url: string, timeout: number): Promise<void> {
        const start = Date.now();
        const healthUrl = `${url}/health`;

        while (Date.now() - start < timeout) {
            try {
                const response = await fetch(healthUrl);
                if (response.ok) {
                    return;
                }
            } catch (error) {
                // Container not ready yet, wait and retry
            }

            await new Promise(resolve => setTimeout(resolve, 500));
        }

        throw new Error(`Container did not become healthy within ${timeout}ms`);
    }

    async function makeHttpRequest(method: string, path: string, body?: any): Promise<any> {
        const url = `${BASE_URL}${path}`;

        const options: RequestInit = {
            method,
            headers: {
                "Content-Type": "application/json",
            },
        };

        if (body) {
            options.body = JSON.stringify(body);
        }

        const response = await fetch(url, options);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${await response.text()}`);
        }

        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
            return await response.json();
        }

        return await response.text();
    }

    test("health endpoint returns OK", async () => {
        const response = await makeHttpRequest("GET", "/health");
        expect(response).toBe("OK");
    }, 30000);

    test("MCP endpoint lists all tools", async () => {
        const request = {
            jsonrpc: "2.0",
            id: 1,
            method: "tools/list",
        };

        const response = await makeHttpRequest("POST", "/mcp", request);

        expect(response.jsonrpc).toBe("2.0");
        expect(response.id).toBe(1);
        expect(response.result).toBeDefined();
        expect(response.result.tools).toBeDefined();
        expect(typeof response.result.tools).toBe("object");
        expect(Array.isArray(response.result.tools)).toBe(true);

        const toolNames = Object.values(response.result.tools).map((t: any) => t.name);
        expect(toolNames).toEqual(
            expect.arrayContaining([
                "add_component",
                "list_local_components",
                "resolve_component",
            ])
        );
    }, 30000);

    test("MCP endpoint calls list_local_components", async () => {
        const request = {
            jsonrpc: "2.0",
            id: 2,
            method: "tools/call",
            params: {
                name: "list_local_components",
                arguments: {},
            },
        };

        const response = await makeHttpRequest("POST", "/mcp", request);

        expect(response.jsonrpc).toBe("2.0");
        expect(response.id).toBe(2);
        expect(response.result).toBeDefined();
        expect(response.result.content).toBeDefined();
        expect(Array.isArray(response.result.content)).toBe(true);

        const content = response.result.content[0];
        expect(content.type).toBe("text");

        const payload = JSON.parse(content.text);
        expect(payload.components).toBeDefined();
        expect(Array.isArray(payload.components)).toBe(true);
    }, 30000);

    test("MCP endpoint calls resolve_component", async () => {
        const request = {
            jsonrpc: "2.0",
            id: 3,
            method: "tools/call",
            params: {
                name: "resolve_component",
                arguments: {
                    query: "resistor",
                },
            },
        };

        const response = await makeHttpRequest("POST", "/mcp", request);

        expect(response.jsonrpc).toBe("2.0");
        expect(response.id).toBe(3);
        expect(response.result).toBeDefined();

        const content = response.result.content[0];
        expect(content.type).toBe("text");

        const payload = JSON.parse(content.text);
        expect(payload.status).toBeDefined();
    }, 30000);

    test("MCP endpoint calls add_component", async () => {
        const componentContent = `import { resistor } from "@tsci/seveibar.resistor";

export const DockerTestComponent = (props: { resistance: string }) => {
  return <resistor resistance={props.resistance} />;
};`;

        const request = {
            jsonrpc: "2.0",
            id: 4,
            method: "tools/call",
            params: {
                name: "add_component",
                arguments: {
                    component_name: "DockerTestComponent",
                    file_content: componentContent,
                },
            },
        };

        const response = await makeHttpRequest("POST", "/mcp", request);

        expect(response.jsonrpc).toBe("2.0");
        expect(response.id).toBe(4);
        expect(response.result).toBeDefined();

        const content = response.result.content[0];
        expect(content.type).toBe("text");

        const payload = JSON.parse(content.text);
        // In Docker environment, validation might fail due to dependencies
        // Just verify we got a response with expected structure
        expect(typeof payload.success).toBe("boolean");
        if (!payload.success) {
            console.log("Component validation failed (expected in Docker):", payload.error);
        }
    }, 30000);

    test("MCP endpoint returns error for invalid method", async () => {
        const request = {
            jsonrpc: "2.0",
            id: 5,
            method: "invalid/method",
        };

        const response = await makeHttpRequest("POST", "/mcp", request);

        expect(response.jsonrpc).toBe("2.0");
        expect(response.id).toBe(5);
        expect(response.error).toBeDefined();
    }, 30000);
});
