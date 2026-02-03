# Feature Landscape: Rust Migration for CLASSIC v8.2.0-part2

**Domain:** Crash log analysis tool migration (Python to Rust)
**Researched:** 2026-02-02
**Confidence:** HIGH (based on existing codebase analysis)

## Executive Summary

This document catalogs the expected features and behaviors for migrating four core components to Rust:
1. **Scanning Orchestration** - Coordinating multiple analysis passes
2. **Game Detection** - Finding game installations, detecting versions
3. **Report Generation** - Markdown formatting, template rendering
4. **Settings Management** - Loading/saving user preferences

The analysis is based on the existing Python implementations and partially-complete Rust equivalents in the codebase.

---

## 1. Scanning Orchestration

### Table Stakes (Must Have)

| Feature | Why Expected | Complexity | Existing Rust | Notes |
|---------|--------------|------------|---------------|-------|
| Single log processing | Core functionality | High | Yes (`OrchestratorCore.process_log()`) | 800+ lines in Rust |
| Batch log processing | Performance requirement | Medium | Yes (`process_logs_batch()`) | Parallel via futures |
| Async context manager | Resource lifecycle | Medium | Partial (`async_enter/exit`) | DB pool initialization |
| Plugin segment parsing | Required for mod detection | Low | Yes (via `PluginAnalyzer`) | Delegates to existing |
| FormID extraction | Crash diagnosis | Medium | Yes (`FormIDAnalyzerCore`) | Integrated |
| Suspect scanning | Core crash analysis | Medium | Yes (`SuspectScanner`) | Pattern matching |
| Mod detection | User value | Medium | Yes (`detect_mods_*`) | Multiple mod databases |
| Report composition | Output generation | Low | Yes (`ReportGenerator`) | Fragment-based |
| Statistics collection | User feedback | Low | Yes (`AnalysisResult`) | scanned/incomplete/failed |
| Crash data reformatting | Data cleanup | Low | Yes (`reformat_crash_data_inline`) | Bracket padding, simplify |
| VR mode auto-detection | Game variant support | Low | Partial | Need per-log detection |
| loadorder.txt override | Power user feature | Low | Yes (`load_loadorder_async`) | Alternate plugin source |

### Differentiators (Improvements over Python)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Unbounded parallelism | 10-20x batch speedup | Medium | vs Python's batch_size=10 limit |
| SIMD-optimized parsing | 20-40x single-log speedup | High | Already in LogParser |
| String interning/pooling | Memory efficiency | Medium | `StringPool` in report.rs |
| Zero-copy Arc sharing | Reduced allocations | Low | Already implemented |
| Adaptive concurrency | CPU-optimal scaling | Low | `num_cpus::get()` based |
| Sub-millisecond timing | Precise performance metrics | Low | Microsecond tracking |
| Lock-free concurrent reads | No contention on hot paths | Medium | DashMap usage |

### Anti-Features (Do NOT Build)

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| GUI integration in Rust | Maintains Python's PySide6 ownership | Keep PyO3 boundary clean |
| Direct YAML file writes | Settings persistence is Python-owned | Return data, let Python write |
| Interactive user prompts | CLI/GUI handles interaction | Return errors, not prompts |
| Mutable shared state | Thread safety issues | Use Arc<RwLock<>> or immutable patterns |
| Runtime-dependent fallbacks | "DISABLE_RUST" was removed in v1.0 | Fail-fast RuntimeError |

### Dependencies on Existing Rust Components

| Dependency | Crate | Status |
|------------|-------|--------|
| File I/O | `classic-file-io-core` | Complete |
| Log parsing | `classic-scanlog-core` (LogParser) | Complete |
| Database pool | `classic-database-core` | Complete |
| YAML operations | `classic-yaml-core` | Complete |
| Plugin analysis | `classic-scanlog-core` (PluginAnalyzer) | Complete |
| FormID analysis | `classic-scanlog-core` (FormIDAnalyzerCore) | Complete |
| Mod detection | `classic-scanlog-core` (mod_detector) | Complete |
| Suspect scanning | `classic-scanlog-core` (SuspectScanner) | Complete |
| Settings validation | `classic-scanlog-core` (SettingsValidator) | Complete |
| Record scanning | `classic-scanlog-core` (RecordScanner) | Complete |

---

## 2. Game Detection

### Table Stakes (Must Have)

| Feature | Why Expected | Complexity | Existing Rust | Notes |
|---------|--------------|------------|---------------|-------|
| Multi-strategy path finding | Fallback chain | Medium | Yes (`GamePathFinder`) | Cache -> Registry -> XSE |
| Windows registry query | Primary detection | Low | Yes (platform::windows) | Bethesda + GOG keys |
| XSE log parsing | Secondary detection | Low | Yes (`parse_xse_log`) | Plugin directory extraction |
| Cached path validation | Performance | Low | Yes (`validate_game_path`) | Exe + loader checks |
| VR variant support | Game variants | Low | Yes (`is_vr` flag) | Affects registry path |
| Game executable validation | Installation integrity | Low | Yes | Part of validation |
| XSE loader detection | Script extender check | Low | Yes (optional in finder) | f4se_loader.exe etc |

### Differentiators (Improvements over Python)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| 10-50x registry query speedup | Faster startup | Low | Measured in existing code |
| Combined strategies in one call | Simpler API | Low | Single `find_game_path()` call |
| Stateless finder | No singleton issues | Low | Create per-use, no global |
| Comprehensive error types | Better diagnostics | Low | `GamePathError` enum |

### Anti-Features (Do NOT Build)

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| User input prompts | CLI/GUI handles interaction | Return NotFound error |
| Automatic path persistence | Python owns YAML writes | Return path, let Python save |
| Steam API integration | Scope creep, fragile | Rely on registry/XSE log |
| Game version checking | Separate concern | Use version-registry-core |

### Dependencies on Existing Rust Components

| Dependency | Crate | Status |
|------------|-------|--------|
| Path validation | `classic-path-core` (validator) | Complete |
| Windows registry | `classic-path-core` (platform::windows) | Complete |
| XSE log parsing | `classic-path-core` (game_path) | Complete |
| Error types | `classic-path-core` (error) | Complete |

---

## 3. Report Generation

### Table Stakes (Must Have)

| Feature | Why Expected | Complexity | Existing Rust | Notes |
|---------|--------------|------------|---------------|-------|
| Header generation | Report structure | Low | Yes (`generate_header`) | Version, filename |
| Error section | Crash info display | Low | Yes (`generate_error_section`) | Main error, version status |
| Suspect section | Analysis results | Low | Yes (`generate_suspect_*`) | Header + footer |
| Settings section | Configuration issues | Low | Yes (`generate_settings_section_header`) | Section header |
| Mod check headers | Organization | Low | Yes (`generate_mod_check_header`) | Dynamic check type |
| Plugin suspect header | Section marker | Low | Yes (`generate_plugin_suspect_header`) | |
| FormID section header | Section marker | Low | Yes (`generate_formid_section_header`) | |
| Record section header | Section marker | Low | Yes (`generate_record_section_header`) | |
| Footer generation | Report closure | Low | Yes (`generate_footer`) | Credits, version |
| Fragment composition | Functional pattern | Medium | Yes (`ReportComposer`) | Immutable fragments |
| Markdown formatting | Output format | Low | Yes | Headers, bullets, emphasis |
| VR mode indicator | VR-specific reports | Low | Partial | Need header variant |

### Differentiators (Improvements over Python)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| 10-15x generation speedup | Faster batch processing | Medium | Measured in existing code |
| String interning | Memory efficiency | Medium | `StringPool` global |
| Parallel fragment processing | Scalability | Low | Rayon-based |
| Efficient string building | Reduced allocations | Low | Pre-sized buffers |
| Arc-based content sharing | Zero-copy fragments | Low | Already implemented |
| Divide-and-conquer composition | Parallel reduction | Low | For 10+ fragments |

### Anti-Features (Do NOT Build)

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| HTML/RTF output | Scope creep, Markdown is standard | Stick to Markdown |
| File writing in generator | Separation of concerns | Return strings, caller writes |
| Localization/i18n | Future scope | Hardcoded English strings |
| Template engine integration | Unnecessary complexity | Direct string formatting |

### Dependencies on Existing Rust Components

| Dependency | Crate | Status |
|------------|-------|--------|
| ReportFragment | `classic-scanlog-core` (report) | Complete |
| ReportComposer | `classic-scanlog-core` (report) | Complete |
| ReportGenerator | `classic-scanlog-core` (report) | Complete |
| StringPool | `classic-scanlog-core` (report) | Complete |

---

## 4. Settings Management

### Table Stakes (Must Have)

| Feature | Why Expected | Complexity | Existing Rust | Notes |
|---------|--------------|------------|---------------|-------|
| YAML file loading (sync) | Settings access | Low | Yes (`load_settings_sync`) | |
| YAML file loading (async) | Non-blocking I/O | Low | Yes (`load_settings_async`) | |
| Thread-safe cache | Concurrent access | Medium | Yes (DashMap-based) | |
| Multi-document YAML support | File format | Low | Yes (yaml-rust2) | |
| Cache invalidation | Settings reload | Low | Yes (`invalidate`) | |
| Batch loading | Startup optimization | Medium | Yes (`load_batch_async`) | Parallel file I/O |
| Key-based retrieval | Simple API | Low | Yes (`get_cached`) | |
| Cache introspection | Debugging | Low | Yes (`cache_keys`, `cache_size`) | |

### Differentiators (Improvements over Python)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| 15-30x YAML parse speedup | Faster startup | High | yaml-rust2 vs ruamel |
| Lock-free concurrent access | No contention | Medium | DashMap |
| Arc-based value sharing | Memory efficiency | Low | Zero-copy on reads |
| Parallel batch loading | Startup optimization | Medium | tokio::join! |
| Rich error context | Better diagnostics | Low | `SettingsError` with path |

### Anti-Features (Do NOT Build)

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Settings writing/persistence | Python owns YAML writes | Read-only cache |
| Deep path navigation | Complex, error-prone | Return Yaml, caller navigates |
| Type conversion | Caller's responsibility | Return raw Yaml values |
| Schema validation | Out of scope | Let Python handle |
| Auto-reload on file change | Complexity, race conditions | Explicit invalidation |

### Dependencies on Existing Rust Components

| Dependency | Crate | Status |
|------------|-------|--------|
| YAML parsing | yaml-rust2 (v0.10.4) | Complete (external) |
| Async runtime | `classic-shared` (get_runtime) | Complete |
| DashMap cache | `classic-settings-core` (cache) | Complete |
| Error types | `classic-settings-core` (error) | Complete |

---

## Feature Dependencies Graph

```
Settings Management
        |
        v
  YAML Operations (classic-yaml-core)
        |
        +---> Game Detection (classic-path-core)
        |           |
        |           v
        |     Path Validation
        |           |
        +---> Scanning Orchestration (classic-scanlog-core)
                    |
                    +---> Log Parser
                    +---> Plugin Analyzer
                    +---> FormID Analyzer
                    +---> Mod Detector
                    +---> Suspect Scanner
                    +---> Settings Validator
                    +---> Record Scanner
                    |
                    v
              Report Generation
                    |
                    +---> ReportFragment
                    +---> ReportComposer
                    +---> StringPool
```

---

## MVP Recommendation

For MVP (minimum viable Rust migration), prioritize:

1. **Scanning Orchestration** (highest impact)
   - Rust `OrchestratorCore` is already 95% complete
   - Missing: VR auto-detection per-log, full Python API parity
   - Delivers 10-20x batch processing speedup

2. **Report Generation** (already complete)
   - `ReportGenerator`, `ReportComposer`, `ReportFragment` all implemented
   - Just needs Python wrapper updates to use Rust

3. **Settings Management** (already complete)
   - `classic-settings-core` fully functional
   - 15-30x speedup on YAML parsing

4. **Game Detection** (partially complete)
   - `GamePathFinder` in Rust works
   - Missing: Python wrapper integration

Defer to post-MVP:
- **Full feature parity testing**: Extensive behavioral parity validation
- **Performance benchmarking**: Detailed speed comparisons
- **GUI integration testing**: PySide6 interaction validation

---

## Gap Analysis

| Component | Rust Implementation | Python Wrapper | Integration Tests |
|-----------|---------------------|----------------|-------------------|
| Scanning Orchestration | 95% | 80% (HybridOrchestrator) | Partial |
| Game Detection | 90% | 50% (game_path.py uses it) | Minimal |
| Report Generation | 100% | 90% (report_rust.py) | Good |
| Settings Management | 100% | 70% (settings_rust.py) | Good |

### Remaining Work

1. **Scanning Orchestration**
   - Add VR auto-detection to Rust per-log processing
   - Complete `is_feature_complete()` checks
   - Full parity tests against Python output

2. **Game Detection**
   - Complete Python wrapper for `GamePathFinder`
   - Integration with GlobalRegistry
   - Error handling alignment

3. **Report Generation**
   - VR mode indicator in header
   - Ensure exact string parity with Python

4. **Settings Management**
   - Path write integration (settings saving stays Python)
   - Cache clear on settings update

---

## Sources

All findings based on direct codebase analysis:

- `ClassicLib/scanning/logs/orchestrator_core.py` (898 lines)
- `ClassicLib/scanning/game/orchestrator.py` (458 lines)
- `ClassicLib/scanning/logs/report_generator.py` (298 lines)
- `ClassicLib/support/game_path.py` (696 lines)
- `ClassicLib/integration/rust/settings_rust.py` (192 lines)
- `rust/business-logic/classic-scanlog-core/src/orchestrator.rs` (1507 lines)
- `rust/business-logic/classic-scanlog-core/src/report.rs` (665 lines)
- `rust/business-logic/classic-settings-core/src/lib.rs` (522 lines)
- `rust/business-logic/classic-path-core/src/game_path.rs` (534 lines)
- `.planning/PROJECT.md` (milestone context)
