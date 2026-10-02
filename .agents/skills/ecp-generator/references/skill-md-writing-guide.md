# Writing `SKILL.md`

## Frontmatter rules (Anthropic Agent Skill format)

```yaml
---
name: package-name
description: >
  Third-person description of what the capability does and precisely when to use it.
  Include concrete trigger phrases the user might say. Keep to <=1024 characters.
---
```

- `name`: lowercase, hyphenated, ≤64 chars, must match the containing folder name exactly.
- `description`: this is the *only* thing an agent sees during skill discovery (before deciding to load
  the rest of the file). It must let the agent correctly decide relevance without ambiguity. Include:
  - what the skill produces/does,
  - the situations/inputs that should trigger it,
  - a couple of example phrasings the user might use.
- No other frontmatter fields are required. Optional fields (`license`, `allowed-tools`, `metadata`)
  may be added only if the target agent runtime supports and needs them.

## Body template

```markdown
# <Package Title>

## Overview
One short paragraph: what capability this package provides and the core concept/model behind it.

## When to use this skill
Bullet list of concrete triggers. Include an explicit "do NOT use for X" if there's a common
near-miss case.

## Inputs / Prerequisites
What must exist before the workflow can run (files, credentials, environment, prior steps).

## Workflow
Numbered steps, each one actionable ("run X", "check Y", "decide Z if condition"). Embed reasoning
guidance inline at the decision points rather than as a separate disconnected list. Link to
`tools/<file>` and `references/<file>` where a step needs them, instead of inlining their full content.

## Verification
How to confirm the workflow succeeded. Concrete checks, expected outputs, or a checklist. Include
common failure signatures and what to do about each.

## Notes / Anti-patterns (optional)
Known pitfalls, edge cases, or explicitly out-of-scope situations.
```

## Style rules

- Keep `SKILL.md` short enough to read in under ~2 minutes for the common case — it's loaded in full on
  every trigger. Aim for the length of this guide's template filled in, not longer.
- Prefer imperative, numbered steps over long prose paragraphs.
- Every reasoning/decision statement should be phrased so it's directly actionable ("if input has no
  header row, use `--no-header`"), not vague ("headers can sometimes be tricky").
- Link to `references/*.md` using relative paths; never use absolute filesystem paths.
- Don't repeat the same instruction in two places in the file.

## Common mistakes

| Mistake | Fix |
|---|---|
| Description is vague ("helps with data stuff") | Name concrete inputs/outputs and trigger phrases |
| `SKILL.md` contains a full API reference table | Move table to `references/`, link to it |
| Reasoning rules buried in `references/` | Move them into `SKILL.md`'s Workflow section |
| No verification section | Add one — even a 3-item checklist is enough |
| Package name in frontmatter ≠ folder name | Rename one to match the other |
