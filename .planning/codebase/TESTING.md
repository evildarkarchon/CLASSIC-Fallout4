# Testing Patterns

**Analysis Date:** 2026-03-30

## Test Framework Overview

This codebase has four parallel test layers, one per language:

| Layer | Framework | Location |
|---|---|---|
| Rust | `cargo test` (built-in) | `ClassicLib-rs/` |
| C++ CLI | Catch2 v3 | `classic-cli/tests/` |
| C++ GUI | Qt Test | `classic-gui/tests/` |
| Node/Bun | `bun:test` | `ClassicLib-rs/node-bindings/classic-node/__test__/` |
| Python | pytest | `ClassicLib-rs/python-bindings/tests/` |

---

## Rust Tests

### Test Runner

**Runner:** `cargo test`
**Config:** `ClassicLib-rs/Cargo.toml` workspace config; no separate test config file

**Run Commands:**
```bash
# All workspace tests
cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml

# Single crate
cargo test --manifest-path ClassicLib-rs/Cargo.toml -p classic-config-core

# Coverage (uses cargo-llvm-cov via PowerShell wrapper)
pwsh -ExecutionPolicy Bypass -File ClassicLib-rs/coverage_report.ps1
pwsh -ExecutionPolicy Bypass -File ClassicLib-rs/coverage_report.ps1 -Package classic-scanlog-core
```

### Test File Organization

**Two patterns coexist:**

1. **Inline unit tests** (`#[cfg(test)]` module at bottom of source file):
   - Located in the same `.rs` file as the code being tested
   - Used in almost all crates: `classic-file-io-core/src/core.rs`, `classic-file-io-core/src/backup.rs`, `classic-file-io-core/src/hash.rs`, `classic-constants-core/src/lib.rs`, `classic-crashgen-settings-core/src/lib.rs`, `classic-database-core/src/pool_sqlx.rs`, `classic-message-core/src/*.rs`, `classic-path-core/src/*.rs`

2. **Separate integration test files** (in `tests/` directory):
   - `ClassicLib-rs/business-logic/classic-config-core/tests/integration_tests.rs`
   - `ClassicLib-rs/business-logic/classic-database-core/tests/integration_tests.rs`
   - `ClassicLib-rs/business-logic/classic-yaml-core/tests/integration_tests.rs`
   - `ClassicLib-rs/foundation/classic-shared-core/tests/test_path_lru.rs`
   - `ClassicLib-rs/foundation/classic-shared-core/tests/test_rolling_stats.rs`
   - `ClassicLib-rs/ui-applications/classic-tui/tests/event_tests.rs`
   - `ClassicLib-rs/ui-applications/classic-tui/tests/render_tests.rs`

**Naming:**
- Unit test functions: `test_<what_is_tested>` pattern: `test_rolling_stats_basic`, `test_lru_cache_bounded`
- Integration test functions: longer descriptive names: `test_complete_config_load_workflow`, `test_from_yaml_content_merges_multiple_documents_per_input`

### Test Suite Structure

**Integration tests use nested modules** organized by concern:
```rust
// integration_tests.rs pattern
mod config_loading_workflows {
    use super::*;
    #[tokio::test]
    async fn test_complete_config_load_workflow() { ... }
}

mod error_handling_workflows {
    use super::*;
    #[test]
    fn test_invalid_yaml_error() { ... }
}

mod parallel_loading {
    use super::*;
    #[tokio::test]
    async fn test_concurrent_config_loading() { ... }
}

mod clone_debug {
    use super::*;
    #[test]
    fn test_config_clone() { ... }
}
```

**Section dividers** using `=` comments are used to group tests:
```rust
// ============================================================================
// Test Data Fixtures
// ============================================================================

// ============================================================================
// Complete Configuration Loading Workflow Tests
// ============================================================================
```

### Async Testing

Use `#[tokio::test]` for async test functions. The Tokio runtime is created per test:
```rust
#[tokio::test]
async fn test_complete_config_load_workflow() {
    let temp_dir = tempdir().expect("Failed to create temp dir");
    let config = YamlDataCore::load_from_yaml_files(yaml_dirs, ...)
        .await
        .expect("Config load should succeed");
    assert_eq!(config.classic_version, "7.31.0");
}
```

**Concurrent test isolation:** The `serial_test` crate is used (`#[serial]`) when tests modify global state such as metrics:
```rust
use serial_test::serial;

#[test]
#[serial]
fn test_rolling_stats_basic() {
    let metrics = get_global_metrics();
    metrics.clear();
    // ...
}
```

### Fixtures and Factories

**Inline fixture functions** that return `&'static str` YAML content are the primary pattern:
```rust
// Found in: classic-config-core/tests/integration_tests.rs
fn minimal_main_yaml() -> &'static str {
    r#"
CLASSIC_Info:
  version: "7.31.0"
  version_date: "2024-01-15"
"#
}

fn minimal_game_yaml() -> &'static str { ... }
fn minimal_ignore_yaml() -> &'static str { ... }
```

**`tempfile` crate** for temporary directories and files:
```rust
use tempfile::{tempdir, NamedTempFile};

let temp_dir = tempdir().expect("Failed to create temp dir");
let databases_dir = temp_dir.path().join("databases");
fs::create_dir_all(&databases_dir).expect("Failed to create databases dir");
fs::write(databases_dir.join("CLASSIC Main.yaml"), minimal_main_yaml())
    .expect("Failed to write main YAML");
```

**Database fixtures:** Helper function pattern for SQLite test databases:
```rust
// Found in: classic-database-core/tests/integration_tests.rs
async fn create_test_database(
    table_name: &str,
    entries: &[(&str, &str, &str)],
) -> Result<(NamedTempFile, PathBuf), DatabaseError> { ... }
```

### Mocking

**No mock framework used.** Rust tests rely on:
- Real temporary files and directories via `tempfile`
- Fixtures providing known-good YAML content strings
- Behavior injection through constructor arguments (e.g., `BackupManager::new(game_root, None)`)
- Global state cleared explicitly between tests (e.g., `clear_global_yaml_cache()`, `FileHasher::clear_cache()`)

### Assertions

**Standard `assert!` / `assert_eq!` / `assert_ne!`** with descriptive messages:
```rust
assert_eq!(config.classic_version, "7.31.0");
assert!(
    cache_size <= 10,
    "Cache should not exceed max size: {} <= 10",
    cache_size
);
```

**Error variant matching** using `match` with panic fallthrough:
```rust
match result {
    Err(ConfigError::IOError { context, .. }) => {
        assert!(context.contains("not found") || context.contains("YAML file"));
    }
    Err(e) => panic!("Expected IOError, got {:?}", e),
    Ok(_) => panic!("Should fail with missing files"),
}
```

### Coverage

**Tool:** `cargo-llvm-cov` via `ClassicLib-rs/coverage_report.ps1`

**Reports generated:** HTML, JSON, and lcov formats

**Exclusions:** PyO3 binding crates excluded from test run (require Python DLL at runtime); generated code (Slint bindings) excluded from metrics

**Commands:**
```bash
# Workspace-wide
pwsh -ExecutionPolicy Bypass -File ClassicLib-rs/coverage_report.ps1

# Per-crate
pwsh -ExecutionPolicy Bypass -File ClassicLib-rs/coverage_report.ps1 -Package classic-config-core

# Clean first
pwsh -ExecutionPolicy Bypass -File ClassicLib-rs/coverage_report.ps1 -Clean
```

### Doc Tests

**Extensively used** in Rust crates. Public functions have `# Examples` sections with runnable doc tests:
```rust
/// # Example
/// ```rust,no_run
/// use classic_file_io_core::hash::FileHasher;
/// let hash = FileHasher::hash_file(Path::new("data.bin"))?;
/// assert_eq!(hash.len(), 64);
/// # Ok::<(), Box<dyn std::error::Error>>(())
/// ```
```

`no_run` is used when the example requires a real filesystem path. `rust,no_run` is the standard annotation. Plain `rust` blocks are runnable and verified by `cargo test`.

---

## C++ CLI Tests (Catch2)

### Test Runner

**Framework:** Catch2 v3 (from vcpkg: `catch2`)
**Config:** `classic-cli/CMakeLists.txt` — tests registered with `catch_discover_tests()`

**Run Commands:**
```bash
# Run all CLI tests
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test

# Run specific test by name
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test -CTestName "CliArgs defaults"

# Integration tests
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test -IntegrationTestName help,version
```

**Important:** Never invoke test binaries or raw `ctest` directly. Always use `build_cli.ps1 -Test`.

### Test File Organization

**Location:** `classic-cli/tests/`
**Naming:** `test_<component>.cpp`: `test_cli_args.cpp`, `test_thread_pool.cpp`, `test_progress.cpp`

**Scope:** Only components that do NOT depend on the Rust CXX bridge are covered. Bridge-dependent code is excluded by design (note in `CMakeLists.txt`).

### Test Structure

```cpp
// test_cli_args.cpp pattern

TEST_CASE("CliArgs defaults", "[cli_args]") {
    ArgvBuilder ab({"classic-cli"});
    CliArgs args = parse_args(ab.argc(), ab.argv());
    REQUIRE(args.game == "Fallout4");
    REQUIRE(args.max_concurrent == 0);
}

TEST_CASE("CliArgs game selection", "[cli_args]") {
    SECTION("Fallout4 (explicit)") {
        ArgvBuilder ab({"classic-cli", "--game", "Fallout4"});
        CliArgs args = parse_args(ab.argc(), ab.argv());
        REQUIRE(args.game == "Fallout4");
    }

    SECTION("Skyrim") {
        ArgvBuilder ab({"classic-cli", "--game", "Skyrim"});
        CliArgs args = parse_args(ab.argc(), ab.argv());
        REQUIRE(args.game == "Skyrim");
    }
}
```

**Tags:** `[cli_args]`, `[thread_pool]`, `[progress]` — match filename

**SECTION blocks** used for related variations of the same `TEST_CASE`.

**Assertions:** `REQUIRE` (terminates test on failure), not `CHECK`.

### Fixtures and Helpers

**Helper structs** local to test files:
```cpp
struct ArgvBuilder {
    std::vector<std::string> args;
    std::vector<char*> ptrs;
    explicit ArgvBuilder(std::initializer_list<std::string> list) : args(list) { ... }
    int argc() const { return static_cast<int>(ptrs.size()); }
    char** argv() { return ptrs.data(); }
};
```

**Factory functions** in anonymous namespaces in GUI tests:
```cpp
namespace {
classic::scanner::BatchProgressEvent makeEvent(
    classic::scanner::BatchProgressEventKind eventKind,
    classic::scanner::BatchProgressPhase phase,
    std::uint32_t inputIndex,
    ...) { ... }
}
```

---

## C++ GUI Tests (Qt Test)

### Test Runner

**Framework:** Qt Test (`Qt6::Test`)
**Config:** `classic-gui/tests/CMakeLists.txt`

**Run Commands:**
```bash
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test -CTestName "test name"
```

### Test File Organization

**Location:** `classic-gui/tests/`
**Naming:** `test_<component>.cpp`: `test_signalhub.cpp`, `test_scan_progress_model.cpp`, `test_mainwindow_geometry.cpp`

**Files:**
- `test_mainwindow_geometry.cpp`
- `test_markdownviewer.cpp`
- `test_reportlistwidget.cpp`
- `test_reportmetadatawidget.cpp`
- `test_resultscontroller.cpp`
- `test_scanworker_cancellation.cpp`
- `test_scan_progress_model.cpp`
- `test_scan_settings_wiring.cpp`
- `test_signalhub.cpp`
- `test_threadmanager.cpp`

### Test Structure

Qt Test uses class-based test organization:
```cpp
class SignalHubTests : public QObject {
    Q_OBJECT

private slots:
    void instance_returns_same_singleton_reference();
    void scanStarted_signal_is_emitted();
    void scanProgress_signal_carries_expected_payload();
};

void SignalHubTests::scanStarted_signal_is_emitted()
{
    SignalHub& hub = SignalHub::instance();
    QSignalSpy spy(&hub, &SignalHub::scanStarted);
    const bool invoked = QMetaObject::invokeMethod(&hub, "scanStarted", Qt::DirectConnection);
    QVERIFY(invoked);
    QCOMPARE(spy.count(), 1);
}

QTEST_GUILESS_MAIN(SignalHubTests)
#include "test_signalhub.moc"
```

**Platform:** Tests run headless using `offscreen` QPA platform (`QT_QPA_PLATFORM=offscreen`).

**Qt Test assertions:** `QCOMPARE`, `QVERIFY`, `QVERIFY2` (with message)

**Signal testing:** `QSignalSpy` used to capture and verify Qt signals

---

## Node/Bun Tests

### Test Runner

**Framework:** `bun:test`
**Config:** `ClassicLib-rs/node-bindings/classic-node/package.json`

**Run Commands:**
```bash
# From ClassicLib-rs/node-bindings/classic-node/
bun install && bun run build
bun run test:bun          # Bun test runner
bun run test:node         # Node.js built-in test runner
bun run parity:gate:local # API parity check + dts freshness
```

### Test File Organization

**Location:** `ClassicLib-rs/node-bindings/classic-node/__test__/`
**Naming:** `<feature>.spec.ts`

**Files:**
- `cli.spec.ts`
- `config.spec.ts`
- `constants.spec.ts`
- `database.spec.ts`
- `fileio.spec.ts`
- `message.spec.ts`
- `parity_tier1.spec.ts`
- `path.spec.ts`
- `regression_drift.spec.ts`
- `resource.spec.ts`
- `runtime.node.test.mjs` (Node.js native test runner)
- `scangame.spec.ts`
- `scanlog.spec.ts`

### Test Structure

```typescript
import { describe, test, expect, beforeEach, afterEach } from "bun:test";

describe("YamlData construction", () => {
  beforeEach(() => {
    clearYamlCache();
  });

  test("fromYamlContent creates a valid instance", () => {
    const data = YamlData.fromYamlContent(MAIN_YAML, GAME_YAML, IGNORE_YAML, "Fallout4", "auto");
    expect(data).toBeDefined();
    expect(data.classicVersion).toBe("7.31.0");
  });
});
```

**Suite identifier:** `THIS_SUITE` constant at top of each file for error reporting:
```typescript
const THIS_SUITE = "ClassicLib-rs/node-bindings/classic-node/__test__/config.spec.ts";
```

### Fixtures and Factories

**SCREAMING_SNAKE_CASE string constants** for YAML content at file scope:
```typescript
const MAIN_YAML = `
CLASSIC_Info:
  version: "7.31.0"
...`;

const GAME_YAML = `...`;
const IGNORE_YAML = `...`;
```

**Temp directories** using Node.js `fs` primitives:
```typescript
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";

let tmpDir: string;
beforeEach(() => { tmpDir = mkdtempSync(join(tmpdir(), "classic-test-")); });
afterEach(() => { rmSync(tmpDir, { recursive: true, force: true }); });
```

### Parity Testing

**Tier-1 parity smoke tests** in `parity_tier1.spec.ts` verify that the Node binding exposes the same API surface as Python bindings. These import nearly every exported symbol and call each function/constructor at least once.

**Parity gate tool:** `bun run parity:gate:local` runs `tools/node_api_parity/check_parity_gate.py` and `tools/node_api_parity/check_dts_freshness.py` to verify `index.d.ts` freshness and API baseline match.

---

## Python Tests

### Test Runner

**Framework:** pytest
**Run Command:**
```bash
uv run pytest ClassicLib-rs/python-bindings/tests -q
```

**Parity gate:**
```bash
python tools/python_api_parity/check_parity_gate.py --repo-root .
```

### Test File Organization

**Location:** `ClassicLib-rs/python-bindings/tests/`
**Files:**
- `test_binding_coverage_tooling.py`
- `test_parity_gate_tooling.py`
- `test_python_parity_tooling.py`
- `test_tier1_parity_smoke.py`
- `fixtures/__init__.py`
- `fixtures/runtime_coverage_registry.py`
- `fixtures/tier1_parity_fixtures.py`

### Test Structure

```python
def test_imports_and_versions() -> None:
    import classic_config
    import classic_scanlog
    assert isinstance(classic_config.__version__, str)
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("classic_pybridge")
```

**Fixtures module:** YAML string constants kept in `fixtures/tier1_parity_fixtures.py` and imported across test files:
```python
from .fixtures.tier1_parity_fixtures import (
    PARITY_GAME_YAML,
    PARITY_IGNORE_YAML,
    PARITY_MAIN_YAML,
)
```

**pytest fixtures:** `tmp_path` (built-in), `monkeypatch` for environment/import state manipulation

**Error testing:**
```python
with pytest.raises(classic_config.RustConfigParseError) as exc_info:
    classic_config.YamlData.from_yaml_content(invalid_yaml, ...)
```

---

## Integration Test Patterns (Cross-Language)

### Sample Log Fixtures

Real crash log content is provided as inline string literals in each binding's test files. Example in `scanlog.spec.ts`:
```typescript
const SAMPLE_CRASH_LOG = `Fallout 4 v1.10.163
Buffout 4 v1.28.6
Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512 ...`;
```

The `sample_logs/FO4/` git submodule provides authoritative test fixtures for the full scan workflow.

### TUI Tests

`ClassicLib-rs/ui-applications/classic-tui/tests/event_tests.rs` uses `ratatui::backend::TestBackend` for headless rendering:
```rust
let backend = TestBackend::new(120, 40);
let mut terminal = Terminal::new(backend).expect("terminal");
terminal.draw(|frame| app.render(frame)).expect("draw frame");
```

`App::new_for_testing()` factory creates an app instance without network or filesystem side effects.

---

*Testing analysis: 2026-03-30*
