## Project Overview

CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker) is a high-performance hybrid Python-Rust desktop application that analyzes crash logs from Bethesda games (Fallout 4 and Skyrim). It provides two Python interfaces: GUI (PySide6/Qt) and CLI. A Rust-based TUI (Ratatui) is also available as a separate application.

**🚀 Rust Acceleration**: CLASSIC uses Rust for performance-critical operations, achieving 10-150x speedups while maintaining full Python compatibility.

## Quick Start

### Installation & Distribution
- **DO NOT use `pip install`** for normal use (not published to PyPI)
- **Exception**: `uv pip install -e . --force-reinstall` for Rust development only

### Development Setup
```bash
# Setup
git clone https://github.com/evildarkarchon/CLASSIC-Fallout4.git
cd CLASSIC-Fallout4
uv sync --all-extras

# Run application
uv run python CLASSIC_Interface.py  # GUI
uv run python CLASSIC_ScanLogs.py   # CLI

# Testing (use terminal, not VS Code test tool)
uv run pytest               # All tests, parallel
uv run pytest -m "unit and not slow"  # Quick unit tests
uv run pytest -m "integration"        # Integration tests
uv run pytest tests/rust_integration/ -v   # Rust integration tests
uv run pytest tests/path/to/test_file.py::test_function -v  # Single test

# Linting
uv run ruff check .
uv run ruff format .

# Build executable (Windows)
uv run pyinstaller --clean --upx-dir 'C:\\Path\\to\\UPX' .\\CLASSIC.spec
```

### Rust Extension Development
```bash
# Method 1: Build wheel (MOST RELIABLE - RECOMMENDED)
# Build individual modules (Manual):
cd rust/python-bindings/classic-yaml-py && maturin build --release --out dist && cd ../../..
uv pip install rust/python-bindings/classic-yaml-py/dist/classic_yaml_py-*.whl --force-reinstall

# Or use the rebuild_rust.ps1 (Unified Script) through powershell:
pwsh -ExecutionPolicy Bypass -File ./rebuild_rust.ps1              # Build all (incremental)
pwsh -ExecutionPolicy Bypass -File ./rebuild_rust.ps1 yaml         # Build specific crate
pwsh -ExecutionPolicy Bypass -File ./rebuild_rust.ps1 -Clean       # Clean build

# Method 2: Editable install (DEVELOPMENT)
uv pip install -e . --force-reinstall

# Verify Rust acceleration
uv run python -c "import classic_yaml; print(f'Rust YAML version: {classic_yaml.__version__}')"
uv run python -c "from ClassicLib.integration.status import print_rust_status; print_rust_status()"
```

**📚 Detailed Guide**: See [PyO3 Integration Patterns](docs/development/pyo3_integration_patterns.md)

## Architecture

### Hybrid Python-Rust Architecture
- **Python**: UI, high-level logic, and coordination in `src/classic/` and `ClassicLib/`
- **Rust**: Three-layer modular architecture delivering 10-150x performance gains
  - **Foundation Layer**: `classic-shared` (runtime, errors, utilities)
  - **Business Logic Layer** (Pure Rust - no PyO3): `-core` crates
  - **Python Bindings Layer** (PyO3 adapters): `-py` crates
- **Integration**: PyO3 0.27 bindings with native async solution
- **Direct Imports**: Python imports individual modules (e.g., `import classic_yaml`)
- **Fallback**: Full Python implementations ensure compatibility
- **Transparent**: Automatic acceleration - no API changes required

**Architecture Rules**:
- **ONE RUNTIME RULE**: Single global Tokio runtime shared across all crates
- **SEPARATION OF CONCERNS**: Business logic in `-core` crates, PyO3 bindings in `-py` crates
- **NO MIXED CRATES**: Never combine business logic with PyO3 bindings in the same crate

**📚 Deep Dive**: See [Rust Workspace Architecture](docs/development/rust_workspace_architecture.md)

### Rust Directory Structure

**IMPORTANT**: All Rust crates are organized in the `rust/` directory with subdirectories by layer. The authoritative list is in `rust/Cargo.toml`.

```
rust/
├── Cargo.toml                        # Workspace manifest (authoritative crate list)
├── Cargo.lock                        # Dependency lock file
├── foundation/                       # Foundation Layer
│   ├── classic-shared-core/         # Core runtime, errors, utilities
│   └── classic-shared-py/           # PyO3 bindings for shared components
├── business-logic/                   # Business Logic Layer (Pure Rust - NO PyO3)
│   └── classic-*-core/              # All business logic crates (yaml, database, scanlog, config, etc.)
├── python-bindings/                  # Python Bindings Layer (PyO3 adapters)
│   └── classic-*-py/                # All Python binding crates (one per -core crate)
└── ui-applications/                  # UI Applications
    ├── classic-cli/                 # Command-line interface
    ├── classic-tui/                 # Terminal UI (Ratatui)
    └── classic-ui-shared/           # Shared UI components
```

**Current crates** (see `rust/Cargo.toml` for full list): yaml, database, file-io, scanlog, config, scangame, registry, perf, pybridge, settings, message, path, constants, version, resource, xse, web, update

**Creating New Crates**:
1. **Business Logic** (`-core` crate): Create in `rust/business-logic/`
   - Pure Rust, NO PyO3 dependencies
   - `Cargo.toml`: `crate-type = ["rlib"]`
   - Add to workspace in `rust/Cargo.toml` under `# Business Logic`

2. **Python Bindings** (`-py` crate): Create in `rust/python-bindings/`
   - Depends on corresponding `-core` crate
   - `Cargo.toml`: `crate-type = ["cdylib", "rlib"]`
   - Add PyO3 dependency: `pyo3.workspace = true`
   - Add to workspace in `rust/Cargo.toml` under `# Python Bindings`
   - Add to `rebuild_rust.ps1` and `build_all.ps1`
   - **MUST create/update `.pyi` stub file** for type hints and IDE support

3. **UI Applications**: Create in `rust/ui-applications/`
   - Standalone applications (CLI/TUI/GUI)
   - Add to workspace in `rust/Cargo.toml` under `# Native Applications`

**Build System Updates**:
- Always update `rust/Cargo.toml` workspace members when adding crates
- Update `rebuild_rust.ps1` for Python binding crates
- Update `build_all.ps1` for PyInstaller bundling

**📚 Deep Dive**: See [Rust Workspace Architecture](docs/development/rust_workspace_architecture.md)

### Core Components
- **Entry Points**: `CLASSIC_Interface.py` (GUI), `CLASSIC_ScanLogs.py` (CLI)
- **AsyncBridge**: Singleton for async/sync bridging (replaces deprecated AsyncCore)
- **MessageHandler**: Central messaging system for all output modes
- **YamlSettingsCache**: Configuration management with batch loading
- **FileIOCore**: Unified async-first file I/O with Rust acceleration (10x faster)
- **OrchestratorCore**: Async-first log scanning orchestration with Rust components

### Essential Patterns

```python
# Use AsyncBridge for sync contexts
from ClassicLib.AsyncBridge import AsyncBridge
bridge = AsyncBridge.get_instance()
result = bridge.run_async(async_function())

# Transparent Rust acceleration
from ClassicLib.ScanLog.Parser import find_segments  # Uses Rust if available
from ClassicLib.integration.factory import get_parser  # Automatic fallback
```

**📚 Complete Guide**: See [Async Development Guide](docs/development/async_development_guide.md)

## Slint GUI Development

**Key Rule**: Always use `AsyncBridge::run_with_ui_update()` for async operations in Slint callbacks.

```rust
use classic_shared::AsyncBridge;

main_window.on_scan_crash_logs({
    let window_weak = main_window.as_weak();
    move || {
        AsyncBridge::run_with_ui_update(
            perform_scan(),
            move |result| {
                if let Some(w) = window_weak.upgrade() {
                    w.handle_result(result);
                }
            }
        );
    }
});
```

**📚 Complete Guide**: See [Slint GUI Development](docs/development/slint_gui_development.md)

## Testing Standards

### Test-Driven Development (TDD) - REQUIRED

**All new features and bug fixes MUST follow TDD methodology.** Use the Red-Green-Refactor cycle:

1. **Red**: Write a failing test first that defines the expected behavior
2. **Green**: Write minimal code to make the test pass
3. **Refactor**: Improve code quality while keeping tests green

**AI Agents**: Use the TDD skill for comprehensive guidance.

```python
# Example TDD workflow
# Step 1: Write failing test (Red)
@pytest.mark.unit
def test_parse_formid_extracts_plugin_index():
    result = parse_formid("0A001234")
    assert result.plugin_index == 0x0A

# Step 2: Implement minimal code (Green)
# Step 3: Refactor with tests as safety net
```

**TDD Checklist** (before marking feature complete):
- [ ] Failing test written first
- [ ] Minimal implementation passes test
- [ ] Code refactored with tests still passing
- [ ] Tests pass individually AND together (`-n auto`)

### Test Organization
- **Structure**: Domain-driven directories in `tests/`
- **File Naming**: `test_<component>_<type>.py` (unit/integration/e2e)
- **Markers**: Required - `@pytest.mark.unit`, `.integration`, `.asyncio`, `.slow`, `.gui`, `.performance`
- **Rust tests**: Place in `tests/rust_integration/` directory (no special marker needed)

### Critical Rules
1. **NEVER modify production YAML** in tests (use `YAML.TEST` or mocks)
2. **NEVER add backward compatibility** to fix tests (update tests to match new API)
3. **Always clear singletons** between tests (GlobalRegistry, MessageHandler)
4. **Use proper async mocking** to avoid unawaited coroutine warnings
5. **Tests are exempt from API stability** - Always use current APIs, never deprecated ones

### Testing Guides
See `docs/` for detailed guides:
- `testing/testing_async_bridge.md` - Async/sync mocking
- `testing/testing_global_registry.md` - Singleton isolation
- `testing/testing_yaml_cache.md` - Config testing
- `testing/test_pollution_guide.md` - Master pollution prevention guide

### Test Fixtures Standards

**All pytest fixtures MUST be defined in `tests/fixtures/`** - Never create fixtures in individual test files or scattered conftest.py files.

```
tests/fixtures/
├── __init__.py              # Re-exports for convenience
├── async_fixtures.py        # Async test utilities, event loops
├── crash_log_fixtures.py    # Crash log content and file creation
├── data_fixtures.py         # General test data fixtures
├── database_pool_fixtures.py # Database connection pool fixtures
├── fcx_fixtures.py          # FCX mode testing fixtures
├── mock_fixtures.py         # Common mock objects
├── qt_fixtures.py           # Qt/PySide6 testing fixtures
├── registry_fixtures.py     # GlobalRegistry fixtures
├── rust_fixtures.py         # Rust FFI compatible mocks
├── scanlog_fixtures.py      # Orchestrator, parser fixtures
├── stress_fixtures.py       # Stress/load testing fixtures
├── version_cache_fixtures.py # Version cache fixtures
└── yamldata_fixtures.py     # YamlData mock fixtures
```

**Creating New Fixtures**:
1. Identify the appropriate module based on the fixture's domain
2. Add the fixture to the existing module, or create a new module if needed
3. If creating a new module, add the import to `tests/conftest.py`
4. Document the fixture with a docstring explaining its purpose

**Exception: Local Autouse Fixtures**:
Local `conftest.py` files are allowed ONLY for `autouse=True` fixtures that must be scoped to a specific directory. The fixture implementation should still live in `tests/fixtures/`, with the local conftest providing a thin autouse wrapper.

```python
# tests/stress/conftest.py - ALLOWED (autouse scoping)
from tests.fixtures.stress_fixtures import cleanup_after_stress_test as _cleanup_impl

@pytest.fixture(autouse=True)
def cleanup_after_stress_test():
    """Apply cleanup only to tests in this directory."""
    yield from _cleanup_impl()
```

This pattern ensures cleanup fixtures don't add overhead to the entire test suite while keeping the implementation centralized.

**Anti-Patterns**:
- Fixtures in individual test files -> Move to `tests/fixtures/`
- Duplicate fixtures across conftest files -> Consolidate in one fixture module
- Fixtures in `tests/*/conftest.py` -> Move to central `tests/fixtures/`
- Autouse fixtures in central fixtures (runs on ALL tests) -> Use local conftest wrapper

## Continuous Integration

CLASSIC uses GitHub Actions for automated testing and validation on every PR and push.

### CI Pipeline
- **Python Linting**: Ruff code quality checks (10 min timeout)
- **Rust Linting**: Clippy and rustfmt validation (15 min timeout)
- **Rust Build**: Full workspace compilation (60 min timeout)
- **Rust Tests**: Independent Rust test suite (30 min timeout)
 - Default feature tests
 - All-features tests
- **Python Bindings**: Maturin builds all PyO3 modules (30 min timeout)
- **Python Tests**: pytest suite with Rust acceleration (30 min timeout)
 - Unit tests: 300s per-test timeout
 - Integration tests: 600s per-test timeout
 - Rust integration tests: 300s per-test timeout
- **Type Checking**: mypy validation (non-blocking, 15 min timeout)

### Running CI Checks Locally
```bash
# Python checks
uv run ruff check .
uv run ruff format --check .

# Rust checks
cargo fmt --all --manifest-path rust/Cargo.toml -- --check
cargo clippy --workspace --all-targets --all-features --manifest-path rust/Cargo.toml -- -D warnings

# Rust build and test
cargo build --workspace --release --manifest-path rust/Cargo.toml
cargo test --workspace --release --manifest-path rust/Cargo.toml
cargo test --workspace --release --all-features --manifest-path rust/Cargo.toml

# Python tests
uv run pytest -n 4 -m "unit and not slow"
```

### Key Features
- **Comprehensive Caching**: Cargo registry, build artifacts, and Python dependencies
- **Timeout Protection**: All jobs and individual tests have timeouts to prevent deadlocks
- **Parallel Execution**: Tests run in parallel with pytest-xdist
- **Artifact Uploads**: Wheels and test results available for debugging

**📚 Complete Guide**: See [CI/CD Guide](docs/development/ci_cd_guide.md) for troubleshooting and release process

## Code Quality Standards

### File Organization
- **One class per file** (exceptions: small related helpers)
- **Max 12 branches per function** (use dict mapping, match statements, or extract methods)
- **Complete type annotations** (Python 3.12+ syntax)

### Development Rules
1. **No print()** - Use MessageHandler (`msg_info()`, `msg_warning()`, `msg_error()`)
2. **Use pathlib.Path** - Never string paths
3. **UTF-8 encoding** with `errors="ignore"` for file ops
4. **Async-first** - Use AsyncBridge for sync contexts
5. **Batch operations** - Load multiple YAML settings together
6. **Test markers** - All tests must have appropriate markers
7. **Google-style docstrings** - All modules, classes, and functions require detailed docstrings
8. **Deprecated APIs = ERRORS** - Treat all deprecated warnings as compilation errors
9. **API Stability Rules** - Production code maintains backward compatibility
   - Tests are exempt from API stability (always use current APIs)
   - Deprecated code ONLY used in tests or `__init__.py` can be deleted
10. **PyO3 Type Stubs** - All Rust Python bindings (`-py` crates) MUST have `.pyi` stub files
   - Create stub file when creating new Python binding crate
   - Update stub file whenever API changes (new functions, classes, or signatures)
   - Place `.pyi` file in same directory as crate (e.g., `rust/python-bindings/classic-yaml-py/classic_yaml.pyi`)

### Rust Documentation Standards

**CRITICAL**: All new Rust code MUST be fully documented according to Rust documentation standards. Missing documentation warnings are treated as errors.

**Requirements**:
- All `pub struct`, `pub enum`, `pub fn`, `pub mod` require `///` doc comments
- All public struct fields and enum variants require documentation
- Crate-level documentation with `//!` at top of `lib.rs` or `main.rs`
- Follow [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/documentation.html)
- Only suppress `missing_docs` for generated code (e.g., Slint UI)

**📚 Complete Guide**: See [Rust Documentation Standards](docs/development/rust_documentation_standards.md) in CLAUDE.md (lines 574-706)

### Python Documentation Standards

**CRITICAL**: All Python code MUST have detailed docstrings following the Google Python Style Guide. Missing or incomplete docstrings are treated as errors.

**Requirements**:
- All modules require a module-level docstring at the top of the file
- All public classes, functions, and methods require docstrings
- All public class attributes and constants require documentation
- Use Google-style docstring format (not NumPy or Sphinx)
- Include complete type information in docstrings (even with type hints)
- Document all parameters, return values, raises, yields, and examples where applicable

**Google Docstring Format**:

```python
"""Module-level docstring describing the module's purpose.

This module provides utilities for scanning crash logs and analyzing
game configurations. It integrates with both Python and Rust backends
for optimal performance.
"""

from pathlib import Path
from typing import Optional


class LogScanner:
    """Scans crash logs and extracts diagnostic information.

    This class provides both synchronous and asynchronous methods for
    parsing crash logs from Bethesda games. It automatically uses Rust
    acceleration when available.

    Attributes:
        log_path: Path to the crash log file to analyze.
        use_rust: Whether to use Rust acceleration (default: True).
        encoding: File encoding to use (default: "utf-8").

    Example:
        >>> scanner = LogScanner(Path("crash.log"))
        >>> result = scanner.scan()
        >>> print(result.error_count)
        42
    """

    def __init__(
        self,
        log_path: Path,
        use_rust: bool = True,
        encoding: str = "utf-8"
    ) -> None:
        """Initialize the LogScanner.

        Args:
            log_path: Path to the crash log file.
            use_rust: Whether to use Rust acceleration if available.
            encoding: File encoding to use when reading the log.

        Raises:
            FileNotFoundError: If log_path does not exist.
            ValueError: If encoding is not supported.
        """
        self.log_path = log_path
        self.use_rust = use_rust
        self.encoding = encoding


async def scan_log_async(
    log_path: Path,
    *,
    max_errors: Optional[int] = None,
    timeout: float = 30.0
) -> ScanResult:
    """Asynchronously scan a crash log file.

    This function performs async I/O to read and parse crash logs
    without blocking the event loop. It automatically falls back
    to Python implementation if Rust acceleration is unavailable.

    Args:
        log_path: Path to the crash log file to scan.
        max_errors: Maximum number of errors to collect (None = unlimited).
        timeout: Maximum time in seconds to wait for scan completion.

    Returns:
        A ScanResult object containing parsed diagnostic information,
        error counts, and recommendations.

    Raises:
        asyncio.TimeoutError: If scan exceeds timeout duration.
        FileNotFoundError: If log_path does not exist.
        PermissionError: If log_path is not readable.

    Example:
        >>> result = await scan_log_async(Path("crash.log"))
        >>> for error in result.errors:
        ...     print(error.message)

    Note:
        This function uses AsyncBridge internally for proper
        async/sync coordination in Qt applications.
    """
    ...


def process_segments(data: str) -> list[str]:
    """Split crash log data into logical segments.

    Args:
        data: Raw crash log content as string.

    Returns:
        List of segment strings, one per logical section.
        Empty list if data is empty or invalid.

    Example:
        >>> segments = process_segments(log_content)
        >>> len(segments)
        5
    """
    ...
```

**Documentation Requirements by Scope**:

1. **Modules**: Brief summary and overview of contents
2. **Classes**:
   - Purpose and behavior
   - Public attributes in `Attributes:` section
   - Usage example in `Example:` section
3. **Functions/Methods**:
   - Clear description of what it does (not how)
   - All parameters in `Args:` section
   - Return value in `Returns:` section
   - Exceptions in `Raises:` section
   - Generators use `Yields:` section
   - Complex functions include `Example:` section
4. **Properties**: Document the property, not just the backing field
5. **Constants**: Document purpose and valid values

**Special Cases**:
- **`__init__`**: Always document parameters and any exceptions
- **Private methods** (`_method`): Optional but recommended for complex logic
- **Test functions**: Docstring should describe what is being tested
- **Async functions**: Note async behavior and any AsyncBridge usage
- **Deprecated code**: Include `Deprecated:` section with migration path

**Anti-Patterns to Avoid**:
- ❌ No docstring → ✅ Complete Google-style docstring
- ❌ Single-line "Returns result" → ✅ Detailed description
- ❌ Missing Args/Returns sections → ✅ Complete documentation
- ❌ No examples for complex APIs → ✅ Include usage examples
- ❌ Outdated docstrings → ✅ Update docs with code changes

**Enforcement**:
- Ruff will warn about missing docstrings (treat as errors)
- Code reviews must verify docstring completeness
- All new code requires docstrings before PR approval

### Common Anti-Patterns to Avoid
- ❌ `asyncio.run()` in sync → ✅ `AsyncBridge.run_async()`
- ❌ Production YAML in tests → ✅ `YAML.TEST` or mocks
- ❌ String paths → ✅ `pathlib.Path`
- ❌ Direct print → ✅ MessageHandler
- ❌ Missing type hints → ✅ Complete annotations
- ❌ Missing docstrings → ✅ Google-style docstrings
- ❌ Manual event loops → ✅ AsyncBridge
- ❌ Deprecated APIs (Python/Rust) → ✅ Use current APIs immediately
- ❌ Multiple Tokio runtimes → ✅ `classic_shared::get_runtime()`
- ❌ Module-level YAML settings imports → ✅ Import `yaml_settings`, `yaml_settings_async`, `classic_settings`, `classic_settings_async` inside functions to avoid circular imports

## Rust Development Guides

### Core Guides
- **[Rust Workspace Architecture](docs/development/rust_workspace_architecture.md)** - Crate structure and dependency hierarchy
- **[Rust 2024 Edition Guide](docs/development/rust_2024_edition_guide.md)** - Modern Rust features and best practices
- **[Async Development Guide](docs/development/async_development_guide.md)** - Async patterns for Python and Rust
- **[PyO3 Integration Patterns](docs/development/pyo3_integration_patterns.md)** - PyO3 module registration and troubleshooting
- **[Rust Acceleration Guide](docs/development/rust_acceleration_guide.md)** - Performance monitoring and debugging
- **[Slint GUI Development](docs/development/slint_gui_development.md)** - Slint GUI patterns and AsyncBridge usage

### Reference Documentation
- **[Rust Documentation Index](docs/RUST_DOCUMENTATION_INDEX.md)** - Complete guide to all Rust docs
- **[Rust Usage Guide](docs/rust/rust_usage_guide.md)** - User guide for Rust features
- **[Performance Monitoring](docs/performance/performance_monitoring.md)** - Monitor Rust performance
- **[Troubleshooting Guide](docs/rust/troubleshooting_rust.md)** - Debug Rust issues
- **[Development Guide](docs/rust/development_with_rust.md)** - Develop with Rust components

### PyO3 0.27 Documentation
- **[PyO3 0.27 Migration Guide](docs/rust/PyO3-0.27-migration.md)** - Migration from 0.22 to 0.27
- **[PyO3 Quick Reference](docs/rust/pyo3_quick_reference.md)** - Quick reference for common patterns
- **[Official PyO3 Docs](https://pyo3.rs/v0.27.0/)** - Official PyO3 documentation

## Important Notes
- **Python 3.12+ required**
- **uv** package manager (faster than poetry)
- **Terminal for tests** (VS Code test tool freezes)
- **API compatibility priority** with deprecation warnings (production code only - tests always use current APIs)
- **Rust acceleration** automatic and transparent (10-150x speedups)
- **Native async solution** - no PyO3-asyncio dependency
- **No proactive doc creation** unless requested

## YAML Operations (yaml-rust2)
- **Library**: yaml-rust2 v0.10.4 (YAML 1.2 compliant, pure Rust, owned types)
- **Import**: `import classic_yaml; ops = classic_yaml.RustYamlOperations()`
- **Performance**: 15-30x faster than ruamel.yaml
- **Features**: Multi-document, anchor/alias, insertion order, pure Rust safety

## Memories
- Output test results to file to avoid truncation
- Use Mixins with TYPE_CHECKING for MainWindow extensions
- Maintain API compatibility with deprecation warnings
- **Direct module imports**: Import individual Rust modules directly (e.g., `import classic_yaml`, `import classic_scanlog`)
- **Facade removed** (2025-11-01): classic-core facade eliminated - Python imports individual modules for cleaner PyO3 integration
- **ONE RUNTIME RULE**: All Rust crates use `classic_shared::get_runtime()` to share global Tokio runtime
- **PyO3 module registration**: `#[pyclass]` types ONLY export from standalone cdylib modules
- **Standalone module pattern**: Each Rust crate exporting Python classes must have `crate-type = ["cdylib", "rlib"]`
- **GIL handling for parallel work**: Use `py.detach()` to release GIL, `Python::attach()` to reacquire in worker threads (PyO3 0.27)
- **Runtime conflicts**: Avoid `get_runtime().block_on()` when already in Python context
- **Business logic separation** (2025-10-08): ALL new Rust code MUST separate business logic (`-core` crates) from Python bindings (`-py` crates)
- **NO MIXED CRATES**: Never combine business logic with PyO3 bindings in the same crate
- **Slint AsyncBridge pattern** (2025-10-11): ALWAYS use `AsyncBridge::run_with_ui_update()` for async operations in Slint GUI
- **Rust documentation requirement** (2025-10-23): ALL new Rust code MUST be fully documented. Missing documentation warnings are treated as errors.
- **FCX mode read-only** (2025-10-29): FCX mode now operates in read-only mode - it detects configuration issues but never modifies files. All detected issues are reported with current vs. recommended values. Auto-fix functions (`apply_ini_fix_async`, `apply_all_ini_fixes_async`, `ConfigFileCache.set()`) have been removed. Use new detection functions (`detect_ini_issue_async`, `detect_all_ini_issues_async`, `ConfigFileCache.detect_issue()`) for read-only issue detection.
- **Rust directory reorganization** (2025-11-01): All Rust crates moved to `rust/` directory with subdirectories: `foundation/`, `business-logic/`, `python-bindings/`, `ui-applications/`. ALL new Rust crates MUST be created in the appropriate subdirectory. Workspace manifest at `rust/Cargo.toml`. Build scripts (`rebuild_rust.ps1`, `build_all.ps1`) updated to reference new paths.
- **AsyncBridge usage patterns** (2025-11-02, enforced 2025-12-14): AsyncBridge and `create_sync_wrapper()` are ONLY for same-thread GUI contexts and testing. Production CLI code MUST use async-first pattern with single `asyncio.run()` at entry point. **ENFORCEMENT**: Non-GUI production code using AsyncBridge is an architecture violation that must be refactored.
- **AsyncBridge is thread-local**: AsyncBridge stores its event loop in a thread-local variable, so it CANNOT be used in GUI workers that cross threads (e.g., `QRunnable`, `QThread`). For cross-thread workers, use `asyncio.run()` instead to create a new event loop in the worker thread.
- **Three-tier import classification**:
  - **Tier 1 (Core)**: `AsyncBridge.py`, `_async_utils/bridge_helpers.py` - Never refactor
  - **Tier 2 (Legitimate)**: Same-thread GUI callbacks, test files, sync adapters for GUI - Keep as-is
  - **Tier 3 (Violation)**: Production CLI paths using AsyncBridge, cross-thread workers using AsyncBridge - Must be refactored
- **Dual interface pattern**: Modules shared by GUI and CLI SHALL provide async methods as primary API (for CLI) and sync wrappers clearly documented as "GUI-only" (for Qt workers).
- **Single event loop rule**: CLI applications SHALL use single `asyncio.run(main())` at entry point; no AsyncBridge or `create_sync_wrapper()` in CLI execution paths.
- **PyO3 type stubs requirement** (2025-11-04): ALL Python binding crates (`-py` crates) MUST have corresponding `.pyi` stub files for type hints and IDE support. When creating a new Python binding crate or modifying APIs (functions, classes, signatures), the `.pyi` file MUST be created or updated. Stub files are placed in the same directory as the crate (e.g., `rust/python-bindings/classic-yaml-py/classic_yaml.pyi`).
- **Custom Rust exceptions** (2025-11-06): All Rust Python bindings now use custom exception hierarchies that map to Python `ClassicLib.integration.exceptions`. Each `-py` crate defines module-specific exceptions (e.g., `RustYamlError`, `RustYamlIOError`, `RustYamlParseError`) using PyO3's `create_exception!` macro. Error conversion functions (`to_pyerr`) map Rust error variants to appropriate Python exception types for better error handling and debugging. Implemented in: `classic-yaml-py`, `classic-scanlog-py`, `classic-file-io-py`, `classic-database-py`, `classic-config-py`.
- **YAML helper methods fix** (2025-11-21): Fixed `get_string_value`, `get_vec_value`, and `get_hashmap_value` in `classic-yaml-core` to properly navigate YAML hash structures instead of using index notation which returns `BadValue` for missing keys. These methods now match the behavior of `get_setting` by checking if current node is a Hash, creating Yaml::String keys, and using `.get()` to safely retrieve values.
- **Parallel YAML loading order fix** (2025-11-21): Fixed critical bug in `classic-config-core/yamldata.rs` where parallel YAML file loading used `JoinSet::join_next()` which returns tasks in completion order, not spawn order. This caused file contents to be assigned to wrong variables (e.g., game YAML content assigned to main). Replaced with `tokio::join!` macro which preserves the order of results (main, game, ignore) ensuring correct file-to-variable mapping.