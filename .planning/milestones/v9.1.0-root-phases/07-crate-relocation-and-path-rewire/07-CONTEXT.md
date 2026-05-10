# Phase 7: Crate Relocation and Path Rewire - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Move every Rust crate currently under `ClassicLib-rs/` to repo-root-relative locations while preserving crate internals and keeping the workspace/member/path graph valid from the repository root. This phase is about the physical crate move and the Rust manifest/path rewiring only, not the later wrapper/parity/CI/docs follow-through.

</domain>

<decisions>
## Implementation Decisions

### Repo-Root Layout
- **D-01:** Move the six existing Rust layer directories intact from `ClassicLib-rs/` to the repository root: `foundation/`, `business-logic/`, `cpp-bindings/`, `node-bindings/`, `python-bindings/`, and `ui-applications/`.
- **D-02:** Treat the move as layout preservation, not taxonomy cleanup: keep current crate ownership boundaries and each crate's internal files/directories intact.

### Manifest And Path Rewiring
- **D-03:** Keep crate-manifest rewrites minimal. Preserve existing `path =` relationships wherever the preserved layer topology keeps them valid.
- **D-04:** Rewrite only workspace member entries and manifest `path =` edges that actually break because of the move; do not use Phase 7 for broader manifest modernization or dependency-style cleanup.

### Legacy `ClassicLib-rs` Boundary
- **D-05:** By the end of Phase 7, `ClassicLib-rs/` must no longer contain live Rust crates or workspace-owned Rust files.
- **D-06:** If any residue remains under `ClassicLib-rs/` after the move, it must be clearly non-authoritative and must not be required by the live build graph.

### Closure Evidence
- **D-07:** Phase 7 closure must include Cargo root/member proof using `cargo locate-project --workspace` and `cargo metadata --format-version 1 --no-deps`.
- **D-08:** Phase 7 closure must also include an explicit relocation audit that maps old crate locations to new ones and a stale-manifest/member-path sweep.
- **D-09:** Phase 7 proof stays cargo-and-layout focused; wrapper/parity smoke remains later-phase work unless a path contract is inseparable from proving the crate move itself.

### the agent's Discretion
- Exact file-move sequencing and mechanical rewrite method, as long as the preserved-layer layout and minimal-rewrite policy above hold.
- Exact validation script/report shape, as long as it produces the Cargo proof and relocation audit required above.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope And Requirements
- `.planning/ROADMAP.md` — Phase 7 goal, dependency chain, and success criteria for crate relocation and path rewiring.
- `.planning/REQUIREMENTS.md` — `MOVE-01` and `MOVE-02`, plus the out-of-scope rules that forbid redesign work or permanent dual-layout support.
- `.planning/PROJECT.md` — milestone goal, active requirements, and the preserve-structure / no-redesign framing for `v9.1.0-root`.

### Prior Locked Decisions
- `.planning/phases/06-repo-root-workspace-cutover/06-CONTEXT.md` — Phase 6 decisions that keep repo root as the only live workspace root and make repo-root Cargo commands canonical.
- `.planning/phases/06-repo-root-workspace-cutover/06-VERIFICATION.md` — current root-workspace proof surfaces and path contracts that Phase 7 must preserve while moving crates.

### Research Guidance
- `.planning/research/SUMMARY.md` — milestone sequencing, relocation-only strategy, and the warning against false confidence from partial cutovers.
- `.planning/research/STACK.md` — recommended post-move root layout, preserved layer-directory strategy, and minimal path-rewrite guidance.
- `.planning/research/PITFALLS.md` — failure modes for dual-root drift, incomplete manifest rewiring, and weak relocation audits.

### Current Repo Contracts
- `.planning/codebase/STRUCTURE.md` — current layer directories, crate ownership boundaries, and workspace-owned asset locations.
- `.planning/codebase/STACK.md` — current Cargo, binding, and repo-root toolchain assumptions the move must preserve.
- `Cargo.toml` — live root workspace member list that still points at `ClassicLib-rs/...` and must be rewired to the new root-level layer paths.
- `AGENTS.md` — always-on repo rules for Rust ownership, runtime constraints, and workflow rules that remain in force during relocation.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Cargo.toml`: the live root virtual workspace already centralizes members, shared dependencies, lints, and profiles; Phase 7 mainly rewires member paths away from `ClassicLib-rs/...`.
- `ClassicLib-rs/business-logic/**/Cargo.toml` and `ClassicLib-rs/foundation/**/Cargo.toml`: these manifests show the current layer-relative `path =` topology that should largely survive intact if the layer directories move intact.
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/Cargo.toml`, `ClassicLib-rs/node-bindings/classic-node/Cargo.toml`, `ClassicLib-rs/python-bindings/*/Cargo.toml`, and `ClassicLib-rs/ui-applications/classic-tui/Cargo.toml`: high-fanout manifests to use for targeted path verification after the move.
- `.planning/phases/06-repo-root-workspace-cutover/06-VERIFICATION.md` and `tests/planning/phase06_clean_run.ps1`: existing Cargo-root proof pattern to extend with Phase 7 relocation auditing.

### Established Patterns
- The repo already treats the workspace as a root virtual workspace with `resolver = "2"` and no live `ClassicLib-rs/Cargo.toml`.
- Crate relationships are layer-based: `foundation/`, `business-logic/`, `cpp-bindings/`, `node-bindings/`, `python-bindings/`, `ui-applications/`; preserving that geometry minimizes path churn.
- The current tree contains 107 explicit local `path =` dependencies, so mechanical inventory/verification matters more than opportunistic cleanup.
- Phase sequencing intentionally separates cargo/layout work (Phases 6-7) from wrapper/parity rewires (Phase 8), clean validation (Phase 9), and docs/tripwires (Phase 10).

### Integration Points
- `Cargo.toml` workspace `members` array.
- High-fanout member manifests: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/Cargo.toml`, `ClassicLib-rs/node-bindings/classic-node/Cargo.toml`, `ClassicLib-rs/python-bindings/classic-config-py/Cargo.toml`, and `ClassicLib-rs/ui-applications/classic-tui/Cargo.toml`.
- The `ClassicLib-rs/` directory boundary itself: after Phase 7 it cannot remain a live Rust home, even if later phases still clean up adjacent non-authoritative residue.

</code_context>

<specifics>
## Specific Ideas

- Move the six existing Rust layer directories intact to repo root.
- Preserve crate internals and rewrite path edges only when the move actually breaks them.
- `ClassicLib-rs/` must stop being a live Rust workspace/container after this phase.
- Done means explicit old-to-new crate mapping plus a stale-manifest/member-path sweep, not just green Cargo commands.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 07-crate-relocation-and-path-rewire*
*Context gathered: 2026-04-12*
