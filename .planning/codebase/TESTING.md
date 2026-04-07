# Testing Patterns

**Analysis Date:** 2026-04-04

## Test Framework Overview

This is a multi-language project with distinct test frameworks per layer:

| Layer | Framework | Config |
|-------|-----------|--------|
| Rust (core crates) | `cargo test` + `tokio::test` | `ClassicLib-rs/Cargo.toml` |
| C++ | Catch2 v3 | `classic-cli/CMakeLists.txt`, `classic-gui/CMakeLists.txt` |
| Node/Bun bindings | Bun test + Node `node:test` | `ClassicLib-rs/node-bindings/classic-node/package.json` |
| Python bindings | pytest | `ClassicLib-rs/python-bindings/tests/` |

## Rust Test Framework

**Runner:** `cargo test` (standard Rust test harness)

**Async test attribute:** `#[tokio::test]` for async tests (workspace dependency `tokio` with `features = ["full"]`)

**Serial tests:** `serial_test` crate with `#[serial]` attribute for tests that mutate global/filesystem state

**Run Commands:**
```bash
# All workspace tests (excluding PyO3 crates)
cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml

# Single crate
cargo test -p classic-config-core --manifest-path ClassicLib-rs/Cargo.toml

# Named test
cargo test --manifest-path ClassicLib-rs/Cargo.toml test_name
```

**Coverage Commands (PowerShell):**
```powershell
# Workspace coverage (HTML + JSON + lcov)
./ClassicLib-rs/coverage_report.ps1

# Per-crate coverage
./ClassicLib-rs/coverage_report.ps1 -Package classic-scanlog-core

# Summary table (60% target threshold)
./ClassicLib-rs/coverage_summary.ps1
```

**Coverage tool:** `cargo-llvm-cov` (LLVM instrumentation), outputs to `ClassicLib-rs/target/llvm-cov/`

## Rust Test File Organization

**Two patterns are used:**

**1. Inline unit tests** — `#[cfg(test)]` module at the bottom of the source file. Used when tests exercise private internals or require close proximity to the implementation.

Location: Bottom of source file (118 files use this pattern)

```rust
// src/core.rs (bottom)
#[cfg(test)]
mod tests {
    use super::*;
    use serial_test::serial;
    use std::io::Write;
    use tempfile::TempDir;

    #[test]
    fn test_new_with_default_parameters() {
        let core = FileIOCore::default();
        assert_eq!(core.default_encoding, "utf-8");
    }

    #[tokio::test]
    async fn test_read_file_success() {
        let temp = TempDir::new().unwrap();
        let file_path = temp.path().join("test.txt");
        std::fs::write(&file_path, "Hello, World!").unwrap();
        let core = FileIOCore::default();
        let content = core.read_file(&file_path).await.unwrap();
        assert_eq!(content, "Hello, World!");
    }
}
```

**2. Separate integration test files** — `tests/integration_tests.rs` in a `tests/` directory alongside `src/`. Used for cross-component workflows.

Location: `ClassicLib-rs/business-logic/<crate>/tests/integration_tests.rs`

Known integration test files:
- `ClassicLib-rs/business-logic/classic-config-core/tests/integration_tests.rs`
- `ClassicLib-rs/business-logic/classic-database-core/tests/integration_tests.rs`
- `ClassicLib-rs/business-logic/classic-yaml-core/tests/integration_tests.rs`
- `ClassicLib-rs/foundation/classic-shared-core/tests/test_path_lru.rs`
- `ClassicLib-rs/foundation/classic-shared-core/tests/test_rolling_stats.rs`
- `ClassicLib-rs/ui-applications/classic-tui/tests/event_tests.rs`
- `ClassicLib-rs/ui-applications/classic-tui/tests/render_tests.rs`

## Rust Test Structure

**Suite organization in integration tests** — group by workflow using nested `mod` blocks with section comments:

```rust
//! Integration tests for classic-config-core

use classic_config_core::{ConfigError, YamlDataCore};
use tempfile::tempdir;

// ============================================================================
// Test Data Fixtures
// ============================================================================

fn minimal_main_yaml() -> &'static str {
    r#"CLASSIC_Info:
  version: "7.31.0""#
}

// ============================================================================
// Complete Configuration Loading Workflow Tests
// ============================================================================

mod config_loading_workflows {
    use super::*;

    #[tokio::test]
    async fn test_complete_config_load_workflow() {
        let temp_dir = tempdir().expect("Failed to create temp dir");
        // ... setup ...
        let config = YamlDataCore::load_from_yaml_files(yaml_dirs, "Fallout4".to_string(), "auto".to_string())
            .await
            .expect("Config load should succeed");
        assert_eq!(config.classic_version, "7.31.0");
    }
}

mod error_handling_workflows {
    use super::*;

    #[test]
    fn test_invalid_yaml_error() {
        let result = YamlDataCore::from_yaml_content("{ invalid: }}}",  ...);
        assert!(result.is_err());
        match result {
            Err(ConfigError::ParseError { context, .. }) => {
                assert!(context.contains("main"));
            }
            Err(e) => panic!("Expected ParseError, got {:?}", e),
            Ok(_) => panic!("Should fail with invalid YAML"),
        }
    }
}
```

**Patterns:**
- Setup: use `tempfile::tempdir()` or `tempfile::NamedTempFile` for all file-based tests
- Teardown: tempfile handles automatic cleanup on drop
- Assertions: `assert_eq!`, `assert!`, `assert!(result.is_err())`, pattern matching on error variants
- In tests, `.expect("descriptive message")` is preferred over `.unwrap()` for clarity

## Rust Mocking

**Framework:** No external mock framework. Tests use:
- Real in-memory data or temp files instead of mocks
- Dependency injection via function parameters accepting `impl Fn` closures
- `#[cfg(test)]` to expose test-only constructors (e.g., `new_with_limits`)

Example from `classic-config-core/src/config.rs`:
```rust
fn choose_settings_write_path_with_access(
    existing_paths: &[PathBuf],
    app_dir: Option<&Path>,
    _user_dir: Option<&Path>,
    can_update_existing: impl Fn(&Path) -> bool,  // injectable behavior
    can_create_new: impl Fn(&Path) -> bool,
) -> Result<Option<PathBuf>> { ... }
```

**What to use real implementations for:**
- File I/O (use `tempfile::TempDir`)
- SQLite databases (use `tempfile::NamedTempFile` with `.db` suffix)
- YAML parsing (use inline string literals)

**What NOT to mock:**
- The Tokio runtime (use shared runtime from `classic-shared-core`)
- The `#[cfg(test)]` block structure itself

## Rust Test Data Fixtures

**Pattern:** Static functions returning `&'static str` YAML literals

```rust
fn minimal_main_yaml() -> &'static str {
    r#"
CLASSIC_Info:
  version: "7.31.0"
  version_date: "2024-01-15"
"#
}

fn minimal_game_yaml() -> &'static str {
    r#"
Game_Info:
  XSE_Acronym: "F4SE"
  GameVersion: "1.10.163"
"#
}
```

**Location:** Defined at module scope above test mod blocks in integration test files.

**For async database tests:** Helper async functions (e.g., `create_test_database`) that set up SQLite in `tempfile::NamedTempFile`.

## C++ Test Framework

**Runner:** Catch2 v3 (discovered via `catch_discover_tests` in CMake)

**Config:** Built only when `find_package(Catch2 3 CONFIG QUIET)` succeeds; requires `catch2` in vcpkg.json

**Run via PowerShell wrapper (never raw ctest):**
```powershell
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test -CTestName "CliArgs defaults"
```

**Location:** `classic-cli/tests/test_*.cpp`, `classic-gui/tests/test_*.cpp`

**Test structure:**
```cpp
#include <catch2/catch_test_macros.hpp>
#include "cli_args.h"

TEST_CASE("CliArgs defaults", "[cli_args]") {
    ArgvBuilder ab({"classic-cli"});
    CliArgs args = parse_args(ab.argc(), ab.argv());
    REQUIRE(args.game == "Fallout4");
    REQUIRE(args.fcx_mode == false);
}

TEST_CASE("CliArgs boolean flags", "[cli_args]") {
    SECTION("--fcx-mode enables FCX") {
        ArgvBuilder ab({"classic-cli", "--fcx-mode"});
        CliArgs args = parse_args(ab.argc(), ab.argv());
        REQUIRE(args.fcx_mode == true);
    }
    SECTION("--show-fid-values enables FormID display") {
        // ...
    }
}
```

**Patterns:**
- `TEST_CASE("description", "[tag]")` for top-level tests
- `SECTION("...")` for sub-cases within a test
- `REQUIRE(...)` for assertions (test fails immediately on false)
- Helper structs (e.g., `ArgvBuilder`) defined in test files for repeated setup
- Tests only cover bridge-free components; CXX bridge components are tested via PowerShell integration tests

## Node/Bun Test Framework

**Runner (primary):** Bun test (`bun test`)

**Runner (secondary):** Node.js `node:test` module — `__test__/runtime.node.test.mjs` verifies the binding also works with vanilla Node

**Config:** `package.json` scripts

**Run Commands:**
```bash
cd ClassicLib-rs/node-bindings/classic-node
bun run test:bun         # Run all bun tests
bun run test:node        # Run Node.js runtime test
bun run test             # Alias for test:bun
```

## Node Test File Organization

**Location:** `ClassicLib-rs/node-bindings/classic-node/__test__/`

**Naming:** `<module>.spec.ts` (e.g., `config.spec.ts`, `scanlog.spec.ts`, `parity_tier1.spec.ts`)

**Special files:**
- `parity_tier1.spec.ts` — cross-module parity gate; verifies all binding surfaces match expected behavior
- `regression_drift.spec.ts` — reads `index.d.ts` to verify type signature stability
- `runtime.node.test.mjs` — vanilla Node.js compatibility test

**Fixtures location:** `ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/`

```
__test__/
├── config.spec.ts
├── scanlog.spec.ts
├── parity_tier1.spec.ts
├── regression_drift.spec.ts
├── runtime.node.test.mjs
└── fixtures/
    ├── cli.fixtures.ts
    ├── runtime_coverage_registry.json
    ├── runtime_coverage_registry.ts
    ├── tier1_parity.fixtures.ts
    └── tier1_regression.fixtures.ts
```

## Node Test Structure

```typescript
import { describe, test, expect, beforeEach } from "bun:test";
import { YamlData, createYamlDataFromContent, clearYamlCache } from "../index.js";
import { PARITY_MAIN_YAML, PARITY_GAME_YAML, PARITY_IGNORE_YAML } from "./fixtures/tier1_parity.fixtures";

const THIS_SUITE = "ClassicLib-rs/node-bindings/classic-node/__test__/config.spec.ts";

describe("YamlData construction", () => {
  beforeEach(() => {
    clearYamlCache();
  });

  test("fromYamlContent creates a valid instance", () => {
    const data = YamlData.fromYamlContent(MAIN_YAML, GAME_YAML, IGNORE_YAML, "Fallout4", "auto");
    expect(data).toBeDefined();
    expect(data.classicVersion).toBe("7.31.0");
  });

  test("fromYamlContent throws on invalid YAML", () => {
    expect(() =>
      YamlData.fromYamlContent("{ invalid: yaml: }}}",  GAME_YAML, IGNORE_YAML, "Fallout4", "auto")
    ).toThrow(/Failed to parse main YAML:/);
  });

  test("fromYamlContent classifies parse failures as InvalidArg", () => {
    try {
      YamlData.fromYamlContent("{ invalid }}}",  GAME_YAML, IGNORE_YAML, "Fallout4", "auto");
      throw new Error("expected parse failure");
    } catch (err) {
      const error = err as Error & { code?: string };
      expect(error.code).toBe("InvalidArg");
    }
  });
});
```

**Patterns:**
- `THIS_SUITE` constant at the top of each spec file (suite identifier for coverage registry)
- `beforeEach(() => { clearYamlCache(); })` to isolate cache state between tests
- Temp directories created with `mkdtempSync(join(tmpdir(), "prefix-"))` and cleaned with `rmSync(..., { recursive: true })`
- Error testing: use both `expect(...).toThrow(/pattern/)` and try/catch for `error.code` inspection

## Node Fixtures

**YAML content fixtures** — `tier1_parity.fixtures.ts`:
```typescript
export const PARITY_MAIN_YAML = `
CLASSIC_Info:
  version: "9.0.0"
`;

export const scanlogConfigCases = [
  { id: "fallout4-non-vr-defaults", game: "Fallout4", gameVersion: "auto",
    expected: { crashgenName: "", xseAcronym: "", classicVersion: "CLASSIC" } },
];
```

**Runtime coverage registry** — `runtime_coverage_registry.json`:
JSON file listing test coverage entries. The parity spec queries it to decide which test suites to activate. New test coverage entries should be added to this registry.

```typescript
import { getRuntimeCoverageEntries } from "./fixtures/runtime_coverage_registry";
const activeCoverageCases = new Set(
  getRuntimeCoverageEntries(THIS_SUITE).map(e => e.testCaseId).filter(Boolean)
);
```

## Python Test Framework

**Runner:** pytest

**Run Commands:**
```bash
uv run pytest ClassicLib-rs/python-bindings/tests -q
```

**Parity check:**
```bash
python tools/python_api_parity/check_parity_gate.py --repo-root .
```

## Python Test File Organization

**Location:** `ClassicLib-rs/python-bindings/tests/`

**Naming:** `test_*.py`

**Fixtures location:** `ClassicLib-rs/python-bindings/tests/fixtures/`

```
tests/
├── __init__.py
├── test_binding_coverage_tooling.py
├── test_parity_gate_tooling.py
├── test_python_parity_tooling.py
├── test_tier1_parity_smoke.py
└── fixtures/
    ├── __init__.py
    ├── runtime_coverage_registry.json
    ├── runtime_coverage_registry.py
    └── tier1_parity_fixtures.py
```

## Python Test Structure

```python
"""Registry-driven runtime parity smoke tests for maintained Python bindings."""
from __future__ import annotations
import pytest
from .fixtures.tier1_parity_fixtures import PARITY_MAIN_YAML, PARITY_GAME_YAML, PARITY_IGNORE_YAML

THIS_SUITE = "ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py"

def test_imports_and_versions() -> None:
    import classic_config
    assert isinstance(classic_config.__version__, str)

def _run_config_tier1_smoke(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import classic_config
    data = classic_config.YamlData.from_yaml_content(
        PARITY_MAIN_YAML, PARITY_GAME_YAML, PARITY_IGNORE_YAML, "Fallout4", "auto"
    )
    assert data.classic_version == "9.0.0"

    with pytest.raises(classic_config.RustConfigParseError) as exc_info:
        classic_config.YamlData.from_yaml_content("{ invalid }}}",  ...)
    assert "Failed to parse main YAML:" in str(exc_info.value)
```

**Patterns:**
- `THIS_SUITE` constant at top of each test file
- `tmp_path: Path` pytest fixture for temp directories (no manual cleanup needed)
- `monkeypatch` fixture for environment variable manipulation
- `pytest.raises(ExceptionClass)` with `str(exc_info.value)` inspection
- Helper functions prefixed with `_` to indicate they are not direct test functions

## Python Fixtures

**YAML content** — `tier1_parity_fixtures.py`:
```python
PARITY_MAIN_YAML = """
CLASSIC_Info:
  version: "9.0.0"
"""
PARITY_GAME_YAML = """
Game_Info:
  XSE_Acronym: "F4SE"
"""
```

**Note:** Python and Node parity fixtures are maintained in sync to catch cross-binding divergence.

## Coverage

**Rust:**
- Tool: `cargo-llvm-cov` (must be installed)
- Target: 60% line coverage (enforced by `coverage_summary.ps1 -Threshold 60`)
- PyO3 binding crates are excluded from the test run but their source is included in reports if any coverage data is available

**Node:**
- No enforced coverage gate currently; parity coverage is tracked via `runtime_coverage_registry.json`

**Python:**
- Parity coverage tracked via `runtime_coverage_registry.json` (same structure as Node)
- `test_binding_coverage_tooling.py` tests the coverage tooling itself

## Test Types

**Unit Tests (Rust inline):**
- Scope: Single struct/function behavior in isolation
- Location: `#[cfg(test)]` mod at end of source file
- Use real data (temp files, inline strings), never mocks

**Integration Tests (Rust separate files):**
- Scope: Cross-component workflows (e.g., loading config from YAML files in temp dirs)
- Location: `tests/integration_tests.rs`
- Use `tempdir()` for file system isolation
- Group by workflow domain using nested `mod` blocks

**Parity Tests (Node + Python):**
- Scope: Verify binding surfaces match expected Rust core behavior
- Location: `parity_tier1.spec.ts`, `test_tier1_parity_smoke.py`
- Fixtures shared via `tier1_parity.fixtures.ts` / `tier1_parity_fixtures.py`
- Coverage-registry-gated: tests only run when registered in `runtime_coverage_registry.json`

**Regression / Drift Tests (Node):**
- Scope: Verify type signature stability in `index.d.ts`
- Location: `regression_drift.spec.ts`
- Reads the actual `index.d.ts` file and asserts specific signature strings are present

**C++ Unit Tests:**
- Scope: Bridge-free C++ components (CliArgs, ProgressDisplay, ThreadPool)
- Framework: Catch2 with `TEST_CASE` / `SECTION`
- Components requiring Rust CXX bridge are covered by PowerShell integration tests only

**Integration/E2E Tests (PowerShell):**
- Run via `build_cli.ps1 -Test -IntegrationTestName "test name"`
- Cover scenarios that cause `std::exit()` (e.g., mixed `--scan-path` + positional args)

## Common Patterns

**Async Testing (Rust):**
```rust
#[tokio::test]
async fn test_concurrent_config_loading() {
    let mut handles = Vec::new();
    for _ in 0..4 {
        let dirs = base_dirs.clone();
        handles.push(tokio::spawn(async move {
            YamlDataCore::load_from_yaml_files(dirs, "Fallout4".to_string(), "auto".to_string()).await
        }));
    }
    for handle in handles {
        let result = handle.await.expect("Task should complete");
        let config = result.expect("Config load should succeed");
        assert_eq!(config.classic_version, "7.31.0");
    }
}
```

**Error Testing (Rust):**
```rust
#[test]
fn test_invalid_yaml_error() {
    let result = YamlDataCore::from_yaml_content("{ invalid: yaml: }}}",  game, ignore, "Fallout4", "auto");
    assert!(result.is_err());
    match result {
        Err(ConfigError::ParseError { context, .. }) => {
            assert!(context.contains("main"), "Should mention main YAML");
        }
        Err(e) => panic!("Expected ParseError, got {:?}", e),
        Ok(_) => panic!("Should fail with invalid YAML"),
    }
}
```

**Serial Tests (Rust — for global state):**
```rust
use serial_test::serial;

#[serial]
#[tokio::test]
async fn test_that_modifies_global_registry() {
    // ...
}
```

**Error Testing (Node):**
```typescript
test("classifies parse failures as InvalidArg", () => {
  try {
    YamlData.fromYamlContent("{ invalid }}}",  GAME_YAML, IGNORE_YAML, "Fallout4", "auto");
    throw new Error("expected parse failure");
  } catch (err) {
    const error = err as Error & { code?: string };
    expect(error.code).toBe("InvalidArg");
    expect(error.message).toContain("Failed to parse main YAML:");
  }
});
```

---

*Testing analysis: 2026-04-04*
