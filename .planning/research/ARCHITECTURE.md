# Architecture Research

**Domain:** Hybrid Python-Rust codebase cleanup for progressive Rust migration
**Researched:** 2026-02-01
**Confidence:** HIGH (based on direct codebase analysis -- all findings verified against actual source files)

## System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                           │
│  │ GUI (Qt) │  │ CLI      │  │ TUI      │                           │
│  │ PySide6  │  │ asyncio  │  │ Textual  │                           │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                           │
│       │ sync+bridge  │ async       │ async                           │
├───────┴──────────────┴─────────────┴─────────────────────────────────┤
│                  INTEGRATION LAYER (Python)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐         │
│  │   factory/   │  │  detector    │  │  acceleration/     │         │
│  │  (dispatch)  │  │  (discover)  │  │  (coordination)    │         │
│  └──────┬───────┘  └──────┬───────┘  └────────┬───────────┘         │
│         │                 │                    │                     │
│    ┌────┴─────┐     ┌─────┴──────┐             │                     │
│    │ rust/    │     │ python/    │             │                     │
│    │ wrappers │     │ fallbacks  │             │                     │
│    └────┬─────┘     └─────┬──────┘             │                     │
├─────────┴─────────────────┴────────────────────┴─────────────────────┤
│                  BUSINESS LOGIC LAYER                                 │
│  ┌─────────────────────┐  ┌──────────────────────┐                   │
│  │ scanning/logs/      │  │ scanning/game/        │                  │
│  │ OrchestratorCore    │  │ GameFilesManager      │                  │
│  │ FormIDAnalyzer      │  │ ConfigFileCache        │                 │
│  │ ReportGenerator     │  │ SettingsScanner        │                 │
│  │ ModDetector         │  │ INI scanning           │                 │
│  └─────────┬───────────┘  └──────────┬────────────┘                  │
│            │                         │                               │
│  ┌─────────┴───────────┐  ┌──────────┴────────────┐                  │
│  │ support/            │  │ core/                  │                  │
│  │ game_path, xse,     │  │ AsyncBridge, Registry, │                 │
│  │ resources, update   │  │ constants, perf        │                 │
│  └─────────┬───────────┘  └──────────┬────────────┘                  │
├────────────┴─────────────────────────┴───────────────────────────────┤
│                  DATA ACCESS LAYER                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                           │
│  │ io/yaml  │  │ io/files │  │ io/db    │                           │
│  └──────────┘  └──────────┘  └──────────┘                           │
├──────────────────────────────────────────────────────────────────────┤
│                  RUST ENGINE                                         │
│  ┌──────────────────────────────────────────────────────────┐        │
│  │  python-bindings/ (-py crates, PyO3 cdylib adapters)     │        │
│  ├──────────────────────────────────────────────────────────┤        │
│  │  business-logic/  (-core crates, pure Rust rlib)         │        │
│  ├──────────────────────────────────────────────────────────┤        │
│  │  foundation/      (classic-shared-core, runtime, errors) │        │
│  └──────────────────────────────────────────────────────────┘        │
└──────────────────────────────────────────────────────────────────────┘
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

## Anti-Patterns

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

## Suggested Cleanup Order

The cleanup has dependency ordering constraints. Phases should proceed bottom-up through the stack.

### Phase 1: Dead Code Audit and Removal

**Dependency:** None (safe first step)

Tasks:
1. Identify which Rust crates are stubs vs. have real code
2. Remove stub crates from workspace (Phase 4/5 crates with no consumers)
3. Remove `ui-applications/` directory (empty)
4. Remove backward compatibility aliases (`_get_components`, `_is_rust_disabled`)
5. Audit `ClassicLib/Utils/` for overlap with Rust equivalents

**Build impact:** Fewer crates = faster compile times

### Phase 2: Integration Layer Simplification

**Dependency:** Phase 1 (know what's dead)

Tasks:
1. Flatten `factory/` subpackage to single `factory.py` module
2. Replace detector/cache system with try-import pattern
3. Remove `integration/config.py` (component constants)
4. Remove `integration/diagnostics.py` (runtime diagnostics)
5. Remove or heavily simplify `integration/status.py`
6. Remove `acceleration/` package entirely

**Build impact:** Fewer imports at startup, simpler call paths

### Phase 3: Wrapper Thinning

**Dependency:** Phase 2 (factory simplified first)

Tasks:
1. For each file in `integration/rust/`, measure: how much is type conversion vs. business logic?
2. Move business logic from fat wrappers into `-core` Rust crates
3. Reduce wrappers to thin adapters (target: <50 lines each)
4. Where wrappers become trivial, consider eliminating them (import PyO3 class directly)

**Build impact:** Rust rebuild required for moved logic. Most impactful phase.

### Phase 4: Interface Consolidation

**Dependency:** Phase 3 (wrappers thinned)

Tasks:
1. Remove all `_sync` method variants
2. Remove deprecated `FormIDAnalyzer.py` (keep only `FormIDAnalyzerCore.py`)
3. Consolidate `orchestrator_core.py` + `hybrid_orchestrator.py` (single orchestrator with optional Rust batch)
4. Remove dual executor patterns
5. Eliminate `util_legacy.py`

**Build impact:** API changes require test updates

### Phase 5: Python Fallback Pruning

**Dependency:** Phase 4 (interfaces consolidated)

Tasks:
1. For each `integration/python/*.py`: is the Rust equivalent always available in production?
2. Where YES: delete the Python fallback, simplify factory to direct Rust import
3. Where NO: keep fallback but document why
4. Target: reduce `integration/python/` from 8 files to 2-3 (only for components without stable Rust)

**Build impact:** Reduced code surface. Must verify Rust is reliable on all target platforms.

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
*Researched: 2026-02-01*
