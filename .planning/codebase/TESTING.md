# Testing Patterns

**Analysis Date:** 2026-04-14

## Test Framework

**Runner:**
- Rust built-in test harness with `#[test]` and `#[tokio::test]` across repo-root crate `tests/*.rs`, e.g. `foundation/classic-shared-core/tests/test_rolling_stats.rs` and `business-logic/classic-database-core/tests/integration_tests.rs`.
- Config: repo-root workspace manifest `Cargo.toml`; CI entrypoints in `.github/workflows/ci-rust.yml`.
- Catch2 via PowerShell build wrappers for `classic-cli/` in `classic-cli/CMakeLists.txt`.
- Qt Test via PowerShell build wrappers for `classic-gui/tests/` in `classic-gui/tests/CMakeLists.txt`.
- Pytest for Python bindings and parity tooling in `python-bindings/tests/`, `tools/python_api_parity/tests/`, `tools/node_api_parity/tests/`, and `tools/cxx_api_parity/tests/`.
- Bun test for TypeScript binding tests in `node-bindings/classic-node/__test__/*.spec.ts`.
- Node built-in `node:test` for runtime smoke coverage in `node-bindings/classic-node/__test__/runtime.node.test.mjs`.
- Plain PowerShell assertion scripts for script contract tests in `tests/powershell/*.test.ps1`.
- Python `unittest` is also used for planning audits in `tests/planning/test_phase03_validation.py`, `test_phase04_validation.py`, `test_phase05_validation.py`, `test_phase10_validation.py`, and `test_phase11_validation.py`.

**Assertion Library:**
- Rust: standard `assert!`, `assert_eq!`, `expect(...)`.
- C++ CLI: Catch2 macros such as `TEST_CASE`, `SECTION`, and `REQUIRE` in `classic-cli/tests/test_cli_args.cpp`.
- C++ GUI: Qt Test macros such as `QCOMPARE` and `QVERIFY` in `classic-gui/tests/test_signalhub.cpp`.
- Python: plain `assert`, `pytest.raises`, and `unittest.TestCase` helpers.
- TypeScript/Bun: `expect(...).toBe(...)`, `toEqual(...)`, `toThrow(...)`, and async `rejects` in `node-bindings/classic-node/__test__/config.spec.ts`.
- Node runtime smoke tests: `node:assert/strict` in `node-bindings/classic-node/__test__/runtime.node.test.mjs`.

**Run Commands:**
```bash
cargo test --workspace --release                                # Run Rust workspace tests
cargo test --workspace --release --all-features                 # Run Rust tests with all features
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test   # Run classic-cli Catch2 + integration tests
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test   # Run classic-gui Qt/CTest tests
uv run --python python-bindings/.venv/Scripts/python.exe python -m pytest python-bindings/tests -q  # Run Python binding smoke tests
bun run test:bun                                                # Run Bun TypeScript tests
bun run test:node                                               # Run Node runtime smoke tests
bun run parity:gate                                             # Run Node parity gate
python tools/python_api_parity/check_parity_gate.py --repo-root .  # Run Python parity gate
```

## Test File Organization

**Location:**
- Rust crate integration tests live in per-crate `tests/` directories, e.g. `business-logic/classic-database-core/tests/` and `ui-applications/classic-tui/tests/`.
- Some Rust unit tests also live inline under `#[cfg(test)]`, e.g. `foundation/classic-shared-core/src/lib.rs`.
- C++ CLI tests live in `classic-cli/tests/`.
- C++ GUI tests live in `classic-gui/tests/` and are registered in `classic-gui/tests/CMakeLists.txt`.
- Python binding tests live in `python-bindings/tests/` with shared fixtures in `python-bindings/tests/fixtures/`.
- Python parity-tool suites live under `tools/python_api_parity/tests/`, `tools/node_api_parity/tests/`, and `tools/cxx_api_parity/tests/`.
- Node/Bun tests live in `node-bindings/classic-node/__test__/` with reusable fixtures in `node-bindings/classic-node/__test__/fixtures/`.
- Planning audits live in `tests/planning/`.
- PowerShell test scripts live in `tests/powershell/`.

**Naming:**
- Rust integration tests use descriptive snake_case filenames, e.g. `linux_proton_docs_path.rs`, `integration_tests.rs`, and `event_tests.rs`.
- C++ CLI test files use `test_*.cpp`, e.g. `classic-cli/tests/test_cli_args.cpp`.
- C++ GUI tests also use `test_*.cpp`, e.g. `classic-gui/tests/test_signalhub.cpp`.
- Python tests use `test_*.py` everywhere.
- Bun tests use `*.spec.ts`, e.g. `node-bindings/classic-node/__test__/parity_tier1.spec.ts`.
- Node native runtime smoke uses `runtime.node.test.mjs`.
- PowerShell tests use `*.test.ps1`.

**Structure:**
```text
<repo-root crate>/tests/*.rs
python-bindings/tests/test_*.py
python-bindings/tests/fixtures/*
node-bindings/classic-node/__test__/*.spec.ts
node-bindings/classic-node/__test__/fixtures/*
classic-cli/tests/test_*.cpp
classic-gui/tests/test_*.cpp
tools/*_api_parity/tests/test_*.py
tests/planning/test_*.py
tests/powershell/*.test.ps1
```

## Test Structure

**Suite Organization:**
```typescript
// `node-bindings/classic-node/__test__/config.spec.ts`
describe("YamlData construction", () => {
  beforeEach(() => {
    clearYamlCache();
  });

  test("fromYamlContent creates a valid instance", () => {
    const data = YamlData.fromYamlContent(MAIN_YAML, GAME_YAML, IGNORE_YAML, "Fallout4", "auto");
    expect(data.classicVersion).toBe("7.31.0");
  });
});
```

**Patterns:**
- Rust groups related workflows with nested modules in integration tests, e.g. `mod database_workflows` and `mod cache_workflows` in `business-logic/classic-database-core/tests/integration_tests.rs`.
- C++ CLI tests use `TEST_CASE` plus `SECTION` to cover permutations in one file, e.g. `classic-cli/tests/test_cli_args.cpp`.
- C++ GUI tests typically define a single `QObject` test class with `private slots:` and end with `QTEST_GUILESS_MAIN(...)`, e.g. `classic-gui/tests/test_signalhub.cpp`.
- Python smoke tests are heavily scenario-focused and often include long contract explanations at the top of the file, e.g. `python-bindings/tests/test_promoted_config_smoke.py`.
- Planning audits use `unittest.TestCase` and `self.subTest(...)` to validate many required fragments without duplicating setup, e.g. `tests/planning/test_phase10_validation.py` and `tests/planning/test_phase11_validation.py`.
- PowerShell tests parse target scripts via AST and assert on metadata/structure instead of executing full toolchains, e.g. `tests/powershell/cpp_build_scripts.test.ps1` and `tests/powershell/enter_vs_dev_shell.test.ps1`.

## Mocking

**Framework:**
- Python: `pytest` monkeypatch fixtures for module and argv replacement.
- TypeScript/Bun: mostly real-object tests with temp directories; minimal mocking.
- Rust: lightweight function injection and in-memory/test backends rather than heavy mock frameworks.
- C++ GUI: signal spying via `QSignalSpy` instead of mock objects.

**Patterns:**
```python
# `python-bindings/tests/test_parity_gate_tooling.py`
monkeypatch.setattr(module, "parse_rust_surface", lambda *args, **kwargs: {"symbols": []})
monkeypatch.setattr(module, "generate_diff_report", lambda *args, **kwargs: minimal_diff_report(binding))
monkeypatch.setattr(sys, "argv", argv)
```

```rust
// `ui-applications/classic-tui/tests/event_tests.rs`
fn copy_writer_test(_text: &str) -> Result<(), String> {
    COPY_CALLED.store(true, Ordering::SeqCst);
    Ok(())
}

app.set_clipboard_writer(copy_writer_test);
```

```cpp
// `classic-gui/tests/test_signalhub.cpp`
QSignalSpy spy(&hub, &SignalHub::scanStarted);
const bool invoked = QMetaObject::invokeMethod(&hub, "scanStarted", Qt::DirectConnection);
QVERIFY(invoked);
QCOMPARE(spy.count(), 1);
```

**What to Mock:**
- Python parity/tool tests replace filesystem-derived manifests, CLI argv, and imported helper modules, as seen in `python-bindings/tests/test_parity_gate_tooling.py` and `tools/node_api_parity/tests/test_validate_contract_surface.py`.
- Rust TUI tests inject callback functions for clipboard and URL behavior in `ui-applications/classic-tui/tests/event_tests.rs`.
- GUI tests observe Qt signals with `QSignalSpy` instead of faking the entire object graph.

**What NOT to Mock:**
- YAML fixture parsing is usually exercised with real YAML strings, not mocks, in `node-bindings/classic-node/__test__/config.spec.ts`, `node-bindings/classic-node/__test__/runtime.node.test.mjs`, and `python-bindings/tests/test_promoted_config_smoke.py`.
- Rust database integration tests use real temporary SQLite databases through `sqlx` in `business-logic/classic-database-core/tests/integration_tests.rs`.
- CLI/build-script tests often inspect real scripts and checked-in contracts directly rather than stubbing them, e.g. `tests/powershell/cpp_build_scripts.test.ps1` and `tools/node_api_parity/tests/test_check_parity_gate.py`.

## Fixtures and Factories

**Test Data:**
```python
# `python-bindings/tests/fixtures/tier1_parity_fixtures.py`
PARITY_MAIN_YAML = """
CLASSIC_Info:
  version: "9.0.0"
"""
```

```typescript
// `node-bindings/classic-node/__test__/fixtures/tier1_parity.fixtures.ts`
export const scanlogConfigCases = [
  { id: "fallout4-non-vr-defaults", game: "Fallout4", gameVersion: "auto", expected: { ... } },
] as const;
```

```rust
// `business-logic/classic-database-core/tests/integration_tests.rs`
async fn create_test_database(table_name: &str, entries: &[(&str, &str, &str)])
    -> Result<(NamedTempFile, PathBuf), DatabaseError> { ... }
```

**Location:**
- Python fixtures: `python-bindings/tests/fixtures/`.
- Node/Bun fixtures: `node-bindings/classic-node/__test__/fixtures/`.
- CXX parity parser fixtures: `tools/cxx_api_parity/tests/fixtures/`.
- Tempfile/tempdir factories are embedded directly in tests when the setup is small, e.g. `createCliWorkspace()` in `node-bindings/classic-node/__test__/runtime.node.test.mjs`.

## Coverage

**Requirements:** None enforced by a dedicated coverage threshold tool were detected.

**View Coverage:**
```bash
Not detected
```

## Test Types

**Unit Tests:**
- Rust unit tests cover pure helpers and low-level behavior inline and per crate, e.g. `foundation/classic-shared-core/src/lib.rs` and `foundation/classic-shared-core/tests/test_rolling_stats.rs`.
- C++ CLI unit coverage is intentionally limited to bridge-free components, and execution must still go through `classic-cli/build_cli.ps1 -Test` rather than raw `ctest`.
- Qt tests validate signal semantics, widgets, and controllers in isolation, e.g. `classic-gui/tests/test_signalhub.cpp` and targets registered in `classic-gui/tests/CMakeLists.txt`; execution goes through `classic-gui/build_gui.ps1 -Test`.
- Python tool tests validate parser and gate logic at the function level, e.g. `tools/cxx_api_parity/tests/test_parser.py` and `tools/node_api_parity/tests/test_validate_contract_surface.py`.

**Integration Tests:**
- Rust integration tests use real backing services or files, e.g. SQLite via `sqlx` in `business-logic/classic-database-core/tests/integration_tests.rs`.
- Node runtime tests execute the built `.node` addon under actual Node in `node-bindings/classic-node/__test__/runtime.node.test.mjs`.
- CLI integration scenarios are executed from `classic-cli/build_cli.ps1 -Test` via `classic-cli/test_cli.ps1`.
- PowerShell script tests validate script signatures and behavior contracts for build wrappers in `tests/powershell/*.test.ps1`.

**E2E Tests:**
- Not used as a separate framework.
- Closest equivalents are CLI scenario runs via `classic-cli/test_cli.ps1`, runtime binding smoke tests in `node-bindings/classic-node/__test__/runtime.node.test.mjs`, and repository planning audits in `tests/planning/`.

## Common Patterns

**Async Testing:**
```rust
// `business-logic/classic-database-core/tests/integration_tests.rs`
#[tokio::test]
async fn test_complete_formid_lookup_workflow() {
    let (_temp_file, db_path) = create_test_database(table_name, &entries)
        .await
        .expect("Failed to create test database");
}
```

```typescript
// `node-bindings/classic-node/__test__/settings.spec.ts`
await expect(loadSettingsAsync("key", missingPath)).rejects.toThrow();
```

**Error Testing:**
```python
# `python-bindings/tests/test_promoted_config_smoke.py`
with pytest.raises((classic_config.RustConfigError, classic_config.RustConfigIOError, classic_config.RustConfigParseError)):
    classic_config.YamlData(["/nonexistent/yaml/dir"], "Fallout4", "auto")
```

```typescript
// `node-bindings/classic-node/__test__/config.spec.ts`
expect(() => YamlData.fromYamlContent("{ invalid: yaml: content: }}}", GAME_YAML, IGNORE_YAML, "Fallout4", "auto")).toThrow(/Failed to parse main YAML:/);
```

```cpp
// `classic-cli/tests/test_cli_args.cpp`
// Exit-path cases are moved to integration tests when CLI11 terminates the process.
// Example note in file: invalid --game values are covered by PowerShell integration tests.
```

## Notable Gaps

- No repo-wide coverage reporter or threshold configuration was detected for Rust, Python, C++, or Bun tests.
- No single top-level command runs every test family; execution is split across Cargo, PowerShell build wrappers, Bun scripts, pytest, and script-specific entrypoints.
- Python binding CI runs `python-bindings/tests` only in `.github/workflows/ci-python-bindings.yml`; parity-tool suites under `tools/*_api_parity/tests/` and planning audits under `tests/planning/` are separate/manual entrypoints.
- Node test coverage is strong on parity fixtures and runtime smoke, but current automation is centered on contract parity plus smoke tests rather than browser/E2E-style flows.
- C++ CLI unit coverage is intentionally limited to bridge-free components; Rust/CXX integration behavior is validated through build/integration scripts rather than a large C++ unit suite.

---

*Testing analysis: 2026-04-14*
