# FCX Mode Read-Only Conversion Plan

Note: this is a historical implementation/design document. Some examples reference older `classic_core` or legacy Python runtime structures and should not be treated as current binding guidance.

**Status**: In Progress (Phases 1-4 Complete, Documentation Updated)
**Created**: 2025-10-29
**Last Updated**: 2025-10-29
**Breaking Change**: Yes - No backward compatibility
**Scope**: Python + Rust implementations

## Executive Summary

Convert FCX (File Check eXtended) mode from auto-fixing configuration files to a read-only diagnostic feature. All detected issues will be reported with detailed recommendations instead of being automatically fixed.

## Rationale

### Current Behavior (Auto-Fix)
- FCX mode automatically modifies user configuration files without explicit consent
- 5 specific fixes are applied automatically:
  1. ESPExplorer hotkey configuration
  2. EPO particle count limits
  3. F4EE head parts unlock
  4. F4EE face tints unlock
  5. High FPS Physics Fix loading screen FPS
- No rollback capability
- No structured audit log of changes
- Users may not realize files were modified

### New Behavior (Read-Only Reporting)
- FCX mode detects issues but never modifies files
- Comprehensive reports include:
  - Issue description
  - Current value vs. recommended value
  - Exact file path and section/setting
  - Manual fix instructions
- Users maintain full control over their configuration
- No risk of unintended modifications
- Clear audit trail in crash log report

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Fix functionality | **Completely removed** | Auto-fix without consent is problematic |
| Backward compatibility | **None** | Clean break, no legacy code paths |
| Language scope | **Both Python and Rust** | Maintain consistency across implementations |
| Report format | **Text-based markdown** (existing) | User familiarity, add recommendation sections |
| Report detail level | **Current vs. Recommended + Path** | Actionable information for manual fixes |
| Documentation location | **docs/implementation/** | Implementation planning documentation |

## Files to Modify

### Phase 1: Core Fix Logic (Remove Write Operations)

#### ClassicLib/ScanGame/Config.py
**Lines affected**: 485-527, 571-599+

**Current behavior:**
```python
def set[T](self, value_type: type[T], file_name_lower: str,
           section: str, setting: str, value: T) -> None:
    # ... validation ...
    config.set(section, setting, value)

    if not TEST_MODE:
        with cache["path"].open("w", encoding=cache["encoding"], newline="") as f:
            config.write(f)  # ← DIRECT FILE WRITE (REMOVE THIS)
```

**Changes required:**
1. **Remove**: `ConfigFileCache.set()` method entirely
2. **Remove**: `mod_toml_config()` method or make it return recommended changes only
3. **Add**: New method `ConfigFileCache.get_issue_report()` for generating fix recommendations
4. **Add**: New method `ConfigFileCache.detect_issue()` for issue detection without modification

**New API:**
```python
@dataclass
class ConfigIssue:
    """Detected configuration issue with recommendation."""
    file_path: Path
    section: str | None
    setting: str
    current_value: str
    recommended_value: str
    description: str
    severity: Literal["warning", "error", "info"]

def detect_issue(self, file_name_lower: str, section: str,
                setting: str, expected_value: str,
                description: str) -> ConfigIssue | None:
    """Detect configuration issue without modifying file."""
    # Detection logic only

def get_issue_report(self, issue: ConfigIssue) -> str:
    """Format issue as human-readable report section."""
    # Generate markdown report
```

---

#### ClassicLib/ScanGame/ScanModInis.py
**Lines affected**: 222-260 (apply_ini_fix_async), related helper functions

**Current behavior:**
```python
async def apply_ini_fix_async(
    config_files: ConfigFileCache,
    fix_type: str,
    file_name: str,
    section: str,
    setting: str,
    value: str | float,
    condition: Callable[[str | float], bool],
    message_list: list[str],
) -> None:
    """Apply INI fix if condition is met."""
    # ... detection logic ...
    if condition(current_value):
        config_files.set(value.__class__, file_name.lower(), section, setting, value)
        message_list.append(f"> Performed {fix_type.title()} Fix For : {config_files[file_name]}\n")
```

**Changes required:**
1. **Rename**: `apply_ini_fix_async()` → `detect_ini_issue_async()`
2. **Rename**: `apply_all_ini_fixes_async()` → `detect_all_ini_issues_async()`
3. **Remove**: All calls to `config_files.set()`
4. **Change**: Return `ConfigIssue` objects instead of modifying `message_list`
5. **Keep**: All detection and validation logic unchanged

**New API:**
```python
async def detect_ini_issue_async(
    config_files: ConfigFileCache,
    issue_type: str,
    file_name: str,
    section: str,
    setting: str,
    recommended_value: str | float,
    condition: Callable[[str | float], bool],
    description: str,
) -> ConfigIssue | None:
    """Detect INI configuration issue without modifying file."""
    current_value = config_files.get_setting(file_name.lower(), section, setting)

    if current_value is None:
        return None

    if condition(current_value):
        return ConfigIssue(
            file_path=config_files[file_name],
            section=section,
            setting=setting,
            current_value=str(current_value),
            recommended_value=str(recommended_value),
            description=description,
            severity="warning"
        )

    return None

async def detect_all_ini_issues_async(
    config_files: ConfigFileCache
) -> list[ConfigIssue]:
    """Detect all INI configuration issues."""
    issues = []

    # ESPExplorer hotkey check
    if "espexplorer.ini" in config_files:
        issue = await detect_ini_issue_async(
            config_files,
            "ini_hotkey",
            "espexplorer.ini",
            "Main",
            "HotKey",
            "0x79",
            lambda val: isinstance(val, str) and val.startswith(";"),
            "Hotkey is commented out and won't work. Change to hex code 0x79 for F10."
        )
        if issue:
            issues.append(issue)

    # EPO particle count check
    if "epo.ini" in config_files:
        issue = await detect_ini_issue_async(
            config_files,
            "particle_count",
            "epo.ini",
            "Particles",
            "iMaxDesired",
            5000,
            lambda val: int(val) > 5000,
            "High particle count can cause performance issues and crashes."
        )
        if issue:
            issues.append(issue)

    # F4EE head parts check
    if "f4ee.ini" in config_files:
        issue = await detect_ini_issue_async(
            config_files,
            "head_parts",
            "f4ee.ini",
            "HeadParts",
            "bUnlockHeadParts",
            1,
            lambda val: int(val) == 0,
            "Head parts are locked. Set to 1 to unlock all head parts."
        )
        if issue:
            issues.append(issue)

    # F4EE face tints check
    if "f4ee.ini" in config_files:
        issue = await detect_ini_issue_async(
            config_files,
            "face_tints",
            "f4ee.ini",
            "HeadParts",
            "bUnlockTints",
            1,
            lambda val: int(val) == 0,
            "Face tints are locked. Set to 1 to unlock all face tints."
        )
        if issue:
            issues.append(issue)

    # High FPS Physics Fix loading screen FPS
    if "highfpsphysicsfix.ini" in config_files:
        issue = await detect_ini_issue_async(
            config_files,
            "loading_fps",
            "highfpsphysicsfix.ini",
            "Limiter",
            "LoadingScreenFPS",
            600.0,
            lambda val: float(val) < 600,
            "Loading screen FPS is too low. Increase to 600.0 to prevent physics issues."
        )
        if issue:
            issues.append(issue)

    return issues
```

---

### Phase 2: FCX Handler (Update Report Generation)

#### ClassicLib/ScanLog/FCXModeHandler.py
**Lines affected**: 58-84 (check_fcx_mode), 86-95 (get_fcx_messages)

**Current behavior:**
```python
def check_fcx_mode(self) -> None:
    """Run FCX mode checks once per scan."""
    if self._fcx_checks_run:
        return

    self._fcx_checks_run = True

    if not self._fcx_mode:
        return

    self._main_files_result = SetupCoordinator.generate_combined_results()
    self._game_files_result = generate_game_combined_result()  # Contains auto-fixes
```

**Changes required:**
1. **Update**: `check_fcx_mode()` to collect `ConfigIssue` objects
2. **Add**: New class variable `_detected_issues: list[ConfigIssue]`
3. **Update**: `get_fcx_messages()` to format issue recommendations
4. **Add**: Helper method `_format_issue_report()` for consistent formatting
5. **Remove**: Fix confirmation messages ("> Performed ... Fix")

**New implementation:**
```python
from ClassicLib.ScanGame.Config import ConfigIssue

class FCXModeHandlerFragments:
    """FCX mode handler for extended file checks (read-only)."""

    _fcx_checks_run: bool = False
    _main_files_result: str = ""
    _game_files_result: str = ""
    _detected_issues: list[ConfigIssue] = []  # NEW

    def check_fcx_mode(self) -> None:
        """Run FCX mode checks once per scan (read-only detection)."""
        if self._fcx_checks_run:
            return

        self._fcx_checks_run = True

        if not self._fcx_mode:
            return

        # Existing setup checks (already read-only)
        self._main_files_result = SetupCoordinator.generate_combined_results()

        # Game file checks with issue detection (no auto-fix)
        self._game_files_result, self._detected_issues = generate_game_combined_result()

    def get_fcx_messages(self) -> str:
        """Generate FCX mode report with issue recommendations."""
        if not self._fcx_mode:
            return ""

        parts = [
            "* NOTICE: FCX MODE IS ENABLED. CLASSIC MUST BE RUN BY THE ORIGINAL USER FOR CORRECT DETECTION *\n",
            "[ To disable mod & game files detection, disable FCX Mode in the exe or CLASSIC Settings.yaml ]\n\n",
        ]

        # Main files result
        if self._main_files_result:
            parts.append(self._main_files_result)

        # Game files result
        if self._game_files_result:
            parts.append(self._game_files_result)

        # Detected issues with recommendations (NEW)
        if self._detected_issues:
            parts.append("\n--- DETECTED CONFIGURATION ISSUES ---\n\n")
            for issue in self._detected_issues:
                parts.append(self._format_issue_report(issue))

        return "".join(parts)

    @staticmethod
    def _format_issue_report(issue: ConfigIssue) -> str:
        """Format configuration issue as human-readable report."""
        severity_icon = {
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️"
        }

        icon = severity_icon.get(issue.severity, "⚠️")

        return f"""{icon} DETECTED ISSUE: {issue.description}
   File: {issue.file_path}
   Section: [{issue.section}]
   Setting: {issue.setting}
   Current Value: {issue.current_value}
   Recommended Value: {issue.recommended_value}

"""
```

---

#### ClassicLib/rust/fcx_rust.py
**Lines affected**: Entire file

**Changes required:**
1. **Update**: Wrapper methods to match new read-only API
2. **Remove**: Any fix-related method wrappers
3. **Add**: Support for `ConfigIssue` data structure

**New API:**
```python
class RustAcceleratedFcxModeHandler:
    """Rust-accelerated FCX mode handler (read-only)."""

    def __init__(self, fcx_mode: bool) -> None:
        try:
            from classic_core.fcx_handler import FCXModeHandler as RustFCXModeHandler
            self._handler = RustFCXModeHandler(fcx_mode)
            self._rust_available = True
        except ImportError:
            from ClassicLib.ScanLog.FCXModeHandler import FCXModeHandlerFragments
            self._handler = FCXModeHandlerFragments(fcx_mode)
            self._rust_available = False

    def check_fcx_mode(self) -> None:
        """Run FCX mode checks (read-only detection)."""
        self._handler.check_fcx_mode()

    def get_fcx_messages(self) -> str:
        """Generate FCX mode report with issue recommendations."""
        return self._handler.get_fcx_messages()

    def reset_fcx_checks(self) -> None:
        """Reset FCX checks for new scan."""
        self._handler.reset_fcx_checks()
```

---

### Phase 3: Rust Implementation Updates

#### ClassicLib-rs/business-logic/classic-scanlog-core/src/fcx_handler.rs
**Lines affected**: Entire file

**Current behavior:**
```rust
pub struct FCXModeHandler {
    fcx_mode: bool,
    fcx_checks_run: bool,
    main_files_result: String,
    game_files_result: String,
}
```

**Changes required:**
1. **Remove**: Any fix-related state or methods
2. **Keep**: Detection state management
3. **Add**: Support for issue data structures if needed

**New implementation:**
```rust
use std::sync::Arc;
use parking_lot::RwLock;

/// Configuration issue detected by FCX mode.
#[derive(Debug, Clone)]
pub struct ConfigIssue {
    pub file_path: String,
    pub section: Option<String>,
    pub setting: String,
    pub current_value: String,
    pub recommended_value: String,
    pub description: String,
    pub severity: String,  // "error", "warning", "info"
}

/// FCX mode handler for extended file checks (read-only).
#[derive(Debug)]
pub struct FCXModeHandler {
    fcx_mode: bool,
    fcx_checks_run: bool,
    main_files_result: String,
    game_files_result: String,
    detected_issues: Vec<ConfigIssue>,
}

impl FCXModeHandler {
    pub fn new(fcx_mode: bool) -> Self {
        Self {
            fcx_mode,
            fcx_checks_run: false,
            main_files_result: String::new(),
            game_files_result: String::new(),
            detected_issues: Vec::new(),
        }
    }

    pub fn check_fcx_mode(&mut self) {
        if self.fcx_checks_run {
            return;
        }

        self.fcx_checks_run = true;

        if !self.fcx_mode {
            return;
        }

        // Call Python functions for actual checks
        // (Python-side logic handles detection)
    }

    pub fn get_fcx_messages(&self) -> String {
        if !self.fcx_mode {
            return String::new();
        }

        // Format report with detected issues
        // (Python-side formatting handles details)
        String::new()
    }

    pub fn reset_fcx_checks(&mut self) {
        self.fcx_checks_run = false;
        self.main_files_result.clear();
        self.game_files_result.clear();
        self.detected_issues.clear();
    }

    pub fn get_detected_issues(&self) -> &[ConfigIssue] {
        &self.detected_issues
    }
}
```

---

#### ClassicLib-rs/python-bindings/classic-scanlog-py/src/fcx_handler.rs
**Lines affected**: Entire file

**Changes required:**
1. **Remove**: Fix-related PyO3 method exports
2. **Update**: Method signatures to match new read-only API
3. **Add**: PyO3 wrapper for `ConfigIssue` if exposing to Python

**New implementation:**
```rust
use pyo3::prelude::*;
use classic_scanlog_core::fcx_handler::{FCXModeHandler as CoreFCXModeHandler, ConfigIssue as CoreConfigIssue};

/// Configuration issue detected by FCX mode (Python wrapper).
#[pyclass(name = "ConfigIssue")]
#[derive(Debug, Clone)]
pub struct PyConfigIssue {
    #[pyo3(get)]
    pub file_path: String,
    #[pyo3(get)]
    pub section: Option<String>,
    #[pyo3(get)]
    pub setting: String,
    #[pyo3(get)]
    pub current_value: String,
    #[pyo3(get)]
    pub recommended_value: String,
    #[pyo3(get)]
    pub description: String,
    #[pyo3(get)]
    pub severity: String,
}

impl From<CoreConfigIssue> for PyConfigIssue {
    fn from(issue: CoreConfigIssue) -> Self {
        Self {
            file_path: issue.file_path,
            section: issue.section,
            setting: issue.setting,
            current_value: issue.current_value,
            recommended_value: issue.recommended_value,
            description: issue.description,
            severity: issue.severity,
        }
    }
}

/// FCX mode handler for extended file checks (read-only).
#[pyclass(name = "FCXModeHandler")]
pub struct PyFCXModeHandler {
    handler: CoreFCXModeHandler,
}

#[pymethods]
impl PyFCXModeHandler {
    #[new]
    fn new(fcx_mode: bool) -> Self {
        Self {
            handler: CoreFCXModeHandler::new(fcx_mode),
        }
    }

    fn check_fcx_mode(&mut self) {
        self.handler.check_fcx_mode();
    }

    fn get_fcx_messages(&self) -> String {
        self.handler.get_fcx_messages()
    }

    fn reset_fcx_checks(&mut self) {
        self.handler.reset_fcx_checks();
    }

    fn get_detected_issues(&self) -> Vec<PyConfigIssue> {
        self.handler.get_detected_issues()
            .iter()
            .cloned()
            .map(PyConfigIssue::from)
            .collect()
    }
}

pub fn register_fcx_module(parent_module: &Bound<'_, PyModule>) -> PyResult<()> {
    let fcx_module = PyModule::new(parent_module.py(), "fcx_handler")?;
    fcx_module.add_class::<PyConfigIssue>()?;
    fcx_module.add_class::<PyFCXModeHandler>()?;
    parent_module.add_submodule(&fcx_module)?;
    Ok(())
}
```

---

### Phase 4: Data Models (New)

#### ClassicLib/ScanGame/models/fcx_issue.py (NEW FILE)
**Purpose**: Structured data model for configuration issues

```python
"""Data models for FCX mode configuration issues."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

__all__ = ["ConfigIssue", "ConfigIssueSeverity"]

ConfigIssueSeverity = Literal["error", "warning", "info"]

@dataclass
class ConfigIssue:
    """Detected configuration issue with recommendation.

    Attributes:
        file_path: Path to the configuration file
        section: INI section name (None for TOML or non-sectioned files)
        setting: Setting/key name
        current_value: Current value in the file
        recommended_value: Recommended value to fix the issue
        description: Human-readable description of the issue
        severity: Issue severity level
    """

    file_path: Path
    section: str | None
    setting: str
    current_value: str
    recommended_value: str
    description: str
    severity: ConfigIssueSeverity = "warning"

    def __post_init__(self) -> None:
        """Validate data after initialization."""
        if not isinstance(self.file_path, Path):
            self.file_path = Path(self.file_path)

        if self.severity not in ("error", "warning", "info"):
            raise ValueError(f"Invalid severity: {self.severity}")

    def format_report(self) -> str:
        """Format issue as human-readable report section."""
        severity_icons = {
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️"
        }

        icon = severity_icons.get(self.severity, "⚠️")
        section_str = f"[{self.section}]" if self.section else "N/A"

        return f"""{icon} DETECTED ISSUE: {self.description}
   File: {self.file_path}
   Section: {section_str}
   Setting: {self.setting}
   Current Value: {self.current_value}
   Recommended Value: {self.recommended_value}

"""
```

---

### Phase 5: Game Integrity (Minor Adjustments)

#### ClassicLib/ScanGame/GameIntegrityOrchestrator.py
**Changes required**: Update to return detected issues alongside results

**Current:**
```python
def generate_game_combined_result() -> str:
    """Generate combined game files check result."""
    # ... existing logic ...
    return "\n".join(results)
```

**New:**
```python
def generate_game_combined_result() -> tuple[str, list[ConfigIssue]]:
    """Generate combined game files check result with detected issues.

    Returns:
        Tuple of (report_text, detected_issues)
    """
    from ClassicLib.ScanGame.ScanModInis import detect_all_ini_issues_async
    from ClassicLib.ScanGame.Config import ConfigFileCache

    results = []
    detected_issues = []

    # ... existing read-only checks ...

    # Detect configuration issues (no auto-fix)
    config_cache = ConfigFileCache.get_instance()
    issues = await detect_all_ini_issues_async(config_cache)
    detected_issues.extend(issues)

    return "\n".join(results), detected_issues
```

---

### Phase 6: Tests (Update All)

#### tests/scanlog/test_fcx_handler.py
**Changes required:**
1. Remove all fix verification tests
2. Add issue detection tests
3. Verify report format includes recommendations
4. Ensure no file modifications occur

**New test structure:**
```python
import pytest
from pathlib import Path
from ClassicLib.ScanLog.FCXModeHandler import FCXModeHandlerFragments
from ClassicLib.ScanGame.models.fcx_issue import ConfigIssue

@pytest.mark.unit
@pytest.mark.asyncio
class TestFCXModeHandlerReadOnly:
    """Test FCX mode handler read-only behavior."""

    def test_fcx_mode_no_file_writes(self, tmp_path):
        """Verify FCX mode never writes to files."""
        # Create test INI with issues
        ini_path = tmp_path / "test.ini"
        ini_path.write_text("[Main]\nHotKey = ; F10\n")

        # Track file modification time
        initial_mtime = ini_path.stat().st_mtime

        # Run FCX checks
        handler = FCXModeHandlerFragments(fcx_mode=True)
        handler.check_fcx_mode()

        # Verify file was NOT modified
        assert ini_path.stat().st_mtime == initial_mtime

    def test_fcx_detects_espexplorer_hotkey_issue(self):
        """Verify ESPExplorer hotkey issue detection."""
        # ... test detection logic ...

    def test_fcx_report_includes_recommendations(self):
        """Verify FCX report includes current vs. recommended values."""
        handler = FCXModeHandlerFragments(fcx_mode=True)
        handler.check_fcx_mode()

        report = handler.get_fcx_messages()

        # Verify report format
        assert "Current Value:" in report
        assert "Recommended Value:" in report
        assert "File:" in report
        assert "DETECTED ISSUE:" in report

    def test_config_issue_data_structure(self):
        """Verify ConfigIssue data structure."""
        issue = ConfigIssue(
            file_path=Path("/test/file.ini"),
            section="Main",
            setting="HotKey",
            current_value="; F10",
            recommended_value="0x79",
            description="Hotkey is commented out",
            severity="warning"
        )

        assert issue.file_path == Path("/test/file.ini")
        assert issue.section == "Main"
        assert issue.severity == "warning"

        report = issue.format_report()
        assert "⚠️ DETECTED ISSUE:" in report
        assert "Current Value: ; F10" in report
        assert "Recommended Value: 0x79" in report
```

#### tests/scanlog/test_config_file_cache.py
**Changes required:**
1. Remove `set()` write operation tests
2. Keep all read/detection tests
3. Add `detect_issue()` tests

```python
@pytest.mark.unit
class TestConfigFileCacheReadOnly:
    """Test ConfigFileCache read-only operations."""

    def test_no_set_method_exists(self):
        """Verify set() method has been removed."""
        from ClassicLib.ScanGame.Config import ConfigFileCache

        cache = ConfigFileCache()
        assert not hasattr(cache, "set"), "set() method should be removed"

    def test_detect_issue_method_exists(self):
        """Verify detect_issue() method exists."""
        from ClassicLib.ScanGame.Config import ConfigFileCache

        cache = ConfigFileCache()
        assert hasattr(cache, "detect_issue"), "detect_issue() method should exist"

    def test_detect_issue_returns_correct_structure(self):
        """Verify detect_issue() returns ConfigIssue or None."""
        # ... test detection logic ...
```

#### tests/rust_integration/test_fcx_integration.py
**Changes required:**
1. Update to test read-only Rust behavior
2. Verify Rust-Python issue data passing
3. Ensure no file writes from Rust side

```python
@pytest.mark.rust
@pytest.mark.integration
class TestRustFCXIntegration:
    """Test Rust-accelerated FCX mode read-only behavior."""

    def test_rust_fcx_no_file_writes(self, tmp_path):
        """Verify Rust FCX implementation never writes files."""
        from ClassicLib.rust.fcx_rust import RustAcceleratedFcxModeHandler

        # ... test Rust implementation ...

    def test_rust_python_issue_data_passing(self):
        """Verify ConfigIssue data passes correctly between Rust and Python."""
        # ... test PyO3 data conversion ...
```

---

### Phase 7: Documentation

#### docs/RUST_DOCUMENTATION_INDEX.md
**Changes required**: Add reference to this implementation document

**Add to "Implementation Documentation" section:**
```markdown
### Implementation Documentation
- [FCX Mode Read-Only Conversion](implementation/fcx_read_only_conversion.md) - Converting FCX mode from auto-fix to read-only reporting (2025-10-29)
```

#### docs/rust/rust_usage_guide.md (Update)
**Changes required**: Update FCX mode section to reflect read-only behavior

**Old section:**
```markdown
### FCX Mode
FCX mode enables extended scans and automatic configuration fixes.
```

**New section:**
```markdown
### FCX Mode (Read-Only Diagnostic)
FCX mode enables extended scans and detailed configuration issue reporting.

**Behavior**: Read-only - no files are modified
**Output**: Comprehensive issue reports with recommendations

When enabled, FCX mode detects:
- Configuration issues in mod INI files
- VSync settings across multiple files
- Console command configurations
- Duplicate configuration files

Each detected issue includes:
- Current value vs. recommended value
- Exact file path and section/setting
- Description and severity level
- Manual fix instructions
```

---

## Implementation Steps

### Step 1: Create Data Model (No Breaking Changes)
**Estimated time**: 30 minutes

1. Create `ClassicLib/ScanGame/models/fcx_issue.py`
2. Implement `ConfigIssue` dataclass with validation
3. Add unit tests for data model
4. Verify imports work correctly

**Success criteria:**
- ✅ `ConfigIssue` class exists and is importable
- ✅ Data validation works (severity, file_path)
- ✅ `format_report()` method generates correct markdown
- ✅ Tests pass

---

### Step 2: Add Detection Methods (No Breaking Changes)
**Estimated time**: 1-2 hours

1. Add `ConfigFileCache.detect_issue()` method
2. Add `ConfigFileCache.get_issue_report()` method
3. Add `detect_ini_issue_async()` function in `ScanModInis.py`
4. Add `detect_all_ini_issues_async()` function
5. Keep existing `apply_*` methods unchanged (will remove later)
6. Add unit tests for detection methods

**Success criteria:**
- ✅ Detection methods work alongside existing fix methods
- ✅ No files are modified by detection methods
- ✅ `ConfigIssue` objects created correctly
- ✅ All tests pass (existing + new)

---

### Step 3: Update Report Generation (No Breaking Changes)
**Estimated time**: 1 hour

1. Add `_detected_issues` class variable to `FCXModeHandlerFragments`
2. Update `get_fcx_messages()` to include issue recommendations
3. Add `_format_issue_report()` helper method
4. Test new report format
5. Keep existing fix messages (will remove later)

**Success criteria:**
- ✅ Report includes "Recommended Fix" sections
- ✅ Current vs. recommended values displayed
- ✅ File paths shown correctly
- ✅ Existing report format preserved

---

### Step 4: Remove Write Operations (BREAKING CHANGES)
**Estimated time**: 2-3 hours

1. Remove `ConfigFileCache.set()` method entirely
2. Remove `mod_toml_config()` or make read-only
3. Remove `apply_ini_fix_async()` function
4. Remove `apply_all_ini_fixes_async()` function
5. Update `check_fcx_mode()` to use detection-only methods
6. Remove fix confirmation messages from reports
7. Update all callers to use new detection API

**Success criteria:**
- ✅ No file write operations remain in FCX code
- ✅ All fix-related methods removed
- ✅ Detection methods work correctly
- ✅ Reports show recommendations instead of "Performed Fix"

---

### Step 5: Update Tests (BREAKING CHANGES)
**Estimated time**: 2-3 hours

1. Remove all fix verification tests
2. Add file modification time checks (verify no writes)
3. Add detection accuracy tests
4. Add report format tests
5. Update test fixtures and mocks
6. Verify all test markers are correct

**Success criteria:**
- ✅ All tests pass
- ✅ No tests verify file modifications
- ✅ Tests verify read-only behavior
- ✅ Test coverage maintained or improved

---

### Step 6: Update Rust Implementation
**Estimated time**: 2-3 hours

1. Update `ClassicLib-rs/business-logic/classic-scanlog-core/src/fcx_handler.rs`:
   - Remove fix-related state
   - Add `ConfigIssue` struct
   - Update state management
2. Update `ClassicLib-rs/python-bindings/classic-scanlog-py/src/fcx_handler.rs`:
   - Add `PyConfigIssue` wrapper
   - Remove fix-related methods
   - Update PyO3 bindings
3. Update Rust tests
4. Rebuild Rust extensions

**Success criteria:**
- ✅ Rust compiles without warnings
- ✅ PyO3 bindings export correctly
- ✅ Rust tests pass
- ✅ Python can import Rust modules

---

### Step 7: Update Documentation
**Estimated time**: 1 hour

1. Update `docs/RUST_DOCUMENTATION_INDEX.md`
2. Update `docs/rust/rust_usage_guide.md`
3. Add migration notes for users
4. Update CLAUDE.md memories
5. Add code examples to documentation

**Success criteria:**
- ✅ All documentation updated
- ✅ Migration notes clear
- ✅ Code examples accurate
- ✅ CLAUDE.md reflects new behavior

---

### Step 8: Integration Testing
**Estimated time**: 1-2 hours

1. Run full test suite with `pytest -n auto`
2. Test CLI with `--fcx-mode` flag
3. Test GUI with FCX mode enabled
4. Verify Rust integration tests pass
5. Check report output manually
6. Verify no files modified during scan

**Success criteria:**
- ✅ All tests pass
- ✅ CLI works correctly
- ✅ GUI works correctly
- ✅ Reports show recommendations
- ✅ No files modified

---

## Report Format Examples

### Before (Auto-Fix Behavior)

```
* NOTICE: FCX MODE IS ENABLED. CLASSIC MUST BE RUN BY THE ORIGINAL USER FOR CORRECT DETECTION *
[ To disable mod & game files detection, disable FCX Mode in the exe or CLASSIC Settings.yaml ]

✔️ You have the latest version of Fallout 4!
✔️ F4SE is installed and up to date!

> Performed INI HOTKEY Fix For : C:\Users\...\Documents\My Games\Fallout4\F4SE\Plugins\espexplorer.ini
> Performed PARTICLE COUNT Fix For : C:\Users\...\Documents\My Games\Fallout4\F4SE\Plugins\epo.ini
> Performed HEAD PARTS Fix For : C:\Users\...\Documents\My Games\Fallout4\F4SE\Plugins\f4ee.ini
> Performed FACE TINTS Fix For : C:\Users\...\Documents\My Games\Fallout4\F4SE\Plugins\f4ee.ini

* NOTICE : VSYNC IS CURRENTLY ENABLED IN THE FOLLOWING FILES *
* Setting : iPresentInterval in enblocal.ini
```

### After (Read-Only Reporting)

```
* NOTICE: FCX MODE IS ENABLED. CLASSIC MUST BE RUN BY THE ORIGINAL USER FOR CORRECT DETECTION *
[ To disable mod & game files detection, disable FCX Mode in the exe or CLASSIC Settings.yaml ]

✔️ You have the latest version of Fallout 4!
✔️ F4SE is installed and up to date!

--- DETECTED CONFIGURATION ISSUES ---

⚠️ DETECTED ISSUE: Hotkey is commented out and won't work. Change to hex code 0x79 for F10.
   File: C:\Users\...\Documents\My Games\Fallout4\F4SE\Plugins\espexplorer.ini
   Section: [Main]
   Setting: HotKey
   Current Value: ; F10
   Recommended Value: 0x79

⚠️ DETECTED ISSUE: High particle count can cause performance issues and crashes.
   File: C:\Users\...\Documents\My Games\Fallout4\F4SE\Plugins\epo.ini
   Section: [Particles]
   Setting: iMaxDesired
   Current Value: 7500
   Recommended Value: 5000

⚠️ DETECTED ISSUE: Head parts are locked. Set to 1 to unlock all head parts.
   File: C:\Users\...\Documents\My Games\Fallout4\F4SE\Plugins\f4ee.ini
   Section: [HeadParts]
   Setting: bUnlockHeadParts
   Current Value: 0
   Recommended Value: 1

⚠️ DETECTED ISSUE: Face tints are locked. Set to 1 to unlock all face tints.
   File: C:\Users\...\Documents\My Games\Fallout4\F4SE\Plugins\f4ee.ini
   Section: [HeadParts]
   Setting: bUnlockTints
   Current Value: 0
   Recommended Value: 1

* NOTICE : VSYNC IS CURRENTLY ENABLED IN THE FOLLOWING FILES *
* Setting : iPresentInterval in enblocal.ini

ℹ️ DETECTED ISSUE: VSync is enabled. Disable iPresentInterval for better performance with high FPS mods.
   File: C:\Users\...\Documents\My Games\Fallout4\enblocal.ini
   Section: [ENGINE]
   Setting: iPresentInterval
   Current Value: 1
   Recommended Value: 0
```

---

## Risk Assessment

### Low Risk
- **Detection logic unchanged**: No changes to issue identification
- **Report generation only adds information**: Existing reports still work
- **No data loss concerns**: Read-only operations can't corrupt files
- **Gradual implementation**: Can be done incrementally

### Medium Risk
- **API changes**: Existing code calling removed methods will break
- **User expectation change**: Users expecting auto-fix will need to adapt
- **Test coverage**: Need comprehensive tests for new behavior

### High Risk
- **None identified**: This is a safe refactoring with clear boundaries

### Mitigation Strategies

1. **Incremental implementation**: Add new code before removing old code
2. **Comprehensive testing**: Unit + integration + manual testing
3. **Clear documentation**: Update docs and add migration guide
4. **User communication**: Add prominent notice in FCX mode report
5. **Rollback plan**: Git history allows easy revert if needed

---

## Success Criteria

### Functional Requirements
- ✅ No file write operations in FCX mode
- ✅ All detected issues appear in report with recommendations
- ✅ Report includes current vs. recommended values and file paths
- ✅ Detection logic unchanged (same issues detected)
- ✅ Both Python and Rust implementations updated
- ✅ CLI and GUI work correctly with new behavior

### Code Quality Requirements
- ✅ All tests pass (unit + integration + Rust)
- ✅ No deprecated warnings
- ✅ Type hints complete and correct
- ✅ Documentation updated and accurate
- ✅ No backward compatibility code
- ✅ Code follows project standards

### User Experience Requirements
- ✅ Clear, actionable recommendations in reports
- ✅ Consistent formatting across all issue types
- ✅ Severity levels help prioritize issues
- ✅ File paths are accurate and clickable (in supported viewers)
- ✅ Report is easy to understand and follow

---

## Timeline Estimate

| Phase | Estimated Time | Cumulative |
|-------|----------------|------------|
| Step 1: Data Model | 30 min | 30 min |
| Step 2: Detection Methods | 1-2 hours | 2.5 hours |
| Step 3: Report Generation | 1 hour | 3.5 hours |
| Step 4: Remove Write Ops | 2-3 hours | 6.5 hours |
| Step 5: Update Tests | 2-3 hours | 9.5 hours |
| Step 6: Rust Implementation | 2-3 hours | 12.5 hours |
| Step 7: Documentation | 1 hour | 13.5 hours |
| Step 8: Integration Testing | 1-2 hours | 15.5 hours |

**Total estimated time**: 13-16 hours of focused development

---

## Future Enhancements (Out of Scope)

### Potential Future Features
1. **Separate "Fix Mode" tool**: Standalone utility to apply recommended fixes
2. **Interactive fix application**: GUI/TUI to select which fixes to apply
3. **Backup and rollback**: Automatic backups before applying fixes
4. **Batch fix scripts**: Generate PowerShell/Bash scripts to apply fixes
5. **Configuration validation**: Pre-scan validation before game launch
6. **Custom fix rules**: User-defined issue detection and recommendations

### Why Not Included Now
- **Scope creep**: These are separate features, not core to read-only conversion
- **User feedback needed**: Should gather user input on desired fix application methods
- **API stability**: Current refactoring establishes clean separation for future work
- **Complexity**: Each feature deserves its own planning and implementation cycle

---

## References

### Code Locations
- **Python FCX Handler**: [ClassicLib/ScanLog/FCXModeHandler.py](../ClassicLib/ScanLog/FCXModeHandler.py)
- **Rust Wrapper**: [ClassicLib/rust/fcx_rust.py](../ClassicLib/rust/fcx_rust.py)
- **Config Cache**: [ClassicLib/ScanGame/Config.py](../ClassicLib/ScanGame/Config.py)
- **Mod INI Scanner**: [ClassicLib/ScanGame/ScanModInis.py](../ClassicLib/ScanGame/ScanModInis.py)
- **Rust Core**: [ClassicLib-rs/business-logic/classic-scanlog-core/src/fcx_handler.rs](../../ClassicLib-rs/business-logic/classic-scanlog-core/src/fcx_handler.rs)
- **Rust PyO3**: [ClassicLib-rs/python-bindings/classic-scanlog-py/src/fcx_handler.rs](../../ClassicLib-rs/python-bindings/classic-scanlog-py/src/fcx_handler.rs)

### Related Documentation
- [Async Development Guide](../development/async_development_guide.md)
- [Rust Workspace Architecture](../development/rust_workspace_architecture.md)
- [Testing Guide](../testing/test_pollution_guide.md)
- [PyO3 Integration Patterns](../development/pyo3_integration_patterns.md)

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-10-29 | Claude | Initial planning document created |

---

**End of FCX Mode Read-Only Conversion Plan**
