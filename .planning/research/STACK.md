# Technology Stack for Rust Migration

**Project:** CLASSIC Rust Migration - Scanning Orchestration, Game Detection, Report Generation, Settings Management
**Researched:** 2026-02-02
**Confidence:** HIGH - Based on existing crate analysis and verified external sources

## Executive Summary

The CLASSIC project already has a mature Rust infrastructure with PyO3 0.27, Tokio 1.49, and 25+ crates. The migration targets require **no new external crates** for core functionality. The existing stack covers all requirements:

- **Scanning orchestration**: Tokio async runtime (already in place)
- **Game detection**: classic-path-core + winreg (already in place)
- **Report generation**: classic-message-core patterns (already in place)
- **Settings management**: classic-settings-core with yaml-rust2 (already in place)

## Recommended Stack Additions

### DO NOT ADD - Unnecessary Dependencies

| Crate | Why NOT to add |
|-------|----------------|
| `markdown-gen` | Report generation is simple string concatenation; existing `classic-message-core` patterns suffice. Adding a dependency for basic markdown is overengineering. |
| `steamlocate` | CLASSIC targets modded game directories, not Steam detection. Users provide paths via settings; Windows registry detection for game paths is already in `classic-path-core` via `winreg`. |
| `handlebars` / `tera` | Template engines add complexity for simple report format; fragment-based composition already works well. |
| `tokio-util` | Existing `tokio 1.49` with full features provides sufficient orchestration primitives. |

### Already Available - Use Existing Crates

| Migration Target | Existing Crate | What's Available |
|-----------------|----------------|------------------|
| Scanning Orchestration | `classic-shared-core` | Global Tokio runtime, `get_runtime()` for ONE RUNTIME rule |
| Scanning Orchestration | `tokio` | `tokio::join!`, `tokio::select!`, `TaskGroup` patterns |
| Scanning Orchestration | `rayon` | CPU-bound parallel processing |
| Game Detection | `classic-path-core` | Path validation, INI parsing, directory scanning |
| Game Detection | `classic-xse-core` | XSE version detection, loader finding |
| Game Detection | `classic-scangame-core` | TOML config validation, integrity checking |
| Game Detection | `winreg 0.52` (Windows) | Registry access for game paths |
| Report Generation | `classic-message-core` | Message routing, emoji stripping, formatting |
| Report Generation | `string_cache` / `lasso` | String interning for report fragments |
| Report Generation | `smartstring` | Efficient small string handling |
| Settings Management | `classic-settings-core` | YAML settings cache with sync/async API |
| Settings Management | `yaml-rust2 0.11` | YAML parsing (already 15-30x faster than Python) |
| Settings Management | `dashmap 6.1` | Lock-free concurrent cache |

## Per-Migration-Target Analysis

### 1. Scanning Orchestration (OrchestratorCore Replacement)

**Current Python Implementation:** `ClassicLib/scanning/logs/orchestrator_core.py`
- 898 lines of async Python orchestrating crash log processing
- Uses async context managers, asyncio.TaskGroup, concurrent batch processing
- Coordinates: plugin analysis, suspect scanning, mod detection, FormID analysis, report generation

**Rust Implementation Strategy:**

```rust
// Use existing crates - NO new dependencies needed
use classic_shared_core::get_runtime;     // ONE RUNTIME rule
use tokio::{self, task::JoinSet};         // Already in workspace
use rayon::prelude::*;                     // CPU-bound parallelism
use classic_scanlog_core::*;               // Existing parsing logic
use classic_database_core::*;              // FormID database access
```

**Key Patterns to Follow:**
- Pipeline pattern with channels for streaming crash logs
- `tokio::join!` preserves ordering (documented in `05-memories.md`)
- Use `rayon` for CPU-bound fragment composition
- Expose via `classic-orchestrator-py` with PyO3 0.27

**Estimated Stack Footprint:** 0 new dependencies (all from workspace)

### 2. Game Detection (Path Detection, XSE/ENB Checking)

**Current Python Implementation:** `ClassicLib/scanning/game/` package
- `core.py`, `orchestrator.py`, `check_xse_plugins.py`, `check_crashgen.py`
- Uses Windows registry for Steam/GOG paths
- Validates XSE installation, checks ENB presence

**Existing Rust Coverage:**

| Component | Crate | Status |
|-----------|-------|--------|
| XSE detection | `classic-xse-core` | COMPLETE - `detect_xse_version()`, `is_xse_installed()` |
| Path validation | `classic-path-core` | COMPLETE - `PathValidator`, `GamePathLocator` |
| Registry access | `winreg 0.52` | COMPLETE - Already in workspace |
| TOML config | `classic-scangame-core` | COMPLETE - `CrashgenChecker`, `TomlConfigIssue` |
| INI validation | `classic-scangame-core` | COMPLETE - `IniValidator`, `ConfigIssue` |
| BA2 scanning | `classic-scangame-core` | COMPLETE - `BA2Scanner` |

**What Remains:**
- Orchestration layer connecting these components (new `GameIntegrityOrchestrator` in Rust)
- Python bindings via `classic-scangame-py` (partially exists)

**Estimated Stack Footprint:** 0 new dependencies

### 3. Report Generation (Markdown Output)

**Current Python Implementation:**
- `ClassicLib/scanning/logs/report_generator.py`
- `ClassicLib/scanning/logs/reporting/` package (fragment_composer, section_composer, etc.)
- Uses `ReportFragment` immutable objects with functional composition

**Existing Rust Coverage:**

| Component | Crate | Status |
|-----------|-------|--------|
| Message types | `classic-message-core` | COMPLETE - `Message`, `MessageType`, `MessageTarget` |
| Emoji stripping | `classic-message-core` | COMPLETE - `strip_emoji()`, `format_log_message()` |
| String interning | `lasso 0.7` | COMPLETE - `ThreadedRodeo` for concurrent interning |
| String optimization | `smartstring 1.0` | COMPLETE - Small string optimization |

**Report Fragment Implementation:**

The Python `ReportFragment` pattern translates directly to Rust:

```rust
// No new crates needed - use standard library + existing workspace deps
use smartstring::alias::String as SmartString;
use lasso::ThreadedRodeo;

pub struct ReportFragment {
    lines: Vec<SmartString>,
    interned_pool: Arc<ThreadedRodeo>,
}

impl ReportFragment {
    pub fn from_lines(lines: impl IntoIterator<Item = impl AsRef<str>>) -> Self { ... }
    pub fn compose(fragments: &[Self]) -> Self { ... }
    pub fn to_markdown(&self) -> String { ... }
}
```

**Why NOT markdown-gen:**
- `markdown-gen` (v1.2.1, last updated 2020) is designed for document generation with complex nesting
- CLASSIC reports are simple: headers, bullet lists, horizontal rules
- String concatenation with proper formatting is trivial and faster
- No runtime dependencies vs adding 2+ transitive deps

**Estimated Stack Footprint:** 0 new dependencies

### 4. Settings Management (Configuration Loading/Saving)

**Current Python Implementation:**
- `ClassicLib/io/yaml/` package with async cache
- `ClassicLib/classic_settings.py` for user preferences
- Uses ruamel.yaml (replaced by yaml-rust2 in Rust)

**Existing Rust Coverage:**

| Component | Crate | Status |
|-----------|-------|--------|
| YAML parsing | `yaml-rust2 0.11` | COMPLETE - 15-30x faster than ruamel.yaml |
| Settings cache | `classic-settings-core` | COMPLETE - `load_settings_sync/async`, `get_cached` |
| Batch loading | `classic-settings-core` | COMPLETE - `load_batch_async` |
| Concurrent access | `dashmap 6.1` | COMPLETE - Lock-free cache storage |

**What Remains:**
- Higher-level `ClassicSettings` abstraction for user preferences
- Python bindings completion in `classic-settings-py`

**Estimated Stack Footprint:** 0 new dependencies

## Version Verification

All versions verified against workspace `Cargo.toml`:

| Crate | Workspace Version | Current as of 2026-02-02 |
|-------|-------------------|-------------------------|
| PyO3 | 0.27.2 | Current (0.28 available but breaking) |
| pyo3-async-runtimes | 0.27.0 | Current for PyO3 0.27 |
| tokio | 1.49.0 | Current stable |
| yaml-rust2 | 0.11.0 | Current stable |
| winreg | 0.52 | Current stable |
| dashmap | 6.1 | Current stable |
| lasso | 0.7 | Current stable |
| smartstring | 1.0 | Current stable |
| rayon | 1.10 | Current stable |

## Integration Points with Existing Stack

### classic-shared-core (Foundation)

```rust
// All orchestration uses the global runtime
use classic_shared_core::get_runtime;

// Example: Run async orchestration from Python
pub fn run_orchestration(config: ScanConfig) -> PyResult<ScanResult> {
    get_runtime().block_on(async {
        orchestrate_scan(config).await
    })
}
```

### classic-scanlog-core (Business Logic)

```rust
// Existing parsing already handles crash log analysis
use classic_scanlog_core::{LogParser, find_segments};

// Orchestrator coordinates multiple parser instances
async fn process_batch(logs: Vec<PathBuf>) -> Vec<ScanResult> {
    let parser = LogParser::new(crashgen_name, xse_acronym, root_name);

    // Use tokio::join! for ordered parallel processing
    let results = logs.iter()
        .map(|log| process_single(parser.clone(), log))
        .collect::<Vec<_>>();

    futures::future::join_all(results).await
}
```

### classic-scangame-core (Game Scanning)

```rust
// Existing integrity checks can be orchestrated
use classic_scangame_core::{
    GameIntegrityChecker,
    BA2Scanner,
    IniValidator,
    CrashgenChecker,
};

async fn check_game_integrity(game_path: &Path) -> IntegrityResult {
    let checker = GameIntegrityChecker::new(game_path);

    // Run all checks concurrently
    tokio::join!(
        checker.check_xse(),
        checker.check_crashgen(),
        checker.check_ini_files(),
        checker.check_ba2_archives(),
    )
}
```

## New Crates to Create (Not New Dependencies)

These are NEW CRATES within the workspace, not new external dependencies:

| New Crate | Purpose | Dependencies (all from workspace) |
|-----------|---------|----------------------------------|
| `classic-orchestrator-core` | Rust orchestration business logic | classic-shared-core, classic-scanlog-core, tokio, rayon |
| `classic-orchestrator-py` | PyO3 bindings for orchestrator | pyo3, classic-orchestrator-core |
| `classic-report-core` | Report fragment generation | classic-message-core, lasso, smartstring |
| `classic-report-py` | PyO3 bindings for reports | pyo3, classic-report-core |

## Anti-Recommendations

### Do NOT Upgrade PyO3 to 0.28

**Reason:** PyO3 0.28.0 is available but introduces breaking changes. The project uses `abi3-py312` for stable ABI compatibility. Upgrading would require:
- Updating all `-py` crates (18+ crates)
- Testing GIL handling changes
- Potential runtime conflicts with `pyo3-async-runtimes`

**Recommendation:** Stay on PyO3 0.27.2 until a dedicated upgrade milestone.

### Do NOT Add steamlocate

**Reason:** CLASSIC's workflow is:
1. User runs CLASSIC in their modded game directory
2. Or user explicitly configures game path in settings
3. CLASSIC validates the path

The `steamlocate` crate is for:
- Finding ALL Steam games on a system
- Auto-detecting game installations

CLASSIC doesn't need auto-detection; it needs path VALIDATION (already in `classic-path-core`).

### Do NOT Add Template Engines

**Reason:** Report output is:
```markdown
# crash-2024-01-15.log
**AUTOSCAN REPORT GENERATED BY CLASSIC v8.2.0**

### Error Information
**Main Error:** Access violation at 0x00000000
...
```

This is trivially generated with `format!()` and string concatenation. Template engines add:
- Compilation overhead
- Runtime template parsing
- Template file management
- Error handling complexity

None of these provide value for static-format reports.

## Summary

**Total new external dependencies required: 0**

The existing CLASSIC Rust infrastructure provides all necessary capabilities:
- Async runtime: `tokio` via `classic-shared-core`
- Parallel processing: `rayon`
- YAML settings: `yaml-rust2` via `classic-settings-core`
- Game detection: `winreg` + `classic-path-core` + `classic-xse-core`
- Report generation: `classic-message-core` + string interning crates
- Database: `rusqlite`/`sqlx` via `classic-database-core`

The migration is about **creating new crates within the workspace** to house orchestration logic, not about adding new external dependencies.

## Sources

- [PyO3 async-await ecosystem documentation](https://github.com/PyO3/pyo3/blob/main/guide/src/ecosystem/async-await.md)
- [pyo3-async-runtimes for PyO3 0.27+ compatibility](https://github.com/PyO3/pyo3-async-runtimes)
- [markdown-gen crate (v1.2.1, last updated 2020)](https://lib.rs/crates/markdown-gen)
- [steamlocate crate (v2.0.1)](https://lib.rs/crates/steamlocate)
- [Tokio structured concurrency patterns](https://medium.com/@adamszpilewicz/structured-concurrency-in-rust-with-tokio-beyond-tokio-spawn-78eefd1febb4)
- [Worker pool patterns in Rust](https://medium.com/@adamszpilewicz/building-a-worker-pool-in-rust-scalable-task-execution-with-tokio-abcb4f193a05)
- [Rust concurrency patterns (OneSignal)](https://onesignal.com/blog/rust-concurrency-patterns/)
- CLASSIC workspace `rust/Cargo.toml` (authoritative source for current versions)
- CLASSIC existing crates: `classic-settings-core`, `classic-scangame-core`, `classic-xse-core`, `classic-message-core`
