# Phase 4: Gate Validation & Documentation - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Close the v9.1.0 consolidation milestone after Phases 1-3 by proving the workspace is stable end-to-end and by leaving contributor-facing docs aligned with the final 16-crate topology. This phase owns cross-merge validation, stale parity/doc cleanup discovered during closure, and final documentation alignment. It does not add new product capability or redesign existing binding contracts.

</domain>

<decisions>
## Implementation Decisions

### Gate refresh policy
- **D-01:** Start Phase 4 with plain parity verification. Refresh baselines only when drift is intentional and source-backed, then rerun the plain gates to prove zero drift.
- **D-02:** Treat the Node refresh flow as an explicit two-step sequence: `bun run parity:gate:update-baseline` only when needed, followed by `bun run parity:gate`. Do not treat `parity:gate:local` as the canonical audit path for this phase.
- **D-03:** If a gate fails only because checked-in artifacts are stale while live source is correct, Phase 4 fixes that in-phase instead of deferring it.
- **D-04:** After any intentional refresh, rerun all three gates without refresh flags before calling the milestone closed.

### Closure evidence
- **D-05:** Produce a dedicated Phase 4 verification artifact rather than relying only on scattered gate outputs.
- **D-06:** Organize the proof as one milestone-closure checklist covering workspace Rust tests, all three parity gates, required docs updates, and the final doc audit.
- **D-07:** Final success requires all checks green plus explicit doc-audit evidence. Command exit codes alone are not sufficient closure proof.
- **D-08:** Add a targeted Phase 4 audit guard test only if execution uncovers a real closure gap that existing gates and doc sweeps do not already catch.

### Documentation closure
- **D-09:** Run a broad active-doc audit across live contributor docs, including `CLAUDE.md`, `docs/api/`, `.planning/PROJECT.md`, and `.planning/codebase/*.md`, while continuing to skip archived milestone/history snapshots.
- **D-10:** Keep brief phase-history notes in surviving docs where they help contributors find moved or absorbed surfaces, but do not turn active docs into detailed migration narratives.
- **D-11:** `CLAUDE.md` should state the current 16-crate topology explicitly and retain only a short Phase 1-3 history summary.
- **D-12:** Retired crate names may remain only when clearly marked as historical or migration context; otherwise active docs should use present-day owners and names.

### Execution order
- **D-13:** Sequence Phase 4 for fast failure: run cheap doc/parity audits first, then heavier workspace/native validation after cheap closure issues are resolved.
- **D-14:** Run the source-only parity gates before C++ native validation so stale baselines or doc drift fail before bridge, CLI, and GUI build time is paid.
- **D-15:** Run `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` after cheap cleanup, then finish with the full end-to-end milestone suite if the early audits are green.

### Carried-forward constraints
- **D-16:** Active docs only. Do not edit archived milestone plans, historical docs, or snapshot artifacts just to match the new topology.
- **D-17:** Retired API docs stay consolidated into surviving `docs/api/` pages. Phase 4 validates and polishes that end state rather than recreating retired pages.
- **D-18:** One-tier parity remains the acceptance bar: final state must be zero drift across C++, Python, and Node.

### the agent's Discretion
- Whether a new targeted audit guard test is needed at all. Add one only if existing checks leave a real closure gap.
- Exact wording and layout of the verification checklist artifact.
- Exact composition of the final full-suite command, as long as it preserves the chosen fast-fail order and ends with plain gate reruns plus full-suite proof.

</decisions>

<specifics>
## Specific Ideas

- Use an explicit Node refresh sequence (`parity:gate:update-baseline` then `parity:gate`) instead of treating `parity:gate:local` as the milestone-audit command.
- Make the closure artifact a single checklist-style verification file instead of leaving proof scattered across parity reports and shell output.
- Keep active docs concise: preserve brief Phase 1-3 ownership notes where they help contributors, but do not keep long migration narratives alive in current docs.
- Cheap audits should fail first, then the phase should pay for the heavier workspace and native validation runs.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and milestone constraints
- `.planning/ROADMAP.md` - Phase 4 goal, dependency chain, and success criteria.
- `.planning/REQUIREMENTS.md` - GATE-01 through GATE-06 acceptance criteria for this phase.
- `.planning/PROJECT.md` - milestone target features, crate-count goal, parity constraints, and current active requirements.
- `.planning/STATE.md` - carried-forward sequencing notes, especially the Phase 1-3 decisions that defer final cross-merge validation to Phase 4.

### Prior phase decisions that stay locked here
- `.planning/phases/01-yaml-settings-merge/01-CONTEXT.md` - Phase 1 precedent for active-doc-only cleanup, API-doc consolidation, and end-of-phase parity baseline refresh.
- `.planning/phases/02-crashgen-config-merge/02-CONTEXT.md` - Phase 2 precedent for active-doc-only cleanup and verify-only handling when changes are internal import-path moves.
- `.planning/phases/03-constants-version-registry-merge/03-CONTEXT.md` - Phase 3 decision set for active-doc topology cleanup, three-way doc consolidation, and all-three parity baseline regeneration.
- `.planning/phases/03-constants-version-registry-merge/03-VALIDATION.md` - current full-suite validation order and audit-guard precedent to reuse or adapt for Phase 4.

### Parity gate policy and command sources
- `docs/api/binding-parity-policy.md` - one-tier parity policy, gate ownership, and the documented verify-then-refresh workflow.
- `docs/api/cxx-parity-gate.md` - CXX gate behavior, `--update-baseline` workflow, committed-vs-ephemeral artifacts, and source-only scope.
- `docs/api/binding-contract-refresh-note.md` - current C++, Node, and Python contract-refresh rules and when multi-surface refreshes should land together.
- `docs/api/node-python-contract-map.md` - canonical Node/Python contract files, artifact locations, and first places to inspect when a contract looks wrong.
- `ClassicLib-rs/node-bindings/classic-node/package.json` - canonical Node parity and runtime-test scripts (`parity:gate`, `parity:gate:update-baseline`, `parity:gate:local`, `test:bun`, `test:node`).
- `tools/cxx_api_parity/check_parity_gate.py` - CXX gate CLI and tracked baseline-artifact behavior.
- `tools/python_api_parity/check_parity_gate.py` - Python gate CLI, artifact sync flow, and contract/surface guard behavior.
- `tools/node_api_parity/check_parity_gate.py` - Node gate CLI, contract validation rules, and artifact-generation behavior.

### Contributor-facing docs that define the final topology
- `CLAUDE.md` - contributor build/test guidance plus the technology-stack section that must reflect the 16-crate topology.
- `docs/api/README.md` - active API-doc index and crate-layer ordering.
- `docs/api/binding-parity-overview.md` - current per-crate binding exposure and brief Phase 1-3 ownership notes.
- `.planning/codebase/ARCHITECTURE.md` - active architecture map with current crate counts and layer responsibilities.
- `.planning/codebase/STRUCTURE.md` - active directory map and crate inventory used by contributor docs.
- `.planning/codebase/STACK.md` - technology-stack source that feeds `CLAUDE.md`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tools/cxx_api_parity/check_parity_gate.py`: source-only CXX drift detection with built-in `--update-baseline` support and committed artifact sync.
- `tools/python_api_parity/check_parity_gate.py`: Python parity gate plus artifact sync and actionable contract/surface guards.
- `ClassicLib-rs/node-bindings/classic-node/package.json`: canonical Node scripts for parity refresh, parity verification, `index.d.ts` freshness, and runtime tests.
- `.planning/phases/03-constants-version-registry-merge/03-VALIDATION.md`: existing full-suite command and audit-guard precedent that already spans parity, native, and workspace proof.
- `docs/api/README.md` and `docs/api/binding-parity-overview.md`: current contributor-doc entry points for crate ownership and binding exposure.

### Established Patterns
- The documented parity workflow is verify first, refresh only when drift is intentional, then rerun the gate to confirm zero drift.
- Active contributor docs are kept current; archived milestone and historical docs stay frozen.
- Node contract freshness is tracked through generated `index.d.ts` plus parity scripts, Python through `.pyi` plus parity/stub artifacts, and CXX through committed baseline files under `docs/implementation/cxx_api_parity/baseline/`.
- C++ validation must use `classic-cli/build_cli.ps1 -Test` and `classic-gui/build_gui.ps1 -Test`, not raw `ctest`.

### Integration Points
- Workspace proof runs through `ClassicLib-rs/Cargo.toml` via `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml`.
- CXX closure touches `tools/cxx_api_parity/`, `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/`, and the C++ wrapper scripts.
- Node closure touches `ClassicLib-rs/node-bindings/classic-node/` plus `docs/implementation/node_api_parity/baseline/`.
- Python closure touches `tools/python_api_parity/`, `ClassicLib-rs/python-bindings/parity-artifacts/`, and `docs/implementation/python_api_parity/baseline/`.
- Contributor-doc closure touches `CLAUDE.md`, `docs/api/`, `.planning/PROJECT.md`, and `.planning/codebase/*.md`.

</code_context>

<deferred>
## Deferred Ideas

None - discussion stayed within Phase 4 scope.

</deferred>

---

*Phase: 04-gate-validation-documentation*
*Context gathered: 2026-04-11*
