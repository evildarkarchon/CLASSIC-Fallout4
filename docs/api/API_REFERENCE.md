# CLASSIC API Reference

> **Version**: 2.0.0 | **Python**: 3.12+ | **Rust Acceleration**: Optional (10-150x speedups)

This document provides a comprehensive API reference for the CLASSIC library (`ClassicLib`), including all public interfaces, classes, functions, and patterns.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Module Overview](#module-overview)
3. [Core Components](#core-components)
   - [AsyncBridge](#asyncbridge)
   - [GlobalRegistry](#globalregistry)
   - [MessageHandler](#messagehandler)
   - [YamlSettings](#yamlsettings)
   - [FileIOCore](#fileiocore)
4. [Constants and Enums](#constants-and-enums)
5. [Integration Layer](#integration-layer)
6. [ScanLog Components](#scanlog-components)
7. [Utility Functions](#utility-functions)
8. [Rust Acceleration](#rust-acceleration)

---

## Quick Start

```python
# Basic imports
from ClassicLib import (
    # AsyncBridge (for GUI contexts only)
    AsyncBridge,

    # GlobalRegistry
    Keys, register, get, is_registered, get_game, get_local_dir, is_gui_mode,

    # MessageHandler
    msg_info, msg_warning, msg_error, msg_debug, msg_success, msg_critical,
    init_message_handler, get_message_handler, ProgressContext,

    # YamlSettings
    yaml_settings, classic_settings, yaml_cache, YamlSettingsCache,

    # FileIO
    FileIOCore, read_file_sync, write_file_sync,

    # Constants
    YAML, GameID,

    # Performance
    TimedBlock, timed_operation, async_timed_operation,

    # Logging
    logger, configure_logging, enable_debug_logging,
)

# Check Rust acceleration availability
from ClassicLib import (
    RUST_REGISTRY_AVAILABLE, classic_registry,
    RUST_PERF_AVAILABLE, classic_perf,
    RUST_SETTINGS_AVAILABLE, rust_settings,
    RUST_MESSAGE_AVAILABLE, classic_message,
)
```

---

## Module Overview

| Module | Purpose | Rust Accelerated |
|--------|---------|------------------|
| `AsyncBridge` | Sync/async bridging for GUI | No |
| `GlobalRegistry` | Global object storage | Yes (15-25x) |
| `MessageHandler` | Unified message output | Yes (emoji stripping) |
| `YamlSettings` | Configuration management | Yes (15-30x) |
| `FileIOCore` | File I/O operations | Yes (10x) |
| `ScanLog` | Crash log analysis | Yes (varies) |
| `Constants` | Application constants | No |

---

## Core Components

### AsyncBridge

High-performance bridge between synchronous and asynchronous code. **GUI contexts only.**

> **Warning**: Only use in Qt GUI workers and Qt threads. CLI/TUI code should use native `await`.

#### Import

```python
from ClassicLib.AsyncBridge import AsyncBridge, run_async, run_async_with_timeout
```

#### Class: `AsyncBridge`

```python
class AsyncBridge:
    """Thread-local singleton for sync-to-async bridging."""

    @classmethod
    def get_instance(cls) -> AsyncBridge:
        """Get or create the AsyncBridge instance for the current thread."""

    def run_async(self, coro: Coroutine[Any, Any, T]) -> T:
        """Run an async coroutine from a sync context.

        Args:
            coro: The coroutine to run

        Returns:
            The result of the coroutine

        Raises:
            RuntimeError: If called from within an async context
        """

    def run_async_with_timeout(self, coro: Coroutine[Any, Any, T], timeout: float) -> T:
        """Run an async coroutine with a timeout.

        Args:
            coro: The coroutine to run
            timeout: Maximum time to wait in seconds

        Raises:
            TimeoutError: If the coroutine doesn't complete within timeout
        """

    @classmethod
    def set_metrics_callback(cls, callback: Callable[[str, dict], None] | None) -> None:
        """Set a callback for performance metrics collection."""

    def shutdown(self) -> None:
        """Shutdown the event loop for this thread."""
```

#### Usage Examples

```python
# Basic usage in Qt worker
from ClassicLib.AsyncBridge import AsyncBridge

bridge = AsyncBridge.get_instance()
result = bridge.run_async(fetch_data_async())

# With timeout
result = bridge.run_async_with_timeout(long_operation(), timeout=30.0)

# Context manager (explicit lifecycle)
with AsyncBridge.get_instance() as bridge:
    result = bridge.run_async(async_function())

# Convenience functions
from ClassicLib.AsyncBridge import run_async
result = run_async(async_function())

# Metrics collection
def my_metrics_handler(event: str, metrics: dict):
    print(f"{event}: duration={metrics['duration']:.3f}s, success={metrics['success']}")

AsyncBridge.set_metrics_callback(my_metrics_handler)
```

#### When to Use

| Context | Use | Reason |
|---------|-----|--------|
| Qt GUI workers | `AsyncBridge.run_async()` | Qt threads need sync calls |
| CLI main loop | `await` directly | Already in async context |
| TUI event loop | `await` directly | Already in async context |
| Tests | Mock `bridge.run_async()` | Avoid coroutine warnings |

---

### GlobalRegistry

Thread-safe global storage for sharing objects across modules.

#### Import

```python
from ClassicLib import GlobalRegistry
from ClassicLib.GlobalRegistry import Keys, register, get, is_registered
```

#### Registry Keys

```python
class Keys:
    YAML_CACHE = "yaml_cache"           # YamlCache instance
    MANUAL_DOCS_GUI = "manual_docs_gui" # Manual docs path (GUI)
    GAME_PATH_GUI = "game_path_gui"     # Game path (GUI)
    GAME_PATH = "game_path"             # Game installation path
    DOCS_PATH = "docs_path"             # Documentation path
    IS_GUI_MODE = "is_gui_mode"         # GUI/CLI mode flag
    VR = "gamevars_vr"                  # VR game variables
    GAME = "gamevars_game"              # Game identifier
    LOCAL_DIR = "local_dir"             # Application directory
    IS_PRERELEASE = "is_prerelease"     # Prerelease flag
```

#### Core Functions

```python
def register(key: str, obj: Any) -> None:
    """Register an object in the global registry.

    Args:
        key: Unique identifier for the object
        obj: The object to register

    Raises:
        TypeError: If key is not a string
    """

def get(key: str) -> Any:
    """Retrieve an object from the global registry.

    Returns:
        The registered object or None if not found
    """

def is_registered(key: str) -> bool:
    """Check if a key is registered."""

def unregister(key: str) -> bool:
    """Remove a specific key from the registry.

    Returns:
        True if key was found and removed
    """

def clear() -> None:
    """Clear all entries. TESTING ONLY - raises RuntimeError in production."""
```

#### Convenience Functions

```python
def is_gui_mode() -> bool:
    """Check if application is running in GUI mode."""

def get_game() -> str:
    """Get current game name. Default: 'Fallout4'"""

def get_vr() -> str:
    """Get VR mode status. Returns empty string if not VR."""

def get_local_dir(as_string: bool = False) -> Path | str:
    """Get application local directory."""

def get_yaml_cache() -> Any:
    """Get the YAML cache instance."""
```

#### Usage Examples

```python
from ClassicLib import GlobalRegistry
from ClassicLib.GlobalRegistry import Keys

# Register a value
GlobalRegistry.register(Keys.GAME_PATH, Path("/path/to/game"))

# Retrieve a value
game_path = GlobalRegistry.get(Keys.GAME_PATH)

# Check mode
if GlobalRegistry.is_gui_mode():
    # GUI-specific behavior
    pass
else:
    # CLI/TUI behavior
    pass

# In tests (only works under pytest)
@pytest.fixture(autouse=True)
def clean_registry():
    GlobalRegistry.clear()
    yield
    GlobalRegistry.clear()
```

---

### MessageHandler

Unified message handling for GUI and CLI modes with progress tracking.

#### Import

```python
from ClassicLib.MessageHandler import (
    # Convenience functions
    msg_info, msg_warning, msg_error, msg_debug, msg_success, msg_critical,

    # Initialization
    init_message_handler, get_message_handler,

    # Progress
    msg_progress_context, ProgressContext,

    # Types
    Message, MessageType, MessageTarget,
)
```

#### Message Types

```python
class MessageType(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    DEBUG = "debug"
    SUCCESS = "success"
    CRITICAL = "critical"

class MessageTarget(Enum):
    CONSOLE = "console"
    GUI = "gui"
    LOG = "log"
    ALL = "all"
```

#### Convenience Functions

```python
def msg_info(message: str, **kwargs) -> None:
    """Send an informational message."""

def msg_warning(message: str, **kwargs) -> None:
    """Send a warning message."""

def msg_error(message: str, details: str = None, **kwargs) -> None:
    """Send an error message with optional details."""

def msg_debug(message: str, **kwargs) -> None:
    """Send a debug message (only shown when debug logging enabled)."""

def msg_success(message: str, **kwargs) -> None:
    """Send a success message."""

def msg_critical(message: str, **kwargs) -> None:
    """Send a critical error message."""

def init_message_handler(parent: QWidget = None, is_gui_mode: bool = False) -> MessageHandler:
    """Initialize the global message handler.

    Args:
        parent: Qt parent widget (for GUI mode)
        is_gui_mode: True for GUI, False for CLI
    """

def get_message_handler() -> MessageHandler:
    """Get the current message handler instance."""
```

#### Progress Tracking

```python
from ClassicLib.MessageHandler import msg_progress_context, ProgressContext

# Context manager for progress
with msg_progress_context("Processing files", total=100) as progress:
    for i, file in enumerate(files):
        process(file)
        progress.update(1)  # Update by 1
        # or
        progress.update(1, description=f"Processing {file.name}")

# Manual progress context
progress = ProgressContext("Scanning", total=50)
progress.start()
for i in range(50):
    do_work()
    progress.update(1)
progress.finish()
```

#### Usage Examples

```python
from ClassicLib.MessageHandler import (
    init_message_handler, msg_info, msg_error, msg_warning,
    msg_progress_context
)

# Initialize at application startup
# CLI mode
init_message_handler(is_gui_mode=False)

# GUI mode (with parent widget)
init_message_handler(parent=main_window, is_gui_mode=True)

# Send messages
msg_info("Starting crash log analysis...")
msg_warning("Found deprecated plugin format")
msg_error("Failed to parse log file", details="Line 42: Invalid format")

# With progress
with msg_progress_context("Analyzing logs", total=len(log_files)) as progress:
    for log_file in log_files:
        analyze(log_file)
        progress.update(1)
```

---

### YamlSettings

Configuration management with caching and optional Rust acceleration.

#### Import

```python
# Synchronous API (GUI contexts)
from ClassicLib.YamlSettings import (
    yaml_settings,      # Get/set YAML value
    classic_settings,   # Get classic settings shorthand
    yaml_cache,         # Get cache instance
    YamlSettingsCache,  # Cache class
)

# Asynchronous API (CLI/TUI)
from ClassicLib.YamlSettings import (
    yaml_settings_async,
    classic_settings_async,
    get_async_yaml_core,
    AsyncYamlSettingsCore,
    YamlCache,
)
```

#### Sync Functions (GUI)

```python
def yaml_settings(
    type_: Type[T],
    yaml_file: YAML,
    key_path: str,
    value: T = None
) -> T:
    """Get or set a YAML setting.

    Args:
        type_: Expected return type (str, int, bool, list, dict)
        yaml_file: YAML file enum (YAML.Main, YAML.Settings, etc.)
        key_path: Dot-separated path (e.g., "CLASSIC_Info.version")
        value: Value to set (None = get only)

    Returns:
        The setting value, coerced to type_

    Example:
        >>> version = yaml_settings(str, YAML.Main, "CLASSIC_Info.version")
        >>> yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.FCX Mode", True)
    """

def classic_settings(type_: Type[T], setting_name: str, default: T = None) -> T:
    """Shorthand for getting CLASSIC_Settings.* values.

    Example:
        >>> fcx_mode = classic_settings(bool, "FCX Mode")
        >>> custom_path = classic_settings(str, "SCAN Custom Path", "")
    """

def yaml_cache() -> YamlSettingsCache:
    """Get the global YAML cache instance."""
```

#### Async Functions (CLI/TUI)

```python
async def yaml_settings_async(
    type_: Type[T],
    yaml_file: YAML,
    key_path: str,
    value: T = None
) -> T:
    """Async version of yaml_settings."""

async def classic_settings_async(
    type_: Type[T],
    setting_name: str,
    default: T = None
) -> T:
    """Async version of classic_settings."""
```

#### Batch Operations

```python
from ClassicLib.YamlSettings import yaml_cache

cache = yaml_cache()

# Batch get for performance
requests = [
    (str, YAML.Main, "CLASSIC_Info.version"),
    (bool, YAML.Settings, "CLASSIC_Settings.FCX Mode"),
    (str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path"),
]
results = cache.batch_get_settings(requests)
version, fcx_mode, scan_path = results
```

#### Usage Examples

```python
from ClassicLib.YamlSettings import yaml_settings, classic_settings
from ClassicLib.Constants import YAML

# Get application version
version = yaml_settings(str, YAML.Main, "CLASSIC_Info.version")

# Get nested setting
nexus_url = yaml_settings(str, YAML.Main, "CLASSIC_Info.nexus_link")

# Get/set boolean setting
fcx_enabled = classic_settings(bool, "FCX Mode")
yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.FCX Mode", True)

# Get with default
custom_path = classic_settings(str, "SCAN Custom Path", "")

# Async in CLI
async def main():
    from ClassicLib.YamlSettings import yaml_settings_async
    version = await yaml_settings_async(str, YAML.Main, "CLASSIC_Info.version")
```

---

### FileIOCore

Unified file I/O with async support and Rust acceleration.

#### Import

```python
from ClassicLib.FileIO import FileIOCore, read_file_sync, write_file_sync
```

#### Class: `FileIOCore`

```python
class FileIOCore:
    """Unified file I/O with async support and Rust acceleration."""

    def __init__(self, use_rust: bool = True):
        """Initialize FileIOCore.

        Args:
            use_rust: Enable Rust acceleration if available (default: True)
        """

    async def read_file(
        self,
        path: Path | str,
        encoding: str = "utf-8",
        errors: str = "ignore"
    ) -> str:
        """Async file read with automatic encoding detection."""

    async def write_file(
        self,
        path: Path | str,
        content: str,
        encoding: str = "utf-8"
    ) -> bool:
        """Async file write."""

    async def read_lines(
        self,
        path: Path | str,
        encoding: str = "utf-8"
    ) -> list[str]:
        """Read file as list of lines."""

    @property
    def rust_available(self) -> bool:
        """Check if Rust acceleration is available."""
```

#### Convenience Functions

```python
def read_file_sync(
    path: Path | str,
    encoding: str = "utf-8",
    errors: str = "ignore"
) -> str:
    """Synchronous file read (for GUI contexts)."""

def write_file_sync(
    path: Path | str,
    content: str,
    encoding: str = "utf-8"
) -> bool:
    """Synchronous file write (for GUI contexts)."""
```

#### Usage Examples

```python
from ClassicLib.FileIO import FileIOCore, read_file_sync, write_file_sync
from pathlib import Path

# Async usage (preferred for CLI)
async def process_files():
    file_io = FileIOCore()

    content = await file_io.read_file(Path("crash.log"))
    lines = await file_io.read_lines(Path("config.txt"))

    await file_io.write_file(Path("output.txt"), processed_content)

    # Check Rust acceleration
    if file_io.rust_available:
        print("Using Rust acceleration (10x faster)")

# Sync usage (GUI contexts)
content = read_file_sync(Path("crash.log"))
write_file_sync(Path("output.txt"), content)
```

---

## Constants and Enums

### YAML Enum

```python
from ClassicLib.Constants import YAML

class YAML(Enum):
    """YAML file identifiers."""
    Main = "CLASSIC Main.yaml"           # Main configuration
    Settings = "CLASSIC Settings.yaml"   # User settings
    Game = "CLASSIC {game}.yaml"         # Game-specific (Fallout4/Skyrim)
    Ignore = "CLASSIC Ignore.yaml"       # Ignore patterns
    Local = "CLASSIC Local.yaml"         # Local overrides
    TEST = "CLASSIC TEST.yaml"           # Testing only
```

### GameID Enum

```python
from ClassicLib.Constants import GameID

class GameID(Enum):
    """Supported game identifiers."""
    FALLOUT4 = "Fallout4"
    FALLOUT4VR = "Fallout4VR"
    SKYRIMSE = "SkyrimSE"
    SKYRIMVR = "SkyrimVR"
```

### Version Constants

```python
from ClassicLib.Constants import (
    OG_VERSION,        # Original game version threshold
    NG_VERSION,        # Next-gen version threshold
    VR_VERSION,        # VR version threshold
    OG_F4SE_VERSION,   # Original F4SE version
    NG_F4SE_VERSION,   # Next-gen F4SE version
    NULL_VERSION,      # Null version constant
    FO4_VERSIONS,      # All Fallout 4 versions
    F4SE_VERSIONS,     # All F4SE versions
)
```

---

## Integration Layer

The integration layer provides automatic Rust component detection and factory functions.

### Component Detection

```python
from ClassicLib.integration.detector import detect_component
from ClassicLib.integration.status import print_rust_status

# Check if a Rust component is available
is_available, module = detect_component("classic_yaml")
if is_available:
    yaml_ops = module.RustYamlOperations()

# Print status of all Rust components
print_rust_status()
```

### Factory Functions

```python
from ClassicLib.integration.factory import (
    get_parser,           # Best available log parser
    get_file_io,          # FileIOCore with Rust if available
    get_yaml_operations,  # Rust or Python YAML ops
)

# Automatic best-available selection
parser = get_parser()
file_io = get_file_io()
yaml_ops = get_yaml_operations()
```

### Custom Exceptions

```python
from ClassicLib.integration.exceptions import (
    RustYamlError,        # Base YAML error
    RustYamlIOError,      # YAML I/O error
    RustYamlParseError,   # YAML parsing error
    RustIOError,          # File I/O error
    RustDatabaseError,    # Database error
)

try:
    data = yaml_ops.load_file("config.yaml")
except RustYamlParseError as e:
    msg_error(f"Failed to parse YAML: {e}")
```

---

## ScanLog Components

### ScanConfig

```python
from ClassicLib.ScanLog.models import ScanConfig

config = ScanConfig(
    fcx_mode=True,              # Enable FCX mode
    show_formid_values=True,    # Show FormID values in report
    move_unsolved_logs=False,   # Move unsolved logs to subfolder
    simplify_logs=False,        # Simplify log output
    custom_paths={              # Custom paths
        "scan_path": Path("/custom/scan"),
        "ini_path": Path("/custom/ini"),
    }
)
```

### ScanLogsExecutor

```python
from ClassicLib.ScanLog.ScanLogsExecutor import ScanLogsExecutor
from ClassicLib.ScanLog.models import ScanConfig, ScanResult

# Create executor
config = ScanConfig()
executor = ScanLogsExecutor(config)

# Run scan (async)
result: ScanResult = await executor.execute_scan()

# Generate summary
summary = executor.generate_summary(result)
msg_info(summary)
```

### ScanResult

```python
from ClassicLib.ScanLog.models import ScanResult

@dataclass
class ScanResult:
    """Result of a crash log scan."""
    logs_found: int
    logs_analyzed: int
    logs_solved: int
    logs_unsolved: int
    errors: list[str]
    duration: float
    report: str
```

---

## Utility Functions

### File Utilities

```python
from ClassicLib.Utils.file_utils import (
    calculate_file_hash,      # Calculate MD5/SHA hash
    calculate_similarity,     # String similarity score
    open_file_with_encoding,  # Open with encoding detection
)

# Calculate file hash
hash_value = calculate_file_hash(Path("file.dll"), algorithm="md5")

# String similarity
similarity = calculate_similarity("plugin_a.esp", "plugin_b.esp")
```

### Path Utilities

```python
from ClassicLib.Utils.path_utils import remove_readonly

# Remove read-only attribute
remove_readonly(Path("readonly_file.txt"))
```

### Version Utilities

```python
from ClassicLib.Utils.version_utils import (
    read_game_exe_version,  # Read game version from exe
    crashgen_version_gen,   # Parse crashgen version
)

# Read game executable version
version = read_game_exe_version(Path("C:/Games/Fallout4"))
```

### Web Utilities

```python
from ClassicLib.Utils.web_utils import pastebin_fetch, pastebin_fetch_async

# Fetch from Pastebin (sync)
content = pastebin_fetch("https://pastebin.com/raw/abc123")

# Fetch from Pastebin (async)
content = await pastebin_fetch_async("https://pastebin.com/raw/abc123")
```

### Logging Utilities

```python
from ClassicLib.Utils.logging_utils import configure_logging, enable_debug_logging

# Configure logging
configure_logging(level="INFO", log_file=Path("classic.log"))

# Enable debug mode
enable_debug_logging()
```

---

## Rust Acceleration

CLASSIC uses Rust for performance-critical operations, providing 10-150x speedups.

### Checking Availability

```python
from ClassicLib import (
    RUST_REGISTRY_AVAILABLE,  # GlobalRegistry (15-25x)
    RUST_PERF_AVAILABLE,      # PerformanceMonitor
    RUST_PYBRIDGE_AVAILABLE,  # Async bridge
    RUST_SETTINGS_AVAILABLE,  # YAML settings (15-30x)
    RUST_MESSAGE_AVAILABLE,   # Message formatting
)

from ClassicLib.integration.status import print_rust_status
print_rust_status()
```

### Direct Rust Module Usage

```python
# YAML operations
import classic_yaml
yaml_ops = classic_yaml.RustYamlOperations()
data = yaml_ops.load_file("config.yaml")

# Database operations
import classic_database
db = classic_database.RustDatabase("classic.db")

# Scanlog parsing
import classic_scanlog
parser = classic_scanlog.RustLogParser()
segments = parser.find_segments(log_content)
```

### Performance Monitoring

```python
from ClassicLib import TimedBlock, timed_operation, async_timed_operation

# Block timing
with TimedBlock("operation_name"):
    do_work()

# Function decorator
@timed_operation
def process_data(data):
    return transform(data)

# Async function decorator
@async_timed_operation
async def fetch_data():
    return await api.get_data()
```

---

## See Also

- [Architecture Overview](../architecture/ARCHITECTURE_OVERVIEW.md)
- [Quick Start Guide](QUICK_START.md)
- [Rust Integration Guide](../development/rust_acceleration_guide.md)
- [Testing Guide](../testing/TESTING_GUIDE_INDEX.md)
- [Async Development Guide](../development/async_development_guide.md)

---

*Last updated: December 2025*
