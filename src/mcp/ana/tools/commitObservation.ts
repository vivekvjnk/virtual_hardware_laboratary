
import { commitManager } from "../commitManager.js";
import { ObservationCommit } from "./schemas.js";

export async function commitObservation(payload: ObservationCommit) {
    return commitManager.addCommit("/mcp/observe", "commit_observation", payload, "OBSERVATION_MESSAGE");
}
