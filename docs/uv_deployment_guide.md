# CLASSIC-Fallout4 uv Deployment Guide

## Overview

This project uses **uv** as its package and project manager instead of Poetry or pip. uv is a Rust-based Python package manager that offers 10-100x faster performance compared to traditional tools while maintaining compatibility with the Python ecosystem.

## Why uv?

- **Speed**: 10-100x faster than pip, pip-tools, or Poetry
- **All-in-one**: Replaces pip, pip-tools, poetry, pyenv, pipx, and virtualenv
- **Reproducible builds**: Lock files ensure consistent deployments
- **Intelligent caching**: Reduces redundant downloads and installations
- **Cross-platform**: Works seamlessly on Windows, macOS, and Linux
- **GitHub-friendly**: Perfect for projects distributed via GitHub rather than PyPI

## Installation

### Installing uv

#### Windows (PowerShell)
```powershell
# Using PowerShell installer
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or using pip (slower)
pip install uv
```

#### macOS/Linux
```bash
# Using curl
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using pip
pip install uv
```

## Project Setup

### 1. Clone from GitHub
```bash
git clone https://github.com/your-username/CLASSIC-Fallout4.git
cd CLASSIC-Fallout4
```

### 2. Install Dependencies
```bash
# Basic installation (core dependencies only)
uv sync

# Install with all optional features (recommended for development)
uv sync --all-extras

# Install specific extras
uv sync --extra tui      # Terminal UI support
uv sync --extra cli      # CLI progress bars
uv sync --extra windows  # Windows-specific features
```

### 3. Python Version Management
```bash
# uv automatically manages Python versions
# Check Python version requirement
uv python list

# Install required Python version if needed
uv python install 3.12

# Pin Python version for the project
uv python pin 3.12
```

## Development Workflow

### Running the Application
```bash
# GUI Mode (PySide6)
uv run python CLASSIC_Interface.py

# Terminal UI Mode (Textual)
uv run python CLASSIC_TUI.py

# CLI Mode
uv run python CLASSIC_ScanLogs.py --help

# Game Integrity Checker
uv run python CLASSIC_ScanGame.py
```

### Running Tests
```bash
# Run all tests with parallel execution
uv run pytest -n auto

# Run specific test categories
uv run pytest -m "unit and not slow"     # Quick unit tests
uv run pytest -m "integration"           # Integration tests
uv run pytest -m "gui"                   # GUI-dependent tests

# Run with coverage
uv run pytest --cov=. --cov-report=html
```

### Code Quality
```bash
# Linting
uv run ruff check .
uv run ruff format .

# Type checking
uv run mypy .
uv run pyright

# Pre-commit hooks
uv run pre-commit install
uv run pre-commit run --all-files
```

## Dependency Management

### Adding Dependencies
```bash
# Add a production dependency
uv add requests

# Add a development dependency
uv add --dev pytest

# Add with version constraints
uv add "pyside6>=6.8.0"
```

### Updating Dependencies
```bash
# Update all dependencies to latest compatible versions
uv lock --upgrade

# Update specific package
uv lock --upgrade-package pyside6

# Check for outdated packages
uv pip list --outdated
```

### Lock File Management
```bash
# Generate/update lock file
uv lock

# Sync environment with lock file
uv sync

# Export requirements for compatibility
uv export > requirements.txt
uv export --dev > requirements-dev.txt
```

## Building for Distribution

### Creating Standalone Executables

#### Windows Executable with PyInstaller
```bash
# Build GUI executable
uv run pyinstaller --clean CLASSIC.spec

# Build CLI-only executable (smaller)
uv run pyinstaller --clean CLASSIC-CLI.spec

# With UPX compression (smaller file size)
uv run pyinstaller --clean --upx-dir "C:\\Path\\to\\UPX" CLASSIC.spec
```

### GitHub Release Distribution

Since this project is distributed via GitHub rather than PyPI:

1. **Create a Release Archive**:
```bash
# Create distribution archive with all necessary files
uv build --wheel
uv export > requirements.txt

# Package for GitHub release
tar -czf CLASSIC-v8.0.0.tar.gz \
  CLASSIC*.py \
  ClassicLib/ \
  "CLASSIC Data/" \
  pyproject.toml \
  uv.lock \
  requirements.txt \
  README.md \
  LICENSE
```

2. **GitHub Actions Workflow** (`.github/workflows/release.yml`):
```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        run: |
          powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

      - name: Build executable
        run: |
          uv sync --all-extras
          uv run pyinstaller --clean CLASSIC.spec

      - name: Upload Release Assets
        uses: softprops/action-gh-release@v1
        with:
          files: |
            dist/CLASSIC.exe
            requirements.txt
            uv.lock
```

## Migration from Poetry

### For Developers

If you have an existing Poetry environment:

1. **Remove Poetry virtual environment**:
```bash
# Deactivate if active
deactivate

# Remove Poetry files
rm -rf .venv poetry.lock
# Windows: rmdir /s .venv && del poetry.lock
```

2. **Install uv and sync**:
```bash
# Install uv
pip install uv

# Sync project with uv
uv sync --all-extras
```

3. **Update IDE configuration**:
   - **VS Code**: uv automatically creates `.venv` that VS Code detects
   - **PyCharm**: Point to `.venv/Scripts/python.exe` (Windows) or `.venv/bin/python` (Unix)

### Command Mapping

| Poetry Command | uv Equivalent |
|---------------|---------------|
| `poetry install` | `uv sync` |
| `poetry add package` | `uv add package` |
| `poetry add -D package` | `uv add --dev package` |
| `poetry remove package` | `uv remove package` |
| `poetry run python script.py` | `uv run python script.py` |
| `poetry shell` | `source .venv/bin/activate` or `.venv\Scripts\activate` |
| `poetry lock` | `uv lock` |
| `poetry update` | `uv lock --upgrade` |
| `poetry show` | `uv pip list` |
| `poetry build` | `uv build` |

## Performance Tips

### Caching
```bash
# uv caches packages globally by default
# View cache info
uv cache dir

# Clean cache if needed
uv cache clean
```

### Parallel Operations
```bash
# uv uses parallel downloads by default
# Control parallelism
UV_CONCURRENT_DOWNLOADS=10 uv sync
```

### CI/CD Optimization
```yaml
# GitHub Actions with caching
- uses: actions/cache@v3
  with:
    path: ~/.cache/uv
    key: uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}
```

## Troubleshooting

### Common Issues

1. **"uv: command not found"**
   - Ensure uv is in your PATH
   - Restart terminal after installation
   - Try: `python -m uv` instead

2. **Lock file conflicts**
   ```bash
   # Regenerate lock file
   rm uv.lock
   uv lock
   ```

3. **Python version mismatch**
   ```bash
   # Install correct Python version
   uv python install 3.12
   uv python pin 3.12
   ```

4. **Dependency resolution issues**
   ```bash
   # Clear cache and retry
   uv cache clean
   uv sync --refresh
   ```

## Environment Variables

```bash
# Set in your shell profile or .env file
export UV_INDEX_URL=https://pypi.org/simple  # Custom package index
export UV_CACHE_DIR=~/.cache/uv              # Cache location
export UV_VIRTUALENV=.venv                   # Virtual environment location
export UV_COMPILE_BYTECODE=1                 # Pre-compile Python files
```

## Advanced Usage

### Workspace Management (Monorepo)
```toml
# pyproject.toml for workspace
[tool.uv.workspace]
members = ["packages/*", "apps/*"]
```

### Custom Package Sources
```toml
[tool.uv]
index-url = "https://pypi.org/simple"
extra-index-url = ["https://download.pytorch.org/whl/cpu"]
```

### Platform-Specific Dependencies
```toml
[project.dependencies]
pywin32 = { version = ">=306", markers = "sys_platform == 'win32'" }
```

## Best Practices

1. **Always commit `uv.lock`** for reproducible builds
2. **Use `uv sync` instead of `uv install`** to respect the lock file
3. **Run `uv lock --upgrade` periodically** to get security updates
4. **Use `--all-extras` for development** to ensure all features work
5. **Cache uv directory in CI/CD** for faster builds
6. **Document Python version** in README and pyproject.toml

## Resources

- [uv Documentation](https://docs.astral.sh/uv/)
- [uv GitHub Repository](https://github.com/astral-sh/uv)
- [Migration Guide](https://docs.astral.sh/uv/guides/migrations/)
- [Performance Benchmarks](https://docs.astral.sh/uv/benchmarks/)

## Support

For CLASSIC-specific issues:
- Open an issue on [GitHub](https://github.com/your-username/CLASSIC-Fallout4/issues)
- Check existing [uv migration issues](https://github.com/your-username/CLASSIC-Fallout4/issues?q=label:uv)

For uv-related issues:
- [uv Discord](https://discord.gg/astral)
- [uv GitHub Issues](https://github.com/astral-sh/uv/issues)
