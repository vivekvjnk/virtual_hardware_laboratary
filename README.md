# Virtual Hardware Laboratory (VHL) 🔧

A TypeScript-based Model Context Protocol (MCP) server for tscircuit-driven hardware design. VHL enables LLM agents to search, validate, and manage hardware components through a standardized API.

## 🎯 Overview

VHL Library provides:

- **Component Management**: Add, validate, and store TSX components and KiCAD footprints
- **Library Search**: Search both local and global (tscircuit) component libraries
- **Dual Transport**: Run locally via stdio or as a Docker service via HTTP
- **Automatic Validation**: TypeScript compilation and dependency checking
- **MCP Protocol**: Standardized interface for AI agent integration

## ⚡ Quick Start

### Local Development (stdio)

```bash
# Install dependencies
pnpm install

# Run the MCP server
pnpm run dev

# Run tests
pnpm test
```

### Docker Deployment (HTTP)

```bash
# Using Docker Compose (Recommended)
docker-compose up -d

# The service will be available at:
# http://localhost:8080/mcp

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

## 🐳 Docker Container Setup

### Prerequisites

- Docker and Docker Compose installed
- Node.js 20+ (for local development)

### Build and Run

#### Option 1: Docker Compose

```bash
# Build and start
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f vhl-library

# Stop and remove
docker-compose down
```

#### Option 2: Docker CLI

```bash
# Build the image
docker build -t vhl-library .

# Run the container
docker run -d \
  --name vhl-library \
  -p 8080:8080 \
  -v vhl-lib:/app/lib \
  -e VHL_TRANSPORT=http \
  -e PORT=8080 \
  vhl-library

# Check health
curl http://localhost:8080/health

# View logs
docker logs -f vhl-library

# Stop and remove
docker stop vhl-library && docker rm vhl-library
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VHL_TRANSPORT` | `stdio` | Transport mode: `stdio` (local) or `http` (Docker) |
| `PORT` | `8080` | HTTP server port (only for http transport) |
| `VHL_LIBRARY_DIR` | `/app/lib` | Directory for persistent component storage |

### Volume Persistence

The Docker container uses a named volume (`vhl-lib`) to persist components:

```bash
# Inspect the volume
docker volume inspect vhl-lib

# Backup the volume
docker run --rm -v vhl-lib:/data -v $(pwd):/backup alpine tar czf /backup/vhl-backup.tar.gz -C /data .

# Restore from backup
docker run --rm -v vhl-lib:/data -v $(pwd):/backup alpine tar xzf /backup/vhl-backup.tar.gz -C /data
```

## 📡 MCP Server API Reference

The VHL Library implements the Model Context Protocol (MCP) and exposes three tools via JSON-RPC 2.0.

### Transport Modes

#### stdio Transport (Local Development)
- Used by default when running locally
- Communication via stdin/stdout
- Best for testing, CI, and local development

#### HTTP Transport (Docker)
- Enabled when `VHL_TRANSPORT=http`
- RESTful JSON-RPC endpoint at `POST /mcp`
- Health check endpoint at `GET /health`
- Best for production deployments and remote access

### Tool 1: `add_component`

Add or update a TSX component or KiCAD footprint in the local library.

**Input Schema:**
```json
{
  "component_name": "string (required)",
  "file_content": "string (required)"
}
```

**Parameters:**
- `component_name`: Component name (e.g., `MyResistor`) or filename with extension (e.g., `footprint.kicad_mod`)
  - For TSX files: Name will have `.tsx` appended if not specified
  - For KiCAD files: Must end with `.kicad_mod`
- `file_content`: Complete file content (TSX or KiCAD footprint format)

**Validation Rules:**
- TSX files must be valid TypeScript with JSX
- TSX files must export at least one symbol
- TSX files importing `.kicad_mod` files must have those footprints already in the library
- KiCAD `.kicad_mod` files are accepted without compilation validation

**Response:**
```json
{
  "success": true,
  "componentPath": "/app/lib/MyResistor.tsx"
}
```

**Error Response:**
```json
{
  "success": false,
  "errors": [
    "Component must export at least one symbol"
  ]
}
```

**Example (HTTP):**
```bash
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "add_component",
      "arguments": {
        "component_name": "MyResistor",
        "file_content": "import { resistor } from \"@tsci/seveibar.resistor\";\n\nexport const MyResistor = (props: { resistance: string }) => {\n  return <resistor resistance={props.resistance} />;\n};"
      }
    }
  }'
```

### Tool 2: `list_local_components`

List all components in the local library.

**Input Schema:**
```json
{}
```

**Response:**
```json
[
  {
    "name": "MyResistor",
    "file": "MyResistor.tsx"
  },
  {
    "name": "MyCapacitor",
    "file": "MyCapacitor.tsx"
  }
]
```

**Example (HTTP):**
```bash
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "list_local_components",
      "arguments": {}
    }
  }'
```

### Tool 3: `search_library`

Search both local and global (tscircuit registry) libraries for components.

**Input Schema:**
```json
{
  "query": "string (required)",
  "mode": "fuzzy | regex (required)",
  "depth": "surface | deep (required)"
}
```

**Parameters:**
- `query`: Search query string
- `mode`: 
  - `fuzzy`: Case-insensitive substring matching
  - `regex`: Regular expression pattern matching
- `depth`:
  - `surface`: Returns only name and source
  - `deep`: Returns name, source, and additional metadata (exports, pins)

**Response (surface):**
```json
[
  {
    "name": "MyResistor",
    "source": "local",
    "description": "Custom resistor component"
  },
  {
    "name": "seveibar.resistor",
    "source": "global",
    "description": "Standard resistor - Stars: 42"
  }
]
```

**Response (deep):**
```json
[
  {
    "name": "MyResistor",
    "source": "local",
    "exports": ["default"]
  },
  {
    "name": "seveibar.resistor",
    "source": "global",
    "description": "Standard resistor",
    "exports": ["default"]
  }
]
```

**Example (HTTP):**
```bash
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "search_library",
      "arguments": {
        "query": "resistor",
        "mode": "fuzzy",
        "depth": "surface"
      }
    }
  }'
```

### List Available Tools

Query the server for all available tools:

**Request:**
```bash
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 0,
    "method": "tools/list"
  }'
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 0,
  "result": {
    "tools": [
      {
        "name": "add_component",
        "description": "Add or update a TSX component or KiCAD footprint (.kicad_mod) in the local library. Validation is automatic.",
        "inputSchema": { ... }
      },
      {
        "name": "list_local_components",
        "description": "List components explicitly added to the local library.",
        "inputSchema": { ... }
      },
      {
        "name": "search_library",
        "description": "Search local and global libraries for components.",
        "inputSchema": { ... }
      }
    ]
  }
}
```

## 🤖 LLM Agent Integration Guide

### Overview

VHL Library is designed to be used by LLM agents to manage hardware components. The MCP protocol provides a standardized interface that agents can use to:

1. Search for components in local and global libraries
2. Add new components with automatic validation
3. List existing local components
4. Manage component dependencies

### Integration Steps

#### Step 1: Connect to the MCP Server

Choose your transport based on deployment:

**Option A: stdio Transport (Local)**
```typescript
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { spawn } from 'child_process';

// Spawn the VHL server process
const serverProcess = spawn('node', ['dist/index.js'], {
  env: { ...process.env, VHL_TRANSPORT: 'stdio' }
});

// Create stdio transport
const transport = new StdioClientTransport({
  command: 'node',
  args: ['dist/index.js'],
  env: { VHL_TRANSPORT: 'stdio' }
});

// Connect client
const client = new Client({
  name: 'my-agent',
  version: '1.0.0'
}, {
  capabilities: {}
});

await client.connect(transport);
```

**Option B: HTTP Transport (Docker)**
```typescript
// Simple HTTP client example
async function callMCPTool(toolName: string, args: any) {
  const response = await fetch('http://localhost:8080/mcp', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      jsonrpc: '2.0',
      id: Date.now(),
      method: 'tools/call',
      params: {
        name: toolName,
        arguments: args
      }
    })
  });

  const result = await response.json();
  
  if (result.error) {
    throw new Error(result.error.message);
  }

  // Parse the text content
  const content = result.result.content[0];
  return JSON.parse(content.text);
}
```

#### Step 2: Discover Available Tools

```typescript
// Using HTTP
const toolsResponse = await fetch('http://localhost:8080/mcp', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    jsonrpc: '2.0',
    id: 1,
    method: 'tools/list'
  })
});

const tools = await toolsResponse.json();
console.log(tools.result.tools);
```

#### Step 3: Use the Tools

**Search for Components:**
```typescript
const searchResults = await callMCPTool('search_library', {
  query: 'resistor',
  mode: 'fuzzy',
  depth: 'surface'
});

console.log('Found components:', searchResults);
// [
//   { name: 'seveibar.resistor', source: 'global', description: '...' },
//   ...
// ]
```

**Add a Component:**
```typescript
const componentCode = `
import { resistor } from "@tsci/seveibar.resistor";

export const MyCustomResistor = (props: { resistance: string; power?: string }) => {
  return <resistor resistance={props.resistance} />;
};
`;

const result = await callMCPTool('add_component', {
  component_name: 'MyCustomResistor',
  file_content: componentCode
});

if (result.success) {
  console.log('Component added:', result.componentPath);
} else {
  console.error('Validation failed:', result.errors);
}
```

**Add a KiCAD Footprint:**
```typescript
const footprintContent = `(module MY_FOOTPRINT
  (layer F.Cu)
  (at 0 0)
  ...
)`;

const result = await callMCPTool('add_component', {
  component_name: 'my_custom_footprint.kicad_mod',
  file_content: footprintContent
});
```

**List Local Components:**
```typescript
const components = await callMCPTool('list_local_components', {});

console.log('Local library:', components);
// [
//   { name: 'MyCustomResistor', file: 'MyCustomResistor.tsx' },
//   ...
// ]
```

#### Step 4: Handle Component Dependencies

When adding TSX components that import KiCAD footprints, ensure the footprints are added first:

```typescript
// Step 1: Add the footprint
await callMCPTool('add_component', {
  component_name: 'custom.kicad_mod',
  file_content: footprintContent
});

// Step 2: Add the TSX component that uses it
const componentWithFootprint = `
import customFootprint from "./custom.kicad_mod";

export const MyComponent = () => {
  return <footprint footprint={customFootprint} />;
};
`;

await callMCPTool('add_component', {
  component_name: 'MyComponent',
  file_content: componentWithFootprint
});
```

### Agent Workflow Example

Here's a complete workflow for an agent creating a new component:

```typescript
class HardwareDesignAgent {
  async createComponent(userRequest: string) {
    // 1. Search for existing components
    const searchResults = await callMCPTool('search_library', {
      query: userRequest,
      mode: 'fuzzy',
      depth: 'deep'
    });

    // 2. If found, use existing component
    if (searchResults.length > 0) {
      return {
        found: true,
        component: searchResults[0]
      };
    }

    // 3. Generate new component code (using LLM)
    const generatedCode = await this.generateComponentCode(userRequest);

    // 4. Add to library with validation
    const result = await callMCPTool('add_component', {
      component_name: this.extractComponentName(generatedCode),
      file_content: generatedCode
    });

    // 5. Handle validation errors
    if (!result.success) {
      // Retry with fixed code
      const fixedCode = await this.fixValidationErrors(
        generatedCode,
        result.errors
      );
      
      return await callMCPTool('add_component', {
        component_name: this.extractComponentName(fixedCode),
        file_content: fixedCode
      });
    }

    return { created: true, path: result.componentPath };
  }
}
```

### Testing Your Agent

Use the provided test suite as a reference:

```bash
# Run MCP server tests
pnpm test tests/mcp/

# Run Docker integration tests
pnpm test tests/docker/
```

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────┐
│            LLM Agent / Client               │
│                                             │
│  • Component search & discovery             │
│  • Component generation                     │
│  • Validation & error handling              │
└─────────────────┬───────────────────────────┘
                  │
                  │ MCP Protocol (JSON-RPC 2.0)
                  │
        ┌─────────┴──────────┐
        │                    │
    stdio (local)       HTTP (Docker)
        │                    │
        └─────────┬──────────┘
                  │
┌─────────────────▼───────────────────────────┐
│         VHL Library MCP Server              │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │  Tool Handlers                      │   │
│  │  • add_component                    │   │
│  │  • list_local_components            │   │
│  │  • search_library                   │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │  Validation Engine                  │   │
│  │  • TypeScript compilation           │   │
│  │  • Export detection                 │   │
│  │  • Dependency checking              │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │  Library Manager                    │   │
│  │  • Local library (filesystem)       │   │
│  │  • Global search (tscircuit CLI)    │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

### Directory Structure

```
virtual_hardware_laboratory/
├── src/
│   ├── config/
│   │   └── paths.ts              # Path configuration
│   ├── library/
│   │   ├── local/                # Local component storage
│   │   └── validator.ts          # Component validation logic
│   ├── mcp/
│   │   ├── server.ts             # MCP server core
│   │   ├── tools/
│   │   │   ├── addComponent.ts   # Add component tool
│   │   │   ├── listLocal.ts      # List local components tool
│   │   │   └── searchLibrary.ts  # Search library tool
│   │   └── transport/
│   │       └── HttpServerTransport.ts  # HTTP transport
│   ├── runtime/
│   │   └── libraryFs.ts          # Filesystem operations
│   └── index.ts                  # Application entry point
├── tests/
│   ├── mcp/                      # MCP server tests
│   ├── library/                  # Validation tests
│   └── docker/                   # Docker integration tests
├── Dockerfile                    # Docker image definition
├── docker-compose.yml            # Docker Compose configuration
└── package.json                  # Dependencies and scripts
```

### Component Lifecycle

1. **Search**: Agent searches for components using `search_library`
2. **Generate**: If not found, agent generates component code
3. **Stage**: Component is written to temporary directory
4. **Validate**: TypeScript compilation and dependency checks
5. **Commit**: If valid, moved to local library directory
6. **Cleanup**: Temporary files removed

### Transport Abstraction

The MCP server core is transport-agnostic:
- **stdio**: Used for local development and testing
- **HTTP**: Used for Docker deployment
- Both transports use the same tool handlers and validation logic

## 🧪 Development

### Project Setup

```bash
# Clone the repository
git clone <repository-url>
cd virtual_hardware_laboratory

# Install dependencies
pnpm install

# Build the project
pnpm build
```

### Running Tests

```bash
# Run all tests
pnpm test

# Run specific test suite
pnpm test tests/mcp/server.test.ts

# Run with coverage
pnpm test --coverage
```

### Local Development Workflow

1. **Make changes** to source code in `src/`
2. **Run tests** to validate: `pnpm test`
3. **Build** the project: `pnpm build`
4. **Test locally** with stdio: `pnpm run dev`
5. **Test Docker build**: `docker build -t vhl-library .`
6. **Test Docker run**: `docker run -p 8080:8080 vhl-library`

### Adding New Tools

To add a new MCP tool:

1. Create tool handler in `src/mcp/tools/`
2. Define input schema and response type
3. Implement validation logic
4. Register in `src/mcp/server.ts`:
   - Add to `ListToolsRequestSchema` handler
   - Add to `CallToolRequestSchema` dispatcher
5. Add tests in `tests/mcp/`

### Code Style

- TypeScript strict mode enabled
- ES modules (ESM) throughout
- Async/await for asynchronous operations
- Comprehensive error handling

## 🐛 Troubleshooting

### Common Issues

#### "MCP stdio server cannot run in TTY mode"

**Cause**: Running the server directly in a terminal with stdio transport.

**Solution**: Either:
- Use HTTP transport: `VHL_TRANSPORT=http pnpm start`
- Run via MCP client that pipes stdin/stdout
- Use Docker deployment

#### Port Already in Use

**Cause**: Port 8080 is occupied by another service.

**Solution**:
```bash
# Check what's using the port
lsof -i :8080

# Use a different port
docker run -p 9090:8080 -e PORT=8080 vhl-library
```

#### Component Validation Fails

**Cause**: TypeScript compilation errors or missing dependencies.

**Solution**: Check the error messages in the response:
```typescript
{
  "success": false,
  "errors": [
    "Imported footprint not found in library: custom.kicad_mod. Please upload it first."
  ]
}
```

Add dependencies first, then retry.

#### Docker Container Won't Start

**Cause**: Various issues (port conflict, build failure, etc.)

**Solution**:
```bash
# Check container logs
docker logs vhl-library

# Check container status
docker ps -a

# Rebuild image
docker-compose build --no-cache
docker-compose up
```

#### Volume Data Lost

**Cause**: Using anonymous volumes or removing named volumes.

**Solution**: Always use named volumes in production:
```yaml
volumes:
  vhl-lib:
    driver: local
```

Backup regularly:
```bash
docker run --rm -v vhl-lib:/data -v $(pwd):/backup alpine \
  tar czf /backup/vhl-backup.tar.gz -C /data .
```

### Debug Mode

Enable verbose logging:

```bash
# Local
DEBUG=* pnpm run dev

# Docker
docker run -e DEBUG=* -p 8080:8080 vhl-library
```

### Health Checks

```bash
# HTTP health endpoint
curl http://localhost:8080/health

# List tools
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'

# Check Docker container health
docker inspect vhl-library | grep Health
```

## 📚 Additional Resources

- [Model Context Protocol (MCP) Documentation](https://modelcontextprotocol.io)
- [tscircuit Documentation](https://docs.tscircuit.com)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Docker Documentation](https://docs.docker.com)

## 📝 License

[Your License Here]

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## 📧 Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation in `/docs`
- Review test files for usage examples
