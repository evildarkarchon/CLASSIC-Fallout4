# Test Writing Guide for CLASSIC-Fallout4

## Table of Contents
1. [Test Naming Conventions](#test-naming-conventions)
2. [Test Data Generation Patterns](#test-data-generation-patterns)
3. [Test Organization](#test-organization)
4. [Best Practices](#best-practices)
5. [Common Patterns](#common-patterns)
6. [Test Data Guidelines](#test-data-guidelines)

## Test Naming Conventions

### File Naming
```
test_<component>_<type>.py

Examples:
- test_parser_unit.py          # Unit tests for parser
- test_formid_integration.py   # Integration tests for FormID analysis
- test_scan_pipeline_e2e.py    # End-to-end pipeline tests
- test_malformed_crash_logs.py # Edge case tests
```

### Test Function Naming
```python
def test_<component>_<action>_<expected_result>():
    """Brief description of what test validates."""

Examples:
def test_parser_handles_empty_log():
def test_formid_analyzer_validates_hex_format():
def test_async_bridge_prevents_nested_calls():
def test_file_io_recovers_from_permission_error():
```

### Test Class Naming
```python
class Test<Component><Feature>:
    """Test suite for specific component feature."""

Examples:
class TestParserErrorHandling:
class TestFormIDValidation:
class TestAsyncBridgeConcurrency:
```

## Test Data Generation Patterns

### Crash Log Patterns (Based on Real Logs)

**NOTE**: Crash logs are diagnostic outputs shared for debugging - we can use their patterns directly in tests. However, we still avoid using actual game executables or data files.

```python
class CrashLogGenerator:
    """Generate crash logs based on real patterns."""

    @staticmethod
    def generate_typical_log(size_mb: float = 1.5) -> str:
        """Generate typical 1-2MB crash log based on actual patterns."""
        lines = []

        # Header from actual crash logs
        lines.append("Fallout 4 v1.10.163")
        lines.append("Buffout 4 v1.28.6")
        lines.append("")
        lines.append('Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512 Fallout4.exe+0733512')
        lines.append("")

        # System specs section
        lines.append("SYSTEM SPECS:")
        lines.append("\tOS: Microsoft Windows 10 Home v10.0.19045")
        lines.append("\tCPU: GenuineIntel Intel(R) Core(TM) i7-8700K CPU @ 3.70GHz")
        lines.append("")

        # Plugin list format from actual logs: [XX] or [FE:XXX]
        lines.append("PLUGINS:")
        lines.append("\t[00] Fallout4.esm")
        lines.append("\t[01] DLCRobot.esm")
        lines.append("\t[02] DLCworkshop01.esm")

        # Light plugins with actual format
        lines.append("\t[FE:104] [SS2 Addon] BloodMoonRaiders.esp")
        lines.append("\t[FE:105] [SS2] BBVault 88.esp")

        # Stack trace format from actual logs
        lines.append("STACK TRACE:")
        lines.append("\t[0] 0x7FF6EF4C3512 Fallout4.exe+0733512 -> 703355+0x72")
        lines.append("\t[1] 0x7FF6EF4C145E Fallout4.exe+073145E -> 548219+0x3E")

        # Memory registers from actual crash logs
        lines.append("REGISTERS:")
        lines.append("\tRAX 0x463FBF           (size_t)")
        lines.append("\tRCX 0x22FC9E18080      (void*)")

        return "\n".join(lines)
```

### FormID Format (From Actual Logs)

FormIDs are **always 8-character hexadecimal values** as seen in crash logs:

```python
def generate_formid(plugin_index: int = 0, local_id: Optional[int] = None) -> str:
    """Generate valid hex FormID as they appear in crash logs."""
    if local_id is None:
        local_id = random.randint(0x000001, 0xFFFFFF)
    return f"{plugin_index:02X}{local_id:06X}"

# Actual FormID patterns from crash logs:
# "00000014" - Base game FormID (from Fallout4.esm)
# "FE000800" - Light plugin FormID (FE prefix, 800-FFF range)
# "0A001234" - Regular plugin FormID
```

### Plugin List Format (From Real Crash Logs)

These formats are directly observed in actual crash logs:

```python
# Regular plugins as they appear in logs:
"[00] Fallout4.esm"
"[01] DLCRobot.esm"
"[02] DLCworkshop01.esm"
"[0A] SS2.esm"
"[0B] WorkshopFramework.esm"

# Light plugins (FE prefix) from actual logs:
"[FE:000] CCBGSFOVault88.esl"
"[FE:001] CCBGSFOPowerArmor.esl"
"[FE:104] [SS2 Addon] BloodMoonRaiders.esp"
"[FE:105] [SS2] BBVault 88.esp"

# Note: Not all crash logs have plugin lists - this is normal
```

### Stack Trace Format (From Real Crash Logs)

```python
def generate_stack_trace() -> List[str]:
    """Generate stack trace matching actual crash log format."""
    trace = []
    # Format from actual logs: [index] address module+offset -> function+offset
    trace.append("[0] 0x7FF6EF4C3512 Fallout4.exe+0733512 -> 703355+0x72")
    trace.append("[1] 0x7FF6EF4C145E Fallout4.exe+073145E -> 548219+0x3E")
    trace.append("[2] 0x7FF6EEF11959 Fallout4.exe+0171959 -> 897282+0x29")
    trace.append("[3] 0x7FF6F08FEEF4 f4se_1_10_163.dll+002EEF4")
    trace.append("[4] 0x7FF6F08D3C81 Buffout4.dll+0003C81")
    return trace
```

### Memory Dump Format (From Real Crash Logs)

```python
# Actual register format from crash logs
"""
REGISTERS:
    RAX 0x463FBF           (size_t)
    RCX 0x22FC9E18080      (void*)
    RDX 0x13EE6            (size_t)
    RBX 0x80ECFDFA90       (void*)
    RSP 0x80ECFDF940       (void*)
    RSI 0x22FCA037A78      (char*) "WCLINS_PRP_Patch - Main.ba2"
"""

# Stack memory format
"""
STACK:
    [RSP+8  ] 0x80ECFDFA90      (void*)
    [RSP+10 ] 0x1AC             (size_t)
    [RSP+18 ] 0x22FCA037A78     (char*) "WCLINS_PRP_Patch - Main.ba2"
"""
```

## Test Organization

### Directory Structure
```
tests/
├── unit/              # Isolated component tests
├── integration/       # Cross-component tests
├── edge_cases/        # Malformed input, error conditions
├── stress/            # Load and performance tests
├── fixtures/          # Shared test fixtures
└── conftest.py        # Pytest configuration
```

### Test Markers

Always use appropriate pytest markers:

```python
# Required markers
@pytest.mark.unit         # Isolated unit test
@pytest.mark.integration  # Integration test
@pytest.mark.e2e          # End-to-end test
@pytest.mark.asyncio      # Async test
@pytest.mark.slow         # Test takes >1 second
@pytest.mark.gui          # GUI component test
@pytest.mark.performance  # Performance test
@pytest.mark.rust         # Rust FFI test
@pytest.mark.stress       # Stress/load test
@pytest.mark.edge_cases   # Edge case test
@pytest.mark.network      # Network-dependent test
```

## Best Practices

### 1. Always Mock External Dependencies

```python
@patch('aiohttp.ClientSession.get')
async def test_network_operation(mock_get):
    """Test with mocked network call."""
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={"status": "ok"})
    mock_get.return_value.__aenter__.return_value = mock_response
```

### 2. Clean Up Singletons Between Tests

```python
@pytest.fixture(autouse=True)
def clear_singletons():
    """Clear singleton instances between tests."""
    from ClassicLib.core.registry import GlobalRegistry
    from ClassicLib.MessageHandler.MessageHandler import MessageHandler

    for cls in [GlobalRegistry, MessageHandler]:
        if hasattr(cls, "_instance"):
            delattr(cls, "_instance")

    yield  # Run test

    # Cleanup after test
    gc.collect()
```

### 3. Use Async Fixtures Properly

```python
@pytest.fixture
async def async_setup():
    """Async fixture setup."""
    from ClassicLib.FileIOCore import FileIOCore
    io_core = FileIOCore()

    # Setup
    await io_core.initialize()

    yield io_core

    # Teardown
    await io_core.cleanup()
```

### 4. Test Both Success and Failure Paths

```python
def test_operation_success_and_failure():
    """Test both success and failure scenarios."""
    # Success case
    result = operation(valid_input)
    assert result.success

    # Failure case
    with pytest.raises(ExpectedException):
        operation(invalid_input)

    # Recovery case
    operation(invalid_input, recover=True)
    assert result.recovered
```

### 5. Use Realistic Test Sizes

- Typical crash logs: 1-2MB (actual crash log size range)
- Plugin lists: 50-150 plugins (typical modded setup)
- FormID counts: 100-1000 per file
- Concurrent operations: 10-50 (realistic user behavior)

## Common Patterns

### Testing Async/Sync Bridge

```python
def test_async_bridge_pattern():
    """Test AsyncBridge usage pattern."""
    from ClassicLib.core.async_bridge import AsyncBridge

    bridge = AsyncBridge.get_instance()

    # Async function to test
    async def async_operation():
        await asyncio.sleep(0.1)
        return "result"

    # Sync context using bridge
    result = bridge.run_async(async_operation())
    assert result == "result"
```

### Testing Rust FFI Components

```python
def test_rust_component_pattern():
    """Test Rust component with fallback."""
    from ClassicLib.integration.factory import get_parser
    from ClassicLib.integration.status import is_rust_accelerated

    parser = get_parser()
    using_rust = is_rust_accelerated("parser")

    # Test with different expectations based on acceleration
    result = parser.parse(test_data)

    if using_rust:
        # Expect faster performance with Rust
        assert parse_time < 0.5
    else:
        # Python fallback is slower
        assert parse_time < 3.0
```

### Testing File I/O with Proper Cleanup

```python
@pytest.mark.asyncio
async def test_file_io_pattern():
    """Test file I/O with proper cleanup."""
    from ClassicLib.FileIOCore import FileIOCore
    io_core = FileIOCore()

    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = Path(temp_dir) / "test.log"

        try:
            # Write test
            await io_core.write_file(str(file_path), "content")

            # Read test
            content = await io_core.read_file(str(file_path))
            assert content == "content"

        finally:
            # Cleanup is automatic with TemporaryDirectory
            pass
```

## Test Data Guidelines

### What We Can Use (Crash Log Data)
- ✅ Actual crash log formats and patterns
- ✅ Real plugin list structures from logs
- ✅ Actual FormID patterns (hex values)
- ✅ Real stack trace formats
- ✅ Memory dump patterns from crash logs
- ✅ Exception types and addresses
- ✅ Buffout 4 log formats
- ✅ System spec sections

### What We Still Avoid (Game Content)
- ❌ Actual game executable files
- ❌ Game data files (.esm, .esp, .ba2)
- ❌ Proprietary game assets
- ❌ Game scripts or code
- ❌ Texture/model/audio files

### Creating Mock Game Files for Testing

When we need to test file operations, we use synthetic content:

```python
def create_mock_game_files(root_path: Path) -> None:
    """Create mock game files with synthetic content."""
    # We create files with the right names but synthetic content
    (root_path / "Data" / "Fallout4.esm").write_bytes(b"SYNTHETIC_MASTER_FILE")
    (root_path / "Data" / "DLCRobot.esm").write_bytes(b"SYNTHETIC_DLC_FILE")

    # We don't use actual game file content, just placeholders
```

## Performance Testing Guidelines

### Baseline Expectations

With Rust acceleration:
- Log parsing (1MB): <200ms
- FormID analysis (1000 IDs): <10ms
- File I/O (100KB): <5ms

Python fallback:
- Log parsing (1MB): <2s
- FormID analysis (1000 IDs): <250ms
- File I/O (100KB): <50ms

### Memory Usage Targets
- Peak memory under load: <500MB
- Memory leak tolerance: <50MB over 100 operations
- Thread count limit: <50 active threads

## Test Execution

### Quick Unit Tests
```bash
pytest tests/ -m "unit and not slow" -n 4
```

### Full Test Suite
```bash
pytest tests/ --cov=ClassicLib --cov-report=html -n auto
```

### Stress Tests Only
```bash
pytest tests/stress/ -m stress --timeout=60
```

### Rust Integration Tests
```bash
pytest tests/rust_integration/ -v
```

## Debugging Failed Tests

### Enable Verbose Output
```bash
pytest -vvs tests/failing_test.py::test_specific
```

### Check Rust Status
```python
from ClassicLib.integration.status import print_rust_status
print_rust_status()
```

### Memory Profiling
```python
import tracemalloc
tracemalloc.start()
# ... test code ...
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')[:10]
```

## Contributing New Tests

1. **Follow naming conventions** - Use descriptive names
2. **Add appropriate markers** - Help with test organization
3. **Use actual crash log patterns** - They're diagnostic data, not game content
4. **Use synthetic game files** - Don't include actual .esm/.esp files
5. **Clean up resources** - Use context managers and fixtures
6. **Test edge cases** - Not just happy paths
7. **Document complex tests** - Add docstrings explaining logic
8. **Consider performance** - Set appropriate timeouts
9. **Validate with coverage** - Ensure new tests add value

---

*Last Updated: 2025-01-25*
*Coverage Target: 85%*
*Current Coverage: 50% (improving)*