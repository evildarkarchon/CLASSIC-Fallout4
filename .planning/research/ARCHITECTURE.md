# Architecture Research

**Domain:** Hybrid Python-Rust codebase cleanup for progressive Rust migration
**Researched:** 2026-02-01 (Updated: 2026-02-02)
**Confidence:** HIGH (based on direct codebase analysis -- all findings verified against actual source files)

## System Overview

```
+----------------------------------------------------------+
|                    Python Layer (UI)                      |
|  CLASSIC_Interface.py | CLASSIC_ScanLogs.py | Controllers |
+----------------------------------------------------------+
                            |
                            v
+----------------------------------------------------------+
|               Python Integration Layer                    |
|    ClassicLib/integration/factory.py (Protocol types)     |
|    ClassicLib/integration/rust/*.py (Thin wrappers)       |
+----------------------------------------------------------+
                            |
                            v
+----------------------------------------------------------+
|              Python Bindings (-py crates)                 |
|  classic-scanlog-py | classic-scangame-py | classic-*-py  |
|         PyO3 adapters, type conversions, GIL handling     |
+----------------------------------------------------------+
                            |
                            v
+----------------------------------------------------------+
|              Business Logic (-core crates)                |
|  classic-scanlog-core | classic-scangame-core | etc.      |
|            Pure Rust, NO PyO3, maximum performance        |
+----------------------------------------------------------+
                            |
                            v
+----------------------------------------------------------+
|                   Foundation Layer                        |
|   classic-shared-core (ONE RUNTIME, errors, utilities)    |
+----------------------------------------------------------+
```

### Component Responsibilities

| Component | Responsibility | Current Owner | Target Owner |
|-----------|----------------|---------------|--------------|
| `ClassicLib/integration/factory/` | Dispatch between Rust/Python implementations | Python | Python (permanent) |
| `ClassicLib/integration/rust/` | Python wrappers around Rust modules | Python | Shrink as Rust absorbs logic |
| `ClassicLib/integration/python/` | Python fallback implementations | Python | Remove where Rust is stable |
| `ClassicLib/scanning/logs/` | Crash log analysis pipeline | Python | Migrate to Rust `-core` |
| `ClassicLib/scanning/game/` | Game file integrity checking | Python | Migrate to Rust `-core` |
| `ClassicLib/support/` | Path detection, XSE, resources | Python | Migrate to Rust `-core` |
| `ClassicLib/core/` | Infrastructure (registry, bridge, perf) | Python | Keep Python for GUI bridge; Rust for registry/perf |
| `ClassicLib/io/` | File I/O, database, YAML access | Python | Already mostly Rust-accelerated |
| `ClassicLib/acceleration/` | Rust workload coordination | Python | Simplify or remove |
| `ClassicLib/messaging/` | Message routing | Python | Keep Python (GUI-facing) |
| `rust/business-logic/*-core/` | Pure Rust business logic | Rust | Expand (target for migration) |
| `rust/python-bindings/*-py/` | PyO3 thin adapters | Rust | Expand to match `-core` |
| `rust/foundation/` | Shared runtime, errors | Rust | Stable (no changes) |

---

## Migration Targets Integration Analysis

This section addresses how the four remaining migration targets should integrate with the existing Rust architecture.

### Migration Target 1: Scanning Orchestration

**Current Python Implementation:** `ClassicLib/scanning/logs/orchestrator_core.py`

**Existing Rust Support:**
- `classic-scanlog-core::orchestrator` provides `OrchestratorCore`, `AnalysisConfig`, `AnalysisResult`
- `HybridOrchestrator` already bridges Python and Rust
- Rust orchestrator handles batch processing with unbounded parallelism

**Current Data Flow:**
```
User Request
    |
    v
get_orchestrator() [factory.py]
    |
    v
HybridOrchestrator [hybrid_orchestrator.py]
    |
    +-- batch (>5 logs) --> Rust ClassicOrchestrator
    |                            |
    |                            v
    |                       classic_scanlog.Orchestrator
    |                            |
    |                            v
    |                       classic-scanlog-core::orchestrator
    |
    +-- single log ---------> Python OrchestratorCore
                                 |
                                 v
                            Per-analyzer pipeline (get_parser, get_formid_analyzer, etc.)
```

**Integration Strategy:**

The scanning orchestration is ALREADY substantially migrated. The key insight is:

1. **Rust `is_feature_complete()` check** determines if Rust can handle single-log processing
2. **Feature completeness requires:** Plugin analyzer + Suspect scanner + FormID analyzer
3. **Current gap:** Some analyzers still have significant Python logic

**Recommended Crate Changes:**

| Crate | Action | Purpose |
|-------|--------|---------|
| `classic-scanlog-core` | Enhance | Complete all analyzer implementations |
| `classic-scanlog-py` | Enhance | Expose remaining analyzers to Python |

**Python-Rust Boundary:**
```python
# factory.py - Keep existing pattern
def get_orchestrator(...) -> OrchestratorProtocol:
    return HybridOrchestrator(...)  # Bridges to Rust automatically
```

**No new crates needed.** Focus on completing feature parity in existing crates.

---

### Migration Target 2: Game Detection

**Current Python Implementation:** `ClassicLib/scanning/game/`
- `core.py` - `ScanGameCore` orchestrates all game scanning
- `orchestrator.py` - `GameIntegrityOrchestratorCore` coordinates integrity checks
- `checks/` - Individual scanners (BA2, INI, XSE, etc.)

**Existing Rust Support:**
- `classic-scangame-core` provides:
  - `BA2Scanner` - Archive scanning (COMPLETE)
  - `ConfigDuplicateDetector` - Config duplicate detection (COMPLETE)
  - `UnpackedScanner` - Unpacked mod scanning (COMPLETE)
  - `LogProcessor` - Error log processing (COMPLETE)
  - `IniValidator` - INI file validation (COMPLETE)
  - `CrashgenChecker` - Crashgen TOML validation (COMPLETE)
  - `XseChecker` - XSE plugin checking (COMPLETE)
  - `GameIntegrityChecker` - Game file integrity (COMPLETE)

**Current Data Flow:**
```
User Request (Check Game Files)
    |
    v
GameIntegrityOrchestratorCore.generate_game_combined_result_async()
    |
    +-- check_xse_plugins() --> Python (calls scangame_factory -> Rust)
    +-- check_crashgen_settings() --> Python (calls scangame_factory -> Rust)
    +-- check_log_errors() --> Python (calls scangame_factory -> Rust)
    +-- scan_wryecheck() --> Python
    +-- scan_mod_inis_async() --> Python (calls scangame_factory -> Rust)
    |
    v
Combined Report String
```

**Integration Strategy:**

Individual scanners are Rust-accelerated via `scangame_factory.py`. The Python orchestration layer (`GameIntegrityOrchestratorCore`) remains for:
- Progress reporting to GUI
- Error aggregation and formatting
- Async coordination

**Recommended Approach:**

**Option A (Conservative):** Keep Python orchestration, ensure all individual scanners use Rust
- Advantage: Minimal change, GUI integration stays simple
- Implementation: Complete `scangame_factory.py` wrappers

**Option B (Full Migration):** Create Rust orchestrator in `classic-scangame-core`
- Advantage: Maximum performance for batch game checks
- Implementation: New module `classic-scangame-core::orchestrator`

**Recommendation:** Option A for this milestone. Individual scanners are already Rust. The orchestration overhead is minimal compared to actual scanning work.

**Crate Structure (if Option B chosen later):**
```
rust/business-logic/classic-scangame-core/
    src/
        orchestrator.rs    # NEW: Coordinates all game scanners
        progress.rs        # NEW: Progress callback support

rust/python-bindings/classic-scangame-py/
    src/
        orchestrator.rs    # NEW: PyO3 bindings for orchestrator
```

---

### Migration Target 3: Report Generation

**Current Python Implementation:** `ClassicLib/scanning/logs/report_generator.py`
- `ReportGeneratorFragments` - Generates report sections
- Uses `ReportFragment` from Rust for storage

**Existing Rust Support:**
- `classic-scanlog-core::report` provides:
  - `ReportFragment` - Immutable report building block
  - `ReportComposer` - Fragment composition
  - `ReportGenerator` - Report section generation
  - `StringPool` - String interning for efficiency

**Current Data Flow:**
```
Report Generation Request
    |
    v
ReportGeneratorFragments (Python)
    |
    +-- generate_header() --> Returns ReportFragment (Rust storage)
    +-- generate_error_section() --> Returns ReportFragment
    +-- generate_suspect_section_header() --> Returns ReportFragment
    +-- generate_footer() --> Returns ReportFragment
    |
    v
ReportComposer (Rust) combines fragments
    |
    v
Final Report String
```

**Integration Strategy:**

The current boundary is APPROPRIATE:
- **Python decides WHAT to include** (business decisions, i18n, conditional sections)
- **Rust handles HOW to store/compose** (efficient fragment storage, string pooling)

**Recommended Approach:** Keep current pattern. The Python layer is thin (298 lines) and serves as a configuration point for report content.

**No new crates needed.** The existing `classic-scanlog-core::report` module is sufficient.

**Future Enhancement (post-cleanup):**
If report generation becomes a bottleneck (unlikely), move format string templates to Rust and expose via `classic-scanlog-py`. Python would pass parameters only.

---

### Migration Target 4: Settings Management

**Current Python Implementation:** `ClassicLib/io/yaml/async_/cache.py`
- `YamlCache` - YAML caching with TTL and metrics
- `ClassicLib/io/yaml/async_/core.py` - `yaml_settings_async` helper

**Existing Rust Support:**
- `classic-settings-core` provides:
  - `load_settings_sync/async` - File loading
  - `get_cached`, `is_cached` - Cache access
  - `load_batch_async` - Parallel loading
  - Lock-free DashMap storage

**Gap Analysis:**

| Feature | Python YamlCache | Rust classic-settings-core |
|---------|------------------|---------------------------|
| TTL-based expiration | Yes | No |
| File modification detection | Yes | No |
| Metrics tracking | Yes | No |
| Typed value extraction | Yes (helpers) | No |
| Multi-document support | Via ruamel | Yes (yaml-rust2) |
| Lock-free access | No (asyncio.Lock) | Yes (DashMap) |

**Integration Strategy:**

Two options:

**Option A: Enhance Rust, Deprecate Python**
1. Add metrics tracking to `classic-settings-core`
2. Add TTL/modification detection to Rust cache
3. Create typed extraction helpers in `classic-settings-py`
4. Deprecate Python `YamlCache`

**Option B: Parallel Systems (Current)**
- Python `YamlCache` for application settings
- Rust `classic-settings-core` for high-volume operations

**Recommendation:** Option A for full migration. The Rust cache already has superior concurrency (lock-free). Adding metrics is straightforward.

**Crate Enhancement:**
```rust
// classic-settings-core/src/metrics.rs (NEW)
pub struct CacheMetrics {
    pub cache_hits: AtomicU64,
    pub cache_misses: AtomicU64,
    pub file_reloads: AtomicU64,
    pub total_reads: AtomicU64,
}

// classic-settings-core/src/ttl.rs (NEW)
pub struct TtlEntry<T> {
    pub value: T,
    pub expires_at: Instant,
}
```

---

## Recommended Build Order

Based on dependency analysis:

### Phase 1: Complete Existing Crates (Week 1-2)

No new crates. Enhance existing:

1. **classic-settings-core** - Add metrics, TTL, typed extraction
2. **classic-scanlog-core** - Ensure all analyzers are feature-complete
3. **classic-message-core** - Complete message routing if needed

Dependencies:
```
classic-settings-core <- classic-shared-core
classic-scanlog-core <- classic-shared-core, classic-yaml-core, classic-file-io-core
```

### Phase 2: Factory Simplification (Week 2-3)

Simplify Python integration layer:

4. Update `factory.py` - Direct imports where Rust is stable
5. Thin out `integration/rust/*.py` wrappers
6. Remove detection infrastructure

### Phase 3: Integration Validation (Week 3-4)

7. Add Protocol types to `types.py` if missing
8. Test all factory paths
9. Verify fallback behavior

### Phase 4: Optional Full Game Orchestrator (Future)

Only if profiling shows need:

10. Create `classic-scangame-core::orchestrator` (if Option B chosen)
11. Add PyO3 bindings

---

## New vs. Modified Components Summary

### Components to Modify (NOT Create)

| Component | Modification |
|-----------|--------------|
| `classic-settings-core` | Add metrics, TTL, typed extraction |
| `classic-settings-py` | Expose new features |
| `classic-scanlog-core` | Complete analyzer implementations |
| `classic-scanlog-py` | Expose remaining analyzers |
| `factory.py` | Simplify to direct imports |
| `integration/rust/*.py` | Thin out wrappers |

### Components That Are Already Complete

| Component | Status |
|-----------|--------|
| `classic-scangame-core` | All individual scanners implemented |
| `classic-scangame-py` | Bindings complete |
| `classic-scanlog-core::report` | Report fragment system complete |
| `classic-shared-core` | Foundation stable |

### Components to Possibly Create (Optional, Future)

| Component | Condition |
|-----------|-----------|
| `classic-scangame-core::orchestrator` | Only if game scanning orchestration becomes bottleneck |

---

## Current Boundary Analysis

### The Four-Layer Integration Stack (Problem Area)

The current Rust integration has grown into a four-layer stack between callers and Rust code:

```
Caller (GUI/CLI)
  -> factory/ (decides Rust or Python)
    -> rust/ wrapper (Python class around PyO3 import)
      -> -py crate (PyO3 #[pyclass] adapter)
        -> -core crate (pure Rust logic)
```

**Layers 1 and 2 are the consolidation target.** The `rust/` wrappers in `ClassicLib/integration/rust/` are often substantial Python files (e.g., `file_io_rust.py` at 39KB, `parser_rust.py` at 15KB, `formid_rust.py` at 16KB) that add Python-side logic on top of Rust calls. This is the inverse of the target state -- Python should be getting thinner, not fatter.

### Dual Implementation Inventory

Every component currently has both a Rust and Python implementation. The factory decides which to use at runtime.

| Component | Python impl (`python/`) | Rust wrapper (`rust/`) | Status |
|-----------|------------------------|----------------------|--------|
| Parser | `parser_py.py` (8KB) | `parser_rust.py` (15KB) | Rust wrapper is larger than Python impl |
| FormID | `formid_py.py` (12KB) | `formid_rust.py` (16KB) | Rust wrapper has extra Python logic |
| Plugin | `plugin_py.py` (13KB) | `plugin_rust.py` (15KB) | Near parity |
| Record | `record_py.py` (7KB) | `record_rust.py` (14KB) | Rust wrapper 2x Python |
| Report | `report_py.py` (11KB) | `report_rust.py` (1KB) + `report/` dir | Split across files |
| ModDetector | `mod_detector_py.py` (12KB) | `mod_detector_rust.py` (11KB) | Near parity |
| Database | `database_py.py` (14KB) | `database_rust.py` (2KB) | Rust wrapper is thin (good) |
| FileIO | `file_io_py.py` (18KB) | `file_io_rust.py` (39KB) | Rust wrapper is 2x Python -- inverted |

**Key finding:** The `rust/` wrappers should be thin adapters but several have grown to contain significant Python business logic. This defeats the purpose of Rust acceleration and creates a maintenance burden where changes must happen in both the Python wrapper AND the Rust core.

### Crate Proliferation Assessment

The workspace has **21 business-logic crates** and **18 python-bindings crates** (39 total). Several crate pairs appear to be stubs created during planning phases:

| Crate Group | Purpose | Likely Status |
|-------------|---------|---------------|
| yaml, database, file-io, scanlog, config, scangame | Original set | Mature, has real code |
| registry, perf, pybridge, settings, message | Phase 1 infra | Has code, partially used |
| path | Phase 2 | Has code |
| constants, version, resource, xse, web | Phase 4 utilities | Likely stubs or minimal |
| update | Phase 5 | Likely stub |
| version-registry | Standalone | Unknown maturity |

**Recommendation:** Audit each crate for actual code vs. stubs. Remove stubs that have no consumers. Do not create new crates during cleanup.

---

## Architectural Patterns

### Pattern 1: Strangler Fig for Python-to-Rust Migration

**What:** Gradually replace Python implementations with Rust by routing through the factory pattern, then removing the Python fallback once Rust is proven stable.

**When to use:** For each component where Rust `-core` has feature parity with the Python implementation.

**How it works in this codebase:**

```
Phase A (current): Factory dispatches to either Python or Rust
Phase B (cleanup): Identify components where Rust always wins
Phase C (removal): Delete Python fallback, simplify factory to direct import
Phase D (future): Move remaining logic from rust/ wrappers into -core crates
```

**Trade-offs:**
- Pro: Zero risk of breaking production -- always has fallback
- Pro: Can be done one component at a time
- Con: Must maintain both implementations until removal
- Con: Factory indirection adds complexity

**Recommendation for cleanup:** Phase B is the immediate target. For each component, determine: is the Python fallback ever actually exercised? If Rust is always available in production, the fallback is dead code.

### Pattern 2: Wrapper Thinning

**What:** Move business logic OUT of `ClassicLib/integration/rust/` wrappers and INTO the Rust `-core` crates, leaving only type conversion in the `-py` crate.

**When to use:** When a Rust wrapper file is larger than the Python fallback it replaces (signals logic has leaked into the wrong layer).

**Example -- current problem in `file_io_rust.py` (39KB):**

```python
# BAD: Python logic in the Rust wrapper
class FileIOCore:
    async def read_file_with_encoding(self, path, encoding):
        # 200 lines of Python error handling, retry logic, fallback chains
        try:
            result = self._rust_core.read_file(str(path))
        except RustError:
            # Complex Python recovery logic
            ...
```

**Target state:**

```python
# GOOD: Thin adapter, all logic in Rust
class FileIOCore:
    async def read_file_with_encoding(self, path, encoding):
        return self._rust_core.read_file(str(path), encoding)
```

**Trade-offs:**
- Pro: Single source of truth for business logic (Rust)
- Pro: Python layer becomes trivially simple
- Con: Requires Rust feature parity before thinning
- Con: Rust changes require rebuild (slower iteration)

### Pattern 3: Interface Consolidation (Async-Only)

**What:** Remove sync wrappers and dual-interface patterns. Everything async. Wrap at entry points only.

**When to use:** Everywhere. The dual sync/async pattern is documented tech debt.

**Current problem:**

```python
# FormIDAnalyzer has both:
async def analyze_segment(self, ...):  # Primary
def analyze_segment_sync(self, ...):   # "GUI-only" but callable anywhere
```

**Target state:**

```python
# One interface, always async
async def analyze_segment(self, ...):
    ...

# At GUI entry point only:
bridge.run_async(analyzer.analyze_segment(...))
```

### Pattern 4: Factory Simplification Ladder

**What:** Progressively simplify the factory as Rust becomes the default.

**Stages:**

```
Stage 1 (now):    factory checks detection cache, imports conditionally
Stage 2 (cleanup): factory imports Rust directly, catches ImportError only
Stage 3 (future):  factory becomes a re-export module (no logic)
Stage 4 (end):     factory removed, callers import Rust directly
```

**For cleanup milestone, target Stage 2:**

```python
# Stage 2: Direct import with simple fallback
def get_parser(yamldata):
    try:
        from classic_scanlog import LogParser
        return LogParser(yamldata)
    except ImportError:
        from ClassicLib.integration.python.parser_py import LogParser
        return LogParser(yamldata)
```

This eliminates the detection cache, component config map, and multi-layer indirection.

---

## Data Flow

### Current Crash Log Processing Flow

```
CLI Entry (asyncio.run)
    |
    v
ScanLogsExecutor
    |
    v
get_orchestrator() [factory]
    |
    +-- Rust available? --> HybridOrchestrator
    |                           |
    |                           +-- batch (5+ logs) --> Rust ClassicOrchestrator
    |                           +-- single log ------> Python OrchestratorCore
    |
    +-- No Rust -----------> Python OrchestratorCore
                                |
                                v
                        Per-log analysis pipeline:
                        get_parser() -> parse crash log
                        get_formid_analyzer() -> extract FormIDs
                        get_plugin_analyzer() -> check plugins
                        get_record_scanner() -> scan records
                        get_suspect_scanner() -> flag suspects
                        get_settings_validator() -> validate INIs
                        get_report_generator() -> compose report
                                |
                                v
                        Report written to file + DB updated
```

### Data Flow Direction After Cleanup

The cleanup should establish a clear downward flow:

```
Presentation (Python only)
    |  calls async methods
    v
Business Logic Interface (Python, thin)
    |  delegates to Rust via PyO3
    v
Rust Engine (-core crates)
    |  pure Rust operations
    v
Data Access (Rust for perf, Python for platform specifics)
```

**Key principle:** Data should flow DOWN through the layers. No upward callbacks from Rust into Python business logic. The current `rust/` wrappers violate this by adding Python logic between the factory and the Rust engine.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Fat Rust Wrappers

**What people do:** Put Python business logic in `ClassicLib/integration/rust/*.py` files that are supposed to be thin adapters around Rust.

**Why it's wrong:** Creates a third location for business logic (alongside `python/` fallbacks and `-core` crates). Changes require coordination across three files. The wrapper becomes the actual implementation, with Rust only used for hot inner loops.

**Do this instead:** If logic needs to exist in Python, put it in `python/` fallback. If it should be in Rust, put it in `-core`. The `rust/` wrapper should only do: import PyO3 class, adapt types, return result.

### Anti-Pattern 2: Defensive Over-Detection

**What people do:** Build elaborate detection, caching, health-check, and diagnostics infrastructure around Rust availability (detector.py at 370+ lines, config.py with 25 component constants, acceleration/coordinator.py at 670+ lines).

**Why it's wrong:** For a desktop app with controlled deployment, Rust is either compiled in or it's not. The detection infrastructure is proportionate to a microservices deployment, not a desktop tool.

**Do this instead:** Try-import at factory level. If ImportError, fall back. That's it. Remove the detection cache, component config registry, health checks, performance thresholds, and component categories. All of that is dead weight for a desktop app.

### Anti-Pattern 3: Parallel Implementation Maintenance

**What people do:** Maintain both `python/formid_py.py` AND `rust/formid_rust.py` AND `classic-scanlog-core` FormID logic. Three implementations of the same concept.

**Why it's wrong:** Triple maintenance burden. Bugs fixed in one may not be fixed in others. Feature drift between implementations.

**Do this instead:** Pick one owner per component. If Rust is stable and always available, delete the Python fallback. If Rust is not ready, keep Python as primary and don't wrap a partial Rust implementation.

### Anti-Pattern 4: Abstraction Layering for Future Flexibility

**What people do:** Create `acceleration/` coordination package with workload optimization, component metrics, optimization levels -- "in case we need it later."

**Why it's wrong:** YAGNI. A desktop crash log scanner does not need workload-aware optimization routing. The overhead of the abstraction exceeds the benefit.

**Do this instead:** Direct factory dispatch. If profiling later shows a need for batch vs. single optimization, add it then with actual measurements.

---

## Recommended Project Structure After Cleanup

```
ClassicLib/
├── core/                    # Infrastructure (keep, simplify)
│   ├── async_bridge.py      # GUI-only sync bridge (keep)
│   ├── constants.py         # App constants (keep)
│   ├── registry.py          # GlobalRegistry (keep, consider Rust migration)
│   └── performance.py       # Perf monitoring (keep, simplify)
│
├── integration/             # Rust/Python dispatch (simplify heavily)
│   ├── factory.py           # Single file, try-import pattern (flatten from factory/)
│   ├── python/              # Python fallbacks (shrink as Rust matures)
│   └── exceptions.py        # Rust error types (keep)
│   # REMOVED: rust/ wrappers, detector.py, config.py, diagnostics.py
│   # REMOVED: acceleration/ package (coordinator, metrics, workload, types)
│   # REMOVED: scangame_factory.py, status.py
│
├── scanning/                # Business logic (keep, thin out)
│   ├── logs/                # Crash log pipeline
│   └── game/                # Game integrity checks
│
├── support/                 # Path detection, XSE, resources (keep)
│
├── io/                      # Data access (keep, already clean)
│   ├── yaml/
│   ├── files/
│   └── database/
│
├── messaging/               # Message routing (keep)
│
├── Interface/               # Qt GUI (keep, no changes this milestone)
│
├── TUI/                     # Textual TUI (keep, in development)
│
└── Utils/                   # Utility functions (audit for overlap with Rust)
```

### Structure Rationale

- **`integration/factory/` flattened to `integration/factory.py`**: The 8-file factory subpackage with its core.py, analyzers.py, parsers.py, etc. can be a single module. Each factory function is 15-30 lines. Total: ~300 lines in one file.
- **`integration/rust/` removed**: Fat wrappers absorbed -- logic goes to `-core` crates or stays in `python/` fallbacks. The `-py` PyO3 crates become the direct import target.
- **`integration/detector.py` removed**: Detection is "try import" at the factory level. No need for a 370-line detection framework.
- **`acceleration/` removed**: Workload coordination for a desktop app is over-engineering. Direct dispatch suffices.
- **`integration/config.py` removed**: 25 component constant definitions with performance multiplier strings serve no runtime purpose.

---

## Integration Points

### Python-Rust Boundary (Critical)

| Boundary | Current Pattern | Target Pattern |
|----------|-----------------|----------------|
| Factory -> Rust module | factory -> rust/ wrapper -> PyO3 class | factory -> PyO3 class directly |
| Type conversion | In rust/ wrapper (Python) | In -py crate (Rust/PyO3) |
| Error handling | Python try/except around Rust calls | Rust errors mapped to Python exceptions in -py |
| Async bridging | AsyncBridge for GUI, asyncio for CLI | Same (this is correct) |
| Configuration | Python loads YAML, passes to Rust | Same initially; migrate to Rust YAML loading later |

### Internal Module Boundaries

| Boundary | Communication | Cleanup Notes |
|----------|---------------|---------------|
| scanning/logs <-> integration/factory | Factory returns impl instance | Keep; this is the right abstraction |
| scanning/logs <-> io/ | Direct import for DB, file ops | Keep; clean boundary |
| core/ <-> everything | Import constants, registry, bridge | Keep; foundation layer is correct |
| support/ <-> scanning/ | Support provides paths, scanning uses them | Keep; may consolidate some path logic |
| messaging/ <-> everything | MessageHandler called from all layers | Keep; central messaging is correct |
| acceleration/ <-> integration/ | Coordinator wraps factory | Remove; unnecessary indirection |

---

## Ownership Migration Strategy

The end state is "Rust is the engine, Python is GUI/glue." The cleanup establishes clear ownership:

### Immediate (Cleanup Milestone)
- **Rust owns:** YAML parsing, database ops, file I/O, log parsing, batch orchestration
- **Python owns:** GUI, CLI args, TUI, async bridging, message display, report formatting
- **Disputed (resolve during cleanup):** FormID analysis, plugin analysis, mod detection, settings validation

### Future (Post-Cleanup Migration)
- **Rust expands to own:** FormID, plugin, mod detection, settings, game path resolution, XSE checks
- **Python shrinks to:** GUI shell, CLI entry point, TUI, configuration loading, user interaction

### How to Handle Fallback During Cleanup

**Policy:** Keep fallbacks for components where Rust is not yet proven stable on all platforms. Remove fallbacks where Rust has been shipping reliably.

**Decision criteria per component:**
1. Has the Rust implementation been shipping in production? If yes for 3+ months, safe to remove fallback.
2. Are there known platforms where Rust fails? If yes, keep fallback.
3. Is the Python fallback actually tested? If not, it's false safety -- remove it.

**During cleanup:** Add a `CLASSIC_REQUIRE_RUST=1` environment variable (opt-in) that errors instead of falling back. Use this in CI to catch fallback triggers.

---

## Sources

- Direct codebase analysis of `J:\CLASSIC-Fallout4\` (all findings verified against source files)
- `J:\CLASSIC-Fallout4\.planning\codebase\ARCHITECTURE.md` -- existing architecture mapping
- `J:\CLASSIC-Fallout4\.planning\codebase\CONCERNS.md` -- existing concerns audit
- `J:\CLASSIC-Fallout4\.planning\PROJECT.md` -- project scope definition
- `J:\CLASSIC-Fallout4\docs\development\rust_workspace_architecture.md` -- Rust workspace docs
- `J:\CLASSIC-Fallout4\rust\Cargo.toml` -- workspace manifest
- PyO3 documentation (training data, MEDIUM confidence for version-specific claims)
- Strangler Fig pattern (Martin Fowler, well-established architectural pattern)

---
*Architecture research for: CLASSIC hybrid Python-Rust codebase cleanup*
*Researched: 2026-02-01, Updated: 2026-02-02*
