# Suggested Commands for CLASSIC-Fallout4 Development

## Essential Development Commands

### Running the Application
```bash
# Run different interfaces
poetry run python CLASSIC_Interface.py     # GUI mode (main)
poetry run python CLASSIC_TUI.py          # Terminal UI mode
poetry run python CLASSIC_ScanLogs.py     # CLI mode
poetry run python CLASSIC_ScanGame.py     # Game integrity checker
```

### Testing Commands
```bash
# Run all tests with parallel execution
poetry run python -m pytest tests/ -n 4 -v

# Quick test run with summary
poetry run python -m pytest tests/ -n 4 -q

# Run specific test file
poetry run python -m pytest tests/core/test_crash_log_processing.py -n 4 -v

# Run tests by marker
poetry run python -m pytest -n 4 -m "unit and not slow"    # Fast unit tests
poetry run python -m pytest -n 4 -m "integration"           # Integration tests
poetry run python -m pytest -n 4 -m "async_test"           # Async tests
poetry run python -m pytest -n 4 -m "not performance"      # Skip performance tests

# Run with coverage
poetry run python -m pytest --cov=. --cov-report=html --cov-report=term

# Auto-detect CPU cores for parallel execution
poetry run python -m pytest -n auto
```

### Code Quality Commands
```bash
# Linting
poetry run ruff check .
poetry run ruff format .

# Type checking
poetry run mypy .
poetry run pyright

# Pre-commit hooks
poetry run pre-commit install              # Install hooks
poetry run pre-commit run --all-files     # Run on all files
poetry run pre-commit run                 # Run on staged files
```

### Build Commands
```bash
# Build Windows executable
poetry run pyinstaller --clean --upx-dir 'C:\\Path\\to\\UPX' .\\CLASSIC.spec

# Install/update dependencies
poetry install
poetry up --latest    # Update to latest versions
```

### Windows System Commands
```bash
# Git commands
git status
git diff
git log --oneline -10
git add .
git commit -m "message"

# Directory navigation (Windows)
dir                    # List files (Windows equivalent of ls)
cd path\\to\\directory  # Change directory
type filename.txt      # View file contents (Windows equivalent of cat)

# PowerShell alternatives
ls                     # Works in PowerShell
pwd                    # Print working directory
```

### Development Workflow Commands
```bash
# Before committing
poetry run ruff format .                  # Format code
poetry run ruff check . --fix            # Fix linting issues
poetry run python -m pytest -n 4 -m "unit and not slow"  # Quick tests

# Full validation
poetry run ruff check .
poetry run mypy .
poetry run python -m pytest tests/ -n 4
```

## Notes
- Always use `poetry run` prefix for Python commands to ensure virtual environment
- Use terminal for running tests (VS Code test tool has freezing issues)
- Tests use `-n 4` for parallel execution (adjust based on CPU cores)
- UPX path needed for building compressed executables
