---
name: ecp-generator
description: Generates an Engineering Capability Package (ECP) — a SKILL.md-based bundle of tools, operational knowledge, reasoning guidance, and verification steps — from source material such as a markdown document, tool docs, scripts, or APIs with clear operating instructions. Use when the user asks to "create an ECP", "package this as a skill/capability", "turn this documentation into an agent skill", or hands over instructions/scripts/tool references that should become a reusable, progressively-disclosed capability.
metadata:
  version: "0.1"
  author: MOSAIC-Team
---

# ECP Generator

## Overview

An Engineering Capability Package (ECP) turns a raw executable mechanism (script, CLI, API, MCP tool)
into a capability an agent can reason about and apply correctly. The core model:

```text
Tool     → Execute   (the script/CLI/API itself)
Knowledge → Explain   (how it works, its constraints)
Skill    → Enable     (when/why/how to use it, decision rules, success criteria)
Agent    → Reason     (chooses and applies the Skill)
```

An ECP always has three parts:

```text
package-name/
├── SKILL.md          # operational knowledge + reasoning + workflow + verification
├── tools/             # executable mechanisms (scripts, wrappers, CLIs)
└── references/        # deep, tool-specific knowledge loaded only when needed
```

See [references/ecp-structure.md](references/ecp-structure.md) for the full structural spec and a
worked example.

## When to use this skill

Use this skill whenever the input is one of:

- A markdown document (or set of docs) describing how to operate a tool, script, or workflow.
- A script/CLI/API plus scattered notes on how and when to use it.
- An existing loose collection of "tool wrappers" that should be consolidated into a reusable capability.

Do **not** use this skill just to write a single generic how-to doc, create a one-off script, or
document something with no reusable operational/reasoning content — that doesn't need a package.

## Inputs this skill expects

Before scaffolding, gather (ask the user if missing):

1. **Source material** — the markdown/doc/script(s) containing instructions, decision logic, and tool details.
2. **Package name** — short, lowercase, hyphenated (e.g. `matrix-converter`, `cypress-tuning`). Must match the folder name.
3. **Target location** — where the package should live (e.g. a `skills/` folder in the workspace).
4. **Executable assets** — any scripts/binaries that belong in `tools/`, if they exist already.

If any of these are unclear or missing, ask concise clarifying questions rather than guessing package
scope or name.

## Workflow

### Step 1 — Inventory the source material

Read all provided material fully. While reading, tag every piece of content into exactly one of four
buckets (a piece of content should not be duplicated across buckets):

| Bucket | Question it answers | Goes into |
|---|---|---|
| **Tools** | "What executable thing runs?" | `tools/` |
| **Operational knowledge** | "How do I call it correctly? What are its inputs/outputs/constraints?" | `SKILL.md` (or `references/` if long) |
| **Reasoning guidance** | "When/why should I use it vs. alternatives? What decisions does the agent need to make?" | `SKILL.md` |
| **Verification** | "How do I know it worked? What does failure look like?" | `SKILL.md` |

Use [references/extraction-checklist.md](references/extraction-checklist.md) to do this classification
systematically — it lists concrete signals for each bucket.

### Step 2 — Decide package name and scope

- One ECP = one coherent capability (e.g. "convert a bookshelf layout", not "everything about layout").
- If the source material covers multiple unrelated capabilities, split into multiple ECPs rather than
  one oversized package.
- Name must be lowercase-hyphenated and match the directory name.

### Step 3 — Scaffold the directory

Create the structure directly (create_file / create_directory), or if scaffolding many packages at
once, use [scripts/scaffold_ecp.py](scripts/scaffold_ecp.py):

```powershell
python skills/ecp-generator/scripts/scaffold_ecp.py --name <package-name> --dest <target-dir>
```

This produces the empty `SKILL.md`, `tools/`, and `references/` skeleton — content still needs writing.

### Step 4 — Write `SKILL.md`

Follow the Anthropic Agent Skill format:

- YAML frontmatter with exactly `name` and `description` (description is third-person, states **what**
  the capability does and **when** to use it, includes trigger phrases, ≤1024 chars).
- Body sections, in this order: Overview → When to use → Inputs/Prerequisites → Workflow (numbered,
  actionable steps) → Verification → (optional) Anti-patterns/Notes → links to `references/`.
- Keep `SKILL.md` itself short — it is loaded in full whenever the skill triggers (progressive
  disclosure level 2). Move anything long, tool-specific, or rarely needed into `references/` and link
  to it instead of inlining it.

Full writing guidance and a copy-pasteable template are in
[references/skill-md-writing-guide.md](references/skill-md-writing-guide.md).

### Step 5 — Populate `tools/`

- Move or create the executable scripts/wrappers referenced by the operational knowledge.
- Each tool should be runnable on its own (clear CLI args or function signature) — `SKILL.md` explains
  *when/why* to call it, the tool itself just executes.
- Do not embed reasoning logic inside tool scripts; keep decision-making in `SKILL.md`.

### Step 6 — Populate `references/`

- One file per deep topic (e.g. `references/api-schema.md`, `references/error-codes.md`).
- This is where large tables, full API specs, edge-case catalogs, and background theory go.
- `SKILL.md` should link to these files by relative path rather than inlining their content.

### Step 7 — Verify the package

Before considering the ECP done, confirm all of the following:

- [ ] `SKILL.md` frontmatter has valid `name`/`description`, name matches folder name.
- [ ] Every executable mechanism mentioned has a corresponding file under `tools/`.
- [ ] Every decision point ("when to use X vs Y", "what to do on failure") is captured as reasoning
      guidance in `SKILL.md`, not left implicit in the source material.
- [ ] `SKILL.md` includes an explicit verification/success-criteria section.
- [ ] No large reference material is inlined in `SKILL.md` — it's linked from `references/` instead.
- [ ] Nothing from the source material was silently dropped; anything intentionally omitted is noted.

If any box fails, return to the relevant step rather than shipping an incomplete package.

## Output

Report back to the user: the final directory tree, a one-line summary of the capability, and any
clarifications/assumptions made (e.g., content that was ambiguous and how it was classified).
