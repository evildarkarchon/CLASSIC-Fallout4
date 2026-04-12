# Phase 3: Constants Redistribution (formerly "Constants -> Version Registry Merge") - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning (pending roadmap-amendment quick-task)

<domain>
## Phase Boundary

Redistribute the contents of `classic-constants-core` across three target crates by semantic domain, instead of the originally-planned flat merge into `classic-version-registry-core`. When Phase 3 is complete, `classic-constants-core` no longer exists as a separate crate, and its 1214 lines of content are redistributed as follows:

- `Fallout4Version` enum + all impls + `NULL_VERSION` const → `classic-version-registry-core`
- `YamlFile` enum + impls AND `SETTINGS_IGNORE_NONE` + `must_not_be_none()` → `classic-settings-core`
- `GameId` enum + impls → `classic-shared-core` (foundation layer)

The convenience re-exports of `{MatchConfidence, MatchResult, VersionInfo, VersionRegistry, VersionRegistryError, get_version_registry}` (which constants-core currently passes through from version-registry-core) are removed; consumers import those types directly from `classic-version-registry-core`.

All binding crates (C++ bridge, Node, Python) disperse their constants-module contents across the three new target binding modules. `classic-constants-py` is deleted entirely and its wrappers are carved across `classic-version-registry-py`, `classic-settings-py`, and `classic-shared-py`. The `classic::constants` CXX namespace disappears; bridge types move into `classic::version_registry`, `classic::settings`, and a **new** `classic::shared` namespace backed by a new `classic-cpp-bridge/src/shared.rs` module.

All three parity gate baselines (CXX, Python, Node) are regenerated to reflect the redistribution. Zero consumer-visible *behavioral* change — but import paths and source-path metadata change everywhere.

**Scope deviation from roadmap:** The original ROADMAP.md and REQUIREMENTS.md text lock the target as `classic-version-registry-core` alone (CNST-01, CNST-02). This phase deliberately deviates because the roadmap goal "all game/version identity constants live in classic-version-registry-core" was imprecise — `YamlFile` is not version identity and `GameId` is foundation-layer game identity that every layer needs. A **quick-task commit lands the roadmap amendment before Phase 3 planning begins** (see D-01 below).

</domain>

<decisions>
## Implementation Decisions

### Roadmap amendment (blocking quick-task)
- **D-01:** A quick-task commit amends `ROADMAP.md`, `REQUIREMENTS.md`, and `PROJECT.md` BEFORE `/gsd:plan-phase 3` runs. The amendment:
  - Renames Phase 3 title from "Constants -> Version Registry Merge" to "Constants Redistribution" in ROADMAP.md
  - Updates the Phase 3 Goal paragraph to describe three-target redistribution
  - Rewrites CNST-01 from "relocated into classic-version-registry-core" to "redistributed by semantic domain across version-registry-core (Fallout4Version, NULL_VERSION), settings-core (YamlFile, SETTINGS_IGNORE_NONE, must_not_be_none), and shared-core (GameId)"
  - Rewrites CNST-02 from "consumers import from classic-version-registry-core" to "consumers import from the new semantic-domain-appropriate crate"
  - CNST-03 stays unchanged (constants-core still gets deleted)
  - Updates the `v9.1.0-consolidation` milestone target-feature bullet that mentions "Merge classic-constants-core into classic-version-registry-core"
  - Updates PROJECT.md "Current milestone" target-features section to reflect the split
  - The commit is a pure-docs Chore. No code churn. Ships independently before Phase 3 planning so the plan agent reads amended requirements.

### Rust core destinations (three-way split, forced by D-01 / 6=b)
- **D-02:** `Fallout4Version` enum + all its `impl` blocks + `NULL_VERSION: Version` const → `classic-version-registry-core` as a new submodule `fallout4_version.rs` (single flat file, not further split). Re-exported flat at the crate root via `pub use fallout4_version::*;`. Post-merge, `Fallout4Version::get_version_info()`'s call to `get_version_registry()` becomes an in-crate call rather than a cross-crate call — a natural simplification.
- **D-03:** `YamlFile` enum + impls + `SETTINGS_IGNORE_NONE: &[&str]` const + `must_not_be_none(key: &str) -> bool` function → `classic-settings-core` as a new submodule `yaml_file.rs`. Flat re-exports at crate root. This absorbs SETTINGS_IGNORE_NONE and must_not_be_none alongside YamlFile because they are all settings-domain content.
- **D-04:** `GameId` enum + impls → `classic-shared-core` (foundation layer) as a new submodule `game_id.rs`. Flat re-exports at crate root. This makes `GameId` available to every layer of the workspace without a business-logic crate dependency, which is the architectural win of the redistribution.
- **D-05:** The top-of-file convenience re-exports `pub use classic_version_registry_core::{MatchConfidence, MatchResult, VersionInfo, VersionRegistry, VersionRegistryError, get_version_registry};` in constants-core are NOT carried to any target. Consumers that relied on them (notably `classic-version-core/src/lib.rs` which has `pub use classic_constants_core::{VersionInfo, VersionRegistry, ...}`) must add direct imports from `classic-version-registry-core` during the consumer sweep.

### Re-export strategy (carry-forward from Phase 1 D-04 and Phase 2 D-03)
- **D-06:** Flat `pub use submodule::*;` at each target crate root. Consumers migrate by swapping `classic_constants_core::X` to `{classic_version_registry_core, classic_settings_core, classic_shared_core}::X` depending on symbol.

### Git history preservation (carry-forward from Phase 1 D-15 and Phase 2 D-13)
- **D-07:** Use `git mv` for each of the three destination moves. Because constants-core/src/lib.rs is a single file being split three ways, a literal single `git mv` is not possible — the preferred sequence is:
  1. First commit: three `git mv` operations using `git mv` + immediate content delete to carve the source file into three destination files under unique names. If a single `git mv` cannot preserve blame across a three-way file split, fall back to one `git mv` for the largest share (Fallout4Version + NULL_VERSION → `fallout4_version.rs`, which is ~500 of 1214 lines) and `git rm` + new-file creation for the other two shares (YamlFile and GameId). Accept that `YamlFile` and `GameId` lose direct blame linkage — the compensation is that each chunk starts its life in a semantically-correct home.
  2. Second commit: content edits (fix imports, remove the convenience re-exports, add `pub use` lines at each target crate root, strip the old `pub use classic_version_registry_core::{...}` block from the Fallout4Version chunk because those types are now local).
- **D-08:** Document the chosen blame trade-off in the commit message for the first move commit so reviewers understand which slice got blame preservation and why.

### Rust core consumer sweep (5 crates to touch)
- **D-09:** `classic-xse-core` uses only `GameId` — swap `classic-constants-core = ...` dep to `classic-shared-core = ...` in Cargo.toml (already a transitive dep via `classic-shared-core`), update `src/lib.rs` imports `classic_constants_core::GameId` → `classic_shared_core::GameId`.
- **D-10:** `classic-web-core` uses only `GameId` — swap dep, update `src/lib.rs` imports (6 references). Same as D-09.
- **D-11:** `classic-version-core` uses `NULL_VERSION` AND the convenience re-exports — swap `classic-constants-core` dep to `classic-version-registry-core` (may already be present), update `src/lib.rs` `pub use classic_constants_core::{...}` to `pub use classic_version_registry_core::{VersionInfo, VersionRegistry, VersionRegistryError, get_version_registry, NULL_VERSION};`.
- **D-12:** `classic-resource-core` — needs Cargo.toml inspection during planning to determine which constants-core symbols are used and which target crates are needed.
- **D-13:** `classic-tui` uses `Fallout4Version` only (`src/app.rs`) — swap dep to `classic-version-registry-core`, update import.
- **D-14:** No consumer gains a dep that introduces a new transitive graph — all three targets (`classic-version-registry-core`, `classic-settings-core`, `classic-shared-core`) are already in the transitive closure of every consumer, so Cargo.toml edits are swaps, not additions.

### Python binding 3-way carve (not a single fold)
- **D-15:** Delete `classic-constants-py` entirely (crate directory, workspace member entry, `.pyi` stub, `dist-rust` artifacts). Its 787 lines of wrappers get carved across three existing py crates:
  - `PyFallout4Version` wrapper + impl methods → `classic-version-registry-py` (new submodule `fallout4_version.rs`, same layout pattern as existing `matching.rs`, `models.rs`)
  - `PyYamlFile` wrapper + `PySETTINGS_IGNORE_NONE` getter + `must_not_be_none` function binding → `classic-settings-py` (new submodule `yaml_file.rs`)
  - `PyGameId` wrapper → `classic-shared-py` (foundation py crate). If `classic-shared-py` has no prior `#[pymodule]` game-identity content, this adds a new public type to that module for the first time — acceptable; foundation-layer py crates are allowed to grow.
- **D-16:** The `#[pymodule]` fn in each target crate gains a new `m.add_class::<Py...>()?;` registration line for the new types. Update the corresponding `.pyi` stub files: delete `classic_constants.pyi`, add sections to `classic_version_registry.pyi`, `classic_settings.pyi`, and `classic_shared.pyi`.
- **D-17:** Python consumers migrate from `import classic_constants` to the three new import sites: `from classic_version_registry import Fallout4Version`, `from classic_settings import YamlFile, SETTINGS_IGNORE_NONE, must_not_be_none`, `from classic_shared import GameId`. Test files and the `classic-scanlog-py` binding that imports constants-py types get swept.
- **D-18:** `classic-scanlog-py` currently has `classic-constants-core` in its Cargo.toml — during planning, enumerate its exact symbol usage and route each symbol to the correct target crate. Same treatment as Rust core consumers in D-09..D-13.

### Node binding module dispersal
- **D-19:** Merge the contents of `classic-node/src/constants.rs` (198 lines) into the three existing peer modules:
  - `JsFallout4Version` + impls → `classic-node/src/version_registry.rs`
  - `JsYamlFile` + impls + any SETTINGS_IGNORE_NONE / must_not_be_none bindings → `classic-node/src/settings.rs`
  - `JsGameId` + impls → `classic-node/src/shared.rs` (already exists)
- **D-20:** Delete `classic-node/src/constants.rs`. Update `classic-node/src/lib.rs` module declarations to drop `mod constants;`. No re-exports at the NAPI layer need churn — NAPI auto-registers types by `#[napi]` annotation regardless of module location, and `index.d.ts` regenerates during the build so symbol locations update automatically. However, because symbol-to-module mapping changes, the Node parity baseline MUST be regenerated (see D-26).
- **D-21:** Other Node binding modules that import from `classic_constants_core::*` (`xse.rs`, `web.rs`, `scanlog.rs` — all use `GameId`) swap their imports to `classic_shared_core::GameId`.

### CXX bridge dispersal + new `shared.rs` module
- **D-22:** Create a new CXX bridge module `classic-cpp-bridge/src/shared.rs` with namespace `classic::shared`. This is the destination for `GameId` bridge types and any future foundation-layer shared types. The module follows the established bridge conventions (`#[cxx::bridge] namespace = "classic::shared"`, opaque types where needed, DTO types defined in the bridge block).
- **D-23:** The new `shared.rs` module requires **five-place registration** (the Phase 1 D-09 learning: the CXX bridge module list lives in `lib.rs`, `build.rs`, `Cargo.toml`, `include/classic_cxx_bridge/` header directory, AND `classic-cli/CMakeLists.txt` / `classic-gui/CMakeLists.txt` generated-header globs). The planner must explicitly include the five-place add-step; missing any one is a silent runtime failure. This is the memory entry about 4-place → 5-place bridge registration.
- **D-24:** Disperse the contents of `classic-cpp-bridge/src/constants.rs` (419 lines) into the three target modules:
  - `Fallout4Version` bridge types and any delegating fns → `classic-cpp-bridge/src/version_registry.rs` (namespace `classic::version_registry`, which already exists)
  - `YamlFile` bridge types + `must_not_be_none` bridge fn → `classic-cpp-bridge/src/settings.rs` (namespace `classic::settings`, which already exists)
  - `GameId` bridge types → `classic-cpp-bridge/src/shared.rs` (namespace `classic::shared`, new per D-22)
- **D-25:** Delete `classic-cpp-bridge/src/constants.rs`, remove `mod constants;` from `lib.rs`, remove constants entry from `build.rs` bridge list, remove the generated-header entry, remove the CMakeLists glob entry. The CXX namespace `classic::constants` is permanently retired.
- **D-25a:** Other CXX bridge modules that import from `classic_constants_core::*` (`xse.rs`, `web.rs` — both use `GameId`; `path.rs` — uses `Fallout4Version`) swap their imports to the appropriate new target (`classic_shared_core::GameId`, `classic_version_registry_core::Fallout4Version`).

### Parity gate strategy (regenerate ALL THREE baselines)
- **D-26:** Regenerate **all three** parity gate baselines (CXX, Python, Node) after the merge lands, not just CXX. Rationale: under 6=b the redistribution changes (1) CXX namespaces dramatically — `classic::constants` is gone, `classic::shared` is new, and two existing namespaces grow — which makes CXX baseline regen obvious and mandatory; (2) Python baseline `source_decl` / `source_expr` / source-path fields for every affected symbol change because their source crate is different; (3) Node baseline similarly tracks module origin for every exported symbol. Verify-only would produce noise-floor drift on Python and Node even if no symbol names change. Regenerating is the honest answer to "where does this symbol live now."
- **D-27:** The parity generator submodule-scan fix from Phase 1 (recursive scan of business-logic submodule files via `tools/*_api_parity/generate_baseline.py`) is load-bearing for Phase 3 because the redistribution creates three new submodules in three different target crates. Planner must verify the fix is still active and that each target crate's new submodule is picked up. Memory reference: STATE.md accumulated-context line from Phase 1.

### Plan sizing (4 subplans, not Phase 1's 3)
- **D-28:** Phase 3 uses 4 subplans, grown from Phase 1's 3-plan structure due to the 3-way redistribution:
  - **03-01-PLAN**: Rust core-side redistribution — perform the three `git mv` / `git rm`+new-file operations (D-07, D-08), add `pub use` lines at each target crate root (D-06), content-edit imports to drop the convenience re-exports block (D-05), update the 5 Rust core consumers (D-09..D-13), delete `classic-constants-core` directory, remove from workspace members in `ClassicLib-rs/Cargo.toml`.
  - **03-02-PLAN**: Python binding 3-way carve — split `classic-constants-py` contents across `classic-version-registry-py`, `classic-settings-py`, `classic-shared-py` (D-15, D-16), delete `classic-constants-py`, update `.pyi` stub files (D-16), update Python consumers including `classic-scanlog-py` (D-18).
  - **03-03-PLAN**: Node + CXX bridge dispersal — merge node `constants.rs` into 3 peer modules + delete (D-19, D-20), update Node binding consumers (D-21), create new CXX `shared.rs` module with 5-place registration (D-22, D-23), disperse CXX `constants.rs` into 3 target modules + delete (D-24, D-25), update CXX bridge consumers (D-25a).
  - **03-04-PLAN**: Tests, API docs, parity gate regen — migrate constants-core tests (lines 888-1213 of lib.rs; split tests per content destination), merge `docs/api/classic-constants-core.md` content into the three target API doc pages (or primarily into classic-version-registry-core.md with YamlFile/GameId cross-refs — planner decides), update `docs/api/README.md` index, regenerate all three parity gate baselines (D-26), cross-ref cleanup in active docs (D-29).

### Cross-reference cleanup scope (carry-forward from Phase 1 D-14 and Phase 2 D-15)
- **D-29:** Update references in active docs only: `CLAUDE.md`, `AGENTS.md`, `docs/api/*.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, `.planning/PROJECT.md`, `.planning/codebase/*.md`. Skip archived milestone plans and historical docs (`.planning/milestones/*`, `docs/plans/*`, `docs/prd/complete/*`) — they are snapshots in time.

### API doc handling
- **D-30:** `docs/api/classic-constants-core.md` content is redistributed not simply "merged into one target." Fallout4Version section → `docs/api/classic-version-registry-core.md`. YamlFile + SETTINGS_IGNORE_NONE section → `docs/api/classic-settings-core.md`. GameId section → `docs/api/classic-shared-core.md` (create or expand). Delete `docs/api/classic-constants-core.md`. Update `docs/api/README.md` index to remove the constants entry and expand the three target entries. Update `docs/api/binding-parity-overview.md` to reflect redistributed symbol locations. The third canonical ref `docs/api/classic-cpp-bridge-game-entrypoints.md` which references `classic-constants-core` also needs a sweep.

### Crate deletion + workspace member removal
- **D-31:** `git rm -rf ClassicLib-rs/business-logic/classic-constants-core/` and remove the `"business-logic/classic-constants-core"` entry from the `members = [...]` list in `ClassicLib-rs/Cargo.toml` in the same commit (no half-removed state). Same rule for `classic-constants-py`: `git rm -rf ClassicLib-rs/python-bindings/classic-constants-py/` and remove the workspace member entry in the same commit.

### Blame trade-off documentation
- **D-32:** Because the three-way file split cannot preserve blame across all three destinations, the commit message for the first move commit explicitly documents which content chunks received blame preservation and which did not, so future `git log --follow` investigations know to look back through `classic-constants-core/src/lib.rs` for YamlFile and GameId history.

### Claude's Discretion
- Exact ordering of operations within each subplan's commits
- Internal import organization inside each new submodule file
- Any `#[allow(...)]` lint attributes that need to carry forward with the moved code
- Cargo feature-flag deduplication if any (constants-core has `semver`, `phf`, `serde` — destination crates may already have some)
- Decision on whether to `cargo build --workspace` after each subplan or only at the end (verification frequency tradeoff)
- Internal CXX bridge module layout for the new `shared.rs` (number of #[cxx::bridge] blocks, DTO placement)
- Whether to put SETTINGS_IGNORE_NONE as a standalone const in settings-core or co-locate with YamlFile in `yaml_file.rs` (both work; planner decides)
- Whether D-07's three-way `git mv` fallback actually succeeds with git's rename detection, or whether it degrades to `git rm` + new-file creation — mechanical detail, executor decides at runtime

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Prior phase precedents (carry-forward decisions)
- `.planning/phases/01-yaml-settings-merge/01-CONTEXT.md` — Phase 1 context with D-01 through D-15 decisions (re-export strategy D-04, git history D-15, cross-ref scope D-14, API docs D-13, CXX 5-place bridge registration learned in D-09). Parity gate timing (D-12) is DEPARTED from — Phase 3 regenerates all three baselines.
- `.planning/phases/01-yaml-settings-merge/01-VERIFICATION.md` — Phase 1 verification artifact (template for Phase 3 verification)
- `.planning/phases/02-crashgen-config-merge/02-CONTEXT.md` — Phase 2 context with D-01 through D-18 decisions (single-file absorption pattern D-01/D-02, crate deletion D-11, API docs D-14, cross-ref scope D-15). Phase 3 DEPARTS from single-target absorption because the source content is redistributed across three semantic-domain destinations.
- `.planning/phases/02-crashgen-config-merge/02-VERIFICATION.md` — Phase 2 verification artifact

### Source crate (to be deleted)
- `ClassicLib-rs/business-logic/classic-constants-core/src/lib.rs` — Full 1214-line source. Content mapping:
  - Lines 1-45: module docs and `use` statements (discarded in move)
  - Lines 46-54: convenience `pub use classic_version_registry_core::{...}` block — REMOVED under D-05, not carried to any target
  - Line 61: `NULL_VERSION: Version` const — → version-registry-core (D-02)
  - Lines 46-570: `Fallout4Version` enum + all impls + `Display` + `FromStr` — → version-registry-core as `fallout4_version.rs` (D-02)
  - Lines 572-696: `YamlFile` enum + impls + `Display` — → settings-core as part of `yaml_file.rs` (D-03)
  - Lines 698-838: `GameId` enum + impls + `Display` + `FromStr` — → shared-core as `game_id.rs` (D-04)
  - Lines 840-886: `SETTINGS_IGNORE_NONE: &[&str]` const + `must_not_be_none(key) -> bool` — → settings-core in `yaml_file.rs` (D-03)
  - Lines 888-1213: all `#[cfg(test)] mod tests` — SPLIT by content destination during 03-04-PLAN (D-28)
- `ClassicLib-rs/business-logic/classic-constants-core/Cargo.toml` — Source crate dependencies (semver, phf, serde, classic-version-registry-core). None of these are new to any target crate.

### Target Rust crates
- `ClassicLib-rs/business-logic/classic-version-registry-core/src/lib.rs` — Current target for Fallout4Version + NULL_VERSION. Current crate root declares `mod defaults; mod error; mod matching; mod models; mod registry; mod version;`. Will add `mod fallout4_version;` and `pub use fallout4_version::*;`.
- `ClassicLib-rs/business-logic/classic-version-registry-core/Cargo.toml` — Current deps are classic-shared-core + classic-settings-core + yaml-rust2 + thiserror. Will need to add `semver` to deps (because Fallout4Version uses `semver::Version` via NULL_VERSION and `version_semver()`). Verify against workspace dep list.
- `ClassicLib-rs/business-logic/classic-settings-core/Cargo.toml` — Current target for YamlFile + SETTINGS_IGNORE_NONE + must_not_be_none. Will need to verify `serde` feature flags for YamlFile derive.
- `ClassicLib-rs/business-logic/classic-settings-core/src/lib.rs` — Crate root (already expanded in Phase 1 to absorb yaml-core content). Will add `mod yaml_file; pub use yaml_file::*;`.
- `ClassicLib-rs/foundation/classic-shared-core/src/lib.rs` — Target for GameId. Current contents: shared runtime, error types, path helpers, performance primitives, string utilities. Will add `mod game_id; pub use game_id::*;`. Verify `serde` is already in deps (GameId derives Serialize/Deserialize).
- `ClassicLib-rs/foundation/classic-shared-core/Cargo.toml` — Shared-core deps. Will need `serde` + derive feature if not present; `phf` if GameId uses it.

### Workspace root
- `ClassicLib-rs/Cargo.toml` — Workspace members list. `classic-constants-core` AND `classic-constants-py` entries to remove.

### Rust core consumers (5 crates, import path updates; each may need 1-3 target dep additions)
- `ClassicLib-rs/business-logic/classic-xse-core/Cargo.toml` — Swap constants-core dep to shared-core (D-09)
- `ClassicLib-rs/business-logic/classic-xse-core/src/lib.rs` — 1 import reference (`use classic_constants_core::GameId;` on line 26, plus 1 doc reference)
- `ClassicLib-rs/business-logic/classic-web-core/Cargo.toml` — Swap constants-core dep to shared-core (D-10)
- `ClassicLib-rs/business-logic/classic-web-core/src/lib.rs` — 6+ references to `classic_constants_core::GameId` (lines 283, 289, 291-294, 442, 582)
- `ClassicLib-rs/business-logic/classic-version-core/Cargo.toml` — Swap constants-core dep to version-registry-core (D-11); verify version-registry-core is not already present
- `ClassicLib-rs/business-logic/classic-version-core/src/lib.rs` — Lines 48-54: `pub use classic_constants_core::{...}` block needs rewriting to point at version-registry-core
- `ClassicLib-rs/business-logic/classic-resource-core/Cargo.toml` — Needs planning-time symbol enumeration (D-12)
- `ClassicLib-rs/ui-applications/classic-tui/Cargo.toml` — Swap constants-core dep to version-registry-core (D-13)
- `ClassicLib-rs/ui-applications/classic-tui/src/app.rs` — Line 7 import of Fallout4Version
- `ClassicLib-rs/business-logic/classic-registry-core/src/registry.rs` + `src/keys.rs` — Doc comments reference `classic_constants_core::Fallout4Version` (2 lines total); swap to version-registry-core

### Python binding carve (source, targets, and consumers)
- `ClassicLib-rs/python-bindings/classic-constants-py/src/lib.rs` — 787 lines to disperse across three target py crates (D-15, D-16)
- `ClassicLib-rs/python-bindings/classic-constants-py/classic_constants.pyi` — Type stubs to disperse and delete
- `ClassicLib-rs/python-bindings/classic-constants-py/Cargo.toml` — To be deleted (crate removal)
- `ClassicLib-rs/python-bindings/classic-version-registry-py/src/lib.rs` — Target for PyFallout4Version; current contents are matching/models/registry/version submodules
- `ClassicLib-rs/python-bindings/classic-version-registry-py/classic_version_registry.pyi` — Expand with Fallout4Version stubs
- `ClassicLib-rs/python-bindings/classic-settings-py/src/lib.rs` — Target for PyYamlFile + PySETTINGS_IGNORE_NONE + must_not_be_none binding
- `ClassicLib-rs/python-bindings/classic-settings-py/classic_settings.pyi` — Expand with YamlFile stubs
- `ClassicLib-rs/foundation/classic-shared-py/src/lib.rs` — Target for PyGameId (foundation py crate; may be adding its first public class)
- `ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi` — Expand with GameId stubs
- `ClassicLib-rs/python-bindings/classic-scanlog-py/Cargo.toml` — Has classic-constants-core dep; needs symbol enumeration (D-18)
- `ClassicLib-rs/python-bindings/classic-scanlog-py/src/fcx_handler.rs` — References classic_constants_core; swap to appropriate target per symbol

### Node binding dispersal (source, targets, consumers)
- `ClassicLib-rs/node-bindings/classic-node/src/constants.rs` — 198-line source to disperse (D-19, D-20); line 6 imports `{Fallout4Version, GameId, YamlFile}`
- `ClassicLib-rs/node-bindings/classic-node/src/version_registry.rs` — Target for JsFallout4Version
- `ClassicLib-rs/node-bindings/classic-node/src/settings.rs` — Target for JsYamlFile + settings-constants bindings
- `ClassicLib-rs/node-bindings/classic-node/src/shared.rs` — Target for JsGameId (existing module)
- `ClassicLib-rs/node-bindings/classic-node/src/lib.rs` — Remove `mod constants;` declaration
- `ClassicLib-rs/node-bindings/classic-node/src/xse.rs` — Line 7 `use classic_constants_core::GameId;` — swap to shared-core
- `ClassicLib-rs/node-bindings/classic-node/src/web.rs` — Line 7 `use classic_constants_core::GameId;` — swap to shared-core
- `ClassicLib-rs/node-bindings/classic-node/src/scanlog.rs` — Line 15 `use classic_constants_core::GameId;` — swap to shared-core
- `ClassicLib-rs/node-bindings/classic-node/Cargo.toml` — Swap constants-core dep to shared-core + version-registry-core + settings-core (combination check against existing deps)

### CXX bridge dispersal + new `shared.rs` (source, targets, consumers, registration sites)
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs` — 419-line source to disperse (D-24, D-25); line 43 imports `classic_constants_core::{...}`; references Fallout4Version, GameId, YamlFile, must_not_be_none
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/version_registry.rs` — Target for Fallout4Version bridge types (namespace `classic::version_registry`)
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/settings.rs` — Target for YamlFile bridge types + must_not_be_none bridge fn (namespace `classic::settings`)
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/shared.rs` — **TO BE CREATED** (D-22); namespace `classic::shared`; target for GameId bridge types
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs` — Module declarations: add `mod shared;`, remove `mod constants;`
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs` — CXX bridge list: add `shared` entry, remove `constants` entry
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/Cargo.toml` — Swap constants-core dep to shared-core + version-registry-core + settings-core
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/include/classic_cxx_bridge/` — Generated-header directory: shared header to be added, constants header removed (regenerated from build.rs)
- `classic-cli/CMakeLists.txt` — CMake generated-header glob or explicit list entries (5th-place registration site per D-23)
- `classic-gui/CMakeLists.txt` — CMake generated-header glob or explicit list entries (5th-place registration site per D-23)
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/xse.rs` — Line 12 `use classic_constants_core::GameId;` — swap to shared-core
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/web.rs` — Line 36 `use classic_constants_core::GameId as CoreGameId;` — swap to shared-core
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs` — Line 29 `use classic_constants_core::Fallout4Version;` — swap to version-registry-core

### Parity gates (regenerate all three)
- `tools/cxx_api_parity/` — CXX parity gate tooling. Regenerate baseline after CXX namespace redistribution (D-26). Per Phase 1 learning, the CXX parity generator scans build.rs module list.
- `tools/python_api_parity/check_parity_gate.py` — Python parity gate. Regenerate baseline; expect `deferred_total == 0`. Submodule-scan fix from Phase 1 is load-bearing (D-27).
- `tools/python_api_parity/generate_baseline.py` — Python baseline generator; must scan the new submodules inside version-registry-core, settings-core, shared-core.
- `ClassicLib-rs/node-bindings/classic-node/` — Node parity gate entry: `bun run parity:gate:local`. Regenerate baseline.
- `ClassicLib-rs/python-bindings/parity-artifacts/rust_api_surface.json` — Current Python parity baseline (confirmed to contain `pub use classic_constants_core::NULL_VERSION`, `classic_constants_core::VersionInfo`, `classic_constants_core::VersionRegistry`, `classic_constants_core::VersionRegistryError`, `classic_constants_core::get_version_registry`, `classic_constants_core::GameId` entries — all of which will change source-crate attribution)
- `docs/implementation/node_api_parity/baseline/rust_api_surface.json` — Node baseline (same redistribution impact)

### API documentation
- `docs/api/classic-constants-core.md` — Source API doc to disperse across three targets, then delete (D-30)
- `docs/api/classic-version-registry-core.md` — Expand with Fallout4Version section
- `docs/api/classic-settings-core.md` — Expand with YamlFile + SETTINGS_IGNORE_NONE section
- `docs/api/classic-shared-core.md` — Expand or create with GameId section
- `docs/api/README.md` — Remove constants-core entry, expand the three target entries
- `docs/api/binding-parity-overview.md` — Update symbol locations
- `docs/api/classic-cpp-bridge-game-entrypoints.md` — References constants-core; sweep
- `docs/api/game-setup-workflow.md` — References classic_constants_core; sweep
- `docs/api/classic-web-core.md` — References classic_constants_core; sweep
- `docs/api/classic-xse-core.md` — References classic_constants_core; sweep

### Roadmap / requirements amendment targets (for quick-task, D-01)
- `.planning/ROADMAP.md` — Phase 3 title + Phase 3 Goal paragraph + milestone feature bullet
- `.planning/REQUIREMENTS.md` — CNST-01, CNST-02 rewrites; CNST-03 unchanged; Traceability table status stays "Pending"
- `.planning/PROJECT.md` — "Current Milestone" target-features section

### Cross-reference cleanup (active docs only)
- `CLAUDE.md` — Tech stack section; PROJECT section mentions crate count — should update to 16
- `AGENTS.md` — No direct constants-core reference expected; sweep anyway
- `.planning/codebase/*.md` — Codebase map references

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `classic-version-registry-core/src/lib.rs` already has a clean `mod` declaration pattern (`mod defaults; mod error; mod matching; mod models; mod registry; mod version;` + flat re-exports) — adding `mod fallout4_version; pub use fallout4_version::*;` is a 2-line low-risk change
- `classic-settings-core/src/lib.rs` was already expanded in Phase 1 (absorbed yaml-core as `yaml_ops.rs` and `yaml_merge.rs`) — the re-export pattern is proven; adding `mod yaml_file;` is the same shape
- `classic-shared-core` is the foundation crate with zero business-logic dependencies — adding `GameId` as `mod game_id;` does not create any circular dependency risk because GameId is a pure serde-derived enum with no external type dependencies
- `classic-node/src/shared.rs` already exists — target module for JsGameId is pre-built
- `classic-version-registry-py/src/` has a multi-file structure (matching/models/registry/version) — adding `fallout4_version.rs` as a new submodule file matches the existing convention cleanly
- The Phase 1 5-place CXX bridge registration pattern (lib.rs + build.rs + Cargo.toml + generated-headers + CMakeLists) is documented in STATE.md Phase 1 accumulated context — the planner can reuse the learning directly when adding `shared.rs`

### Established Patterns
- **Absorb-into-semantic-home rule (NEW, Phase 3 precedent)**: instead of Phase 1/2's "absorb into the heaviest consumer" rule, Phase 3 establishes "redistribute by semantic domain." When a source crate contains multiple domains (version, settings, identity), each domain goes to its natural home rather than being co-located under whichever destination had the most consumers. This pattern may apply to future consolidation phases if they encounter multi-domain source crates.
- **Flat re-exports** at crate root (`pub use submodule::*;`) — standard pattern across all merged crates (Phase 1 D-04, Phase 2 D-03, Phase 3 D-06)
- **git mv then content edits** — preserve blame history; fails gracefully to `git rm` + new-file creation when source cannot be three-way-split. Phase 3 D-07 documents the trade-off explicitly.
- **Parity gate baselines track EXPOSED binding API**, but Python and Node baselines include source-path metadata that shifts when content relocates, so regeneration is needed even when symbol names are identical. Phase 3 D-26 makes this explicit.
- **5-place CXX bridge module registration** — lib.rs `mod`, build.rs bridge list, Cargo.toml, include/ header dir, CMakeLists.txt glob. Phase 1 D-09 learned this the hard way; Phase 3 D-23 locks it in for the new `shared.rs`.
- **Multi-file submodule layout in target crates** — version-registry-core has 6 submodule files; settings-core has multiple; shared-core has foundation helpers. Adding one new submodule file to each of the three is a pattern, not a surprise.

### Integration Points
- `classic-version-registry-core` is the primary absorption target for version-domain content; Fallout4Version's existing `get_version_registry()` call becomes an in-crate call post-merge (clean simplification)
- `classic-settings-core` is the absorption target for YAML-domain content; already expanded in Phase 1, ready for another submodule
- `classic-shared-core` (foundation) is the absorption target for game-identity content; makes `GameId` available to every layer without a business-logic dependency edge
- The `classic::constants` CXX namespace disappears entirely; `classic::shared` namespace is introduced for the first time
- `ClassicLib-rs/Cargo.toml` workspace members list needs TWO entries removed (`classic-constants-core` AND `classic-constants-py`)
- `Cargo.lock` updates automatically when `classic-constants-core` and `classic-constants-py` are removed and consumers' dep lists change
- The CI-enforced parity gates (per v9.1.0-bindings Phase 5) will catch any dispersal mistake — this is a safety net, not a primary verification

</code_context>

<specifics>
## Specific Ideas

- **User explicitly rejected the flat merge direction.** The roadmap's chosen target (version-registry-core for everything) was semantically imprecise because YamlFile is not version-identity and GameId is foundation-layer game-identity. Redistribution by domain is a conscious architectural improvement that the planner should NOT try to "simplify back" to a flat merge.
- **Roadmap amendment is a blocking prerequisite.** `/gsd:plan-phase 3` MUST NOT start until the quick-task commit lands that updates ROADMAP.md, REQUIREMENTS.md, and PROJECT.md to reflect the three-target redistribution. The plan agent reads these files to understand scope; stale scope = wrong plan.
- **User explicitly chose to create a new CXX `shared.rs` module with `classic::shared` namespace** rather than reusing `game.rs`, `types.rs`, or inlining GameId bridge types. Rationale: mirror the Rust layer's foundation layout cleanly. The 5-place CXX registration cost is acknowledged and accepted.
- **All three parity gate baselines regenerate** — this is a DELIBERATE departure from Phase 2's verify-only strategy because under redistribution, source-crate attribution changes for every moved symbol, which is real baseline drift even when no symbol names change.
- **`classic-shared-py` may gain its first public class** (PyGameId). Foundation py crates are allowed to grow when a foundation-domain type moves in; this is not crate-shape drift.
- **Blame preservation is partial, not complete.** The single 1214-line source file cannot be `git mv`'d three ways; Fallout4Version (the largest chunk) gets blame preservation; YamlFile and GameId get fresh blame starting from Phase 3. The trade-off is documented in the move commit message (D-32) so future debuggers know where to look.
- **Plan count grew from the Phase-1-style 3 to 4** (D-28) because the redistribution expands consumer complexity enough that bundling core + Rust consumer sweep into one subplan while keeping Python carve, Node/CXX dispersal, and tests/docs/gates as three separate subplans keeps each subplan reviewable.
- **The Phase 1 parity generator submodule-scan fix is load-bearing.** If that fix is regressed, Phase 3's new submodules will silently drop symbols from the parity baselines. Planner must verify the fix is active before regeneration (D-27).
- **No new transitive dependency graphs are introduced** — version-registry-core, settings-core, and shared-core are all already in the transitive closure of every consumer, so Cargo.toml edits are swaps, not additions.
- **`deferred-items.md` from Phase 2** lives in `.planning/phases/02-crashgen-config-merge/deferred-items.md` — if any of its items touch constants-core or version-registry, the planner should sweep them during 03-01-PLAN.

</specifics>

<deferred>
## Deferred Ideas

- **Renaming `classic-version-registry-core` to a more descriptive name** (e.g., `classic-version-identity-core` or `classic-fallout-versions-core`) — Phase 3 adds Fallout4Version to it, which keeps the crate name accurate; the original "version-registry absorbing non-version content" tension is resolved by the redistribution, so no rename is needed. Noted here in case a future milestone revisits workspace naming.
- **Retroactively adding tests for `classic-shared-core` GameId behavior** — the migrated tests from constants-core cover GameId directly, but shared-core has no prior test coverage for foundation-layer enums. A future test-coverage phase could expand coverage.
- **Unifying the three Cargo.toml `semver` dep entries into a workspace dep** — during Phase 3, `semver` may become used in 2-3 different target crates. If it isn't already a workspace dep, promoting it would reduce drift. Candidate for a future dep-cleanup phase, NOT Phase 3 scope.
- **A "workspace naming cleanup" phase** — if the milestone revisits workspace structure after consolidation, names like `classic-shared-core` (foundation) vs `classic-shared-py` (same name, different layer) could be rationalized. Not Phase 3 scope.
- **Retiring the `phf` dep from constants-core** — constants-core's Cargo.toml has `phf` listed but the current source file (lines 1-1214) does not visibly use it. This may be dead dep — if so, it can be dropped during the merge rather than propagated. Planner should verify with `cargo +nightly udeps` or manual grep during 03-01-PLAN.
- **Splitting test modules per destination** — Phase 3 already splits the tests (D-28 03-04-PLAN), but a future refactor could consider whether settings-core and shared-core want dedicated `tests/` directories vs inline `#[cfg(test)]` modules. Phase 3 will co-locate tests with the code they cover.
- **Considering GameId → foundation promotion as a repeatable pattern** — if future phases discover other "identity" types that are pure enums with no dependencies, they may belong in shared-core too. Not action for Phase 3, but worth noting as an architectural principle.

</deferred>

---

*Phase: 03-constants-version-registry-merge (slug will be updated by roadmap-amendment quick-task if renamed)*
*Context gathered: 2026-04-11*
