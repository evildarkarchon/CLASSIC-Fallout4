# Phase 8: Wrapper and Parity Rewire - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Keep the existing Rust-consuming wrappers, native frontends, and parity gates working against the repo-root workspace after the Phase 7 relocation. This phase is about operational path rewiring and proof for those consumers, not broader clean-state validation/CI refresh or the later docs-and-guidance sweep.

</domain>

<decisions>
## Implementation Decisions

### Wrapper Surface
- **D-01:** Phase 8 preserves all current operational entrypoints: `rebuild_rust.ps1`, `rebuild_node.ps1`, `classic-cli/build_cli.ps1`, `classic-gui/build_gui.ps1`, package-local Node scripts, and the repo-root `classic-tui` cargo flow.
- **D-02:** When commands overlap, repo-root wrappers are canonical. Package-local commands stay working, but they are secondary to the repo-root workflow.
- **D-03:** `rebuild_node.ps1` remains a supported entrypoint, but it should become a thin alias over the canonical Node rebuild flow rather than a separate maintained implementation.
- **D-04:** The TUI stays a direct repo-root Cargo entrypoint in Phase 8; do not add a dedicated TUI wrapper just to mirror the CLI/GUI script model.

### Legacy Path Policy
- **D-05:** Phase 8 ends active `ClassicLib-rs/...` support in wrapper and parity workflows.
- **D-06:** If a user or script still passes an old `ClassicLib-rs/...` path, tooling should fail fast and show the correct repo-root replacement instead of warning-and-continuing or silently normalizing.
- **D-07:** Help text and wrapper output should explicitly teach the new repo-root command/path when rejecting an old one.
- **D-08:** Regression coverage for Phase 8 should prove both root-path success and legacy-path rejection.

### Parity Tooling And Artifacts
- **D-09:** Python, Node, CXX, and Node d.ts freshness tooling should fully cut over to root-level binding paths in Phase 8; do not rely on old in-code defaults plus overrides.
- **D-10:** Keep non-baseline parity outputs in per-binding local directories at the new root-level locations.
- **D-11:** If checked-in path-bearing parity or freshness artifacts become stale because of the relocation, refresh those artifacts in Phase 8 while keeping parity contracts and API expectations unchanged.
- **D-12:** Any parity or freshness workflow that still reads from or writes to `ClassicLib-rs/...` should hard-fail as a regression.

### Native Proof Depth
- **D-13:** Phase 8 closes on build-plus-smoke proof, not build-only proof and not install/package closure by default.
- **D-14:** CLI and GUI proof should include their existing `-Test` flows through `classic-cli/build_cli.ps1 -Test` and `classic-gui/build_gui.ps1 -Test`.
- **D-15:** TUI proof should include a lightweight repo-root run check, such as `cargo run -p classic-tui -- --help` or `--version`, rather than build-only proof.
- **D-16:** Native install/package flows stay out of the default Phase 8 closure unless they are required to make the mandatory proof surfaces work.

### the agent's Discretion
- Exact alias mechanics for `rebuild_node.ps1`, as long as it delegates to one canonical Node rebuild implementation.
- Exact wording of migration hints, as long as old-path failures point to the correct repo-root replacement.
- Exact lightweight TUI smoke command (`--help` vs `--version`), as long as it proves the repo-root entrypoint runs.
- Exact placement and naming of Phase 8 regression tests, as long as they cover both canonical success and legacy-path rejection.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope And Locked Prior Decisions
- `.planning/ROADMAP.md` — Phase 8 goal, dependency chain, and success criteria for wrapper/front-end/parity rewiring.
- `.planning/REQUIREMENTS.md` — `INTG-01` and `INTG-02`, plus the milestone guardrails that forbid API redesign and permanent dual-layout support.
- `.planning/PROJECT.md` — milestone framing: relocation only, preserve existing wrapper/toolchain stack, and keep parity at zero drift.
- `.planning/STATE.md` — current milestone position and the carry-forward phase sequencing notes for Phases 6-8.
- `.planning/phases/06-repo-root-workspace-cutover/06-CONTEXT.md` — root-workspace decisions, especially repo-root command canon and the no-dual-root direction.
- `.planning/phases/07-crate-relocation-and-path-rewire/07-CONTEXT.md` — preserved-layer layout, minimal path-rewrite policy, and the explicit deferral of wrapper/parity rewires into Phase 8.

### Migration Research
- `.planning/research/SUMMARY.md` — milestone sequencing and the recommendation that wrappers/parity consumers are first-class migration scope.
- `.planning/research/STACK.md` — concrete wrapper/parity path rewires, preserved entrypoint strategy, and the recommendation to remove temporary compatibility after the cutover.
- `.planning/research/PITFALLS.md` — wrapper drift, parity-artifact path drift, and migration-validation failure modes that Phase 8 must avoid.
- `.planning/research/ARCHITECTURE.md` — integration-consumer inventory and the expected repo-root wrapper/parity flow after relocation.

### Parity Contracts
- `docs/implementation/python_api_parity/baseline/parity_contract.json` — locked Python parity contract that must remain semantically unchanged while tooling paths move.
- `docs/implementation/node_api_parity/baseline/parity_contract.json` — locked Node parity contract that must remain semantically unchanged while tooling paths and d.ts freshness flows move.
- `docs/implementation/cxx_api_parity/baseline/parity_contract.json` — locked CXX parity contract that must remain semantically unchanged while gate paths move.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `rebuild_rust.ps1`: already centralizes repo-root Cargo rebuild behavior and target routing; Phase 8 mainly needs to finish the Python/Node subtree rewires and preserve this as the canonical wrapper.
- `classic-cli/build_cli.ps1` and `classic-gui/build_gui.ps1`: existing public native entrypoints already expose `-Test`, install, and package flows, so Phase 8 can preserve them rather than inventing new proof commands.
- `node-bindings/classic-node/package.json`: existing build/test/parity script hub; the main work is updating relative tool-path depth and keeping the package-local workflows working under the new layout.
- `tools/python_api_parity/check_parity_gate.py`, `tools/node_api_parity/check_parity_gate.py`, `tools/cxx_api_parity/check_parity_gate.py`, and `tools/node_api_parity/check_dts_freshness.py`: existing parity/freshness entrypoints already support `--repo-root`; they need default-path rewires, not workflow replacement.
- `validate_stubs.py`: repo-root stub validator already exists and can be tightened from transitional normalization to Phase 8 root-only behavior.
- `tools/enter_vs_dev_shell.ps1`: existing VS Dev Shell wrapper already supports Node parity local flows; only stale path guidance should need rewiring if Phase 8 touches that path.

### Established Patterns
- Preserve the current wrapper/gate entrypoints and retarget their internal paths rather than replacing the toolchain.
- Repo-root Cargo is already canonical; lingering `ClassicLib-rs/...` references are regressions, not an alternate supported layout.
- Parity tooling keeps checked-in baseline contracts under `docs/implementation/**` while writing working artifacts near each binding.
- C++ native frontends consume the Rust bridge through Corrosion/CXX using the root workspace manifest plus explicit bridge include paths.

### Integration Points
- `classic-cli/CMakeLists.txt` and `classic-gui/CMakeLists.txt` for Corrosion/CXX bridge include-path rewires.
- `rebuild_rust.ps1` and `rebuild_node.ps1` for wrapper-surface alignment and repo-root canon.
- `node-bindings/classic-node/package.json` and `tools/node_api_parity/check_dts_freshness.py` for package-local Node flow rewiring.
- `tools/python_api_parity/check_parity_gate.py`, `tools/node_api_parity/check_parity_gate.py`, `tools/cxx_api_parity/check_parity_gate.py`, and `validate_stubs.py` for parity/stub path cutover and legacy-path rejection.
- `ui-applications/classic-tui` for the repo-root TUI smoke-run proof surface.

</code_context>

<specifics>
## Specific Ideas

- Keep every current operational entrypoint alive, but collapse duplicate implementations under one canonical repo-root flow where possible.
- Old `ClassicLib-rs/...` paths should teach the new command/path instead of continuing silently.
- TUI should remain a repo-root Cargo flow rather than gaining a dedicated wrapper for symmetry.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 8 scope.

</deferred>

---

*Phase: 08-wrapper-and-parity-rewire*
*Context gathered: 2026-04-12*
