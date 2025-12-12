# Python Documentation Standards

**CRITICAL**: All Python code MUST have detailed docstrings following the Google Python Style Guide. Missing or incomplete docstrings are treated as errors.

## Requirements
- All modules require a module-level docstring at the top of the file
- All public classes, functions, and methods require docstrings
- All public class attributes and constants require documentation
- Use Google-style docstring format (not NumPy or Sphinx)
- Include complete type information in docstrings (even with type hints)
- Document all parameters, return values, raises, yields, and examples where applicable

## Google Docstring Format

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

## Documentation Requirements by Scope

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

## Special Cases
- **`__init__`**: Always document parameters and any exceptions
- **Private methods** (`_method`): Optional but recommended for complex logic
- **Test functions**: Docstring should describe what is being tested
- **Async functions**: Note async behavior and any AsyncBridge usage
- **Deprecated code**: Include `Deprecated:` section with migration path

## Anti-Patterns to Avoid
- No docstring -> Complete Google-style docstring
- Single-line "Returns result" -> Detailed description
- Missing Args/Returns sections -> Complete documentation
- No examples for complex APIs -> Include usage examples
- Outdated docstrings -> Update docs with code changes

## Enforcement
- Ruff will warn about missing docstrings (treat as errors)
- Code reviews must verify docstring completeness
- All new code requires docstrings before PR approval
