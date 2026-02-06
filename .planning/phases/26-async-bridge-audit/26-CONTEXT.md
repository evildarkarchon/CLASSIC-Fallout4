# Phase 26: Async Bridge Audit - Context

**Gathered:** 2026-02-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Audit and improve the `async_bridge` module in `classic-shared-core` and the `get_runtime()` Tokio setup. Remove dead code, add resilience features (timeout, cancellation), introduce testability through trait abstraction, and update all GUI call sites. All findings are implemented in-phase -- no deferred recommendations.

</domain>

<decisions>
## Implementation Decisions

### Dead Code & API Surface
- Remove `run_with_ui_update_blocking` method and the `BRIDGE_POOL` static rayon thread pool entirely -- no callers exist
- Remove the `Bridge` type alias (`pub use AsyncBridge as Bridge`) -- one canonical name only
- Audit and remove `rayon` and `num_cpus` dependencies from the crate if nothing else uses them
- Migrate `once_cell::sync::Lazy` to `std::sync::LazyLock` (stabilized Rust 1.80) if once_cell has no other users in the crate

### Error Handling & Resilience
- Add an optional timeout variant (`run_with_timeout` or similar) that wraps operations in `tokio::time::timeout`
- Add a `run_cancellable` method that accepts a `CancellationToken` and returns a handle -- makes cancellation a first-class bridge concept instead of caller-threaded
- Panic handling and `.expect()` policy: Claude's discretion on whether to keep panics, log+drop, or return Result

### Testing Strategy
- Extract an `EventLoopDispatcher` trait to abstract UI-thread dispatch -- tests use a mock dispatcher, production uses Slint's `invoke_from_event_loop`
- Test both the bridge module itself AND the 6 GUI call sites in main.rs
- Functional tests only -- no stress testing (CLASSIC's scan workload is modest)
- Test scope for bridge: timeout behavior, cancellation integration, mock dispatch verification
- Testing depth: Claude's discretion on what's practically testable given Slint's constraints

### Findings Disposition
- All improvements implemented in Phase 26 -- no documentation-only findings
- Breaking API changes require full migration of all existing call sites in the same phase -- no mixed old/new API
- Audit scope includes `get_runtime()` and Tokio runtime configuration, not just async_bridge

### Claude's Discretion
- Whether to remove or keep `run_with_loading` (currently unused, has subtle design issue with dual spawns)
- Panic handling strategy for `.expect()` calls (keep, log+drop, or Result)
- Panic catching in spawned async tasks (catch_unwind or let panics be bugs)
- Practical test coverage level given Slint's testing limitations

</decisions>

<specifics>
## Specific Ideas

- The scan code currently threads `CancellationToken` manually through `run_with_ui_update` -- the new `run_cancellable` should simplify this pattern
- `ScanWindowProperties` trait pattern from Phase 19 is a good precedent for the `EventLoopDispatcher` trait abstraction
- The `BRIDGE_POOL` uses `(num_cpus::get() / 2).clamp(2, 8)` which pulls in two crates for code that's being deleted

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 26-async-bridge-audit*
*Context gathered: 2026-02-05*
