# Roadmap: CLASSIC

## Milestones

- 🚧 **v9.1.0-consolidation Crate Consolidation** — Phases 1-5 (in progress)
- ✅ **v9.1.0-bindings Full Bindings Parity** — Phases 1-7 (shipped 2026-04-10) — see [`milestones/v9.1.0-bindings-ROADMAP.md`](./milestones/v9.1.0-bindings-ROADMAP.md)
- ✅ **v9.1.0-bugfixes CLASSIC Codebase Health** — Phases 1-11 (shipped 2026-04-07) — see [`milestones/v9.1.0-bugfixes-ROADMAP.md`](./milestones/v9.1.0-bugfixes-ROADMAP.md)
- ✅ **v8.3.0 Performance & Polish** — Phases 12-18 (shipped 2026-02-05) — see [`milestones/v8.3.0-ROADMAP.md`](./milestones/v8.3.0-ROADMAP.md)
- ✅ **v8.2.0-part2 Rust Migration** — Phases 6-11 (shipped 2026-02-04) — see [`milestones/v8.2.0-part2-ROADMAP.md`](./milestones/v8.2.0-part2-ROADMAP.md)

## Phases

### v9.1.0-consolidation Crate Consolidation

**Phase Numbering:**
- Integer phases (1, 2, 3, 4, 5): Planned milestone work
- Decimal phases (e.g., 2.1): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: YAML -> Settings Merge** - Absorb classic-yaml-core into classic-settings-core, update all consumers and bindings
- [ ] **Phase 2: Crashgen -> Config Merge** - Absorb classic-crashgen-settings-core into classic-config-core, update all consumers
- [ ] **Phase 3: Constants Redistribution** - Redistribute classic-constants-core across three target crates by semantic domain (version-registry-core, settings-core, shared-core), update all consumers across the workspace
- [ ] **Phase 4: Gate Validation & Documentation** - All parity gates green, workspace tests pass, documentation reflects 16-crate topology
- [ ] **Phase 5: Milestone Cleanup** - Close non-blocking audit debt from the consolidation milestone (stale docs index links, stale Phase 3 verification bookkeeping, stale Node parity floor tripwire)

<details>
<summary>✅ v9.1.0-bindings Full Bindings Parity (Phases 1-7) — SHIPPED 2026-04-10</summary>

- [x] Phase 1: CXX Parity Gate Tooling (3/3 plans) — completed 2026-04-07
- [x] Phase 2: CXX Bridge Surface Expansion (8/8 plans) — completed 2026-04-08
- [x] Phase 3: Python Tier Collapse (10/10 plans) — completed 2026-04-08
- [x] Phase 4: Node Tier Collapse (6/6 plans) — completed 2026-04-10
- [x] Phase 5: CI Enforcement (1/2 plans — CI-04 user-deferred) — completed 2026-04-09
- [x] Phase 6: Documentation Reset (2/2 plans) — completed 2026-04-10
- [x] Phase 7: Milestone Cleanup (1/1 plan) — completed 2026-04-10

</details>

<details>
<summary>✅ v9.1.0-bugfixes CLASSIC Codebase Health (Phases 1-11) — SHIPPED 2026-04-07</summary>

- [x] Phase 1: Deprecated API Migration (2/2 plans) — completed 2026-04-06
- [x] Phase 2: Dead Code Removal (3/3 plans) — completed 2026-04-06
- [x] Phase 3: FCX State Hardening (3/3 plans) — completed 2026-04-06
- [x] Phase 4: Bounded Cache Replacement (6/6 plans) — completed 2026-04-06
- [x] Phase 5: Pattern Caching and Performance (7/7 plans) — completed 2026-04-06
- [x] Phase 6: mmap TOCTOU Safety (3/3 plans) — completed 2026-04-06
- [x] Phase 7: Consistency Sweep (2/2 plans) — completed 2026-04-06
- [x] Phase 8: Workspace and Infrastructure (3/3 plans) — completed 2026-04-06
- [x] Phase 9: Deprecated API Verification Closure (1/1 plan) — completed 2026-04-07 (Phase 1 gap closure)
- [x] Phase 10: Pattern Caching Verification Backfill (1/1 plan) — completed 2026-04-07 (Phase 5 gap closure)
- [x] Phase 11: Workspace/Infra Verification Completion (1/1 plan) — completed 2026-04-07 (Phase 8 gap closure)

</details>

## Phase Details

### Phase 1: YAML -> Settings Merge
**Goal**: classic-yaml-core no longer exists as a separate crate; all its public API is available from classic-settings-core with no consumer-visible behavior change
**Depends on**: Nothing (first phase; all three merges are independent)
**Requirements**: YAML-01, YAML-02, YAML-03, YAML-04
**Success Criteria** (what must be TRUE):
  1. Every public type, function, and re-export that classic-yaml-core provided is accessible from classic-settings-core at the same API surface
  2. No crate in the workspace has a `classic-yaml-core` dependency in its Cargo.toml -- all former consumers import from classic-settings-core
  3. The classic-yaml-core directory is deleted and removed from workspace members in the root Cargo.toml
  4. All three binding crates (C++ bridge, Node, Python) that referenced yaml-core types compile and their existing tests pass against the settings-core import path
  5. `cargo build --workspace` and `cargo test --workspace` succeed with zero failures
**Plans:** 1/3 plans executed

Plans:
- [x] 01-01-PLAN.md — Rust core merge: git mv yaml-core into settings-core, content edits, consumer migration, crate removal
- [x] 01-02-PLAN.md — Binding consolidation: C++ bridge rename, Node yaml merge, Python yaml-py fold-in
- [x] 01-03-PLAN.md — Test migration, documentation consolidation, parity gate regeneration

### Phase 2: Crashgen -> Config Merge
**Goal**: classic-crashgen-settings-core no longer exists as a separate crate; its rule model and evaluator are part of classic-config-core with no consumer-visible behavior change
**Depends on**: Nothing (independent of other merges; listed after Phase 1 for execution ordering)
**Requirements**: CGEN-01, CGEN-02, CGEN-03
**Success Criteria** (what must be TRUE):
  1. Every public type, function, and re-export that classic-crashgen-settings-core provided is accessible from classic-config-core at the same API surface
  2. No crate in the workspace has a `classic-crashgen-settings-core` dependency in its Cargo.toml -- all former consumers import from classic-config-core
  3. The classic-crashgen-settings-core directory is deleted and removed from workspace members in the root Cargo.toml
  4. `cargo build --workspace` and `cargo test --workspace` succeed with zero failures
**Plans:** 2 plans

Plans:
- [x] 02-01-PLAN.md — Rust core merge: git mv source, consumer/binding migration, crate deletion, yamldata.rs.bak cleanup
- [x] 02-02-PLAN.md — Node parity tooling update, API docs consolidation, parity gate verification

### Phase 3: Constants Redistribution
**Goal**: classic-constants-core no longer exists as a separate crate; its contents are redistributed by semantic domain: Fallout4Version and NULL_VERSION live in classic-version-registry-core, YamlFile and settings constants live in classic-settings-core, and GameId lives in classic-shared-core (foundation). Zero consumer-visible behavior change.
**Depends on**: Nothing (independent of other merges; listed after Phase 2 for execution ordering)
**Requirements**: CNST-01, CNST-02, CNST-03
**Success Criteria** (what must be TRUE):
  1. Fallout4Version, NULL_VERSION, and related version identity APIs are accessible from classic-version-registry-core at the same public names
  2. YamlFile, SETTINGS_IGNORE_NONE, and must_not_be_none() are accessible from classic-settings-core at the same public names
  3. GameId is accessible from classic-shared-core (foundation layer) at the same public name
  4. No crate in the workspace has a `classic-constants-core` dependency in its Cargo.toml -- all former consumers import from the semantic-domain-appropriate target crate (version-registry-core, settings-core, or shared-core)
  5. The classic-constants-core directory is deleted and removed from workspace members in the root Cargo.toml
  6. `cargo build --workspace` and `cargo test --workspace` succeed with zero failures
**Plans:** 4/4 plans complete

Plans:
- [x] 03-01-PLAN.md — Redistribute Rust core constants, migrate inline tests first, sweep workspace Cargo dependencies, then delete classic-constants-core
- [x] 03-02-PLAN.md — Carve classic-constants-py into version-registry-py, settings-py, and shared-py with module retags; migrate Python consumers; delete classic-constants-py
- [x] 03-03-PLAN.md — Disperse Node and CXX constants surfaces into semantic modules, migrate constants.spec.ts and the GUI consumer, and add classic::shared bridge support
- [x] 03-04-PLAN.md — Consolidate active docs, refresh parity tooling inputs in split-aware order, and regenerate all three parity baselines with live-reference checks

### Phase 4: Gate Validation & Documentation
**Goal**: All three parity gates confirm zero drift after consolidation, and project documentation reflects the new 16-crate workspace topology
**Depends on**: Phase 1, Phase 2, Phase 3 (all merges must land before cross-cutting validation)
**Requirements**: GATE-01, GATE-02, GATE-03, GATE-04, GATE-05, GATE-06
**Success Criteria** (what must be TRUE):
  1. `cargo test --workspace` passes end-to-end with zero failures across all 16 remaining business-logic crates
  2. CXX parity gate baseline is regenerated to reflect the merged crate topology and exits 0
  3. Python parity gate exits 0 under the current one-tier parity contract after import path updates for merged crates, with zero coverage gaps, registry mismatches, or stale tracked artifacts
  4. Node parity gate exits 0 after any needed import path updates for merged crates
  5. API docs under `docs/api/` are updated: absorbed crate pages (yaml-core, crashgen-settings-core, constants-core) are consolidated into their target crate pages, and all cross-references point to the surviving crates
**Plans**: 3 plans

Plans:
- [x] 04-01-PLAN.md — Align active topology and API docs with the 16-crate closure state and verify-first parity wording
- [x] 04-02-PLAN.md — Run plain parity gates first, refresh only source-backed drift, and revalidate Node/Python runtime artifacts
- [x] 04-03-PLAN.md — Run the full closure suite and write the dedicated Phase 4 verification checklist artifact

### Phase 5: Milestone Cleanup
**Goal**: Close the remaining non-blocking audit debt from the consolidation milestone so documentation navigation, verification bookkeeping, and parity-tripwire tracking all match the live codebase
**Depends on**: Phase 4 (closure evidence must exist before cleanup)
**Requirements**: (none -- audit cleanup phase; no unsatisfied milestone requirements)
**Gap Closure**: Closes tech debt from `.planning/v9.1.0-MILESTONE-AUDIT.md`
**Success Criteria** (what must be TRUE):
  1. `docs/RUST_DOCUMENTATION_INDEX.md` no longer links to deleted absorbed-crate pages and instead routes contributors to surviving owner docs
  2. `.planning/phases/03-constants-version-registry-merge/03-VERIFICATION.md` is refreshed or superseded so its reported status matches the current live tree and `03-VALIDATION.md`
  3. `tools/node_api_parity/tests/test_check_parity_gate.py` and `.planning/phases/02-crashgen-config-merge/deferred-items.md` agree on the intended Node tier-1 contract floor after consolidation
**Plans**: 1 plan

Plans:
- [x] 05-01-PLAN.md — Close the consolidation milestone cleanup debt (docs index links, Phase 3 verification bookkeeping, Node parity floor tripwire)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. YAML -> Settings Merge | 1/3 | In Progress|  |
| 2. Crashgen -> Config Merge | 0/TBD | Not started | - |
| 3. Constants Redistribution | 4/4 | Complete   | 2026-04-12 |
| 4. Gate Validation & Documentation | 3/3 | Complete   | 2026-04-12 |
| 5. Milestone Cleanup | 1/1 | Complete | 2026-04-12 |
