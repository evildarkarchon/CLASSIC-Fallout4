# Technology Stack - CLASSIC

## Backend & Core Logic
- **Python 3.12+:** The primary language for application logic, CLI, and GUI integration.
- **Rust:** Used for performance-critical components (scanning, bindings) and specialized low-level tasks.
- **PyO3 & Maturin:** The bridge between Python and Rust, enabling high-performance Rust extensions to be used seamlessly in Python.

## User Interface
- **PySide6 (Qt for Python):** The framework for the graphical user interface, providing a cross-platform, professional desktop experience.

## Data & Persistence
- **SQLite:** Used for high-efficiency information retrieval for large data sets that exceed the practical limits of YAML, such as the FormID database.
- **YAML:** The standard format for primary configuration files, structured data exchange, and smaller data sets.

## Development & Build Tools
- **uv:** The universal Python package manager for fast, reliable dependency resolution and virtual environment management.
- **PyInstaller:** Used to package the application into standalone Windows executables.
- **Maturin:** Used to build and publish the Rust-based Python extensions.
- **pytest:** The framework for automated testing of Python components.
