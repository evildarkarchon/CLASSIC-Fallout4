# Error Contract Conventions

Documents the per-binding error shape conventions for Rust error types as they cross FFI boundaries. These conventions are intentional design choices, not inconsistencies to fix.

Reference: [`AGENTS.md`](../../AGENTS.md).

Need an old-to-new path translation first? Use the shared [`workspace migration matrix`](../workspace-migration-matrix.md).

---

## Scope

Each binding surface adapts Rust `Result<T, E>` errors into the idiom expected by its consumers. This document covers the three active surfaces:

- C++ (CXX bridge) -- `rust::Error` exceptions and empty-string sentinels
- Node (NAPI-RS) -- `napi::Error` with structured `code` fields
- Python (PyO3) -- typed Python exception classes

---

## C++ (CXX Bridge)

**Pattern:** `rust::Error` exceptions for hard failures, empty-string sentinels for fail-soft returns.

**Example 1 -- empty-string sentinel:** `db_pool_get_entry()` in [`cpp-bindings/classic-cpp-bridge/src/database.rs`](../../cpp-bindings/classic-cpp-bridge/src/database.rs) returns `""` on lookup failure because Qt callers check `.isEmpty()` rather than catching exceptions.

**Example 2 -- DTO with `found: false`:** `db_pool_get_entry_typed()` in the same file returns a `FormIdEntryDto` with `found: false` for lookup misses. The DTO has fields `{formid, plugin, value, found}` where `found` is a `bool`. C++ callers check `dto.found` before using `dto.value`.

**Example 3 -- propagated `rust::Error`:** Functions like `orchestrator_process_log()` in [`cpp-bindings/classic-cpp-bridge/src/scanner.rs`](../../cpp-bindings/classic-cpp-bridge/src/scanner.rs) propagate `rust::Error` for infrastructure failures (runtime not initialized, config not loaded). The scan entry points are `orchestrator_process_log`, `orchestrator_process_logs_batch`, and `orchestrator_process_logs_batch_with_progress`.

---

## Node (NAPI-RS)

**Pattern:** `napi::Error` with a `code` field matching the Rust error variant name (e.g., `"InvalidArg"`, `"ParseError"`).

**Example 1:** `config_error_to_napi_err()` in [`node-bindings/classic-node/src/config.rs`](../../node-bindings/classic-node/src/config.rs) converts `ConfigError` variants to NAPI errors with structured codes. JavaScript consumers use `catch (e) { if (e.code === "ParseError") ... }`.

**Example 2:** `settings_error_to_napi_err()` in the same file converts `SettingsError` variants with codes like `"NotFound"`, `"YamlError"`, etc.

**Example 3:** `runtime_to_napi_err()` handles `anyhow::Error` wrapping with automatic downcast to typed errors.

Tests verify both `error.message` and `error.code` to ensure the structured error contract holds.

---

## Python (PyO3)

**Pattern:** Typed Python exception classes (e.g., `RustConfigParseError`, `RustConfigIOError`) with message inspection.

**Example 1:** `config_error_to_pyerr()` in [`python-bindings/classic-config-py/src/lib.rs`](../../python-bindings/classic-config-py/src/lib.rs) maps each `ConfigError` variant to a specific Python exception class.

**Example 2:** [`foundation/classic-shared-py/src/lib.rs`](../../foundation/classic-shared-py/src/lib.rs) provides `define_exceptions!` and `register_exceptions!` macros plus the `ToPyErr` trait and `ResultExt` extension for consistent exception wiring across all Python binding crates.

**Example 3:** Tests use `pytest.raises(RustConfigParseError)` with message inspection to verify both the exception type and the error context.

---

## Why They Differ

The three binding surfaces intentionally use different error shapes because each consumer ecosystem has established idioms:

- **C++ uses empty-string sentinels** because Qt callers (`classic-gui/`) are written to check `.isEmpty()` and display "not found" UI. Changing to exceptions would break existing call sites and require rewriting the GUI error handling flow.

- **Node uses `error.code` strings** because the Node ecosystem convention is `catch (e) { if (e.code === "ParseError") ... }`. This is idiomatic for JS/TS consumers and integrates naturally with error-handling middleware.

- **Python uses typed exception classes** because the Python ecosystem convention is `except RustConfigParseError as e:` with `isinstance` checks. This is idiomatic for Python consumers and enables fine-grained exception handling.

The project's Out of Scope section explicitly excluded standardizing these shapes: "Intentional design -- Qt fail-soft callers depend on empty-string sentinel return."

---

## Conversion Helper Reference

### C++

No dedicated error-conversion helper functions. Each bridge function uses `block_on()` with an inline `match` on `Result`. Errors either propagate as `rust::Error` exceptions or return sentinel values.

### Node

- `config_error_to_napi_err()` -- converts `ConfigError` variants to `napi::Error` with structured codes
- `settings_error_to_napi_err()` -- converts `SettingsError` variants
- `runtime_to_napi_err()` -- wraps `anyhow::Error` with automatic downcast

Source: [`node-bindings/classic-node/src/config.rs`](../../node-bindings/classic-node/src/config.rs)

### Python

- `define_exceptions!` -- creates the standard 3-tier exception hierarchy per module
- `register_exceptions!` -- registers exception classes in a Python module
- `ToPyErr` trait -- standard interface for error-to-`PyErr` conversion
- `ResultExt` -- extension trait for converting `Result<T, E>` to `PyResult<T>`
- `without_gil` -- GIL release helper for blocking operations

Source: [`foundation/classic-shared-py/src/lib.rs`](../../foundation/classic-shared-py/src/lib.rs)

Per-module converters like `config_error_to_pyerr()` live alongside each binding crate: [`python-bindings/classic-config-py/src/lib.rs`](../../python-bindings/classic-config-py/src/lib.rs)
