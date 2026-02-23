
import { runAnaServer } from "./server.js";

runAnaServer().catch((err) => {
    console.error("ANA Commit MCP server failed:", err);
    process.exit(1);
});
