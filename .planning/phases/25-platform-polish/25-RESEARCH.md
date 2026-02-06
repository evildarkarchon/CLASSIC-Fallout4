# Phase 25: Platform Polish - Research

**Researched:** 2026-02-05
**Domain:** Windows distribution readiness, renderer fallback, HiDPI, packaging
**Confidence:** HIGH

## Summary

Phase 25 is about making the existing Slint GUI application production-ready for Windows distribution. The application already works (Phases 19-24 complete) but needs: (1) renderer fallback for systems without GPU acceleration, (2) proper HiDPI scaling via Windows manifest, (3) distribution packaging with static CRT and embedded icon, and (4) launch experience polish including no console window and file logging.

The codebase is well-positioned. Slint 1.15 with the `renderer-skia` feature already includes automatic GPU-to-software fallback. Window geometry persistence is already implemented per-tab. The main work areas are: adding the `renderer-software` Cargo feature as a compiled-in fallback, embedding a Windows application manifest for DPI awareness, replacing all `eprintln!` calls with `tracing` (already a workspace dependency), configuring static CRT linking, and embedding the icon via `tauri-winres`.

**Primary recommendation:** This phase splits naturally into 4 plans: (1) Renderer fallback + BackendSelector, (2) HiDPI manifest + window defaults, (3) File logging + console suppression, (4) Distribution packaging (icon, CRT, windows_subsystem).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Renderer fallback**: Silent fallback to software renderer when GPU is unavailable (no user notification). Use Skia software (CPU rasterizer) as the fallback. Support `SLINT_BACKEND` environment variable override for power users.
- **HiDPI scaling**: Follow system DPI scaling exactly. Per-monitor DPI awareness with re-render on monitor drag. Embed Windows application manifest declaring per-monitor-v2 DPI awareness. Default window size 800x600 at 100% scaling.
- **Distribution packaging**: Folder-based distribution (folder with .exe + assets, zipped). Static link Visual C++ runtime into .exe (zero DLL dependencies). Embed CLASSIC icon into .exe via Windows resource file (.rc).
- **Launch experience**: No console window using `#![windows_subsystem = "windows"]`. Log to file always in app data directory. Self-healing on startup failure (delete corrupted state, recreate defaults). Restore window position and size across launches.

### Claude's Discretion
- Total rendering failure error handling approach (when both GPU and software fail)
- Log file rotation strategy and naming
- Exact self-healing recovery logic (what gets reset vs preserved)
- Whether window geometry is already persisted from Phase 20 (verify and extend if needed)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| slint | 1.15.0 | GUI framework (already in workspace) | Already chosen, has built-in Skia software fallback |
| tracing | 0.1.44 | Structured logging (already in workspace) | Standard Rust logging, replaces eprintln! |
| tracing-subscriber | 0.3.22 | Log formatting (already in workspace) | Pairs with tracing for file output |
| tracing-appender | 0.2.x | File-based log output with rotation | Official companion to tracing-subscriber |
| tauri-winres | 0.3.5 | Icon + manifest embedding in build.rs | Actively maintained fork of winres, uses embed-resource internally |
| embed-manifest | latest | DPI awareness manifest embedding | Alternative to tauri-winres for manifest; can combine with it |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| directories | 6.0.0 | Config/data/log directories (already in workspace) | Already used for settings and state paths |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| tauri-winres | winres (original) | winres is unmaintained, broken on Rust 1.61+; tauri-winres is the maintained fork |
| tauri-winres | embed-manifest + manual .rc | More control but more complexity; tauri-winres handles both icon and manifest in one tool |
| tracing-appender | manual file I/O | tracing-appender provides non-blocking writes and rotation out of the box |

**Installation (new dependencies to add to classic-gui Cargo.toml):**
```toml
[dependencies]
tracing = { workspace = true }
tracing-subscriber = { workspace = true, features = ["fmt"] }
tracing-appender = "0.2"

[build-dependencies]
tauri-winres = "0.3"
```

**Installation (workspace Cargo.toml -- add if not present):**
```toml
tracing-appender = "0.2"
```

## Architecture Patterns

### Recommended Project Structure Changes
```
rust/ui-applications/classic-gui/
├── assets/
│   ├── CLASSIC.ico           # Already exists
│   └── classic-gui.manifest  # NEW: DPI awareness manifest XML
├── build.rs                  # MODIFY: Add tauri-winres for icon + manifest
├── src/
│   ├── main.rs               # MODIFY: Add logging init, BackendSelector, self-healing
│   ├── logging.rs            # NEW: File logging initialization
│   └── ...                   # MODIFY: Replace eprintln! with tracing macros
└── Cargo.toml                # MODIFY: Add dependencies and features
```

### Pattern 1: Slint Renderer Fallback with BackendSelector
**What:** Use Slint's `BackendSelector` API to try Skia GPU first, then fall back to Skia software, then to the software renderer.
**When to use:** At application startup, before creating the MainWindow.
**Confidence:** HIGH (verified via Slint official docs and GitHub discussions)

The current Cargo.toml has `features = ["backend-winit", "renderer-skia", "image-default-formats"]`. The key finding is:

1. **Slint's Skia renderer already includes automatic software fallback.** When GPU (Direct3D/OpenGL/Vulkan) is unavailable, the Skia renderer automatically falls back to CPU-based Skia software rendering. This was confirmed in Slint issue #5270 and discussion #3782.

2. **Adding `renderer-software` as an additional feature** provides a secondary fallback if Skia itself fails to initialize entirely.

3. **`SLINT_BACKEND` environment variable** is respected by Slint automatically -- no code needed. Users can set `SLINT_BACKEND=winit-skia` or `SLINT_BACKEND=winit-software` to force a specific renderer.

4. **`BackendSelector`** can be used programmatically for more control, but is optional since Slint handles the common case automatically.

**Example (Cargo.toml features):**
```toml
slint = { workspace = true, features = [
    "backend-winit",
    "renderer-skia",
    "renderer-software",    # Fallback if Skia entirely fails
    "image-default-formats"
] }
```

**Example (programmatic fallback in main.rs -- optional):**
```rust
// Source: https://docs.slint.dev/latest/docs/rust/slint/struct.BackendSelector
use slint::BackendSelector;

fn init_renderer() -> Result<(), slint::PlatformError> {
    // Try Skia first (will auto-fallback to Skia software if GPU unavailable)
    let result = BackendSelector::new()
        .renderer_name("skia".into())
        .select();

    match result {
        Ok(()) => Ok(()),
        Err(_) => {
            // If Skia entirely fails, fall back to software renderer
            BackendSelector::new()
                .renderer_name("software".into())
                .select()
        }
    }
}
```

### Pattern 2: Windows Application Manifest for DPI Awareness
**What:** Embed a manifest declaring per-monitor-v2 DPI awareness so Windows does not bitmap-scale the application.
**When to use:** Build-time embedding via build.rs.
**Confidence:** HIGH (verified via Microsoft Learn docs)

**Key finding:** Winit (Slint's windowing backend) already calls `SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)` at runtime. However, embedding a manifest is still the recommended approach because:
- The manifest takes priority and is more reliable
- It prevents any window of time before the runtime call where Windows might apply bitmap scaling
- It declares compatibility with specific Windows versions

**Example (classic-gui.manifest):**
```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0"
          xmlns:asmv3="urn:schemas-microsoft-com:asm.v3">
    <assemblyIdentity
        type="win32"
        name="com.classic.classic-gui"
        version="9.0.0.0"
        processorArchitecture="*"/>
    <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
        <application>
            <!-- Windows 10 / 11 -->
            <supportedOS Id="{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}"/>
            <!-- Windows 8.1 -->
            <supportedOS Id="{1f676c76-80e1-4239-95bb-83d0f6d0da78}"/>
        </application>
    </compatibility>
    <asmv3:application>
        <asmv3:windowsSettings>
            <dpiAware xmlns="http://schemas.microsoft.com/SMI/2005/WindowsSettings">true/PM</dpiAware>
            <dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">PerMonitorV2,PerMonitor</dpiAwareness>
            <activeCodePage xmlns="http://schemas.microsoft.com/SMI/2019/WindowsSettings">UTF-8</activeCodePage>
            <longPathAware xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">true</longPathAware>
        </asmv3:windowsSettings>
    </asmv3:application>
    <asmv3:trustInfo>
        <asmv3:security>
            <asmv3:requestedPrivileges>
                <asmv3:requestedExecutionLevel level="asInvoker" uiAccess="false"/>
            </asmv3:requestedPrivileges>
        </asmv3:security>
    </asmv3:trustInfo>
</assembly>
```

### Pattern 3: Static CRT Linking
**What:** Statically link the MSVC Visual C++ runtime to eliminate DLL dependencies.
**When to use:** Release builds for distribution.
**Confidence:** HIGH (verified via Rust RFC 1721 and official docs)

**Example (.cargo/config.toml):**
```toml
[target.'cfg(all(windows, target_env = "msvc"))']
rustflags = ["-C", "target-feature=+crt-static"]
```

**Note:** This increases binary size but eliminates the need for `VCRUNTIME140.dll` on target systems. For a GUI app this tradeoff is worthwhile since the Skia renderer already adds significant binary size.

### Pattern 4: File Logging with tracing-appender
**What:** Replace all `eprintln!` calls with `tracing` macros and route output to a log file.
**When to use:** Application initialization, before any other operations.
**Confidence:** HIGH (tracing ecosystem is the standard Rust logging solution)

**Example (logging initialization):**
```rust
use tracing_appender::rolling;
use tracing_subscriber::fmt;
use tracing_subscriber::prelude::*;

fn init_logging() -> tracing_appender::non_blocking::WorkerGuard {
    let log_dir = directories::ProjectDirs::from("com", "classic", "classic-gui")
        .map(|dirs| dirs.data_dir().to_path_buf())
        .unwrap_or_else(|| std::env::current_dir().unwrap_or_default());

    // Create a non-rolling file appender (overwrite each launch)
    let file_appender = rolling::never(&log_dir, "classic-gui.log");
    let (non_blocking, guard) = tracing_appender::non_blocking(file_appender);

    tracing_subscriber::fmt()
        .with_writer(non_blocking)
        .with_ansi(false)
        .with_target(true)
        .with_level(true)
        .init();

    guard // MUST be held for the lifetime of the application
}
```

### Anti-Patterns to Avoid
- **Do NOT use `eprintln!` in release builds with `windows_subsystem = "windows"`:** stderr is null, output is silently lost. Use tracing instead.
- **Do NOT create multiple log files or rotate on size without reason:** This is a desktop app, not a server. Simple overwrite-each-launch is sufficient.
- **Do NOT embed the manifest via raw linker args:** Use `tauri-winres` for cross-toolchain compatibility.
- **Do NOT call `SetProcessDpiAwarenessContext` manually:** Winit already does this, and the manifest handles the declarative side.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Windows resource embedding | Manual .rc files + rc.exe invocation | `tauri-winres` in build.rs | Handles MSVC/MinGW/cross-compilation automatically |
| DPI awareness declaration | Manual Win32 API calls | Manifest XML + `tauri-winres` | Manifest is declarative and processed before any window creation |
| Log file writing | Manual `File::create` + `write!` | `tracing` + `tracing-appender` | Non-blocking, structured, already in workspace |
| Renderer fallback logic | Manual GPU capability detection | Slint's built-in fallback + `renderer-software` feature | Slint's Skia renderer auto-falls back to CPU; adding software renderer feature covers the edge case |

**Key insight:** Most of the "hard" work here is already handled by the existing stack. Slint handles renderer fallback. Winit handles DPI at runtime. The workspace already has tracing. The main work is wiring these together and configuring build-time settings.

## Common Pitfalls

### Pitfall 1: eprintln! Silently Lost with windows_subsystem = "windows"
**What goes wrong:** All `eprintln!` output disappears because there is no console. Errors during settings save, state load, etc. become invisible.
**Why it happens:** `#![windows_subsystem = "windows"]` means the process has no console; stderr writes return EBADF.
**How to avoid:** Replace ALL `eprintln!` calls with `tracing::error!` / `tracing::warn!` before adding the `windows_subsystem` attribute. There are currently 12 `eprintln!` calls across main.rs and settings.rs.
**Warning signs:** Application silently fails to save settings or state with no indication to the user.

### Pitfall 2: tracing-appender Guard Dropped Too Early
**What goes wrong:** Log file stops receiving messages partway through application lifetime.
**Why it happens:** The `WorkerGuard` returned by `tracing_appender::non_blocking()` flushes and closes the log when dropped. If it goes out of scope before the app exits, later log messages are lost.
**How to avoid:** Hold the guard in main() for the entire application lifetime. Use `let _guard = init_logging();` at the top of main().
**Warning signs:** Log file is truncated or missing late-stage error messages.

### Pitfall 3: Static CRT Linking Applies to ALL Crates
**What goes wrong:** Setting `+crt-static` in `.cargo/config.toml` affects all crates in the workspace, including Python bindings (PyO3 crates).
**Why it happens:** The config.toml applies to the entire workspace build.
**How to avoid:** Either scope the rustflag to the specific binary build, or use `RUSTFLAGS` only when building the GUI. Alternative: use a separate `.cargo/config.toml` in the classic-gui directory, or pass the flag via the build command rather than config.
**Warning signs:** PyO3 crates fail to build or produce incompatible binaries.

### Pitfall 4: Window Position Restored Off-Screen
**What goes wrong:** User disconnects a monitor, and the saved window position is now off-screen. The app appears to not launch.
**Why it happens:** Window geometry is restored to coordinates that no longer correspond to any visible display.
**How to avoid:** Before restoring window position, validate that the coordinates are within the bounds of a currently connected monitor. If not, reset to centered on primary monitor. (Note: Slint/winit may handle this partially, but explicit validation is safer.)
**Warning signs:** Users report "app doesn't start" after monitor configuration changes.

### Pitfall 5: Self-Healing Deletes Too Much State
**What goes wrong:** Overly aggressive self-healing deletes user settings along with corrupted state.
**Why it happens:** No distinction between "corrupted state file" and "valid settings file."
**How to avoid:** Self-healing should only delete/recreate the specific file that failed to parse. The state file (`window_state.json`) and settings file (`settings.yaml`) are separate files. If settings load fails, only reset settings. If state load fails, only reset state.
**Warning signs:** Users lose their configured paths and preferences after a crash.

## Code Examples

### Build Script with Icon + Manifest Embedding
```rust
// Source: tauri-winres docs (https://docs.rs/tauri-winres)
// build.rs
fn main() {
    // Compile Slint UI files
    let config = slint_build::CompilerConfiguration::new()
        .with_style("fluent-dark".into());
    slint_build::compile_with_config("ui/main.slint", config)
        .expect("Slint compilation failed");

    // Windows resource embedding (icon + manifest)
    #[cfg(target_os = "windows")]
    {
        let mut res = tauri_winres::WindowsResource::new();
        res.set_icon("assets/CLASSIC.ico");
        res.set_manifest_file("assets/classic-gui.manifest");
        res.compile()
            .expect("Failed to compile Windows resources");
    }
}
```

### Main Entry Point with Logging + Self-Healing + Renderer Init
```rust
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    // 1. Initialize logging FIRST (before anything else)
    let _log_guard = init_logging();

    // 2. Initialize renderer (optional -- Slint handles auto-fallback)
    if let Err(e) = init_renderer() {
        // Total failure -- show native Windows message box
        show_fatal_error(&format!("Failed to initialize renderer: {}", e));
        std::process::exit(1);
    }

    // 3. Initialize Tokio runtime
    let _ = get_runtime();

    // 4. Load state with self-healing
    let state = load_state_with_healing();

    // 5. Create window and run
    let window = MainWindow::new().expect("Failed to create main window");
    // ... rest of initialization
}
```

### Self-Healing State Load
```rust
fn load_state_with_healing() -> AppState {
    // Try loading window state
    let window_state = match try_load_window_state() {
        Ok(state) => state,
        Err(e) => {
            tracing::warn!("Corrupted window state, resetting: {}", e);
            delete_state_file();
            WindowState::default()
        }
    };

    // Try loading settings (separate file, separate healing)
    let settings = match try_load_settings() {
        Ok(config) => config,
        Err(e) => {
            tracing::warn!("Corrupted settings, resetting: {}", e);
            delete_settings_file();
            ClassicConfig::default()
        }
    };

    AppState {
        cancel_token: None,
        window_state,
        initialized: false,
        reports: None,
        settings,
    }
}
```

### Fatal Error Dialog (When Renderer Completely Fails)
```rust
// For total rendering failure -- use Windows MessageBox directly
#[cfg(target_os = "windows")]
fn show_fatal_error(message: &str) {
    use std::ffi::OsStr;
    use std::os::windows::ffi::OsStrExt;
    use std::ptr;

    let wide_msg: Vec<u16> = OsStr::new(message)
        .encode_wide()
        .chain(std::iter::once(0))
        .collect();
    let wide_title: Vec<u16> = OsStr::new("CLASSIC - Fatal Error")
        .encode_wide()
        .chain(std::iter::once(0))
        .collect();

    unsafe {
        // MB_OK | MB_ICONERROR
        windows_sys::Win32::UI::WindowsAndMessaging::MessageBoxW(
            ptr::null_mut(),
            wide_msg.as_ptr(),
            wide_title.as_ptr(),
            0x00000010, // MB_ICONERROR
        );
    }
}
```

**Note on the fatal error dialog:** Using `windows-sys` is one option, but it adds a dependency. A simpler approach is to write the error to the log file and exit, since by definition the screen cannot be rendered. The user would check the log file. Alternatively, `std::process::Command` could launch a PowerShell one-liner to show a message box. This is a Claude's discretion area.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| winres crate | tauri-winres | 2023+ | winres broken on Rust 1.61+, tauri-winres is the maintained fork |
| Manual DPI calls | Manifest + winit runtime DPI | Stable since winit 0.20+ | Combined manifest + runtime is most reliable |
| env_logger for file logging | tracing + tracing-appender | 2022+ | Non-blocking, structured, better ecosystem |
| FemtoVG (Slint default) | Skia (project choice from Phase 19) | Phase 19-01 | Better visual quality, auto GPU-to-software fallback |

**Key version notes:**
- Slint 1.15.0 supports `BackendSelector` for programmatic renderer selection
- `tracing-appender` 0.2.x provides `rolling::never()` for non-rotating files
- `tauri-winres` 0.3.5 is the latest, using `embed-resource` internally

## Existing Codebase Findings

### Window Geometry Persistence: ALREADY IMPLEMENTED
Phase 20-02 already implemented per-tab window geometry persistence. The `state.rs` module has:
- `TabGeometry { x, y, width, height, maximized }` struct
- `WindowState` with `HashMap<String, TabGeometry>` for per-tab geometries
- `load_window_state()` and `save_window_state()` functions
- Geometry is saved on tab switch and on exit
- Geometry is restored on startup

**Verdict:** Window geometry persistence is already complete. No new work needed for this requirement. The existing code restores position and size correctly.

### Default Window Size: NEEDS IMPLEMENTATION
The current code does not set a default window size. When no saved geometry exists, `TabGeometry::default()` returns all zeros, and the `if geometry.width > 0 && geometry.height > 0` check skips restoration. Slint then uses its own default size. The user wants 800x600 at 100% scaling as the explicit default.

### eprintln! Usage: 12 CALLS NEED REPLACEMENT
Found 12 `eprintln!` calls across `main.rs` and `settings.rs` that will become silent with `windows_subsystem = "windows"`. All must be replaced with `tracing::error!` or `tracing::warn!`.

### Icon Asset: ALREADY EXISTS
`rust/ui-applications/classic-gui/assets/CLASSIC.ico` exists and is ready for embedding.

### No .rc or .manifest Files: NEED CREATION
No Windows resource files or manifests exist yet. Both must be created.

### No Console Suppression: NEEDS IMPLEMENTATION
`main.rs` does not have `#![windows_subsystem = "windows"]` yet.

### Renderer Features: PARTIALLY CONFIGURED
Current features: `["backend-winit", "renderer-skia", "image-default-formats"]`. Missing `renderer-software` for the secondary fallback path.

## Open Questions

1. **Fatal error handling for total renderer failure**
   - What we know: When both Skia GPU and Skia software fail, and the software renderer also fails, the application cannot display anything.
   - What's unclear: How to notify the user without any rendering capability.
   - Recommendation: Log the error to file, then use `std::process::Command` to invoke a PowerShell message box, or simply exit with an error code. The log file provides diagnostics. In practice, this scenario is extremely rare (software renderer has almost zero system requirements).

2. **CRT static linking scope**
   - What we know: `.cargo/config.toml` applies workspace-wide. The GUI needs static CRT but PyO3 crates may not.
   - What's unclear: Whether PyO3 crates are affected when building only the GUI binary.
   - Recommendation: Place `+crt-static` in `rust/ui-applications/classic-gui/.cargo/config.toml` (crate-local) rather than the workspace-level config, OR only pass `RUSTFLAGS=-C target-feature=+crt-static` when building the GUI binary specifically. A build script/profile approach may also work.

3. **Off-screen window position validation**
   - What we know: Saved positions can become invalid when monitor configuration changes.
   - What's unclear: Whether Slint/winit already clamps window positions to visible displays.
   - Recommendation: Add basic bounds checking when restoring position. If x/y are negative by more than 100px or exceed 10000, reset to defaults.

## Sources

### Primary (HIGH confidence)
- [Slint Backends & Renderers docs](https://docs.slint.dev/latest/docs/slint/guide/backends-and-renderers/backends_and_renderers/) - Renderer selection, SLINT_BACKEND env var
- [Slint Cargo Features](https://docs.slint.dev/latest/docs/slint/../rust/slint/docs/cargo_features/) - renderer-skia, renderer-software feature flags
- [Slint BackendSelector API](https://docs.slint.dev/latest/docs/rust/slint/struct.BackendSelector) - Programmatic renderer selection
- [Slint Discussion #3782](https://github.com/slint-ui/slint/discussions/3782) - Skia software mode, auto-fallback confirmation
- [Slint Issue #5270](https://github.com/slint-ui/slint/issues/5270) - Skia crash auto-fallback to software in release
- [Microsoft Learn: DPI Awareness](https://learn.microsoft.com/en-us/windows/win32/hidpi/setting-the-default-dpi-awareness-for-a-process) - Per-Monitor-V2 manifest XML
- [Rust RFC 1721: crt-static](https://rust-lang.github.io/rfcs/1721-crt-static.html) - Static CRT linking
- [tauri-winres docs](https://docs.rs/tauri-winres/latest/tauri_winres/) - WindowsResource API
- [tracing-appender docs](https://docs.rs/tracing-appender/latest/tracing_appender/) - File logging with rotation

### Secondary (MEDIUM confidence)
- [dev.to: Embed Windows Manifest in Rust](https://dev.to/carey/embed-a-windows-manifest-in-your-rust-program-26j2) - Comprehensive manifest embedding guide
- [Slint Issue #3235](https://github.com/slint-ui/slint/issues/3235) - windows_subsystem documentation
- [Rust Forum: Static CRT](https://users.rust-lang.org/t/statically-link-to-msvc-on-windows/108952) - Community guidance on CRT static linking
- [Winit DPI source](https://docs.rs/winit/0.20.0-alpha1/src/winit/platform_impl/windows/dpi.rs.html) - Winit's automatic DPI awareness calls

### Tertiary (LOW confidence)
- None -- all findings verified with primary or secondary sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries are already in use or are the clear standard choice
- Architecture: HIGH - Patterns verified against official Slint docs and existing codebase
- Pitfalls: HIGH - Based on actual codebase analysis (12 eprintln! calls found) and documented Windows behavior
- Renderer fallback: HIGH - Confirmed via multiple Slint GitHub sources that Skia auto-falls back
- Window geometry: HIGH - Verified by reading actual source code (state.rs, main.rs)

**Research date:** 2026-02-05
**Valid until:** 2026-03-07 (30 days -- stable domain, no fast-moving APIs)
