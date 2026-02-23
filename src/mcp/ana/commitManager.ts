
import { ObservationCommit } from "./tools/schemas.js";

export interface CommitEntry {
    commit_id: number;
    timestamp: string;
    endpoint: string;
    tool_name: string;
    message: {
        type: string;
        payload: any;
        metadata: {
            timestamp: string;
            tool: string;
        };
    };
}

class CommitManager {
    private commitLog: CommitEntry[] = [];
    private commitCounter: number = 0;

    addCommit(endpoint: string, toolName: string, payload: any, targetChannel: string) {
        const timestamp = new Date().toISOString();

        const message = {
            type: targetChannel,
            payload: payload,
            metadata: {
                timestamp: timestamp,
                tool: toolName,
            },
        };

        const commitEntry: CommitEntry = {
            commit_id: this.commitCounter++,
            timestamp: timestamp,
            endpoint: endpoint,
            tool_name: toolName,
            message: message,
        };

        this.commitLog.push(commitEntry);
        return { status: "ACK", message: message };
    }

    getCommits(since?: number, endpoint?: string): CommitEntry[] {
        let commits = this.commitLog;
        if (since !== undefined) {
            commits = commits.filter(c => c.commit_id > since);
        }
        if (endpoint !== undefined) {
            commits = commits.filter(c => c.endpoint === endpoint);
        }
        return commits;
    }
}

export const commitManager = new CommitManager();
