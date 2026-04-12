# Phase 3: Constants Redistribution - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-11
**Phase:** 03-constants-version-registry-merge (slug may change via roadmap amendment)
**Areas discussed:** Module layout, Python binding fold, Node/CXX module handling, Parity gate strategy, Plan sizing, Semantic naming tension, + 5 sub-decisions cascading from 6=b

---

## Area 1: Module layout inside target crate(s)

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Single flat `constants.rs` in one target crate | Matches Phase 2 D-02 precedent; single `git mv`; cleanest blame | |
| (b) Domain split across file boundaries | Smaller files by domain; clearer module boundaries | ✓ |

**User's choice:** (b) — domain split.

**Notes:** Originally presented as "layout inside a single target crate." After user picked 6=b (split destinations), this decision was **forced** rather than chosen — the domain split happens across three target crates, not three files in one crate. The original "single flat file" option is no longer on the table because the three domains can no longer coexist in one target.

---

## Area 2: Python binding fold

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Delete `classic-constants-py`, fold into target py crate(s) | Phase 1 precedent; matches consolidation goal; no dangling crate | ✓ |
| (b) Keep `classic-constants-py` as thin re-export shim | Python `import classic_constants` keeps working | |

**User's choice:** (a) — delete and fold.

**Notes:** Under 6=b, the fold became a 3-way carve rather than a single fold. PyFallout4Version → classic-version-registry-py, PyYamlFile + settings constants → classic-settings-py, PyGameId → classic-shared-py. The `classic-constants-py` crate is fully deleted. Python consumers now import from three separate modules.

---

## Area 3: Node + CXX bridge module handling

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Merge `constants.rs` content into peers, delete the file | Mirrors core-side merge; single module per domain; CXX namespace collapse | ✓ |
| (b) Keep both files, only rewire internal `use` lines | Zero binding-surface drift; smallest diff | |

**User's choice:** (a) — merge and delete binding-side `constants.rs`.

**Notes:** Under 6=b, the merge dispersed across THREE peer modules on both Node and CXX sides, not two. Node side: content goes to version_registry.rs, settings.rs, and shared.rs (all already exist). CXX side: content goes to version_registry.rs, settings.rs, and a NEW shared.rs module (created per sub-decision Q2). The CXX namespace `classic::constants` is retired permanently.

---

## Area 4: Parity gate strategy

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Regenerate CXX only, verify-only Python + Node | Targeted regen; matches original flat-merge scope | |
| (b) Regenerate all three baselines | Uniform treatment; no drift-noise ambiguity | ✓ (upgraded under 6=b) |
| (c) Verify-only all three | Matches Phase 2 | |

**User's choice:** Originally (a), **upgraded to (b)** via follow-up Q5.

**Notes:** Under 6=b, the symbol source-crate attribution changes for EVERY moved symbol across all three bindings, not just CXX. Python and Node parity baselines include source-path metadata; verify-only would produce drift noise that blocks the gates. Regenerating all three is the correct response to a redistribution.

---

## Area 5: Plan sizing / subplan structure

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Mirror Phase 1's 3-subplan structure | Proven shape; matches prior phase fanout | ✓ (upgraded to 4 under 6=b) |
| (b) Mirror Phase 2's 2-subplan structure | Simpler scope; fewer plans | |
| (c) 4-plan structure | Split Rust-cores into its own plan | |

**User's choice:** Originally (a), **upgraded to 4 subplans** under 6=b cascade.

**Notes:** 3 subplans fit the flat-merge scope. Under 6=b, the additional complexity of a 3-way Python carve + 3-way CXX dispersal + new `shared.rs` module creation pushed the natural plan count to 4: (1) Rust core redistribution + consumer sweep, (2) Python 3-way carve, (3) Node + CXX bridge dispersal, (4) tests/docs/parity regen. See D-28 in CONTEXT.md.

---

## Area 6: Semantic naming tension (scope-adjacent)

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Accept target naming and note as deferred idea | Roadmap-locked; reduces crate count per milestone goal | |
| (b) Split destinations by semantic domain | Fallout4Version → vr-core, YamlFile → settings-core, GameId → shared-core | ✓ |
| (c) Partial split + create new small crate | Rejected — cancels consolidation goal | |

**User's choice:** (b) — redistribute by semantic domain.

**User's explicit rationale:** "Fallut4Version should go to version-registry-core, YamlFile should go to classic-settings-core, GameId should go to classic-shared-core"

**Notes:** This is the CORE decision of Phase 3. It reframes the phase from "absorb into one target" to "redistribute by domain." It contradicts the roadmap's Phase 3 title and CNST-01/CNST-02 requirements, which forced the cascade of sub-decisions below. Architecturally sounder than the flat merge because each content chunk goes to its natural semantic home.

---

## Sub-decision Q1: Destination for `SETTINGS_IGNORE_NONE` + `must_not_be_none()`

| Option | Description | Selected |
|--------|-------------|----------|
| (a) `classic-settings-core` alongside YamlFile | Content is literally settings-domain; natural co-location | ✓ |
| (b) `classic-shared-core` as app-wide utility | Alternative generic home | |
| (c) Elsewhere | | |

**User's choice:** (a) — settings-core alongside YamlFile.

---

## Sub-decision Q2: CXX bridge GameId home

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Create new `classic-cpp-bridge/src/shared.rs` with namespace `classic::shared` | Mirrors Rust layer layout; clean; new 5-place registration | ✓ |
| (b) Add GameId to existing `game.rs` (namespace `classic::game`) | Reuses existing module; no new registration | |
| (c) Add to `types.rs` (shared DTOs) | Namespace-less catch-all | |
| (d) Inline duplicated into consumer modules | Rejected — violates SSoT | |

**User's choice:** (a) — create new `shared.rs` module.

**Notes:** Accepts the 5-place CXX bridge registration cost (lib.rs, build.rs, Cargo.toml, include/ dir, CMakeLists.txt) per Phase 1 D-09 learning. Gives the CXX bridge layer a `shared` namespace that mirrors the Rust foundation layer for the first time.

---

## Sub-decision Q3: Python module name for GameId wrappers

| Option | Description | Selected |
|--------|-------------|----------|
| (a) `classic_shared` (existing foundation py crate) | Mirrors Rust layout; matches shared-core destination | ✓ |
| (b) Create new py module | | |

**User's choice:** (a) / "yes" — use existing `classic-shared-py`.

**Notes:** `classic-shared-py` may be adding its first public `#[pyclass]` (PyGameId). Foundation py crates are allowed to grow when a foundation-domain type moves in.

---

## Sub-decision Q4: Roadmap amendment timing

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Land inside Phase 3 first subplan | Keeps amendment with the work | |
| (b) Quick-task commit BEFORE Phase 3 planning | Cleaner separation; plan agent reads amended scope | ✓ |

**User's choice:** (b) — quick-task commit before planning.

**Notes:** CRITICAL prerequisite. `/gsd:plan-phase 3` MUST NOT start until the quick-task lands. The plan agent reads ROADMAP.md, REQUIREMENTS.md, PROJECT.md for scope; stale scope = wrong plan.

---

## Sub-decision Q5: Parity gate regeneration scope

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Regenerate CXX only | Original flat-merge scope | |
| (b) Regenerate all three baselines | 6=b changes source-crate attribution for every symbol | ✓ |

**User's choice:** (b) / "yes" — regenerate all three.

**Notes:** This upgrade cascaded directly from 6=b. Under flat merge, Python and Node baselines would be unchanged; under redistribution, the source-path metadata for every moved symbol shifts, which is real drift.

---

## Claude's Discretion (areas where user deferred to planner/executor)

- Exact ordering of operations within each subplan's commits
- Internal import organization inside each new submodule file
- Any `#[allow(...)]` lint attributes that need to carry forward with the moved code
- Cargo feature-flag deduplication in target crates
- Verification frequency (per-subplan `cargo build --workspace` vs end-only)
- Internal CXX bridge module layout for new `shared.rs` (number of `#[cxx::bridge]` blocks, DTO placement)
- Whether `SETTINGS_IGNORE_NONE` becomes a standalone const or co-locates with YamlFile in `yaml_file.rs`
- D-07 blame-preservation fallback detail (`git mv` vs `git rm` + new-file per destination chunk)

---

## Deferred Ideas (captured for future, not Phase 3 scope)

- Renaming `classic-version-registry-core` for semantic accuracy (resolved by redistribution; no rename needed)
- Retroactive test coverage for shared-core foundation enums
- Unifying `semver` dep into a workspace-level entry
- Workspace naming cleanup (classic-shared-core vs classic-shared-py layer confusion)
- Retiring `phf` dep from constants-core if unused (verify during planning)
- Dedicated `tests/` directories for settings-core and shared-core vs inline modules
- GameId → foundation as a reusable "identity type" pattern for future consolidation phases
