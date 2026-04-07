# Phase 8: Workspace and Infrastructure - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Clean up the remaining workspace-level dependency and contract-artifact drift, make Linux documents-path discovery handle Steam Proton installs, resolve the `zerovec` workaround situation in `classic-shared-core`, and make the Node `index.d.ts` workflow a clean tracked contract with freshness enforcement. This phase does not broaden into a general repo-wide cleanup pass beyond direct blockers adjacent to those goals.

</domain>

<decisions>
## Implementation Decisions

### Linux docs-path behavior
- **D-01:** Make Proton awareness part of the shared Linux docs-path workflow in `classic-path-core`, not a Fallout 4-specific wrapper and not binding-specific duplication.
- **D-02:** On Linux, after any cached-path success check, a valid Proton documents path should win over the existing `~/.local/share/<relative_path>` path.
- **D-03:** If Steam metadata lookup fails or the Proton documents path is invalid/missing, fall back to the existing `~/.local/share/<relative_path>` Linux path before returning not found.
- **D-04:** Fallout 4 VR Linux Proton support is out of scope for this phase. Phase 8 should target standard Fallout 4 Proton docs-path detection only.

### Linux proof strength
- **D-05:** The required proof should live in `classic-path-core` as crate-level integration coverage for the shared workflow, not as per-binding Linux tests.
- **D-06:** Required Linux Proton coverage includes all of the following:
  - a happy-path Proton case using a mock Proton prefix structure
  - a case where Steam metadata resolves but the Proton docs path is invalid, forcing local-share fallback
  - a case where Steam metadata lookup fails entirely, forcing local-share fallback
  - a regression test proving the legacy non-Proton Linux `~/.local/share/<relative_path>` path still works when it is the only valid candidate

### `zerovec` workaround policy
- **D-07:** Force removal of the `zerovec` workaround rather than keeping it as a documented historical workaround.
- **D-08:** If removing the workaround exposes stale Slint/gui-bridge code that directly blocks the removal, Phase 8 may remove that adjacent blocker code too.
- **D-09:** This adjacent cleanup allowance is narrow: remove only the Slint/gui-bridge pieces directly blocking workaround removal, not a broad repo-wide Slint purge.
- **D-10:** Remove or rewrite stale comments/docs that still describe the workaround after removal. Do not preserve historical workaround notes unless some active feature still truly requires them.

### Node type freshness enforcement
- **D-11:** `ClassicLib-rs/node-bindings/classic-node/index.d.ts` is a required tracked contract artifact and should no longer be gitignored.
- **D-12:** Any public Node binding export change must refresh and commit `index.d.ts` in the same change unit. Do not rely on CI to catch stale declarations later.
- **D-13:** The same-change workflow also includes the existing Node freshness/parity validation path rather than treating declaration refresh as a standalone file update.
- **D-14:** Contributor guidance should stop implying a build-first requirement just to inspect Node types. The committed `index.d.ts` snapshot becomes the first-class inspection artifact; builds are for regeneration and verification.

### the agent's Discretion
- Exact internal helper/API shape used to make Linux docs-path discovery Proton-aware, as long as the shared `classic-path-core` workflow stays the source of truth and existing public call patterns remain stable.
- Exact test helper structure, temp-directory layout, and environment injection used to exercise the Linux Proton and fallback paths.
- Exact command wiring and file-update sequencing for the Node declaration freshness workflow, as long as `index.d.ts` is tracked and same-change refresh remains enforced.
- Exact implementation steps used to remove direct Slint/gui-bridge blockers revealed by `zerovec` removal, as long as the cleanup stays tightly adjacent to that goal.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone contract
- `.planning/ROADMAP.md` - Phase 8 goal, requirement mapping, and success criteria for workspace deps, Proton docs-path wiring, `zerovec`, and Node declaration freshness.
- `.planning/PROJECT.md` - milestone constraints, active infrastructure work, and the locked decision that Proton path code should be wired up rather than deleted.
- `.planning/REQUIREMENTS.md` - `INFRA-01` through `INFRA-05` and `TEST-03`.
- `.planning/STATE.md` - carried-forward decisions about thin bindings, contract artifacts moving with source, and current phase continuity.
- `.planning/codebase/CONCERNS.md` - original concerns for dead Proton helper code, `zerovec` workaround fragility, non-workspace `winreg`/`phf`, and Node `index.d.ts` drift.

### Linux docs-path discovery
- `docs/api/classic-path-core.md` - current `DocsPathFinder` behavior, current Linux limitation, and contributor-visible path-detection flow.
- `docs/api/game-setup-workflow.md` - current setup workflow showing where documents-path detection fits relative to higher-level setup checks.
- `ClassicLib-rs/business-logic/classic-path-core/src/docs_path.rs` - shared `DocsPathFinder` logic and current Linux fallback behavior.
- `ClassicLib-rs/business-logic/classic-path-core/src/platform/linux.rs` - Steam library parsing, Proton path construction helper, and current Linux tests.
- `ClassicLib-rs/business-logic/classic-path-core/src/platform/mod.rs` - current platform abstraction boundary exposing Linux Steam-library parsing.
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs` - current Fallout 4 bridge consumer of `DocsPathFinder`, useful for understanding existing caller expectations.

### Workspace dependency cleanup
- `ClassicLib-rs/Cargo.toml` - root workspace manifest and `[workspace.dependencies]` target for `winreg` and `phf` promotion.
- `ClassicLib-rs/business-logic/classic-path-core/Cargo.toml` - current crate-local `winreg` declaration and Windows target gating.
- `ClassicLib-rs/business-logic/classic-constants-core/Cargo.toml` - current crate-local `phf` declaration.

### `zerovec` and gui-bridge cleanup
- `ClassicLib-rs/foundation/classic-shared-core/Cargo.toml` - current `zerovec` workaround declaration and `gui-bridge` feature wiring.
- `ClassicLib-rs/foundation/classic-shared-core/src/lib.rs` - current optional Slint/gui-bridge re-export boundary.
- `ClassicLib-rs/foundation/classic-shared-core/src/async_bridge.rs` - current Slint event-loop bridge implementation that may be an adjacent blocker if the workaround is removed.
- `docs/api/classic-shared-core.md` - contributor-facing contract for the `gui-bridge` feature and Slint dispatcher surface.

### Node contract and freshness workflow
- `docs/api/binding-parity-overview.md` - current repo statement that `classic-node/index.d.ts` is part of the public Node contract.
- `docs/api/binding-contract-refresh-note.md` - current contributor workflow for refreshing Node contract artifacts alongside public binding changes.
- `docs/implementation/node_api_parity/governance/gate_contract_baseline.md` - Node gate contract naming the required freshness/parity commands.
- `ClassicLib-rs/node-bindings/classic-node/package.json` - current Node scripts including `dts:freshness:check` and local parity commands.
- `ClassicLib-rs/node-bindings/classic-node/.gitignore` - current contradiction where `index.d.ts` is still ignored.
- `ClassicLib-rs/node-bindings/classic-node/index.d.ts` - current committed declaration snapshot that Phase 8 should formalize as tracked contract.
- `ClassicLib-rs/node-bindings/classic-node/__test__/regression_drift.spec.ts` - test file already treating `index.d.ts` as a drift-sensitive contract artifact.
- `tools/node_api_parity/check_dts_freshness.py` - freshness script behavior and current regeneration/check mechanics.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ClassicLib-rs/business-logic/classic-path-core/src/platform/linux.rs`: already has `parse_steam_library_vdf()` and `construct_proton_docs_path()`; Phase 8 is wiring existing Linux Proton helpers into the shared workflow, not inventing them from scratch.
- `ClassicLib-rs/business-logic/classic-path-core/src/docs_path.rs`: already centralizes cached-path and platform fallback logic in one `DocsPathFinder`, giving Phase 8 a single shared integration point.
- `ClassicLib-rs/node-bindings/classic-node/package.json`: already has `dts:freshness:check`, `dts:freshness:local`, and parity scripts; enforcement mostly needs cleanup/alignment rather than a brand-new workflow.
- `ClassicLib-rs/node-bindings/classic-node/__test__/regression_drift.spec.ts`: already reads `index.d.ts` directly, so the repo has an existing declaration-drift testing pattern.

### Established Patterns
- Shared behavior belongs in Rust core crates; wrappers should reuse the shared workflow instead of duplicating Linux docs-path logic.
- Contract artifacts move with source changes in the same change unit, especially for Node parity/governance work.
- Workspace dependency promotion is reserved for shared dependencies, while local-only dependencies stay crate-scoped.
- Earlier phases already normalized on committed Node contract artifacts; Phase 8 is finishing that policy cleanly instead of inventing a new one.

### Integration Points
- Linux Proton docs-path wiring lands primarily in `classic-path-core`, then benefits existing callers in the C++ bridge, Node bindings, Python bindings, and TUI automatically.
- Workspace dependency cleanup lands in the root `ClassicLib-rs/Cargo.toml` plus the affected crate manifests for `classic-path-core` and `classic-constants-core`.
- `zerovec` removal centers on `classic-shared-core` manifest/feature boundaries and any directly adjacent Slint/gui-bridge code that proves to be dead blocker code.
- Node declaration workflow cleanup lands in `classic-node/.gitignore`, `package.json`, the freshness script, and the contributor/parity docs that define the contract-refresh workflow.

</code_context>

<specifics>
## Specific Ideas

- Proton docs-path support should prefer the Steam/Proton location when available, but preserve the old Linux local-share path as an explicit fallback path.
- Fallout 4 VR Linux Proton support is intentionally out of scope for this phase.
- The old Slint GUI is gone, so stale Slint-specific blocker code should not be preserved just to keep the `zerovec` workaround alive.
- The committed Node declaration snapshot should become the normal contributor inspection surface rather than something contributors must build locally before they can read it.

</specifics>

<deferred>
## Deferred Ideas

- Broader repo-wide removal of all remaining Slint integration code beyond the direct blockers adjacent to `zerovec` removal. Phase 8 only allows narrow blocker cleanup tied to the workaround-removal goal.

</deferred>

---

*Phase: 08-workspace-and-infrastructure*
*Context gathered: 2026-04-06*
