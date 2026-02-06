# Phase 27: Test Coverage Evaluation and Improvement - Research

**Researched:** 2026-02-06
**Domain:** Rust test coverage measurement and gap-filling (cargo-llvm-cov)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Coverage Scope & Priorities
- **Rust crates only** -- all crates in the workspace (foundation, business-logic, ui-applications)
- Python testing deferred to a separate future phase
- Slint GUI crate (classic-gui) IS in scope -- test Rust logic behind the GUI
- No pre-identified gap modules -- let coverage tools reveal the gaps

#### Coverage Tooling & Reporting
- **cargo-llvm-cov** as the coverage tool (LLVM native instrumentation, good Windows support)
- **Dual report format**: HTML for local browsing + lcov/cobertura for future CI integration
- **Per-crate breakdown** -- individual coverage numbers for each crate, not just workspace aggregate
- Installation/scripting approach: Claude's discretion

#### Test Strategy by Layer
- **Unit + integration tests** for gap-filling (not unit-only)
- GUI crate: Both direct logic tests AND trait-based mock tests (MockDispatcher, ScanWindowProperties)
- **Exclude generated code** from coverage metrics (Slint bindings, PyO3 generated code)
- **Error paths included** -- test error handling, edge cases, and boundary conditions alongside happy paths

#### Quality Bar Definition
- **60% minimum line coverage** target for all crates
- **Uniform target** -- same bar for every crate, no tiered requirements
- **Advisory only** -- report coverage but don't enforce as CI gate
- **Full coverage push** -- measure, write tests, iterate until all crates meet 60%

### Claude's Discretion
- Coverage tooling installation approach (cargo install vs script)
- Test file organization within each crate
- Prioritization order when filling gaps across crates
- Specific exclusion patterns for generated code in cargo-llvm-cov config

### Deferred Ideas (OUT OF SCOPE)
- Python module test coverage -- separate future phase
- CI enforcement of coverage thresholds -- after baseline is established and stable
</user_constraints>

## Summary

This phase covers establishing Rust test coverage measurement across all 39 crates in the CLASSIC workspace, identifying coverage gaps, and writing tests until every crate reaches 60% line coverage. The workspace already has **cargo-llvm-cov 0.8.3** installed and 916 existing test functions across 85 files, but coverage is unevenly distributed -- some crates (classic-scanlog-core, classic-file-io-core) have extensive inline tests while all 18 Python binding crates have zero Rust tests.

The standard approach is: (1) run a workspace-wide baseline coverage report with generated code excluded, (2) build a per-crate summary script that identifies which crates fall below 60%, (3) systematically fill gaps starting with the largest/most critical crates, (4) iterate until all crates meet the 60% bar. The key challenge is excluding ~85K lines of Slint-generated code and PyO3 procedural macro output from coverage metrics while still measuring the hand-written PyO3 adapter code in `-py` crates.

**Primary recommendation:** Use `cargo llvm-cov --workspace --html --ignore-filename-regex "(target|build|\.slint)" --exclude-from-report <binary-crates>` for baseline measurement, then iterate per-crate with a PowerShell coverage script that produces a gap summary table.

## Standard Stack

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| cargo-llvm-cov | 0.8.3 (installed) | LLVM source-based coverage | Only production-quality Rust coverage tool; uses rustc native instrumentation |
| rustc | 1.91.1 (stable) | Compiler with -C instrument-coverage | Built-in instrumentation support on stable |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| tempfile | 3.24.0 (in workspace) | Temp directories for test fixtures | Integration tests needing file I/O |
| serial_test | 3.2 (in shared-core dev-deps) | Sequential test execution | Tests that modify global state (singletons, dispatchers) |
| tokio (test) | 1.49.0 (in workspace) | Async test runtime | Any test with `#[tokio::test]` for async functions |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| cargo-llvm-cov | cargo-tarpaulin | tarpaulin has weaker Windows support; llvm-cov is already installed |
| JSON parsing for per-crate report | lcov parsing | JSON is easier to script; lcov better for CI integration |

**Installation:** Already installed. No additional cargo install needed.

## Architecture Patterns

### Workspace Crate Inventory (39 crates)

```
Foundation (2 crates):
  classic-shared-core     - 2214 lines, 504 test lines, 17 test files (HAS TESTS)
  classic-shared-py       - 1611 lines, 0 test lines (NO TESTS - has 6 inline test functions)

Business Logic (19 crates):
  classic-scanlog-core    - 11172 lines, 0 separate test files, 186 inline tests (MOST TESTS)
  classic-file-io-core    - 4411 lines, 60 inline tests
  classic-path-core       - 4377 lines, 67 inline tests
  classic-scangame-core   - 4168 lines, 57 inline tests
  classic-version-registry-core - 3168 lines, 63 inline tests
  classic-config-core     - 2137 lines, 674 test lines + 30 inline tests (HAS INTEGRATION TESTS)
  classic-yaml-core       - 2982 lines, 560 test lines + 65 inline tests (HAS INTEGRATION TESTS)
  classic-settings-core   - 1967 lines, 48 inline tests
  classic-database-core   - 1696 lines, 690 test lines + 17 inline tests (HAS INTEGRATION TESTS)
  classic-message-core    - 1336 lines, 32 inline tests
  classic-constants-core  - 1279 lines, 31 inline tests
  classic-update-core     - 1212 lines, 48 inline tests
  classic-web-core        - 834 lines, 35 inline tests
  classic-registry-core   - 775 lines, 16 inline tests
  classic-resource-core   - 630 lines, 8 inline tests
  classic-perf-core       - 620 lines, 15 inline tests
  classic-version-core    - 599 lines, 10 inline tests
  classic-xse-core        - 561 lines, 8 inline tests
  classic-pybridge-core   - 457 lines, 10 inline tests

Python Bindings (18 crates):
  classic-scanlog-py      - 3543 lines, 0 tests
  classic-scangame-py     - 1667 lines, 0 tests
  classic-file-io-py      - 1593 lines, 0 tests
  classic-path-py         - 1434 lines, 0 tests
  classic-constants-py    - 823 lines, 0 tests
  classic-message-py      - 818 lines, 0 tests
  classic-yaml-py         - 493 lines, 0 tests
  classic-update-py       - 473 lines, 0 tests
  classic-resource-py     - 472 lines, 0 tests
  classic-database-py     - 469 lines, 0 tests
  classic-config-py       - 465 lines, 0 tests
  classic-settings-py     - 440 lines, 0 tests
  classic-registry-py     - 404 lines, 0 tests
  classic-xse-py          - 358 lines, 0 tests
  classic-version-py      - 331 lines, 0 tests
  classic-web-py          - 323 lines, 0 tests
  classic-perf-py         - 252 lines, 0 tests
  classic-pybridge-py     - 271 lines, 0 tests

UI Applications (1 crate):
  classic-gui             - 2745 lines, 39 inline tests (HAS TESTS)
```

### Pattern 1: Baseline-First Coverage Workflow
**What:** Run workspace coverage first, identify gaps, then fill systematically
**When to use:** Always -- this is the prescribed workflow for this phase

Step 1 - Run baseline with exclusions:
```bash
# From rust/ directory
cargo llvm-cov --workspace --html \
  --ignore-filename-regex "(target[/\\\\]|build[/\\\\]|\.slint)" \
  --output-dir target/llvm-cov/html
```

Step 2 - Generate JSON for scripted per-crate analysis:
```bash
cargo llvm-cov --workspace --json \
  --ignore-filename-regex "(target[/\\\\]|build[/\\\\]|\.slint)" \
  --output-path target/llvm-cov/coverage.json
```

Step 3 - Generate lcov for CI:
```bash
cargo llvm-cov --workspace --lcov \
  --ignore-filename-regex "(target[/\\\\]|build[/\\\\]|\.slint)" \
  --output-path target/llvm-cov/lcov.info
```

### Pattern 2: Per-Crate Coverage Measurement
**What:** Run coverage for individual crates to track improvement
**When to use:** After baseline, when filling gaps in specific crates

```bash
# Per-crate coverage with text summary
cargo llvm-cov --package classic-scanlog-core --text \
  --ignore-filename-regex "(target[/\\\\]|build[/\\\\])"
```

### Pattern 3: Two-Phase Run (No-Report + Report)
**What:** Run tests once, generate multiple report formats
**When to use:** When generating both HTML and lcov from same test run

```bash
# Phase 1: Run tests and collect profiling data
cargo llvm-cov --workspace --no-report \
  --ignore-filename-regex "(target[/\\\\]|build[/\\\\]|\.slint)"

# Phase 2a: Generate HTML report
cargo llvm-cov report --html --output-dir target/llvm-cov/html \
  --ignore-filename-regex "(target[/\\\\]|build[/\\\\]|\.slint)"

# Phase 2b: Generate lcov report
cargo llvm-cov report --lcov --output-path target/llvm-cov/lcov.info \
  --ignore-filename-regex "(target[/\\\\]|build[/\\\\]|\.slint)"

# Phase 2c: Generate JSON for per-crate analysis
cargo llvm-cov report --json --output-path target/llvm-cov/coverage.json \
  --ignore-filename-regex "(target[/\\\\]|build[/\\\\]|\.slint)"
```

### Pattern 4: GUI Crate Testing Without Slint Event Loop
**What:** Test pure Rust logic behind the GUI without requiring a display server
**When to use:** Testing classic-gui crate modules (markdown, results, settings, state)

The GUI crate already has `pub` library exports in `lib.rs` with testable modules:
- `markdown::parse_markdown()` - Pure function, no Slint dependency
- `results::extract_timestamp()`, `prepare_report_entries()` - Pure functions
- `settings::settings_file_path()`, `game_version_*()` - Pure functions
- `state::WindowState`, `TabGeometry` - Data structures with methods
- `worker::ScanWindowProperties` trait - Mockable via trait implementation

Existing test patterns show inline `#[cfg(test)]` modules working in all 4 testable GUI files.

### Pattern 5: PyO3 Binding Crate Testing
**What:** Testing Python binding adapter code without a Python interpreter
**When to use:** For `-py` crate coverage

PyO3 binding crates have `crate-type = ["cdylib", "rlib"]`. The `rlib` target allows `cargo test` to run without Python. However, most PyO3 code uses `#[pyclass]`, `#[pymethods]`, and `Python::with_gil()` which require PyO3 initialization. Testing these crates meaningfully at the Rust level is limited to:
- Type conversion functions that don't need GIL
- Error mapping functions
- Pure Rust helper functions within the crate

**Recommendation for `-py` crates:** Exclude them from the 60% coverage target with `--exclude-from-report` since they are thin adapters. Their business logic lives in `-core` crates which ARE covered. Report their coverage separately as informational.

### Anti-Patterns to Avoid
- **Testing Slint-generated code:** The build script generates ~85K lines in `target/debug/build/classic-gui-slint-*/out/main.rs`. This MUST be excluded via `--ignore-filename-regex`.
- **Testing PyO3 macro expansions:** PyO3 procedural macros generate boilerplate. Focus on the hand-written conversion logic, not macro output.
- **Running coverage with `--release`:** Coverage instrumentation conflicts with heavy optimizations. Use debug profile (default).
- **Single monolithic coverage run:** Run `--no-report` first, then generate multiple formats from collected data. Avoids re-running all tests for each format.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Coverage measurement | Custom profiling | cargo-llvm-cov (already installed) | LLVM instrumentation is precise and maintained |
| Per-crate JSON parsing | Manual regex on text output | JSON export + simple script | Structured data is more reliable |
| Test file organization | Custom test runner | Standard Rust `#[cfg(test)]` inline + `tests/` dir | Cargo convention, auto-discovered |
| Async test harness | Manual runtime setup | `#[tokio::test]` macro | Standard, handles runtime lifecycle |
| Temp directory cleanup | Manual rmdir | `tempfile::tempdir()` | RAII cleanup, already in workspace deps |
| Global state isolation | Manual reset | `serial_test::serial` | Prevents test interference |

**Key insight:** The coverage infrastructure is already 90% set up -- cargo-llvm-cov is installed and the workspace compiles. The work is in writing tests and organizing reports, not in tooling.

## Common Pitfalls

### Pitfall 1: Slint-Generated Code Inflating/Deflating Coverage
**What goes wrong:** Slint's build script generates ~85,000 lines of Rust in `target/debug/build/classic-gui-slint-*/out/`. If not excluded, it massively distorts coverage numbers (either showing very low coverage because generated code is untested, or if the test binary happens to exercise UI paths, inflating it).
**Why it happens:** `cargo llvm-cov` instruments ALL compiled Rust code including build-script generated code.
**How to avoid:** Use `--ignore-filename-regex "(target[/\\\\]|build[/\\\\]|\.slint)"` on every coverage run. This regex catches:
  - `target/` directory paths (build artifacts, generated code)
  - `build/` directory paths (build.rs output)
  - `.slint` source files (if somehow included)
**Warning signs:** Coverage numbers seem impossibly low or impossibly high for classic-gui.

### Pitfall 2: PyO3 `extension-module` Linking Issues
**What goes wrong:** PyO3 crates with `extension-module` feature might fail to link during coverage builds because they expect to be loaded by Python.
**Why it happens:** `cdylib` crates with `extension-module` suppress linking against `libpython`. During `cargo test`, the `rlib` target is used instead, but feature resolution can still trigger linker issues.
**How to avoid:** All 18 PyO3 crates in this workspace already have `crate-type = ["cdylib", "rlib"]` which allows testing. If linking issues arise, use `--exclude <crate-name>` to skip problematic crates from the test run while still reporting their source coverage.
**Warning signs:** Linker errors mentioning `Python` or `_Py` symbols during `cargo llvm-cov`.

### Pitfall 3: Global State Contamination Between Tests
**What goes wrong:** Tests that modify global singletons (Tokio runtime, dispatchers, caches) interfere with each other, causing non-deterministic failures.
**Why it happens:** Rust tests run in parallel by default within a crate. Global state (OnceLock, static Lazy) persists across tests.
**How to avoid:** Use `serial_test` for tests touching global state. The async_bridge tests already note this pattern -- the DISPATCHER OnceLock can only be set once per process.
**Warning signs:** Tests pass individually but fail when run together; intermittent failures.

### Pitfall 4: Confusing "No Tests" with "Low Coverage"
**What goes wrong:** A crate that compiles but has no `#[test]` functions will show 0% coverage. This is different from a crate with tests that don't exercise enough code.
**Why it happens:** cargo-llvm-cov reports 0% for crates where no test binary ran any code.
**How to avoid:** Separate the "add first tests" work (0% -> some%) from "improve existing tests" work (some% -> 60%).
**Warning signs:** Per-crate report showing exactly 0.00% coverage.

### Pitfall 5: Windows Path Separators in Regex
**What goes wrong:** `--ignore-filename-regex` patterns with Unix-style `/` separators don't match Windows paths which use `\`.
**Why it happens:** On Windows, file paths in coverage data use `\` (or sometimes `\\`). LLVM path formatting varies.
**How to avoid:** Use `[/\\\\]` in regex patterns to match both forward and backward slashes: `"(target[/\\\\]|build[/\\\\])"`.
**Warning signs:** Excluded files still appearing in coverage reports on Windows.

### Pitfall 6: GUI Feature Gate Tests Not Running
**What goes wrong:** AsyncBridge tests in classic-shared-core require `features = ["gui-bridge"]` to compile. Without the feature flag, these tests are `#[cfg(feature = "gui-bridge")]` gated and silently skipped.
**Why it happens:** Default `cargo test` runs with default features only.
**How to avoid:** For classic-shared-core, run tests with `--features gui-bridge` explicitly: `cargo llvm-cov -p classic-shared-core --features gui-bridge`.
**Warning signs:** async_bridge.rs showing 0% coverage despite having 15 test functions.

## Code Examples

### Example 1: PowerShell Per-Crate Coverage Script
```powershell
# coverage_report.ps1 - Generate per-crate coverage summary
# Run from rust/ directory

$excludeRegex = "(target[/\\]|build[/\\]|\.slint)"

# Run all tests and collect profiling data
cargo llvm-cov --workspace --no-report --ignore-filename-regex $excludeRegex

# Generate JSON report
cargo llvm-cov report --json --output-path target/llvm-cov/coverage.json `
  --ignore-filename-regex $excludeRegex

# Generate HTML report
cargo llvm-cov report --html --output-dir target/llvm-cov/html `
  --ignore-filename-regex $excludeRegex

# Generate lcov for future CI
cargo llvm-cov report --lcov --output-path target/llvm-cov/lcov.info `
  --ignore-filename-regex $excludeRegex

Write-Host "`nCoverage reports generated:"
Write-Host "  HTML: target/llvm-cov/html/index.html"
Write-Host "  JSON: target/llvm-cov/coverage.json"
Write-Host "  LCOV: target/llvm-cov/lcov.info"
```

### Example 2: Inline Test Module Pattern (Existing Convention)
```rust
// Source: Observed pattern in classic-gui/src/markdown.rs, classic-scanlog-core/src/patterns.rs
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_function_name() {
        // Arrange
        let input = "test data";

        // Act
        let result = function_under_test(input);

        // Assert
        assert_eq!(result, expected_value);
    }
}
```

### Example 3: Integration Test Pattern (Existing Convention)
```rust
// Source: Observed pattern in classic-config-core/tests/integration_tests.rs
//! Integration tests for classic-<crate-name>

use classic_crate_name::PublicType;
use tempfile::tempdir;
use std::fs;

fn test_fixture_data() -> &'static str {
    r#"
    yaml: content
    for: testing
    "#
}

#[test]
fn test_cross_component_workflow() {
    let dir = tempdir().unwrap();
    let file_path = dir.path().join("test.yaml");
    fs::write(&file_path, test_fixture_data()).unwrap();

    let result = PublicType::load_from(&file_path);
    assert!(result.is_ok());
}
```

### Example 4: Async Test Pattern
```rust
// Source: Observed pattern in classic-shared-core async tests
#[tokio::test]
async fn test_async_operation() {
    let result = async_function().await;
    assert!(result.is_ok());
}
```

### Example 5: GUI Trait Mock Test Pattern
```rust
// Source: Observed pattern in classic-shared-core/src/async_bridge.rs
// and classic-gui/src/worker.rs

/// Mock implementing ScanWindowProperties for testing without Slint
struct MockScanWindow {
    progress: std::cell::RefCell<f32>,
    status: std::cell::RefCell<String>,
    in_progress: std::cell::RefCell<bool>,
}

impl ScanWindowProperties for MockScanWindow {
    fn set_scan_progress(&self, value: f32) {
        *self.progress.borrow_mut() = value;
    }
    fn set_scan_status(&self, value: slint::SharedString) {
        *self.status.borrow_mut() = value.to_string();
    }
    fn set_scan_in_progress(&self, value: bool) {
        *self.in_progress.borrow_mut() = value;
    }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| cargo-tarpaulin | cargo-llvm-cov | ~2023 | LLVM instrumentation is more precise and faster |
| `#[coverage(off)]` on stable | Still nightly-only | Reverted stabilization | Must use `--ignore-filename-regex` for exclusions on stable |
| gcov-style coverage | LLVM source-based (instrument-coverage) | Rust 1.60+ | Much more accurate region/line tracking |

**Deprecated/outdated:**
- `#[coverage(off)]` attribute: Requires nightly Rust (not available on stable 1.91.1). Use `--ignore-filename-regex` instead.
- `cargo-tarpaulin`: Still maintained but weaker Windows support. Not applicable here since cargo-llvm-cov is already installed.

## Recommendations for Claude's Discretion Items

### Coverage Tooling Installation
**Recommendation:** No installation needed -- `cargo-llvm-cov 0.8.3` is already installed. Create a `coverage_report.ps1` PowerShell script in `rust/` that wraps the common coverage commands with proper exclusion patterns.

### Test File Organization
**Recommendation:** Follow existing project convention:
- **Inline `#[cfg(test)] mod tests`** for unit tests in source files (already the dominant pattern with 85 files using this)
- **`tests/` directory** for integration tests that span multiple modules (already used by classic-config-core, classic-yaml-core, classic-database-core, classic-shared-core)
- Do NOT create separate test files for single-module unit tests -- keep them inline

### Prioritization Order for Gap-Filling
**Recommendation:** Prioritize by (1) code volume and (2) criticality:

**Wave 1 -- Foundation (get tooling working, establish patterns):**
1. Set up coverage script and run baseline
2. Assess which crates are already at/above 60%

**Wave 2 -- Largest business-logic crates (most impact per test written):**
1. classic-scanlog-core (11,172 lines -- largest crate, already has 186 tests)
2. classic-file-io-core (4,411 lines -- 60 tests)
3. classic-path-core (4,377 lines -- 67 tests)
4. classic-scangame-core (4,168 lines -- 57 tests)
5. classic-version-registry-core (3,168 lines -- 63 tests)

**Wave 3 -- Medium crates:**
6. classic-config-core (2,137 lines)
7. classic-yaml-core (2,982 lines)
8. classic-settings-core (1,967 lines)
9. classic-database-core (1,696 lines)
10. classic-message-core (1,336 lines)

**Wave 4 -- Small crates and GUI:**
11. classic-gui (2,745 lines -- 39 tests already)
12. Remaining small business-logic crates
13. Foundation crates (classic-shared-core, classic-shared-py)

**Wave 5 -- Python bindings (if needed):**
14. PyO3 `-py` crates (thin adapters; business logic covered by -core tests)
Recommendation: Exclude from 60% target since they're adapters; report separately.

### Exclusion Patterns for Generated Code
**Recommendation:** Use this `--ignore-filename-regex` pattern:

```
"(target[/\\\\]|build[/\\\\]|\.slint)"
```

This excludes:
- `target/` -- all build artifacts, including Slint-generated code at `target/debug/build/classic-gui-slint-*/out/main.rs` (84,811 lines)
- `build/` -- build script output directories
- `.slint` -- Slint UI definition files (if included)

For PyO3 binding crates, use `--exclude-from-report` rather than filename regex:
```bash
cargo llvm-cov --workspace --exclude-from-report classic-yaml-py --exclude-from-report classic-scanlog-py [... etc]
```

Or, for the per-crate gap analysis, simply list them separately in the report.

## Open Questions

1. **Exact current coverage percentages per crate**
   - What we know: Many crates have tests (916 total test functions), but coverage percentages are unknown until the baseline runs
   - What's unclear: Which crates are already at 60%+ and which need work
   - Recommendation: The first plan task should run the baseline and produce the gap table; subsequent tasks depend on this data

2. **PyO3 crate compilation under coverage instrumentation**
   - What we know: All 18 PyO3 crates have `rlib` as a crate-type and compile with `cargo test --no-run --workspace`
   - What's unclear: Whether all of them actually PASS their (empty) test suites under coverage instrumentation without linker issues
   - Recommendation: First baseline run will reveal any issues; use `--exclude` for problematic crates

3. **classic-shared-core `gui-bridge` feature coverage**
   - What we know: AsyncBridge tests (15 functions) are behind `#[cfg(feature = "gui-bridge")]`
   - What's unclear: Whether workspace-level coverage run automatically enables this feature (it should, since classic-gui depends on classic-shared-core with `features = ["gui-bridge"]`)
   - Recommendation: Verify during baseline run; if not enabled, add explicit `--features` flag

## Sources

### Primary (HIGH confidence)
- **Local filesystem inspection** - Cargo.toml, source files, existing tests across all 39 crates
- **cargo llvm-cov --help** (v0.8.3) - Complete CLI reference verified locally
- **cargo llvm-cov --version** - Confirmed 0.8.3 installed, rustc 1.91.1 stable
- **cargo test --workspace --no-run** - Verified all crates compile for testing

### Secondary (MEDIUM confidence)
- [GitHub: taiki-e/cargo-llvm-cov](https://github.com/taiki-e/cargo-llvm-cov) - Official repository, README docs
- [docs.rs: cargo-llvm-cov](https://docs.rs/crate/cargo-llvm-cov/latest/source/docs/cargo-llvm-cov.txt) - CLI documentation
- [GitHub Issue #123: Exclude test code](https://github.com/taiki-e/cargo-llvm-cov/issues/123) - `#[coverage(off)]` nightly-only status confirmed
- [Rust Project Primer: Coverage](https://rustprojectprimer.com/measure/coverage.html) - General coverage patterns

### Tertiary (LOW confidence)
- [LLVM llvm-cov docs](https://llvm.org/docs/CommandGuide/llvm-cov.html) - JSON export format details (actual schema undocumented)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - cargo-llvm-cov is already installed and verified; workspace compiles
- Architecture: HIGH - All crate sizes, test counts, and file structures inspected directly
- Pitfalls: HIGH - Windows-specific issues verified against actual toolchain (stable 1.91.1, MSVC)
- Coverage patterns: MEDIUM - Command-line options verified from help output; per-crate reporting strategy needs baseline validation

**Research date:** 2026-02-06
**Valid until:** 2026-03-08 (30 days -- cargo-llvm-cov is stable tooling)
