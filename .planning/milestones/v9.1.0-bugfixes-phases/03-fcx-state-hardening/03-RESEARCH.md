# Phase 3: FCX State Hardening - Research

**Date:** 2026-04-06
**Discovery level:** Level 1 — codebase-grounded verification only (no new external dependencies)

## Goal

Plan Phase 3 so FCX reset semantics become reliable under contention, C++ and Node scan entrypoints start from clean FCX state every time, and Node can inspect structured FCX issues without reshaping existing scan result payloads.

## Locked Decisions To Preserve

- **D-01:** Node must export `resetFcxGlobalState()` and `getFcxConfigIssues()`.
- **D-02:** `getFcxConfigIssues()` returns structured issue objects, not formatted report text.
- **D-03:** C++ and Node scan entrypoints auto-reset FCX state before every single-log and batch session.
- **D-04:** Explicit reset APIs stay public even with auto-reset.
- **D-05:** Core reset contract stays `Result<(), FcxResetError>`.
- **D-06:** Real reset failures abort scan start.
- **D-07:** The unnecessary/no-op reset outcome is non-fatal.
- **D-08:** Node issue inspection stays a standalone getter, not part of `JsAnalysisResult`.
- **D-09:** C++ remains reset-only in this phase.

## Relevant Source Facts

### Core

- `classic-scanlog-core/src/fcx_handler.rs` currently defines `GLOBAL_FCX_HANDLER` as `Lazy<Mutex<FcxModeHandler>>` and uses `try_lock()` inside `reset_global_state()`, silently dropping resets on contention.
- `FcxModeHandler` already has enough state to determine whether reset is necessary: `main_files_check`, `game_files_check`, `detected_issues`, and `checks_run`.
- `classic-scanlog-core/src/lib.rs` currently re-exports `ConfigIssue`, `FcxModeHandler`, and `GLOBAL_FCX_HANDLER`; Phase 3 should also re-export `FcxResetError` so bindings can pattern-match on the contract directly.

### C++ bridge

- `classic-cpp-bridge/src/scanner.rs` owns the public scan session entrypoints: `orchestrator_process_log`, `orchestrator_process_logs_batch`, and `orchestrator_process_logs_batch_with_progress`.
- The CXX extern block is the correct place to add an explicit `fcx_reset_global_state()` bridge API.
- The bridge already converts Rust errors into `Result<... , String>`-style failures, so it can treat `FcxResetError::Unnecessary` as success and real failures as scan-start errors.

### Node bindings

- `classic-node/src/scanlog.rs` owns the public scanlog exports. The NAPI `snake_case` Rust names automatically surface as camelCase JS/TS names.
- The public scan session entrypoints are `process_log`, `process_logs_batch`, `process_log_with_yaml_content`, and `process_logs_batch_with_yaml_content`.
- `classic-node/__test__/scanlog.spec.ts` already covers these four entrypoints and is the right place for same-process carryover checks.
- `classic-node/package.json` and repo guidance require refreshing `index.d.ts` plus parity/runtime coverage artifacts when Node public APIs change.

### Python reference pattern

- `classic-scanlog-py/src/fcx_handler.rs` already demonstrates the intended FCX singleton usage pattern: read/update `GLOBAL_FCX_HANDLER`, expose structured `ConfigIssue` wrappers, and keep reset as a standalone entrypoint.
- Node should copy the binding shape, not invent a different state model.

## Recommended Implementation Shape

### 1. Core reset contract first

Implement the semantic contract in `classic-scanlog-core` before touching bindings:

- Add `FcxResetError` with an `Unnecessary` variant and at least one real-failure variant reserved for binding-visible failure mapping.
- Change `FcxModeHandler::reset_global_state()` to `Result<(), FcxResetError>`.
- Replace `try_lock()` with blocking `lock()` so resets wait rather than disappearing.
- Treat an already-clean handler as `Err(FcxResetError::Unnecessary)` so bindings can explicitly preserve D-07.
- Add a contention test that holds the mutex on one thread while another thread calls `reset_global_state()`, then confirms the reset eventually succeeds and clears stale state.

### 2. C++ bridge after core

- Add bridge helper `fcx_reset_global_state()` to `scanner.rs` and expose it through the `extern "Rust"` block.
- Call the same helper at the start of all public scan entrypoints named above.
- Map `Unnecessary` to the normal path; map true failures to returned bridge errors before any scan work starts.
- Keep C++ reset-only; do not add FCX issue DTOs or getters.

### 3. Node binding surface after core

- Add `#[napi(object)]` DTO for FCX issues using the existing `ConfigIssue` fields (`filePath`, `section`, `setting`, `currentValue`, `recommendedValue`, `description`, `severity`).
- Add free exports `reset_fcx_global_state()` and `get_fcx_config_issues()` so JS sees `resetFcxGlobalState()` and `getFcxConfigIssues()` per D-01.
- Keep FCX issues out of `JsAnalysisResult` per D-08.
- Auto-reset at the start of all four scan entrypoints. If Node needs to populate the singleton for issue inspection, do so via a narrow helper modeled on Python's FCX check path and existing Rust/scangame helpers instead of inventing Node-local business logic.
- Add a same-process Node test that proves stale FCX issues do not leak from one scan call into the next.

## Risks / Pitfalls

- **Silent no-op regression:** any leftover `try_lock()` path would reintroduce SAFE-01.
- **Binding drift:** Node API changes require `index.d.ts` and parity/runtime coverage artifact refreshes in the same change.
- **Scope creep:** C++ issue inspection and scan-result payload changes are explicitly out of scope.
- **False-positive failure mapping:** `Unnecessary` must stay non-fatal in C++ and Node even though the core contract uses `Result`.

## Validation Architecture

- **Core quick loop:** `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml -- fcx_reset`
- **Bridge quick loop:** `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml scanner`
- **Node quick loop:** `bun test __test__/scanlog.spec.ts`
- **Phase full loop:**
  - `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml`
  - `cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings`
  - `bun run parity:gate:local`
  - `bun run test:bun`
  - `bun run test:node`

## Planning Consequences

- Split Phase 3 into one core plan followed by parallel binding plans.
- Make the core plan first-wave because both binding surfaces depend on the new reset contract.
- Keep Node parity/docs refresh in the Node plan so public contract work stays with the API change.
