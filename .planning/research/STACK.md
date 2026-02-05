# Technology Stack: Slint GUI Integration

**Project:** CLASSIC Slint GUI Milestone
**Researched:** 2026-02-05
**Overall Confidence:** HIGH

## Executive Summary

This research covers stack additions for replacing the Python/PySide6 GUI with a native Slint GUI. The existing Rust business logic crates remain unchanged. Key findings:

- **Slint 1.15.0** is the current stable release (released 2026-02-04)
- **Tokio integration** is well-supported via the existing `AsyncBridge` pattern
- **Markdown rendering** is experimental in Slint; recommend `pulldown-cmark` + custom renderer
- **Skia renderer** recommended for Windows (better CPU efficiency, Direct3D support)

## Recommended Stack Additions

### Core GUI Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| slint | 1.15.0 | GUI framework | Current stable, already in workspace at 1.14.1 - upgrade to 1.15.0 |
| slint-build | 1.15.0 | Compile .slint files | Required for build.rs compilation of UI markup |

**Rationale:** Slint 1.15.0 (released 2026-02-04) is the latest stable. The project already has Slint 1.14.1 in workspace dependencies and an `AsyncBridge` designed for Slint. Upgrade to 1.15.0 for latest fixes and dynamic GridLayout.

### Rendering Backend

| Feature | Recommended | Why |
|---------|-------------|-----|
| `backend-winit` | Yes | Cross-platform windowing, Windows support via Direct3D |
| `renderer-skia` | Yes (Windows) | 2% CPU vs 30% with FemtoVG, Direct3D native, better text quality |
| `renderer-femtovg` | Fallback | Default renderer, lighter memory footprint, good for dev/testing |

**Rationale:** Skia provides significantly better CPU efficiency on Windows (2% vs ~30%) with superior text rendering quality. The increased memory (~60MB) is acceptable for a desktop application. FemtoVG remains as fallback.

### Markdown Rendering

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pulldown-cmark | 0.13.0 | Parse markdown reports | CommonMark compliant, pull parser, minimal deps |

**Slint's Native Markdown Status (MEDIUM confidence):**
- `@markdown()` macro merged in PR #9733 (Oct 2025) but **experimental**
- Requires `SLINT_ENABLE_EXPERIMENTAL_FEATURES=1` at build time
- Supports: bold, italic, strikethrough, code blocks, lists, hyperlinks
- Missing: complex tables, full styling control
- Targeted for Slint 1.16 stable release

**Recommended Approach:**
1. **Phase 1:** Use `pulldown-cmark` to parse markdown into events
2. **Phase 2:** Render as formatted text blocks with Slint's Text elements
3. **Phase 3:** Migrate to native `@markdown()` when stabilized in 1.16+

### Tokio Integration

**NO NEW DEPENDENCIES REQUIRED.** The existing pattern is correct:

| Component | Status | Notes |
|-----------|--------|-------|
| `classic-shared-core::get_runtime()` | Existing | Global Tokio runtime (ONE RUNTIME RULE) |
| `classic-shared-core::AsyncBridge` | Existing | Slint event loop bridge |
| `async-compat` | NOT NEEDED | Only needed if using `slint::spawn_local` |

**Architecture (already implemented in codebase):**
```rust
// In Slint button callback:
AsyncBridge::run_with_ui_update(
    async_operation(),  // Runs on shared Tokio runtime
    |result| {          // Runs on Slint event loop
        window.set_data(result);
    }
);
```

The existing `AsyncBridge::run_with_ui_update()` spawns directly on the Tokio runtime via `get_runtime().spawn()` and uses `slint::invoke_from_event_loop()` for UI updates. This is the optimal pattern.

## Workspace Cargo.toml Changes

### Update Version

```toml
[workspace.dependencies]
# GUI (Slint) - UPDATE to latest
slint = "1.15.0"  # Was 1.14.1

# Markdown parsing (NEW)
pulldown-cmark = { version = "0.13.0", default-features = false }
```

### New Build Dependency

```toml
[workspace.dependencies]
# For .slint file compilation
slint-build = "1.15.0"
```

## New Crate: classic-gui

Create: `rust/ui-applications/classic-gui/Cargo.toml`

```toml
[package]
name = "classic-gui"
version = "0.1.0"
edition = "2024"
rust-version = "1.85.0"

[dependencies]
# GUI framework
slint = { workspace = true, features = [
    "backend-winit",
    "renderer-skia",      # Primary: Better CPU efficiency on Windows
    "renderer-femtovg",   # Fallback renderer
    "accessibility",      # Screen reader support
] }

# Async bridge (from foundation)
classic-shared-core = { path = "../../foundation/classic-shared-core", features = ["gui-bridge"] }

# Business logic crates (as needed)
classic-yaml-core = { path = "../../business-logic/classic-yaml-core" }
classic-scanlog-core = { path = "../../business-logic/classic-scanlog-core" }
classic-settings-core = { path = "../../business-logic/classic-settings-core" }
classic-file-io-core = { path = "../../business-logic/classic-file-io-core" }

# Markdown rendering
pulldown-cmark = { workspace = true }

# Error handling
anyhow = { workspace = true }
thiserror = { workspace = true }

# Logging
log = { workspace = true }

[build-dependencies]
slint-build = { workspace = true }

[[bin]]
name = "classic-gui"
path = "src/main.rs"
```

## Build System Changes

### build.rs Required

Create: `rust/ui-applications/classic-gui/build.rs`

```rust
fn main() {
    slint_build::compile("ui/main.slint").unwrap();
}
```

### UI File Structure

```
rust/ui-applications/classic-gui/
├── Cargo.toml
├── build.rs
├── src/
│   ├── main.rs
│   ├── app.rs
│   └── markdown_renderer.rs
└── ui/
    ├── main.slint
    ├── components/
    │   ├── scan_panel.slint
    │   ├── results_view.slint
    │   └── settings_panel.slint
    └── styles/
        └── theme.slint
```

## What NOT to Add

| Don't Add | Why |
|-----------|-----|
| `async-compat` | Existing AsyncBridge handles Tokio integration correctly |
| `slint-interpreter` | Not needed - use compile-time .slint with slint-build |
| `renderer-software` | CPU rendering too slow for desktop, Skia handles everything |
| `egui` or `iced` | Different frameworks - stick with Slint as originally planned |
| `comrak` | pulldown-cmark is sufficient and lighter |
| New Tokio runtime | ONE RUNTIME RULE - use existing `get_runtime()` |

## Platform-Specific Notes

### Windows (Primary Platform)

- **Renderer:** Skia with Direct3D backend (automatic via `renderer-skia`)
- **Build:** MSVC toolchain required for Skia
- **Distribution:** Single binary, no runtime dependencies
- **Performance:** ~2% CPU at idle, ~60MB memory

### Linux/macOS (Secondary)

- **Renderer:** Skia with Vulkan (Linux) or Metal (macOS)
- **Fallback:** FemtoVG with OpenGL if Skia unavailable
- **Selection:** Runtime via `SLINT_BACKEND` environment variable

## Migration Path from PySide6

| Python Component | Rust Replacement |
|-----------------|------------------|
| `CLASSIC_Interface.py` | `classic-gui` binary |
| `ClassicLib.AsyncBridge` | `classic_shared_core::AsyncBridge` |
| PySide6 widgets | `.slint` component files |
| Qt signals/slots | Slint callbacks and properties |
| QThread workers | `AsyncBridge::run_with_ui_update()` |

## Sources

### HIGH Confidence (Official Documentation)
- [Slint 1.15 Release Blog](https://slint.dev/blog/slint-1.15-released) - Version and features
- [Slint Cargo Features](https://docs.rs/slint/latest/slint/docs/cargo_features/index.html) - Feature flags
- [Slint Backends & Renderers](https://docs.slint.dev/latest/docs/slint/guide/backends-and-renderers/backends_and_renderers/) - Renderer options
- [GitHub Releases](https://github.com/slint-ui/slint/releases) - Version history

### MEDIUM Confidence (GitHub Issues/Discussions)
- [Rich Text Support #9560](https://github.com/slint-ui/slint/issues/9560) - Markdown status
- [Tokio Integration #5784](https://github.com/slint-ui/slint/discussions/5784) - Async patterns
- [PR #9733](https://github.com/slint-ui/slint/pull/9733) - Markdown implementation (merged)
- [Renderer Performance #5677](https://github.com/slint-ui/slint/discussions/5677) - Skia vs FemtoVG CPU usage

### HIGH Confidence (Crates)
- [pulldown-cmark 0.13.0](https://crates.io/crates/pulldown-cmark) - Latest version
- [pulldown-cmark Releases](https://github.com/pulldown-cmark/pulldown-cmark/releases) - v0.13.0 features
