# Phase 26: Async Bridge Audit - Research

**Researched:** 2026-02-05
**Domain:** Rust async bridge (Tokio + Slint event loop coordination)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Dead Code & API Surface
- Remove `run_with_ui_update_blocking` method and the `BRIDGE_POOL` static rayon thread pool entirely -- no callers exist
- Remove the `Bridge` type alias (`pub use AsyncBridge as Bridge`) -- one canonical name only
- Audit and remove `rayon` and `num_cpus` dependencies from the crate if nothing else uses them
- Migrate `once_cell::sync::Lazy` to `std::sync::LazyLock` (stabilized Rust 1.80) if once_cell has no other users in the crate

#### Error Handling & Resilience
- Add an optional timeout variant (`run_with_timeout` or similar) that wraps operations in `tokio::time::timeout`
- Add a `run_cancellable` method that accepts a `CancellationToken` and returns a handle -- makes cancellation a first-class bridge concept instead of caller-threaded
- Panic handling and `.expect()` policy: Claude's discretion on whether to keep panics, log+drop, or return Result

#### Testing Strategy
- Extract an `EventLoopDispatcher` trait to abstract UI-thread dispatch -- tests use a mock dispatcher, production uses Slint's `invoke_from_event_loop`
- Test both the bridge module itself AND the 6 GUI call sites in main.rs
- Functional tests only -- no stress testing (CLASSIC's scan workload is modest)
- Test scope for bridge: timeout behavior, cancellation integration, mock dispatch verification
- Testing depth: Claude's discretion on what's practically testable given Slint's constraints

#### Findings Disposition
- All improvements implemented in Phase 26 -- no documentation-only findings
- Breaking API changes require full migration of all existing call sites in the same phase -- no mixed old/new API
- Audit scope includes `get_runtime()` and Tokio runtime configuration, not just async_bridge

### Claude's Discretion
- Whether to remove or keep `run_with_loading` (currently unused, has subtle design issue with dual spawns)
- Panic handling strategy for `.expect()` calls (keep, log+drop, or Result)
- Panic catching in spawned async tasks (catch_unwind or let panics be bugs)
- Practical test coverage level given Slint's testing limitations

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

## Summary

This phase audits and improves the `async_bridge` module in `classic-shared-core` (at `rust/foundation/classic-shared-core/src/async_bridge.rs`) and the `get_runtime()` Tokio runtime setup (in `lib.rs`). The current async_bridge module is 357 lines with 4 public methods, a dead static thread pool, a dead type alias, and minimal test coverage (single compile-check test). The module coordinates between Slint's UI event loop and the shared Tokio runtime.

The codebase has 7 AsyncBridge call sites in `classic-gui/src/main.rs`: 6 `run_with_ui_update` calls (1 scan operation + 5 browse folder dialogs) and 1 `spawn_background` call (auto-clear status timer). Cancellation is currently threaded manually through `run_with_ui_update` by the scan operation -- the `CancellationToken` is created in the callback, stored in `AppState`, and passed into the async operation. The new `run_cancellable` method should simplify this.

Key migration work: (1) remove dead code (`run_with_ui_update_blocking`, `BRIDGE_POOL`, `Bridge` alias, `run_with_loading`), (2) migrate `once_cell::Lazy` to `std::sync::LazyLock` across 3 files, (3) remove `num_cpus` dependency from the crate, (4) add `run_with_timeout` and `run_cancellable` methods, (5) extract `EventLoopDispatcher` trait for testability, (6) update all 7 GUI call sites, and (7) write comprehensive tests.

**Primary recommendation:** Approach this as a 3-wave effort: dead code removal and dependency cleanup first, new API methods second, trait extraction and testing third.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| tokio | 1.49.0 | Async runtime (ONE RUNTIME RULE) | Already in workspace, `timeout` and `spawn` used by bridge |
| tokio-util | 0.7 | `CancellationToken` for cooperative cancellation | Already used by classic-gui, needs to be added to classic-shared-core |
| slint | 1.15.0 | `invoke_from_event_loop` for UI-thread dispatch | Already a conditional dep via `gui-bridge` feature |
| std::sync::LazyLock | (stdlib) | Replaces `once_cell::sync::Lazy` for static initialization | Stabilized Rust 1.80, project uses rust-version 1.85.0 |

### Dependencies to Remove from classic-shared-core
| Library | Current Use | Why Remove |
|---------|-------------|------------|
| `num_cpus` | Only used in `BRIDGE_POOL` (being deleted) | No other users in this crate |
| `once_cell` | `Lazy` in 3 files | All migrated to `std::sync::LazyLock` |

### Dependencies to Keep (cannot remove)
| Library | Why Keep |
|---------|----------|
| `rayon` | Used by `strings_core.rs` (`rayon::prelude::*`) and `path_core.rs` (`rayon::prelude::*`) for parallel iteration |

### Dependencies to Add to classic-shared-core
| Library | Version | Purpose | Conditional |
|---------|---------|---------|-------------|
| `tokio-util` | workspace (0.7) | `CancellationToken` type in `run_cancellable` signature | Behind `gui-bridge` feature |

**Key finding:** The workspace `Cargo.toml` already has `tokio-util = "0.7"` as a workspace dependency. It just needs to be added to classic-shared-core's `Cargo.toml` with the `gui-bridge` feature gate.

## Architecture Patterns

### Current Module Structure
```
rust/foundation/classic-shared-core/src/
  async_bridge.rs    # AsyncBridge struct (behind gui-bridge feature)
  lib.rs             # get_runtime(), RUNTIME static, RuntimeConfig
  errors.rs          # ClassicError types
  path_core.rs       # Path utilities (uses rayon)
  strings_core.rs    # String processing (uses rayon)
  performance_core.rs # Metrics (uses once_cell::Lazy)
```

### Pattern 1: EventLoopDispatcher Trait Extraction
**What:** Abstract `slint::invoke_from_event_loop` behind a trait so tests can mock UI dispatch.
**When to use:** All AsyncBridge methods that dispatch to the UI thread.
**Precedent:** `ScanWindowProperties` trait in `classic-gui/src/worker.rs` (lines 76-83) follows the same pattern -- abstract Slint-generated code behind a trait.

```rust
// Source: Codebase pattern from ScanWindowProperties (worker.rs)
/// Trait for dispatching closures to the UI event loop
pub trait EventLoopDispatcher: Send + Sync + 'static {
    /// Dispatch a closure to run on the UI thread
    fn dispatch(&self, f: Box<dyn FnOnce() + Send + 'static>) -> Result<(), BridgeError>;
}

/// Production dispatcher using Slint's invoke_from_event_loop
pub struct SlintDispatcher;

impl EventLoopDispatcher for SlintDispatcher {
    fn dispatch(&self, f: Box<dyn FnOnce() + Send + 'static>) -> Result<(), BridgeError> {
        slint::invoke_from_event_loop(f)
            .map_err(|e| BridgeError::DispatchFailed(e.to_string()))
    }
}
```

**Design decision:** The `AsyncBridge` struct should become generic over `D: EventLoopDispatcher`, or the dispatcher should be stored as a static that can be swapped for testing. Given that `AsyncBridge` uses static methods (no instance), the recommendation is a **module-level static dispatcher** that defaults to `SlintDispatcher` but can be replaced in tests.

### Pattern 2: run_with_timeout Method
**What:** Wraps an async operation with `tokio::time::timeout`.
**API:**
```rust
// Source: tokio docs (https://docs.rs/tokio/latest/tokio/time/fn.timeout.html)
pub fn run_with_timeout<F, R, C>(
    duration: Duration,
    operation: F,
    on_complete: C,
) where
    F: Future<Output = R> + Send + 'static,
    R: Send + 'static,
    C: FnOnce(Result<R, BridgeError>) + Send + 'static,
{
    get_runtime().spawn(async move {
        let result = tokio::time::timeout(duration, operation).await;
        let mapped = result.map_err(|_| BridgeError::Timeout(duration));
        // dispatch to UI thread...
    });
}
```

**Important:** The Tokio runtime MUST have `enable_time` set (it does -- `RuntimeConfig::default()` has `enable_time: true`). Without it, `tokio::time::timeout` panics.

### Pattern 3: run_cancellable Method
**What:** Runs an async operation with first-class cancellation support, returning a handle.
**API leveraging CancellationToken.run_until_cancelled():**
```rust
// Source: tokio-util docs (https://docs.rs/tokio-util/latest/tokio_util/sync/struct.CancellationToken.html)
pub fn run_cancellable<F, R, C>(
    cancel_token: CancellationToken,
    operation: F,
    on_complete: C,
) where
    F: Future<Output = R> + Send + 'static,
    R: Send + 'static,
    C: FnOnce(Option<R>) + Send + 'static,  // None = cancelled
{
    get_runtime().spawn(async move {
        let result = cancel_token.run_until_cancelled(operation).await;
        // dispatch to UI thread with Option<R>...
    });
}
```

**Current scan pattern to simplify:**
The scan currently creates a `CancellationToken`, stores it in `AppState`, passes it into the async operation via `run_with_ui_update`, and the operation checks `cancel_token.is_cancelled()` in a loop. With `run_cancellable`, the bridge handles the cancellation race, and the operation can focus on its work.

### Pattern 4: BridgeError Type
**What:** Dedicated error type for bridge operations.
```rust
#[derive(Debug, thiserror::Error)]
pub enum BridgeError {
    #[error("Operation timed out after {0:?}")]
    Timeout(Duration),
    #[error("Operation was cancelled")]
    Cancelled,
    #[error("Failed to dispatch to UI thread: {0}")]
    DispatchFailed(String),
}
```

### Anti-Patterns to Avoid
- **Nested runtime creation:** Never call `Runtime::new()` inside the bridge -- always use `get_runtime()`
- **Blocking the UI thread:** Never call `block_on()` from the Slint event loop thread
- **`unwrap()`/`expect()` on dispatch:** The `.expect("Failed to invoke...")` calls will panic if the Slint event loop has shut down. Use Result propagation or log+drop instead
- **Dual spawn in `run_with_loading`:** This method does `invoke_on_ui_thread` (sets loading=true) then `run_with_ui_update` (operation + callback). The first dispatch is a separate spawn that races with the operation spawn -- the loading flag might not be set before the operation completes on fast paths

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cancellation | Manual `is_cancelled()` polling loops | `CancellationToken::run_until_cancelled()` | tokio-util provides this out of the box; handles edge cases (cancel during poll) |
| Timeout | Manual `tokio::select!` with `sleep` | `tokio::time::timeout()` | One-liner wrapper, handles `Elapsed` error type correctly |
| Lazy statics | `once_cell::sync::Lazy` | `std::sync::LazyLock` | Standard library, zero dependencies, identical semantics |
| Thread counting | `num_cpus::get()` | `std::thread::available_parallelism()` | Standard library since Rust 1.59, already used in `RuntimeConfig` |

**Key insight:** The bridge's core value is the Slint-Tokio coordination pattern. Timeout and cancellation should wrap existing tokio/tokio-util primitives, not re-implement them.

## Common Pitfalls

### Pitfall 1: Slint Event Loop Not Running During Tests
**What goes wrong:** `slint::invoke_from_event_loop()` returns `Err(EventLoopError)` when no event loop is running, which currently causes a panic via `.expect()`.
**Why it happens:** Unit tests don't run a Slint event loop. The `EventLoopDispatcher` trait solves this, but only if the bridge actually uses it.
**How to avoid:** Ensure the bridge is parameterized by dispatcher and tests inject a mock that collects dispatched closures into a `Vec` or executes them immediately.
**Warning signs:** Tests that only work with `#[ignore]` or require a running GUI.

### Pitfall 2: LazyLock Migration Requires Exact Semantics Match
**What goes wrong:** `std::sync::LazyLock` has the same API as `once_cell::sync::Lazy` for the common case, but subtle differences exist.
**Why it happens:** Both use `LazyLock::new(|| ...)` / `Lazy::new(|| ...)`. The migration is mechanical.
**How to avoid:** Direct find-and-replace: `once_cell::sync::Lazy` -> `std::sync::LazyLock`, remove `once_cell` import. Verify with `cargo build`.
**Warning signs:** Compile errors about trait bounds (unlikely with this usage pattern).

### Pitfall 3: CancellationToken Must Be in tokio-util Feature Gate
**What goes wrong:** Adding `tokio-util` to classic-shared-core without feature-gating pulls it into all builds (including Python bindings).
**Why it happens:** classic-shared-core is used by many crates, most don't need CancellationToken.
**How to avoid:** Add `tokio-util` as an optional dependency gated behind the `gui-bridge` feature:
```toml
[dependencies]
tokio-util = { workspace = true, optional = true }

[features]
gui-bridge = ["slint", "tokio-util"]
```

### Pitfall 4: Removing once_cell While Other Crates Still Use It
**What goes wrong:** Removing `once_cell` from workspace deps would break other crates.
**Why it happens:** `once_cell` is a workspace dependency used by many crates.
**How to avoid:** Only remove `once_cell` from classic-shared-core's `Cargo.toml`. Leave the workspace-level dependency untouched. Other crates can migrate independently later.

### Pitfall 5: run_cancellable Interaction with Scan Architecture
**What goes wrong:** The scan currently passes `CancellationToken` INTO the async operation (for per-log cancellation checks). `run_cancellable` wraps the ENTIRE future. These are different cancellation granularities.
**Why it happens:** `CancellationToken::run_until_cancelled()` only checks cancellation between polls. If the scan's inner loop doesn't yield between logs, cancellation may be delayed.
**How to avoid:** The scan operation already yields (it calls `.await` for each log). `run_until_cancelled` will work at the inter-log boundary. The per-log `is_cancelled()` check can remain as a belt-and-suspenders approach, or the scan can rely entirely on `run_cancellable`'s cancellation.
**Recommendation:** Keep the per-log `is_cancelled()` check for immediate responsiveness, but let `run_cancellable` handle the bridge-level cancellation and result type.

### Pitfall 6: Breaking API Changes Require Full Migration
**What goes wrong:** Changing `run_with_ui_update` signature or behavior without updating all 7 call sites causes compile errors.
**Why it happens:** Decision: "Breaking API changes require full migration of all existing call sites in the same phase."
**How to avoid:** Plan the API changes first, then update all call sites in a single task. The call sites are all in `main.rs` which makes this manageable.

## Code Examples

### Current AsyncBridge Usage (from main.rs)
```rust
// Source: classic-gui/src/main.rs:333-405
// Scan with manual cancellation threading
let cancel_token = CancellationToken::new();
state.lock().cancel_token = Some(cancel_token.clone());

AsyncBridge::run_with_ui_update(
    scan_crash_logs(window_weak.clone(), cancel_token, crash_log_path),
    move |result| {
        // Handle result on UI thread
    },
);
```

### Proposed run_cancellable Pattern
```rust
// Simplified scan with first-class cancellation
let cancel_token = CancellationToken::new();
state.lock().cancel_token = Some(cancel_token.clone());

AsyncBridge::run_cancellable(
    cancel_token,
    scan_crash_logs(window_weak.clone(), crash_log_path),
    move |result| {
        match result {
            Some(Ok(scan_result)) => { /* success */ },
            Some(Err(msg)) => { /* error */ },
            None => { /* cancelled */ },
        }
    },
);
```

### LazyLock Migration Example
```rust
// Before (lib.rs):
use once_cell::sync::Lazy;
pub(crate) static RUNTIME: Lazy<Runtime> = Lazy::new(|| { ... });

// After:
use std::sync::LazyLock;
pub(crate) static RUNTIME: LazyLock<Runtime> = LazyLock::new(|| { ... });
```

### EventLoopDispatcher Test Mock
```rust
// Test mock that captures dispatched closures
use std::sync::{Arc, Mutex};

struct MockDispatcher {
    dispatched: Arc<Mutex<Vec<Box<dyn FnOnce() + Send>>>>,
}

impl EventLoopDispatcher for MockDispatcher {
    fn dispatch(&self, f: Box<dyn FnOnce() + Send + 'static>) -> Result<(), BridgeError> {
        self.dispatched.lock().unwrap().push(f);
        Ok(())
    }
}

// In tests:
let mock = MockDispatcher { dispatched: Arc::new(Mutex::new(Vec::new())) };
// Run bridge operation with mock...
// Assert dispatched closures were queued
let closures = mock.dispatched.lock().unwrap();
assert_eq!(closures.len(), 1);
// Execute the closure to verify behavior
closures.into_iter().for_each(|f| f());
```

### Timeout Usage
```rust
// Source: tokio docs (https://docs.rs/tokio/latest/tokio/time/fn.timeout.html)
use tokio::time::{timeout, Duration};

// Inside run_with_timeout implementation:
let result = timeout(duration, operation).await;
match result {
    Ok(value) => on_complete(Ok(value)),
    Err(_elapsed) => on_complete(Err(BridgeError::Timeout(duration))),
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `once_cell::sync::Lazy` | `std::sync::LazyLock` | Rust 1.80 (July 2024) | Drop `once_cell` dependency |
| `num_cpus::get()` | `std::thread::available_parallelism()` | Rust 1.59 (Feb 2022) | Drop `num_cpus` dependency |
| `rayon::ThreadPool` for bridging | `tokio::spawn` directly | Already done in `run_with_ui_update` | BRIDGE_POOL is dead code |
| Manual `select!` for cancellation | `CancellationToken::run_until_cancelled()` | tokio-util 0.7 | Cleaner cancellation API |

**Deprecated/outdated:**
- `BRIDGE_POOL` static: Dead code since `run_with_ui_update` was refactored to use `tokio::spawn` directly
- `run_with_ui_update_blocking`: Legacy method, zero callers in codebase
- `Bridge` type alias: Unnecessary indirection
- `run_with_loading`: Never used, has race condition between loading flag dispatch and operation spawn

## Discretion Recommendations

### Remove `run_with_loading` -- RECOMMEND REMOVAL
**Reasoning:** (1) Zero callers in the entire codebase, (2) the dual-spawn design has a race condition where the loading flag might not be set before a fast operation completes, (3) callers can trivially compose loading state management themselves using `invoke_on_ui_thread` + `run_with_ui_update`. Keeping unused code with known design issues is worse than removing it.

### Panic Handling Strategy -- RECOMMEND Result PROPAGATION
**Reasoning:** The 3 `.expect()` calls in async_bridge.rs are:
1. `BRIDGE_POOL` builder `.expect("Failed to create async bridge thread pool")` -- being deleted
2. `run_with_ui_update` line 200: `.expect("Failed to invoke callback on Slint event loop")`
3. `run_with_ui_update_blocking` line 222: same -- being deleted
4. `invoke_on_ui_thread` line 284: `.expect("Failed to invoke function on Slint event loop")`

The remaining expects (items 2, 4) will panic if the Slint event loop shuts down while async operations are in flight (e.g., user closes the window during a scan). This is a realistic scenario. **Recommendation:** Return `Result<(), BridgeError>` from dispatch and let callers decide. For `run_with_ui_update`, log a warning and drop the result silently (the window is closing anyway). For `invoke_on_ui_thread`, return `Result<(), BridgeError>` to callers.

### Panic Catching in Spawned Tasks -- RECOMMEND LET PANICS BE BUGS
**Reasoning:** `std::panic::catch_unwind` adds complexity and only catches `panic!` (not `abort`). Panics in async tasks already cause the JoinHandle to return an error. Since CLASSIC doesn't collect JoinHandles from bridge operations (fire-and-forget spawns), a panic would silently drop. The application is a desktop tool, not a server -- a panic in a spawned task is a bug to fix, not a condition to recover from. Wrapping everything in `catch_unwind` would obscure bugs.

### Practical Test Coverage -- RECOMMEND BRIDGE-FOCUSED TESTING
**Reasoning:** Testing Slint event loop interactions in unit tests is constrained by needing `slint::testing::init_no_event_loop()` or a running backend. The `EventLoopDispatcher` trait extraction specifically addresses this. Tests should cover:
1. **Bridge methods with mock dispatcher:** Verify closures are dispatched correctly
2. **Timeout behavior:** Use a mock dispatcher + `tokio::time::pause()` for deterministic timeout tests
3. **Cancellation integration:** Verify `run_cancellable` returns `None` when token is cancelled
4. **Error propagation:** Verify `BridgeError` types are correct
5. **Call site migration verification:** Compile-time verification (if it compiles, the types match)

GUI call site testing beyond "does it compile" is impractical without a full Slint event loop and would be integration/E2E testing, not unit testing.

## Audit Findings Summary

### Files to Modify
| File | Changes |
|------|---------|
| `async_bridge.rs` | Remove dead code, add new methods, extract trait, add tests |
| `lib.rs` | Migrate `Lazy` to `LazyLock`, remove `once_cell` import |
| `performance_core.rs` | Migrate `Lazy` to `LazyLock`, remove `once_cell` import |
| `Cargo.toml` (classic-shared-core) | Remove `num_cpus`, remove `once_cell`, add `tokio-util` (optional) |
| `main.rs` (classic-gui) | Update 7 call sites (especially scan to use `run_cancellable`) |
| `scan.rs` (classic-gui) | May simplify cancellation handling if `run_cancellable` handles it |

### Call Site Inventory (main.rs)
| Line | Method | Purpose | Migration Notes |
|------|--------|---------|-----------------|
| 333 | `run_with_ui_update` | Scan crash logs | Migrate to `run_cancellable` |
| 395 | `spawn_background` | Auto-clear status (5s delay) | No change needed |
| 563 | `run_with_ui_update` | Browse crash log folder | No change needed (simple browse) |
| 610 | `run_with_ui_update` | Browse game folder | No change needed |
| 890 | `run_with_ui_update` | Browse INI folder | No change needed |
| 940 | `run_with_ui_update` | Browse mods folder | No change needed |
| 990 | `run_with_ui_update` | Browse scan folder | No change needed |

### get_runtime() Audit
The `get_runtime()` function and `RuntimeConfig` in `lib.rs` are well-designed:
- Uses `available_parallelism()` for thread count (not `num_cpus`)
- Enables both IO and time drivers (required for timeout)
- `RuntimeConfig` is flexible but only default config is used
- The `io_optimized()`, `cpu_optimized()`, `minimal()` config variants are unused but not harmful -- they're public API for potential callers

**Recommendation:** Keep `RuntimeConfig` as-is. Only change is `Lazy` -> `LazyLock` migration.

## Open Questions

1. **Dispatcher static vs generic parameter**
   - What we know: AsyncBridge uses static methods, so a generic parameter would require changing all call sites to `AsyncBridge::<SlintDispatcher>::run_with_ui_update(...)`
   - What's unclear: Whether a module-level static dispatcher (set once at startup) or a generic type parameter is cleaner
   - Recommendation: Use a module-level static `OnceLock<Box<dyn EventLoopDispatcher>>` with a `set_dispatcher()` function called at startup. Tests call `set_dispatcher(MockDispatcher)`. This keeps call sites unchanged.

2. **Return type of run_cancellable -- `Option<R>` vs `Result<R, BridgeError>`**
   - What we know: `CancellationToken::run_until_cancelled()` returns `Option<T>` (None = cancelled)
   - What's unclear: Whether callers want `Option<R>` (where R itself may be Result) or a unified error type
   - Recommendation: Use `Option<R>` to match tokio-util's convention. The scan already uses `Result<ScanResult, String>` as R, so callers get `Option<Result<ScanResult, String>>`.

3. **Whether scan.rs needs modification**
   - What we know: `scan_crash_logs` currently takes a `CancellationToken` parameter and does per-log `is_cancelled()` checks
   - What's unclear: Whether to remove the token parameter from `scan_crash_logs` if `run_cancellable` handles cancellation at the bridge level
   - Recommendation: Keep the `CancellationToken` parameter in `scan_crash_logs` for per-log responsiveness, but the bridge's `run_cancellable` provides an additional safety net. The token should be created and stored in the callback, cloned to both the bridge and the scan function.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `async_bridge.rs`, `lib.rs`, `performance_core.rs`, `main.rs`, `scan.rs`, `worker.rs` -- direct file reads
- [std::sync::LazyLock documentation](https://doc.rust-lang.org/std/sync/struct.LazyLock.html) -- stabilized in Rust 1.80
- [Rust 1.80 release notes (LazyLock)](https://www.infoq.com/news/2024/08/rust-1-80-lazy-globals/) -- confirms stabilization
- [tokio::time::timeout](https://docs.rs/tokio/latest/tokio/time/fn.timeout.html) -- API verified
- [CancellationToken API](https://docs.rs/tokio-util/latest/tokio_util/sync/struct.CancellationToken.html) -- `run_until_cancelled()` method confirmed
- [slint::invoke_from_event_loop](https://docs.rs/slint/latest/slint/fn.invoke_from_event_loop.html) -- returns `Result<(), EventLoopError>`

### Secondary (MEDIUM confidence)
- [Slint testing backend](https://lib.rs/crates/i-slint-backend-testing) -- `init_no_event_loop()` for unit tests

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in workspace, versions verified from Cargo.toml
- Architecture: HIGH - Patterns derived from existing codebase (ScanWindowProperties precedent) and verified official docs
- Pitfalls: HIGH - Identified from direct code analysis of current implementation
- Discretion recommendations: MEDIUM - Based on engineering judgment, no external validation needed

**Research date:** 2026-02-05
**Valid until:** 2026-03-07 (30 days -- stable Rust ecosystem, no expected breaking changes)
