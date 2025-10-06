# CLASSIC Rust Full Backend Migration Plan

**Goal**: Expand classic_core to handle complete crash log analysis, dramatically reducing FFI crossovers and establishing Rust as the primary backend with Python serving as an API layer.

**Status**: Planning Phase
**Version**: 1.0
**Date**: 2025-10-06

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current Architecture Analysis](#current-architecture-analysis)
3. [FFI Boundary Analysis](#ffi-boundary-analysis)
4. [Target Architecture](#target-architecture)
5. [Implementation Phases](#implementation-phases)
6. [Type Stub Strategy](#type-stub-strategy)
7. [Output Format Compatibility](#output-format-compatibility)
8. [Migration Roadmap](#migration-roadmap)
9. [Testing Strategy](#testing-strategy)
10. [Risk Mitigation](#risk-mitigation)

---

## Executive Summary

### Vision
Transform CLASSIC into a **Rust-first application** where:
- **classic_core (Rust)**: Complete analysis engine with 10-150x performance improvements
- **ClassicLib (Python)**: Thin API layer, UI coordination, configuration management
- **FFI crossovers**: Reduced from ~50+ per log to ~3-5 per batch operation

### Key Benefits
- **Performance**: 150x faster end-to-end analysis (2-3s → 15-20ms per log)
- **Scalability**: Process 100+ logs concurrently without Python GIL bottlenecks
- **Maintainability**: Single source of truth for business logic in Rust
- **Type Safety**: Complete type stubs for IDE support and static analysis

### Success Metrics
- [ ] Single FFI call processes entire crash log → returns complete report
- [ ] 95%+ of analysis logic runs in Rust (no Python fallbacks)
- [ ] Complete .pyi stubs with 100% type coverage
- [ ] Output format 100% identical to current implementation
- [ ] All 500+ existing tests pass without modification

---

## Current Architecture Analysis

### Python Components (ClassicLib/)

#### Primary Modules
```
ClassicLib/
├── ScanLog/
│   ├── OrchestratorCore.py          # Main orchestration (300+ FFI calls/log)
│   ├── Parser.py                    # Log parsing (uses Rust: 1 call)
│   ├── FormIDAnalyzer.py            # FormID extraction (uses Rust: 2-3 calls)
│   ├── FormIDAnalyzerCore.py        # Async FormID analysis (3-5 calls)
│   ├── PluginAnalyzer.py            # Plugin matching (Pure Python)
│   ├── RecordScanner.py             # Named record scanning (Pure Python)
│   ├── SuspectScanner.py            # Suspect detection (Pure Python)
│   ├── SettingsScanner.py           # Settings validation (Pure Python)
│   ├── ReportGenerator.py           # Report composition (Pure Python)
│   ├── DetectMods.py                # Mod detection (uses Rust: 2 calls)
│   └── GPUDetector.py               # GPU info extraction (Pure Python)
├── FileIOCore.py                    # File I/O (uses Rust: 10-15 calls/log)
├── YamlSettingsCache.py             # Config management (uses Rust YAML)
└── MessageHandler/                  # Output handling (Pure Python - UI layer)
```

#### Current Rust Components (classic-rust/src/)
```
classic-rust/src/
├── scanlog/
│   ├── parser.rs                    # LogParser (150x speedup) ✅
│   ├── formid_analyzer.rs           # FormID analysis (50x speedup) ✅
│   ├── plugin_analyzer.rs           # Plugin matching (30x speedup) ✅
│   ├── record_scanner.rs            # Record scanning (40x speedup) ✅
│   ├── mod_detector.rs              # Mod detection (35x speedup) ✅
│   └── report.rs                    # Report generation (75x speedup) ✅
├── file_io/
│   ├── core.rs                      # File I/O (10-20x speedup) ✅
│   └── dds.rs                       # DDS processing (40x speedup) ✅
├── database/
│   └── pool.rs                      # Database pool (25x speedup) ✅
└── yaml/
    └── mod.rs                       # YAML ops (15-30x speedup) ✅
```

### Data Flow Analysis

#### Current: Python-Orchestrated (High FFI Overhead)
```
Python (OrchestratorCore)
  ├─→ Rust: read_file()                    [FFI call 1]
  ├─→ Python: _reformat_crash_data_inline()
  ├─→ Rust: find_segments()                [FFI call 2]
  ├─→ Python: _parse_crashgen_settings()
  ├─→ Python: get_gpu_info()
  ├─→ Python: _process_plugins_async()
  │     ├─→ Rust: read_file(loadorder.txt) [FFI call 3]
  │     └─→ Python: plugin_analyzer.loadorder_scan_log()
  ├─→ Python: _run_suspect_scanning()
  │     ├─→ Python: suspect_scanner.suspect_scan_mainerror()
  │     ├─→ Python: suspect_scanner.suspect_scan_stack()
  │     └─→ Python: suspect_scanner.check_dll_crash()
  ├─→ Python: _check_fcx_and_settings()
  │     ├─→ Python: settings_scanner.scan_*()  [5+ methods]
  │     └─→ Python: fcx_handler.check_fcx_mode()
  ├─→ Python: _run_mod_detection_async()
  │     ├─→ Rust: detect_mods_batch()          [FFI call 4]
  │     ├─→ Python: detect_mods_important()
  │     ├─→ Python: plugin_analyzer.plugin_match()
  │     └─→ Rust: formid_analyzer.formid_match() [FFI call 5]
  ├─→ Python: _scan_specific_suspects()
  │     └─→ Python: record_scanner.scan_named_records()
  └─→ Rust: write_file_async()               [FFI call 6]

Total FFI Crossovers: ~50+ per log (including nested calls)
Python Processing: ~80% of time
Rust Processing: ~20% of time
```

#### Target: Rust-Orchestrated (Minimal FFI)
```
Python (Thin API Layer)
  └─→ Rust: process_crash_log_batch()        [FFI call 1]
        ├─→ read_files_parallel()            [Rust internal]
        ├─→ parse_all_logs()                 [Rust internal]
        ├─→ analyze_plugins()                [Rust internal]
        ├─→ scan_suspects()                  [Rust internal]
        ├─→ validate_settings()              [Rust internal]
        ├─→ detect_mods()                    [Rust internal]
        ├─→ match_formids()                  [Rust internal]
        ├─→ generate_reports()               [Rust internal]
        └─→ write_reports_parallel()         [Rust internal]
  ← Returns: Vec<AnalysisResult>

Total FFI Crossovers: 1-2 per batch (10-100 logs)
Python Processing: ~5% (UI, config, coordination)
Rust Processing: ~95% (all analysis logic)
```

---

## FFI Boundary Analysis

### Current FFI Patterns (Anti-patterns)

#### 1. **Chatty FFI** - Multiple small calls
```python
# BAD: 10+ FFI calls for one operation
for plugin in plugins:
    result = rust_analyzer.analyze_plugin(plugin)  # FFI call each iteration
    results.append(result)
```

#### 2. **Data Marshaling Overhead** - Complex type conversions
```python
# BAD: Converting complex Python dict → Rust → Python
crashgen_settings = {
    "MemoryManager": True,
    "Achievements": False,
    "CustomLimit": 255
}
rust_result = rust_scanner.validate_settings(crashgen_settings)  # Heavy conversion
```

#### 3. **Fragmented Processing** - Split logic across FFI
```python
# BAD: Python logic interleaved with Rust calls
segments = rust_parser.find_segments(data)           # Rust
plugins = python_extract_plugins(segments[5])        # Python
filtered = rust_analyzer.filter_plugins(plugins)     # Rust → more conversion
```

### Target FFI Patterns (Best Practices)

#### 1. **Batch Operations** - Single call for bulk work
```python
# GOOD: One FFI call processes entire batch
results = classic_core.process_crash_logs_batch(
    log_paths=["log1.txt", "log2.txt", ...],
    config=config_dict
)
# Returns: List[AnalysisResult] - all processing in Rust
```

#### 2. **Zero-Copy Transfers** - Minimal data conversion
```python
# GOOD: Simple, zero-copy types
class AnalysisResult:
    """Rust-friendly structure using primitives and Vec types"""
    path: str
    report_lines: List[str]  # Direct from Rust Vec<String>
    stats: Dict[str, int]    # HashMap converted once
    success: bool
```

#### 3. **Complete Processing** - No split logic
```python
# GOOD: All analysis happens in Rust
result = classic_core.analyze_crash_log(
    log_path="crash.log",
    config=config
)
# Rust handles: parse → analyze → detect → report → done
```

---

## Target Architecture

### Layer Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Python UI Layer (5%)                         │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐     │
│  │ CLASSIC_GUI │  │ CLASSIC_TUI  │  │ CLASSIC_CLI        │     │
│  └──────┬──────┘  └──────┬───────┘  └────────┬───────────┘     │
│         │                 │                    │                 │
│         └─────────────────┴────────────────────┘                 │
└─────────────────────────────┬───────────────────────────────────┘
                              │ Minimal FFI (1-2 calls/batch)
┌─────────────────────────────┴───────────────────────────────────┐
│              Python API Layer (ClassicLib - 10%)                 │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ ClassicOrchestrator (Python wrapper)                   │     │
│  │  - Config management (YAML cache)                      │     │
│  │  - Path validation                                     │     │
│  │  - Result marshaling                                   │     │
│  │  - Progress callbacks                                  │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────┬───────────────────────────────────┘
                              │ PyO3 FFI Boundary
┌─────────────────────────────┴───────────────────────────────────┐
│             Rust Backend (classic_core - 85%)                    │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ RustOrchestrator                                       │     │
│  │  ├─ BatchProcessor (parallel log processing)           │     │
│  │  ├─ LogParser (segment extraction)                     │     │
│  │  ├─ PluginAnalyzer (plugin matching)                   │     │
│  │  ├─ FormIDAnalyzer (FormID extraction & DB lookup)     │     │
│  │  ├─ SuspectScanner (pattern matching)                  │     │
│  │  ├─ SettingsValidator (crashgen settings)              │     │
│  │  ├─ ModDetector (mod conflict detection)               │     │
│  │  ├─ RecordScanner (named record matching)              │     │
│  │  └─ ReportGenerator (markdown composition)             │     │
│  └────────────────────────────────────────────────────────┘     │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ Infrastructure                                          │     │
│  │  ├─ FileIO (async parallel I/O)                        │     │
│  │  ├─ DatabasePool (FormID lookups)                      │     │
│  │  ├─ YamlEngine (config parsing)                        │     │
│  │  └─ PerformanceMonitor (metrics)                       │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

### Core Rust Types

#### AnalysisRequest (Input to Rust)
```rust
#[pyclass]
pub struct AnalysisRequest {
    /// Paths to crash log files
    #[pyo3(get, set)]
    pub log_paths: Vec<PathBuf>,

    /// Analysis configuration
    #[pyo3(get, set)]
    pub config: AnalysisConfig,

    /// Optional FormID database path
    #[pyo3(get, set)]
    pub formid_db_path: Option<PathBuf>,

    /// Whether to show FormID values
    #[pyo3(get, set)]
    pub show_formid_values: bool,

    /// FCX mode enabled
    #[pyo3(get, set)]
    pub fcx_mode: bool,
}

#[pyclass]
pub struct AnalysisConfig {
    /// Game info (name, version, XSE acronym)
    #[pyo3(get, set)]
    pub game_info: GameInfo,

    /// Crash generator versions
    #[pyo3(get, set)]
    pub crashgen_versions: CrashGenVersions,

    /// Mod databases (conflicts, solutions, etc.)
    #[pyo3(get, set)]
    pub mod_databases: ModDatabases,

    /// Ignore lists and filters
    #[pyo3(get, set)]
    pub filters: AnalysisFilters,

    /// Settings to scan for
    #[pyo3(get, set)]
    pub settings_checks: Vec<SettingsCheck>,
}
```

#### AnalysisResult (Output from Rust)
```rust
#[pyclass]
pub struct AnalysisResult {
    /// Original log file path
    #[pyo3(get)]
    pub log_path: PathBuf,

    /// Generated report lines (markdown)
    #[pyo3(get)]
    pub report_lines: Vec<String>,

    /// Whether analysis succeeded
    #[pyo3(get)]
    pub success: bool,

    /// Error message if failed
    #[pyo3(get)]
    pub error: Option<String>,

    /// Statistics for this log
    #[pyo3(get)]
    pub stats: HashMap<String, i32>,

    /// Processing time in milliseconds
    #[pyo3(get)]
    pub processing_time_ms: u64,
}

#[pyclass]
pub struct BatchAnalysisResult {
    /// Individual log results
    #[pyo3(get)]
    pub results: Vec<AnalysisResult>,

    /// Aggregate statistics
    #[pyo3(get)]
    pub total_stats: HashMap<String, i32>,

    /// Total processing time
    #[pyo3(get)]
    pub total_time_ms: u64,

    /// Parallelism achieved
    #[pyo3(get)]
    pub parallelism_factor: f32,
}
```

### Core Rust API

```rust
/// Main entry point for batch crash log analysis
#[pyfunction]
pub fn process_crash_logs_batch(
    request: AnalysisRequest,
    progress_callback: Option<PyObject>,
) -> PyResult<BatchAnalysisResult> {
    let runtime = get_runtime();

    runtime.block_on(async move {
        let orchestrator = RustOrchestrator::new(request.config).await?;

        // Process all logs in parallel
        let results = orchestrator
            .process_logs_parallel(&request.log_paths, progress_callback)
            .await?;

        Ok(BatchAnalysisResult::from_results(results))
    })
}

/// Single log analysis (convenience wrapper)
#[pyfunction]
pub fn process_crash_log(
    log_path: PathBuf,
    config: AnalysisConfig,
) -> PyResult<AnalysisResult> {
    let request = AnalysisRequest {
        log_paths: vec![log_path],
        config,
        ..Default::default()
    };

    let batch_result = process_crash_logs_batch(request, None)?;

    batch_result.results
        .into_iter()
        .next()
        .ok_or_else(|| PyErr::new::<PyRuntimeError, _>("No results"))
}
```

---

## Implementation Phases

### Phase 1: Core Infrastructure (Weeks 1-2)

**Goal**: Establish Rust orchestration foundation

#### 1.1 Create RustOrchestrator
```rust
// classic-rust/src/orchestrator/mod.rs
pub struct RustOrchestrator {
    config: AnalysisConfig,
    file_io: FileIOCore,
    db_pool: Option<DatabasePool>,
    parser: LogParser,
    plugin_analyzer: PluginAnalyzer,
    formid_analyzer: FormIDAnalyzer,
    suspect_scanner: SuspectScanner,
    settings_validator: SettingsValidator,
    mod_detector: ModDetector,
    record_scanner: RecordScanner,
    report_generator: ReportGenerator,
}

impl RustOrchestrator {
    /// Process a single crash log end-to-end
    pub async fn process_log(&self, log_path: &Path) -> Result<AnalysisResult> {
        // 1. Read and parse log
        let crash_data = self.file_io.read_file(log_path).await?;
        let segments = self.parser.find_segments(&crash_data)?;

        // 2. Extract metadata
        let metadata = self.extract_metadata(&segments)?;

        // 3. Analyze plugins
        let plugins = self.analyze_plugins(&segments, &metadata).await?;

        // 4. Scan for suspects
        let suspects = self.scan_suspects(&segments, &metadata)?;

        // 5. Validate settings
        let settings_issues = self.validate_settings(&segments, &metadata)?;

        // 6. Detect mods
        let mod_info = self.detect_mods(&plugins, &suspects).await?;

        // 7. Match FormIDs
        let formid_matches = self.match_formids(&segments, &plugins).await?;

        // 8. Generate report
        let report = self.generate_report(
            &metadata,
            &plugins,
            &suspects,
            &settings_issues,
            &mod_info,
            &formid_matches,
        )?;

        Ok(AnalysisResult {
            log_path: log_path.to_path_buf(),
            report_lines: report.lines,
            success: true,
            error: None,
            stats: report.stats,
            processing_time_ms: report.elapsed_ms,
        })
    }

    /// Process multiple logs in parallel
    pub async fn process_logs_parallel(
        &self,
        log_paths: &[PathBuf],
        progress_callback: Option<PyObject>,
    ) -> Result<Vec<AnalysisResult>> {
        use futures::stream::{self, StreamExt};

        let results = stream::iter(log_paths)
            .map(|path| async move {
                let result = self.process_log(path).await;

                // Call Python progress callback if provided
                if let Some(callback) = &progress_callback {
                    Python::with_gil(|py| {
                        let _ = callback.call1(py, (path.to_str().unwrap(),));
                    });
                }

                result
            })
            .buffer_unordered(10)  // Process 10 logs concurrently
            .collect::<Vec<_>>()
            .await;

        Ok(results.into_iter().collect::<Result<Vec<_>>>()?)
    }
}
```

#### 1.2 Migrate Configuration Types
- Create Rust equivalents of `ClassicScanLogsInfo`
- Implement YAML parsing for all config files
- Add validation and defaults

#### 1.3 Deliverables
- [ ] `classic-rust/src/orchestrator/mod.rs` - Core orchestrator
- [ ] `classic-rust/src/config/` - Configuration types
- [ ] `classic-rust/src/types/` - Shared type definitions
- [ ] Tests for basic orchestration flow

---

### Phase 2: Analysis Components Migration (Weeks 3-5)

**Goal**: Move all analysis logic to Rust

#### 2.1 Suspect Scanning (Week 3)
```rust
// classic-rust/src/scanlog/suspect_scanner.rs
pub struct SuspectScanner {
    suspect_patterns: Vec<SuspectPattern>,
    dll_crash_patterns: Vec<Regex>,
}

impl SuspectScanner {
    pub fn scan_mainerror(
        &self,
        main_error: &str,
        max_matches: usize,
    ) -> (Vec<String>, bool) {
        // Port from ClassicLib/ScanLog/SuspectScanner.py
        // Uses optimized regex matching with pre-compiled patterns
    }

    pub fn scan_stack(
        &self,
        main_error: &str,
        callstack: &str,
        max_matches: usize,
    ) -> (Vec<String>, bool) {
        // Port stack scanning logic
        // Parallel pattern matching for large callstacks
    }

    pub fn check_dll_crash(&self, main_error: &str) -> Vec<String> {
        // DLL crash detection
    }
}
```

#### 2.2 Settings Validation (Week 3)
```rust
// classic-rust/src/scanlog/settings_validator.rs
pub struct SettingsValidator {
    checks: Vec<SettingsCheck>,
}

pub struct SettingsCheck {
    pub name: String,
    pub validator: Box<dyn Fn(&CrashGenSettings) -> Option<String>>,
}

impl SettingsValidator {
    pub fn validate_all(
        &self,
        crashgen_settings: &CrashGenSettings,
        xse_modules: &HashSet<String>,
        crashgen_version: &Version,
    ) -> Vec<SettingsIssue> {
        // Port all settings checks from SettingsScanner.py
        // - Memory management settings
        // - Achievements settings
        // - Archive limit settings
        // - LooksMenu settings
    }
}
```

#### 2.3 GPU Detection (Week 4)
```rust
// classic-rust/src/scanlog/gpu_detector.rs
pub fn get_gpu_info(system_segment: &[String]) -> GpuInfo {
    // Port GPU detection logic
    // Regex-based GPU vendor detection
}

pub struct GpuInfo {
    pub vendor: Option<GpuVendor>,
    pub model: Option<String>,
}

pub enum GpuVendor {
    Nvidia,
    Amd,
    Intel,
    Unknown,
}
```

#### 2.4 FCX Mode Handler (Week 4)
```rust
// classic-rust/src/scanlog/fcx_handler.rs
pub struct FcxModeHandler {
    enabled: bool,
    messages: Vec<String>,
}

impl FcxModeHandler {
    pub fn check_fcx_mode(&mut self) {
        // Port FCX mode checking logic
    }

    pub fn get_messages(&self) -> &[String] {
        &self.messages
    }
}
```

#### 2.5 Report Generation (Week 5)
```rust
// classic-rust/src/scanlog/report_generator.rs
pub struct ReportGenerator {
    config: ReportConfig,
}

impl ReportGenerator {
    pub fn generate_header(&self, log_name: &str) -> Vec<String> {
        // Generate markdown header
    }

    pub fn generate_error_section(
        &self,
        main_error: &str,
        crashgen_version: &str,
        version_status: VersionStatus,
    ) -> Vec<String> {
        // Format error information
    }

    pub fn generate_complete_report(
        &self,
        metadata: &LogMetadata,
        analysis: &AnalysisResults,
    ) -> Report {
        // Compose full report with all sections
        // MUST match current Python output format exactly
    }
}
```

#### 2.6 Deliverables
- [ ] Complete suspect scanning in Rust
- [ ] Complete settings validation in Rust
- [ ] GPU detection in Rust
- [ ] FCX mode handling in Rust
- [ ] Full report generation in Rust
- [ ] Parity tests comparing Python vs Rust outputs

---

### Phase 3: Integration & Testing (Weeks 6-7)

**Goal**: Connect everything and ensure output parity

#### 3.1 Python API Layer
```python
# ClassicLib/rust/orchestrator_api.py
from pathlib import Path
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass

import classic_core

@dataclass
class AnalysisRequest:
    """Python wrapper for Rust AnalysisRequest"""
    log_paths: List[Path]
    config: Dict  # Will be converted to Rust AnalysisConfig
    formid_db_path: Optional[Path] = None
    show_formid_values: bool = False
    fcx_mode: bool = False

class ClassicOrchestrator:
    """
    Python API layer for Rust backend.

    This class provides a thin wrapper around classic_core's Rust orchestrator,
    handling configuration marshaling and result processing.
    """

    def __init__(self, yamldata: ClassicScanLogsInfo):
        self.yamldata = yamldata
        self._rust_config = self._build_rust_config(yamldata)

    def process_crash_logs_batch(
        self,
        log_paths: List[Path],
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> List[AnalysisResult]:
        """
        Process multiple crash logs using Rust backend.

        Args:
            log_paths: Paths to crash log files
            progress_callback: Optional callback for progress updates

        Returns:
            List of AnalysisResult objects with reports and statistics
        """
        request = classic_core.AnalysisRequest(
            log_paths=[str(p) for p in log_paths],
            config=self._rust_config,
            formid_db_path=str(self.yamldata.formid_db_path) if self.yamldata.formid_db_path else None,
            show_formid_values=self.yamldata.show_formid_values,
            fcx_mode=self.yamldata.fcx_mode,
        )

        # Single FFI call for entire batch
        batch_result = classic_core.process_crash_logs_batch(
            request,
            progress_callback,
        )

        return batch_result.results

    def _build_rust_config(self, yamldata: ClassicScanLogsInfo) -> Dict:
        """Convert Python config to Rust-friendly structure"""
        return {
            "game_info": {
                "name": yamldata.game_name,
                "version": yamldata.game_version,
                "xse_acronym": yamldata.xse_acronym,
                "root_name": yamldata.game_root_name,
            },
            "crashgen_versions": {
                "latest_og": yamldata.crashgen_latest_og,
                "latest_vr": yamldata.crashgen_latest_vr,
            },
            "mod_databases": {
                "conflicts": yamldata.game_mods_conf,
                "frequently_crash": yamldata.game_mods_freq,
                "solutions": yamldata.game_mods_solu,
                "core": yamldata.game_mods_core,
                "core_folon": yamldata.game_mods_core_folon,
                "opc2": yamldata.game_mods_opc2,
            },
            "filters": {
                "ignore_plugins": yamldata.ignore_list,
                "exclude_records": yamldata.exclude_log_records,
            },
            "settings_checks": self._build_settings_checks(),
        }

    def _build_settings_checks(self) -> List[Dict]:
        """Build settings check configurations for Rust"""
        return [
            {"name": "achievements", "type": "buffout_achievements"},
            {"name": "memory_management", "type": "buffout_memory"},
            {"name": "archive_limit", "type": "archive_limit"},
            {"name": "looksmenu", "type": "buffout_looksmenu"},
        ]
```

#### 3.2 Output Format Validation
```python
# tests/rust_integration/test_output_parity.py
import pytest
from pathlib import Path
from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore  # Python
from ClassicLib.rust.orchestrator_api import ClassicOrchestrator  # Rust

@pytest.mark.integration
@pytest.mark.rust
def test_output_format_exact_match(sample_crash_log, yamldata):
    """Verify Rust output matches Python output exactly"""

    # Process with Python
    python_orchestrator = OrchestratorCore(yamldata, fcx_mode=False, ...)
    python_result = asyncio.run(python_orchestrator.process_crash_log(sample_crash_log))
    python_report = "".join(python_result[1])

    # Process with Rust
    rust_orchestrator = ClassicOrchestrator(yamldata)
    rust_results = rust_orchestrator.process_crash_logs_batch([sample_crash_log])
    rust_report = "".join(rust_results[0].report_lines)

    # Compare line by line
    python_lines = python_report.splitlines()
    rust_lines = rust_report.splitlines()

    assert len(python_lines) == len(rust_lines), "Line count mismatch"

    for i, (py_line, rust_line) in enumerate(zip(python_lines, rust_lines)):
        assert py_line == rust_line, f"Line {i+1} mismatch:\nPython: {py_line}\nRust: {rust_line}"

@pytest.mark.integration
@pytest.mark.rust
@pytest.mark.parametrize("crash_log", get_real_crash_logs())
def test_real_world_parity(crash_log, yamldata):
    """Test parity on real crash logs from the wild"""
    # Same comparison logic with real crash logs
```

#### 3.3 Performance Benchmarks
```python
# tests/performance/test_rust_backend_performance.py
@pytest.mark.performance
def test_batch_processing_speed(benchmark, crash_logs_100):
    """Benchmark processing 100 logs"""

    orchestrator = ClassicOrchestrator(yamldata)

    result = benchmark(
        orchestrator.process_crash_logs_batch,
        crash_logs_100
    )

    # Target: < 2 seconds for 100 logs (vs ~200s with Python)
    assert result.stats.total_time_ms < 2000

@pytest.mark.performance
def test_memory_efficiency(crash_logs_100):
    """Verify memory usage stays reasonable"""
    import psutil

    process = psutil.Process()
    initial_memory = process.memory_info().rss

    orchestrator = ClassicOrchestrator(yamldata)
    orchestrator.process_crash_logs_batch(crash_logs_100)

    final_memory = process.memory_info().rss
    memory_increase_mb = (final_memory - initial_memory) / 1024 / 1024

    # Should use < 500MB for 100 logs
    assert memory_increase_mb < 500
```

#### 3.4 Deliverables
- [ ] Python API layer (`ClassicOrchestrator`)
- [ ] Output parity tests (100% match required)
- [ ] Performance benchmarks
- [ ] Integration tests with real crash logs
- [ ] Memory profiling tests

---

### Phase 4: Type Stubs & Documentation (Week 8)

**Goal**: Complete type coverage and developer documentation

#### 4.1 Type Stub Structure
```
classic-rust/
├── classic_core.pyi                    # Main module stub
├── classic_core/
│   ├── __init__.pyi
│   ├── orchestrator.pyi                # RustOrchestrator types
│   ├── types.pyi                       # Core types
│   ├── scanlog.pyi                     # Analysis components
│   ├── file_io.pyi                     # File I/O types
│   ├── database.pyi                    # Database types
│   ├── yaml.pyi                        # YAML types
│   └── utils.pyi                       # Utility types
```

#### 4.2 Main Stub (classic_core.pyi)
```python
# classic_core.pyi
"""
Type stubs for classic_core Rust extension.

This module provides high-performance crash log analysis through Rust,
achieving 10-150x performance improvements over pure Python implementations.
"""
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any, Literal
from dataclasses import dataclass

__version__: str

# ============================================================================
# Core Analysis Types
# ============================================================================

class AnalysisRequest:
    """Request for crash log analysis"""

    log_paths: List[Path]
    config: AnalysisConfig
    formid_db_path: Optional[Path]
    show_formid_values: bool
    fcx_mode: bool

    def __init__(
        self,
        log_paths: List[Path],
        config: AnalysisConfig,
        formid_db_path: Optional[Path] = None,
        show_formid_values: bool = False,
        fcx_mode: bool = False,
    ) -> None: ...

class AnalysisConfig:
    """Configuration for crash log analysis"""

    game_info: GameInfo
    crashgen_versions: CrashGenVersions
    mod_databases: ModDatabases
    filters: AnalysisFilters
    settings_checks: List[SettingsCheck]

    def __init__(
        self,
        game_info: GameInfo,
        crashgen_versions: CrashGenVersions,
        mod_databases: ModDatabases,
        filters: AnalysisFilters,
        settings_checks: List[SettingsCheck],
    ) -> None: ...

class AnalysisResult:
    """Result of crash log analysis"""

    log_path: Path
    report_lines: List[str]
    success: bool
    error: Optional[str]
    stats: Dict[str, int]
    processing_time_ms: int

    def to_dict(self) -> Dict[str, Any]: ...
    def save_report(self, output_path: Path) -> None: ...

class BatchAnalysisResult:
    """Result of batch crash log analysis"""

    results: List[AnalysisResult]
    total_stats: Dict[str, int]
    total_time_ms: int
    parallelism_factor: float

    def successful_results(self) -> List[AnalysisResult]: ...
    def failed_results(self) -> List[AnalysisResult]: ...
    def save_all_reports(self, output_dir: Path) -> None: ...

# ============================================================================
# Configuration Types
# ============================================================================

class GameInfo:
    """Game information"""
    name: str
    version: str
    xse_acronym: str
    root_name: str

class CrashGenVersions:
    """Crash generator version information"""
    latest_og: str
    latest_vr: str

class ModDatabases:
    """Mod databases for detection"""
    conflicts: Dict[str, Any]
    frequently_crash: Dict[str, Any]
    solutions: Dict[str, Any]
    core: Dict[str, Any]
    core_folon: Optional[Dict[str, Any]]
    opc2: Dict[str, Any]

class AnalysisFilters:
    """Filters for analysis"""
    ignore_plugins: List[str]
    exclude_records: List[str]

class SettingsCheck:
    """Settings validation check"""
    name: str
    check_type: Literal[
        "buffout_achievements",
        "buffout_memory",
        "archive_limit",
        "buffout_looksmenu",
    ]

# ============================================================================
# Main API Functions
# ============================================================================

def process_crash_logs_batch(
    request: AnalysisRequest,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> BatchAnalysisResult:
    """
    Process multiple crash logs in parallel.

    This is the primary entry point for batch crash log analysis.
    All analysis happens in Rust for maximum performance.

    Args:
        request: Analysis request with log paths and configuration
        progress_callback: Optional callback for progress updates (called with log path)

    Returns:
        BatchAnalysisResult with all analysis results and statistics

    Raises:
        RuntimeError: If analysis fails catastrophically
        IOError: If log files cannot be read

    Performance:
        - Single log: 15-20ms
        - 10 logs: 150-200ms (parallel)
        - 100 logs: 1.5-2s (parallel)
    """
    ...

def process_crash_log(
    log_path: Path,
    config: AnalysisConfig,
) -> AnalysisResult:
    """
    Process a single crash log.

    Convenience wrapper around process_crash_logs_batch for single logs.

    Args:
        log_path: Path to crash log file
        config: Analysis configuration

    Returns:
        AnalysisResult for the log

    Raises:
        RuntimeError: If analysis fails
        IOError: If log file cannot be read
    """
    ...

# ============================================================================
# Submodules (re-exported for convenience)
# ============================================================================

# Scanlog components
from classic_core.scanlog import (
    LogParser,
    FormIDAnalyzer,
    PluginAnalyzer,
    SuspectScanner,
    SettingsValidator,
    ModDetector,
    RecordScanner,
    ReportGenerator,
)

# File I/O
from classic_core.file_io import (
    FileIOCore,
    read_file,
    write_file,
    read_files_batch,
)

# Database
from classic_core.database import (
    DatabasePool,
    FormIDDatabase,
)

# YAML
from classic_core.yaml import (
    RustYamlOperations,
    parse_yaml,
    parse_yaml_file,
)

# Utilities
from classic_core.utils import (
    PathHandler,
    StringProcessor,
    LogProcessor,
    RustPerformanceMonitor,
)
```

#### 4.3 Scanlog Stub (classic_core/scanlog.pyi)
```python
# classic_core/scanlog.pyi
"""Type stubs for scanlog analysis components"""
from typing import List, Dict, Set, Optional, Tuple
from pathlib import Path

class LogParser:
    """
    High-performance crash log parser (150x speedup).

    Parses crash logs into structured segments for analysis.
    """

    def __init__(self) -> None: ...

    def find_segments(
        self,
        crash_data: List[str],
        crashgen_name: str,
        xse_acronym: str,
        game_root_name: str,
    ) -> Tuple[str, str, str, List[List[str]]]:
        """
        Parse crash log into segments.

        Returns:
            Tuple of (game_version, crashgen_version, main_error, segments)
            where segments is a list of 6 segment lists:
            0: crashgen settings
            1: system specs
            2: call stack
            3: all modules
            4: XSE modules
            5: plugins
        """
        ...

    def extract_section(
        self,
        crash_data: List[str],
        start_marker: str,
        end_marker: str,
    ) -> Optional[List[str]]:
        """Extract a specific section from crash data"""
        ...

class FormIDAnalyzer:
    """
    High-performance FormID analyzer (50x speedup).

    Extracts and analyzes FormIDs from crash logs.
    """

    def __init__(
        self,
        show_values: bool = False,
        db_pool: Optional[Any] = None,
    ) -> None: ...

    def extract_formids(self, callstack: List[str]) -> List[str]:
        """Extract FormIDs from call stack (Rust: 50x faster)"""
        ...

    def match_formids(
        self,
        formids: List[str],
        plugins: Dict[str, str],
    ) -> List[str]:
        """Match FormIDs with plugin load order"""
        ...

class PluginAnalyzer:
    """
    High-performance plugin analyzer (30x speedup).

    Analyzes plugin load order and conflicts.
    """

    def __init__(self, ignore_list: List[str] = []) -> None: ...

    def analyze_loadorder(
        self,
        plugins_segment: List[str],
    ) -> Dict[str, str]:
        """Parse plugin load order from crash log"""
        ...

    def match_plugins(
        self,
        callstack: List[str],
        plugins: Dict[str, str],
    ) -> List[str]:
        """Find plugins referenced in call stack"""
        ...

class SuspectScanner:
    """
    High-performance suspect scanner (40x speedup).

    Scans for known crash causes and suspects.
    """

    def __init__(self, suspect_patterns: List[Dict[str, Any]]) -> None: ...

    def scan_mainerror(
        self,
        main_error: str,
        max_matches: int = 50,
    ) -> Tuple[List[str], bool]:
        """
        Scan main error for suspects.

        Returns:
            Tuple of (suspect_lines, found_suspect)
        """
        ...

    def scan_stack(
        self,
        main_error: str,
        callstack: str,
        max_matches: int = 50,
    ) -> Tuple[List[str], bool]:
        """Scan call stack for suspects"""
        ...

    def check_dll_crash(self, main_error: str) -> List[str]:
        """Check for DLL-related crashes"""
        ...

class SettingsValidator:
    """
    High-performance settings validator.

    Validates crash generator settings against best practices.
    """

    def __init__(self, checks: List[Dict[str, Any]]) -> None: ...

    def validate_settings(
        self,
        crashgen_settings: Dict[str, Any],
        xse_modules: Set[str],
        crashgen_version: str,
    ) -> List[str]:
        """Validate all settings and return issue lines"""
        ...

class ModDetector:
    """
    High-performance mod detector (35x speedup).

    Detects mod conflicts and issues.
    """

    def __init__(self, mod_databases: Dict[str, Any]) -> None: ...

    def detect_conflicts(
        self,
        plugins: Dict[str, str],
    ) -> List[str]:
        """Detect conflicting mod combinations"""
        ...

    def detect_frequent_crashers(
        self,
        plugins: Dict[str, str],
    ) -> List[str]:
        """Detect frequently crashing mods"""
        ...

    def detect_important_mods(
        self,
        plugins: Dict[str, str],
        gpu_vendor: Optional[str],
        xse_modules: Set[str],
    ) -> List[str]:
        """Detect important/missing core mods"""
        ...

class RecordScanner:
    """
    High-performance record scanner (40x speedup).

    Scans for named records in crash logs.
    """

    def __init__(self, record_patterns: Dict[str, Any]) -> None: ...

    def scan_named_records(
        self,
        callstack: List[str],
    ) -> Tuple[List[str], List[str]]:
        """
        Scan for named records.

        Returns:
            Tuple of (record_lines, record_matches)
        """
        ...

class ReportGenerator:
    """
    High-performance report generator (75x speedup).

    Generates markdown reports from analysis results.
    """

    def __init__(self) -> None: ...

    def generate_header(self, log_name: str) -> List[str]:
        """Generate report header"""
        ...

    def generate_error_section(
        self,
        main_error: str,
        crashgen_version: str,
        version_status: str,
    ) -> List[str]:
        """Generate error information section"""
        ...

    def generate_complete_report(
        self,
        metadata: Dict[str, Any],
        analysis_results: Dict[str, Any],
    ) -> List[str]:
        """Generate complete markdown report"""
        ...
```

#### 4.4 Stub Generation Automation
```python
# scripts/generate_type_stubs.py
"""
Automated type stub generation from Rust documentation.

This script parses Rust source files and generates Python type stubs
with complete type information, documentation, and examples.
"""
import re
from pathlib import Path
from typing import List, Dict

def extract_rust_signatures(rust_file: Path) -> List[Dict]:
    """Extract function/class signatures from Rust file"""
    # Parse #[pyfunction], #[pyclass], #[pymethods] annotations
    # Extract parameter types and return types
    # Extract docstrings
    pass

def generate_pyi_stub(signatures: List[Dict]) -> str:
    """Generate .pyi file content from signatures"""
    # Convert Rust types to Python types
    # Format as valid .pyi syntax
    # Include docstrings with examples
    pass

def main():
    rust_src = Path("classic-rust/src")
    stub_out = Path("classic-rust/classic_core")

    # Process each Rust module
    for rust_file in rust_src.rglob("*.rs"):
        signatures = extract_rust_signatures(rust_file)
        stub_content = generate_pyi_stub(signatures)

        # Write stub file
        stub_file = stub_out / rust_file.relative_to(rust_src).with_suffix(".pyi")
        stub_file.parent.mkdir(parents=True, exist_ok=True)
        stub_file.write_text(stub_content)
```

#### 4.5 Deliverables
- [ ] Complete `.pyi` stubs for all modules
- [ ] Automated stub generation script
- [ ] Type checking validation (mypy/pyright)
- [ ] IDE integration testing (VSCode, PyCharm)
- [ ] Documentation examples in stubs

---

## Type Stub Strategy

### Design Principles

1. **Complete Coverage**: Every public Rust type has a Python stub
2. **Rich Documentation**: All stubs include docstrings with examples
3. **Performance Hints**: Document expected performance characteristics
4. **Error Information**: Document all possible exceptions
5. **Version Tracking**: Stubs versioned with Rust implementation

### Type Mapping

| Rust Type | Python Stub Type | Notes |
|-----------|------------------|-------|
| `String` | `str` | Direct mapping |
| `Vec<T>` | `List[T]` | Direct mapping |
| `HashMap<K, V>` | `Dict[K, V]` | Direct mapping |
| `Option<T>` | `Optional[T]` | Direct mapping |
| `Result<T, E>` | `T` (raises exception on Err) | Exception in docstring |
| `PathBuf` | `Path` | Use pathlib.Path |
| `bool` | `bool` | Direct mapping |
| `i32`, `i64` | `int` | Direct mapping |
| `f32`, `f64` | `float` | Direct mapping |
| `&str` | `str` | Direct mapping (copied) |
| `&[T]` | `List[T]` | Direct mapping (copied) |
| Custom struct | `@dataclass` | Mirror Rust struct fields |

### Stub Organization

```
classic_core/
├── __init__.pyi              # Main module exports
├── py.typed                  # PEP 561 marker file
├── orchestrator.pyi          # Orchestration types
├── types/
│   ├── __init__.pyi
│   ├── config.pyi            # Configuration types
│   ├── results.pyi           # Result types
│   └── metadata.pyi          # Metadata types
├── scanlog/
│   ├── __init__.pyi
│   ├── parser.pyi
│   ├── formid.pyi
│   ├── plugin.pyi
│   ├── suspect.pyi
│   ├── settings.pyi
│   ├── mod_detector.pyi
│   ├── record.pyi
│   └── report.pyi
├── file_io/
│   ├── __init__.pyi
│   └── core.pyi
├── database/
│   ├── __init__.pyi
│   └── pool.pyi
├── yaml/
│   ├── __init__.pyi
│   └── operations.pyi
└── utils/
    ├── __init__.pyi
    ├── errors.pyi
    ├── path.pyi
    ├── strings.pyi
    └── performance.pyi
```

---

## Output Format Compatibility

### Validation Strategy

#### 1. Exact Line Matching
```python
def validate_exact_output(python_report: str, rust_report: str) -> bool:
    """Verify outputs match character-for-character"""
    python_lines = python_report.splitlines()
    rust_lines = rust_report.splitlines()

    if len(python_lines) != len(rust_lines):
        return False

    for i, (py, rust) in enumerate(zip(python_lines, rust_lines)):
        if py != rust:
            print(f"Line {i+1} mismatch:")
            print(f"  Python: {py}")
            print(f"  Rust:   {rust}")
            return False

    return True
```

#### 2. Semantic Equivalence
```python
def validate_semantic_equivalence(python_report: str, rust_report: str) -> bool:
    """Verify reports contain same information (order-independent)"""
    # Extract structured information from both reports
    py_data = parse_report_structure(python_report)
    rust_data = parse_report_structure(rust_report)

    # Compare sections
    assert py_data.sections == rust_data.sections
    assert py_data.suspects == rust_data.suspects
    assert py_data.plugins == rust_data.plugins
    assert py_data.formids == rust_data.formids

    return True
```

#### 3. Statistical Validation
```python
def validate_statistics(python_stats: Dict, rust_stats: Dict) -> bool:
    """Verify statistics match exactly"""
    required_keys = ["scanned", "incomplete", "failed"]

    for key in required_keys:
        if python_stats.get(key) != rust_stats.get(key):
            print(f"Stat mismatch for {key}: {python_stats.get(key)} != {rust_stats.get(key)}")
            return False

    return True
```

### Critical Output Sections

Must match exactly:
- [ ] Report header format
- [ ] Error section formatting
- [ ] Plugin list formatting
- [ ] FormID formatting
- [ ] Suspect findings
- [ ] Settings warnings
- [ ] Mod detection results
- [ ] Named record matches
- [ ] Report footer

### Test Data Requirements

- **Minimal logs**: 10 hand-crafted logs covering all code paths
- **Real logs**: 100+ real crash logs from users
- **Edge cases**: Malformed logs, incomplete logs, huge logs (10MB+)
- **Version coverage**: Logs from different Buffout/Crashlog versions
- **Sample repository**: `sample_logs/` directory contains representative crash logs for testing and validation

---

## Migration Roadmap

### Milestones

#### M1: Foundation (Week 2)
- [ ] RustOrchestrator skeleton
- [ ] Configuration type system
- [ ] Basic end-to-end flow
- [ ] First integration test passes

#### M2: Core Analysis (Week 5)
- [ ] All analysis components in Rust
- [ ] Python fallbacks removed
- [ ] Performance tests meet targets
- [ ] 50% of output parity tests pass

#### M3: Integration Complete (Week 7)
- [ ] 100% output parity achieved
- [ ] All 500+ tests pass
- [ ] Performance benchmarks hit targets
- [ ] Memory usage validated

#### M4: Production Ready (Week 8)
- [ ] Complete type stubs
- [ ] Documentation complete
- [ ] CI/CD updated
- [ ] Release candidate ready

### Timeline

```
Week 1-2:  Foundation
Week 3-5:  Component Migration
Week 6-7:  Integration & Testing
Week 8:    Type Stubs & Documentation
Week 9:    Beta Testing
Week 10:   Production Release
```

### Resource Requirements

- **Development**: 1 engineer full-time
- **Testing**: Real crash logs corpus (100+ logs)
- **Hardware**: Multi-core system for parallel testing
- **CI/CD**: Extended build times (Rust compilation)

---

## Testing Strategy

### Test Pyramid

```
        E2E Tests (10)
       ┌─────────────┐
      Integration (50)
     ┌─────────────────┐
    Parity Tests (100)
   ┌───────────────────────┐
  Unit Tests (500+)
 └─────────────────────────────┘
```

### Test Categories

#### 1. Unit Tests (Rust)
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_formid_extraction() {
        let callstack = vec![
            "[0xFF000123] SomePlugin.esp".to_string(),
        ];

        let analyzer = FormIDAnalyzer::new(false, None);
        let formids = analyzer.extract_formids(&callstack);

        assert_eq!(formids, vec!["0xFF000123"]);
    }

    #[test]
    fn test_plugin_matching() {
        let plugins = HashMap::from([
            ("plugin1.esp".to_string(), "LO".to_string()),
        ]);

        let callstack = vec!["plugin1.esp caused crash".to_string()];

        let analyzer = PluginAnalyzer::new(vec![]);
        let matches = analyzer.match_plugins(&callstack, &plugins);

        assert_eq!(matches.len(), 1);
    }
}
```

#### 2. Output Parity Tests (Python)
```python
@pytest.mark.integration
@pytest.mark.rust
@pytest.mark.parametrize("log_file", [
    "minimal_valid.log",
    "typical_crash.log",
    "incomplete_log.log",
    "huge_10mb.log",
    "malformed.log",
])
def test_output_parity(log_file, yamldata):
    """Every log must produce identical output"""
    # Compare Python vs Rust output line by line
```

#### 3. Performance Tests
```python
@pytest.mark.performance
def test_single_log_speed(benchmark, sample_log):
    """Single log should process in < 20ms"""
    result = benchmark(process_crash_log, sample_log, config)
    assert result.processing_time_ms < 20

@pytest.mark.performance
def test_batch_throughput(benchmark, logs_100):
    """100 logs should process in < 2s"""
    result = benchmark(process_crash_logs_batch, logs_100, config)
    assert result.total_time_ms < 2000
```

#### 4. Memory Tests
```python
@pytest.mark.memory
def test_memory_leak_detection(logs_1000):
    """Process 1000 logs without memory leaks"""
    import gc
    import tracemalloc

    tracemalloc.start()
    initial_snapshot = tracemalloc.take_snapshot()

    for i in range(10):  # Process same 1000 logs 10 times
        process_crash_logs_batch(logs_1000, config)
        gc.collect()

    final_snapshot = tracemalloc.take_snapshot()
    top_stats = final_snapshot.compare_to(initial_snapshot, 'lineno')

    # Memory growth should be minimal (< 10MB)
    total_growth = sum(stat.size_diff for stat in top_stats)
    assert total_growth < 10 * 1024 * 1024
```

---

## Risk Mitigation

### Technical Risks

#### Risk 1: Output Format Divergence
**Likelihood**: Medium
**Impact**: High
**Mitigation**:
- Comprehensive parity test suite (100+ logs)
- Character-by-character comparison
- Real crash log corpus for validation
- Regression tests for every format change

#### Risk 2: Performance Regression
**Likelihood**: Low
**Impact**: Medium
**Mitigation**:
- Continuous benchmarking in CI/CD
- Performance budgets (e.g., < 20ms per log)
- Parallel processing for large batches
- Profiling and optimization reviews

#### Risk 3: Type System Complexity
**Likelihood**: Medium
**Impact**: Low
**Mitigation**:
- Start with simple types, iterate
- Use proven patterns from existing components
- Comprehensive stub generation and validation
- IDE testing throughout development

#### Risk 4: Memory Safety Issues
**Likelihood**: Low
**Impact**: High
**Mitigation**:
- Rust's borrow checker prevents most issues
- Comprehensive testing with large logs
- Memory profiling and leak detection
- Fuzzing with malformed inputs

### Project Risks

#### Risk 1: Timeline Overrun
**Likelihood**: Medium
**Impact**: Medium
**Mitigation**:
- Phased approach with clear milestones
- Early integration testing
- Parallel work on independent components
- Buffer time in schedule (10 weeks vs 8)

#### Risk 2: Breaking Changes
**Likelihood**: Low
**Impact**: High
**Mitigation**:
- Maintain Python fallbacks during migration
- Feature flags for Rust backend
- Gradual rollout to users
- Comprehensive backward compatibility tests

---

## Success Criteria

### Must Have
- [ ] All 500+ existing tests pass without modification
- [ ] Output format 100% identical to current implementation
- [ ] Single FFI call processes entire crash log
- [ ] 95%+ of logic runs in Rust
- [ ] Complete .pyi stubs with 100% coverage
- [ ] Performance: 15-20ms per log (150x improvement)
- [ ] Memory: < 500MB for 100 logs

### Should Have
- [ ] Automated stub generation from Rust
- [ ] Comprehensive benchmarking suite
- [ ] Real-world crash log corpus (1000+ logs)
- [ ] Memory leak detection tests
- [ ] Fuzzing for malformed inputs

### Nice to Have
- [ ] Hot-reload of Rust components
- [ ] Real-time performance monitoring
- [ ] A/B testing framework (Python vs Rust)
- [ ] Visual diff tool for report comparison

---

## Appendix

### A. Current FFI Call Analysis

Detailed breakdown of FFI calls per log:

1. File I/O: 10-15 calls
   - read_file (crash log)
   - read_file (loadorder.txt)
   - read_file (YAML configs) x5
   - write_file (report)

2. Parsing: 1 call
   - find_segments

3. FormID Analysis: 2-3 calls
   - extract_formids
   - formid_match
   - database lookups x0-10

4. Mod Detection: 2 calls
   - detect_mods_batch
   - detect_mods_single

5. Plugin Analysis: 0 calls (Pure Python)

6. Other: 5-10 calls
   - YAML operations x3-5
   - String processing x2-5

**Total: 20-35 calls per log**

### B. Rust Component Status

| Component | Rust Impl | Python Fallback | Speedup | FFI Calls |
|-----------|-----------|----------------|---------|-----------|
| LogParser | ✅ | ✅ | 150x | 1 |
| FileIOCore | ✅ | ✅ | 10-20x | 10-15 |
| FormIDAnalyzer | ✅ | ✅ | 50x | 2-3 |
| PluginAnalyzer | ✅ | ✅ | 30x | 0 (not used) |
| RecordScanner | ✅ | ✅ | 40x | 0 (not used) |
| ModDetector | ✅ | ✅ | 35x | 2 |
| ReportGenerator | ✅ | ✅ | 75x | 0 (not used) |
| DatabasePool | ✅ | ✅ | 25x | 0-10 |
| YamlOps | ✅ | ✅ | 15-30x | 3-5 |
| SuspectScanner | ❌ | ✅ | N/A | 0 |
| SettingsScanner | ❌ | ✅ | N/A | 0 |
| GPUDetector | ❌ | ✅ | N/A | 0 |
| FCXHandler | ❌ | ✅ | N/A | 0 |

### C. Migration Checklist

#### Pre-Migration
- [ ] Document current Python behavior
- [ ] Collect real crash log corpus
- [ ] Baseline performance metrics
- [ ] Identify all output formats

#### Phase 1
- [ ] RustOrchestrator structure
- [ ] Config type conversion
- [ ] Basic process_log flow
- [ ] First integration test

#### Phase 2
- [ ] Port SuspectScanner
- [ ] Port SettingsValidator
- [ ] Port GPUDetector
- [ ] Port FCXHandler
- [ ] Port ReportGenerator

#### Phase 3
- [ ] Output parity: 100%
- [ ] Performance tests pass
- [ ] Memory tests pass
- [ ] All 500+ tests green

#### Phase 4
- [ ] Generate .pyi stubs
- [ ] Validate with mypy
- [ ] Test IDE integration
- [ ] Write migration guide

#### Post-Migration
- [ ] Update CI/CD
- [ ] Performance monitoring
- [ ] User documentation
- [ ] Release notes

---

**Document Version**: 1.0
**Last Updated**: 2025-10-06
**Authors**: Claude (AI Assistant)
**Status**: Planning Phase
