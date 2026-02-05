# Project Research Summary

**Project:** CLASSIC Slint GUI Migration
**Domain:** Desktop Application GUI Migration (PySide6/Qt to Rust/Slint)
**Researched:** 2026-02-05
**Confidence:** HIGH

## Executive Summary

CLASSIC is migrating from PySide6/Qt to Slint for its GUI while preserving all existing Rust business logic in `-core` crates. Slint is a modern declarative GUI framework that compiles `.slint` markup files to native Rust code, enabling direct integration with CLASSIC's async-first Rust architecture without the Python/PyO3 overhead.

The recommended approach uses Slint 1.15.0 with Skia renderer for Windows, integrating directly with existing `-core` crates via the established global Tokio runtime. Core features (tabbed interface, scan operations, settings, dark theme) are well-supported, but markdown rendering requires a custom solution using `pulldown-cmark` to parse reports and render them as styled Slint elements. The async integration pattern uses worker threads on the global Tokio runtime with `invoke_from_event_loop()` for UI updates, maintaining CLASSIC's ONE RUNTIME RULE.

The main risk is Tokio runtime conflicts: Slint's event loop cannot coexist with a current-thread Tokio runtime on the same thread. This is mitigated by using `slint::spawn_local()` with `async_compat` for UI-thread async operations and spawning background work on the existing multi-threaded runtime. Early validation of the async bridge pattern in Phase 1 (Foundation) is critical, as architectural errors here require complete rewrites.

## Key Findings

### Recommended Stack

Slint 1.15.0 (released 2026-02-04) is the latest stable release with dynamic GridLayout support and mature Tokio integration patterns. The project already has Slint 1.14.1 in workspace dependencies, so this is an upgrade rather than a new framework addition. Skia renderer is strongly recommended for Windows due to 2% CPU usage vs 30% with FemtoVG, plus superior Direct3D integration and text rendering quality.

**Core technologies:**
- **Slint 1.15.0**: Declarative GUI framework — compile-time type safety, GPU acceleration, native Rust integration
- **Skia renderer**: Graphics backend — 15x better CPU efficiency (2% vs 30%), Direct3D native on Windows
- **pulldown-cmark 0.13.0**: Markdown parsing — custom renderer for crash log reports until native markdown stabilizes in Slint 1.16+
- **rfd (Rust File Dialog)**: Native file dialogs — Slint has no built-in file picker, external crate required
- **async-compat 0.2**: Runtime bridging — bridges Slint's `spawn_local()` to the global Tokio runtime

**No new runtime dependencies**: Existing `classic-shared-core::get_runtime()` provides the Tokio runtime. No Python dependencies. No PyO3 layer.

### Expected Features

**Must have (table stakes):**
- TabWidget with 4 tabs (MAIN, BACKUP, ARTICLES, RESULTS) — native Slint widget
- Scan operations with progress feedback — worker threads + channel-based updates
- ListView for crash reports — built-in virtualized list with potential flicker under rapid updates
- Context menus on reports — native `ContextMenuArea` (Slint 1.10+)
- Settings dialog with tabs — `Dialog` element + TabWidget
- Dark theme — `fluent-dark` or `material-dark` built-in styles
- File/folder selection — via `rfd` crate (not built into Slint)
- Markdown report viewing — custom `pulldown-cmark` renderer (Slint's native markdown experimental, targets 1.16)

**Should have (differentiators):**
- Native Rust integration — eliminates AsyncBridge complexity, no GIL contention, type-safe entire stack
- Compile-time UI validation — `.slint` files checked at build, LSP integration for IDE errors
- Lightweight runtime — <300KB RAM vs 50-100MB with Qt+Python
- GPU-accelerated rendering — Skia or FemtoVG, significantly better performance than Qt software renderer

**Defer (v2+):**
- Tooltips — no native support, PopupWindow workaround clunky (tracked in issue #6446)
- Resizable splitter panes — custom TouchArea implementation required, fixed layout sufficient for MVP
- Rich text editing — read-only markdown viewing sufficient for crash reports

**Known gaps requiring custom implementation:**
- Markdown rendering (HIGH priority) — custom component using `pulldown-cmark` to generate styled Text elements
- File dialogs (MEDIUM priority) — integrate `rfd` crate, test on Windows
- Splitter (LOW priority) — custom TouchArea drag handler if needed

### Architecture Approach

The Slint GUI lives in `rust/ui-applications/classic-gui/` and integrates directly with business logic `-core` crates, completely bypassing the Python binding layer. The architecture follows the worker thread pattern: Slint's event loop runs on the main thread, async operations spawn on the existing global Tokio runtime (`classic_shared_core::get_runtime()`), and UI updates use `invoke_from_event_loop()` or `upgrade_in_event_loop()` to safely cross from worker threads back to the UI thread.

**Major components:**
1. **Slint Runtime (main thread)** — event loop, rendering, property reactivity, user input handling
2. **TokioBridge (cross-thread communication)** — spawns async operations on the global runtime, queues UI updates via channels
3. **ProgressBridge (progress feedback)** — timer-based polling of progress channels at 60 FPS to update progress bars
4. **Global Callbacks (state management)** — `.slint` files define `global ScanLogic`, `global SettingsLogic` with callbacks implemented in Rust
5. **Business logic integration** — direct calls to `OrchestratorCore::process_log()`, `YamlSettingsCache`, etc. (no FFI boundary)

**Data flow:** User clicks button → Slint callback → Clone `Weak<MainWindow>` → Spawn on Tokio runtime → Worker processes → Send progress via channel → Timer polls channel → `upgrade_in_event_loop()` updates UI → Worker completes → Final result via `upgrade_in_event_loop()`.

**Critical architectural constraint:** Slint's event loop and Tokio's current-thread runtime cannot coexist on the same thread. Use `spawn_local()` for UI-thread async, wrap with `async_compat::Compat` to bridge to the multi-threaded runtime.

### Critical Pitfalls

1. **Tokio current-thread runtime incompatibility** — Using `#[tokio::main]` or current-thread scheduler on the same thread as Slint causes deadlocks. Prevention: Use `spawn_local()` + `async_compat` for UI-thread async, spawn workers on existing multi-threaded runtime via `get_runtime().spawn()`. Phase 1 (Foundation) critical.

2. **Reference cycle memory leaks in callbacks** — Capturing strong `ComponentHandle` references in closures creates cycles where neither component nor callback can be dropped. Prevention: Always use `Weak<T>` via `handle.as_weak()`, upgrade with `upgrade_in_event_loop()`. Phase 1 (Foundation) — establish pattern immediately.

3. **No built-in markdown support** — Slint's `@markdown()` macro is experimental (SLINT_ENABLE_EXPERIMENTAL_FEATURES=1), targets Slint 1.16. Prevention: Build custom renderer using `pulldown-cmark` to parse markdown, render as styled Slint Text/Rectangle elements. Phase 3 (Results Viewer) — core requirement for crash log display.

4. **Cross-thread Rc/RefCell usage with models** — `VecModel<T>` uses `Rc` internally, cannot be sent across threads. Prevention: Workers return `Vec<T>`, main thread creates/updates `VecModel` via `invoke_from_event_loop()`. Phase 2 (Log Scanning) — affects all background operations.

5. **Widget style compile-time lock-in** — Style (fluent/material/cupertino) is set at compile time via `SLINT_STYLE` or cargo features, cannot change at runtime. Prevention: Decide on `fluent` style early, use `Palette` for runtime light/dark switching (Slint 1.6+). Phase 1 (Foundation) — irreversible decision.

## Implications for Roadmap

Based on research, suggested phase structure follows dependency ordering and risk mitigation:

### Phase 1: Foundation and Async Bridge
**Rationale:** Async architecture must be correct from the start. Tokio runtime conflicts (Pitfall #1) cause deadlocks requiring complete rewrites. Establishing weak reference patterns (Pitfall #2) early prevents memory leaks throughout the codebase.

**Delivers:**
- `classic-gui` crate structure in `rust/ui-applications/classic-gui/`
- Build system with `slint-build` compiling `.slint` files
- Minimal main window that displays (validates Slint integration)
- `TokioBridge` implementation using `async_compat` + global runtime
- `ProgressBridge` with channel-based updates and timer polling
- Weak reference patterns for all callbacks

**Addresses:**
- Widget style decision (fluent-dark for Windows)
- Tokio runtime integration (ONE RUNTIME RULE compliance)
- Window lifecycle (single event loop, hide/show pattern)

**Avoids:**
- Pitfall #1 (Tokio incompatibility)
- Pitfall #2 (reference cycles)
- Pitfall #4 (style lock-in)
- Pitfall #12 (event loop cannot run twice)

**Research flag:** LOW — Async patterns well-documented, existing `AsyncBridge` provides reference implementation. Validate early with smoke test (spawn worker, update progress bar).

---

### Phase 2: Core UI Layout and Settings
**Rationale:** UI structure and settings must exist before scan operations can display results or load configuration. Settings integration validates the TokioBridge pattern with real business logic (`classic-settings-core`, `classic-yaml-core`).

**Delivers:**
- Main window TabWidget with 4 tabs (MAIN, BACKUP, ARTICLES, RESULTS)
- Global callbacks in `.slint` files (`ScanLogic`, `SettingsLogic`)
- Settings dialog with tabs for configuration
- File dialog integration via `rfd` crate
- Settings loading/saving using `YamlSettingsCache`
- Dark theme application (`fluent-dark`)

**Uses:**
- Slint TabWidget, Dialog, Button, LineEdit, CheckBox, ComboBox
- `rfd` for folder selection (Browse buttons)
- `classic-settings-core` for YAML configuration
- `classic-yaml-core` for file operations

**Implements:** Global Callbacks state management pattern from ARCHITECTURE.md

**Avoids:**
- Pitfall #7 (no native file dialogs — use `rfd`)
- Pitfall #14 (VC++ redistributable — plan for bundling early)

**Research flag:** LOW — Standard widgets well-documented. File dialog integration has known patterns.

---

### Phase 3: Scan Operations
**Rationale:** Scanning is the core business logic of CLASSIC. This phase validates the worker thread pattern under real load and tests progress feedback reliability. Must complete before results viewer because it generates the data to display.

**Delivers:**
- Scan button callbacks spawning workers on Tokio runtime
- Integration with `OrchestratorCore::process_log()` and batch scanning
- Progress bar updates via `ProgressBridge` channels
- Enable/disable states for scan controls during operations
- Error handling with Slint Dialog elements
- Basic scan result storage in `VecModel`

**Uses:**
- `classic-scanlog-core` for log parsing and analysis
- `classic-file-io-core` for async file operations
- `classic-database-core` for results storage
- TokioBridge and ProgressBridge from Phase 1

**Addresses:**
- Background operations without blocking UI
- Progress feedback during long scans
- Error reporting to user

**Avoids:**
- Pitfall #1 (Tokio deadlock — use established worker pattern)
- Pitfall #3 (model threading — workers return Vec, main thread updates VecModel)
- Pitfall #6 (ListView not updating — explicit redraw triggers)
- Pitfall #8 (upgrade_in_event_loop reliability — timer-based backup)

**Research flag:** MEDIUM — Integration of Slint progress patterns with CLASSIC's existing `OrchestratorCore` batch operations. May need phase research for progress reporting granularity.

---

### Phase 4: Results Viewer (Markdown Renderer)
**Rationale:** Custom markdown rendering is the highest complexity feature (Pitfall #5). Defer until core scanning works to avoid blocking critical functionality. This is a presentation-layer concern, not business logic.

**Delivers:**
- Custom `MarkdownViewer` component in `.slint` files
- `pulldown-cmark` parser integration
- Renderer converting markdown events to styled Slint elements (Text, Rectangle)
- ListView for crash reports with context menus
- Report selection → markdown display flow
- Clipboard operations for report content

**Uses:**
- `pulldown-cmark` for parsing markdown to events
- Slint Text elements with styling for headers, bold, code blocks
- `ContextMenuArea` for right-click actions
- `arboard` crate for clipboard operations

**Addresses:**
- Markdown report viewing (table stakes feature)
- Report list with selection
- Context menu actions (View, Copy, Delete)

**Avoids:**
- Pitfall #5 (no native markdown — custom renderer)
- Pitfall #15 (image caching — monitor memory with large reports)

**Research flag:** HIGH — Custom markdown renderer is novel implementation. Recommend `/gsd:research-phase` to investigate rendering strategies (inline text vs layout hierarchy) and performance characteristics.

---

### Phase 5: Backup Operations and Remaining Features
**Rationale:** File backup is independent of core scanning functionality. Deferring to Phase 5 allows focus on critical path (scan → view results) first.

**Delivers:**
- Backup tab UI with file operations
- Integration with existing backup logic (if in `-core` crates)
- Update check functionality
- Pastebin upload integration
- About dialog
- Window geometry persistence

**Addresses:**
- File backup (existing feature parity)
- Auto-update checks
- Pastebin report sharing
- Window size/position saving

**Avoids:**
- Pitfall #10 (Windows scaling issues — test on 125%, 150%, 200% DPI)

**Research flag:** LOW — Standard file operations and network requests, well-documented patterns.

---

### Phase 6: Distribution and Polish
**Rationale:** Final phase focuses on Windows packaging, multi-renderer support for compatibility, and edge case handling discovered during earlier phases.

**Delivers:**
- Windows installer with VC++ redistributable
- Multi-renderer build (Skia primary, FemtoVG fallback, software emergency)
- Renderer auto-detection and fallback logic
- `SLINT_BACKEND` override documentation for users
- DPI awareness testing and fixes
- GPU driver compatibility testing (Intel, AMD, NVIDIA)

**Addresses:**
- Windows distribution (installer, dependencies)
- GPU driver compatibility (Pitfall #9)
- High-DPI display support (Pitfall #10)

**Avoids:**
- Pitfall #9 (GPU crashes — multi-renderer fallback)
- Pitfall #10 (scaling issues — DPI testing)
- Pitfall #13 (Skia build with spaces — CARGO_HOME configuration)
- Pitfall #14 (VC++ runtime — bundled installer)

**Research flag:** MEDIUM — Windows installer creation and renderer fallback logic. Phase research for packaging strategy.

---

### Phase Ordering Rationale

- **Foundation first (Phase 1)**: Async architecture errors require full rewrites. Validate Tokio integration before building features.
- **Settings before scanning (Phase 2 → 3)**: Scanning requires configuration to know where to find crash logs and how to process them.
- **Scanning before viewer (Phase 3 → 4)**: Results viewer needs scan data to display. Markdown renderer is presentation-layer, not blocking.
- **Defer backup and polish (Phase 5-6)**: Not on critical path for core workflow (scan logs → view results). Distribution concerns naturally come last.

**Dependency chain:** Foundation → Settings (loads config) → Scanning (uses config, generates reports) → Viewer (displays reports) → Backup/Polish (ancillary features).

**Risk mitigation:** Place high-risk items (Tokio integration, markdown rendering) in isolated phases with clear validation criteria. Phase 1 validates async patterns with smoke tests before building features. Phase 4 isolates markdown complexity from core functionality.

### Research Flags

**Phases likely needing deeper research during planning:**
- **Phase 4 (Results Viewer):** Custom markdown renderer is novel. Need research-phase to determine rendering strategy (inline styled Text vs hierarchical layout), performance characteristics with large reports (10K+ lines), and whether to stream rendering or parse-then-render.
- **Phase 6 (Distribution):** Windows installer creation and multi-renderer fallback logic. Phase research for packaging tools (WiX vs Inno Setup), VC++ bundling, and renderer auto-detection patterns.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Foundation):** Async patterns documented in research, existing `AsyncBridge` provides reference.
- **Phase 2 (Core UI Layout):** Standard Slint widgets, settings loading via existing `-core` crates.
- **Phase 3 (Scan Operations):** Worker thread pattern established in Phase 1, integration with existing `OrchestratorCore`.
- **Phase 5 (Backup/Features):** Standard file I/O and network operations.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Slint 1.15.0 released 2026-02-04 with official docs, Skia renderer performance verified in GitHub discussions, `pulldown-cmark` is mature (0.13.0) |
| Features | MEDIUM | Core widgets well-documented, but custom markdown renderer is untested. File dialog integration via `rfd` has known patterns but Windows-specific path issues reported. |
| Architecture | HIGH | Worker thread pattern officially recommended by Slint maintainers, global callback pattern documented in official recipes, ONE RUNTIME RULE alignment validated. |
| Pitfalls | HIGH | Tokio incompatibility confirmed in multiple GitHub discussions with official maintainer responses. Reference cycle pattern documented in official Weak struct docs. Markdown gap confirmed via issue #6684. |

**Overall confidence:** HIGH

Research is based on official Slint documentation (1.15 release, API docs), GitHub issues with maintainer responses, and verification that CLASSIC's existing architecture (global Tokio runtime, `-core` crates) aligns with recommended Slint patterns.

### Gaps to Address

**Markdown rendering performance:** Research identified the need for custom rendering but did not profile performance with CLASSIC's actual crash reports (potentially 10K+ lines, complex nested structures). **Mitigation:** Phase 4 should include performance testing with real reports and consider streaming rendering if parse-then-display is too slow.

**ListView rapid update flicker:** GitHub issue #7986 reports flickering with rapid content updates in ListView. CLASSIC's progress updates may trigger this. **Mitigation:** Phase 3 should test debouncing progress updates (e.g., max 60 FPS) and validate with stress tests (1000+ files).

**Windows file dialog path issues:** `rfd` crate has reported issues with `C:\Users\[User]\Downloads` path (issue #4773). **Mitigation:** Phase 2 should explicitly test file dialogs with system folders and edge case paths.

**GPU driver compatibility scope:** Research identified AMD OpenGL driver crashes but did not quantify prevalence. **Mitigation:** Phase 6 should prioritize multi-renderer fallback and collect telemetry during beta to determine if Skia should be default or if FemtoVG is safer primary choice.

## Sources

### Primary (HIGH confidence)
- [Slint 1.15 Release Blog](https://slint.dev/blog/slint-1.15-released) — version features, changelog
- [Slint Backends & Renderers](https://docs.slint.dev/latest/docs/slint/guide/backends-and-renderers/backends_and_renderers/) — Skia vs FemtoVG performance, renderer selection
- [Slint Cargo Features](https://docs.rs/slint/latest/slint/docs/cargo_features/index.html) — feature flag documentation
- [Slint Rust API Documentation](https://docs.slint.dev/latest/docs/rust/slint) — ComponentHandle, Weak, spawn_local APIs
- [Widget Styles](https://docs.slint.dev/latest/docs/slint/reference/std-widgets/style/) — compile-time style selection
- [pulldown-cmark 0.13.0](https://crates.io/crates/pulldown-cmark) — markdown parser version and features

### Secondary (MEDIUM confidence)
- [Tokio Integration Discussion #5784](https://github.com/slint-ui/slint/discussions/5784) — official maintainer guidance on runtime coexistence
- [Async Rust Discussion #4377](https://github.com/slint-ui/slint/discussions/4377) — async patterns and spawn_local usage
- [Model Threading Discussion #5300](https://github.com/slint-ui/slint/discussions/5300) — Rc/VecModel thread safety
- [ListView Performance Issue #7986](https://github.com/slint-ui/slint/discussions/7986) — virtualization and flicker reports
- [Markdown Support Issue #6684](https://github.com/slint-ui/slint/issues/6684) — rich text roadmap
- [File Dialog Discussion #3015](https://github.com/slint-ui/slint/discussions/3015) — external crate recommendations
- [Windows Crashes Discussion #6436](https://github.com/slint-ui/slint/discussions/6436) — GPU driver compatibility
- [Renderer Performance Discussion #5677](https://github.com/slint-ui/slint/discussions/5677) — Skia 2% CPU vs FemtoVG 30%

### Tertiary (LOW confidence)
- [Context Menu PR #9733](https://github.com/slint-ui/slint/pull/9733) — experimental markdown macro, not yet stable
- [Windows Scaling Issue #8765](https://github.com/slint-ui/slint/issues/8765) — DPI awareness, may be fixed in later versions

---
*Research completed: 2026-02-05*
*Ready for roadmap: yes*
