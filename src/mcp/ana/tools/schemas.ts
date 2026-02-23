
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
