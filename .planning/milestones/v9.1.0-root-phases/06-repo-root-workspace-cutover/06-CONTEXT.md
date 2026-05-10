# Phase 6: Repo-Root Workspace Cutover - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the repository root the single authoritative Cargo workspace root for CLASSIC. This phase is about the workspace-anchor cutover and the repo-root Cargo contract, not the later physical crate-directory move or the broader wrapper/docs rewires.

</domain>

<decisions>
## Implementation Decisions

### Workspace-Owned Files
- **D-01:** Phase 6 moves the full workspace-owned file set to the repository root, not just `Cargo.toml`.
- **D-02:** The Phase 6 move includes `Cargo.toml`, `Cargo.lock`, `.cargo/config.toml`, `validate_stubs.py`, `criterion.toml`, `benchmark-config.yaml`, and `benches/`.
- **D-03:** `validate_stubs.py` becomes a repo-root tool in this phase and should treat the repo root as the Rust workspace root.
- **D-04:** The cutover preserves current Cargo alias and profile behavior exactly; only the authoritative root path changes.

### Canonical Root Behavior
- **D-05:** `ClassicLib-rs/Cargo.toml` is retired in Phase 6 as a live workspace manifest.
- **D-06:** The old manifest should be removed entirely, not kept live and not retained as a compatibility workspace.
- **D-07:** Phase 6 is cargo-first, not wrapper-first: direct Cargo workflows and Rust CI must stop depending on `ClassicLib-rs/Cargo.toml` now, while broader wrapper/CMake rewires can remain in later phases.
- **D-08:** The important cutover rule is one canonical workspace root with no direct old-manifest usage; Phase 6 does not need extra blocker machinery just to stop Cargo parent-directory discovery inside `ClassicLib-rs/...`.

### Repo-Root Command Contract
- **D-09:** Repo-root `cargo fmt`, `cargo clippy`, `cargo build`, and `cargo test` are all first-class Phase 6 workflows.
- **D-10:** Package-filtered repo-root commands such as `cargo build -p classic-scanlog-core` are also part of the Phase 6 contract.
- **D-11:** Active workflows should prefer plain repo-root `cargo ...` invocation style after the cutover, not `--manifest-path` calls to either the old or new root manifest.
- **D-12:** Existing alias/profile-based developer flows from `.cargo/config.toml` should keep working from repo root after the cutover.

### Phase-6 Proof
- **D-13:** Phase 6 closes only after both repo-root Cargo workflows and cargo-based Rust CI are updated to the new root behavior.
- **D-14:** Proof must include an explicit Cargo root-detection check such as `cargo metadata` so the planner verifies one canonical workspace root.
- **D-15:** Proof must include at least one clean validation pass that does not rely on stale `ClassicLib-rs/target` outputs.
- **D-16:** Proof must include an explicit audit that active cargo-based workflows no longer mention `ClassicLib-rs/Cargo.toml`.

### the agent's Discretion
- Exact file-move mechanics for promoting the workspace root, as long as the moved file set and behavior above are preserved.
- Exact command ordering for the clean validation pass and old-manifest audit.
- Whether Phase 6 proves root detection with `cargo metadata`, `cargo locate-project --workspace`, or both, as long as Cargo itself confirms the canonical root.

</decisions>

<specifics>
## Specific Ideas

- "This isn't just moving the Cargo.toml."
- The overall milestone keeps the existing crate structure intact even though the crate-directory move itself is Phase 7 work.
- The reason for the cutover is day-to-day Cargo convenience from the project root.
- The user expects stale docs, skills, and agent context to be updated later in the milestone, but Phase 6 should already stop active Cargo workflows from depending on `ClassicLib-rs/Cargo.toml`.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope And Acceptance Criteria
- `.planning/ROADMAP.md` — Phase 6 goal, dependency chain, and success criteria for the repo-root workspace cutover.
- `.planning/REQUIREMENTS.md` — `ROOT-01` and `ROOT-02`, plus the milestone out-of-scope guardrails that forbid dual-root support and redesign work.
- `.planning/PROJECT.md` — milestone goal, active requirements, and the preserve-structure / no-redesign framing.

### Research Guidance
- `.planning/research/SUMMARY.md` — recommended cutover order, no-dual-root warning, and phase sequencing rationale.

### Current Repo Contracts
- `.planning/codebase/STRUCTURE.md` — current workspace-owned file locations and the `ClassicLib-rs/` layer layout that Phase 6 temporarily anchors.
- `.planning/codebase/STACK.md` — current Cargo, CI, alias/profile, benchmark, and stub-validation assumptions that the cutover must preserve or update.
- `.planning/codebase/TESTING.md` — current Cargo and Rust-CI command surface that needs to stop relying on `--manifest-path ClassicLib-rs/Cargo.toml`.
- `AGENTS.md` — repo rules for Rust ownership, runtime constraints, and wrapper-testing conventions that remain in force during the cutover.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ClassicLib-rs/Cargo.toml`: already centralizes workspace members, shared dependencies, lints, and profiles; this is the source material for the repo-root workspace manifest.
- `ClassicLib-rs/.cargo/config.toml`: existing Cargo aliases/profiling commands that should move intact to repo root.
- `ClassicLib-rs/criterion.toml`, `ClassicLib-rs/benchmark-config.yaml`, and `ClassicLib-rs/benches/`: current workspace-owned benchmark assets that the user wants cut over with the root.
- `ClassicLib-rs/validate_stubs.py`: existing stub-validation helper that already models a workspace-root-oriented Python validation flow.

### Established Patterns
- `rebuild_rust.ps1` derives from repo root and then joins into `ClassicLib-rs/...`, so the cutover can reuse its root-driven orchestration pattern while changing only the workspace-owned path contracts.
- `.github/workflows/ci-rust.yml` treats Rust validation as root-level automation but currently routes it through `--manifest-path ClassicLib-rs/Cargo.toml` and `ClassicLib-rs/target` caches.
- `classic-cli/CMakeLists.txt` and `classic-gui/CMakeLists.txt` import the CXX bridge through explicit old-root manifest/include paths, which is why wrapper rewires remain a later-phase integration concern unless needed to satisfy the cargo-first cutover.

### Integration Points
- `rebuild_rust.ps1`: workspace manifest path, Python bindings root, and repo-root build orchestration.
- `.github/workflows/ci-rust.yml`: root Cargo command style, cache roots, and explicit manifest references.
- `ClassicLib-rs/node-bindings/classic-node/package.json`: parity and developer scripts that currently assume the old workspace-relative layout.
- Later-phase integration consumers: `classic-cli/CMakeLists.txt` and `classic-gui/CMakeLists.txt` still point at `ClassicLib-rs/Cargo.toml`, but Phase 6 keeps those rewires sequenced after the cargo-first cutover.

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 6 scope.

</deferred>

---

*Phase: 06-repo-root-workspace-cutover*
*Context gathered: 2026-04-11*
