# Suggested Commands for CLASSIC-Fallout4 Development

## Essential Development Commands

### Running the Application
```bash
# Run different interfaces
uv run python CLASSIC_Interface.py     # GUI mode (main)
uv run python CLASSIC_ScanLogs.py     # CLI mode
uv run python CLASSIC_ScanGame.py     # Game integrity checker
```

### Testing Commands
```bash
# Run all tests with parallel execution
uv run pytest tests/ -n 4 -v

# Quick test run with summary
uv run pytest tests/ -n 4 -q

# Run specific test file
uv run pytest tests/core/test_crash_log_processing.py -n 4 -v

# Run tests by marker
uv run pytest -n 4 -m "unit and not slow"    # Fast unit tests
uv run pytest -n 4 -m "integration"           # Integration tests
uv run pytest -n 4 -m "async_test"           # Async tests
uv run pytest -n 4 -m "not performance"      # Skip performance tests

# Run with coverage
uv run pytest --cov=. --cov-report=html --cov-report=term

# Auto-detect CPU cores for parallel execution
uv run pytest -n auto
```

### Code Quality Commands
```bash
# Linting
uv run ruff check .
uv run ruff format .

# Type checking
uv run mypy .
uv run pyright

# Pre-commit hooks
uv run pre-commit install              # Install hooks
uv run pre-commit run --all-files     # Run on all files
uv run pre-commit run                 # Run on staged files
```

### Build Commands
```bash
# Build Windows executable
uv run pyinstaller --clean --upx-dir 'C:\\Path\\to\\UPX' .\\CLASSIC.spec

# Install/update dependencies
uv sync --all-extras
uv lock --upgrade    # Update to latest versions
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
uv run ruff format .                  # Format code
uv run ruff check . --fix            # Fix linting issues
uv run pytest -n 4 -m "unit and not slow"  # Quick tests

# Full validation
uv run ruff check .
uv run mypy .
uv run pytest tests/ -n 4
```

## Notes
- Always use `uv run` prefix for Python commands to ensure virtual environment
- Use terminal for running tests (VS Code test tool has freezing issues)
- Tests use `-n 4` for parallel execution (adjust based on CPU cores)
- UPX path needed for building compressed executables
