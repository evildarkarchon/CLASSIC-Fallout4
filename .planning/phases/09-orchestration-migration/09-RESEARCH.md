# Phase 9: Orchestration Migration - Research

**Researched:** 2026-02-03
**Domain:** Rust OrchestratorCore wiring, batch parallelism, progress callbacks, cancellation support
**Confidence:** HIGH

## Summary

Phase 9 migrates all crash log scanning orchestration to Rust. The Rust `OrchestratorCore` in `classic-scanlog-core` is already 90-100% complete with full feature parity: single-log processing, batch parallelism, VR auto-detection, and all analyzers (Plugin, FormID, Suspect, Mod, Record, Settings) callable from Rust. The primary work is:

1. **Wiring** - Route all calls from Python through Rust orchestrator (not hybrid mode)
2. **Python Removal** - Delete `OrchestratorCore` from Python entirely (per CONTEXT.md: "Remove Python OrchestratorCore entirely")
3. **Progress Callbacks** - Implement per-log callbacks with (current, total, filename) data
4. **Cancellation Support** - Allow mid-batch abort via cancellation flag
5. **Order Preservation** - Buffer results to return in input order with placeholders for failures

The Rust implementation already uses `buffer_unordered` for parallelism (lines 1012-1024 of orchestrator.rs) and `futures::stream` for async processing. Progress and cancellation support will be added to the existing batch processing infrastructure.

**Primary recommendation:** Remove Python `OrchestratorCore`, update `HybridOrchestrator` to delegate directly to Rust, implement progress callback via `PyObject.call1()` pattern, and use `AtomicBool` for cancellation (simpler than `CancellationToken` for the between-logs check pattern).

## Standard Stack

### Core (Already Present)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `classic-scanlog-core` | N/A | Rust business logic: OrchestratorCore, all analyzers | Complete implementation exists |
| `classic-scanlog-py` | N/A | PyO3 bindings: Orchestrator, AnalysisConfig, AnalysisResult | Full API exposed |
| `tokio` | 1.x | Async runtime for batch processing | ONE RUNTIME RULE |
| `futures` | 0.3.x | Stream processing with `buffer_unordered` | Already used for parallelism |
| `rayon` | 1.x | CPU-bound parallel processing | Used by analyzers |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `std::sync::atomic::AtomicBool` | std | Cancellation flag | Simple between-log cancellation |
| `pyo3::types::PyAny` | 0.27 | Accept Python callback functions | Progress reporting |
| `IndexMap` | 2.x | Order-preserving result collection | Maintain input order |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| AtomicBool for cancellation | tokio_util::CancellationToken | CancellationToken is for within-task cancellation at await points; AtomicBool is simpler for between-log checks |
| IndexMap for ordering | Vec with indices | IndexMap handles sparse indices better for failed logs |

**Installation:**
No new dependencies required - all libraries already in project.

## Architecture Patterns

### Current State

```
CLASSIC_ScanLogs.py / CLASSIC_Interface.py
    |
    v
HybridOrchestrator (ClassicLib/scanning/logs/hybrid_orchestrator.py)
    |
    +-- process_crash_log() ------> Python OrchestratorCore (if Rust not feature-complete)
    |                                    |
    +-- process_crash_logs_batch() --> Rust Orchestrator (if batch > 5 logs)
```

### Target State (Per CONTEXT.md)

```
CLASSIC_ScanLogs.py / CLASSIC_Interface.py
    |
    v
Rust Orchestrator (import classic_scanlog.Orchestrator directly)
    |
    +-- process_log(log_path) -> AnalysisResult
    |
    +-- process_logs_batch(
    |       log_paths,
    |       max_concurrent,
    |       progress_callback,    # NEW: Py<PyAny>
    |       cancellation_flag     # NEW: Arc<AtomicBool>
    |   ) -> Vec<AnalysisResult>
```

### Pattern 1: Rust-Only with Hard Fail

**What:** RuntimeError if Rust unavailable, no Python fallback
**When to use:** Per CONTEXT.md decision - consistent with Phase 7-8
**Example:**
```python
# Source: CONTEXT.md fallback behavior decision
try:
    from classic_scanlog import Orchestrator, AnalysisConfig
except ImportError as e:
    raise RuntimeError("Rust orchestrator module not available") from e

# Create orchestrator
config = AnalysisConfig.from_yamldata(yamldata)
orchestrator = Orchestrator(config)

# Process logs - no try/except fallback
results = orchestrator.process_logs_batch(log_paths)
```

### Pattern 2: Progress Callback via PyObject

**What:** Python passes callback to Rust, Rust calls it per-log
**When to use:** Per CONTEXT.md - per-log granularity with (current, total, filename)
**Example:**
```rust
// Source: PyO3 documentation + CONTEXT.md callback decision
use pyo3::prelude::*;

#[pymethods]
impl PyRustOrchestrator {
    #[pyo3(signature = (log_paths, max_concurrent = None, progress_callback = None))]
    pub fn process_logs_batch(
        &self,
        py: Python<'_>,
        log_paths: Vec<String>,
        max_concurrent: Option<usize>,
        progress_callback: Option<PyObject>,
    ) -> PyResult<Vec<PyAnalysisResult>> {
        let total = log_paths.len();

        // Release GIL during processing
        let results = without_gil(py, || {
            get_runtime().block_on(async {
                self.inner.process_logs_batch_with_callback(
                    log_paths,
                    max_concurrent,
                    |current, filename| {
                        // Callback invocation (requires GIL)
                        if let Some(ref cb) = progress_callback {
                            Python::attach(|py| {
                                let _ = cb.call1(py, (current, total, filename));
                            });
                        }
                    }
                ).await
            })
        });

        Ok(results.into_iter().map(|r| PyAnalysisResult { inner: r }).collect())
    }
}
```

### Pattern 3: Cancellation via AtomicBool

**What:** Check cancellation flag between logs, abort batch if set
**When to use:** Per CONTEXT.md - cancellation checked between logs
**Example:**
```rust
// Source: CONTEXT.md cancellation decision + Tokio patterns
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

pub async fn process_logs_batch_with_cancellation(
    &self,
    log_paths: Vec<String>,
    cancellation: Arc<AtomicBool>,
    progress_callback: impl Fn(usize, &str),
) -> Vec<AnalysisResult> {
    let total = log_paths.len();
    let mut results = Vec::with_capacity(total);

    for (index, log_path) in log_paths.iter().enumerate() {
        // Check cancellation between logs
        if cancellation.load(Ordering::Relaxed) {
            // Add placeholder for remaining logs
            for remaining_path in &log_paths[index..] {
                results.push(AnalysisResult::failure(
                    remaining_path.clone(),
                    "Cancelled by user".to_string(),
                ));
            }
            break;
        }

        // Process this log
        let result = self.process_log(log_path.clone()).await;

        // Report progress
        progress_callback(index + 1, log_path);

        results.push(result.unwrap_or_else(|e| {
            AnalysisResult::failure(log_path.clone(), e.to_string())
        }));
    }

    results
}
```

### Pattern 4: Order-Preserving Parallel Processing

**What:** Process in parallel but return results in input order
**When to use:** Per CONTEXT.md - preserve input order with placeholders
**Example:**
```rust
// Source: CONTEXT.md batch result ordering decision
use futures::stream::{self, StreamExt};
use std::collections::HashMap;

pub async fn process_logs_batch_ordered(
    &self,
    log_paths: Vec<String>,
    max_concurrent: Option<usize>,
) -> Vec<AnalysisResult> {
    let concurrency = max_concurrent.unwrap_or_else(|| num_cpus::get());

    // Process with index tracking
    let indexed_results: HashMap<usize, AnalysisResult> = stream::iter(
        log_paths.iter().enumerate()
    )
    .map(|(index, log_path)| async move {
        let result = self.process_log(log_path.clone()).await
            .unwrap_or_else(|e| AnalysisResult::failure(log_path.clone(), e.to_string()));
        (index, result)
    })
    .buffer_unordered(concurrency)
    .collect()
    .await;

    // Reconstruct in input order
    (0..log_paths.len())
        .map(|i| indexed_results.get(&i).cloned().unwrap_or_else(|| {
            AnalysisResult::failure(log_paths[i].clone(), "Processing failed".to_string())
        }))
        .collect()
}
```

### Anti-Patterns to Avoid

- **Python fallback:** Don't implement Python OrchestratorCore fallback - CONTEXT.md specifies Rust-only
- **Hybrid mode retention:** Don't keep HybridOrchestrator choosing between Python/Rust - remove Python path entirely
- **CancellationToken for between-logs:** CancellationToken is for cancelling at await points; AtomicBool is simpler for polling between logs
- **Unordered results:** Don't use `buffer_unordered` without index tracking if order matters
- **Blocking GIL during batch:** Always release GIL with `without_gil()` during Rust processing

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Callback invocation from Rust | Custom FFI | `PyObject.call1(py, args)` | PyO3 provides safe, idiomatic API |
| Cancellation signaling | Channel-based signaling | `AtomicBool` | Simpler for polling pattern |
| Order preservation | Manual Vec reordering | `IndexMap` or index-tracking HashMap | Handles sparse indices correctly |
| Parallel with backpressure | Manual semaphore | `buffer_unordered(concurrency)` | futures::stream handles this |
| Error log file writing | Custom file I/O | `FileIOCore` from classic-file-io | Already exists, async, handles encoding |

**Key insight:** The Rust orchestrator already has 90% of the infrastructure. Adding progress/cancellation is incremental enhancement, not reimplementation.

## Common Pitfalls

### Pitfall 1: GIL Deadlock on Callback

**What goes wrong:** Rust tries to acquire GIL while GIL is held by Python caller
**Why it happens:** Callback invocation requires GIL, but GIL was released for batch processing
**How to avoid:** Use `Python::attach()` to properly reacquire GIL for callback, not `Python::with_gil()`
**Warning signs:** Deadlock or "cannot access Python GIL" errors

### Pitfall 2: Progress Callback Overhead

**What goes wrong:** Calling Python callback per-log adds significant overhead
**Why it happens:** GIL acquisition/release for every callback
**How to avoid:** Per CONTEXT.md - coarse granularity (per-log, not per-analyzer) is correct; batch callbacks if needed
**Warning signs:** Batch processing slower than single-log processing

### Pitfall 3: Cancellation Not Checked

**What goes wrong:** Long-running batch continues after user requests cancel
**Why it happens:** Cancellation flag only checked at batch level, not between logs
**How to avoid:** Check `AtomicBool` at start of each log's processing loop
**Warning signs:** UI remains blocked after cancel button clicked

### Pitfall 4: Lost Results on Failure

**What goes wrong:** Results Vec has fewer entries than input paths
**Why it happens:** Errors filtered out instead of replaced with placeholders
**How to avoid:** Per CONTEXT.md - use placeholder entries for failed logs
**Warning signs:** Results count doesn't match input count

### Pitfall 5: Order Mismatch with buffer_unordered

**What goes wrong:** Results returned in completion order, not input order
**Why it happens:** `buffer_unordered` returns results as they complete
**How to avoid:** Track indices and reorder, or use ordered stream processing
**Warning signs:** First result is from last log (longest processing time)

### Pitfall 6: Error Log Location Confusion

**What goes wrong:** Error log written to wrong location or not found
**Why it happens:** Unclear where error log should be written
**How to avoid:** Per Claude's Discretion - recommend `{CLASSIC_folder}/classic_errors.log`
**Warning signs:** Users can't find error details

## Code Examples

### Existing Rust Orchestrator API (Working)

```rust
// Source: j:\CLASSIC-Fallout4\rust\business-logic\classic-scanlog-core\src\orchestrator.rs
impl OrchestratorCore {
    pub fn new(config: AnalysisConfig) -> Result<Self>;

    pub async fn process_log(&self, log_path: String) -> Result<AnalysisResult>;

    pub async fn process_logs_batch(
        &self,
        log_paths: Vec<String>,
        max_concurrent: Option<usize>,
    ) -> Vec<AnalysisResult>;

    pub fn is_feature_complete(&self) -> bool;
}
```

### Current PyO3 Bindings (To Be Extended)

```python
# Source: j:\CLASSIC-Fallout4\rust\python-bindings\classic-scanlog-py\classic_scanlog.pyi
class Orchestrator:
    def __init__(self, config: AnalysisConfig) -> None: ...
    def process_log(self, log_path: str) -> AnalysisResult: ...
    def process_logs_batch(
        self,
        log_paths: list[str],
        max_concurrent: int | None = None,
    ) -> list[AnalysisResult]: ...
    def is_feature_complete(self) -> bool: ...
```

### Target Extended API (Phase 9)

```python
# Target: Extended classic_scanlog.pyi after Phase 9
from collections.abc import Callable

class Orchestrator:
    def __init__(self, config: AnalysisConfig) -> None: ...

    def process_log(self, log_path: str) -> AnalysisResult: ...

    def process_logs_batch(
        self,
        log_paths: list[str],
        max_concurrent: int | None = None,
        progress_callback: Callable[[int, int, str], None] | None = None,
        cancellation_flag: object | None = None,  # Python object with is_cancelled() method
    ) -> list[AnalysisResult]: ...

    def is_feature_complete(self) -> bool: ...

    @staticmethod
    def create_cancellation_token() -> CancellationToken: ...

class CancellationToken:
    """Token for cancelling batch operations."""
    def cancel(self) -> None: ...
    def is_cancelled(self) -> bool: ...
```

### Progress Callback Data Structure

```python
# Source: CONTEXT.md callback data decision
# Callback signature: (current: int, total: int, filename: str) -> None

def progress_callback(current: int, total: int, filename: str) -> None:
    """Called when each log completes processing.

    Args:
        current: Number of logs processed so far (1-indexed)
        total: Total number of logs in batch
        filename: Name of the log file just processed
    """
    print(f"Processing {current}/{total}: {filename}")
```

### Error Log File Pattern

```python
# Source: Claude's Discretion per CONTEXT.md
# Recommended location: CLASSIC_folder/classic_errors.log

from pathlib import Path
from datetime import datetime

def write_error_log(errors: list[tuple[str, str]], output_dir: Path) -> Path:
    """Write accumulated errors to error log file.

    Args:
        errors: List of (log_path, error_message) tuples
        output_dir: Directory to write error log

    Returns:
        Path to written error log file
    """
    error_log_path = output_dir / "classic_errors.log"

    with error_log_path.open("a", encoding="utf-8") as f:
        f.write(f"\n=== Scan Session {datetime.now().isoformat()} ===\n")
        for log_path, error in errors:
            f.write(f"\nLog: {log_path}\n")
            f.write(f"Error: {error}\n")

    return error_log_path
```

### VR Auto-Detection Per-Log

```rust
// Source: j:\CLASSIC-Fallout4\rust\business-logic\classic-scanlog-core\src\orchestrator.rs
// VR detection already exists in process_log() via detect_vr_log()

pub async fn process_log(&self, log_path: String) -> Result<AnalysisResult> {
    // Read log file
    let content = self.file_io.read_file(Path::new(&log_path)).await?;

    // Detect VR mode for THIS SPECIFIC LOG
    let is_vr_log = self.parser.detect_vr_log(&content);

    // Use VR-appropriate configuration
    let effective_config = if is_vr_log {
        self.config.with_vr_settings()
    } else {
        self.config.clone()
    };

    // Continue processing with effective config...
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| HybridOrchestrator chooses Python/Rust | Rust-only, no Python fallback | Phase 9 | Simpler code, faster execution |
| Python batch_size=10 limit | Rust unbounded default | Phase 9 | Full parallelism utilization |
| No progress callbacks | Per-log callbacks | Phase 9 | Responsive UI during batch |
| No cancellation support | AtomicBool between logs | Phase 9 | User can abort long batches |
| Unordered results | Input order with placeholders | Phase 9 | Predictable output mapping |

**Deprecated/outdated:**
- `ClassicLib/scanning/logs/orchestrator_core.py` - Entire file removed
- `HybridOrchestrator._python_orch` - No Python orchestrator reference
- `HybridOrchestrator.process_crash_log()` with Python fallback - Removed
- `OrchestratorCore.process_crash_logs_batch()` with batch_size=10 - Replaced by unbounded Rust

## VR Auto-Detection Scope

Based on codebase analysis, VR detection for Phase 9:

### Already Implemented in Rust
1. `LogParser.detect_vr_log()` - Detects VR from log content
2. `OrchestratorCore` - Uses VR-aware config accessors

### Python Changes for Phase 9
1. **Remove** - `is_vr_log` parameter passing in orchestrator_core.py
2. **Remove** - `is_vr_log` argument to `_process_log_sections_async()`
3. **Keep** - VR detection for version registry (internal use, not display)

## Error Handling Scope

Per CONTEXT.md decisions:

### Continue on Failure
- Skip failed logs, continue with others
- Use placeholder entries in results

### Tiered Verbosity
- Brief by default: "Failed to process: {filename}"
- Verbose/debug: Full stack trace, line numbers

### Isolated Analyzer Failures
- Each analyzer runs independently
- One failing doesn't affect others on same log

### Separate Error Log
- Accumulated errors written to `classic_errors.log`
- Not inline in results, not in summary section

## Open Questions

1. **Error Log File Format**
   - What we know: Separate file, not inline in results
   - What's unclear: Exact format (plain text vs markdown vs JSON)
   - Recommendation: Plain text with timestamps, one error per block

2. **CancellationToken Python Wrapper**
   - What we know: AtomicBool in Rust, exposed to Python
   - What's unclear: Should Python receive a wrapper class or raw object?
   - Recommendation: Wrapper class with `cancel()` and `is_cancelled()` methods

3. **Progress Callback Thread Safety**
   - What we know: Callback needs GIL, processing releases GIL
   - What's unclear: Exact attach/detach pattern for callbacks
   - Recommendation: Use `Python::attach()` per PyO3 docs for thread-spawned callbacks

## Sources

### Primary (HIGH confidence)

- `j:\CLASSIC-Fallout4\rust\business-logic\classic-scanlog-core\src\orchestrator.rs` - Full Rust implementation
- `j:\CLASSIC-Fallout4\rust\python-bindings\classic-scanlog-py\src\orchestrator.rs` - PyO3 bindings
- `j:\CLASSIC-Fallout4\rust\python-bindings\classic-scanlog-py\classic_scanlog.pyi` - Type stubs
- `j:\CLASSIC-Fallout4\ClassicLib\scanning\logs\orchestrator_core.py` - Python implementation to remove
- `j:\CLASSIC-Fallout4\ClassicLib\scanning\logs\hybrid_orchestrator.py` - Hybrid wrapper to simplify
- `j:\CLASSIC-Fallout4\.planning\phases\09-orchestration-migration\09-CONTEXT.md` - User decisions
- [PyO3 GitHub Issue #120](https://github.com/PyO3/pyo3/issues/120) - Python callback pattern

### Secondary (MEDIUM confidence)

- [Tokio CancellationToken docs](https://docs.rs/tokio-util/latest/tokio_util/sync/struct.CancellationToken.html) - Cancellation patterns
- [Tokio Graceful Shutdown](https://tokio.rs/tokio/topics/shutdown) - Shutdown patterns
- `j:\CLASSIC-Fallout4\.planning\phases\07-game-detection\07-RESEARCH.md` - Rust-only pattern
- `j:\CLASSIC-Fallout4\.planning\phases\08-report-generation\08-RESEARCH.md` - Hard fail pattern

### Tertiary (LOW confidence)

- [RustConf 2025 Cancellation Talk](https://github.com/sunshowers/cancelling-async-rust) - Cancellation patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already present and tested in codebase
- Architecture: HIGH - Patterns derived from existing Rust code and CONTEXT.md decisions
- Pitfalls: HIGH - Based on PyO3/Tokio documentation and project memories

**Research date:** 2026-02-03
**Valid until:** 30 days (stable codebase, internal migration)
