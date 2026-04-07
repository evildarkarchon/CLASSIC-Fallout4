# Coding Conventions

**Analysis Date:** 2026-04-04

## Naming Patterns

**Files:**
- Rust: `snake_case.rs` (e.g., `core.rs`, `pool_sqlx.rs`, `game_files.rs`)
- Crates: kebab-case with game-prefix (e.g., `classic-config-core`, `classic-file-io-py`)
- C++ source: `snake_case.cpp` / `snake_case.h` (e.g., `cli_args.cpp`, `thread_pool.h`)
- TypeScript: `camelCase.ts` for CLI (`run-scan.ts`), `kebab.spec.ts` for tests
- Python: `snake_case.py` (e.g., `tier1_parity_fixtures.py`)

**Functions:**
- Rust: `snake_case` for all functions and methods (e.g., `load_yaml_file`, `resolve_settings_search_paths`)
- NAPI (Node bindings): Rust functions are `snake_case` internally; NAPI auto-converts them to `camelCase` for JS consumers
- PyO3 (Python bindings): `snake_case` for Python-facing methods, using `#[pyo3(name = "...")]` to override when needed
- C++: `snake_case` for free functions and methods (e.g., `parse_args`, `auto_concurrency_for_cpu_count`)
- TypeScript: `camelCase` (e.g., `parseArgs`, `printHelp`, `requireValue`)

**Variables:**
- Rust: `snake_case` always
- C++: `snake_case` (e.g., `cpu_count`, `recommended`, `args`)
- TypeScript: `camelCase` (e.g., `gameVersion`, `fcxMode`, `showFidValues`)
- Python: `snake_case`

**Types (structs, enums, traits):**
- Rust: `PascalCase` (e.g., `FileIOCore`, `YamlDataCore`, `SuspectScanner`, `BackupType`)
- NAPI wrapper types: `Js` prefix (e.g., `JsModConflictEntry`, `JsSuspectErrorRule`, `JsDatabasePool`)
- C++: `PascalCase` structs (e.g., `CliArgs`, `ArgvBuilder`, `ProgressDisplay`)
- TypeScript interfaces/types: `PascalCase` (e.g., `CliOptions`, `SupportedGame`)

**Constants:**
- Rust: `SCREAMING_SNAKE_CASE` (e.g., `DEFAULT_CONFIG_FILENAME`, `NULL_VERSION`)
- TypeScript: `SCREAMING_SNAKE_CASE` (e.g., `BATCH_CACHE_TTL`, `THIS_SUITE`)

**Crate modules within Python bindings:**
- Python module names: `classic_config`, `classic_scanlog`, `classic_version_registry` (underscore, not hyphen)

## Code Style

**Rust formatting:**
- Tool: `rustfmt` via `cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml`
- No standalone `rustfmt.toml` detected; default rustfmt settings apply
- Workspace lints enforced in `ClassicLib-rs/Cargo.toml`:
  - `deprecated = "deny"`
  - `unused = "deny"`

**C++ formatting:**
- Tool: clang-format, config at `classic-cli/.clang-format` and `classic-gui/.clang-format`
- `ColumnLimit: 120`, `IndentWidth: 4`, `UseTab: Never`
- Braces: K&R / Attach style (same line for everything)
- Pointer alignment: `Left` (`int* p`)
- Standard: C++20, MSVC-targeted

**TypeScript:**
- Compiler: TypeScript 5.8+, `strict: true` in `tsconfig.json`
- No eslint or prettier config detected; strict TypeScript is the primary linting tool
- Target: `ES2022`, `module: CommonJS`

**Python:**
- Formatter: `ruff format` (from `CLAUDE.md` commands)
- No `ruff.toml` or `pyproject.toml` detected at repo root; ruff uses defaults
- Type hints: `from __future__ import annotations` used in test files; type annotations on all public functions

## Import Organization

**Rust:**

Standard order (by convention, enforced by rustfmt):
1. Standard library (`use std::...`)
2. External crates (alphabetical)
3. Internal crate modules (`use super::*`, `use crate::...`)
4. Re-exports (`pub use ...`)

Example from `classic-file-io-core/src/core.rs`:
```rust
use dashmap::DashMap;
use lru::LruCache;
// ... more external
use std::fs::File;
use std::path::{Path, PathBuf};
use tokio::fs;
// then internal
use super::dds::DDSHeader;
use super::encoding::EncodingDetector;
use super::error::FileIOError;
```

**TypeScript:**
1. Node built-ins (`node:fs`, `node:path`, `node:os`)
2. Framework imports (`bun:test`)
3. Local binding index (`../index.js`)
4. Local fixture files (`./fixtures/...`)

**Python:**
1. `from __future__ import annotations`
2. Standard library
3. Third-party (`pytest`)
4. Local imports

## Error Handling

**Rust - Core crates:**
- Use `thiserror` for typed, domain-specific errors
- Define a dedicated `error.rs` in each crate exposing a typed enum
- Provide a `Result<T>` type alias in each crate: `pub type Result<T> = std::result::Result<T, CrateError>`
- Use `anyhow::Result` and `.context()` in higher-level integration code and config loading
- `#[from]` attribute on error variants for `std::io::Error` and `tokio::task::JoinError` conversions
- Never use bare `unwrap()` in production code; use `.expect("descriptive message")` only in tests

Example from `classic-file-io-core/src/error.rs`:
```rust
#[derive(Debug, Error)]
pub enum FileIOError {
    #[error("I/O error: {0}")]
    IoError(#[from] std::io::Error),
    #[error("File not found: {0}")]
    NotFound(String),
    // ...
}
pub type Result<T> = std::result::Result<T, FileIOError>;
```

**NAPI (Node bindings):**
- Convert Rust errors to NAPI errors via helper functions (e.g., `config_error_to_napi_err`)
- NAPI errors include a `code` field matching the variant name (e.g., `"InvalidArg"`, `"ParseError"`)
- Tests verify both `error.message` and `error.code`

**PyO3 (Python bindings):**
- Expose typed Python exception classes (e.g., `classic_config.RustConfigParseError`, `classic_config.RustConfigIOError`)
- Tests use `pytest.raises(ExceptionClass)` with message inspection

**C++:**
- CLI11 parse errors call `std::exit(app.exit(e))` directly
- Result propagation via return values; no exceptions in bridge-facing code

## Logging

**Framework:** `log` crate (`log::debug!`, `log::warn!`, `log::info!`, `log::error!`)

**Patterns:**
- Internal business-logic crates use `log::debug!` extensively for tracing data extraction
- `log::warn!` used for missing or unexpected YAML keys
- `tracing` crate is a workspace dependency but primary usage in business logic is `log` macros
- Production code does not use `println!`/`eprintln!` directly; CLI output goes through the report system

## Comments

**Rust doc comments:**
- Module-level: `//!` doc comments at the top of every `lib.rs` and key modules
- Required sections for modules: description, architecture note, and `# Examples` with runnable code
- Public items: `///` doc comments with `# Arguments`, `# Returns`, `# Examples` as needed
- Private items: `//` comments where behavior is non-obvious

Example pattern from `classic-message-core/src/lib.rs`:
```rust
//! Core message routing and formatting for CLASSIC.
//!
//! # Architecture
//! ...
//! # Examples
//! ```rust
//! use classic_message_core::{Message, MessageType};
//! let msg = Message::new("Operation started", MessageType::Info);
//! ```
```

**C++:**
- `///` doc-style comments for public functions in headers (Doxygen-adjacent)
- `//` for inline implementation notes

**TypeScript:**
- TSDoc `@param`, `@throws` comments on NAPI-exposed Rust functions (in `.rs` source, not `.ts`)
- Minimal comments in TypeScript CLI source; self-documenting code preferred

## Function Design

**Size:** Functions are generally focused; larger methods in `FileIOCore` and `YamlDataCore` are acceptable for complex workflows

**Parameters:**
- Rust: prefer `&str` over `String` for input, `impl Into<String>` for builders
- Use `Option<&Path>` for optional path parameters
- Async functions use `async fn` throughout; no manual `Future` boxing in business logic

**Return Values:**
- Return `Result<T>` or `Option<T>` consistently; never panic on expected failure conditions
- Builder pattern used in `Message`: `Message::new(...).with_title(...).with_details(...)`

## Module Design

**Exports (Rust):**
- `lib.rs` re-exports all public API items explicitly
- `pub use` is used to flatten module hierarchies at the crate boundary
- Internal helpers stay private (`fn` without `pub`)

**Barrel files (TypeScript):**
- Single `index.js` / `index.d.ts` as the binding surface; all exports flow through it
- Test files import exclusively from `"../index.js"`, never from individual binding modules

**Python modules:**
- Each crate produces a top-level `classic_*` Python module
- A `pyi` stub file lives alongside each binding crate (e.g., `classic-config-py/classic_config.pyi`)

## NAPI-RS Specific Conventions (Node Bindings)

- All NAPI structs are annotated `#[napi]` or `#[napi(object)]`
- Constructors use `#[napi(constructor)]`, factory methods use `#[napi(factory)]`
- Private state in NAPI structs uses an `inner:` field holding the core Rust type
- The `Js` prefix is used for NAPI-facing types that wrap core types (e.g., `JsFileIO`, `JsDatabasePool`)
- App directory must be initialized via `Once` guard to resolve paths correctly in Node/Bun context

## PyO3 Specific Conventions (Python Bindings)

- `#[getter]` attribute exposes Python properties with `snake_case` names
- `#[pyo3(name = "method_name")]` overrides Rust name when Python convention differs
- `#[allow(non_snake_case)]` used selectively where YAML keys require uppercase names
- Python binding crates are excluded from the standard Rust test run (require Python DLL at runtime)

---

*Convention analysis: 2026-04-04*
