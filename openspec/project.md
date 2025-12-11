# Project Context

## Purpose
CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker) is a high-performance hybrid Python-Rust desktop application that analyzes crash logs from Bethesda games (Fallout 4 and Skyrim). It provides diagnostic information, identifies problematic mods, and checks game configuration integrity. The application offers three interfaces: GUI (PySide6/Qt), CLI (Python), and TUI (Rust/Ratatui).

**Key Goals:**
- Automated crash log analysis with pattern matching against known issues
- Game setup validation and configuration checking
- Mod compatibility detection and conflict identification
- High performance through Rust acceleration (10-150x speedups)
- Cross-platform support with Windows as primary target

## Tech Stack

### Core Languages
- **Python 3.12+** - High-level logic, UI coordination, configuration management
- **Rust (2024 Edition)** - Performance-critical operations, TUI, and native applications

### Python Frameworks & Libraries
- **PySide6/Qt** - GUI framework
- **uv** - Package manager (faster than poetry)
- **pytest** - Testing framework with pytest-xdist for parallelization
- **Ruff** - Linting and formatting
- **mypy** - Static type checking

### Rust Frameworks & Libraries
- **PyO3 0.26.0** - Python bindings for Rust
- **Tokio** - Async runtime (single global runtime shared across all crates)
- **yaml-rust2 0.10.4** - YAML 1.2 compliant parsing (15-30x faster than ruamel.yaml)
- **Ratatui** - Terminal UI framework
- **Slint** - Cross-platform GUI framework (experimental)
- **Maturin** - Build system for PyO3 modules

### Build & Distribution
- **PyInstaller** - Python executable bundling
- **Cargo** - Rust package manager and build system
- **GitHub Actions** - CI/CD pipeline

## Project Conventions

### Code Style

#### Python
- **One class per file** (exceptions: small related helpers)
- **Max 12 branches per function** - Use dict mapping, match statements, or extract methods
- **Complete type annotations** using Python 3.12+ syntax
- **Google-style docstrings** - Required for all modules, classes, and functions
- **pathlib.Path** - Never use string paths
- **UTF-8 encoding** with `errors="ignore"` for file operations
- **No print()** - Use MessageHandler (`msg_info()`, `msg_warning()`, `msg_error()`)
- **Deprecated APIs = ERRORS** - Treat all deprecated warnings as compilation errors

#### Rust
- **Full documentation required** - All `pub` items must have `///` doc comments
- **Clippy warnings as errors** - `-D warnings` in CI
- **rustfmt enforced** - All code must pass `cargo fmt --check`
- **ONE RUNTIME RULE** - All crates use `classic_shared::get_runtime()` for shared Tokio runtime
- **Separation of concerns** - Business logic in `-core` crates, PyO3 bindings in `-py` crates
- **NO MIXED CRATES** - Never combine business logic with PyO3 bindings in the same crate

#### Naming Conventions
- **Python**: snake_case for functions/variables, PascalCase for classes
- **Rust**: snake_case for functions/variables, PascalCase for types, SCREAMING_SNAKE_CASE for constants
- **Test files**: `test_<component>_<type>.py` (unit/integration/e2e)
- **Rust crates**: `classic-<domain>-core` for business logic, `classic-<domain>-py` for bindings

### Architecture Patterns

#### Hybrid Python-Rust Architecture
```
Python Layer (UI, coordination)     Rust Layer (performance-critical)
├── ClassicLib/                     ├── rust/foundation/
│   ├── AsyncBridge.py             │   └── classic-shared-core/
│   ├── MessageHandler/            ├── rust/business-logic/
│   ├── ScanLog/                   │   └── classic-*-core/
│   └── FileIO/                    ├── rust/python-bindings/
└── Entry Points                   │   └── classic-*-py/
    ├── CLASSIC_Interface.py       └── rust/ui-applications/
    ├── CLASSIC_ScanLogs.py            ├── classic-cli/
    └── CLASSIC_ScanGame.py            └── classic-tui/
```

#### Three-Layer Rust Architecture
1. **Foundation Layer** (`classic-shared`) - Runtime, errors, utilities
2. **Business Logic Layer** (`-core` crates) - Pure Rust, no PyO3 dependencies
3. **Python Bindings Layer** (`-py` crates) - PyO3 adapters with `crate-type = ["cdylib", "rlib"]`

#### Key Patterns
- **AsyncBridge** - Singleton for async/sync bridging (required for GUI workers)
- **MessageHandler** - Central messaging system for all output modes
- **Factory Pattern** - `get_parser()`, `get_yaml_operations()` for automatic Rust/Python fallback
- **Transparent Acceleration** - Automatic use of Rust when available, no API changes needed

### Testing Strategy

#### Test Organization
- **Directory**: Domain-driven structure in `tests/`
- **Naming**: `test_<component>_<type>.py` (unit/integration/e2e)
- **Rust tests**: `tests/rust_integration/` directory

#### Required Markers
```python
@pytest.mark.unit        # Fast, isolated unit tests
@pytest.mark.integration # Tests with external dependencies
@pytest.mark.asyncio     # Async tests
@pytest.mark.slow        # Long-running tests
@pytest.mark.gui         # GUI-dependent tests
@pytest.mark.performance # Performance benchmarks
```

#### Critical Rules
1. **NEVER modify production YAML** in tests - Use `YAML.TEST` or mocks
2. **NEVER add backward compatibility** to fix tests - Update tests to match new API
3. **Always clear singletons** between tests (GlobalRegistry, MessageHandler)
4. **Use proper async mocking** to avoid unawaited coroutine warnings
5. **Tests are exempt from API stability** - Always use current APIs, never deprecated ones

#### Running Tests
```bash
uv run pytest -n auto               # All tests, parallel
uv run pytest -n auto -m "unit and not slow"  # Quick unit tests
uv run pytest tests/rust_integration/ -v       # Rust integration tests
```

### Git Workflow

#### Branching Strategy
- **main** - Stable release branch
- **feature/** - New features
- **fix/** - Bug fixes
- **docs/** - Documentation updates

#### Commit Conventions
- Use clear, descriptive commit messages
- Reference issues where applicable
- Keep commits atomic and focused

#### CI Pipeline (GitHub Actions)
- Python Linting (Ruff)
- Rust Linting (Clippy + rustfmt)
- Rust Build and Test
- Python Bindings Build (Maturin)
- Python Test Suite (pytest)
- Type Checking (mypy, non-blocking)

## Domain Context

### Crash Log Analysis
CLASSIC analyzes crash logs from Bethesda games to identify:
- **Crash patterns** - Known crash signatures from the community dictionary
- **Problematic mods** - Mods associated with stability issues
- **Configuration errors** - Invalid INI settings, missing requirements
- **Plugin conflicts** - Load order issues, incompatible mods

### Supported Games
- **Fallout 4** (primary focus of this repository)
- **Skyrim Special Edition** (separate repository: CLASSIC-Skyrim)

### Key Terminology
- **Buffout 4** - Crash logger mod that generates crash logs
- **FCX Mode** - File Configuration eXaminer (read-only configuration detection)
- **xSE** - Script Extender (F4SE for Fallout 4)
- **FormID** - Unique identifier for game objects/records
- **Plugin** - .esp/.esm/.esl mod files

### YAML Configuration
The application uses YAML files in `CLASSIC Data/` for:
- Crash pattern dictionaries
- Plugin compatibility databases
- User settings
- Game-specific configurations

## Important Constraints

### Technical Constraints
- **Python 3.12+** required (not compatible with older versions)
- **Windows primary** - Primary development and testing on Windows
- **uv package manager** - Do NOT use `pip install` for normal use

### API Constraints
- **API compatibility priority** - Maintain backward compatibility with deprecation warnings
- **Production code stability** - Tests are exempt; production code must not break existing APIs
- **PyO3 type stubs required** - All `-py` crates must have `.pyi` stub files

### Performance Constraints
- **Rust acceleration mandatory** for performance-critical paths
- **File I/O must use async** where possible (FileIOCore)
- **Batch YAML loading** - Load multiple settings together

### Safety Constraints
- **FCX mode is read-only** - Never modifies game files, only detects issues
- **No auto-fix functions** - Removed to prevent accidental file corruption

## External Dependencies

### Rust Crates (Key Dependencies)
- **PyO3 0.26.0** - Python bindings
- **Tokio** - Async runtime
- **yaml-rust2** - YAML parsing
- **serde** - Serialization
- **regex** - Pattern matching
- **rusqlite** - SQLite database

### Python Packages (Key Dependencies)
- **PySide6** - Qt bindings for GUI
- **aiofiles** - Async file operations
- **aiosqlite** - Async SQLite
- **chardet** - Character encoding detection

### External Services
- **GitHub Actions** - CI/CD
- **Nexus Mods** - Mod hosting (for update checking)

### Game Files (Read-Only Access)
- Crash logs from `%LOCALAPPDATA%/Fallout4/`
- Game INI files from `Documents/My Games/Fallout4/`
- Plugin list from game installation directory

## Quick Reference

### Development Commands
```bash
# Setup
uv sync --all-extras

# Run application
uv run python CLASSIC_Interface.py  # GUI
uv run python CLASSIC_ScanLogs.py   # CLI

# Testing
uv run pytest -n auto -m "unit and not slow"

# Linting
uv run ruff check .
uv run ruff format .

# Build Rust
./rebuild_rust.ps1              # All crates
./rebuild_rust.ps1 yaml         # Specific crate
```

### Key Files
- `CLAUDE.md` - Comprehensive development guide
- `pyproject.toml` - Python project configuration
- `rust/Cargo.toml` - Rust workspace manifest
- `CLASSIC Data/` - Configuration and data files
