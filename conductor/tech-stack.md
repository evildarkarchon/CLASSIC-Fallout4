# Technology Stack

## Core Languages & Runtimes
*   **Python:** 3.12+ (Primary orchestration and UI)
*   **Rust:** Latest Stable (Performance-critical core logic)

## Application Frameworks
*   **GUI:** PySide6 (Qt binding for Python)
*   **Integration:** PyO3 (Rust bindings for Python)
*   **Async Support:**
    *   **Python:** `qasync` (Qt-asyncio integration), `asyncio`
    *   **Rust:** `tokio` (Async runtime)

## Build & Package Management
*   **Python:** `uv` (Fast package manager and venv management)
*   **Rust:** `cargo` (Standard Rust package manager)
*   **Build System:** `maturin` (Building and publishing Rust extensions as Python packages)
*   **Distribution:** `PyInstaller` (Executable generation)

## Data Storage & Formats
*   **Databases:**
    *   SQLite (via `sqlx`/`rusqlite` in Rust, `aiosqlite` in Python)
*   **Configuration:**
    *   YAML (`yaml-rust2` in Rust, `ruamel.yaml` in Python)
    *   TOML (`tomlkit`)
    *   INI (`iniparse`, `configparser`)

## Testing & Quality Assurance
*   **Python:** `pytest` (Test runner), `pytest-qt`, `pytest-asyncio`
*   **Rust:** `cargo test` (Native testing framework)
*   **Linting:** `ruff` (Python), `clippy` (Rust), `rustfmt`

## Target Platforms
*   **Primary:** Windows (win32) - Main target for Bethesda games support.
*   **Secondary:** Linux (Potential support)
