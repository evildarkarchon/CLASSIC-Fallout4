# Pitfalls Research

**Domain:** Hybrid Python-Rust codebase cleanup and consolidation
**Researched:** 2026-02-01
**Confidence:** HIGH (based on codebase analysis docs, not external sources)

## Critical Pitfalls

### Pitfall 1: Removing "Dead" Python Fallbacks That Are Active in Deployed Builds

**What goes wrong:**
A Python fallback implementation appears dead because Rust is always available in the dev environment. The cleanup deletes it. But in deployed PyInstaller builds, Rust extension loading can fail silently (DLL not found, ABI mismatch, missing redistributable on user machine). The factory pattern returns the Python fallback -- which no longer exists. The app crashes on launch for some users while working perfectly for the developer.

**Why it happens:**
The factory pattern in `ClassicLib/integration/factory/` caches Rust component availability at startup. In development, Rust modules are always built and available. The developer never exercises the fallback path. There is no CI matrix testing "Rust unavailable" mode. The Python fallback code looks dead because `detect_rust_components()` always returns `True` for everything.

**How to avoid:**
1. Before removing any Python fallback, verify by running the full test suite with `CLASSIC_DISABLE_RUST=1` environment variable (the `is_rust_disabled()` check in `factory/core.py` supports this).
2. For each factory function (`get_parser()`, `get_file_io()`, `get_database_pool()`, etc.), explicitly decide: "Is this fallback still needed?" Document the answer.
3. If a fallback IS removed, the factory function must raise a clear error ("Rust module X required but not found") instead of silently returning None or crashing with ImportError.
4. Test the PyInstaller build without Rust extensions present to verify error messages are user-friendly.

**Warning signs:**
- Factory functions that import both Rust and Python implementations but Python side has no recent test coverage
- `detect_rust_components()` returns all-True in every test run
- No tests marked with `CLASSIC_DISABLE_RUST=1` or mocking Rust unavailability

**Phase to address:**
Inventory/audit phase (first phase). Before removing anything, catalog which fallbacks are exercised and which are truly dead.

---

### Pitfall 2: Breaking PyInstaller Hidden Imports When Renaming or Moving Modules

**What goes wrong:**
A module is moved, renamed, or consolidated during cleanup. Python tests pass because pytest uses direct imports. But PyInstaller bundles based on `hiddenimports` in `CLASSIC.spec` and the `pyinstaller_rust_helper`. The renamed module is not in the bundle. The app crashes at runtime with `ModuleNotFoundError` -- but only in the distributed executable, not in development.

**Why it happens:**
`CLASSIC.spec` hardcodes module paths like `ClassicLib.rust_loader`, `ClassicLib.integration.factory`, and every Rust binding name. The `collect_all()` calls for PySide6 and Textual also depend on the import graph being intact. When modules are moved or merged, the spec file and hidden import list become stale. PyInstaller's analysis only traces `import` statements it can find statically -- lazy imports, factory patterns, and `importlib` calls are invisible to it.

**How to avoid:**
1. Maintain a checklist: every module rename/move must update `CLASSIC.spec` hidden imports.
2. After any cleanup phase, do a test PyInstaller build (`uv run pyinstaller --clean CLASSIC.spec`) and verify the executable launches.
3. Treat the `CLASSIC.spec` file as a first-class artifact that must be updated in the same commit as any module restructuring.
4. The `pyinstaller_rust_helper.find_rust_extensions()` scans for `.pyd`/`.so` files -- if Rust crate names change, this helper must be updated too.

**Warning signs:**
- Module renames that do not touch `CLASSIC.spec` in the same commit
- `hiddenimports` list in spec file references modules that no longer exist
- Nobody has done a PyInstaller build in the current cleanup cycle

**Phase to address:**
Every phase that moves or renames modules. Add "PyInstaller build test" as a phase gate for any structural cleanup phase.

---

### Pitfall 3: Singleton State Leaks Across Cleanup Boundaries

**What goes wrong:**
During cleanup, singletons (GlobalRegistry, MessageHandler, AsyncBridge, `_components_cache` in factory/core.py) accumulate stale state references to removed or restructured code. Tests pass individually but fail in batch. Or worse, tests pass but the singletons hold references to old module paths, causing subtle runtime bugs.

**Why it happens:**
CLASSIC uses at least four singletons with module-level mutable state:
- `GlobalRegistry` (class-level dict)
- `MessageHandler` (singleton)
- `AsyncBridge._instances` (thread-local dict)
- `_components_cache` in `ClassicLib/integration/factory/core.py` (module-level dict)
- `_VERSION_WARNING_LOGGED` in `ClassicLib/support/game_path.py` (module-level bool)

When cleanup changes what these singletons reference (e.g., moving a message backend, restructuring the registry), the cached state becomes stale. CONCERNS.md already documents that `_VERSION_WARNING_LOGGED` is fragile in tests. The `_components_cache` caches Rust availability once -- if a factory is restructured, the cache does not know.

**How to avoid:**
1. Reset ALL singleton state between test runs. The existing `reset_cache()` in factory/core.py is a good pattern -- extend it to all singletons.
2. During cleanup, if a singleton's interface changes, grep for all call sites. Singletons are referenced everywhere and don't show up in import graphs.
3. Consider adding a `reset_all_singletons()` test fixture that is `autouse=True` for the entire test suite.
4. When consolidating singletons (e.g., merging GlobalRegistry with another registry), do it in a single atomic step with all tests updated.

**Warning signs:**
- Tests pass individually (`pytest tests/path/to/test.py`) but fail in batch (`pytest -n auto`)
- Test order affects results (classic singleton contamination)
- Module-level mutable variables (`global` keyword in function body)

**Phase to address:**
First phase (inventory) should catalog all singletons. Singleton cleanup should be its own focused step, not mixed with other refactoring.

---

### Pitfall 4: Breaking the Async/Sync Boundary During Sync Wrapper Removal

**What goes wrong:**
The cleanup removes deprecated sync wrappers (as recommended in CONCERNS.md for FormIDAnalyzer). But some call site deep in the GUI layer was using the sync wrapper from a QThread worker context where `await` is not available and `asyncio.run()` would conflict with the existing event loop. The GUI freezes or deadlocks.

**Why it happens:**
CLASSIC has a complex async model:
- CLI: native `asyncio.run()` at entry point
- GUI: Qt event loop + AsyncBridge for sync-to-async
- Workers: QThread with AsyncBridge (thread-local instances)
- Rust: Tokio runtime (single global)

The sync wrappers exist because some GUI code paths cannot use `await`. Removing them requires understanding which call sites need AsyncBridge and which are already async. The CONCERNS.md notes: "No tests verify sync wrappers aren't called in CLI/TUI mode." This means the usage map is incomplete.

**How to avoid:**
1. Before removing any sync wrapper, trace ALL call sites using grep. Pay special attention to `ClassicLib/Interface/workers/` and `ClassicLib/Interface/controllers/`.
2. For each call site, determine the execution context: Is it in a QThread? Is it in the Qt main thread? Is it in an async context?
3. Replace sync wrappers with the appropriate async pattern for each context:
   - QThread workers: `AsyncBridge.run_async(coro)`
   - Qt main thread slots: `qasync` integration
   - CLI/TUI: direct `await`
4. Test GUI functionality manually after each sync wrapper removal. Deadlocks are not caught by unit tests.

**Warning signs:**
- Sync wrapper removal PR that only updates unit tests, not integration tests
- No GUI testing (manual or automated) after removing sync code
- AsyncBridge `run_async` calls that were previously sync wrapper calls -- verify the caller is actually in a sync context

**Phase to address:**
Dual interface consolidation phase. This should be a dedicated phase, not mixed with dead code removal, because the failure mode (deadlock) is invisible to automated tests.

---

### Pitfall 5: Removing Rust Crates That Are Depended On Through Cargo Workspace Features

**What goes wrong:**
A Rust `-core` crate appears unused (no Python binding imports it directly). It is removed from `Cargo.toml` workspace members. But another `-core` crate depends on it via `[dependencies]`. The entire Rust workspace fails to build. Or worse, the dependency was optional and the build succeeds but a feature is silently disabled.

**Why it happens:**
The workspace has 19 business-logic crates and matching Python binding crates. The dependency graph between `-core` crates is not obvious from the workspace member list. For example, `classic-scanlog-core` likely depends on `classic-yaml-core` for reading configuration, and `classic-scangame-core` may depend on `classic-path-core`. Removing a crate that looks unused from the Python side can break the Rust side.

**How to avoid:**
1. Before removing any Rust crate, run `cargo tree -p classic-<name>-core --invert` to see what depends on it.
2. Run `cargo build --workspace` after every crate removal to verify the workspace is intact.
3. Check both the `-core` and `-py` crate for each removal -- the `-py` crate may re-export types from `-core` that other `-py` crates use.
4. Look at `[workspace.dependencies]` in the root `Cargo.toml` -- removing a crate from `members` does not remove its entry from workspace deps, which can cause confusing errors.

**Warning signs:**
- Crate removed from workspace members but `cargo build` not run before committing
- `Cargo.lock` changes that remove transitive dependencies unexpectedly
- `-py` crate that wraps a `-core` crate where the `-core` crate is being removed

**Phase to address:**
Rust cleanup phase (should be separate from Python cleanup). Rust crate dependencies form a graph that needs analysis before removal.

---

### Pitfall 6: Consolidating Overlapping Abstractions Breaks the Integration Layer Contract

**What goes wrong:**
Two abstractions that appear redundant (e.g., `FileIOCore` Python + `classic_file_io` Rust) are merged into one. But the factory pattern in `ClassicLib/integration/factory/file_io.py` expects a specific interface -- method names, parameter signatures, return types. The consolidated version has a slightly different interface. The factory returns an object that does not match what callers expect.

**Why it happens:**
The Rust and Python implementations of the same concept often have subtly different APIs. The Python version might return `pathlib.Path`, the Rust version returns `str`. The Python version might be async, the Rust version sync. The factory normalizes this -- but the normalization logic is in the factory function, not in the implementations. When you consolidate, you lose the normalization.

**How to avoid:**
1. Document the interface contract for each factory function BEFORE consolidating. What methods? What signatures? What return types?
2. Use Python Protocol classes (typing.Protocol) to define the interface, then verify both implementations satisfy it.
3. When consolidating, update the factory function and all callers in the same PR. Do not leave the factory pointing at a half-migrated implementation.
4. Run integration tests (not just unit tests) after consolidation -- the factory/caller interaction is an integration boundary.

**Warning signs:**
- Factory function updated without updating callers
- Return type changes (e.g., `str` to `Path`, sync to async) without updating all consumers
- Tests that mock the factory return value (these tests pass even when the real factory is broken)

**Phase to address:**
Abstraction flattening phase. This needs careful interface documentation before any merging begins.

---

### Pitfall 7: Lazy YAML Import Discipline Breaks During Module Consolidation

**What goes wrong:**
CLAUDE.md rule 8 states: "Lazy YAML imports -- Import `yaml_settings`, `classic_settings` inside functions to avoid circular imports." During cleanup, modules are merged or moved. The developer adds a top-level import of YAML settings in the consolidated module because it looks cleaner. Circular import chain triggers at startup. Application fails to launch.

**Why it happens:**
CLASSIC's YAML configuration system is loaded eagerly during `SetupCoordinator.initialize_application()`. Many modules need YAML settings, but the YAML module itself depends on core infrastructure that depends on other modules that need settings. The lazy import pattern breaks this cycle. During cleanup, the "why" behind lazy imports is not obvious -- it looks like sloppy code that should be cleaned up.

**How to avoid:**
1. Add a comment on every lazy YAML import: `# Lazy import: circular dependency with ClassicLib.io.yaml`
2. During cleanup, if two modules with lazy imports are merged, keep the lazy import pattern even if it looks redundant.
3. Test startup (not just individual module tests) after any module consolidation: `uv run python -c "from ClassicLib import ..."` to verify no circular imports.
4. Consider creating a `LAZY_IMPORTS.md` document listing all intentional lazy imports and why they exist, so cleanup does not accidentally "fix" them.

**Warning signs:**
- `ImportError` or `AttributeError` at startup that was not present before cleanup
- Module consolidation PR that converts lazy (function-level) imports to module-level imports
- Circular import errors only visible when running the actual application, not in isolated tests

**Phase to address:**
Any phase that moves or consolidates Python modules. This is a cross-cutting concern, not a single phase.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems during cleanup.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Removing code without tracing all callers | Faster cleanup | Runtime crashes in untested paths | Never during cleanup of a production app |
| Skipping PyInstaller build verification | Saves 5-10 minutes per change | Broken release build discovered late | Never -- build verification is non-negotiable |
| Updating tests to pass without understanding why they broke | Green CI faster | Masks real breakage, false confidence | Never -- broken tests mean the refactoring is wrong |
| Removing sync wrappers without GUI testing | Simplifies code quickly | Deadlocks in GUI that only show under load | Never for GUI-affecting changes |
| Cleaning Python and Rust in the same commit | Fewer commits | Impossible to bisect if something breaks | Only for trivially coupled changes (e.g., removing a stub + its binding) |

## Integration Gotchas

Common mistakes when changing the Python-Rust boundary during cleanup.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| PyO3 bindings (`.pyi` stubs) | Removing or renaming a Python-side module without updating the `.pyi` type stub for the Rust binding | Update `.pyi` stubs in the same commit as any interface change; run `pyright` to verify |
| Factory pattern | Changing a Rust module's Python API without updating the factory fallback | Test with `CLASSIC_DISABLE_RUST=1` after any Rust API change |
| `classic_shared::get_runtime()` | Creating a second Tokio runtime during refactoring of async code | grep for `tokio::runtime::Runtime::new` -- there should be exactly one, in classic-shared-core |
| PyInstaller Rust bundling | Moving `.pyd` files or renaming crates without updating `pyinstaller_rust_helper` | Run `find_rust_extensions()` manually and verify it finds all expected modules |
| `_components_cache` | Not calling `reset_cache()` in test fixtures after changing detector behavior | Add `reset_cache()` to test setup for any test touching the integration layer |

## Performance Traps

Patterns that work at small scale but fail during cleanup verification.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Running full test suite after every small cleanup change | Test runs take 5+ minutes, developer starts skipping tests | Use `pytest -m "unit and not slow"` for fast feedback; full suite as phase gate only | When cleanup changes span 20+ files |
| `cargo build --workspace` on every Rust change | 2-5 minute incremental builds on Windows | Use `cargo check` for quick verification; full build at phase end | When touching Cargo.toml workspace config |
| PyInstaller rebuild after every Python change | 3-10 minute builds | Only rebuild at phase boundaries or when module structure changes | When cleanup is module-level restructuring |

## UX Pitfalls

Common mistakes that affect end users during cleanup of a user-facing tool.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Changing log output format during "cleanup" | Users who parse CLASSIC output with scripts break | Treat output format as API -- no changes unless explicitly decided |
| Renaming CLI arguments for "consistency" | Users' batch scripts and shortcuts break | CLI arguments are user-facing API -- deprecate, do not rename |
| Changing crash report markdown format | Users familiar with report layout are confused | Report format is a feature -- changes require explicit decision |
| Removing "redundant" error messages that users rely on for debugging | Users lose diagnostic information | Before removing any user-visible message, verify it is not documented in community guides |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces during cleanup.

- [ ] **Dead code removal:** Module deleted but still referenced in `CLASSIC.spec` hidden imports -- verify spec file is updated
- [ ] **Sync wrapper removal:** Wrapper deleted but AsyncBridge call site not updated in GUI worker -- verify all GUI paths manually
- [ ] **Factory consolidation:** Factory updated but `.pyi` type stubs still reference old interface -- run `pyright` strict mode
- [ ] **Rust crate removal:** Crate removed from workspace but still in another crate's `[dependencies]` -- run `cargo build --workspace`
- [ ] **Import cleanup:** Module-level import replaces lazy import, works in tests, circular import in production -- test with `uv run python CLASSIC_Interface.py` and `uv run python CLASSIC_ScanLogs.py`
- [ ] **Test fixture cleanup:** Fixture removed but another fixture depended on it via conftest chain -- run `pytest --collect-only` to verify all tests are discoverable
- [ ] **Singleton cleanup:** Singleton interface changed but test reset fixtures not updated -- run full suite with `pytest -n auto` (parallel catches state leaks)

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Broken PyInstaller build | LOW | Revert module rename, update spec, rebuild. Git bisect to find breaking commit. |
| Deadlocked GUI after sync removal | MEDIUM | Revert sync wrapper removal. Map all call sites more carefully. Reapply with correct AsyncBridge calls. |
| Circular import from lazy import cleanup | LOW | Revert to lazy import. Add comment explaining why. |
| Broken Rust workspace | LOW | `cargo build --workspace` error message identifies the missing dep. Re-add crate or update dependents. |
| Singleton state corruption in tests | MEDIUM | Add `autouse=True` reset fixture. May need to audit all test files for implicit singleton usage. |
| Removed fallback causes user crashes | HIGH | Emergency release with fallback restored. Requires understanding which users are affected (those without Rust extensions). |
| Factory contract broken | MEDIUM | Add Protocol class defining the interface. Update both implementations to match. Run integration tests. |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Removing active Python fallbacks | Audit/inventory phase | Run test suite with `CLASSIC_DISABLE_RUST=1`; all core features must pass |
| Breaking PyInstaller hidden imports | Every structural phase | PyInstaller build + launch test at each phase gate |
| Singleton state leaks | Singleton cleanup sub-phase | Full test suite with `pytest -n auto` (parallel) -- no order-dependent failures |
| Async/sync boundary breakage | Dual interface consolidation phase | Manual GUI testing + stress test with concurrent scanning |
| Rust crate dependency breakage | Rust cleanup phase | `cargo build --workspace` + `cargo test --workspace` at phase gate |
| Factory contract breakage | Abstraction flattening phase | Integration tests for each factory function with both Rust and Python paths |
| Circular import from lazy import loss | Any module consolidation phase | `uv run python -c "import ClassicLib"` and both entry points launch successfully |

## Sources

- `J:\CLASSIC-Fallout4\.planning\codebase\CONCERNS.md` -- Known bugs, tech debt, fragile areas, test gaps
- `J:\CLASSIC-Fallout4\.planning\codebase\ARCHITECTURE.md` -- Data flow, async patterns, factory pattern
- `J:\CLASSIC-Fallout4\.planning\codebase\TESTING.md` -- Test organization, singleton mocking patterns
- `J:\CLASSIC-Fallout4\.planning\codebase\STRUCTURE.md` -- Module layout, Rust crate inventory
- `J:\CLASSIC-Fallout4\.planning\PROJECT.md` -- Cleanup scope, constraints, key decisions
- `J:\CLASSIC-Fallout4\CLASSIC.spec` -- PyInstaller configuration with hardcoded module paths
- `J:\CLASSIC-Fallout4\rust\Cargo.toml` -- Workspace membership and dependency graph
- `J:\CLASSIC-Fallout4\ClassicLib\integration\factory\core.py` -- Singleton cache, Rust disable mechanism
- `J:\CLASSIC-Fallout4\.claude\rules\` -- Project conventions (lazy imports, ONE RUNTIME, TDD)

---
*Pitfalls research for: CLASSIC hybrid Python-Rust codebase cleanup*
*Researched: 2026-02-01*
