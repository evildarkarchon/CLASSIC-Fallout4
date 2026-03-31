# CLASSIC Code Examples

> Practical examples for common development patterns

Note: many examples in this file target the legacy Python runtime/orchestration layer under `deprecated/` and older migration helpers. They are not the default path for current product work, which centers on `ClassicLib-rs/`, the maintained bindings, and the C++ frontends.

This document provides ready-to-use code examples for common tasks in CLASSIC development.

---

## Table of Contents

1. [Configuration and Settings](#configuration-and-settings)
2. [Message Handling](#message-handling)
3. [File Operations](#file-operations)
4. [Async Patterns](#async-patterns)
5. [Crash Log Analysis](#crash-log-analysis)
6. [GUI Development](#gui-development)
7. [Testing Patterns](#testing-patterns)
8. [Rust Integration](#rust-integration)

---

## Configuration and Settings

### Reading YAML Settings

```python
from ClassicLib.YamlSettings import yaml_settings, classic_settings
from ClassicLib.Constants import YAML

# Read application version
version = yaml_settings(str, YAML.Main, "CLASSIC_Info.version")
print(f"CLASSIC version: {version}")

# Read nested settings
nexus_url = yaml_settings(str, YAML.Main, "CLASSIC_Info.nexus_link")
github_url = yaml_settings(str, YAML.Main, "CLASSIC_Info.github_link")

# Read user settings (shorthand)
fcx_mode = classic_settings(bool, "FCX Mode")
show_formids = classic_settings(bool, "Show FormID Values")
custom_path = classic_settings(str, "SCAN Custom Path", "")  # With default

# Read game-specific settings
game_name = yaml_settings(str, YAML.Game, "Game.name")
```

### Writing YAML Settings

```python
from ClassicLib.YamlSettings import yaml_settings
from ClassicLib.Constants import YAML

# Update a setting
yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.FCX Mode", True)

# Update custom path
yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", "/path/to/logs")

# Batch updates (for performance)
from ClassicLib.YamlSettings import yaml_cache

cache = yaml_cache()
cache.set_value(YAML.Settings, "CLASSIC_Settings.FCX Mode", True)
cache.set_value(YAML.Settings, "CLASSIC_Settings.Move Unsolved Logs", False)
cache.save_file(YAML.Settings)  # Save once after all updates
```

### Async Settings Access (CLI/TUI)

```python
from ClassicLib.YamlSettings import yaml_settings_async, classic_settings_async
from ClassicLib.Constants import YAML

async def load_settings():
    """Load settings asynchronously."""
    version = await yaml_settings_async(str, YAML.Main, "CLASSIC_Info.version")
    fcx_mode = await classic_settings_async(bool, "FCX Mode")
    return version, fcx_mode

# Usage in async main
async def main():
    version, fcx_mode = await load_settings()
    print(f"Version: {version}, FCX: {fcx_mode}")
```

### Batch Loading for Performance

```python
from ClassicLib.YamlSettings import yaml_cache
from ClassicLib.Constants import YAML

def load_all_settings():
    """Load multiple settings efficiently."""
    cache = yaml_cache()

    requests = [
        (str, YAML.Main, "CLASSIC_Info.version"),
        (str, YAML.Main, "CLASSIC_Info.nexus_link"),
        (bool, YAML.Settings, "CLASSIC_Settings.FCX Mode"),
        (bool, YAML.Settings, "CLASSIC_Settings.Show FormID Values"),
        (str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path"),
    ]

    results = cache.batch_get_settings(requests)

    version, nexus_url, fcx_mode, show_formids, scan_path = results
    return {
        "version": version,
        "nexus_url": nexus_url,
        "fcx_mode": fcx_mode,
        "show_formids": show_formids,
        "scan_path": scan_path,
    }
```

---

## Message Handling

### Basic Messages

```python
from ClassicLib.MessageHandler import (
    msg_info, msg_warning, msg_error, msg_debug, msg_success, msg_critical
)

# Information message
msg_info("Starting crash log analysis...")

# Warning
msg_warning("Plugin 'Example.esp' uses deprecated format")

# Error with details
msg_error(
    "Failed to parse crash log",
    details="Line 42: Expected module header, got 'INVALID'"
)

# Success
msg_success("Analysis complete! Found 3 potential causes.")

# Debug (only shown when debug logging enabled)
msg_debug(f"Processing file: {file_path}")

# Critical error
msg_critical("Application state corrupted - restart required")
```

### Progress Tracking

```python
from ClassicLib.MessageHandler import msg_progress_context
from pathlib import Path

def analyze_logs(log_dir: Path):
    """Analyze all crash logs in directory with progress."""
    log_files = list(log_dir.glob("*.log"))

    with msg_progress_context("Analyzing crash logs", total=len(log_files)) as progress:
        results = []
        for log_file in log_files:
            result = analyze_single_log(log_file)
            results.append(result)

            # Update progress with description
            progress.update(1, description=f"Analyzed {log_file.name}")

        return results

# Nested progress for complex operations
def process_all_games(game_dirs: list[Path]):
    """Process multiple game directories."""
    with msg_progress_context("Processing games", total=len(game_dirs)) as outer:
        for game_dir in game_dirs:
            log_files = list(game_dir.glob("*.log"))

            with msg_progress_context(f"Processing {game_dir.name}", total=len(log_files)) as inner:
                for log_file in log_files:
                    process_log(log_file)
                    inner.update(1)

            outer.update(1)
```

### Custom Message Handler

```python
from ClassicLib.MessageHandler import init_message_handler, get_message_handler

# Initialize for CLI mode
init_message_handler(is_gui_mode=False)

# Initialize for GUI mode (with parent widget)
init_message_handler(parent=main_window, is_gui_mode=True)

# Get current handler
handler = get_message_handler()

# Send structured message
from ClassicLib.MessageHandler import Message, MessageType, MessageTarget

message = Message(
    type=MessageType.INFO,
    content="Custom structured message",
    target=MessageTarget.ALL,
    metadata={"source": "custom_module", "priority": "high"}
)
handler.send(message)
```

---

## File Operations

### Reading Files

```python
from ClassicLib.FileIO import FileIOCore, read_file_sync
from pathlib import Path

# Synchronous read (GUI contexts)
content = read_file_sync(Path("crash.log"))

# With custom encoding
content = read_file_sync(
    Path("unicode_log.txt"),
    encoding="utf-16",
    errors="replace"
)

# Async read (CLI/TUI)
async def read_logs():
    file_io = FileIOCore()

    content = await file_io.read_file(Path("crash.log"))
    lines = await file_io.read_lines(Path("config.txt"))

    return content, lines

# Check Rust acceleration
file_io = FileIOCore()
if file_io.rust_available:
    print("Using Rust file I/O (10x faster)")
```

### Writing Files

```python
from ClassicLib.FileIO import write_file_sync, FileIOCore
from pathlib import Path

# Synchronous write (GUI contexts)
write_file_sync(
    Path("output.txt"),
    "Content to write",
    encoding="utf-8"
)

# Async write (CLI/TUI)
async def save_results():
    file_io = FileIOCore()

    await file_io.write_file(Path("results.txt"), "Analysis results...")
    await file_io.write_file(Path("report.json"), json.dumps(data))

    return True
```

### File Utilities

```python
from ClassicLib.Utils.file_utils import (
    calculate_file_hash,
    calculate_similarity,
    open_file_with_encoding
)
from pathlib import Path

# Calculate file hash
hash_value = calculate_file_hash(Path("plugin.dll"), algorithm="md5")
print(f"MD5: {hash_value}")

# SHA256 hash
sha256 = calculate_file_hash(Path("plugin.dll"), algorithm="sha256")

# String similarity (for plugin matching)
similarity = calculate_similarity("MyPlugin.esp", "MyPlugin_v2.esp")
print(f"Similarity: {similarity:.2%}")

# Open with encoding detection
with open_file_with_encoding(Path("mixed_encoding.txt")) as f:
    content = f.read()
```

---

## Async Patterns

### CLI Async-First Pattern

```python
import asyncio
from pathlib import Path

async def main():
    """Async-first CLI entry point."""
    from ClassicLib.YamlSettings import yaml_settings_async
    from ClassicLib.Constants import YAML
    from ClassicLib.MessageHandler import msg_info

    # Load settings asynchronously
    version = await yaml_settings_async(str, YAML.Main, "CLASSIC_Info.version")
    msg_info(f"CLASSIC v{version}")

    # Process files concurrently
    log_files = list(Path("logs").glob("*.log"))

    results = await asyncio.gather(*[
        process_log_async(log_file)
        for log_file in log_files
    ])

    msg_info(f"Processed {len(results)} logs")

if __name__ == "__main__":
    # Single asyncio.run() at entry point
    asyncio.run(main())
```

### GUI AsyncBridge Pattern

```python
from ClassicLib.AsyncBridge import AsyncBridge, run_async
from PySide6.QtCore import QThread, Signal

class ScanWorker(QThread):
    """Worker thread for crash log scanning."""

    finished = Signal(object)
    error = Signal(str)

    def __init__(self, log_path: Path):
        super().__init__()
        self.log_path = log_path

    def run(self):
        """Run scan in worker thread."""
        try:
            # Use AsyncBridge for async operations
            bridge = AsyncBridge.get_instance()

            # Run async function from sync context
            result = bridge.run_async(self.scan_log_async())

            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

    async def scan_log_async(self):
        """Async log scanning."""
        from ClassicLib.ScanLog.ScanLogsExecutor import ScanLogsExecutor
        from ClassicLib.ScanLog.models import ScanConfig

        config = ScanConfig()
        executor = ScanLogsExecutor(config)
        return await executor.execute_scan()

# Usage in GUI
def start_scan(self):
    """Start scan from GUI."""
    self.worker = ScanWorker(self.log_path)
    self.worker.finished.connect(self.on_scan_complete)
    self.worker.error.connect(self.on_scan_error)
    self.worker.start()
```

### Timeout Handling

```python
from ClassicLib.AsyncBridge import AsyncBridge
import asyncio

def fetch_with_timeout():
    """Fetch with timeout handling."""
    bridge = AsyncBridge.get_instance()

    try:
        result = bridge.run_async_with_timeout(
            slow_async_operation(),
            timeout=30.0
        )
        return result
    except TimeoutError:
        msg_warning("Operation timed out after 30 seconds")
        return None

async def slow_async_operation():
    """Simulated slow operation."""
    await asyncio.sleep(5)
    return "result"
```

---

## Crash Log Analysis

### Basic Log Scanning

```python
from ClassicLib.ScanLog.ScanLogsExecutor import ScanLogsExecutor
from ClassicLib.ScanLog.models import ScanConfig, ScanResult

async def scan_crash_logs():
    """Scan crash logs with default settings."""
    config = ScanConfig()
    executor = ScanLogsExecutor(config)

    result: ScanResult = await executor.execute_scan()

    print(f"Logs found: {result.logs_found}")
    print(f"Logs analyzed: {result.logs_analyzed}")
    print(f"Solved: {result.logs_solved}")
    print(f"Unsolved: {result.logs_unsolved}")
    print(f"Duration: {result.duration:.2f}s")

    return result
```

### Custom Scan Configuration

```python
from ClassicLib.ScanLog.models import ScanConfig
from pathlib import Path

# Create custom configuration
config = ScanConfig(
    fcx_mode=True,              # Enable FCX mode
    show_formid_values=True,    # Show FormIDs in report
    move_unsolved_logs=True,    # Move unsolved to subfolder
    simplify_logs=False,        # Keep detailed output
    custom_paths={
        "scan_path": Path("C:/Custom/Logs"),
        "ini_path": Path("C:/Custom/INI"),
        "mods_folder_path": Path("C:/Mods"),
    }
)

# Use configuration
from ClassicLib.ScanLog.ScanLogsExecutor import ScanLogsExecutor

executor = ScanLogsExecutor(config)
result = await executor.execute_scan()
```

### Using Individual Analyzers

```python
from ClassicLib.ScanLog.FormIDAnalyzer import FormIDAnalyzer
from ClassicLib.ScanLog.PluginAnalyzer import PluginAnalyzer
from ClassicLib.ScanLog.GPUDetector import GPUDetector

# Analyze FormIDs
formid_analyzer = FormIDAnalyzer()
formid_results = formid_analyzer.analyze(log_content, yamldata)

# Analyze plugins
plugin_analyzer = PluginAnalyzer()
plugin_results = plugin_analyzer.analyze(log_content, yamldata)

# Detect GPU issues
gpu_detector = GPUDetector()
gpu_issues = gpu_detector.detect(log_content)
```

---

## GUI Development

### Controller Pattern

```python
from ClassicLib.Interface.context import FeatureContext
from ClassicLib.MessageHandler import msg_info, msg_error

class MyFeatureController:
    """Controller for custom feature."""

    def __init__(self, context: FeatureContext):
        self.context = context
        self.main_window = context.main_window
        self.signal_hub = context.signal_hub

        # Connect signals
        self.signal_hub.scan_completed.connect(self.on_scan_complete)

    def start_feature(self):
        """Start feature operation."""
        msg_info("Starting feature...")

        # Access widgets
        button = self.context.ui_widgets.get("my_button")
        if button:
            button.setEnabled(False)

        # Start worker
        self.worker = MyFeatureWorker()
        self.worker.finished.connect(self.on_complete)
        self.worker.start()

    def on_scan_complete(self, result):
        """Handle scan completion."""
        msg_info(f"Scan complete: {result}")

    def on_complete(self, result):
        """Handle feature completion."""
        button = self.context.ui_widgets.get("my_button")
        if button:
            button.setEnabled(True)
```

### Worker Thread Pattern

```python
from PySide6.QtCore import QThread, Signal
from ClassicLib.AsyncBridge import AsyncBridge

class DataProcessingWorker(QThread):
    """Worker for data processing."""

    progress = Signal(int, str)  # (percent, message)
    finished = Signal(object)    # result
    error = Signal(str)          # error message

    def __init__(self, data: list):
        super().__init__()
        self.data = data

    def run(self):
        try:
            bridge = AsyncBridge.get_instance()
            result = bridge.run_async(self.process_data())
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

    async def process_data(self):
        results = []
        total = len(self.data)

        for i, item in enumerate(self.data):
            result = await self.process_item(item)
            results.append(result)

            percent = int((i + 1) / total * 100)
            self.progress.emit(percent, f"Processing {i + 1}/{total}")

        return results

    async def process_item(self, item):
        # Async processing
        return item.upper()

# Usage
worker = DataProcessingWorker(data_list)
worker.progress.connect(lambda p, m: progress_bar.setValue(p))
worker.finished.connect(handle_results)
worker.error.connect(show_error)
worker.start()
```

---

## Testing Patterns

### Unit Test Structure

```python
# tests/my_module/test_my_feature_unit.py
import pytest
from ClassicLib.MessageHandler import msg_info

class TestMyFeature:
    """Tests for MyFeature."""

    @pytest.mark.unit
    def test_basic_functionality(self):
        """Test basic feature operation."""
        from my_module import MyFeature

        feature = MyFeature()
        result = feature.process("input")

        assert result == "expected"

    @pytest.mark.unit
    def test_edge_case(self):
        """Test edge case handling."""
        from my_module import MyFeature

        feature = MyFeature()
        result = feature.process("")

        assert result == ""

    @pytest.mark.unit
    def test_error_handling(self):
        """Test error handling."""
        from my_module import MyFeature

        feature = MyFeature()

        with pytest.raises(ValueError, match="Invalid input"):
            feature.process(None)
```

### Async Test Pattern

```python
import pytest
from unittest.mock import AsyncMock, patch

class TestAsyncFeature:
    """Tests for async features."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_async_operation(self):
        """Test async operation."""
        from my_module import async_process

        result = await async_process("input")
        assert result is not None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_async_with_mock(self):
        """Test async with mocked dependency."""
        mock_fetch = AsyncMock(return_value="mocked_data")

        with patch("my_module.fetch_data", mock_fetch):
            from my_module import process_with_fetch

            result = await process_with_fetch()
            assert result == "mocked_data"
            mock_fetch.assert_called_once()
```

### Fixture Usage

```python
import pytest
from pathlib import Path

# Use fixtures from tests/fixtures/
class TestWithFixtures:
    """Tests using centralized fixtures."""

    @pytest.mark.unit
    def test_with_crash_log(self, sample_crash_log_content):
        """Test with crash log fixture."""
        from ClassicLib.ScanLog.Parser import parse_log

        result = parse_log(sample_crash_log_content)
        assert result is not None

    @pytest.mark.unit
    def test_with_yamldata(self, mock_yamldata):
        """Test with YAML data fixture."""
        from ClassicLib.ScanLog.FormIDAnalyzer import FormIDAnalyzer

        analyzer = FormIDAnalyzer()
        result = analyzer.analyze("log content", mock_yamldata)
        assert result is not None

    @pytest.mark.integration
    def test_with_temp_files(self, tmp_path):
        """Test with temporary files."""
        test_file = tmp_path / "test.log"
        test_file.write_text("crash log content")

        from ClassicLib.FileIO import read_file_sync

        content = read_file_sync(test_file)
        assert "crash log" in content
```

### Mocking AsyncBridge

```python
import pytest
from unittest.mock import MagicMock, patch

class TestWithAsyncBridge:
    """Tests involving AsyncBridge."""

    @pytest.mark.unit
    def test_gui_operation(self):
        """Test GUI operation that uses AsyncBridge."""
        # Mock the bridge's run_async method, NOT the async function
        mock_bridge = MagicMock()
        mock_bridge.run_async.return_value = "result"

        with patch("ClassicLib.AsyncBridge.AsyncBridge.get_instance", return_value=mock_bridge):
            from my_module import gui_operation

            result = gui_operation()

            assert result == "result"
            mock_bridge.run_async.assert_called_once()
```

---

## Rust Integration

### Using Rust YAML Operations

```python
from ClassicLib.integration.factory import get_yaml_operations

# Get best available implementation
yaml_ops = get_yaml_operations()

# Load YAML file
data = yaml_ops.load_file("config.yaml")

# Get nested value
version = yaml_ops.get_value(data, "CLASSIC_Info.version")

# Modify and save
yaml_ops.set_value(data, "CLASSIC_Settings.FCX Mode", True)
yaml_ops.save_file("config.yaml", data)
```

### Checking Rust Availability

```python
# classic_registry is mandatory (always available)
from ClassicLib import (
    RUST_SETTINGS_AVAILABLE,
    RUST_MESSAGE_AVAILABLE,
)
from ClassicLib.integration.status import print_rust_status

# Check individual components
if RUST_SETTINGS_AVAILABLE:
    print("Using Rust settings cache (25x faster)")

# Print full status
print_rust_status()

# Component detection
from ClassicLib.integration.detector import detect_component

is_available, module = detect_component("classic_scanlog")
if is_available:
    parser = module.RustLogParser()
else:
    from ClassicLib.python.parser_py import PythonParser
    parser = PythonParser()
```

### Performance Monitoring

```python
from ClassicLib import TimedBlock, timed_operation, async_timed_operation

# Block timing
with TimedBlock("yaml_loading"):
    data = yaml_ops.load_file("large_config.yaml")
# Output: yaml_loading: 0.004s

# Function decorator
@timed_operation
def process_logs(logs):
    return [analyze(log) for log in logs]

result = process_logs(log_list)
# Output: process_logs: 0.150s

# Async decorator
@async_timed_operation
async def fetch_all_data():
    return await gather_data()

result = await fetch_all_data()
# Output: fetch_all_data: 0.250s
```

---

## See Also

- [API Docs Index](../api/README.md)
- [Architecture Overview](../architecture/ARCHITECTURE_OVERVIEW.md)
- [Quick Start Guide](QUICK_START.md)
- [Testing Guide](../testing/TESTING_GUIDE_INDEX.md)

---

*Last updated: December 2025*
