
export interface ObservationCommit {
    issue_kind: "NONE" | "LOCAL" | "NON_LOCAL" | "INTENT_MISMATCH";
    confidence: number;
    observations: string;
}

export const ObservationCommitSchema = {
    type: "object",
    properties: {
        issue_kind: {
            type: "string",
            enum: ["NONE", "LOCAL", "NON_LOCAL", "INTENT_MISMATCH"],
            description: "Classification of the observed issue. LOCAL denotes deterministic, isolated, unambiguous failures confined to a narrow scope. NON_LOCAL denotes all other failures, including structural, hub-centric, ripple effects, or cases with ambiguity or low confidence. INTENT_MISMATCH denotes contradiction or ambiguity against explicit SCUD guarantees. NONE denotes no detected issue."
        },
        confidence: {
            type: "number",
            minimum: 0.0,
            maximum: 1.0,
            description: "Confidence level of the classification (0.0 to 1.0)."
        },
        observations: {
            type: "string",
            description: "All observations on the error/s in simple string format."
        }
    },
    required: ["issue_kind", "confidence", "observations"]
};

export const VapEvaluationSchema = {
    type: "object",
    properties: {
        circuit_name: {
            type: "string",
            description: "Name of the circuit to evaluate (without extension)."
        },
        blob_id: {
            type: "string",
            description: "The MinIO blob ID of the circuit code artifact."
        },
        iteration_id: {
            type: "string",
            description: "Optional iteration ID for context."
        }
    },
    required: ["circuit_name", "blob_id"]
};

export const VapDecisionSchema = {
    type: "object",
    properties: {
        task_id: {
            type: "string",
            description: "The unique task ID for the evaluation session."
        },
        decision: {
            type: "string",
            enum: ["ACCEPT", "REJECT"],
            description: "The final decision on whether to commit the circuit changes."
        }
    },
    required: ["task_id", "decision"]
};

