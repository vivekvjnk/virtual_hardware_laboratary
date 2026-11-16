# Legacy VAP (VHL ANA Process) Archive

This directory archives historical documents detailing the original **VHL ANA Process (VAP)**.

## Archival Context

VAP was designed during the early architectural phase of VHL when the system was split into separate `vhl-agent-backend` and `vhl-runtime` services. In that architecture, circuit validation was divided into fine-grained stateful polling operations (`VAP_init`, `VAP_status`, `VAP_EXECUTE`, `VAP_DECISION`) executed by a dedicated runtime evaluator (`src/vap/`).

With the integration of `vhl-backend` and the adoption of the **MESH multi-agent framework**, fine-grained runtime-level state machine polling is retired. Circuit validation is now orchestrated directly by agents using declarative workflow markdown documents and Engineering Capability Packages (ECPs), such as `vhl-circuit-evaluator` and `module-synthesis-workflow`.

## Archived Documents

- `dry_run_1_the_success.md`: Original VAP dry run trace for successful `.tsx` evaluation.
- `dry_run_2_deterministic_failure.md`: Original VAP dry run trace for deterministic compiler/syntax failure.
- `dry_run_3_probabilistic_failure.md`: Original VAP dry run trace for timeout / non-deterministic hang scenarios.
- `tsckt_operational_manual.md`: Legacy operational manual for `tscircuit` component creation, symbols, and assembly.
- `VAP_ANA_Regression_test_cases.md`: Legacy regression test cases for VAP socket/state transitions.

## Modern Replacement

See [`docs/VAP_Equivalent_Specification.md`](../VAP_Equivalent_Specification.md) for the active specification of the MESH workflow- and ECP-driven circuit evaluation architecture.
