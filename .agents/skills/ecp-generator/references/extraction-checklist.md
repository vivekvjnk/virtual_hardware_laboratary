# Extraction Checklist

Use this while reading source material to sort content into the four ECP buckets. For each paragraph,
code block, or table in the source, ask these signal questions in order — the first one that matches
decides the bucket.

## 1. Tools bucket

Signals:

- It's a script, function, CLI command, API endpoint, or MCP tool definition.
- It has a callable signature (args, flags, request/response shape).
- Removing the prose around it would still leave something directly executable.

Action: extract the executable artifact itself into `tools/`. If the source only *describes* a tool
that doesn't exist yet as code, note that a tool needs to be created and flag it to the user — don't
fabricate a script that wasn't provided or requested.

## 2. Operational knowledge bucket

Signals:

- Explains *how* to call a tool correctly: required inputs, output format, preconditions, config.
- Describes formats, schemas, units, constraints, environment setup.
- Answers "what do I need to know to use this without guessing?"

Action: short/critical items go directly in `SKILL.md` (inline, near the relevant workflow step). Long
items (full schemas, big tables, exhaustive parameter lists) go to a dedicated file in `references/` and
are linked from `SKILL.md`.

## 3. Reasoning guidance bucket

Signals:

- Contains words like "if", "when", "prefer", "instead of", "unless", "only if", "avoid".
- Compares two or more options / tools / approaches.
- Describes a decision an agent must make that isn't purely mechanical.

Action: always goes into `SKILL.md` directly (never buried in `references/`) — this is the highest-value
content and must be visible without extra lookups. Phrase as explicit rules or a short decision
table/tree.

## 4. Verification bucket

Signals:

- Describes what "success" looks like, expected outputs, sanity checks.
- Describes failure modes, error messages, how to detect them.
- Any testing/validation step mentioned after an operation.

Action: consolidate into an explicit "Verification" section in `SKILL.md`. If failure modes are
extensive, keep a short summary in `SKILL.md` and move the full catalog to
`references/failure-modes.md` (or similar), linked from the Verification section.

## Content that fits none of the buckets

- Pure background/motivation with no operational impact → keep out of the ECP, or compress to one
  sentence in the Overview.
- Marketing-style or redundant restatement of the same fact → drop.
- If genuinely unsure, ask the user rather than guessing; note the ambiguity in the final report.

## Anti-patterns to avoid while extracting

- Don't duplicate the same fact in both `SKILL.md` and a `references/` file — link, don't copy.
- Don't let reasoning guidance leak into `tools/` as code comments or CLI help text only — it must be
  visible in `SKILL.md`.
- Don't inline a full API/schema reference in `SKILL.md` "just in case" — that defeats progressive
  disclosure and bloats every invocation of the skill.
