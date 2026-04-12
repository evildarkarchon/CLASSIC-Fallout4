# Phase 3: Constants Redistribution - Research

**Researched:** 2026-04-11
**Domain:** Rust workspace crate redistribution across Rust core and binding layers
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

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

### Deferred Ideas (OUT OF SCOPE)
- **Renaming `classic-version-registry-core` to a more descriptive name** (e.g., `classic-version-identity-core` or `classic-fallout-versions-core`) — Phase 3 adds Fallout4Version to it, which keeps the crate name accurate; the original "version-registry absorbing non-version content" tension is resolved by the redistribution, so no rename is needed. Noted here in case a future milestone revisits workspace naming.
- **Retroactively adding tests for `classic-shared-core` GameId behavior** — the migrated tests from constants-core cover GameId directly, but shared-core has no prior test coverage for foundation-layer enums. A future test-coverage phase could expand coverage.
- **Unifying the three Cargo.toml `semver` dep entries into a workspace dep** — during Phase 3, `semver` may become used in 2-3 different target crates. If it isn't already a workspace dep, promoting it would reduce drift. Candidate for a future dep-cleanup phase, NOT Phase 3 scope.
- **A "workspace naming cleanup" phase** — if the milestone revisits workspace structure after consolidation, names like `classic-shared-core` (foundation) vs `classic-shared-py` (same name, different layer) could be rationalized. Not Phase 3 scope.
- **Retiring the `phf` dep from constants-core** — constants-core's Cargo.toml has `phf` listed but the current source file (lines 1-1214) does not visibly use it. This may be dead dep — if so, it can be dropped during the merge rather than propagated. Planner should verify with `cargo +nightly udeps` or manual grep during 03-01-PLAN.
- **Splitting test modules per destination** — Phase 3 already splits the tests (D-28 03-04-PLAN), but a future refactor could consider whether settings-core and shared-core want dedicated `tests/` directories vs inline `#[cfg(test)]` modules. Phase 3 will co-locate tests with the code they cover.
- **Considering GameId → foundation promotion as a repeatable pattern** — if future phases discover other "identity" types that are pure enums with no dependencies, they may belong in shared-core too. Not action for Phase 3, but worth noting as an architectural principle.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CNST-01 | `classic-constants-core` source modules are redistributed by semantic domain: Fallout4Version + NULL_VERSION to `classic-version-registry-core`, YamlFile + `SETTINGS_IGNORE_NONE` + `must_not_be_none` to `classic-settings-core`, and GameId to `classic-shared-core`, with the same public API names preserved at their new locations | Standard Stack, Architecture Patterns 1-3, Code Examples 1-4, Common Pitfalls 1/2/4 |
| CNST-02 | All workspace crates that imported from `classic-constants-core` now import from the semantic-domain-appropriate target crate (`classic-version-registry-core`, `classic-settings-core`, or `classic-shared-core`) depending on which symbol they use | Architecture Patterns 2/4, Don't Hand-Roll 1/3, Common Pitfalls 2/3/5 |
| CNST-03 | `classic-constants-core` crate is removed from `Cargo.toml` workspace members and its directory deleted | Architecture Patterns 4, Runtime State Inventory, Validation Architecture |
</phase_requirements>

## Summary

This phase is not a library-selection problem; it is a topology-preserving redistribution problem. The safest implementation is to move each symbol family to its semantic home, keep the public names flat at the target crate roots, then sweep every consumer and every parity tool that still assumes a dedicated `classic-constants-core` owner. The repo already has the pattern: Phase 1 and Phase 2 absorbed source into destination submodules and re-exported from `lib.rs`; Phase 3 repeats that pattern three times instead of once.

The hidden work is in the binding and tooling surface, not the Rust enum code. `classic-constants-core` is currently a root-only crate, but its symbols are reflected in Node tests, Python smoke tests, PyO3 stubs, CXX namespaces, parity generator target maps, API docs, and workspace membership lists. If the planner treats this as a simple Rust move, the build will fail late and the parity baselines will drift noisily.

**Primary recommendation:** Redistribute into three new target submodules with flat crate-root re-exports, then immediately do a full consumer/parity/docs sweep before deleting `classic-constants-core` and `classic-constants-py`.

## Project Constraints (from AGENTS.md)

- Prioritize active work in `classic-cli/`, `classic-gui/`, and `ClassicLib-rs/`.
- Keep all business logic in Rust; binding/UI layers stay thin wrappers.
- Maintain a single shared Tokio runtime from Rust core facilities; do not introduce another runtime.
- Keep docs synchronized with architecture/workflow changes, especially `README.md` and `AGENTS.md`.
- Never write to `NUL` or `nul` on Windows.
- Consult `docs/api/README.md` before changing public Rust, bridge, GUI-consumer, or binding-facing APIs; update affected `docs/api/` pages in the same change.
- Never run raw `ctest` or direct C++ test binaries; use `classic-cli/build_cli.ps1 -Test` or `classic-gui/build_gui.ps1 -Test`.
- Windows/MSVC constraints apply for native C++ surfaces.
- Python and Node bindings must stay in sync with Rust core logic.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `classic-version-registry-core` | 9.0.0 | New semantic home for `Fallout4Version`, `NULL_VERSION`, direct registry-facing re-exports | Already owns version metadata and `get_version_registry()`; moving version identity here removes an artificial convenience layer |
| `classic-settings-core` | 9.0.0 | New semantic home for `YamlFile`, `SETTINGS_IGNORE_NONE`, `must_not_be_none` | Already owns YAML/settings concerns and Phase 1 proved the submodule + flat re-export pattern |
| `classic-shared-core` | 9.0.0 | New foundation-layer home for `GameId` | Makes game identity available without depending on a business-logic crate |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pyo3` | 0.27.2 | Python binding registration and `#[pyclass]` exposure | For carving `classic-constants-py` into target `-py` crates |
| `napi` / `napi-derive` | 3 / 3 | Node binding exports with `#[napi]` | For moving `JsFallout4Version`, `JsYamlFile`, `JsGameId` into semantic modules |
| `cxx` / `cxx-build` | 1.0 / 1.0 | C++ bridge modules and generated headers | For retiring `classic::constants` and adding `classic::shared` |
| `serde` | 1.0 (workspace) | Preserve enum serialization derives | Required by moved Rust enums |
| `semver` | 1.0 (workspace) | `NULL_VERSION` and `version_semver()` | Required in `classic-version-registry-core` after move |
| `yaml-rust2` | 0.11.0 (workspace) | Existing settings crate support | Already pinned in target settings workflow |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Semantic 3-way redistribution | Flat merge into `classic-version-registry-core` | Contradicts locked scope and keeps non-version symbols in the wrong crate |
| Flat crate-root re-exports | Force callers onto new submodule paths | Causes avoidable consumer churn and breaks the proven Phase 1/2 migration pattern |
| Regenerating all three parity baselines | Verify-only for Python/Node | Incorrect for this phase because source-path ownership changes are real baseline drift |

**Installation:**
```bash
cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml
```

**Version verification:** Repo-pinned versions were verified in `ClassicLib-rs/Cargo.toml`, target crate `Cargo.toml` files, and `ClassicLib-rs/node-bindings/classic-node/package.json` on 2026-04-11. This phase should not introduce alternate libraries.

## Architecture Patterns

### Recommended Project Structure
```text
ClassicLib-rs/
├── business-logic/
│   ├── classic-version-registry-core/
│   │   └── src/
│   │       ├── lib.rs              # add mod fallout4_version; pub use fallout4_version::*;
│   │       └── fallout4_version.rs # moved Fallout4Version + NULL_VERSION
│   └── classic-settings-core/
│       └── src/
│           ├── lib.rs              # add mod yaml_file; pub use yaml_file::*;
│           └── yaml_file.rs        # moved YamlFile + settings constants
├── foundation/
│   └── classic-shared-core/
│       └── src/
│           ├── lib.rs              # add mod game_id; pub use game_id::*;
│           └── game_id.rs          # moved GameId
└── bindings/
    ├── python-bindings/*           # carve wrappers/stubs into existing target crates
    ├── node-bindings/classic-node/ # disperse constants.rs into shared/settings/version_registry
    └── cpp-bindings/classic-cpp-bridge/ # disperse constants.rs; add shared.rs
```

### Pattern 1: Semantic-home redistribution + flat crate-root re-exports
**What:** Move code into one new destination submodule per target crate, then re-export at the crate root with `pub use`.
**When to use:** For every Rust-core symbol moved out of `classic-constants-core`.
**Example:**
```rust
// Source: ClassicLib-rs/business-logic/classic-version-registry-core/src/lib.rs
mod fallout4_version;

pub use fallout4_version::*;
pub use registry::{VersionRegistry, get_version_registry};
```

### Pattern 2: Thin binding dispersal into existing semantic modules
**What:** Move binding wrappers into the target module that already owns the related core crate instead of preserving a binding-side `constants` bucket.
**When to use:** Node `constants.rs`, Python `classic-constants-py`, and CXX `constants.rs`.
**Example:**
```rust
// Source: ClassicLib-rs/python-bindings/classic-version-registry-py/src/lib.rs
mod fallout4_version;

#[pymodule]
fn classic_version_registry(m: &Bound<'_, PyModule>) -> PyResult<()> {
    fallout4_version::register(m)?;
    Ok(())
}
```

### Pattern 3: Direct-import consumer sweep, not re-export preservation
**What:** Replace old `classic_constants_core::*` imports with direct imports from the owning target crate.
**When to use:** Every Rust, Node, Python, and CXX consumer.
**Example:**
```rust
// Source: ClassicLib-rs/business-logic/classic-version-core/src/lib.rs
pub use classic_version_registry_core::{
    VersionInfo, VersionRegistry, VersionRegistryError, get_version_registry, NULL_VERSION,
};
```

### Pattern 4: Delete source crates only after the workspace is in a compilable state
**What:** Update destination modules, target root re-exports, consumer imports, parity-generator target maps, and workspace members before the final delete commit leaves no references.
**When to use:** `classic-constants-core` and `classic-constants-py` deletion.
**Example:**
```rust
// Source: /dtolnay/cxx via Context7 and repo build.rs pattern
cxx_build::bridges([
    "src/settings.rs",
    "src/version_registry.rs",
    "src/shared.rs",
])
.include("include")
.compile("classic-cpp-bridge");
```

### Anti-Patterns to Avoid
- **Keeping the convenience re-exports alive somewhere else:** That recreates the deleted crate's role and hides the semantic split.
- **Leaving a `constants` binding module as a forwarding layer:** It defeats the point of redistributing by domain and adds extra parity churn later.
- **Deleting the source crate before toolchain maps are updated:** `tools/python_api_parity/generate_baseline.py` and `tools/node_api_parity/generate_baseline.py` still hardcode `classic-constants-core` today.
- **Assuming docs/comments do not matter:** doc-comment examples and API docs still reference `classic_constants_core` and will become stale search noise.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Version metadata after move | New hardcoded FO4 tables | Existing `get_version_registry()` + moved `Fallout4Version` methods | The repo already treats Version Registry as the source of truth |
| Binding registration glue | Custom ad-hoc registries | Existing `register(m)` PyO3 pattern, `#[napi]` exports, `#[cxx::bridge]` modules | These frameworks already generate the public contract and parity artifacts |
| Baseline refresh | Manual JSON edits | Existing parity generators and local parity gates | Manual edits will drift on source-path metadata and are hard to review |
| C++ headers | Hand-authored bridge headers | `cxx_build::bridges(...)` + Corrosion/CMake registration | Header generation and namespace wiring are already automated |

**Key insight:** The complexity here is ownership bookkeeping, not enum logic. Reuse the repo's existing generators, module patterns, and crate-root re-export convention instead of creating transitional compatibility layers.

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | None — verified by repo/context inspection; this phase renames code ownership, not persisted DB keys or collections | None |
| Live service config | None — no external service/UI-owned config references were identified in phase scope | None |
| OS-registered state | None — no scheduled-task, service, or launcher registrations tied to `classic-constants-core` were identified | None |
| Secrets/env vars | None — no env-var or secret key names referencing `classic-constants-core` were identified | None |
| Build artifacts | Stale installed/importable `classic_constants` Python module, stale generated Node `index.d.ts`, stale parity baselines, and stale CXX generated headers/build outputs remain possible after source edits | Rebuild bindings, regenerate baselines, refresh generated contracts; if local Python env still exposes `classic_constants`, remove/reinstall target modules |

## Common Pitfalls

### Pitfall 1: Recreating `classic-constants-core` as a hidden convenience layer
**What goes wrong:** Planner moves code but leaves root-level convenience re-exports elsewhere.
**Why it happens:** It feels safer than changing consumers.
**How to avoid:** Enforce direct imports from the semantic owner crate and explicitly remove the convenience block.
**Warning signs:** `pub use classic_version_registry_core::{...}` survives in a new "constants-like" file or `classic-version-core` still re-exports through the old path.

### Pitfall 2: Incomplete consumer sweep
**What goes wrong:** Cargo.toml or import paths remain on `classic-constants-core` in consumers, tests, docs, or parity generators.
**Why it happens:** Search focuses on Rust core only.
**How to avoid:** Sweep Rust, Node, Python, CXX, docs, and tooling in the same plan.
**Warning signs:** `grep` still finds `classic-constants-core` or `classic_constants_core` outside archived docs after the move.

### Pitfall 3: Missing the CXX five-place registration for `shared.rs`
**What goes wrong:** `classic::shared` compiles partially or never appears in generated outputs.
**Why it happens:** Only `src/lib.rs` and `build.rs` get updated.
**How to avoid:** Update `src/lib.rs`, `build.rs`, `Cargo.toml`, header generation path expectations, and both CMakeLists files together.
**Warning signs:** Build scripts still list `constants.rs`, or CMake `FILES` lists do not include `shared.rs`.

### Pitfall 4: Orphaned tests after deleting `classic-constants-core`
**What goes wrong:** The old inline tests vanish, but equivalent coverage is not recreated in destination crates and binding tests still import `classic_constants`.
**Why it happens:** Test code was co-located in the deleted crate and a separate Python smoke file still imports the deleted module.
**How to avoid:** Split tests by destination before deleting the source crate and migrate Python/Node smoke tests the same day.
**Warning signs:** `test_promoted_residuals_smoke.py` or `__test__/constants.spec.ts` still reference the old module after Rust code is moved.

### Pitfall 5: Propagating dead dependencies blindly
**What goes wrong:** `phf`/other source-crate deps get copied into all targets even if the moved code does not need them.
**Why it happens:** Copy-paste Cargo edits.
**How to avoid:** Add only dependencies used by the moved slice; verify with build/clippy.
**Warning signs:** `classic-resource-core` keeps a `classic-constants-core` dependency even though no `.rs` usage remains, or target crates gain unused-dependency warnings.

## Code Examples

Verified patterns from repo source and official docs:

### Rust target crate root re-export
```rust
// Source: ClassicLib-rs/business-logic/classic-settings-core/src/lib.rs
mod yaml_file;

pub use yaml_file::*;
```

### PyO3 registration via per-file helper
```rust
// Source: ClassicLib-rs/python-bindings/classic-version-registry-py/src/lib.rs
mod fallout4_version;

#[pymodule]
fn classic_version_registry(m: &Bound<'_, PyModule>) -> PyResult<()> {
    fallout4_version::register(m)?;
    Ok(())
}
```

### NAPI export from any compiled module
```rust
// Source: ClassicLib-rs/node-bindings/classic-node/src/constants.rs
#[napi(string_enum)]
pub enum JsFallout4Version {
    Original,
    NextGen,
    AnniversaryEdition,
    #[napi(value = "VR")]
    Vr,
}

#[napi]
pub fn get_fallout4_version_info(version: JsFallout4Version) -> Fallout4VersionInfo {
    // delegate to core type
}
```

### CXX multi-bridge build registration
```rust
// Source: ClassicLib-rs/cpp-bindings/classic-cpp-bridge/build.rs and /dtolnay/cxx docs via Context7
cxx_build::bridges([
    "src/settings.rs",
    "src/version_registry.rs",
    "src/shared.rs",
])
.include("include")
.std("c++17")
.compile("classic-cpp-bridge");
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Mixed-domain convenience crate (`classic-constants-core`) | Semantic ownership in domain crates | Locked for Phase 3 on 2026-04-11 | Better layering; fewer misleading dependencies |
| Single public root file in source crate | Destination submodule files + flat root re-exports | Proven in Phase 1/2, reused here | Keeps public names stable while allowing internal re-homing |
| Verify-only when symbol names do not change | Regenerate parity baselines when source ownership metadata changes | Explicit in Phase 3 D-26 | Prevents false-positive drift and stale owner/module attribution |

**Deprecated/outdated:**
- `classic::constants` CXX namespace — replaced by `classic::version_registry`, `classic::settings`, and new `classic::shared`
- `classic-constants-py` as a standalone binding crate — replaced by carving wrappers into semantic target crates

## Open Questions

1. **Is `classic-resource-core` actually using any constants symbols?**
   - What we know: `Cargo.toml` still depends on `classic-constants-core`, but grep found no `.rs` references under `classic-resource-core`.
   - What's unclear: Whether the dependency is fully dead or only used through generated/docs paths not captured by grep.
   - Recommendation: Treat it as likely removable, but verify with `cargo check`/`cargo build` immediately after dropping the dep.

2. **How much blame preservation will Git actually recover in the 3-way split?**
   - What we know: One-file-to-three-file splits cannot preserve perfect `--follow` history.
   - What's unclear: Whether Git rename detection will carry more than the largest `Fallout4Version` chunk.
   - Recommendation: Preserve blame for the largest slice, document the tradeoff in the move commit, and do not over-optimize beyond that.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Cargo | Rust workspace move/build/test | ✓ | 1.94.0 | — |
| Rustc | Rust compile/test | ✓ | 1.94.0 | — |
| Python | Parity generators, Python gate/tests | ✓ | 3.14.3 | — |
| uv | Python env/test workflow | ✓ | 0.11.6 | Use direct `.venv` Python only if needed |
| Node | Node contract/runtime tests | ✓ | v25.9.0 | — |
| Bun | Node build/parity/test scripts | ✓ | 1.3.10 | No good local fallback for `classic-node` scripts |
| PowerShell | Repo wrapper scripts | ✓ | 7.6.0 | — |
| CMake | Native/CXX workflows | ✓ | 4.3.1 | — |
| MSVC `cl` | Windows CXX/cpp-bridge compilation | ✗ | — | Enter VS dev shell / install VS workload |
| Ninja | Native wrapper builds | ✗ | — | Install via VS toolchain; no repo-local substitute |
| `VCPKG_ROOT` | Native dependency resolution | ✓ | `C:\vcpkg` | — |

**Missing dependencies with no fallback:**
- Local full native/CXX validation from the current shell is blocked by missing `cl` and `ninja`.

**Missing dependencies with fallback:**
- MSVC toolchain can usually be recovered by running the repo PowerShell/VS-shell wrappers instead of using the current shell directly.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Rust built-in test harness + Bun test + pytest |
| Config file | `ClassicLib-rs/Cargo.toml`; `ClassicLib-rs/node-bindings/classic-node/package.json`; none dedicated for pytest |
| Quick run command | `cargo test -p classic-version-registry-core -p classic-settings-core -p classic-shared-core --manifest-path ClassicLib-rs/Cargo.toml` |
| Full suite command | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` plus Node/Python parity/test commands from repo guide |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CNST-01 | Moved APIs remain accessible from the three target crates with same names | unit | `cargo test -p classic-version-registry-core -p classic-settings-core -p classic-shared-core --manifest-path ClassicLib-rs/Cargo.toml` | ❌ Wave 0 split needed |
| CNST-02 | All consumers compile against semantic target crates | integration/build | `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml` | ✅ |
| CNST-03 | Deleted crate no longer appears in workspace/tooling | structural + tooling | `python ClassicLib-rs/python-bindings/tests/test_parity_gate_tooling.py -q` is not sufficient alone; use parity generator/gate commands after target-map edits | ❌ Wave 0 guard needed |

### Sampling Rate
- **Per task commit:** `cargo test -p classic-version-registry-core -p classic-settings-core -p classic-shared-core --manifest-path ClassicLib-rs/Cargo.toml`
- **Per wave merge:** `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml` and binding-local parity/test commands
- **Phase gate:** Full workspace Rust build/test plus regenerated Node/Python parity artifacts green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] Split `ClassicLib-rs/business-logic/classic-constants-core/src/lib.rs` tests into destination crates before deleting the source crate.
- [ ] Migrate `ClassicLib-rs/node-bindings/classic-node/__test__/constants.spec.ts` into `shared.spec.ts`, `settings.spec.ts`, and `version_registry.spec.ts` or equivalent replacement coverage.
- [ ] Migrate `ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py` off `import classic_constants` onto the three target modules.
- [ ] Update `tools/python_api_parity/generate_baseline.py` and `tools/node_api_parity/generate_baseline.py` target/owner maps before baseline regeneration.
- [ ] Add a structural verification step that asserts no remaining `classic-constants-core` workspace members or Cargo dependencies remain.

## Sources

### Primary (HIGH confidence)
- `J:\CLASSIC-Fallout4\.planning\phases\03-constants-version-registry-merge\03-CONTEXT.md` - locked scope, destination mapping, binding/parity/doc decisions
- `J:\CLASSIC-Fallout4\AGENTS.md` - repo constraints and required validation/doc rules
- `J:\CLASSIC-Fallout4\.opencode\skills\classic-project-guide\references\repo-guide.md` - repo-approved Rust/Node/Python/C++ validation commands
- `J:\CLASSIC-Fallout4\ClassicLib-rs\business-logic\classic-constants-core\src\lib.rs` - actual symbol/test layout being redistributed
- `J:\CLASSIC-Fallout4\ClassicLib-rs\business-logic\classic-version-registry-core\src\lib.rs` - destination root re-export pattern
- `J:\CLASSIC-Fallout4\ClassicLib-rs\business-logic\classic-settings-core\src\lib.rs` - destination root re-export pattern
- `J:\CLASSIC-Fallout4\ClassicLib-rs\foundation\classic-shared-core\src\lib.rs` - foundation destination root pattern
- `/pyo3/pyo3` via Context7 - `#[pymodule]` registration and export patterns
- `/dtolnay/cxx` via Context7 - `cxx_build::bridge(s)` and namespace/build.rs patterns

### Secondary (MEDIUM confidence)
- `/napi-rs/napi-rs` via Context7 - `#[napi]` export behavior and generated contract expectations
- `J:\CLASSIC-Fallout4\docs\api\README.md` and related `docs/api/*.md` - current public-doc topology and required doc redistribution targets
- `J:\CLASSIC-Fallout4\tools\python_api_parity\generate_baseline.py` / `tools\node_api_parity\generate_baseline.py` - current hardcoded crate-owner mappings that must change

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - repo pins and internal target crates are explicit
- Architecture: HIGH - locked context plus existing Phase 1/2 patterns and current source files align
- Pitfalls: MEDIUM - most are source-backed, but exact local CXX/build behavior depends on shell/toolchain availability

**Research date:** 2026-04-11
**Valid until:** 2026-05-11
