---
name: tdd
description: Test-Driven Development skill for a Rust-first project with Python, C++, and Node.js bindings. Enforces Red-Green-Refactor cycle with Rust-primary testing patterns and binding-layer verification.
---

This skill guides test-driven development for the CLASSIC project. All business logic lives in Rust core crates under `foundation/` and `business-logic/`, in a Cargo workspace rooted at the repository root. Python, C++, and Node.js are binding layers only. Follow the Red-Green-Refactor cycle strictly: write a failing test first, implement minimal code to pass, then refactor while keeping tests green.

## TDD Workflow

### Phase 1: Red (Write Failing Test)

Before writing any implementation code:

1. **Identify the layer** - Is this business logic (Rust) or a binding concern?
2. **Write the test first** - In the correct language for that layer
3. **Run the test** - Verify it fails for the right reason
4. **Commit the failing test** - Document the requirement

> **Rule of thumb**: If the logic could exist without any binding, it belongs in a Rust core crate and should be tested in Rust first.

### Phase 2: Green (Make It Pass)

Write the **minimal** code to make the test pass:

1. **Implement just enough** - No extra features
2. **Run the test** - Verify it passes
3. **Run related tests** - Ensure no regressions

### Phase 3: Refactor (Improve)

With passing tests as a safety net:

1. **Improve code quality** - Readability, performance, patterns
2. **Run all tests** - Maintain green status
3. **Commit the refactor** - Separate from feature commits

## Where to Write Tests

| What you're testing | Language | Location |
|---|---|---|
| Business logic, parsing, analysis | Rust | `#[cfg(test)]` in source or `tests/` dir in crate |
| Cross-crate workflows | Rust | `tests/integration_tests.rs` in the crate |
| PyO3 binding correctness | Python | `tests/rust_integration/` |
| Python-layer orchestration | Python | `tests/` by domain |
| C++ CLI behavior | C++ | `classic-cli/tests/` (Catch2) |
| C++ CLI integration | PowerShell | `classic-cli/test_cli.ps1` |
| Node.js/Bun bindings | TypeScript | NAPI-RS test suite |

## Rust Testing Patterns (Primary)

### Unit Tests (Sibling File)

Unit tests live in a sibling `<stem>_tests.rs` file colocated with the module
under test. See rule 11 in `AGENTS.md` for the workspace-wide rule.

In `src/parser.rs`:

```rust
pub fn parse_formid(hex: &str) -> Result<FormID, ParseError> {
    // implementation
}

#[cfg(test)]
#[path = "parser_tests.rs"]
mod tests;
```

In the sibling `src/parser_tests.rs`:

```rust
use super::*;

#[test]
fn parse_formid_valid_hex() {
    let result = parse_formid("0A001234").unwrap();
    assert_eq!(result.plugin_index, 0x0A);
    assert_eq!(result.local_id, 0x001234);
}

#[test]
fn parse_formid_invalid_hex_returns_error() {
    let result = parse_formid("ZZZZZZZZ");
    assert!(result.is_err());
}
```

### Integration Tests (Cross-Component)

Place in `tests/` directory within each crate. Organize with `mod` blocks:

```rust
// tests/integration_tests.rs
use classic_yaml_core::{YamlOperations, clear_global_yaml_cache};
use tempfile::tempdir;

mod file_workflows {
    use super::*;

    #[test]
    fn load_modify_save_workflow() {
        clear_global_yaml_cache();
        let temp_dir = tempdir().expect("Failed to create temp dir");
        // ...
    }
}

mod concurrent_access {
    use super::*;

    #[test]
    fn concurrent_reads_do_not_panic() {
        // ...
    }
}
```

### Async Rust Tests

Use `#[tokio::test]` for async tests. Remember the ONE RUNTIME RULE -- in tests, `#[tokio::test]` creates its own runtime, which is fine for isolated test execution:

In the parent source file (e.g. `src/io.rs`):

```rust
#[cfg(test)]
#[path = "io_tests.rs"]
mod tests;
```

In the sibling `src/io_tests.rs`:

```rust
use super::*;

#[tokio::test]
async fn async_file_read_returns_content() {
    let result = read_file_async("test_fixture.txt").await.unwrap();
    assert!(!result.is_empty());
}

#[tokio::test]
async fn concurrent_tasks_complete_without_deadlock() {
    let handles: Vec<_> = (0..10)
        .map(|_| tokio::spawn(async { do_work().await }))
        .collect();
    for h in handles {
        h.await.unwrap();
    }
}
```

### Test Naming Convention (Rust)

```rust
// Pattern: <action>_<scenario>_<expected_result>
fn parse_formid_valid_hex_returns_components() { }
fn parse_formid_empty_string_returns_error() { }
fn load_yaml_missing_file_returns_io_error() { }
fn concurrent_writes_preserve_all_entries() { }
```

### Singleton / Cache Cleanup

Always clear global caches at test start to ensure isolation:

```rust
#[test]
fn test_something() {
    clear_global_yaml_cache(); // or equivalent reset function
    // ...
}
```

### Test Execution (Rust)

Run these from the repository root; it is the workspace root, so no `--manifest-path` is needed.

```bash
# All Rust tests
cargo test --workspace

# Specific crate
cargo test -p classic-scanlog-core

# With stdout output
cargo test --workspace -- --nocapture

# Specific test by name
cargo test -p classic-settings-core -- load_modify_save
```

Set `PYO3_PYTHON` first if the command can build a PyO3 crate — see `AGENTS.md`.

## Python Testing Patterns (Binding Layer)

Python tests are binding smoke tests: they verify that the PyO3 surface exposes Rust
functionality correctly and returns the expected types. They are **not** where business
logic gets tested — that belongs in the `-core` crate's Rust tests.

### Layout

Tests live as flat `test_*.py` modules under `python-bindings/tests/`, with shared data
under `python-bindings/tests/fixtures/`. There is no `conftest.py` and no registered
pytest marker set, so do not add `@pytest.mark.*` decorators expecting them to be
selectable.

```python
def test_shared_module_loads():
    """Verify the PyO3 binding imports and exposes its version."""
    import classic_shared

    assert hasattr(classic_shared, "__version__")
```

### Test Execution (Python)

Python tests run against maturin-built wheels, so the build order matters. The full
four-step sequence (pin `PYO3_PYTHON` → `uv sync --inexact` → `rebuild_rust.ps1` →
pytest) is in `CLAUDE.md`; skipping the rebuild fails at collection time with
`ModuleNotFoundError`.

```powershell
# Whole binding suite
uv run --project python-bindings python -m pytest python-bindings/tests -q

# Single file or test
uv run --project python-bindings python -m pytest python-bindings/tests/test_classic_shared_smoke.py -v
uv run --project python-bindings python -m pytest python-bindings/tests/test_classic_shared_smoke.py::test_name -v
```

Use `python -m pytest`, never the `pytest.exe` entrypoint — the config crate anchors
settings lookup to `sys.argv[0]`'s parent.

## C++ Testing Patterns (CLI Frontend)

The C++ CLI (`classic-cli/`) tests bridge-free components using Catch2 v3.

### Unit Tests (Catch2)

```cpp
#include <catch2/catch_test_macros.hpp>
#include "thread_pool.h"

TEST_CASE("ThreadPool submit and wait", "[thread_pool]") {
    ThreadPool pool(2);

    SECTION("single task executes") {
        std::atomic<int> counter{0};
        pool.submit([&] { counter.fetch_add(1); });
        pool.wait_all();
        REQUIRE(counter.load() == 1);
    }

    SECTION("multiple tasks all execute") {
        std::atomic<int> counter{0};
        for (int i = 0; i < 50; ++i) {
            pool.submit([&] { counter.fetch_add(1); });
        }
        pool.wait_all();
        REQUIRE(counter.load() == 50);
    }
}
```

### Tags

Use Catch2 tags to categorize: `[thread_pool]`, `[progress]`, `[cli_args]`

### Test Execution (C++)

```bash
# Build and run via CTest (requires VS Dev Shell)
cmake --preset default
cmake --build build --target classic-cli-tests
ctest --test-dir build --output-on-failure

# Run by tag
.\build\classic-cli-tests.exe [thread_pool]

# Verbose with SECTION names
.\build\classic-cli-tests.exe -s
```

### Integration Tests (PowerShell)

Full CLI binary exercising Rust CXX bridge:

```powershell
.\test_cli.ps1
```

## Anti-Patterns to Avoid

### Never Test Business Logic in Bindings

```python
# WRONG - testing parsing logic in Python
def test_formid_parser_handles_edge_cases():
    result = classic_scanlog.parse_formid("FE000800")
    assert result.is_light_plugin  # This logic belongs in Rust tests

# CORRECT - test that binding exposes the function
def test_formid_parser_binding_callable():
    result = classic_scanlog.parse_formid("0A001234")
    assert result is not None  # Verify binding works
```

### Never Modify Production YAML in Tests

```python
# FORBIDDEN
yaml_settings(str, YAML.Settings, "key", "value")

# CORRECT - use test YAML or mocks
yaml_settings(str, YAML.TEST, "key", "value")
```

### Never Create Fixtures in Python Test Files

```python
# WRONG - fixture in test file
@pytest.fixture
def my_local_fixture():
    return "data"

# CORRECT - add to tests/fixtures/<appropriate_module>.py
```

### Never Test Fallback Paths (Rust Is Mandatory)

```python
# WRONG - testing Python fallback behavior
if not is_rust_accelerated("parser"):
    # test fallback...

# Rust is mandatory. If import fails, the test should fail.
```

### Never Use `.expect()` in Async Bridge Code

In production Slint bridge code, use `BridgeError` and log-and-drop on dispatch failures. In tests, `.unwrap()` / `.expect()` are fine since panics are the desired failure mode.

## TDD Checklist

Before marking a feature complete:

- [ ] Failing test written first (Red)
- [ ] Minimal implementation passes test (Green)
- [ ] Code refactored with tests still passing (Refactor)
- [ ] Business logic tested in Rust (not in bindings)
- [ ] Binding tests verify FFI correctness only
- [ ] Appropriate markers applied (Python) or tags applied (C++)
- [ ] Python fixtures in `tests/fixtures/` (not in test file)
- [ ] Caches/singletons cleaned up in tests
- [ ] No production YAML modifications
- [ ] Tests pass individually AND together
- [ ] `cargo test --workspace` passes
- [ ] `uv run pytest` passes

## References

- `tests/TEST_WRITING_GUIDE.md` - Python test data patterns and crash log formats
- `CLAUDE.md` - Build commands, architecture, and conventions
