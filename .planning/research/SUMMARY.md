# Project Research Summary

**Project:** CLASSIC — milestone `v9.1.0-root`
**Domain:** Brownfield Rust workspace relocation in a multi-language repository
**Researched:** 2026-04-11
**Confidence:** HIGH

## Executive Summary

This milestone is a repository-layout migration, not a product or architecture redesign. The recommended expert approach is to make the repository root the single Cargo workspace root, move the six existing Rust layer directories from `ClassicLib-rs/` to the root intact, and preserve the current Rust-core / thin-wrapper architecture across C++, Python, Node, and TUI surfaces. The move succeeds only if repo-root Cargo commands become canonical **and** every downstream path consumer is rewired to the new layout.

The most important implementation choice is to preserve internal crate structure and existing toolchain versions while updating the workspace anchor, external path contracts, and generated artifacts. In practice, that means moving `Cargo.toml`, `Cargo.lock`, `.cargo/config.toml`, `validate_stubs.py`, benches, and benchmark configs to the repo root first; then relocating `foundation/`, `business-logic/`, `cpp-bindings/`, `node-bindings/`, `python-bindings/`, and `ui-applications/`; then fixing CMake/Corrosion, `rebuild_rust.ps1`, parity tooling, CI workflows, and documentation.

The key risk is false confidence from partial cutovers: a root manifest can appear to work while wrappers, parity gates, CI caches, or docs still target `ClassicLib-rs/`. Prevent that by enforcing a single authoritative workspace root, validating real entrypoints instead of Cargo alone, regenerating path-bearing artifacts, and treating docs/skills/planning updates as required migration work rather than cleanup.

## Key Findings

### Recommended Stack

Research strongly recommends a pure relocation strategy: keep Cargo stable, keep current workspace dependency inheritance, keep Corrosion/CXX, PyO3, NAPI-RS, Bun, uv, and PowerShell wrapper flows, and change only the workspace root plus path contracts. The milestone should not bundle dependency upgrades, crate renames, or workflow replacements.

**Core technologies:**
- **Repo-root Cargo virtual workspace:** canonical Rust entrypoint — removes `--manifest-path ClassicLib-rs/Cargo.toml` from normal workflows.
- **Preserved root-level layer directories:** keep crate topology stable — minimizes intra-workspace churn and protects parity.
- **Existing multi-language binding stack:** preserve current integrations — this is a path migration, not a toolchain refresh.
- **Root-level workspace support files:** `Cargo.lock`, `.cargo/config.toml`, `validate_stubs.py`, benches, and benchmark config must move with the workspace root.

### Expected Features

The milestone definition is outcome-based: repo-root Cargo must work, every crate under `ClassicLib-rs/` must be relocated without internal redesign, and all wrapper/parity/frontend workflows must still pass. The strongest recommendation is to treat path rewiring across scripts, CMake, CI, parity tools, docs, and agent guidance as part of the core feature set, not post-move polish.

**Must have (table stakes):**
- **Repository-root Cargo workspace entrypoint** — root `Cargo.toml` becomes the only authoritative workspace manifest.
- **All crates relocated with internal structure preserved** — move directories intact; no crate graph redesign.
- **Path-reference rewiring across tooling, wrappers, CI, docs, and skills** — all `ClassicLib-rs/**` operational references must be updated.
- **Parity gates and frontend/wrapper workflows still pass** — preserve Node, Python, C++, CLI, GUI, and Rust validation behavior.
- **No functional or API drift** — relocation only.

**Should have (competitive):**
- **Path-regression tripwires** — prevent reintroduction of stale `ClassicLib-rs/` references.
- **Root-level command simplification evidence** — contributor ergonomics improve visibly once root commands are canonical.
- **Verification matrix / migration notes** — useful closure evidence if cheap.

**Defer (v2+):**
- **Crate renames, merges, or splits** — out of scope.
- **Binding API redesign or parity schema changes** — out of scope.
- **Broader repository reorganization or bundled upgrades** — separate initiative.

### Architecture Approach

Architecturally, the system should remain the same: Rust core crates in layered directories, thin wrappers above them, and one shared Tokio runtime. The only intended architectural change is the workspace anchor moving to the repository root, with all repo tooling becoming repo-root-relative instead of `ClassicLib-rs`-relative.

**Major components:**
1. **Repo-root workspace shell** — owns the authoritative `Cargo.toml`, `Cargo.lock`, `.cargo/config.toml`, benchmark files, and shared `target/` behavior.
2. **Layer directories** — `foundation/`, `business-logic/`, `cpp-bindings/`, `node-bindings/`, `python-bindings/`, `ui-applications/`; preserve current ownership boundaries.
3. **Integration consumers** — `classic-cli`, `classic-gui`, `rebuild_rust.ps1`, parity tools, CI workflows, and generated artifacts that must be retargeted to the new root.

### Critical Pitfalls

1. **Dual-workspace / partial-move state** — avoid by making repo root the only live workspace root and verifying `cargo metadata` reports one `workspace_root` everywhere.
2. **Incomplete manifest/path rewrite** — avoid by inventorying and mechanically updating all local `path =` edges, then checking high-fan-out crates and workspace metadata.
3. **Wrappers and frontends still targeting `ClassicLib-rs`** — avoid by giving CMake/Corrosion and PowerShell rewiring a dedicated phase and validating real CLI/GUI/rebuild entrypoints.
4. **Parity tools and generated artifacts still using old paths** — avoid by updating tool defaults and package scripts before baseline refreshes, then rerunning all three parity gates.
5. **Stale docs, planning, and agent context** — avoid by treating authoritative documentation and skill cleanup as required closure work, backed by grep/audit sweeps.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Root Workspace Cutover
**Rationale:** Everything else depends on a real root workspace existing first.
**Delivers:** Root `Cargo.toml`, `Cargo.lock`, `.cargo/config.toml`, `validate_stubs.py`, benches, and benchmark config moved or recreated at repo root; root Cargo commands become canonical.
**Addresses:** Repo-root Cargo entrypoint; no dual-manifest steady state.
**Avoids:** Dual-workspace / partial-move risk.

### Phase 2: Crate Relocation and Manifest Rewiring
**Rationale:** Establish the final filesystem layout before fixing downstream consumers.
**Delivers:** `foundation/`, `business-logic/`, `cpp-bindings/`, `node-bindings/`, `python-bindings/`, and `ui-applications/` moved intact; all required `members` and `path =` relationships corrected.
**Uses:** Preserved layer-directory topology and workspace dependency inheritance.
**Implements:** “preserve internals, rewrite path edges only” pattern.
**Avoids:** Incomplete path-dependency fan-out rewrite.

### Phase 3: Wrapper and Parity Integration Rewiring
**Rationale:** Native wrappers and binding flows are the first proof that relocation preserved the real product surface.
**Delivers:** Updated `classic-cli/CMakeLists.txt`, `classic-gui/CMakeLists.txt`, `rebuild_rust.ps1`, Node `package.json` script paths, parity-tool defaults, and root-relative stub/parity flows.
**Addresses:** Preserved parity gates and frontend/wrapper workflows.
**Avoids:** Wrapper breakage and stale parity-tool path drift.

### Phase 4: Clean Validation, CI, and Artifact Refresh
**Rationale:** After rewiring, the team needs clean-state evidence rather than incremental false greens.
**Delivers:** Updated workflow paths, cache roots, artifact upload paths, benchmark paths, regenerated parity/path-bearing artifacts, and clean build/test validation.
**Addresses:** Existing CI/build/test workflows still work under the new root.
**Avoids:** Stale cache shadowing and hidden fixture/include/benchmark path failures.

### Phase 5: Docs, Skills, Planning, and Regression Guards
**Rationale:** In this repo, stale human guidance quickly becomes operational drift.
**Delivers:** Updated `README.md`, `AGENTS.md`, skills, planning docs/tests, API docs, and optional stale-path tripwires.
**Addresses:** Docs, skills, and agent context updated to the new layout.
**Avoids:** Reintroduction of `ClassicLib-rs` through instructions, tests, or follow-up work.

### Phase Ordering Rationale

- The root workspace must exist before crate relocation can be validated safely.
- Crates must move before wrappers, parity tools, and CI can be retargeted against final paths.
- Wrappers/parity need to pass before cache refreshes and generated-artifact regeneration have trustworthy outputs.
- Documentation and regression guards should follow the final validated layout, but they are still required for milestone closure.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3:** high integration density across Corrosion/CMake, PowerShell, Bun/NAPI, PyO3, and parity tooling; validate exact path changes per consumer.
- **Phase 4:** CI/cache/artifact refresh may require targeted review of workflow-specific assumptions, especially benchmark and parity artifact jobs.

Phases with standard patterns (skip research-phase):
- **Phase 1:** Cargo root cutover is well documented by official Cargo workspace behavior.
- **Phase 2:** directory relocation with preserved internal structure is mechanically clear once the workspace root is defined.
- **Phase 5:** documentation and agent cleanup is broad but not conceptually ambiguous.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Based on official Cargo workspace behavior plus live repo scripts, workflows, and manifests. |
| Features | HIGH | Milestone scope is explicit in `.planning/PROJECT.md` and aligns with current repo testing/contracts. |
| Architecture | HIGH | The desired end state is a location move with stable system architecture, confirmed by repo structure and wrapper integration points. |
| Pitfalls | HIGH | Risks are concrete, path-driven, and backed by known hardcoded consumers in scripts, CI, parity tools, and docs. |

**Overall confidence: HIGH**

### Gaps to Address

- **Exact manifest-path rewrite count:** research agrees on the pattern, but implementation should inventory every local `path =` edge before execution to avoid missed crates.
- **Generated artifact scope:** parity baselines and docs likely need regeneration, but the exact file list should be confirmed during Phase 4 planning.
- **Residual `ClassicLib-rs` references:** research identifies many likely surfaces, but a repo-wide audit should classify which remaining references are active, archival, or intentionally historical.

## Sources

### Primary (HIGH confidence)
- `.planning/research/STACK.md` — recommended layout, stack preservation strategy, integration points, sequencing.
- `.planning/research/FEATURES.md` — milestone table stakes, scope boundaries, and feature priorities.
- `.planning/research/ARCHITECTURE.md` — structural patterns, build order, integration surfaces, verification flows.
- `.planning/research/PITFALLS.md` — failure modes, prevention strategies, and phase-to-risk mapping.
- `.planning/PROJECT.md` — milestone goal, active requirements, and out-of-scope constraints.
- Official Cargo docs (`workspaces`, `specifying-dependencies`, `manifest`) — authoritative workspace-root and path-dependency semantics.

### Secondary (MEDIUM confidence)
- Live repo consumers cited across the research set: `rebuild_rust.ps1`, `classic-cli/CMakeLists.txt`, `classic-gui/CMakeLists.txt`, `.github/workflows/*`, parity tooling under `tools/*_api_parity/*`, and binding package scripts.

### Tertiary (LOW confidence)
- None identified; the open items are implementation inventory questions rather than source-quality gaps.

---
*Research completed: 2026-04-11*
*Ready for roadmap: yes*
