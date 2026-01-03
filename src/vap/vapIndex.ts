import { runVapServer } from "./vapServer.js";

runVapServer().catch((err) => {
    console.error("VAP server failed:", err);
    process.exit(1);
});
