import fs from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";

async function renderCardTemplate(
    templatePath: string,
    replacements: Record<string, string>
): Promise<any> {
    let content = await fs.readFile(templatePath, "utf-8");
    for (const [key, val] of Object.entries(replacements)) {
        content = content.replaceAll(`{{${key}}}`, val);
    }
    return JSON.parse(content);
}

/**
 * Scaffolds an autonomous MOSAIC Agent Cluster inside a module worktree.
 * Creates the .agents/ directory tree, symlinks canonical VHL skills,
 * generates module-scoped declarative Agent Cards, and establishes the synthesis workflow contract.
 *
 * @param worktreePath - Absolute path to the module worktree
 * @param moduleName - Name of the hardware module
 * @param projectId - Project identifier
 * @param runtimeRoot - Root directory of vhl-runtime-mosaic where canonical skills reside
 */
export async function scaffoldModuleCluster(
    worktreePath: string,
    moduleName: string,
    projectId: string,
    runtimeRoot: string
): Promise<void> {
    const agentsDir = path.join(worktreePath, ".agents");
    const wellKnownDir = path.join(agentsDir, "well_known");
    const skillsDir = path.join(agentsDir, "skills");
    const workflowsDir = path.join(agentsDir, "workflows");
    const sessionsDir = path.join(agentsDir, "sessions");
    const tasksDir = path.join(agentsDir, "tasks");

    // 1. Create standard .agents/ directory structure
    await fs.mkdir(wellKnownDir, { recursive: true });
    await fs.mkdir(skillsDir, { recursive: true });
    await fs.mkdir(workflowsDir, { recursive: true });
    await fs.mkdir(sessionsDir, { recursive: true });
    await fs.mkdir(tasksDir, { recursive: true });

    // 2. Provision ground-up module ECPs from templates/ecp into module worktree
    const moduleEcps = [
        "module-synthesis-workflow",
        "module-cluster-orchestrator",
        "schematic-asset-analyst",
        "component-procurement-workflow",
        "tsci-component-resolver",
        "vhl-workspace-ops"
    ];

    const ecpTemplatesDir = path.join(runtimeRoot, "templates", "ecp");
    for (const ecp of moduleEcps) {
        const sourceEcpPath = path.join(ecpTemplatesDir, ecp);
        const targetEcpPath = path.join(skillsDir, ecp);

        if (existsSync(sourceEcpPath)) {
            try {
                const stat = await fs.lstat(targetEcpPath).catch(() => null);
                if (stat && stat.isSymbolicLink()) {
                    await fs.unlink(targetEcpPath);
                }
                if (!existsSync(targetEcpPath)) {
                    await fs.cp(sourceEcpPath, targetEcpPath, { recursive: true });
                }
            } catch (err: any) {
                console.warn(`[clusterScaffolding] Warning provisioning ECP '${ecp}' to ${targetEcpPath}:`, err.message);
            }
        }
    }

    // Provision canonical skills into module worktree as standalone directories (no symlinks)
    const canonicalSkills = [
        "a2a-peer-dialing",
        "vhl-circuit-evaluator",
        "vhl-component-resolver",
        "vhl-workspace-ops"
    ];

    for (const skill of canonicalSkills) {
        const sourceSkillPath = path.join(runtimeRoot, ".agents", "skills", skill);
        const targetSkillPath = path.join(skillsDir, skill);

        if (existsSync(sourceSkillPath)) {
            try {
                const stat = await fs.lstat(targetSkillPath).catch(() => null);
                if (stat && stat.isSymbolicLink()) {
                    await fs.unlink(targetSkillPath);
                }
                if (!existsSync(targetSkillPath)) {
                    await fs.cp(sourceSkillPath, targetSkillPath, { recursive: true });
                }
            } catch (err: any) {
                console.warn(`[clusterScaffolding] Warning provisioning skill '${skill}' to ${targetSkillPath}:`, err.message);
            }
        }
    }

    // 3. Generate module-scoped declarative Agent Cards from templates
    const templatesDir = path.join(runtimeRoot, "templates", "agent_cards");
    const replacements = { moduleName, projectId };

    const archyCard = await renderCardTemplate(path.join(templatesDir, "archy.json"), replacements);
    const librarianCard = await renderCardTemplate(path.join(templatesDir, "librarian.json"), replacements);
    const anaCard = await renderCardTemplate(path.join(templatesDir, "ana.json"), replacements);

    await fs.writeFile(
        path.join(wellKnownDir, "archy.json"),
        JSON.stringify(archyCard, null, 2),
        "utf-8"
    );
    await fs.writeFile(
        path.join(wellKnownDir, "librarian.json"),
        JSON.stringify(librarianCard, null, 2),
        "utf-8"
    );
    await fs.writeFile(
        path.join(wellKnownDir, "ana.json"),
        JSON.stringify(anaCard, null, 2),
        "utf-8"
    );

    // 4. Generate declarative workflow contract
    const workflowContent = `# Module Synthesis Workflow Contract: ${moduleName}

> **Project:** ${projectId}  
> **Module Worktree:** ${worktreePath}  
> **Architecture:** MOSAIC Multi-Cluster Autonomous Triad  

---

## 1. Cluster Roles & Responsibilities

- **Lead Orchestrator (\`archy\`)**: Directs the synthesis lifecycle, translates visual and boundary requirements into \`${moduleName}.scud\`, and coordinates domain workers.
- **Component Specialist (\`librarian\`)**: Ingests the SCUD component inventory, resolves footprints, and populates \`${moduleName}/Workspace/imports/\`.
- **Circuit Implementer (\`ana\`)**: Generates \`${moduleName}.tsx\`, runs deterministic VAP evaluation, and rectifies compiler and DRC errors.

---

## 2. Stage Gates & Definitions of Done (DoD)

### Stage 1: SCUD Synthesis & Boundary Ingestion
- **Assigned Peer**: \`archy\`
- **Definition of Done**:
  1. \`${moduleName}.scud\` exists under \`${moduleName}/Workspace/\` with all 5 mandatory sections.
  2. All external boundary ports and power domains are explicitly mapped.
  3. No dangling or unresolved uncertainties remain in Section 5 (or escalated to HIL).
  4. Literal string \`IN_PROGRESS\` is removed from the file.

### Stage 2: Component & Footprint Resolution
- **Assigned Peer**: \`librarian\`
- **Definition of Done**:
  1. Every non-trivial IC, sensor, and connector in the SCUD is resolved to a verified footprint.
  2. Verified TSX components exist under \`${moduleName}/Workspace/imports/\`.
  3. Pin labels and polarities match manufacturer datasheets.
  4. SCUD is updated with the \`Library Mapping\` table.

### Stage 3: TSX Circuit Synthesis & VAP Verification
- **Assigned Peer**: \`ana\`
- **Definition of Done**:
  1. \`${moduleName}.tsx\` exports a valid React component representing the synthesized circuit.
  2. Synchronous VAP evaluation via \`vhl_evaluate_circuit\` returns decision \`ACCEPT\`.
  3. Zero compilation errors, missing footprints, or DRC violations.
  4. Output circuit JSON is generated under \`dist/\`.

### Stage 4: Promotion & Semantic Ledger Commitment
- **Assigned Peer**: \`archy\`
- **Definition of Done**:
  1. Semantic operation recorded in SQLite ledger using \`vhl_record_operation\`.
  2. Worktree Git branch is committed and ready for stable trunk integration.
`;

    await fs.writeFile(
        path.join(workflowsDir, "module_synthesis.md"),
        workflowContent,
        "utf-8"
    );
}

/**
 * Scaffolds an autonomous MOSAIC Agent Cluster for root assemblies in the root worktree.
 * Creates the .agents/ directory tree, symlinks canonical VHL skills,
 * discovers assembly targets, and generates flat, namespaced Agent Cards for each assembly.
 *
 * @param rootWorktreePath - Absolute path to the project root worktree (<project_id>_root)
 * @param projectId - Project identifier
 * @param runtimeRoot - Root directory of vhl-runtime-mosaic where canonical skills reside
 * @param assemblies - Optional list of assembly names (e.g. ['control_circuit', 'power_circuit'])
 */
export async function scaffoldRootCluster(
    rootWorktreePath: string,
    projectId: string,
    runtimeRoot: string,
    assemblies?: string[]
): Promise<void> {
    const agentsDir = path.join(rootWorktreePath, ".agents");
    const wellKnownDir = path.join(agentsDir, "well_known");
    const skillsDir = path.join(agentsDir, "skills");
    const workflowsDir = path.join(agentsDir, "workflows");
    const sessionsDir = path.join(agentsDir, "sessions");
    const tasksDir = path.join(agentsDir, "tasks");

    // 1. Create standard .agents/ directory structure
    await fs.mkdir(wellKnownDir, { recursive: true });
    await fs.mkdir(skillsDir, { recursive: true });
    await fs.mkdir(workflowsDir, { recursive: true });
    await fs.mkdir(sessionsDir, { recursive: true });
    await fs.mkdir(tasksDir, { recursive: true });

    // 2. Provision canonical skills from runtimeRoot into root worktree as standalone directories (no symlinks)
    const canonicalSkills = [
        "a2a-peer-dialing",
        "vhl-circuit-evaluator",
        "vhl-component-resolver",
        "vhl-workspace-ops"
    ];

    for (const skill of canonicalSkills) {
        const sourceSkillPath = path.join(runtimeRoot, ".agents", "skills", skill);
        const targetSkillPath = path.join(skillsDir, skill);

        if (existsSync(sourceSkillPath)) {
            try {
                const stat = await fs.lstat(targetSkillPath).catch(() => null);
                if (stat && stat.isSymbolicLink()) {
                    await fs.unlink(targetSkillPath);
                }
                if (!existsSync(targetSkillPath)) {
                    await fs.cp(sourceSkillPath, targetSkillPath, { recursive: true });
                }
            } catch (err: any) {
                console.warn(`[clusterScaffolding] Warning provisioning skill '${skill}' to ${targetSkillPath}:`, err.message);
            }
        }
    }

    // 3. Discover assemblies
    let resolvedAssemblies: string[] = [];
    if (assemblies && assemblies.length > 0) {
        resolvedAssemblies = assemblies;
    } else {
        const discovered = new Set<string>();
        if (existsSync(rootWorktreePath)) {
            try {
                const entries = await fs.readdir(rootWorktreePath, { withFileTypes: true });
                for (const entry of entries) {
                    if (entry.isFile()) {
                        const name = entry.name;
                        if (name.endsWith(".scud")) {
                            discovered.add(name.slice(0, -5));
                        } else if (name.endsWith(".circuit.tsx")) {
                            const base = name.slice(0, -12);
                            if (base && base !== "index") discovered.add(base);
                        } else if (name.endsWith(".tsx") && !name.startsWith("index.") && !name.includes(".test.")) {
                            discovered.add(name.slice(0, -4));
                        }
                    }
                }
            } catch {}
        }
        if (discovered.size === 0) {
            resolvedAssemblies = ["main"];
        } else {
            resolvedAssemblies = Array.from(discovered);
        }
    }

    // 4. Generate namespaced agent cards for each assembly from templates
    const templatesDir = path.join(runtimeRoot, "templates", "agent_cards");

    for (const rawAssembly of resolvedAssemblies) {
        const cleanPrefix = rawAssembly
            .toLowerCase()
            .replace(/[^a-z0-9_]/g, "_")
            .replace(/^_+|_+$/g, "") || "main";

        const replacements = {
            cleanPrefix,
            assemblyName: rawAssembly,
            projectId
        };

        const archyCard = await renderCardTemplate(path.join(templatesDir, "assembly_archy.json"), replacements);
        const anaCard = await renderCardTemplate(path.join(templatesDir, "assembly_ana.json"), replacements);
        const layoutCard = await renderCardTemplate(path.join(templatesDir, "assembly_layout.json"), replacements);

        await fs.writeFile(
            path.join(wellKnownDir, `${cleanPrefix}_archy.json`),
            JSON.stringify(archyCard, null, 2),
            "utf-8"
        );
        await fs.writeFile(
            path.join(wellKnownDir, `${cleanPrefix}_ana.json`),
            JSON.stringify(anaCard, null, 2),
            "utf-8"
        );
        await fs.writeFile(
            path.join(wellKnownDir, `${cleanPrefix}_layout.json`),
            JSON.stringify(layoutCard, null, 2),
            "utf-8"
        );
    }

    // 5. Generate declarative workflow contract for assemblies
    const workflowContent = `# Root Assembly Synthesis Workflow Contract

> **Project:** ${projectId}  
> **Root Worktree:** ${rootWorktreePath}  
> **Architecture:** MOSAIC Multi-Cluster Assembly Flat Cluster (Port 8000)  
> **Configured Assemblies:** ${resolvedAssemblies.join(", ")}  

---

## 1. Assembly Cluster Roles & Namespacing

For each top-level assembly (\`<assembly>\`), the root cluster operates a flat triad:
- **Lead Assembly Architect (\`<assembly>_archy\`)**: Ingests \`system-boundary.md\`, communicates across clusters with module Archies via A2A, and authors \`<assembly>.scud\`.
- **Assembly Synthesizer (\`<assembly>_ana\`)**: Assembles and wires submodules into top-level TSX board code (\`<assembly>.tsx\`), invoking VAP evaluation.
- **Physical Layout Specialist (\`<assembly>_layout\`)**: Sets PCB board dimensions, component keepouts, layer stackup, and tunes Cypress autorouter constraints.

---

## 2. Stage Gates & Definitions of Done (DoD)

### Stage 1: System Boundary Ingestion & Inter-Cluster Coordination
- **Assigned Peer**: \`<assembly>_archy\`
- **Definition of Done**:
  1. Top-level \`<assembly>.scud\` reflects complete system boundary requirements and inter-module pinouts.
  2. Pinout agreements with peer module Archies verified via A2A peer dialing.
  3. No ambiguous or silent inferences remain in Section 5.

### Stage 2: Top-Level Assembly Wiring & Bus Routing
- **Assigned Peer**: \`<assembly>_ana\`
- **Definition of Done**:
  1. \`<assembly>.tsx\` instantiates all required module components.
  2. Inter-module signal and power nets routed without dangling nets.
  3. Synchronous VAP evaluation returns decision \`ACCEPT\`.

### Stage 3: Board Dimensioning, Critical Placement & Cypress Autorouting
- **Assigned Peer**: \`<assembly>_layout\`
- **Definition of Done**:
  1. Board outline and dimensions calculated with appropriate clearance.
  2. Critical isolation barriers maintained (e.g. HV vs LV).
  3. Autorouter parameters tuned with 100% completion.

### Stage 4: Promotion & Assembly Verification
- **Assigned Peer**: \`<assembly>_archy\`
- **Definition of Done**:
  1. Final board passes full design rule check.
  2. Git commit created on master trunk branch and recorded in SQLite state ledger.
`;

    await fs.writeFile(
        path.join(workflowsDir, "assembly_synthesis.md"),
        workflowContent,
        "utf-8"
    );
}
