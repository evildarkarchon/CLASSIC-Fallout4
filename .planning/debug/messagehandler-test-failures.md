---
status: diagnosed
trigger: "MessageHandler not initialized test failures after reset_all_singletons fixture"
created: 2026-02-02T03:45:00Z
updated: 2026-02-02T03:45:00Z
---

## Root Cause Analysis: MessageHandler Initialization Failures

### Summary

**Root Cause:** Four tests fail with `RuntimeError: Message handler not initialized` because they directly or indirectly call `get_message_handler()` without first calling `init_message_handler()`. The `reset_all_singletons` autouse fixture (added in Phase 01 Plan 03) correctly resets `_message_handler = None` after each test, exposing pre-existing state leakage where these tests relied on MessageHandler being initialized by previous tests.

**Status:** All four failures are **pre-existing state-leakage bugs exposed by the fixture**, NOT regressions introduced by the fixture itself.

### Evidence

#### 1. How MessageHandler Reset Works

From `tests/fixtures/singleton_fixtures.py` lines 85-92:

```python
# MessageHandler
try:
    import ClassicLib.messaging.handler as handler_mod

    with handler_mod._message_handler_lock:
        handler_mod._message_handler = None
except (ImportError, AttributeError):
    pass
```

The fixture correctly resets the module-level `_message_handler` singleton to `None` after each test.

From `ClassicLib/messaging/handler.py` lines 272-286:

```python
def get_message_handler() -> MessageHandler:
    """Get the global message handler.

    Returns:
        The initialized message handler.

    Raises:
        RuntimeError: If handler not initialized.

    """
    with _message_handler_lock:
        if _message_handler is None:
            msg = "Message handler not initialized. Call init_message_handler() first."
            raise RuntimeError(msg)
        return _message_handler
```

**Expected behavior:** Tests that use MessageHandler must explicitly call `init_message_handler()` before using convenience functions like `msg_info()`, `msg_warning()`, etc., which internally call `get_message_handler()`.

#### 2. Analysis of Failing Tests

**Test 1 & 2: GUI Settings E2E Tests**

File: `tests/gui/settings/test_settings_persistence_e2e.py`

Lines 19-44:
```python
def test_settings_persistence_across_instances(self, app, reset_settings):
    """Test that settings persist across dialog instances."""
    from tests.fixtures.gui_settings_fixtures import get_game_version_value, set_game_version_by_value

    dialog1 = SettingsDialog(yaml_store=YAML.TEST)
    set_game_version_by_value(dialog1.game_version_combo, "VR")
    dialog1.fcx_checkbox.setChecked(False)
    dialog1.save_settings()
    dialog1.close()
    dialog2 = SettingsDialog(yaml_store=YAML.TEST)
    assert get_game_version_value(dialog2.game_version_combo) == "VR"
    assert not dialog2.fcx_checkbox.isChecked()
    dialog2.close()
```

**Problem:** Tests use `app` fixture but do NOT initialize MessageHandler. They directly instantiate `SettingsDialog`, which may internally call MessageHandler methods.

**Fixture availability:** The `gui_settings_dialog` fixture (lines 210-236 in `tests/fixtures/gui_settings_fixtures.py`) properly calls `init_message_handler()`:

```python
@pytest.fixture
def gui_settings_dialog(
    gui_settings_app: Any,
    gui_settings_mock_cache: MockSettingsCache,
) -> Generator[SettingsDialog, None, None]:
    """Create a SettingsDialog instance for testing."""
    # Initialize message handler for GUI mode
    handler = init_message_handler(parent=None, is_gui_mode=True)

    # Mock the GUI backend's show method to prevent blocking QMessageBox
    handler._gui_backend.show = MagicMock()

    # Create dialog as NON-MODAL to prevent freezing in tests
    dialog = SettingsDialog(yaml_store=YAML.TEST, modal=False)
    yield dialog
    dialog.close()
```

**Diagnosis:** Tests 1 & 2 use `app` fixture directly instead of using the provided `gui_settings_dialog` fixture. They manually create `SettingsDialog` instances without initializing MessageHandler first. This worked previously only because a prior test had initialized it.

**Pre-existing confirmation:** From `.planning/phases/01-foundation-cleanup/01-03-SUMMARY.md` lines 88-93:

```markdown
**1. Test state leakage exposed in settings e2e test**

- **Found during:** Task 2 verification (broader test run)
- **Issue:** `tests/gui/settings/test_settings_persistence_e2e.py::test_settings_persistence_across_instances` fails because it relies on MessageHandler being initialized by a previous test -- classic state leakage
- **Confirmed pre-existing:** Test also fails on pre-change codebase when run in isolation
- **Action:** Not fixed (out of scope), documented for future cleanup
```

**Test 3: Async Pipeline Performance Test**

File: `tests/performance/test_async_pipeline_performance.py`

Lines 76-126:
```python
@pytest.mark.slow
@pytest.mark.asyncio
async def test_async_pipeline_scalability_baseline(self, tmp_path: Path, mock_yamldata: MagicMock) -> None:
    """Baseline: Async pipeline scalability with different log counts."""
    from collections import Counter

    test_counts = [5, 10, 25]
    results = []

    for count in test_counts:
        test_files = create_large_crash_log_set(tmp_path / f"scale_{count}", count)

        pipeline = AsyncCrashLogPipeline(
            yamldata=mock_yamldata,
            fcx_mode=False,
            show_formid_values=False,
            formid_db_exists=False,
        )
        # ... pipeline execution with mocks
```

**Problem:** Test uses `mock_yamldata` fixture but does NOT initialize MessageHandler before creating `AsyncCrashLogPipeline`. The pipeline may internally use messaging functions for logging/progress updates.

**Diagnosis:** Performance test creates pipeline without ensuring MessageHandler is initialized. Worked previously due to state leakage from other tests.

**Test 4: Crash Log Processing Performance Test**

File: `tests/performance/test_crash_log_processing_performance.py`

Lines 30-175:
```python
async def test_real_world_crash_logs_performance(self, mock_yamldata: MagicMock, performance_test_logs: list[Path]) -> None:
    """Real-world performance test: Process crash logs using test fixtures."""
    # Use fixture-provided crash log files
    crash_log_files: list[Path] = performance_test_logs

    print("\n=== REAL-WORLD CRASH LOGS PERFORMANCE TEST ===")
    print(f"Processing {len(crash_log_files)} actual crash logs")

    # ... lots of processing code

    pipeline: AsyncCrashLogPipeline = AsyncCrashLogPipeline(
        yamldata=mock_yamldata,
        fcx_mode=False,
        show_formid_values=True,
        formid_db_exists=False,
    )
    # ... pipeline execution
```

**Problem:** Test uses `print()` statements (lines 39, 40, 115, etc.) and creates `AsyncCrashLogPipeline` without initializing MessageHandler. Pipeline internals likely call messaging functions.

**Diagnosis:** Same as Test 3 -- performance test relies on state leakage from other tests for MessageHandler initialization.

#### 3. Fixture Availability Analysis

**For GUI tests (Tests 1 & 2):**
- `gui_settings_fixtures.py` provides `gui_settings_dialog` fixture that properly initializes MessageHandler (line 227)
- Tests use `app` and `reset_settings` fixtures but do NOT use `gui_settings_dialog`
- Tests manually create `SettingsDialog` instances without initialization

**For performance tests (Tests 3 & 4):**
- `performance_fixtures.py` provides only file/path fixtures (perf_test_logs, perf_sample_crash_logs_dir, etc.)
- NO MessageHandler initialization fixture exists in performance_fixtures.py
- `mock_yamldata` fixture (from `yamldata_fixtures.py`) does NOT initialize MessageHandler

**For comparison - working fixtures:**
- `tests/fixtures/gui_settings_fixtures.py` line 227: `init_message_handler(parent=None, is_gui_mode=True)`
- Other test categories that pass likely have similar initialization patterns

### Root Cause Summary

**Direct cause:** Tests call code that invokes `get_message_handler()` without first calling `init_message_handler()`.

**Why it worked before:** Test execution order was such that a previous test initialized MessageHandler, and it persisted across tests because no reset mechanism existed.

**Why it fails now:** The `reset_all_singletons` autouse fixture correctly resets MessageHandler after each test, exposing the missing initialization in these four tests.

**Classification:** **Pre-existing state-leakage bugs exposed by fixture** (NOT regressions)

### Evidence of Pre-existing Issues

From `.planning/phases/01-foundation-cleanup/01-03-SUMMARY.md` (lines 88-93):

1. **Confirmed during Plan 03 verification:** Settings e2e test was explicitly discovered and documented as pre-existing
2. **Confirmed via isolation test:** "Test also fails on pre-change codebase when run in isolation"
3. **Documented decision:** "Not fixed (out of scope), documented for future cleanup"

The other 3 tests (2 performance tests) follow the same pattern and exhibit the same root cause (missing initialization).

### Test Failure Breakdown

| Test | File | Root Cause | Fixture Available | Fix Type |
|------|------|-----------|------------------|----------|
| test_settings_persistence_across_instances | test_settings_persistence_e2e.py | Uses `app` instead of `gui_settings_dialog` fixture | YES (gui_settings_dialog) | Use existing fixture |
| test_settings_reload_after_save | test_settings_persistence_e2e.py | Uses `app` instead of `gui_settings_dialog` fixture | YES (gui_settings_dialog) | Use existing fixture |
| test_async_pipeline_scalability_baseline | test_async_pipeline_performance.py | No MessageHandler init before pipeline creation | NO | Add init call or fixture |
| test_real_world_crash_logs_performance | test_crash_log_processing_performance.py | No MessageHandler init before pipeline creation | NO | Add init call or fixture |

### Recommended Fixes

**GUI Tests (1 & 2):**
- Replace `app` fixture usage with `gui_settings_dialog` fixture
- OR add `init_message_handler(parent=None, is_gui_mode=True)` call in test setup

**Performance Tests (3 & 4):**
- Add `init_message_handler(is_gui_mode=False)` call at test start
- OR create a `message_handler_cli` fixture in `performance_fixtures.py` that initializes for CLI mode

### Files Involved

**Fixture implementation:**
- `tests/fixtures/singleton_fixtures.py` (lines 85-92) - MessageHandler reset logic
- `tests/conftest.py` - autouse fixture registration

**Handler implementation:**
- `ClassicLib/messaging/handler.py` (lines 240-286) - init/get functions

**Failing test files:**
- `tests/gui/settings/test_settings_persistence_e2e.py` (Tests 1 & 2)
- `tests/performance/test_async_pipeline_performance.py` (Test 3)
- `tests/performance/test_crash_log_processing_performance.py` (Test 4)

**Working fixture example:**
- `tests/fixtures/gui_settings_fixtures.py` (lines 210-236) - gui_settings_dialog fixture with proper init

### Conclusion

All four test failures are **pre-existing state-leakage bugs** that were hidden by test execution order. The `reset_all_singletons` fixture is functioning correctly and has successfully exposed these bugs. The fixture should NOT be modified or removed -- instead, the four failing tests need to be fixed to properly initialize MessageHandler before use.

**The fixture is working as designed.** These failures confirm the fixture's value in enforcing test isolation.
