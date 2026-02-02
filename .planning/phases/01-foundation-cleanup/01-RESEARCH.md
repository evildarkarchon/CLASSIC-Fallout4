# Phase 1: Foundation Cleanup - Research

**Researched:** 2026-02-01
**Domain:** Dead code removal, global state cleanup, CI tooling for Python-Rust hybrid codebase
**Confidence:** HIGH

## Summary

Phase 1 is the foundational cleanup phase for CLASSIC, targeting dead code removal, global mutable state cleanup, and CI tooling baselines. The codebase investigation reveals that the "11 deprecated files" claim from initial research overstates reality -- there are actually 2 clearly deprecated modules (one file with deprecated re-exports, one file with deprecated version constants) plus several deprecated code *sections* within otherwise-live files. The Rust workspace has no empty/stub crates -- all 39 crates contain substantial code (250-10800 lines each). Global state cleanup is well-scoped: 19 `global _*` instances in ClassicLib/ are categorizable into lazy-init singletons (keep), lazy-init caches (keep with reset), and mutable flags (replace). Existing singleton patterns already have `reset_instance()` methods in 4 classes, and `GlobalRegistry.clear()` exists for test cleanup -- the gap is a unified autouse fixture.

**Primary recommendation:** Start with GLOB-02 (audit/categorize globals) since it informs all other work, then do DEAD-01 (remove deprecated modules) as a quick win, then DEAD-02/DEAD-04 (tooling) in parallel, then GLOB-01/GLOB-03 (replace flags, add fixture), and finally DEAD-03 (Rust audit -- turns out to be a verification task, not a removal task).

## Standard Stack

### Core

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| vulture | 2.14+ | Whole-program dead code detection | Only Python tool that does cross-file unused function/class detection. Ruff catches unused imports/variables within a file; vulture catches functions defined in module A but never called from anywhere. |
| pytest-cov | 7.0.0 (installed) | Test coverage baseline | Already configured in pyproject.toml with `--cov` in addopts. Coverage config exists with branch=true, fail_under=80. |
| ruff | 0.11.0+ (installed) | Linting, unused imports (F401), unused variables (F841) | Already running in CI. Catches file-level dead code. |
| cargo clippy | bundled | Rust dead code detection | Workspace already has `unused = "deny"` lint. Catches dead Rust code at compile time. |

### Supporting

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| cargo-machete | 0.7+ | Find unused Cargo dependencies | After DEAD-03 audit to verify no unused deps in Cargo.toml files. Works on stable Rust (unlike cargo-udeps which needs nightly). |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| vulture | ruff only | Ruff only catches unused within a single file; vulture does cross-file analysis. Both needed. |
| vulture whitelist file | vulture `--min-confidence 100` | Whitelist is more maintainable long-term; min-confidence 100 misses some real dead code. Use whitelist. |
| cargo-machete | cargo-udeps | cargo-udeps requires nightly Rust. cargo-machete works on stable with heuristic-based approach. |

**Installation:**
```bash
uv add --dev vulture
# cargo-machete is optional, install if needed:
cargo install cargo-machete
```

## Architecture Patterns

### Pattern 1: Vulture Whitelist for False Positives

**What:** Vulture reports false positives for dynamic dispatch, pytest fixtures, and PyO3-imported names. A whitelist file tells vulture these names are intentionally used.
**When to use:** Immediately after first vulture run to suppress known false positives.
**Example:**
```python
# vulture_whitelist.py
# PyO3 imports used at runtime but not visible to static analysis
import classic_yaml  # noqa: vulture
classic_yaml.RustYamlOperations

# Pytest fixtures (discovered by pytest, not imported directly)
from tests.fixtures.registry_fixtures import init_message_handler_fixture
init_message_handler_fixture

# PySide6 slots connected via string names
from ClassicLib.Interface.MainWindow import MainWindow
MainWindow.on_scan_complete
```

**Configuration in pyproject.toml:**
```toml
[tool.vulture]
paths = ["ClassicLib/"]
exclude = ["**/tests/*", "**/.venv/*", "**/dist/*", "**/build/*"]
min_confidence = 80
```
Source: Context7 /jendrikseipp/vulture documentation

### Pattern 2: Singleton Reset for Test Isolation

**What:** Each singleton class exposes a `reset_instance()` classmethod guarded by `PYTEST_CURRENT_TEST` env var check. A unified autouse fixture calls all resets.
**When to use:** Between every test to prevent state leakage.
**Example:**
```python
# Existing pattern in ClassicLib (4 classes already have this):
@classmethod
def reset_instance(cls) -> None:
    if "PYTEST_CURRENT_TEST" not in os.environ:
        msg = "reset_instance() is only allowed in testing contexts"
        raise RuntimeError(msg)
    cls._instance = None

# New autouse fixture (GLOB-03):
@pytest.fixture(autouse=True)
def reset_all_singletons():
    """Reset all singleton state between tests."""
    yield
    # Post-test cleanup
    GlobalRegistry.clear()
    YamlSettingsCache.reset_instance()
    VersionRegistry.reset_instance()
    DatabasePoolManager.reset_instance()
    RustAcceleration.reset_instance()
    reset_component_cache()  # factory/core.py
    # Reset module-level globals
    import ClassicLib.messaging.handler as h
    with h._message_handler_lock:
        h._message_handler = None
```

### Pattern 3: Global Flag Replacement with lru_cache

**What:** Replace `global _FLAG; _FLAG = True` pattern with `@functools.lru_cache(maxsize=1)` that returns the computed value, with `func.cache_clear()` for test reset.
**When to use:** For one-shot flags like `_VERSION_WARNING_LOGGED` that exist solely to prevent repeated computation.
**Example:**
```python
# BEFORE (current pattern):
_VERSION_WARNING_LOGGED = False
def _log_version_warning():
    global _VERSION_WARNING_LOGGED
    if not _VERSION_WARNING_LOGGED:
        logger.warning(...)
        _VERSION_WARNING_LOGGED = True

# AFTER (lru_cache pattern):
@functools.lru_cache(maxsize=1)
def _log_version_warning():
    logger.warning(...)
    return True  # Return value cached, function only runs once

# In test fixture: _log_version_warning.cache_clear()
```

### Anti-Patterns to Avoid

- **Removing deprecated code without checking callers first:** Always grep for imports of the deprecated module before deletion. The `database_rust.py` file has zero callers (verified), but the deprecated version constants in `constants.py` are imported by 4 files (they import `NULL_VERSION` and `YAML`, not the deprecated versions -- but the file contains both).
- **Making vulture report 0 violations on first run:** Expect 50-100+ false positives. Budget time for whitelist curation. Do not lower `min_confidence` to hide real issues.
- **Resetting singletons in setUp instead of tearDown:** Always reset AFTER the test (in `yield` fixture teardown), not before. Tests that fail mid-execution still get cleanup.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Dead code detection across files | Manual grep + review | vulture + ruff F401 | Cross-file analysis catches functions defined but never called anywhere. Manual review misses this. |
| Coverage baseline report | Custom script | `pytest --cov=ClassicLib --cov-report=term` | Already configured in pyproject.toml. Just run it. |
| Rust dead code detection | Manual crate audit | `cargo clippy` with `unused = "deny"` | Already configured in workspace Cargo.toml. Compiler catches it. |
| Singleton test isolation | Per-test manual reset | Centralized autouse fixture | One fixture, all singletons. Prevents "forgot to reset X" bugs. |

**Key insight:** The tooling for this phase is 80% already installed and configured. The work is running the tools, interpreting results, and acting on findings -- not building infrastructure.

## Common Pitfalls

### Pitfall 1: Deprecated Code in Mixed Files
**What goes wrong:** Deleting an entire file that contains both deprecated AND live code.
**Why it happens:** `constants.py` contains deprecated `_DeprecatedVersion` wrapper (~80 lines) AND live code (`YAML` enum, `DB_PATHS`, `SETTINGS_IGNORE_NONE`, `get_db_paths()`). Deleting the file breaks everything.
**How to avoid:** For `constants.py`, remove only the `_DeprecatedVersion` class and the deprecated constant block (lines 40-137). Keep the rest. For `database_rust.py`, the entire file is a deprecated re-export shim with zero callers -- safe to delete entirely.
**Warning signs:** File has both `DEPRECATED` markers AND active imports from non-deprecated sections.

### Pitfall 2: Vulture False Positives from Dynamic Dispatch
**What goes wrong:** Vulture reports PySide6 slot methods, pytest fixtures, and PyO3-imported classes as unused. Developer removes them. Application crashes.
**Why it happens:** Vulture does static analysis. It cannot see: Qt signal-slot connections by string name, pytest fixture discovery, PyO3 module imports that happen at C level.
**How to avoid:** Start with `min_confidence = 80`. Create whitelist file for known dynamic patterns. Review every vulture finding before acting. Never auto-delete.
**Warning signs:** vulture reporting functions in `ClassicLib/Interface/` (likely Qt slots) or in `tests/fixtures/` (pytest fixtures).

### Pitfall 3: Rust Crate Audit Finds Nothing to Remove
**What goes wrong:** Time spent auditing 39 Rust crates expecting to find stubs, but all crates have real code (250-10800 lines each).
**Why it happens:** The initial estimate of "stub/empty crates" was based on the project having been through multiple migration phases. In reality, all crates were implemented.
**How to avoid:** Reframe DEAD-03 as a verification task, not a removal task. The output is "all crates verified as containing real code" or "these N crates have dead code detected by clippy." Run `cargo clippy --workspace` and `cargo build --workspace` to verify health, not to find crates to delete.
**Warning signs:** Spending more than 2 hours manually reading Rust source to determine if a 600-line crate is "stub."

### Pitfall 4: Breaking Lazy Import Discipline
**What goes wrong:** While cleaning up global state, developer consolidates imports to top-of-file. Circular import breaks startup.
**Why it happens:** CLAUDE.md rule: "Import `yaml_settings`, `classic_settings` inside functions to avoid circular imports." This rule exists because YAML settings depend on GlobalRegistry which depends on constants which historically depended on YAML settings.
**How to avoid:** Keep all lazy imports lazy, even when they look like they could be top-level. Test app startup (`uv run python -c "import ClassicLib"`) after every change.
**Warning signs:** `ImportError: cannot import name X from partially initialized module Y`.

### Pitfall 5: Coverage Baseline Misleading for Rust-Accelerated Code
**What goes wrong:** `pytest --cov` shows 0% coverage for Python modules that are actually exercised through Rust. Developer marks them for deletion. But the Python fallback is still the reference implementation.
**Why it happens:** When Rust acceleration is active (which it always is in dev), the Python fallback code paths in `ClassicLib/integration/python/` are never executed. Coverage correctly reports 0%.
**How to avoid:** The 0% coverage modules in `integration/python/` are NOT Phase 1 deletion candidates -- they're Phase 5 (Fallback Pruning). For Phase 1, focus coverage analysis on `ClassicLib/` modules OUTSIDE of `integration/python/` and `integration/rust/`.
**Warning signs:** Coverage report showing 0% for files in `ClassicLib/integration/python/` -- these are expected.

## Code Examples

### Running vulture for the first time
```bash
# Install
uv add --dev vulture

# First run -- expect many false positives
uv run vulture ClassicLib/ --min-confidence 80

# Generate whitelist skeleton from current false positives
uv run vulture ClassicLib/ --make-whitelist > vulture_whitelist.py

# Edit whitelist to keep only genuine false positives, remove real dead code

# Run with whitelist
uv run vulture ClassicLib/ vulture_whitelist.py --min-confidence 80
```

### Running coverage baseline
```bash
# Already configured in pyproject.toml addopts
# Just run tests -- coverage report appears automatically
uv run pytest -m "unit and not slow" --cov=ClassicLib --cov-report=term

# For detailed HTML report
uv run pytest -m "unit and not slow" --cov=ClassicLib --cov-report=html

# Identify 0% coverage modules (deletion candidates, excluding integration/python/)
uv run pytest --cov=ClassicLib --cov-report=term | grep "0%"
```

### Adding vulture to CI
```yaml
# In .github/workflows/ci.yml, add new job:
dead-code:
  name: Dead Code Detection (Vulture)
  runs-on: windows-latest
  timeout-minutes: 10
  steps:
    - uses: actions/checkout@v4
    - name: Install uv
      uses: astral-sh/setup-uv@v4
    - name: Set up Python
      run: uv python install ${{ env.PYTHON_VERSION }}
    - name: Install dependencies
      run: uv sync --all-extras
    - name: Run vulture
      run: uv run vulture ClassicLib/ vulture_whitelist.py --min-confidence 80
```

### Categorizing global state (GLOB-02 reference)
```
GLOBAL STATE INVENTORY (19 instances):

LAZY-INIT SINGLETONS (keep, ensure reset_instance() exists):
1. _message_handler (messaging/handler.py) -- MessageHandler singleton, has lock
2. _thread_manager (Interface/workers/ThreadManager.py) -- ThreadManager singleton
3. _game_integrity_orchestrator_core (scanning/game/orchestrator.py) -- lazy singleton
4. _async_yaml_core (io/yaml/async_/core.py) -- lazy singleton
5. _game_files_manager_core (scanning/game/game_files_manager.py) -- lazy singleton
6. _components_cache (integration/factory/core.py) -- has reset function
7. _file_io_instance (integration/factory/file_io.py) -- FileIO singleton
8. _core_lock (io/yaml/async_/core.py) -- asyncio.Lock lazy init

LAZY-INIT CACHES (keep, add cache_clear/reset):
9. _VERSION_TOOLTIP (Interface/Settings/tab_creators.py) -- computed once, cached
10. _EMOJI_PATTERN (messaging/formatting/formatter.py) -- compiled regex, cached
11. _ALL_ADDRESS_LIB_INFO_CACHE (scanning/game/check_xse_plugins.py) -- data cache
12. _PyReportFragment x4 (integration/rust/report/*.py) -- lazy class import cache
13. _PyReportGenerator (integration/rust/report/generator.py) -- lazy class import
14. _PyReportComposer (integration/rust/report/composer.py) -- lazy class import

MUTABLE FLAGS (replace with lru_cache or instance state):
15. _VERSION_WARNING_LOGGED (support/game_path.py) -- one-shot warning flag

CONSTANTS (no action needed):
16. _TESTING_MODE_ENV_VAR (core/registry.py) -- string constant, not mutable
17. _RUST_AVAILABLE (integration/scangame_factory.py) -- set once at import
18. _HAS_RUST_PATH x3 (support/game_path.py, docs_path.py, path_validator.py) -- set once at import
19. _RUST_PATH_AVAILABLE (Interface/shared/FolderManagement.py) -- set once at import
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual dead code review | vulture + ruff F401 in CI | vulture stable since 2020+ | Automated regression prevention |
| Per-test manual singleton reset | Centralized autouse fixture | Common pytest pattern | No forgotten resets |
| `global _FLAG = True` for one-shot | `@functools.lru_cache(maxsize=1)` with `cache_clear()` | Python 3.2+ (lru_cache) | Testable, no global mutation |

## Open Questions

1. **How many actual false positives will vulture produce on this codebase?**
   - What we know: PySide6 slots, pytest fixtures, and PyO3 imports will be false positives. Expect 30-100.
   - What's unclear: Exact count until first run.
   - Recommendation: Budget 1-2 hours for whitelist curation in plan 01-02.

2. **Are the deprecated version constants in constants.py still referenced anywhere?**
   - What we know: No file imports `OG_VERSION`, `NG_VERSION`, etc. by name (grep found zero matches for the deprecated constant names). Files import `NULL_VERSION` and `YAML` from the same module.
   - What's unclear: Whether any YAML config files reference these constant names as strings.
   - Recommendation: Remove the `_DeprecatedVersion` class and deprecated constant block. Keep `NULL_VERSION`, `YAML`, `GameID`, `SETTINGS_IGNORE_NONE`, `DB_PATHS`, `get_db_paths()`.

3. **Should the `reset_all_singletons()` fixture reset lazy-import caches in `integration/rust/report/*.py`?**
   - What we know: These 6 globals (`_PyReportFragment` x4, `_PyReportGenerator`, `_PyReportComposer`) cache class references from lazy imports. They prevent circular imports.
   - What's unclear: Whether stale references cause test issues. They cache class objects, not instances, so probably safe.
   - Recommendation: Include them in the reset fixture for completeness. Setting them to `None` is harmless -- they'll be re-imported on next access.

4. **What coverage threshold to set for CI?**
   - What we know: pyproject.toml already has `fail_under = 80`. Current actual coverage is unknown until first run.
   - What's unclear: Whether current tests meet 80% threshold.
   - Recommendation: Run coverage baseline first. If below 80%, set initial CI threshold at current level minus 2% (allows small fluctuations), then ratchet up as coverage improves.

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis: `grep -r "global _" ClassicLib/`, `grep -r "DEPRECATED" ClassicLib/`, `grep -r "reset_instance" ClassicLib/`
- `J:/CLASSIC-Fallout4/pyproject.toml` -- existing tool configuration, coverage config, pytest config
- `J:/CLASSIC-Fallout4/.github/workflows/ci.yml` -- current CI pipeline structure
- `J:/CLASSIC-Fallout4/rust/Cargo.toml` -- workspace manifest, lint config
- `J:/CLASSIC-Fallout4/tests/conftest.py` -- existing test infrastructure
- `J:/CLASSIC-Fallout4/tests/fixtures/registry_fixtures.py` -- existing reset patterns
- Context7 `/jendrikseipp/vulture` -- vulture configuration, whitelist, CI integration

### Secondary (MEDIUM confidence)
- `J:/CLASSIC-Fallout4/.planning/research/SUMMARY.md` -- prior research (verified against actual codebase)
- `J:/CLASSIC-Fallout4/.planning/research/FEATURES.md` -- feature inventory
- `J:/CLASSIC-Fallout4/.planning/codebase/CONCERNS.md` -- known fragile areas

### Tertiary (LOW confidence)
- cargo-machete version (0.7+) -- from training data, not verified against crates.io

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- tools verified from pyproject.toml and existing CI config
- Architecture: HIGH -- patterns derived from reading actual source code (handler.py, registry.py, cache.py, coordinator.py)
- Pitfalls: HIGH -- each pitfall grounded in specific codebase findings (e.g., constants.py mixed content, Rust crate line counts)

**Research date:** 2026-02-01
**Valid until:** 2026-03-01 (stable domain, no fast-moving dependencies)
