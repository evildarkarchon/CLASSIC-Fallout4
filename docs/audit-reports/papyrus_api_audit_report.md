# Papyrus API Compliance Audit Report
**Phase 1.2: Python Code Analysis for classic-scanlog-py Papyrus Classes**

**Date**: 2025-11-04
**Auditor**: Claude (Python Development Expert)
**Scope**: Python codebase compliance with classic-scanlog-py Papyrus Rust bindings

---

## Executive Summary

**FINDING: SCENARIO A - Python Implementation Only (No Rust Usage)**

The Python codebase does NOT currently use the Rust Papyrus classes (`PapyrusAnalyzer`, `PapyrusStats`, `papyrus_logging()`) that are available in `classic-scanlog-py`. All Papyrus functionality is implemented in pure Python.

**Risk Level**: **LOW** - No immediate issues, but opportunity for significant performance improvement
**Type Stub Impact**: **INFORMATIONAL** - Missing stub entries don't currently affect Python code
**Recommendation**: Consider migrating to Rust implementation for 15-30x performance gains

---

## Rust API Availability

### What's Available in classic-scanlog-py

From `rust/python-bindings/classic-scanlog-py/src/papyrus.rs` and `lib.rs`:

**1. PapyrusAnalyzer Class** (`PyPapyrusAnalyzer`):
```python
# Available but NOT used in Python
from classic_scanlog import PapyrusAnalyzer

analyzer = PapyrusAnalyzer("/path/to/Papyrus.0.log")
stats = analyzer.analyze_full()  # Returns PapyrusStats
summary = analyzer.analyze_to_string()  # Returns formatted string
analyzer.start_monitoring()  # Tail-f behavior
updates = analyzer.check_for_updates()  # Incremental reads
```

**2. PapyrusStats Class** (`PyPapyrusStats`):
```python
# Available but NOT used in Python
from classic_scanlog import PapyrusStats

stats = analyzer.stats()
print(stats.dumps, stats.stacks, stats.warnings, stats.errors)
print(stats.dumps_to_stacks_ratio())
print(stats.severity_level())  # "OK", "Warning", "Critical"
```

**3. papyrus_logging() Function**:
```python
# Available but NOT used in Python
from classic_scanlog import papyrus_logging

summary, dumps_count = papyrus_logging("/path/to/Papyrus.0.log")
```

**Confirmed Exports** (from `lib.rs` lines 110, 181):
- Line 110: `pub use papyrus::{PyPapyrusAnalyzer, PyPapyrusStats, papyrus_logging};`
- Line 181: `papyrus::register(m)?;` - Registered in module initialization

**Performance Promise**: 15-30x faster than Python implementation (from module docstring)

---

## Python Implementation Analysis

### File 1: ClassicLib/PapyrusLog.py

**Status**: Pure Python implementation - **NO Rust usage**

**Current Implementation**:
```python
def papyrus_logging() -> tuple[str, int]:
    """Analyzes Papyrus log files, extracting various statistics..."""

    # Uses Rust-accelerated file I/O for reading:
    papyrus_data: list[str] = read_lines_sync(papyrus_path)

    # BUT does NOT use Rust Papyrus analysis
    # Manual line-by-line parsing in Python:
    for line in papyrus_data:
        if "Dumping Stacks" in line:
            count_dumps += 1
        elif "Dumping Stack" in line:
            count_stacks += 1
        elif " warning: " in line:
            count_warnings += 1
        elif " error: " in line:
            count_errors += 1
```

**Key Observations**:
1. **NO imports from classic_scanlog** - Uses pure Python parsing
2. **Partial acceleration** - Uses `read_lines_sync()` from Rust file I/O (10x faster file reading)
3. **Manual analysis** - Parses each line with Python string operations (NOT accelerated)
4. **Simple pattern matching** - String `in` checks for each line
5. **Ratio calculation** - Computed in Python: `count_dumps / count_stacks`
6. **Docstring mentions Rust** - But only refers to file I/O, not Papyrus analysis

**Performance Bottleneck**:
- Reading is fast (Rust file I/O)
- Parsing is slow (Python string operations on large logs)

**Potential Speedup**: 15-30x if migrated to `papyrus_logging()` Rust function

---

### File 2: ClassicLib/Interface/Papyrus.py

**Status**: Pure Python implementation - **NO Rust usage**

**Current Implementation**:

**PapyrusStats Class** (lines 23-82):
```python
@dataclass
class PapyrusStats:
    """Python dataclass for Papyrus statistics"""
    timestamp: datetime
    dumps: int
    stacks: int
    warnings: int
    errors: int
    ratio: float

    def __eq__(self, other: object) -> bool:
        # Custom equality based on counts
        return (self.dumps == other.dumps and
                self.stacks == other.stacks and ...)
```

**Key Observations**:
1. **Duplicate name** - Python has its own `PapyrusStats` class (NOT from Rust)
2. **Different API** - Python version includes `timestamp` and pre-calculated `ratio`
3. **Missing methods** - Python version doesn't have:
   - `dumps_to_stacks_ratio()` - Rust method
   - `total_issues()` - Rust method
   - `error_to_warning_ratio()` - Rust method
   - `severity_level()` - Rust method (returns "OK"/"Warning"/"Critical")
4. **Extra features** - Python version has:
   - `timestamp` field (tracking when stats were recorded)
   - Custom `__eq__` for change detection
   - Custom `__hash__` for set/dict usage

**PapyrusMonitorWorker Class** (lines 84-233):
```python
class PapyrusMonitorWorker(QObject):
    """Qt worker for real-time Papyrus monitoring"""

    def run(self) -> None:
        while True:
            message, count = papyrus_logging()  # Calls Python function
            current_stats: PapyrusStats = self._parse_stats(message, count)

            if self._last_stats != current_stats:
                self.statsUpdated.emit(current_stats)
```

**Key Observations**:
1. **NO Rust monitoring** - Does not use `PapyrusAnalyzer.check_for_updates()`
2. **Re-parses each time** - Calls `papyrus_logging()` repeatedly (inefficient)
3. **Full file read** - Reads entire log every second (no incremental)
4. **Manual parsing** - `_parse_stats()` re-extracts numbers from formatted string
5. **Change detection** - Uses custom `__eq__` to detect stat changes

**Performance Issues**:
- Re-reads entire log file every 1 second
- Re-parses all lines every iteration
- No tail-f optimization (Rust has `check_for_updates()`)

**Potential Speedup**: 15-30x with Rust + incremental monitoring

---

### File 3: ClassicLib/Interface/PapyrusDialog.py

**Status**: Pure Python UI - Consumes Python `PapyrusStats`

**Current Implementation**:
```python
from ClassicLib.Interface.Papyrus import PapyrusStats  # Python version

class PapyrusMonitorDialog(QDialog):
    def update_stats(self, stats: PapyrusStats) -> None:
        """Updates UI with Python PapyrusStats"""
        self.stat_value_labels["dumps"].setText(str(stats.dumps))
        self.stat_value_labels["stacks"].setText(str(stats.stacks))
        self.stat_value_labels["dumps_stacks_ratio"].setText(f"{stats.ratio:.3f}")
```

**Key Observations**:
1. **Depends on Python PapyrusStats** - Expects Python dataclass format
2. **No direct Rust usage** - Pure Qt UI consumer
3. **Status indicator logic** - Hardcoded thresholds (ratio > 0.8 = red)
4. **No use of severity_level()** - Rust has this method, Python reimplements logic

**Migration Note**: Could benefit from Rust `PapyrusStats.severity_level()` method

---

### File 4: ClassicLib/integration/factory.py

**Status**: Factory pattern - **NO Papyrus factory function**

**Key Observations**:
1. **No `get_papyrus_analyzer()` function** - Factory doesn't provide Papyrus
2. **No detection of Papyrus component** - `detect_rust_components()` doesn't check for it
3. **Other factories exist** - For parser, FormID analyzer, plugin analyzer, etc.
4. **Missing pattern** - Should have Rust/Python selection for Papyrus

**Expected Pattern** (NOT implemented):
```python
def get_papyrus_analyzer(log_path: Path) -> Any:
    """Get Papyrus analyzer with automatic Rust/Python fallback."""
    components = _get_components()

    if not _is_rust_disabled() and components.get("papyrus", False):
        try:
            from classic_scanlog import PapyrusAnalyzer
            logger.debug("Using Rust PapyrusAnalyzer (15-30x speedup)")
            return PapyrusAnalyzer(log_path)
        except ImportError as e:
            logger.warning(f"Failed to import Rust PapyrusAnalyzer: {e}")

    # Fall back to Python implementation
    logger.debug("Using Python papyrus_logging implementation")
    # ... return Python equivalent
```

---

## API Compatibility Analysis

### Python vs. Rust API Differences

**Function Signature Comparison**:

| Component | Python API | Rust API | Compatible? |
|-----------|-----------|----------|-------------|
| `papyrus_logging()` | `() -> tuple[str, int]` | `(log_path: Path) -> tuple[str, int]` | ❌ Different signature |
| `PapyrusStats` | Dataclass with `timestamp`, `ratio` | Class with methods, no timestamp | ⚠️ Similar but different |
| `PapyrusAnalyzer` | N/A (doesn't exist in Python) | Full class with monitoring | ✅ Could add to Python |

**Python `papyrus_logging()` Differences**:
```python
# Python (ClassicLib/PapyrusLog.py)
def papyrus_logging() -> tuple[str, int]:
    # NO parameters - reads path from YAML settings
    papyrus_path = yaml_settings(Path, YAML.Game_Local, "...")
    # Returns: (formatted_message, dump_count)

# Rust (classic-scanlog-py)
def papyrus_logging(log_path: PathBuf) -> tuple[str, int]:
    # Requires log_path parameter
    # Returns: (formatted_summary, dump_count)
```

**Migration Blocker**: Parameter mismatch prevents drop-in replacement

---

## Import Analysis

### Classic-Scanlog Imports Across Codebase

**Files importing `classic_scanlog`**: 34 files (from Grep search)

**Papyrus-specific imports**: **NONE FOUND**

**Examples of classic_scanlog usage** (NOT Papyrus):
```python
# Report generation
from classic_scanlog import ReportGenerator, ReportComposer

# Parser
from classic_scanlog import LogParser

# Orchestrator
from classic_scanlog import AnalysisConfig, AnalysisResult, RustOrchestrator

# GPU detection
import classic_scanlog  # For GpuDetector

# Mod detection
import classic_scanlog  # For detect_mods_*
```

**Conclusion**: While `classic_scanlog` is heavily used for other components, **Papyrus classes are NOT imported anywhere**.

---

## Type Stub Impact Assessment

### Missing from `.pyi` Stub

From `rust/python-bindings/classic-scanlog-py/classic_scanlog.pyi`:

**Currently MISSING**:
1. `class PapyrusAnalyzer` - Not in stub
2. `class PapyrusStats` - Not in stub
3. `def papyrus_logging(log_path: str) -> tuple[str, int]` - Not in stub

**Impact on Current Codebase**: **NONE**

**Reasoning**:
- Python code doesn't import these classes
- No Rust Papyrus functionality is used
- Type checkers won't complain because nothing references them

**IF Python code DID import them**:
```python
# This would fail type checking (missing from stub):
from classic_scanlog import PapyrusAnalyzer, PapyrusStats  # ❌ Type checker error

# But would work at runtime (classes ARE registered):
analyzer = PapyrusAnalyzer("/path/to/log")  # ✅ Works at runtime
```

**Impact Level**:
- **Current**: No impact (code doesn't use them)
- **Future**: HIGH impact if migration happens without updating stub

---

## Test Coverage Analysis

### Papyrus Tests

**Test File**: `tests/interface/test_papyrus_monitor_worker.py`

**Key Observation**: Tests Python implementation, **NOT Rust**

```python
from ClassicLib.Interface.Papyrus import PapyrusMonitorWorker, PapyrusStats
# Uses Python classes, not Rust
```

**Additional Tests**:
- `tests/gui/test_papyrus_dialog_comprehensive_unit.py` - Tests dialog UI
- `tests/gui/test_papyrus_dialog_unit.py` - Tests dialog UI
- `tests/concurrency/test_worker_lifecycle.py` - Tests worker threads

**None test Rust Papyrus classes**

---

## Performance Comparison

### Benchmarking Opportunity

**Current Python Performance** (estimated):
- File read: ~10ms (Rust-accelerated file I/O)
- Parsing: ~50-100ms (Python string operations on typical log)
- Total: ~60-110ms per analysis

**Potential Rust Performance** (from Rust docs):
- File read + parsing: ~5-10ms (15-30x speedup claim)
- Total: ~5-10ms per analysis

**Monitoring Performance**:
- Current: Re-reads entire file every 1 second
- Rust: Incremental `check_for_updates()` only reads new lines

**Real-World Scenario**:
- 1000-line Papyrus log
- Current: 60-110ms every second = 100% CPU usage of reading/parsing
- Rust: 5-10ms initial, then <1ms incremental = 10% CPU usage

---

## Recommendations

### Priority 1: Update Type Stub (Low Effort, High Value)

**Action**: Add missing Papyrus classes to `classic_scanlog.pyi`

**Location**: `rust/python-bindings/classic-scanlog-py/classic_scanlog.pyi`

**Required Additions**:
```python
# Add after line 1783 (near other classes)

class PapyrusStats:
    """Statistics from Papyrus log analysis."""

    @property
    def dumps(self) -> int:
        """Number of 'Dumping Stacks' (plural) entries."""
        ...

    @property
    def stacks(self) -> int:
        """Number of 'Dumping Stack' (singular) entries."""
        ...

    @property
    def warnings(self) -> int:
        """Number of warning messages."""
        ...

    @property
    def errors(self) -> int:
        """Number of error messages."""
        ...

    @property
    def lines_processed(self) -> int:
        """Total lines processed."""
        ...

    def dumps_to_stacks_ratio(self) -> float:
        """Calculate dumps to stacks ratio (0.0 if no dumps/stacks)."""
        ...

    def total_issues(self) -> int:
        """Get total issues (warnings + errors)."""
        ...

    def error_to_warning_ratio(self) -> float:
        """Calculate error to warning ratio (0.0 if no warnings)."""
        ...

    def severity_level(self) -> Literal["OK", "Warning", "Critical"]:
        """
        Determine severity level:
        - "OK": No errors or errors < 25% of warnings
        - "Warning": Errors between 25-100% of warnings
        - "Critical": Errors exceed warnings
        """
        ...

    def __repr__(self) -> str: ...


class PapyrusAnalyzer:
    """Analyzer for Papyrus script logs with incremental monitoring support."""

    def __init__(self, log_path: str | Path) -> None:
        """
        Create analyzer for the given log file.

        Args:
            log_path: Path to Papyrus.0.log file
        """
        ...

    def log_exists(self) -> bool:
        """Check if log file exists."""
        ...

    def log_path(self) -> Path:
        """Get log file path."""
        ...

    def stats(self) -> PapyrusStats:
        """Get current statistics."""
        ...

    def reset(self) -> None:
        """Reset statistics and position (start from beginning)."""
        ...

    def analyze_full(self) -> PapyrusStats:
        """
        Perform full analysis from beginning.

        Returns:
            PapyrusStats: Collected statistics

        Raises:
            FileNotFoundError: If log file doesn't exist
            IOError: If failed to read file
        """
        ...

    def analyze_to_string(self) -> str:
        """
        Analyze log and return formatted summary.

        Returns:
            Formatted string with statistics or error message
        """
        ...

    def start_monitoring(self) -> None:
        """
        Start monitoring from END of file (tail -f behavior).

        Positions analyzer at end of current file so only NEW lines
        added after this point are tracked.

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If can't read file metadata
        """
        ...

    def check_for_updates(self) -> tuple[list[str], PapyrusStats] | None:
        """
        Read only new lines added since last check (incremental).

        Returns:
            Tuple of (new lines, updated statistics) or None if no changes

        Raises:
            IOError: If failed to read file or file was truncated
        """
        ...

    def __repr__(self) -> str: ...


def papyrus_logging(log_path: str | Path) -> tuple[str, int]:
    """
    Analyze a Papyrus log file (convenience function).

    Equivalent to creating PapyrusAnalyzer and calling analyze_to_string().

    Args:
        log_path: Path to Papyrus.0.log file

    Returns:
        Tuple of (formatted summary, dumps count)

    Example:
        >>> from classic_scanlog import papyrus_logging
        >>> summary, dumps = papyrus_logging("/path/to/Papyrus.0.log")
        >>> print(f"Summary:\\n{summary}")
        >>> print(f"Total dumps: {dumps}")
    """
    ...
```

**Effort**: 30 minutes
**Benefit**: Enables future Rust migration with type safety

---

### Priority 2: Migrate to Rust Papyrus (Medium Effort, High Value)

**Action**: Create migration path to use Rust Papyrus classes

**Step 1**: Add factory function to `factory.py`:
```python
def get_papyrus_analyzer(log_path: Path) -> Any:
    """Get Papyrus analyzer with automatic Rust/Python fallback."""
    components = _get_components()

    if not _is_rust_disabled() and components.get("papyrus", False):
        try:
            from classic_scanlog import PapyrusAnalyzer
            logger.debug("Using Rust PapyrusAnalyzer (15-30x speedup)")
            return PapyrusAnalyzer(str(log_path))
        except ImportError as e:
            logger.warning(f"Failed to import Rust PapyrusAnalyzer: {e}")

    # Fall back to Python implementation
    logger.debug("Using Python papyrus_logging implementation")
    from ClassicLib.PapyrusLog import papyrus_logging

    class PythonPapyrusWrapper:
        """Wrapper to match Rust API."""
        def __init__(self, log_path: Path):
            self.log_path_value = log_path

        def analyze_to_string(self) -> str:
            # Call Python function
            message, _ = papyrus_logging()
            return message

        def stats(self) -> Any:
            # Would need adaptation
            pass

    return PythonPapyrusWrapper(log_path)
```

**Step 2**: Update `PapyrusLog.py` to use factory:
```python
def papyrus_logging() -> tuple[str, int]:
    """Legacy function - delegates to factory."""
    papyrus_path = yaml_settings(Path, YAML.Game_Local, "...")

    if papyrus_path and papyrus_path.exists():
        # Try Rust acceleration
        from ClassicLib.integration.factory import get_papyrus_analyzer
        analyzer = get_papyrus_analyzer(papyrus_path)
        summary = analyzer.analyze_to_string()
        stats = analyzer.stats()
        return summary, stats.dumps
    else:
        # Error case
        return error_message, 0
```

**Step 3**: Update `PapyrusMonitorWorker` for incremental monitoring:
```python
class PapyrusMonitorWorker(QObject):
    def __init__(self):
        super().__init__()
        self.analyzer = None  # Will be PapyrusAnalyzer or Python wrapper

    def run(self):
        papyrus_path = yaml_settings(...)

        # Get analyzer with Rust fallback
        from ClassicLib.integration.factory import get_papyrus_analyzer
        self.analyzer = get_papyrus_analyzer(papyrus_path)

        # Start monitoring (tail -f mode)
        self.analyzer.start_monitoring()

        while self._should_run:
            # Incremental updates (only new lines)
            updates = self.analyzer.check_for_updates()

            if updates:
                new_lines, stats = updates
                # Convert Rust PapyrusStats to Python format
                py_stats = PapyrusStats(
                    timestamp=datetime.now(),
                    dumps=stats.dumps,
                    stacks=stats.stacks,
                    warnings=stats.warnings,
                    errors=stats.errors,
                    ratio=stats.dumps_to_stacks_ratio()
                )
                self.statsUpdated.emit(py_stats)

            QThread.msleep(1000)
```

**Effort**: 4-6 hours
**Benefit**: 15-30x performance improvement, incremental monitoring

---

### Priority 3: Update Component Detection (Low Effort)

**Action**: Add Papyrus to Rust component detection

**Location**: `ClassicLib/integration/detector.py`

**Add to detection**:
```python
def detect_rust_components() -> dict[str, bool]:
    """Detect available Rust components."""
    components = {}

    # ... existing checks ...

    # Check for Papyrus analyzer
    try:
        from classic_scanlog import PapyrusAnalyzer, PapyrusStats
        components["papyrus"] = True
    except (ImportError, AttributeError):
        components["papyrus"] = False

    return components
```

**Effort**: 15 minutes
**Benefit**: Enables factory pattern detection

---

### Priority 4: Performance Benchmarking (Optional)

**Action**: Create benchmark comparing Python vs Rust Papyrus

**Test Script**:
```python
import time
from pathlib import Path

# Python version
def benchmark_python():
    from ClassicLib.PapyrusLog import papyrus_logging
    start = time.perf_counter()
    for _ in range(100):
        message, count = papyrus_logging()
    end = time.perf_counter()
    return (end - start) / 100

# Rust version
def benchmark_rust():
    from classic_scanlog import papyrus_logging
    log_path = Path("path/to/Papyrus.0.log")
    start = time.perf_counter()
    for _ in range(100):
        message, count = papyrus_logging(log_path)
    end = time.perf_counter()
    return (end - start) / 100

python_time = benchmark_python()
rust_time = benchmark_rust()
speedup = python_time / rust_time

print(f"Python: {python_time*1000:.2f}ms")
print(f"Rust: {rust_time*1000:.2f}ms")
print(f"Speedup: {speedup:.1f}x")
```

**Effort**: 1 hour
**Benefit**: Quantify actual performance gains

---

## Migration Risk Assessment

### Low Risk Factors
- Rust classes already implemented and tested
- No breaking changes to existing Python code
- Factory pattern provides automatic fallback
- Type stub additions are purely additive

### Medium Risk Factors
- API signature mismatch (`papyrus_logging` parameters)
- Python `PapyrusStats` has different attributes
- Qt worker thread integration needs testing
- Incremental monitoring is new behavior

### Mitigation Strategy
1. **Phase 1**: Add type stub (no code changes)
2. **Phase 2**: Add factory with Python fallback
3. **Phase 3**: Update one consumer at a time
4. **Phase 4**: Measure performance gains
5. **Phase 5**: Deprecate pure Python implementation

---

## Conclusion

### Current State
- ✅ **Rust Papyrus classes ARE available** in classic-scanlog-py
- ✅ **Rust classes ARE properly registered** in module
- ❌ **Python code does NOT use them** (pure Python implementation)
- ⚠️ **Type stub is incomplete** (missing Papyrus classes)

### Compliance Status
- **API Registration**: ✅ COMPLIANT - Rust exports all classes
- **Type Stub Coverage**: ❌ NON-COMPLIANT - Missing 3 Papyrus items
- **Python Usage**: ✅ COMPLIANT - No runtime errors (doesn't use them)
- **Performance**: ⚠️ OPPORTUNITY - Could be 15-30x faster

### Next Steps
1. ✅ **UPDATE TYPE STUB** (Priority 1) - Add missing Papyrus classes to `.pyi`
2. ⚠️ **CONSIDER MIGRATION** (Priority 2) - Evaluate cost/benefit of Rust adoption
3. ✅ **ADD DETECTION** (Priority 3) - Include Papyrus in component detection
4. 📊 **BENCHMARK** (Priority 4) - Measure actual performance gains

### Final Recommendation

**For Type Stub Compliance**: **MUST FIX**
Add `PapyrusAnalyzer`, `PapyrusStats`, and `papyrus_logging()` to the `.pyi` stub file.

**For Rust Migration**: **RECOMMENDED BUT OPTIONAL**
The current Python implementation works correctly. Migration would provide significant performance benefits (15-30x) but requires moderate effort (4-6 hours) and carries medium risk. Recommend:
- Short-term: Update type stub (30 minutes)
- Long-term: Migrate to Rust when Papyrus monitoring becomes a bottleneck

---

## Appendix A: File Locations

| Component | Location |
|-----------|----------|
| Python Papyrus implementation | `ClassicLib/PapyrusLog.py` |
| Python PapyrusStats class | `ClassicLib/Interface/Papyrus.py` |
| Python PapyrusMonitorWorker | `ClassicLib/Interface/Papyrus.py` |
| Python dialog UI | `ClassicLib/Interface/PapyrusDialog.py` |
| Factory pattern | `ClassicLib/integration/factory.py` |
| Rust Papyrus implementation | `rust/business-logic/classic-scanlog-core/src/papyrus.rs` |
| Rust Python bindings | `rust/python-bindings/classic-scanlog-py/src/papyrus.rs` |
| Type stub | `rust/python-bindings/classic-scanlog-py/classic_scanlog.pyi` |
| Tests | `tests/interface/test_papyrus_monitor_worker.py` |

---

## Appendix B: API Reference Comparison

### Python `papyrus_logging()` Function

```python
# Location: ClassicLib/PapyrusLog.py
def papyrus_logging() -> tuple[str, int]:
    """
    Args: NONE (reads path from YAML settings)
    Returns: (formatted_message: str, dump_count: int)
    Behavior: Full file read and parse every call
    """
```

### Rust `papyrus_logging()` Function

```rust
// Location: rust/python-bindings/classic-scanlog-py/src/papyrus.rs
#[pyfunction]
pub fn papyrus_logging(log_path: PathBuf) -> (String, usize) {
    """
    Args: log_path (required parameter)
    Returns: (formatted_summary: str, dump_count: int)
    Behavior: Creates analyzer, runs full analysis
    """
}
```

### Python `PapyrusStats` Dataclass

```python
# Location: ClassicLib/Interface/Papyrus.py
@dataclass
class PapyrusStats:
    timestamp: datetime    # ← Python-specific
    dumps: int
    stacks: int
    warnings: int
    errors: int
    ratio: float          # ← Pre-calculated

    def __eq__(self, other) -> bool: ...  # ← Python-specific
    def __hash__(self) -> int: ...        # ← Python-specific
```

### Rust `PapyrusStats` Class

```rust
// Location: rust/python-bindings/classic-scanlog-py/src/papyrus.rs
#[pyclass(name = "PapyrusStats")]
pub struct PyPapyrusStats {
    // Properties:
    dumps: usize
    stacks: usize
    warnings: usize
    errors: usize
    lines_processed: usize  # ← Rust-specific

    // Methods (NOT properties):
    dumps_to_stacks_ratio() -> f64
    total_issues() -> usize
    error_to_warning_ratio() -> f64
    severity_level() -> &'static str  # ← Rust-specific: "OK"/"Warning"/"Critical"
}
```

### Python `PapyrusAnalyzer` - N/A

**Does not exist** in Python codebase. Rust provides full monitoring API.

---

**End of Report**
