# Coding Conventions

**Analysis Date:** 2026-03-30

## Language-Specific Conventions

This codebase is multi-language. Each language has its own conventions.

---

## Rust Conventions

### Naming Patterns

**Crates:**
- Kebab-case with a `-core` suffix for pure business logic: `classic-config-core`, `classic-yaml-core`
- Kebab-case with a `-py` suffix for PyO3 bindings: `classic-config-py`, `classic-yaml-py`
- Kebab-case with a `-cpp-bridge` or `-node` suffix for C++ / Node bindings

**Files:**
- snake_case module files: `pool_sqlx.rs`, `game_files.rs`, `log_collection.rs`
- Integration test files named `integration_tests.rs` under `tests/`
- Benchmark files under `benches/`

**Functions and Methods:**
- snake_case for all functions: `load_yaml_file`, `hash_files_parallel`, `create_backup`
- Async functions use same naming: `read_file`, `write_file`, `load_from_yaml_files`
- Builder methods use `with_` prefix: `with_title()`, `with_details()`

**Types and Structs:**
- PascalCase for all types: `FileIOCore`, `YamlDataCore`, `ClassicError`, `BackupManager`
- Enums use PascalCase: `MessageType`, `MessageTarget`, `BackupType`, `Fallout4Version`
- Error types end in `Error`: `ClassicError`, `FileIOError`, `DatabaseError`, `ConfigError`

**Constants:**
- SCREAMING_SNAKE_CASE: `HASH_CHUNK_SIZE`, `DEFAULT_CONFIG_FILENAME`, `SHORT_SCAN_CACHE_CAPACITY`
- Static globals use `LazyLock` with SCREAMING_SNAKE_CASE: `HASH_CACHE`, `NULL_VERSION`

**Variables:**
- snake_case: `backup_dir`, `game_root`, `temp_dir`, `yaml_dirs`
- Abbreviations preserved when conventional: `ec` for `error_code`, `mmap` for memory map

### Code Style

**Formatting:**
- `cargo fmt` enforced (run as part of pre-commit minimum: `cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml`)
- Rust edition 2024 (`edition = "2024"`) with `rust-version = "1.85"`

**Linting:**
- Workspace-level lint config in each crate's `Cargo.toml` under `[lints.rust]`:
  ```toml
  [lints.rust]
  deprecated = "deny"
  rust_2024_compatibility = "warn"
  unsafe_code = "deny"
  missing_docs = "warn"
  unused = "deny"
  ```
- `unsafe_code = "deny"` across all business logic crates; exceptions require `#[allow(unsafe_code)]` with justification
- Actual unsafe is limited to CXX FFI (`classic-cpp-bridge/src/scanner.rs`) and mmap (`classic-file-io-core/src/core.rs`)
- Clippy run with `-D warnings` in CI: `cargo clippy --workspace --all-targets --all-features -- -D warnings`

### Attributes

**`#[must_use]`:** Applied to all pure query/accessor methods that return meaningful values. Example from `classic-constants-core/src/lib.rs`:
```rust
#[must_use]
pub const fn is_vr(&self) -> bool { ... }

#[must_use]
pub const fn exe_name(&self) -> &'static str { ... }
```

**`#[derive(...)]`:** Use standard derives together:
```rust
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
```

### Import Organization

**Order:**
1. Standard library (`std::`)
2. External crates (alphabetical within each group)
3. Internal workspace crates (`classic_*`)
4. Local module imports (`super::`, `crate::`)

**Namespace aliases:** Use `fs` for `std::fs` or `tokio::fs`, `Arc` from prelude, `ns` prefixes for long module paths:
```rust
use tokio::fs;
use std::path::{Path, PathBuf};
use classic_yaml_core::YamlOperations;
```

### Module Documentation

**Crate-level docs:** Every crate has a module-level doc comment (`//!`) in `lib.rs` explaining purpose, architecture notes, and examples:
```rust
//! Core file I/O implementation with async support (Pure Rust)
//!
//! This module provides high-performance file I/O operations with:
//! - Async file operations with Tokio
//! - Memory-mapped file support for large files
```

**Function-level docs:** Public functions must have doc comments with `# Arguments`, `# Returns`, `# Errors`, and `# Examples` sections. `missing_docs = "warn"` is enforced.

**Inline comments:** `//` comments for implementation logic, especially for optimization notes:
```rust
// Optimization 1.3: Use lock-free Cache instead of RwLock<LruCache>
// Expected impact: 15-25% faster reads, 3-5x better concurrency
let read_cache = Cache::new(cache_size);
```

### Error Handling

**Strategy:** `Result<T, E>` propagation with `?`. Never panic in library code.

**Error types:**
- Business logic crates define their own error enum using `thiserror`: `ClassicError`, `FileIOError`, `DatabaseError`, `ConfigError`, `GamePathError`
- `anyhow` is used in application-layer and async orchestrators for context chaining: `.context("Failed to read config")?`
- The `IntoClassicError` trait provides ergonomic conversion: `.into_classic("context message")?`
- Error variants carry structured context fields, not just strings:
  ```rust
  ConfigError::IOError { context, .. }
  ConfigError::ParseError { context, .. }
  ConfigError::EmptyDocument(msg)
  ConfigError::InvalidInput(msg)
  ```

**Pattern for async errors:**
```rust
tokio::fs::read_to_string(path)
    .await
    .into_classic(format!("Failed to read config: {}", path.display()))?;
```

### Async Patterns

**ONE RUNTIME RULE:** All crates use the shared Tokio runtime from `classic_shared_core::get_runtime()`. Never create a new `tokio::runtime::Runtime` in any crate.

**Async functions:** Prefer `async fn` at public API boundaries; use `tokio::spawn` for concurrent tasks, `JoinSet` for collecting multiple results.

**Blocking I/O:** Memory-mapped reads are wrapped with `#[allow(unsafe_code)]` and use `tokio::task::spawn_blocking` or are sequenced outside async contexts.

### Logging

**Mixed approach:** Two logging facades are used across the codebase:
- `log` crate (`log::info!`, `log::warn!`, `log::error!`, `log::debug!`): used in business logic crates (`classic-config-core`, `classic-database-core`, `classic-scanlog-core`, `classic-message-core`)
- `tracing` crate (`tracing::warn!`, `tracing::debug!`, `tracing::trace!`): used in `classic-file-io-core`, `classic-settings-core`, `classic-yaml-core`, and TUI application

**Pattern:** Log at `warn` for recoverable issues, `error` for propagated failures, `debug`/`trace` for cache hits and performance notes.

---

## C++ Conventions (classic-cli)

### Naming Patterns

**Files:** snake_case for both headers and implementation: `cli_args.h`, `cli_args.cpp`, `thread_pool.h`

**Types and Structs:** PascalCase: `CliArgs`, `ArgvBuilder`, `DataDirs`

**Functions:** snake_case: `parse_args()`, `auto_concurrency_for_cpu_count()`, `find_data_root()`

**Variables and Parameters:** snake_case: `cpu_count`, `recommended`, `exe_path`

**Private members:** Trailing underscore convention noted in `.clang-format` comment: "trailing underscore for private members"

### Code Style

**Formatting:** clang-format with K&R brace style (Attach), 4-space indent, 120-column limit. Config: `classic-cli/.clang-format`

**Pointer/reference alignment:** Left-aligned: `int* p`, `const std::string& s`

**Short forms:** `AllowShortFunctionsOnASingleLine: Inline` — inline functions in one line, `if` statements always use braces

**Standard:** C++20 (`set(CMAKE_CXX_STANDARD 20)`)

**MSVC flags:** `/utf-8 /W4` applied to all targets

**Header guard:** `#pragma once` in all headers (not include guards)

**Anonymous namespaces:** Used for file-local helpers in `.cpp` files:
```cpp
namespace {
QString format_elapsed_seconds(const QElapsedTimer& timer) { ... }
}
```

**Namespace alias:** `namespace fs = std::filesystem;` at top of files using std::filesystem

### Import Organization

**Order:**
1. Corresponding header (`#include "scanner.h"`)
2. Platform-specific includes (inside `#ifdef _WIN32`)
3. CXX bridge headers
4. Standard library headers (alphabetical)
5. Third-party headers (fmt, CLI11)

### Comments

**Triple-slash doc comments (`///`):** Used for public types, functions, and structs in headers
**Section dividers:** `// ── Section Name ────────────` style used in larger files

---

## C++ Conventions (classic-gui)

### Naming Patterns

**Files:** lowercase camelCase filenames: `mainwindow.h`, `scancontroller.cpp`, `signalhub.h`, `reportlistwidget.cpp`

**Classes:** PascalCase Qt-style: `MainWindow`, `ScanController`, `SignalHub`, `BatchProgressModel`

**Member variables:** `m_` prefix for private members (noted in `.clang-format`: "m_ prefix members")

**Methods:** camelCase: `setupUi()`, `connectSignals()`, `loadSettings()`, `setStatusMessage()`

**Qt slots:** camelCase, described in `private slots:` section

### Code Style

**Formatting:** clang-format with custom brace style (next-line for function definitions only), 4-space indent, 120-column limit. Config: `classic-gui/.clang-format`

**Qt macros:** `Q_OBJECT`, `Q_EMIT`, `Q_SIGNAL`, `Q_SLOT` treated as statement-attribute-like macros

**Test framework:** Qt Test (`QTest`) with `QTEST_GUILESS_MAIN` for headless tests, `QCOMPARE`/`QVERIFY`/`QVERIFY2`

---

## TypeScript/Node Conventions (classic-node)

### Naming Patterns

**Test files:** `*.spec.ts` in `__test__/` directory

**Imports:** Named imports from `"../index.js"` (not `.ts`)

**Test fixtures:** SCREAMING_SNAKE_CASE for inline YAML string constants: `MAIN_YAML`, `GAME_YAML`, `IGNORE_YAML`

**Exported functions:** camelCase: `createYamlDataFromContent`, `clearYamlCache`, `setApplicationDir`

**Classes:** PascalCase mirroring Rust: `YamlData`, `ClassicConfigJs`, `JsFileIO`, `JsDatabasePool`

### Code Style

**Runtime:** Bun with TypeScript; compiled via `tsc`
**Test framework:** `bun:test` — `describe`, `test`, `expect`, `beforeEach`, `afterEach`
**Fixture management:** `beforeEach` clears caches (`clearYamlCache()`), `afterEach` removes temp directories

---

## Python Conventions (python-bindings)

### Naming Patterns

**Test files:** `test_*.py` in `tests/` directory

**Fixtures:** Separate `fixtures/` subdirectory with `__init__.py`: `ClassicLib-rs/python-bindings/tests/fixtures/`

**Constants:** SCREAMING_SNAKE_CASE for YAML fixture strings: `PARITY_MAIN_YAML`, `PARITY_GAME_YAML`

**Functions:** snake_case: `test_imports_and_versions()`, `_run_config_tier1_smoke()`

### Code Style

**Type annotations:** `from __future__ import annotations` at top of all test files; full typing with `Any`, `cast`, return type annotations

**Formatter:** `uv run ruff format .` (enforced in pre-commit minimum)

**Test framework:** pytest with `pytest.raises` for exception testing, `tmp_path` fixture for temp dirs, `monkeypatch` for environment patching

---

## Cross-Language Architecture Conventions

**Layering rule:** Business logic lives in Rust `-core` crates. Binding layers (Python `-py`, Node `-node`, C++ bridge) are thin wrappers. Logic duplication across binding layers is prohibited.

**Parity enforcement:** Node and Python bindings maintain API parity checked via `tools/node_api_parity/` and `tools/python_api_parity/`. The parity gate runs as part of CI.

**Version:** All crates within the workspace share `version = "9.0.0"`.

**Docs requirement:** Public API changes require updating files under `docs/api/` in the same change (enforced by `AGENTS.md`).

---

*Convention analysis: 2026-03-30*
