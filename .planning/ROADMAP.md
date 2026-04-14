# Roadmap: CLASSIC

## Milestones

- 🚧 **v9.1.0-root Move Crates to Project Root** — Phases 6-10 (planned)
- ✅ **v9.1.0-consolidation Crate Consolidation** — Phases 1-5 (shipped 2026-04-12) — see [`milestones/v9.1.0-ROADMAP.md`](./milestones/v9.1.0-ROADMAP.md)
- ✅ **v9.1.0-bindings Full Bindings Parity** — Phases 1-7 (shipped 2026-04-10) — see [`milestones/v9.1.0-bindings-ROADMAP.md`](./milestones/v9.1.0-bindings-ROADMAP.md)
- ✅ **v9.1.0-bugfixes CLASSIC Codebase Health** — Phases 1-11 (shipped 2026-04-07) — see [`milestones/v9.1.0-bugfixes-ROADMAP.md`](./milestones/v9.1.0-bugfixes-ROADMAP.md)
- ✅ **v8.3.0 Performance & Polish** — Phases 12-18 (shipped 2026-02-05) — see [`milestones/v8.3.0-ROADMAP.md`](./milestones/v8.3.0-ROADMAP.md)
- ✅ **v8.2.0-part2 Rust Migration** — Phases 6-11 (shipped 2026-02-04) — see [`milestones/v8.2.0-part2-ROADMAP.md`](./milestones/v8.2.0-part2-ROADMAP.md)

## Phases

- [x] **Phase 6: Repo-Root Workspace Cutover** - Repository root becomes the only canonical Cargo workspace entrypoint.
- [x] **Phase 7: Crate Relocation and Path Rewire** - All crates move out of `ClassicLib-rs/` intact and still resolve as one workspace.
- [ ] **Phase 8: Wrapper and Parity Rewire** - Existing wrappers, frontends, and parity gates keep working against the relocated workspace.
- [ ] **Phase 9: Clean Validation and CI Refresh** - Clean-state validation, CI, and path-bearing artifacts prove the new layout is durable.
- [ ] **Phase 10: Docs, Guidance, and Tripwires** - Active docs and agent guidance point at the new root layout and guard against regressions.

## Phase Details

### Phase 6: Repo-Root Workspace Cutover
**Goal**: Contributors can treat the repository root as the single authoritative Cargo workspace root.
**Depends on**: Phase 5
**Requirements**: ROOT-01, ROOT-02
**Success Criteria** (what must be TRUE):
  1. Contributor can run Cargo from the repository root without relying on `ClassicLib-rs/Cargo.toml` as the live workspace manifest.
  2. Contributor can run canonical repo-root workspace commands including `cargo fmt --all`, `cargo clippy --workspace`, and `cargo test --workspace`.
  3. Contributor can observe one active workspace root instead of a dual-workspace steady state.
**Plans**: 4 plans

Plans:
- [x] `06-00-PLAN.md` — Bootstrap the Phase 6 validation scaffold and clean-run helper.
- [x] `06-01-PLAN.md` — Promote the repo-root workspace shell and root-aware helper scripts.
- [x] `06-02-PLAN.md` — Move benchmark-owned support files to repo root and remove old copies.
- [x] `06-03-PLAN.md` — Rewire cargo-based CI/workflow paths, sync active workflow docs, and prove the clean repo-root Cargo contract.

### Phase 7: Crate Relocation and Path Rewire
**Goal**: Every Rust crate currently under `ClassicLib-rs/` exists at its new repo-root-relative location with working local path relationships.
**Depends on**: Phase 6
**Requirements**: MOVE-01, MOVE-02
**Success Criteria** (what must be TRUE):
  1. Contributor can find each relocated crate at its new repository-root-relative path with its internal directory layout preserved.
  2. Contributor can resolve all workspace members and local crate path dependencies after the move.
  3. Contributor does not need a second active workspace under `ClassicLib-rs/` to build or inspect crate relationships.
**Plans**: 3 plans

Plans:
- [x] `07-01-PLAN.md` — Bootstrap the relocation audit artifact and Phase 7 planning validation scaffold.
- [x] `07-02-PLAN.md` — Move the six Rust layer directories to repo root and rewire only broken member/path edges.
- [x] `07-03-PLAN.md` — Complete the relocation audit and prove `ClassicLib-rs` is no longer a live Rust workspace home.

### Phase 8: Wrapper and Parity Rewire
**Goal**: Existing Rust-consuming wrappers, frontends, and parity gates continue to operate against the relocated workspace.
**Depends on**: Phase 7
**Requirements**: INTG-01, INTG-02
**Success Criteria** (what must be TRUE):
  1. Contributor can run the existing rebuild and wrapper entrypoints against the relocated workspace.
  2. Contributor can run native CLI, GUI, and TUI integration flows without restoring `ClassicLib-rs/` as the workspace root.
  3. Contributor can run the Python, Node, and CXX parity gates against the relocated workspace with no parity-contract changes caused by the move.
**Plans**: 6 plans
**UI hint**: yes

Plans:
- [ ] `08-01-PLAN.md` — Rewire repo-root rebuild wrappers and collapse `rebuild_node.ps1` into the canonical Node flow.
- [ ] `08-02-PLAN.md` — Rewire native CLI/GUI bridge includes and add a lightweight repo-root TUI smoke path.
- [ ] `08-03-PLAN.md` — Cut Python stub/parity tooling over to root-level binding paths with legacy-path rejection.
- [ ] `08-04-PLAN.md` — Rewire `classic-node` package scripts plus Node parity and d.ts freshness defaults.
- [ ] `08-05-PLAN.md` — Cut CXX parity tooling over to repo-root bridge paths and refresh stale CXX baseline metadata.
- [ ] `08-06-PLAN.md` — Refresh Python/Node checked-in parity artifacts and add the final Phase 8 planning audit.

### Phase 9: Clean Validation and CI Refresh
**Goal**: Clean-state verification and CI prove the repo-root workspace works without stale caches or legacy path artifacts.
**Depends on**: Phase 8
**Requirements**: INTG-03, INTG-04
**Success Criteria** (what must be TRUE):
  1. Contributor can run CI and path-sensitive build or packaging jobs against the new repository-root layout.
  2. Contributor can verify the relocation from a clean state with regenerated path-bearing artifacts.
  3. Contributor can see that successful validation does not depend on stale caches, stale outputs, or leftover `ClassicLib-rs` artifacts.
**Plans**: 4 plans

Plans:
- [ ] `09-01-PLAN.md` — Bootstrap the Phase 9 clean-validation audit and stronger targeted-clean harness.
- [ ] `09-02-PLAN.md` — Refresh Rust, native C++, and benchmark workflow path contracts plus GUI package proof invariants.
- [ ] `09-03-PLAN.md` — Refresh Python and Node PR workflow path contracts and lock the allowed artifact scope.
- [ ] `09-04-PLAN.md` — Regenerate only the owned path-bearing artifacts and finish the clean-state + GUI package proof.

### Phase 10: Docs, Guidance, and Tripwires
**Goal**: Active documentation and agent guidance teach the new workspace layout and help prevent `ClassicLib-rs` workspace-root regressions.
**Depends on**: Phase 9
**Requirements**: DOCS-01, DOCS-02, DOCS-03
**Success Criteria** (what must be TRUE):
  1. Contributor can follow active docs, skills, and agent context files without being sent to `ClassicLib-rs/` as the live workspace root.
  2. Contributor can use migration notes or a verification matrix to translate old `ClassicLib-rs` workflows into repo-root workflows.
  3. Contributor gets automated regression protection against newly introduced active `ClassicLib-rs` workspace-root references in validation-critical docs, scripts, or tests.
**Plans**: 10 plans

Plans:
- [ ] `10-00-PLAN.md` — Bootstrap the Phase 10 planning audit and wrapper-script tripwires before doc rewrites begin.
- [ ] `10-01-PLAN.md` — Create the shared workspace migration matrix and repoint top-level contributor entry docs to repo-root guidance.
- [ ] `10-02-PLAN.md` — Refresh the active API hubs and binding workflow docs to the repo-root path and artifact contract.
- [ ] `10-03-PLAN.md` — Update the foundation and settings API reference pages to root-level source links.
- [ ] `10-04-PLAN.md` — Update the version/config/web/update API reference pages to root-level source links.
- [ ] `10-05-PLAN.md` — Update the path/setup/file/resource API workflow docs to the moved repo-root tree.
- [ ] `10-06-PLAN.md` — Update the scan/database/bridge/gui API docs to the moved repo-root tree.
- [ ] `10-07-PLAN.md` — Update `AGENTS.md`, `CLAUDE.md`, and all classic-project-guide entrypoint mirrors to the repo-root contract.
- [ ] `10-08-PLAN.md` — Refresh the mirrored classic-project-guide repo-guide references with repo-root architecture, command, and parity-path guidance.
- [ ] `10-09-PLAN.md` — Update all active `.planning/codebase/*.md` maps to repo-root examples, commands, and live-tree paths.

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 6. Repo-Root Workspace Cutover | 4/4 | Complete | 2026-04-12 |
| 7. Crate Relocation and Path Rewire | 3/3 | Complete | 2026-04-12 |
| 8. Wrapper and Parity Rewire | 0/TBD | Not started | - |
| 9. Clean Validation and CI Refresh | 0/TBD | Not started | - |
| 10. Docs, Guidance, and Tripwires | 6/10 | In Progress|  |

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
