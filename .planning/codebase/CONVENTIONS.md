# Coding Conventions

**Analysis Date:** 2026-04-14

## Naming Patterns

**Files:**
- Rust crate source files use `snake_case.rs` under the repo-root Rust layers, e.g. `foundation/classic-shared-core/src/errors.rs` and `business-logic/classic-config-core/src/config.rs`.
- Rust crate names use `classic-*-core`, `classic-*-py`, and `classic-node` patterns in the repo-root `Cargo.toml` workspace.
- C++ CLI files use `snake_case.cpp` / `snake_case.h` in `classic-cli/src/`, e.g. `classic-cli/src/cli_args.cpp` and `classic-cli/src/thread_pool.h`.
- C++ GUI files also use lowercase path segments with `snake_case` filenames in `classic-gui/src/`, e.g. `classic-gui/src/controllers/scancontroller.cpp` and `classic-gui/src/core/signalhub.h`.
- TypeScript CLI files use `camelCase.ts` in `node-bindings/classic-node/cli/`, e.g. `node-bindings/classic-node/cli/run-scan.ts` and `node-bindings/classic-node/cli/main.ts`.
- TypeScript/Bun tests use `*.spec.ts` in `node-bindings/classic-node/__test__/`, e.g. `node-bindings/classic-node/__test__/config.spec.ts`.
- Python modules and tests use `snake_case.py`, e.g. `python-bindings/tests/test_promoted_config_smoke.py` and `tools/node_api_parity/check_parity_gate.py`.

**Functions:**
- Rust uses `snake_case` for functions and methods, e.g. `resolve_settings_search_paths()` in `business-logic/classic-config-core/src/config.rs` and `get_runtime()` in `foundation/classic-shared-core/src/lib.rs`.
- C++ CLI free functions use `snake_case`, e.g. `parse_args()` and `auto_concurrency_for_cpu_count()` in `classic-cli/src/cli_args.cpp`.
- TypeScript uses `camelCase`, e.g. `parseArgs()`, `printHelp()`, and `requireValue()` in `node-bindings/classic-node/cli/main.ts`.
- Python test helpers use `snake_case`, e.g. `load_module()` and `minimal_diff_report()` in `python-bindings/tests/test_parity_gate_tooling.py`.

**Variables:**
- Rust local variables use `snake_case`, e.g. `worker_threads`, `effective_rust_symbol`, and `targeted_rejection_message` in `foundation/classic-shared-core/src/lib.rs`, `tools/node_api_parity/check_parity_gate.py`, and `classic-gui/src/controllers/scancontroller.cpp`.
- C++ GUI member variables use `m_` prefixes, e.g. `m_scanning`, `m_signalHub`, and `m_currentWorker` in `classic-gui/src/controllers/scancontroller.h`.
- C++ CLI struct fields use plain `snake_case`, e.g. `game_version`, `max_concurrent`, and `input_paths` in `classic-cli/src/cli_args.h`.
- TypeScript object fields use `camelCase`, e.g. `gameVersion`, `showFidValues`, and `maxConcurrent` in `node-bindings/classic-node/cli/main.ts`.
- Shared constants use `SCREAMING_SNAKE_CASE`, e.g. `DEFAULT_CONFIG_FILENAME` in `business-logic/classic-config-core/src/config.rs`, `THIS_SUITE` in `node-bindings/classic-node/__test__/config.spec.ts`, and `PARITY_MAIN_YAML` in `python-bindings/tests/fixtures/tier1_parity_fixtures.py`.

**Types:**
- Rust types use `PascalCase`, e.g. `RuntimeConfig`, `ClassicError`, and `YamlSource` in `foundation/classic-shared-core/src/lib.rs` and `business-logic/classic-config-core/src/config.rs`.
- NAPI-facing Rust wrappers use `Js` prefixes where they wrap JS-visible types, as described in `node-bindings/classic-node/src/lib.rs` and reflected by exports like `JsDatabasePool` in `node-bindings/classic-node/__test__/parity_tier1.spec.ts`.
- C++ structs/classes use `PascalCase`, e.g. `CliArgs` in `classic-cli/src/cli_args.h` and `ScanController` in `classic-gui/src/controllers/scancontroller.h`.
- TypeScript type imports use `PascalCase`, e.g. `CliOptions` and `SupportedGame` in `node-bindings/classic-node/cli/main.ts`.

## Code Style

**Formatting:**
- Rust formatting is enforced through `cargo fmt --all -- --check` in `.github/workflows/ci-rust.yml`.
- No standalone Rust formatter config file was detected; workspace code follows default `rustfmt` style plus workspace lints in `Cargo.toml`.
- C++ formatting is explicitly configured in `classic-cli/.clang-format` and `classic-gui/.clang-format`.
- Common C++ settings across both `.clang-format` files: `ColumnLimit: 120`, `IndentWidth: 4`, `UseTab: Never`, left-aligned pointers/references, and preserved include blocks.
- `classic-cli/.clang-format` uses attach/K&R braces and snake_case-oriented comments.
- `classic-gui/.clang-format` uses custom brace wrapping with function-definition braces on the next line and Qt macro awareness for `Q_EMIT`, `Q_SIGNAL`, and `Q_SLOT`.
- TypeScript strictness is enforced by `node-bindings/classic-node/tsconfig.json` with `strict: true`, `target: "ES2022"`, `module: "CommonJS"`, and `noEmitOnError: true`.
- No ESLint, Prettier, Ruff, or repo-level `.editorconfig` config was detected.

**Linting:**
- Rust workspace lints deny `deprecated` and `unused` in `Cargo.toml` under `[workspace.lints.rust]`.
- Clippy is treated as a CI gate via `cargo clippy --workspace --all-targets --all-features -- -D warnings` in `.github/workflows/ci-rust.yml`.
- TypeScript quality is primarily enforced by `tsconfig.json` and runtime parity tests; no separate TS lint config was detected.
- Python quality is test-driven in current state: `python-bindings/requirements-ci.txt` only lists `maturin` and `pytest`.

## Import Organization

**Order:**
1. Standard library / platform modules first, e.g. `use std::...` in `business-logic/classic-config-core/src/config.rs`, `import json` / `from pathlib import Path` in `python-bindings/tests/test_parity_gate_tooling.py`, and `import { basename } from "node:path"` in `node-bindings/classic-node/cli/main.ts`.
2. Third-party dependencies next, e.g. `use anyhow::{Context, Result};`, `use serde::{Deserialize, Serialize};`, `import pytest`, and `import { describe, test, expect } from "bun:test"`.
3. Repo-local modules last, e.g. `use classic_settings_core::{...}` in `business-logic/classic-config-core/src/config.rs`, `import classic_config` in `python-bindings/tests/test_promoted_config_smoke.py`, and `import { SUPPORTED_GAMES } from "./types"` in `node-bindings/classic-node/cli/main.ts`.

**Path Aliases:**
- No TypeScript path aliases were detected in `node-bindings/classic-node/tsconfig.json`.
- Tests import the Node binding surface from `../index.js` rather than internal modules, e.g. `node-bindings/classic-node/__test__/config.spec.ts` and `node-bindings/classic-node/__test__/parity_tier1.spec.ts`.
- Python parity-tool tests centralize `sys.path` bootstrapping in `tools/python_api_parity/tests/conftest.py` and `tools/node_api_parity/tests/conftest.py` instead of repeating `sys.path.insert()` per test file.

## Error Handling

**Patterns:**
- Rust foundational code prefers typed domain errors. `foundation/classic-shared-core/src/errors.rs` defines `ClassicError` with structured variants like `Io`, `Validation`, `Parse`, `NotFound`, and `InvalidState`.
- Higher-level Rust integration code often uses `anyhow::{Context, Result}`, e.g. `business-logic/classic-config-core/src/config.rs`.
- Expectation failures in tests use explicit messages, e.g. `expect("Lookup should succeed")` in `business-logic/classic-database-core/tests/integration_tests.rs` and `expect("Stats should exist")` in `foundation/classic-shared-core/tests/test_rolling_stats.rs`.
- Node parity/tooling code returns human-readable diagnostics rather than silent booleans, e.g. `validate_contract_surface()` in `tools/node_api_parity/check_parity_gate.py` appends specific remediation messages that include crate names and `bun run build` guidance.
- C++ Qt bridge code converts Rust failures to UI-safe signals instead of throwing through Qt event loops, e.g. `classic-gui/src/controllers/scancontroller.cpp` catches `rust::Error`, emits `scanError`, and returns early.
- TypeScript tests validate both message and code where exposed. `node-bindings/classic-node/__test__/config.spec.ts` checks thrown `Error & { code?: string }` values and asserts `code === "InvalidArg"`.
- Python fixtures treat cleanup as best effort rather than suite-failing teardown, e.g. `python-bindings/tests/conftest.py` catches broad exceptions only inside cleanup code and documents the intent.

## Logging

**Framework:** `log` / `tracing` in Rust, Qt logging helpers in GUI, stderr/console only in thin CLIs.

**Patterns:**
- Rust workspace dependencies include `log`, `env_logger`, `tracing`, and `tracing-subscriber` in `Cargo.toml`.
- GUI code uses Qt logging for operator-visible warnings, e.g. `qWarning(...)` in `classic-gui/src/controllers/scancontroller.cpp` when targeted inputs are rejected.
- TypeScript CLI writes human-facing errors to `console.error(...)` only at the executable boundary in `node-bindings/classic-node/cli/main.ts`.
- Tests do not rely on log scraping; they assert return values, emitted signals, generated files, or structured diagnostics directly.

## Comments

**When to Comment:**
- Public Rust modules commonly start with `//!` module docs that state purpose and architecture, e.g. `foundation/classic-shared-core/src/lib.rs` and `foundation/classic-shared-core/src/errors.rs`.
- Section-divider comments are common in larger test files, e.g. `node-bindings/classic-node/__test__/config.spec.ts`, `python-bindings/tests/test_promoted_config_smoke.py`, and `business-logic/classic-database-core/tests/integration_tests.rs`.
- Non-obvious behavior is documented inline near the logic it protects, e.g. the portable-app write-path comments in `classic-gui/src/controllers/scancontroller.cpp` and the proxy-row rules in `tools/node_api_parity/check_parity_gate.py`.

**JSDoc/TSDoc:**
- Rust public APIs carry `///` docs with examples and rationale, e.g. `RuntimeConfig` and `get_runtime()` in `foundation/classic-shared-core/src/lib.rs`.
- Python tests use docstrings to state contract intent, e.g. `python-bindings/tests/test_promoted_config_smoke.py` and `tools/cxx_api_parity/tests/test_parser.py`.
- TypeScript CLI code is mostly self-documenting and uses minimal doc comments; long-form documentation lives closer to Rust-exported APIs and test fixtures.

## Function Design

**Size:**
- Small helpers are preferred for parsing and normalization, e.g. `cleanDirectoryPath()`, `isCrashLogPath()`, and `collectReportDirectories()` in `classic-gui/src/controllers/scancontroller.cpp`.
- Larger workflow functions are acceptable when they orchestrate multi-step flows, e.g. `ScanController::startScan(...)` in `classic-gui/src/controllers/scancontroller.cpp` and `validate_contract_surface()` in `tools/node_api_parity/check_parity_gate.py`. Keep helper extraction around them rather than embedding all logic inline.

**Parameters:**
- Rust favors borrowed path/string inputs and typed enums where possible, e.g. `Option<&Path>` helpers in `business-logic/classic-config-core/src/config.rs`.
- CLI adapters prefer flat, explicit option structs rather than dynamic maps, e.g. `CliArgs` in `classic-cli/src/cli_args.h` and `CliOptions` construction in `node-bindings/classic-node/cli/main.ts`.
- Python tests type annotate helper parameters consistently, e.g. `tmp_path: Path`, `monkeypatch: pytest.MonkeyPatch`, and explicit return types in `python-bindings/tests/test_parity_gate_tooling.py`.

**Return Values:**
- Rust returns `Result<T, E>` or `Option<T>` for expected failure states, e.g. `foundation/classic-shared-core/src/errors.rs` and `business-logic/classic-config-core/src/config.rs`.
- TypeScript parsing helpers throw `Error` on invalid CLI input rather than returning sentinel values, e.g. `parseInteger()` and `requireValue()` in `node-bindings/classic-node/cli/main.ts`.
- Qt controller methods signal failures through emitted signals and object state rather than exceptions crossing thread boundaries, e.g. `classic-gui/src/controllers/scancontroller.cpp`.

## Module Design

**Exports:**
- Rust crate boundaries are flattened through explicit `pub use`, e.g. `foundation/classic-shared-core/src/lib.rs` re-exports `ClassicError`, `ClassicResult`, and `game_id` items.
- Node bindings are intentionally centralized behind `node-bindings/classic-node/index.js` and `index.d.ts`; tests consume that public surface only.
- Python bindings expose one top-level module per crate plus `.pyi` stubs, e.g. `python-bindings/classic-config-py/classic_config.pyi` and `foundation/classic-shared-py/classic_shared.pyi`.

**Barrel Files:**
- Rust uses `lib.rs` as the barrel/export boundary in each crate, e.g. `foundation/classic-shared-core/src/lib.rs` and `node-bindings/classic-node/src/lib.rs`.
- Node uses a single binding barrel (`node-bindings/classic-node/index.js` / `index.d.ts`) instead of per-feature public entrypoints.
- Python tooling tests use `conftest.py` as shared bootstrap/fixture entrypoints rather than package barrels.

---

*Convention analysis: 2026-04-14*
