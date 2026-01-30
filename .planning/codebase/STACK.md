# Technology Stack

**Analysis Date:** 2026-01-29

## Languages

**Primary:**
- Python 3.12+ - GUI (PySide6), CLI, TUI, async orchestration, business logic

**Secondary:**
- Rust 1.85.0 - Performance-critical operations (YAML parsing, log scanning, file I/O, database operations) with 10-150x speedups

## Runtime

**Environment:**
- Python 3.12+ (requires-python >= 3.12, < 3.15)
- Rust stable (edition 2024, MSRV 1.85.0)

**Package Manager:**
- uv (modern Python package manager) - Primary
- pip (fallback for Rust wheel installation: `uv pip install -e .`)
- Cargo (Rust package manager)
- maturin (Rust-to-Python wheel builder)
- Lockfiles: uv.lock (Python), Cargo.lock (Rust)

## Frameworks

**Core UI:**
- PySide6 >= 6.8.0 - Qt-based GUI application (`CLASSIC_Interface.py`)
- Textual >= 0.50.0 - TUI framework for terminal interface (`ClassicLib.TUI`, entry point `classic-tui`)
- qasync >= 0.28.0 - Qt event loop integration with asyncio

**Async & Concurrency:**
- asyncio - Native Python async runtime
- aiohttp >= 3.10.10 - Async HTTP client for API calls
- aiofiles >= 25.1.0 - Async file I/O wrapper
- aiosqlite >= 0.21.0 - Async SQLite interface
- Tokio 1.49.0 - Rust async runtime (single global instance via `classic-shared::get_runtime()`)
- rayon 1.10 - Rust data parallelism
- crossbeam 0.8 - Rust concurrency primitives

**Testing:**
- pytest >= 9.0.2 - Test runner
- pytest-asyncio >= 1.3.0 - Async test support
- pytest-cov >= 7.0.0 - Coverage reporting
- pytest-qt >= 4.4.0 - Qt/PySide6 testing
- pytest-timeout >= 2.4 - Test timeout enforcement
- pytest-textual-snapshot >= 1.0.0 - TUI snapshot testing
- pytest-benchmark >= 5.2.3 - Performance benchmarking
- hypothesis >= 6.140.2 - Property-based testing
- pyright >= 1.1.405 - Static type checking
- mypy >= 1.12.0 - Type checking (strict mode)

**Build/Dev:**
- maturin >= 1.9.4, < 2.0 - Build Rust extensions into Python wheels
- PyInstaller >= 6.16.0 - Bundle applications into Windows executables
- PyInstaller-hooks-contrib >= 2025.0 - Plugin hooks for bundling
- ruff >= 0.11.0 - Python linter and formatter
- setuptools >= 80.9.0 - Python package build backend
- pyinstaller-rust-helper - Custom helper for bundling Rust extensions

## Key Dependencies

**Critical:**
- classic_yaml (Rust/PyO3) - YAML parsing via yaml-rust2 (15-30x faster than ruamel.yaml)
- classic_database (Rust/PyO3) - SQLite database pooling (25x faster than pure Python)
- classic_scanlog (Rust/PyO3) - Crash log parsing and analysis (10-50x speedup)
- classic_file_io (Rust/PyO3) - Async file operations with encoding detection
- classic_settings (Rust/PyO3) - Configuration management
- classic_registry (Rust/PyO3) - Game version registry and plugin detection

**Text Processing:**
- beautifulsoup4 >= 4.12.3 - HTML/XML parsing
- ruamel-yaml >= 0.18.6 - YAML handling (fallback to pure Python)
- tomlkit >= 0.13.2 - TOML file parsing
- regex >= 2025.11.3 - Advanced regex with named groups
- iniparse >= 0.5 - INI file parsing
- chardet >= 5.2.0 - Character encoding detection
- markdown2 >= 2.5.4 - Markdown rendering
- pyclip >= 0.7.0 - TUI clipboard access

**Network & HTTP:**
- requests >= 2.32.3 - Synchronous HTTP client (pastebin fetching)
- urllib3 >= 2.2.3 - HTTP library (requests dependency)
- aiohttp >= 3.10.10 - Async HTTP (GitHub API, pastebin async)
- reqwest 0.13.1 (Rust) - Async HTTP for Rust code

**File & Path Handling:**
- pathlib - Standard library path operations (exclusive, no string paths)
- appdirs >= 1.4.4 - Platform-specific app data directories
- pefile < 2024.8.26 - Executable file parsing
- pyffi >= 2.2.2 - Win32 type definitions
- ba2 3.0.1 (Rust) - Bethesda Archive 2 format support

**Utilities:**
- typed-argument-parser >= 1.10.1 - CLI argument parsing
- packaging >= 25.0 - Version comparison and parsing
- tqdm >= 4.67.1 - Progress bars (CLI only)
- pillow >= 12.0.0 - Image processing for GUI icons
- pyperclip >= 1.11.0 - Clipboard access
- psutil >= 7.0.0 - Process/system utilities
- lasso 0.7 (Rust) - String interning for optimization

**Windows-Specific:**
- pywin32 >= 310 - Windows API access (conditional: sys_platform == 'win32')

**Rust Core Libraries:**
- yaml-rust2 0.11.0 - Pure Rust YAML 1.2 parsing
- serde 1.0 - Serialization framework
- serde_json 1.0 - JSON serialization
- thiserror 2.0 - Error handling
- anyhow 1.0 - Error context
- tokio 1.49.0 - Async runtime
- futures 0.3 - Async utilities

**Rust Concurrency & Performance:**
- dashmap 6.1 - Concurrent hash map
- parking_lot 0.12.5 - Better mutexes/RwLocks than std
- once_cell 1.20 - Lazy static initialization
- rayon 1.10 - Data parallelism
- crossbeam 0.8 - Channels, work-stealing
- lru 0.16.3 - LRU cache
- quick_cache 0.6 - Lock-free concurrent cache
- rustc-hash 2.1 - Fast hash for short strings
- xxhash-rust 0.8 - Fast non-crypto hashing

**Rust Database:**
- rusqlite 0.38.0 - SQLite with bundled library
- sqlx 0.8 - Async SQL toolkit (compile-time checked)

**Rust GUI (Slint):**
- slint 1.14.1 - Declarative UI framework (optional for Rust apps)

## Configuration

**Environment:**
- `.env` - GitHub API token (GITHUB_TOKEN)
- `pyproject.toml` - Python package config, dependencies, tool settings
- `rust/Cargo.toml` - Rust workspace manifest with shared dependencies
- `CLASSIC.spec` - PyInstaller bundling spec for executable generation
- `.ruff.toml` - Ruff linter/formatter config (indent=4, line-length=140)
- `pyproject.toml [tool.pyright]` - Strict type checking config
- `pyproject.toml [tool.mypy]` - MyPy strict mode config

**Build:**
- `rebuild_rust.ps1` - PowerShell script for rebuilding all Rust modules with maturin
- `maturin.toml` (implicit) - Maturin config for each `-py` crate
- `CLASSIC.spec` - PyInstaller spec for GUI executable

## Platform Requirements

**Development:**
- Python 3.12+ with pip/uv
- Rust 1.85.0+
- PowerShell 5.1+ (Windows) for build scripts
- Git for version control
- C compiler (MSVC on Windows for PyO3 compilation)

**Production:**
- Windows 10+ (primary target)
- Fallout 4 or Skyrim installation (for game data analysis)
- ~200MB disk space for application + data files
- No external services required (offline-capable)

---

*Stack analysis: 2026-01-29*
