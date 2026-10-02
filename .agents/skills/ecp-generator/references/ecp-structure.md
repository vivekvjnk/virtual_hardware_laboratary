# ECP Structure Spec

## Directory layout

```text
package-name/
├── SKILL.md
├── tools/
│   ├── <tool_a>.py
│   └── <tool_b>.sh
└── references/
    ├── <deep-topic-1>.md
    └── <deep-topic-2>.md
```

Rules:

- `package-name` is lowercase, hyphenated, no spaces; it must equal the `name` field in `SKILL.md`'s
  frontmatter.
- `tools/` and `references/` are optional individually, but at least one must exist — a package with
  neither executable tools nor deep references is just operational knowledge and may not need the full
  ECP structure (a plain doc may suffice).
- Nested subfolders are fine inside `tools/` or `references/` for larger packages, but avoid nesting
  `SKILL.md` itself anywhere but the package root.

## Progressive disclosure levels

An agent consuming an ECP loads information in three stages, matching the ECP.md concept doc:

1. **Discovery** — the agent sees only the skill's `name` + `description` (frontmatter) when deciding
   whether the skill is relevant. This must be enough to trigger correctly without loading the rest.
2. **SKILL.md body** — loaded in full once the skill is selected. Contains everything needed for the
   common case: workflow, reasoning, verification.
3. **references/** — loaded on demand, only when the task needs that specific deep knowledge (e.g. a
   full API schema, an error-code table, background theory). Keeps the common-case context small.

`tools/` is not "loaded" as text — it's executed. Its documentation-of-use lives in `SKILL.md` /
`references/`, not duplicated inside the tool file itself (beyond minimal usage comments).

## Worked example

Given source material describing a `matrix_converter.py` script plus a doc explaining bookshelf-format
conversion rules, tolerances, and common failure modes:

```text
bookshelf-converter/
├── SKILL.md                     # when to convert, format assumptions, decision rules,
│                                 # how to verify a conversion succeeded
├── tools/
│   └── matrix_converter.py      # the actual conversion script
└── references/
    ├── format-spec.md           # full input/output format definition
    └── failure-modes.md         # catalog of edge cases and how to detect/handle them
```

`SKILL.md` would say, e.g.: "Use `tools/matrix_converter.py --in <file> --out <file>`. Before running,
confirm the input matches the format in
[references/format-spec.md](references/format-spec.md#header). After running, verify success by
checking row/column sums per [references/failure-modes.md](references/failure-modes.md#checksum)."
