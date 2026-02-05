# Domain Pitfalls: Slint GUI Migration

**Domain:** Desktop GUI migration from PySide6/Qt to Slint (Rust)
**Researched:** 2026-02-05
**Confidence:** HIGH (verified via official Slint documentation and GitHub issues)

## Critical Pitfalls

Mistakes that cause rewrites, architectural problems, or major delays.

### Pitfall 1: Tokio Current-Thread Runtime Incompatibility

**What goes wrong:** Using `#[tokio::main]` or Tokio's current-thread scheduler on the same thread as Slint's event loop causes futures to never complete or deadlock.

**Why it happens:** Slint's event loop cannot yield to Tokio's runtime. Tokio futures require regular yielding to the Tokio runtime for fairness, and the current-thread scheduler expects to be the sole executor on its thread.

**Consequences:**
- Async operations hang indefinitely
- UI becomes unresponsive
- Progress updates never arrive
- Complete architectural rework required

**Prevention:**
1. Use `slint::spawn_local()` for async operations on the main thread
2. Wrap Tokio futures with `async_compat::Compat::new()` to use a shared multi-threaded runtime
3. Run worker operations on a separate multi-threaded Tokio runtime
4. Communicate between worker threads and UI via channels + `invoke_from_event_loop()`

**Detection:**
- Futures never complete despite logic being correct
- UI freezes when starting async operations
- `spawn_local` panics about runtime context

**Phase to address:** Phase 1 (Foundation) - Must establish async architecture correctly from the start

**Sources:**
- [Slint + async Rust discussion](https://github.com/slint-ui/slint/discussions/4377)
- [Using Slint with Tokio main thread](https://github.com/slint-ui/slint/discussions/5784)
- [spawn_local documentation](https://docs.slint.dev/latest/docs/rust/slint/fn.spawn_local)

---

### Pitfall 2: Reference Cycle Memory Leaks in Callbacks

**What goes wrong:** Capturing strong component references (`ComponentHandle`) in callbacks creates reference cycles that leak the entire component.

**Why it happens:** Callbacks form closures that hold references. If a callback holds a strong reference to the component, and the component owns the callback, neither can be dropped.

**Consequences:**
- Memory usage grows continuously
- Components never deallocate
- Eventually crashes on memory exhaustion
- Hard to diagnose without memory profiling

**Prevention:**
1. Always use `Weak<T>` references in callbacks: `let weak = handle.as_weak();`
2. Use `upgrade()` or `upgrade_in_event_loop()` to access component
3. Review all callbacks for captured strong references during code review

**Detection:**
- Memory grows with each window open/close cycle
- Components remain in memory after window closes
- Rust analyzer warnings about captured references (sometimes)

**Phase to address:** Phase 1 (Foundation) - Establish correct callback patterns in initial code

**Sources:**
- [Weak struct documentation](https://docs.slint.dev/latest/docs/rust/slint/struct.Weak.html)
- Official docs: "Strong references should not be captured by the functions given to a lambda"

---

### Pitfall 3: Cross-Thread Rc/RefCell Usage with Models

**What goes wrong:** Attempting to send `Rc<VecModel<T>>` or similar non-Send types across threads causes compile errors or runtime panics.

**Why it happens:** Slint's `VecModel` uses `Rc` internally for reference counting, which is not thread-safe. Developers try to share models between worker threads and UI.

**Consequences:**
- Compile-time errors about `Rc` not being `Send`
- Runtime panics if bypassed with unsafe code
- Architecture must be redesigned

**Prevention:**
1. Never share `Rc`-based types across threads
2. Use channels to send raw data between threads
3. Update models only on the main thread using `invoke_from_event_loop()`
4. Worker threads return `Vec<T>`, main thread creates/updates `VecModel`

**Detection:**
- Compiler error: `Rc<VecModel<...>> cannot be sent between threads safely`
- Design reviews show model shared between threads

**Phase to address:** Phase 1-2 (Foundation/Log Scanning) - Affects all background operations

**Sources:**
- [Updating UI from threads with ModelRc](https://github.com/slint-ui/slint/discussions/5300)
- [VecModel.push threading issues](https://github.com/slint-ui/slint/issues/3849)

---

### Pitfall 4: Widget Style Compile-Time Lock-In

**What goes wrong:** Widget style (fluent, cupertino, material, qt) is set at compile time and cannot be changed at runtime. Planning for runtime style switching fails.

**Why it happens:** Slint compiles the widget style into the binary. The visual appearance is determined by `SLINT_STYLE` environment variable or cargo feature at build time.

**Consequences:**
- Cannot offer user-selectable themes (material vs fluent)
- Multiple binaries needed for different styles
- Significant rework if requirements change

**Prevention:**
1. Decide on a single style early (recommend `fluent` for Windows)
2. Use `Palette` for runtime color scheme changes (light/dark) - available since Slint 1.6
3. Do not plan features requiring runtime style switching
4. Custom styling via Palette for brand consistency

**Detection:**
- Feature requests for runtime theme switching
- Attempting to set `SLINT_STYLE` at runtime

**Phase to address:** Phase 1 (Foundation) - Style decision must be made upfront

**Sources:**
- [Widget Styles documentation](https://docs.slint.dev/latest/docs/slint/reference/std-widgets/style/)
- [Runtime theme switching discussion](https://github.com/slint-ui/slint/discussions/5213)

---

### Pitfall 5: No Built-In Markdown/Rich Text Support

**What goes wrong:** Planning to use Slint's text components for markdown rendering fails because the feature doesn't exist yet.

**Why it happens:** Slint's `Text` and `TextEdit` elements support plain text only. Rich text/markdown support is actively being developed but not yet released.

**Consequences:**
- Must implement custom markdown rendering
- Significant additional development effort
- May need to embed a separate rendering engine

**Prevention:**
1. Plan for custom markdown-to-Slint conversion
2. Consider using a Rust markdown parser (pulldown-cmark) to generate styled elements
3. Build a custom `MarkdownViewer` component that renders markdown as a layout of Text elements
4. Track [Issue #6684](https://github.com/slint-ui/slint/issues/6684) for official support
5. Alternative: Use a WebView component for markdown (adds complexity)

**Detection:**
- Searching for `markdown` or `rich-text` in Slint API yields no results
- Feature request shows "in progress" not "released"

**Phase to address:** Phase 3 (Results Viewer) - Core requirement for crash log display

**Sources:**
- [Markdown syntax support issue](https://github.com/slint-ui/slint/issues/6684)
- [Rich text rendering issue](https://github.com/slint-ui/slint/issues/9560)

---

## Moderate Pitfalls

Mistakes that cause delays, technical debt, or reduced quality.

### Pitfall 6: ListView Not Updating After Model Changes

**What goes wrong:** Calling `VecModel.push()` or `set_vec()` from `invoke_from_event_loop` doesn't visually update the ListView until user interaction.

**Why it happens:** Model change notifications from background thread callbacks may not properly trigger UI invalidation and redraw.

**Consequences:**
- UI appears frozen/stale
- Users must interact (mouse move) to see updates
- Poor user experience during long operations

**Prevention:**
1. After model updates, explicitly call `window.request_redraw()` if available
2. Ensure model notifications complete before callback returns
3. Test model updates from background operations early
4. Use property bindings that trigger on model changes

**Detection:**
- ListView shows stale data until mouse moved over window
- Progress indicators don't update smoothly

**Phase to address:** Phase 2 (Log Scanning) - First phase with background operations

**Sources:**
- [VecModel.push not updating ListView](https://github.com/slint-ui/slint/issues/3849)
- [ListView not redrawn on model change](https://github.com/slint-ui/slint/issues/4538)

---

### Pitfall 7: No Native File Dialog in Slint

**What goes wrong:** Expecting Slint to provide file/folder selection dialogs, then discovering it doesn't.

**Why it happens:** Slint focuses on custom UI rendering, not native platform dialogs. File dialogs require external crates.

**Consequences:**
- Additional dependency on `native-dialog` or `rfd` crate
- Integration work required
- Potential issues on Windows with certain paths

**Prevention:**
1. Add `rfd` (Rust File Dialog) or `native-dialog` as dependency early
2. Test file dialog integration on Windows specifically
3. Known issue: Some integrations have problems with `C:\Users\[User]\Downloads` path
4. Call file dialogs from callbacks, handle results via `spawn_local`

**Detection:**
- Searching Slint docs for "file dialog" yields no built-in solution
- Planning file selection without external crate

**Phase to address:** Phase 1 (Foundation) - File/folder selection is table stakes

**Sources:**
- [File dialog discussion](https://github.com/slint-ui/slint/discussions/3015)
- [Windows Downloads folder issue](https://github.com/slint-ui/slint/issues/4773)

---

### Pitfall 8: upgrade_in_event_loop Not Always Processed

**What goes wrong:** Callbacks queued via `upgrade_in_event_loop()` occasionally don't execute until another event wakes the loop.

**Why it happens:** Platform-specific event loop wake mechanisms can be unreliable, particularly on Android but potentially affecting other platforms.

**Consequences:**
- UI updates delayed or lost
- Progress indicators stuck
- Intermittent, hard-to-reproduce bugs

**Prevention:**
1. Don't rely solely on `upgrade_in_event_loop` for time-critical updates
2. Use timers as backup to ensure periodic UI refresh
3. Batch updates to reduce callback frequency
4. Test progress updates under heavy load

**Detection:**
- Progress bar occasionally freezes mid-operation
- UI updates only when moving mouse
- Intermittent reports of stuck overlays

**Phase to address:** Phase 2 (Log Scanning) - Progress feedback system design

**Sources:**
- [upgrade_in_event_loop not always processed](https://github.com/slint-ui/slint/issues/5699)

---

### Pitfall 9: GPU Driver Crashes on Some Windows Systems

**What goes wrong:** Application crashes with `ACCESS DENIED (0xC0000005)` on certain Windows machines, particularly with AMD drivers.

**Why it happens:** GPU driver compatibility issues with OpenGL/Vulkan rendering. The `atio6axx.dll` (AMD OpenGL library) has known issues.

**Consequences:**
- Application unusable for subset of users
- Support burden
- Potential need for software renderer fallback

**Prevention:**
1. Compile with both GPU and software renderer support
2. Implement renderer fallback detection
3. Provide `SLINT_BACKEND` override instructions for users
4. Test on multiple GPU vendors (Intel, AMD, NVIDIA)
5. Consider defaulting to `femtovg` (OpenGL) over Skia on Windows

**Detection:**
- Crash reports mentioning `atio6axx.dll` or GPU drivers
- Application fails to start on some machines
- Users report "works after setting SLINT_BACKEND=winit-software"

**Phase to address:** Phase 4 (Distribution) - Windows packaging and compatibility

**Sources:**
- [Windows crashes discussion](https://github.com/slint-ui/slint/discussions/6436)
- [Backends and Renderers documentation](https://docs.slint.dev/latest/docs/slint/guide/backends-and-renderers/backends_and_renderers/)

---

### Pitfall 10: Windows System Scaling Issues

**What goes wrong:** Windows with non-100% display scaling cause immediate resize to "unscaled" equivalent when attempting to resize.

**Why it happens:** DPI awareness handling issue in Slint 1.12+ on Windows.

**Consequences:**
- Window sizes incorrect on high-DPI displays
- Poor appearance on modern laptops (often 125-150% scaling)
- User complaints about sizing

**Prevention:**
1. Test on Windows with 125%, 150%, 200% scaling
2. Monitor Slint releases for DPI fixes
3. Consider setting explicit DPI handling if available
4. Document known issues for users

**Detection:**
- Window jumps to different size when resized
- UI elements appear wrong size on high-DPI displays

**Phase to address:** Phase 4 (Distribution) - Windows compatibility testing

**Sources:**
- [System scaling broken on Windows](https://github.com/slint-ui/slint/issues/8765)

---

### Pitfall 11: Changed Callback Loop Detection Limits

**What goes wrong:** Property changed callbacks that trigger each other create infinite loops, hitting the 10-change limit.

**Why it happens:** Slint's `changed` callback feature (experimental) queues callbacks. If callback A changes property B which triggers callback B which changes property A, a loop forms.

**Consequences:**
- Unexpected behavior when loop limit hit
- Partial updates
- Hard to debug reactive logic

**Prevention:**
1. Design property dependencies as DAG (no cycles)
2. Use flags to prevent re-entry
3. Avoid `changed` callbacks for bi-directional sync
4. Prefer two-way bindings (`<=>`) for paired properties

**Detection:**
- Property updates stop after exactly 10 changes
- Callbacks seem to stop firing mid-chain

**Phase to address:** Phase 2-3 (Scanning/Viewer) - Complex UI state management

**Sources:**
- [Property Changed Callback blog](https://slint.dev/blog/property-changed-callback)

---

### Pitfall 12: Event Loop Cannot Run Twice

**What goes wrong:** After closing window and trying to show a new one, the event loop refuses to start or fails with `NoPlatform`.

**Why it happens:** Winit's exit status is set to `Some(0)` when event loop exits, and subsequent calls to `pump_events` return `PumpStatus::Exit` immediately.

**Consequences:**
- Cannot implement "restart" functionality
- Cannot show new windows after main window closes
- Application must fully exit to restart

**Prevention:**
1. Design for single event loop lifetime
2. Hide windows instead of closing if re-show needed
3. Use `Window::hide()` / `Window::show()` instead of dropping and recreating
4. If restart needed, use process restart

**Detection:**
- Second window creation fails after first closes
- `NoPlatform` errors on component creation
- Event loop silently exits immediately

**Phase to address:** Phase 1 (Foundation) - Window lifecycle architecture

**Sources:**
- [Event loop second run issue](https://github.com/slint-ui/slint/issues/4468)
- [run_event_loop documentation](https://docs.rs/slint/latest/slint/fn.run_event_loop.html)

---

## Minor Pitfalls

Mistakes that cause annoyance but are easily fixed.

### Pitfall 13: Skia Compilation with Spaces in CARGO_HOME

**What goes wrong:** Skia renderer fails to compile on Windows if `CARGO_HOME` path contains spaces.

**Why it happens:** Skia build scripts don't handle paths with spaces correctly.

**Prevention:**
1. Set `CARGO_HOME` to path without spaces (e.g., `C:\cargo_home`)
2. Avoid Skia renderer if path change not feasible
3. Use FemtoVG renderer instead

**Detection:**
- Build errors mentioning Skia and path issues
- Compilation fails only with `renderer-skia` feature

**Phase to address:** Phase 1 (Foundation) - Build setup

**Sources:**
- [Backends and Renderers documentation](https://docs.slint.dev/latest/docs/slint/guide/backends-and-renderers/backends_and_renderers/)

---

### Pitfall 14: Missing Visual C++ Redistributable on End-User Machines

**What goes wrong:** Application fails to start on some Windows machines without developer tools.

**Why it happens:** Slint (via winit/Skia) links against MSVC runtime libraries not present on all systems.

**Prevention:**
1. Bundle VC++ Redistributable with installer
2. Use static linking where possible
3. Document runtime requirements
4. Test on clean Windows VM

**Detection:**
- "Missing VCRUNTIME140.dll" or similar errors
- Application fails on non-developer machines

**Phase to address:** Phase 4 (Distribution) - Installer creation

**Sources:**
- [Backends and Renderers documentation](https://docs.slint.dev/latest/docs/slint/guide/backends-and-renderers/backends_and_renderers/)

---

### Pitfall 15: Image/Font Resource Caching Not Releasable

**What goes wrong:** Loaded images and fonts remain in memory cache and cannot be manually freed.

**Why it happens:** Slint caches resources for performance but provides no API to release them.

**Consequences:**
- Memory usage grows if loading many images
- Cannot fully "reset" application state

**Prevention:**
1. Be selective about image loading
2. Reuse image resources where possible
3. Monitor memory usage during development
4. Consider image size limits

**Detection:**
- Memory grows when viewing many different images
- Memory doesn't decrease after closing views

**Phase to address:** Phase 3 (Results Viewer) - Image handling (if displaying images)

**Sources:**
- [Image resource release issue](https://github.com/slint-ui/slint/issues/3029)
- [Memory usage discussion](https://github.com/slint-ui/slint/discussions/5854)

---

### Pitfall 16: Weak Reference Upgrade Fails on Wrong Thread

**What goes wrong:** Calling `weak.upgrade()` returns `None` even though component exists.

**Why it happens:** Weak references can only be upgraded on the thread where the component was created.

**Prevention:**
1. Always use `upgrade_in_event_loop()` from worker threads
2. Only use `upgrade()` on the main UI thread
3. Document thread expectations in code comments

**Detection:**
- `upgrade()` returning `None` unexpectedly
- Code works in tests but fails in production threading

**Phase to address:** Phase 2 (Log Scanning) - First background operations

**Sources:**
- [Weak struct documentation](https://docs.slint.dev/latest/docs/rust/slint/struct.Weak.html)

---

## Phase-Specific Warnings

| Phase | Topic | Likely Pitfall | Mitigation |
|-------|-------|---------------|------------|
| 1 | Async setup | Tokio incompatibility (#1) | Use spawn_local + async_compat |
| 1 | Callback patterns | Reference cycles (#2) | Weak references from start |
| 1 | Build configuration | Style lock-in (#4) | Decide style, configure Cargo |
| 2 | Background scanning | Model threading (#3, #6) | Channels + main thread updates |
| 2 | Progress feedback | Event loop reliability (#8) | Timer-based refresh backup |
| 3 | Markdown display | No built-in support (#5) | Custom markdown component |
| 3 | Results display | Memory caching (#15) | Resource management strategy |
| 4 | Windows distribution | GPU crashes (#9), scaling (#10) | Multi-renderer, testing matrix |
| 4 | Installer | VC++ runtime (#14) | Bundle redistributable |

## CLASSIC-Specific Considerations

Given CLASSIC's existing architecture:

1. **Existing Tokio Runtime:** CLASSIC already has a global Tokio runtime via `classic_shared::get_runtime()`. The Slint GUI must NOT create a conflicting current-thread runtime. Use `spawn_local` for UI-thread async, and the existing runtime for worker threads.

2. **Progress Feedback Pattern:** Current PySide6 uses signals for progress. Slint equivalent is `invoke_from_event_loop()` with property updates. Plan for timer-based fallback.

3. **File Dialogs:** Current file dialogs use Qt's native dialogs. Must add `rfd` or `native-dialog` crate and test Windows integration thoroughly.

4. **Markdown Results:** Current results viewer likely uses Qt's rich text. Must build custom markdown renderer or track Slint's rich text progress.

5. **Dark Mode:** PySide6 likely follows system theme. Slint can do this automatically with `fluent` style + `Palette` for runtime light/dark switching.

## Sources Summary

### Official Documentation (HIGH confidence)
- [Slint Backends & Renderers](https://docs.slint.dev/latest/docs/slint/guide/backends-and-renderers/backends_and_renderers/)
- [Slint Cargo Features](https://docs.slint.dev/latest/docs/rust/slint/docs/cargo_features/)
- [Weak struct](https://docs.slint.dev/latest/docs/rust/slint/struct.Weak.html)
- [spawn_local](https://docs.slint.dev/latest/docs/rust/slint/fn.spawn_local)
- [Widget Styles](https://docs.slint.dev/latest/docs/slint/reference/std-widgets/style/)

### GitHub Issues/Discussions (MEDIUM-HIGH confidence)
- [Tokio integration](https://github.com/slint-ui/slint/discussions/5784)
- [Async patterns](https://github.com/slint-ui/slint/discussions/4377)
- [Model threading](https://github.com/slint-ui/slint/discussions/5300)
- [ListView updates](https://github.com/slint-ui/slint/issues/3849)
- [Event loop reliability](https://github.com/slint-ui/slint/issues/5699)
- [File dialogs](https://github.com/slint-ui/slint/discussions/3015)
- [Markdown support](https://github.com/slint-ui/slint/issues/6684)
- [Windows crashes](https://github.com/slint-ui/slint/discussions/6436)
- [Scaling issues](https://github.com/slint-ui/slint/issues/8765)
