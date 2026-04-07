# Roadmap: CLASSIC

## Milestones

- 🚧 **v9.1.0-bindings Full Bindings Parity** — Phases 1-6 (active) — see below
- ✅ **v9.1.0-bugfixes CLASSIC Codebase Health** — Phases 1-11 (shipped 2026-04-07) — see [`milestones/v9.1.0-bugfixes-ROADMAP.md`](./milestones/v9.1.0-bugfixes-ROADMAP.md)
- ✅ **v8.3.0 Performance & Polish** — Phases 12-18 (shipped 2026-02-05) — see [`milestones/v8.3.0-ROADMAP.md`](./milestones/v8.3.0-ROADMAP.md)
- ✅ **v8.2.0-part2 Rust Migration** — Phases 6-11 (shipped 2026-02-04) — see [`milestones/v8.2.0-part2-ROADMAP.md`](./milestones/v8.2.0-part2-ROADMAP.md)

## Phases

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

### v9.1.0-bindings Full Bindings Parity (Active Milestone — Phase numbering reset to 1)

- [x] **Phase 1: CXX Parity Gate Tooling** (3/3 plans) — completed 2026-04-07 — first-class C++ bridge parity gate operational; born-green 202-entry baseline; 22 passing tests; contributor doc at docs/api/cxx-parity-gate.md
- [ ] **Phase 2: CXX Bridge Surface Expansion** — Close all narrowing gaps and add first-time C++ surfaces for constants, web, and FCX inspection
- [ ] **Phase 3: Python Tier Collapse** — Promote all 289 deferred Python entries to one enforced tier; wire classic_shared module
- [ ] **Phase 4: Node Tier Collapse** — Promote all 109 deferred Node entries to one enforced tier; add PE-version extraction
- [ ] **Phase 5: CI Enforcement** — Wire all three parity gates into CI with branch-protection blocking on every PR
- [ ] **Phase 6: Documentation Reset** — Rewrite harmony reference, delete Tier-2 governance files, add parity policy doc

## Phase Details

### Phase 1: CXX Parity Gate Tooling
**Goal**: A committed C++ bridge parity gate exists that enumerates the CXX bridge surface from Rust source, produces a baseline JSON contract, and fails on drift — before any bridge surface changes land
**Depends on**: Nothing (first phase; no build required — gate reads source only)
**Requirements**: CXXG-01, CXXG-02, CXXG-03, CXXG-04, CXXG-05
**Success Criteria** (what must be TRUE):
  1. Running `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` against the current bridge source exits zero and emits a parity report showing 0 drift from the committed baseline
  2. Modifying a bridge source file (adding or removing a `pub fn`) and re-running the gate exits non-zero with an explicit drift message identifying the changed symbol
  3. A committed `tools/cxx_api_parity/cxx_baseline_surface.json` baseline captures every current CXX bridge export and is regenerable by `generate_baseline.py` without a Rust build
  4. The gate script accepts a missing-deferred-registry path gracefully (no FileNotFoundError crash) — deferred registry concept is absent from the gate design
  5. A contributor can follow `docs/api/cxx-parity-gate.md` to run the gate locally and refresh the baseline after an intentional bridge change
**Plans**: 3 plans
Plans:
- [x] 01-cxx-parity-gate-tooling/01-01-PLAN.md — Parser TDD (parse_cxx_bridge_surface + helpers; Wave 0 scaffolding + 9 unit tests; CXXG-01)
- [x] 01-cxx-parity-gate-tooling/01-02-PLAN.md — Gate scripts + born-green baseline bootstrap + integration tests (CXXG-02, CXXG-03, CXXG-04)
- [x] 01-cxx-parity-gate-tooling/01-03-PLAN.md — Contributor doc + .gitignore + doc index entry + VALIDATION.md task-id backfill (CXXG-05, CXXG-04)

### Phase 2: CXX Bridge Surface Expansion
**Goal**: The C++ bridge exposes the full surface of every shared Rust crate it currently narrows, plus first-time exposure for classic-constants-core, classic-web-core, and the FCX issue getter — and the CXX parity gate baseline is updated to reflect the complete surface
**Depends on**: Phase 1 (gate must exist to accept the new baseline)
**Requirements**: CXXS-01, CXXS-02, CXXS-03, CXXS-04, CXXS-05, CXXS-06, CXXS-07, CXXS-08, CXXS-09, CXXS-10
**Success Criteria** (what must be TRUE):
  1. `classic-cli/build_cli.ps1 -Test` and `classic-gui/build_gui.ps1 -Test` both pass against the widened bridge with no API breakage in existing C++ frontend code
  2. C++ frontend code can call into `classic::constants`, `classic::web`, and `classic::scanner::get_fcx_config_issues()` using the new bridge namespaces — functions compile and link without modification to existing call sites
  3. The CXX parity gate (`check_parity_gate.py`) passes with the updated baseline that includes all new and widened bridge entry points — 0 drift from the committed baseline JSON
  4. `classic-cpp-bridge::scangame` exposes the same orchestration entry points that Python and Node bindings expose for classic-scangame-core (verified by reading the gate report — no scangame narrowing gaps remain)
  5. `classic-cpp-bridge::database`, `registry`, `config`, `path`, and `xse` surface gaps are closed: the gate report shows no missing-from-bridge entries for these domains
**Plans**: 8 plans
**UI hint**: yes
Plans:
- [ ] 02-cxx-bridge-surface-expansion/02-01-path-promotion-and-widening-PLAN.md — Promote src/path.rs into build.rs and widen for full classic-path-core surface (CXXS-08); migrate pathdialog.cpp to classic::path::check_restricted_path (D-11)
- [ ] 02-cxx-bridge-surface-expansion/02-02-constants-bridge-PLAN.md — New src/constants.rs exposing classic-constants-core enums + helpers (CXXS-01, D-04)
- [ ] 02-cxx-bridge-surface-expansion/02-03-web-bridge-PLAN.md — New src/web.rs exposing classic-web-core URL/user-agent/ModSite helpers (CXXS-02)
- [ ] 02-cxx-bridge-surface-expansion/02-04-xse-and-version-registry-split-PLAN.md — Split XSE and version registry from game.rs into dedicated bridge modules (CXXS-06, CXXS-09; D-01, D-02, D-08 shims preserved)
- [ ] 02-cxx-bridge-surface-expansion/02-05-scangame-widening-ba2-ini-enb-PLAN.md — Widen scangame.rs with BA2 / INI / ENB sub-domain entry points (CXXS-04 part 1; D-06 split)
- [ ] 02-cxx-bridge-surface-expansion/02-06-scangame-widening-toml-wrye-integrity-setup-PLAN.md — Widen scangame.rs with TOML / Wrye / Integrity / Setup structured / Crashgen orchestrator (CXXS-04 part 2)
- [ ] 02-cxx-bridge-surface-expansion/02-07-config-suspect-rules-and-database-typed-PLAN.md — config suspect-rule DTOs (CXXS-07) + database typed FormID API (CXXS-05; D-08 additive)
- [ ] 02-cxx-bridge-surface-expansion/02-08-fcx-getter-and-final-verification-PLAN.md — scanner.rs FCX issue getter (CXXS-03) + final clean-build pair + Phase 2 baseline closeout (CXXS-10)

### Phase 3: Python Tier Collapse
**Goal**: All 289 currently-deferred Python parity entries are promoted to the single enforced contract tier; the Python parity gate exits zero with no deferred entries; classic_shared is wired as a gate-enrolled build target
**Depends on**: Nothing (independent of CXX work and Node collapse; can run in parallel with Phase 4)
**Requirements**: PYT-01, PYT-02, PYT-03, PYT-04, PYT-05, PYT-06, HARM-03, HARM-04
**Success Criteria** (what must be TRUE):
  1. `python tools/python_api_parity/check_parity_gate.py --repo-root .` exits zero; the gate report shows 0 deferred entries and 0 Tier-1 drift across all 19 business-logic crate pairs
  2. `uv run pytest ClassicLib-rs/python-bindings/tests -q` passes with smoke tests for at least one promoted method per newly-covered module (no AttributeError or ImportError on any promoted symbol)
  3. `mypy --strict` passes against the updated `.pyi` stubs for every binding crate that gained promoted APIs
  4. Python code can `import classic_shared` and call `classic_shared.get_runtime_stats()` and `classic_shared.is_runtime_healthy()` — the module is importable from the build output and the parity gate enforces it as Tier-1
  5. The `runtime_coverage_summary.md` reports deferred-entry count of 0; `classic_shared` appears in the module map with at least 3 enforced contract rows
**Plans**: TBD

### Phase 4: Node Tier Collapse
**Goal**: All 109 currently-deferred Node parity entries are promoted to the single enforced contract tier; the Node parity gate exits zero with no deferred entries; Node gains PE-version extraction
**Depends on**: Nothing (independent of CXX work and Python collapse; can run in parallel with Phase 3)
**Requirements**: NODE-01, NODE-02, NODE-03, NODE-04, NODE-05, NODE-06, HARM-01, HARM-02
**Success Criteria** (what must be TRUE):
  1. `bun run parity:gate:local` exits zero; the gate report shows 0 deferred entries and 0 Tier-1 drift across all business-logic crate modules
  2. `bun run test:bun && bun run test:node` pass with smoke tests for at least one promoted method per newly-covered module
  3. `bun run dts:freshness:check` passes against the committed `index.d.ts` that includes all promoted exports in camelCase (every `nodeExport` field in the contract matches the TypeScript identifier in `index.d.ts`)
  4. Node code can call `extractPeVersion(path)` and receive a typed object `{ major, minor, patch, build }` (or null) — the function is in `index.d.ts`, runtime-tested, and parity-verified against the Python/C++ PE-version API
  5. The `runtime_coverage_summary.md` reports deferred-entry count of 0; the Node coverage registry no longer references any Tier-2 governance files
**Plans**: TBD

### Phase 5: CI Enforcement
**Goal**: All three parity gates run in CI on every PR and block merge on failure; adding a new public Rust API without updating all three bindings fails CI; branch protection enforces the C++ gate in the same PR that adds the CI job
**Depends on**: Phase 1 (CXX gate must exist), Phase 3 (Python gate must be single-tier), Phase 4 (Node gate must be single-tier)
**Requirements**: CI-01, CI-02, CI-03, CI-04, CI-05, CI-06
**Success Criteria** (what must be TRUE):
  1. A PR that adds a new `pub fn` to a `-core` crate `lib.rs` without updating any binding surfaces fails CI on all three parity gate jobs (Python, Node, and CXX) — the triple-gate failure is confirmed by an explicit assertion test
  2. The new `cxx-parity-gate` CI job in `ci-cpp.yml` runs before `cli-tests` and `gui-tests`, requires only Python and a checkout (no Rust build), and blocks both downstream jobs on drift failure
  3. The C++ parity gate CI job is listed in branch-protection required checks in the same PR that adds the CI job — there is no window where the gate exists in CI but does not block merge
  4. A `.gitignore`-respecting freshness gate fails CI when committed CXX artifacts (baseline JSON or committed header snapshots) drift from what a fresh source scan would produce
  5. The Python and Node parity gates remain green in CI after their respective Tier-2 removal (CI-01 and CI-02 verified as still passing after Phase 3 and Phase 4 changes)
**Plans**: TBD

### Phase 6: Documentation Reset
**Goal**: All Tier-2 governance files are deleted; binding-parity-overview.md is rewritten as the harmony-achieved reference; a single source-of-truth parity policy doc exists; error-contract conventions are documented
**Depends on**: Phase 3 (Python gate must be single-tier and green), Phase 4 (Node gate must be single-tier and green), Phase 5 (CI enforcement must be in place before governance deletion)
**Requirements**: DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06, DOC-07, HARM-05
**Success Criteria** (what must be TRUE):
  1. `python tools/python_api_parity/check_parity_gate.py --repo-root .` and `python tools/node_api_parity/check_parity_gate.py --repo-root .` both exit zero with a missing deferred-registry path argument (scripts are tolerant before governance files are deleted)
  2. No files exist under `docs/implementation/python_api_parity/governance/` or `docs/implementation/node_api_parity/governance/`; a `grep -r "tier2" docs/` across all committed docs files returns zero results referencing deleted files
  3. A promotion audit trail at `.planning/milestones/v9.1.0-bindings-promotion-audit.md` records which entries were promoted from each governance file before deletion (this file is committed before any governance file is deleted)
  4. `docs/api/binding-parity-overview.md` contains no Tier-2 language, no `classic-constants-core` / `classic-web-core` divergence rows, and reflects full CXX/Node/Python surface parity with updated columns
  5. `docs/api/binding-parity-policy.md` exists and states the one-tier policy: when gate refreshes happen, who owns each gate, and how to add a new public Rust API across all three bindings
**Plans**: TBD

## Progress

### v9.1.0-bindings Full Bindings Parity

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. CXX Parity Gate Tooling | 1/3 | In Progress|  |
| 2. CXX Bridge Surface Expansion | 1/8 | In Progress|  |
| 3. Python Tier Collapse | 0/TBD | Not started | - |
| 4. Node Tier Collapse | 0/TBD | Not started | - |
| 5. CI Enforcement | 0/TBD | Not started | - |
| 6. Documentation Reset | 0/TBD | Not started | - |

### v9.1.0-bugfixes CLASSIC Codebase Health (Archived — shipped 2026-04-07)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Deprecated API Migration | v9.1.0-bugfixes | 2/2 | Complete | 2026-04-06 |
| 2. Dead Code Removal | v9.1.0-bugfixes | 3/3 | Complete | 2026-04-06 |
| 3. FCX State Hardening | v9.1.0-bugfixes | 3/3 | Complete | 2026-04-06 |
| 4. Bounded Cache Replacement | v9.1.0-bugfixes | 6/6 | Complete | 2026-04-06 |
| 5. Pattern Caching and Performance | v9.1.0-bugfixes | 7/7 | Complete | 2026-04-06 |
| 6. mmap TOCTOU Safety | v9.1.0-bugfixes | 3/3 | Complete | 2026-04-06 |
| 7. Consistency Sweep | v9.1.0-bugfixes | 2/2 | Complete | 2026-04-06 |
| 8. Workspace and Infrastructure | v9.1.0-bugfixes | 3/3 | Complete | 2026-04-06 |
| 9. Deprecated API Verification Closure | v9.1.0-bugfixes | 1/1 | Complete | 2026-04-07 |
| 10. Pattern Caching Verification Backfill | v9.1.0-bugfixes | 1/1 | Complete | 2026-04-07 |
| 11. Workspace/Infra Verification Completion | v9.1.0-bugfixes | 1/1 | Complete | 2026-04-07 |
