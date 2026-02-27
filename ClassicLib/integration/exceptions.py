"""Rust integration exception types.

This module defines a typed exception hierarchy for Rust errors, including
startup binding validation failures (import vs initialization) so entrypoints
can report precise, actionable diagnostics.
"""


class RustError(Exception):
    """Base exception for all Rust integration errors.

    All Rust-originated errors inherit from this class, making it easy to
    catch all Rust errors generically if needed, while also allowing
    specific error types for targeted handling.

    Example:
        >>> try:
        ...     rust_operation()
        ... except RustIOError as e:
        ...     print(f"File error: {e}")
        ... except RustError as e:
        ...     print(f"Other Rust error: {e}")

    """


def get_rust_rebuild_remediation() -> str:
    """Return standardized remediation text for missing/broken Rust bindings."""
    return "Rebuild and reinstall Rust bindings with `pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1`."


class RustBindingError(RustError):
    """Base error for required Rust binding failures."""

    def __init__(self, binding: str, failure_type: str, details: str) -> None:
        self.binding = binding
        self.failure_type = failure_type
        self.details = details
        message = f"Rust binding failure ({failure_type}) for '{binding}': {details}. {get_rust_rebuild_remediation()}"
        super().__init__(message)


class RustBindingImportError(RustBindingError, ImportError):
    """Raised when a required Rust binding cannot be imported."""

    def __init__(self, binding: str, details: str) -> None:
        super().__init__(binding=binding, failure_type="import", details=details)


class RustBindingInitError(RustBindingError, RuntimeError):
    """Raised when a required Rust binding imports but cannot initialize."""

    def __init__(self, binding: str, details: str) -> None:
        super().__init__(binding=binding, failure_type="initialization", details=details)


class RustIOError(RustError, IOError):
    """Rust file I/O errors.

    Raised when Rust encounters file system errors such as:
    - File not found
    - Permission denied
    - Disk full
    - Invalid file descriptor

    This inherits from both RustError and IOError to maintain compatibility
    with standard Python error handling patterns.

    Example:
        >>> try:
        ...     yaml_ops.load_yaml_file("/nonexistent.yaml")
        ... except RustIOError as e:
        ...     print(f"Cannot read file: {e}")

    """


class RustParseError(RustError, ValueError):
    """Rust parsing errors.

    Raised when Rust fails to parse data due to:
    - Invalid format
    - Corrupt data
    - Unexpected structure
    - Encoding issues

    This inherits from ValueError since parse errors typically indicate
    invalid input data.

    Example:
        >>> try:
        ...     yaml_ops.parse_yaml("invalid: yaml: content")
        ... except RustParseError as e:
        ...     print(f"Parse failed: {e}")

    """


class RustConfigError(RustError, ValueError):
    """Rust configuration errors.

    Raised when Rust encounters configuration issues:
    - Missing required settings
    - Invalid configuration values
    - Type mismatches in config
    - Conflicting options

    Example:
        >>> try:
        ...     config_ops.load_config({"invalid_key": "value"})
        ... except RustConfigError as e:
        ...     print(f"Configuration error: {e}")

    """


class RustDatabaseError(RustError):
    """Rust database errors.

    Raised when Rust encounters database operation failures:
    - Connection errors
    - Query failures
    - Transaction errors
    - Schema mismatches

    Example:
        >>> try:
        ...     db_ops.query_formids(["invalid"])
        ... except RustDatabaseError as e:
        ...     print(f"Database error: {e}")

    """


class RustMemoryError(RustError, MemoryError):
    """Rust memory errors.

    Raised when Rust encounters memory-related errors:
    - Out of memory
    - Allocation failures
    - Buffer overflows (caught)

    This is rare but can occur with extremely large files or datasets.

    Example:
        >>> try:
        ...     file_ops.read_large_file("/huge/file.dat")
        ... except RustMemoryError as e:
        ...     print(f"Out of memory: {e}")

    """


class RustConcurrencyError(RustError):
    """Rust concurrency errors.

    Raised when Rust encounters async/threading issues:
    - Tokio runtime errors
    - Task cancellation
    - Deadlock detection
    - Channel errors

    Example:
        >>> try:
        ...     async_ops.run_parallel_tasks(tasks)
        ... except RustConcurrencyError as e:
        ...     print(f"Concurrency error: {e}")

    """


# Export all exception types
__all__ = [
    "RustError",
    "RustBindingError",
    "RustBindingImportError",
    "RustBindingInitError",
    "get_rust_rebuild_remediation",
    "RustIOError",
    "RustParseError",
    "RustConfigError",
    "RustDatabaseError",
    "RustMemoryError",
    "RustConcurrencyError",
]
