---
name: tsci-component-resolver
description: Resilient, agent-ready component resolution, verification, and scaffolding tool wrapping tscircuit and JLCPCB. Solves false 0 exit codes, eliminates TTY blocking, enforces network timeouts, ranks by package and stock, and automatically relocates imported parts to components/.
license: Apache-2.0
metadata:
  author: MOSAIC-Team
  version: "1.0"
  category: component-procurement
  tags:
    - tscircuit
    - jlcpcb
    - component-resolver
    - footprint
    - procurement
---

# TSCI Component Resolver

## Overview

The `tsci-component-resolver` capability package wraps the underlying `tsci` CLI with a robust, production-grade interface designed specifically for autonomous software agents. It addresses the critical reliability failure modes of raw CLI execution:
1. **False Exit Code Elimination**: Accurately maps "No results found" outputs (which raw `tsci` returns as exit code 0) to standard error code `1`.
2. **Network Timeout Guardrails**: Enforces a strict 10s search timeout and 30s import timeout, preventing agent subprocess hangs.
3. **Automated File Relocation**: Automatically validates generated TSX syntax and moves parts from `imports/` to `components/<Name>.tsx`.
4. **Intelligent Search & Ranking**: Filters by package type (`SOIC-8`, `TSSOP-8`, `QFN`) and ranks in-stock preferred parts.
5. **Fallback Scaffolding**: Provides clean, valid tscircuit React component scaffolding when a specialized part is missing from JLCPCB.

---

## Tool Assets & Execution

| Tool | Subcommand | Purpose | Key Parameters |
|---|---|---|---|
| `tools/component_resolver` | `search` | Search JLCPCB parts with stock & package ranking | `<query> [--package <pkg>] [--min-stock <N>] [--json]` |
| `tools/component_resolver` | `import` | Import part, verify syntax, move to `components/` | `<query_or_C_code> [--dest-dir <dir>] [--json]` |
| `tools/component_resolver` | `scaffold` | Scaffold custom tscircuit React component | `<name> [--footprint <fp>] [--pins <p1,p2...>] [--dest-dir <dir>]` |
| `tools/component_resolver` | `verify` | Verify TSX component syntax & chip definition | `<file_path> [--json]` |

### Exit Codes
- `0`: Success (component found, imported, or verified).
- `1`: Component not found or syntax verification failed.
- `2`: Network connection error (unable to reach registry API).

---

## Invocation Patterns & Examples

### Pattern 1: Search for an IC with Package Filtering
```bash
.agents/skills/tsci-component-resolver/tools/component_resolver search NE555 --package SOIC-8 --json
```
Output:
```json
{
  "query": "NE555",
  "status": "success",
  "total_found": 3,
  "results": [
    {
      "lcsc": 7593,
      "mfr": "NE555DR",
      "package": "SOIC-8",
      "stock": 209450,
      "price": 0.1263,
      "is_preferred": true
    }
  ]
}
```

### Pattern 2: Import by Exact JLCPCB Part ID
```bash
.agents/skills/tsci-component-resolver/tools/component_resolver import C2040 --dest-dir ./components
```
Output:
```text
✔ Successfully imported RP2040 (from C2040) -> /path/to/components/RP2040.tsx
```

### Pattern 3: Fallback Scaffolding for Missing Custom ICs
If a part is not available on JLCPCB or the registry:
```bash
.agents/skills/tsci-component-resolver/tools/component_resolver scaffold BQ79616 \
  --footprint tssop32 \
  --pins VCC,GND,IN_P,IN_N,OUT_P,OUT_N,FAULT,CS \
  --dest-dir ./components
```

### Pattern 4: Verifying Component Syntax
```bash
.agents/skills/tsci-component-resolver/tools/component_resolver verify ./components/RP2040.tsx
```

---

## Operating Invariants & Strict Boundaries

1. **Non-Interactive Execution**: Every call uses closed stdin (`DEVNULL`). It will never prompt for user cursor selection or block on terminal inputs.
2. **Deterministic Placement**: Components are placed into `components/<Name>.tsx` (or specified `--dest-dir`).
3. **Explicit Syntax Guard**: Every imported or scaffolded component must export a valid component with a `<chip ... />` declaration and defined `pinLabels`.
