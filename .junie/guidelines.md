# CLASSIC-Fallout4 Development Guidelines

This document provides essential information for advanced developers working on the CLASSIC-Fallout4 project - a comprehensive crash log analysis tool for Fallout 4 with multiple interfaces (GUI, TUI, CLI).

## Build/Configuration Instructions

### Prerequisites
- **Python**: Requires Python 3.12 or 3.13 (strictly `>=3.12,<3.14`)
- **Package Manager**: Uses uv for dependency management
- **Virtual Environment**: Recommended (uv handles this automatically)

### Setup Process
1. **Install uv** (if not already installed):
   ```bash
   # Windows (PowerShell)
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install Dependencies**:
   ```bash
   uv sync --all-extras
   ```
   This installs all dependencies including development tools.

3. **Install Optional Dependencies**:
   - For CLI features: `uv sync --extra cli`
   - For Windows-specific features: `uv sync --extra windows`

### Application Entry Points
The project has multiple interfaces:
- **GUI Interface**: `CLASSIC_Interface.py` (PySide6-based)
- **CLI Scanning**: `CLASSIC_ScanLogs.py`, `CLASSIC_ScanGame.py`
- **TUI Interface**: Rust-based TUI (Ratatui) available separately

### Key Architecture Components
- **ClassicLib/**: Core library containing all functionality
  - `AsyncCore/`: Asynchronous processing components
  - `Interface/`: GUI mixins and components (PySide6)
  - `ScanGame/`: Game file scanning functionality
  - `ScanLog/`: Crash log analysis core
- **SetupCoordinator**: Handles application initialization
- **GlobalRegistry**: Centralized configuration management
- **YamlSettingsCache**: Settings persistence

## Testing Information

### Test Configuration
The project uses pytest with comprehensive configuration:
- **Test Discovery**: `tests/` directory, `test_*.py` files
- **Async Support**: Automatic asyncio mode enabled
- **Coverage**: Minimum 85% required, reports in multiple formats

### Available Test Markers
Use these markers to categorize and run specific test types:
- `@pytest.mark.unit`: Fast, isolated unit tests
- `@pytest.mark.integration`: Multi-component integration tests  
- `@pytest.mark.slow`: Time-intensive tests
- `@pytest.mark.asyncio`: Async/await pattern tests
- `@pytest.mark.gui`: GUI-dependent tests (Qt required)
- `@pytest.mark.performance`: Performance/benchmark tests
- `@pytest.mark.file_io`: File I/O operation tests
- `@pytest.mark.network`: Network connectivity tests
- `@pytest.mark.e2e`: End-to-end integration tests

### Running Tests

#### Basic Test Execution
```bash
# Run all tests
python -m pytest

# Run with verbose output
python -m pytest -v

# Run specific test file
python -m pytest tests/test_async_util.py

# Run tests with coverage
python -m pytest --cov --cov-report=term
```

#### Filtering Tests by Markers
```bash
# Run only unit tests
python -m pytest -m "unit"

# Run tests except slow ones
python -m pytest -m "not slow"

# Run integration and performance tests
python -m pytest -m "integration or performance"

# Exclude GUI tests (useful for CI)
python -m pytest -m "not gui"
```

### Test Fixtures Available
The `conftest.py` provides comprehensive fixtures:
- `mock_global_registry`: Mocked GlobalRegistry
- `mock_yaml_settings`: Mocked YAML settings cache
- `sample_crash_logs_dir`: Sample crash log files
- `mock_network_responses`: HTTP response mocking
- `async_cleanup`: Async resource cleanup
- `temp_game_installation`: Temporary game directory

### Adding New Tests
1. **Create test file**: Follow `test_*.py` naming convention
2. **Use appropriate markers**: Tag tests with relevant markers
3. **Leverage fixtures**: Use existing fixtures from conftest.py
4. **Async tests**: Use `@pytest.mark.asyncio` for async functionality
5. **Isolation**: Ensure tests don't depend on external state

#### Example Test Structure
```python

import pytest
from ClassicLib.SomeModule import SomeClass

class TestSomeFeature:
    @pytest.mark.unit
    def test_basic_functionality(self):
        """Test basic functionality."""
        instance = SomeClass()
        result = instance.some_method()
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_async_functionality(self, mock_global_registry):
        """Test async functionality with mocked registry."""
        instance = SomeClass()
        result = await instance.async_method()
        assert result == expected_value
```

## Code Style and Development Practices

### Linting and Formatting
The project uses multiple tools for code quality:

#### Ruff (Primary Linter)
- **Line Length**: 140 characters
- **Quote Style**: Double quotes
- **Import Sorting**: Enabled with comprehensive rules
- **Enabled Rules**: Type annotations, async best practices, performance anti-patterns, modernization suggestions

#### MyPy (Type Checking)  
- **Mode**: Standard type checking with NewGenericSyntax support
- **Disabled Checks**: Some redundant checks disabled (covered by Ruff)
- **Configuration**: Allows incomplete features for forward compatibility

#### Black (Code Formatting)
- **Line Length**: 140 characters  
- **Target Versions**: Python 3.12, 3.13
- **Integration**: Works alongside Ruff

### Development Commands
```bash
# Format code
uv run ruff format .

# Check for linting issues
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .

# Type checking
uv run mypy .

# Run all quality checks
uv run ruff check . && uv run mypy . && uv run pytest
```

### Code Style Guidelines

#### General Practices
- **Type Hints**: Required for all public APIs and complex functions
- **Docstrings**: Use for classes and public methods
- **Async/Await**: Prefer async patterns for I/O operations
- **Error Handling**: Use specific exception types, avoid bare except
- **Imports**: Group and sort according to Ruff configuration

#### Project-Specific Patterns
- **Mixins**: GUI functionality organized into focused mixins
- **Global Registry**: Use for configuration access across modules
- **Settings Cache**: Use YamlSettingsCache for persistent settings
- **Message Handling**: Use centralized MessageHandler for user communication
- **Resource Management**: Proper async context managers for file operations

#### Architecture Considerations
- **Separation of Concerns**: Keep GUI, TUI, and core logic separated
- **Async Design**: Most I/O operations are async for performance
- **Cross-Platform**: Code should work on Windows and Unix-like systems
- **Unicode Support**: Handle encoding detection for crash logs
- **Thread Safety**: Use appropriate locking for shared resources

### Performance Considerations
- **Async I/O**: Use aiofiles and aiohttp for file/network operations
- **Lazy Loading**: Import heavy modules only when needed
- **Memory Management**: Be conscious of large crash log files
- **Caching**: Use appropriate caching strategies for expensive operations

### Debugging Tips
- **Logging**: Use the ClassicLib.Logger for consistent logging
- **Crash Log Analysis**: Understanding Buffout 4 log formats is crucial
- **Unicode Issues**: Be aware of encoding detection for various log formats
- **GUI Debugging**: Use Qt's debugging tools for PySide6 issues

### Release and Build Process
- **Executable Generation**: Uses PyInstaller with custom specs
- **Dependency Management**: uv handles all dependencies
- **Version Management**: Version defined in pyproject.toml
- **Distribution**: Multiple entry points for different interfaces

### Cleanliness
- If a file is created to verify functionality, and is not meant for the test suite, it should be removed when no longer needed.

This project is mature and complex, focusing on robust crash log analysis with multiple user interfaces. Pay special attention to async patterns, proper resource management, and the separation between core logic and UI layers.