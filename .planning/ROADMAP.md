# Roadmap: CLASSIC

## Milestones

- **v1.0 Codebase Cleanup** -- Phases 1-5 (shipped 2026-02-02)
- **v8.2.0-part2 Rust Migration** -- Phases 6-11 (shipped 2026-02-04)
- **v8.3.0 Performance & Polish** -- Phases 12-18 (shipped 2026-02-05)
- **v9.0.0 Slint GUI** -- Phases 19-25 (in progress)

## Phases

<details>
<summary>v1.0 Codebase Cleanup (Phases 1-5) -- SHIPPED 2026-02-02</summary>

See `.planning/milestones/v1.0-ROADMAP.md` for full details.

- [x] Phase 1: Foundation Cleanup (4/4 plans)
- [x] Phase 2: Integration Layer Simplification (2/2 plans)
- [x] Phase 3: Wrapper Thinning (2/2 plans)
- [x] Phase 4: Interface Consolidation (3/3 plans)
- [x] Phase 5: Fallback Pruning (3/3 plans)

**Accomplishments:** Removed 11,993 net lines, 8 Python fallbacks eliminated, factory.py consolidated with 13 Protocol types.

</details>

<details>
<summary>v8.2.0-part2 Rust Migration (Phases 6-11) -- SHIPPED 2026-02-04</summary>

See `.planning/milestones/v8.2.0-part2-ROADMAP.md` for full details.

- [x] Phase 6: Foundation & Settings (2/2 plans)
- [x] Phase 7: Game Detection (2/2 plans)
- [x] Phase 8: Report Generation (2/2 plans)
- [x] Phase 9: Orchestration Migration (4/4 plans)
- [x] Phase 10: Parity Validation (2/2 plans)
- [x] Phase 11: Integration & Cleanup (2/2 plans)

**Accomplishments:** Python is now UI-only shell. All business logic in Rust. 7 Python analyzers deleted, 19 Rust modules bundled.

</details>

<details>
<summary>v8.3.0 Performance & Polish (Phases 12-18) -- SHIPPED 2026-02-05</summary>

See `.planning/milestones/v8.3.0-ROADMAP.md` for full details.

- [x] Phase 12: GIL Release Audit (1/1 plan)
- [x] Phase 13: Benchmark Infrastructure (3/3 plans)
- [x] Phase 14: Hot Path Profiling (3/3 plans)
- [x] Phase 15: Bug Fixes (2/2 plans)
- [x] Phase 16: Hot Path Optimization (2/2 plans)
- [x] Phase 17: CI Regression Detection (3/3 plans)
- [x] Phase 18: Tech Debt Cleanup (1/1 plan)

**Accomplishments:** 77+ Criterion benchmarks established, CI regression detection (10% threshold), GIL release audit (65 without_gil), profiling tooling (flamegraph/py-spy/dhat), O(1) membership optimization, both pre-existing bugs fixed.

</details>

### v9.0.0 Slint GUI (In Progress)

**Milestone Goal:** Rust-native GUI using Slint -- all business logic and UI in Rust, no Python dependency.

#### Phase 19: Foundation and Async Bridge
**Goal**: Slint application builds, launches, and integrates with existing Tokio runtime
**Depends on**: Phase 18 (v8.3.0 complete)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05
**Success Criteria** (what must be TRUE):
  1. Running `cargo build -p classic-gui` produces a Windows executable
  2. Launching the executable displays a window (any content)
  3. Worker thread can spawn async tasks on Tokio runtime without blocking UI
  4. Long-running operation demonstrates progress callback to UI thread
**Plans:** 2 plans

Plans:
- [x] 19-01-PLAN.md — Create classic-gui Slint crate with build system and scaffold UI
- [x] 19-02-PLAN.md — Wire AsyncBridge for worker thread pattern with progress callbacks

#### Phase 20: Core UI Layout
**Goal**: Main window with proper layout, theming, and tabbed interface
**Depends on**: Phase 19
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05
**Success Criteria** (what must be TRUE):
  1. Window shows "CLASSIC" title and icon in title bar
  2. Dark theme renders (fluent-dark style)
  3. User can switch between Main Options, Results, and Settings tabs
  4. Buttons, inputs, and checkboxes render and respond to clicks
  5. Window resizes without layout breaking
**Plans:** 2 plans

Plans:
- [x] 20-01-PLAN.md — Main window layout with fluent-dark theme and 3-tab structure
- [x] 20-02-PLAN.md — State persistence and native file dialogs

#### Phase 21: Scan Operations
**Goal**: User can trigger, monitor, and cancel crash log scans
**Depends on**: Phase 20
**Requirements**: SCAN-01, SCAN-02, SCAN-03, SCAN-04, SCAN-05
**Success Criteria** (what must be TRUE):
  1. User can click "Scan" button and see scanning begin
  2. Progress bar updates with percentage during scan
  3. User can click "Cancel" to stop a running scan
  4. Scan completion shows summary (X logs scanned, Y issues found)
  5. OrchestratorCore executes actual scan logic (not mocked)
**Plans:** 2 plans

Plans:
- [x] 21-01-PLAN.md — Wire OrchestratorCore to GUI with morphing Scan/Cancel button
- [x] 21-02-PLAN.md — Add indeterminate progress, cancellation with partial results, and auto-tab-switch

#### Phase 22: Results Viewer
**Goal**: User can browse and view scan reports
**Depends on**: Phase 21
**Requirements**: RSLT-01, RSLT-02, RSLT-03, RSLT-04, RSLT-06, RSLT-07
**Success Criteria** (what must be TRUE):
  1. Results tab shows list of available reports with timestamps
  2. User can type in search box to filter report list
  3. Clicking a report displays its content in viewer panel
  4. Long reports scroll properly
  5. User can select and copy text from the viewer
**Plans:** 1 plan

Plans:
- [x] 22-01-PLAN.md — Master-detail results viewer with report list, search/filter/sort, viewer panel, and clipboard copy

#### Phase 23: Markdown Renderer
**Goal**: Report content renders with proper markdown formatting
**Depends on**: Phase 22
**Requirements**: RSLT-05
**Success Criteria** (what must be TRUE):
  1. Headers (H1-H3) render with distinct sizes
  2. Bullet lists render with proper indentation
  3. Code blocks render with monospace font and background
  4. Inline formatting (bold, italic, code) renders correctly
**Plans:** 1 plan

Plans:
- [ ] 23-01-PLAN.md — Markdown parsing with pulldown-cmark and block-based Slint rendering

#### Phase 24: Settings Dialog
**Goal**: User can configure application settings
**Depends on**: Phase 20
**Requirements**: SETT-01, SETT-02, SETT-03, SETT-04, SETT-05, SETT-06, SETT-07
**Success Criteria** (what must be TRUE):
  1. Settings button opens a dialog window
  2. Dialog has tabbed layout (General, Scanning, Paths)
  3. User can select game version from dropdown and change persists
  4. User can toggle scan options and changes persist
  5. User can browse for folder paths (native file dialog opens)
  6. OK saves changes; Cancel discards changes
**Plans**: TBD

Plans:
- [ ] 24-01: Settings dialog layout
- [ ] 24-02: Settings persistence and file dialogs

#### Phase 25: Platform Polish
**Goal**: Application is ready for Windows distribution
**Depends on**: Phase 21, Phase 22, Phase 23, Phase 24
**Requirements**: PLAT-01, PLAT-02, PLAT-03
**Success Criteria** (what must be TRUE):
  1. Application runs on Windows 10 and Windows 11
  2. UI is legible and properly scaled on 4K display (200% scaling)
  3. Application launches without GPU (software renderer fallback works)
**Plans**: TBD

Plans:
- [ ] 25-01: Platform testing and renderer fallback

#### Phase 26: Async Bridge Audit
**Goal**: Audit the async_bridge module of classic-shared-core for potential improvements for Slint GUI
**Depends on**: Phase 25
**Requirements**: TBD
**Success Criteria** (what must be TRUE):
  1. async_bridge module reviewed for Slint integration patterns
  2. Improvement opportunities identified and documented
  3. Recommendations implemented or deferred with rationale
**Plans**: TBD

Plans:
- [ ] 26-01: TBD (run /gsd:plan-phase 26 to break down)

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-5 | v1.0 | 14/14 | Complete | 2026-02-02 |
| 6-11 | v8.2.0-part2 | 14/14 | Complete | 2026-02-04 |
| 12-18 | v8.3.0 | 15/15 | Complete | 2026-02-05 |
| 19. Foundation | v9.0.0 | 2/2 | Complete | 2026-02-05 |
| 20. Core UI | v9.0.0 | 2/2 | Complete | 2026-02-05 |
| 21. Scan Ops | v9.0.0 | 2/2 | Complete | 2026-02-06 |
| 22. Results | v9.0.0 | 1/1 | Complete | 2026-02-06 |
| 23. Markdown | v9.0.0 | 0/1 | Not started | - |
| 24. Settings | v9.0.0 | 0/2 | Not started | - |
| 25. Platform | v9.0.0 | 0/1 | Not started | - |
| 26. Async Bridge Audit | v9.0.0 | 0/1 | Not started | - |

**Overall:** 3 milestones shipped, 50 plans completed | v9.0.0: 7/12 plans
