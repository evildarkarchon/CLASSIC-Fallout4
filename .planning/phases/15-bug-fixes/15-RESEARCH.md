# Phase 15: Bug Fixes & Test Stabilization - Research

**Researched:** 2026-02-04
**Domain:** Rust test isolation, Python path resolution, pytest fixtures
**Confidence:** HIGH

## Summary

This phase addresses two documented bugs and stabilizes the test suite for reliable parallel execution. BUG-01 involves global static cache state in Rust (`YAML_CACHE` in `classic-yaml-core`) that causes test pollution during parallel runs. BUG-02 involves relative path usage in `classic_settings()` that fails when the current working directory differs from the project root.

Both bugs are well-documented in PITFALLS.md with clear root causes and fix approaches. The existing test infrastructure in CLASSIC already has sophisticated singleton reset patterns (see `singleton_fixtures.py`), which provides a template for the Rust-side cache clearing.

**Primary recommendation:** Add `#[serial_test::serial]` attribute to `test_clear_cache` in `classic-yaml-core` (and similar cache-touching tests), clear caches at test START and END, and resolve all paths through ResourceLoader or absolute path construction in Python.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| serial_test | 3.2 | Serialize Rust tests touching global state | Already in classic-settings-core dev-deps |
| pytest | 8.x | Python test framework | Project standard |
| pytest-xdist | 3.x | Parallel test execution | Already in use |
| tempfile | 3.14 | Rust temporary directories | Already in Rust dev-deps |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| DashMap | workspace | Lock-free concurrent cache | Already used in YAML_CACHE |
| pathlib | stdlib | Python path operations | Always for path construction |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| #[serial] attribute | Per-test cache instances | More code, but truly parallel; serial is simpler |
| ResourceLoader | `Path(__file__)` resolution | ResourceLoader handles frozen/dev/package modes correctly |

## Architecture Patterns

### BUG-01: Global Static Cache Pollution Pattern

**Root cause:** `YAML_CACHE` at line 156 of `classic-yaml-core/src/lib.rs` is a global `Lazy<DashMap<PathBuf, CachedYaml>>`. The `test_clear_cache` test at line 1890:
1. Loads a file (populating cache)
2. Asserts `cached_files >= 1`
3. Clears cache
4. Asserts `cached_files == 0`

**The race condition:** Between step 3 (clear) and step 4 (assert), a parallel test loads a file into the cache, causing the assertion to fail.

**Fix pattern:**
```rust
// Source: classic-settings-core/src/cache.rs lines 501-516 (working example)
#[test]
#[serial]  // <-- Required for tests touching global cache
fn test_clear_cache() {
    clear_cache();  // Clear at START

    // ... test logic ...

    clear_cache();  // Clear at END (optional but recommended)
    assert_eq!(cache_size(), 0);
}
```

**Why classic-yaml-core tests don't have #[serial]:**
Examining `classic-yaml-core/Cargo.toml` shows NO `serial_test` dev-dependency. The crate relies on test order stability, which is not guaranteed.

### BUG-02: Relative Path Resolution Pattern

**Root cause:** Line 196 of `ClassicLib/io/yaml/convenience.py`:
```python
settings_path = Path("CLASSIC Settings.yaml")  # WRONG
```

This works when CWD is project root but fails from GUI launched via shortcuts.

**Fix pattern:**
```python
# Source: ResourceLoader pattern from ClassicLib/support/resources.py
from ClassicLib.support.resources import ResourceLoader

def classic_settings[T](_type: type[T], setting: str) -> T | None:
    # Option A: Use project root detection
    project_root = Path(__file__).parent.parent.parent
    settings_path = project_root / "CLASSIC Settings.yaml"

    # Option B: Use ResourceLoader (handles frozen/dev/package)
    settings_path = ResourceLoader.get_data_directory().parent / "CLASSIC Settings.yaml"
```

### Audit for Similar CWD Dependencies

Per CONTEXT.md decision "Audit path functions", grep found these relative paths in ClassicLib:

| File | Line | Path | Risk Level |
|------|------|------|------------|
| `io/yaml/convenience.py` | 196 | `Path("CLASSIC Settings.yaml")` | HIGH - BUG-02 |
| `io/yaml/async_/core.py` | 87 | `Path("CLASSIC Data")` | MEDIUM - default only |
| `support/file_gen.py` | 36, 86 | `Path("CLASSIC Ignore.yaml")` | HIGH |
| `support/setup.py` | 196 | `Path("CLASSIC Settings.yaml")` | HIGH |
| `Interface/controllers/backup_manager.py` | 270 | `Path("CLASSIC Backup")` | MEDIUM |
| `scanning/game/orchestrator.py` | 195 | `Path("CLASSIC GFS Report.md")` | MEDIUM |

**Recommendation:** Fix all HIGH-risk paths in this phase. MEDIUM-risk paths may be acceptable if they're only used with explicit path context.

### Recommended Regression Test Structure

```
tests/
├── regression/           # New directory for this phase
│   └── test_bug_fixes.py # Explicit regression tests
```

```python
# tests/regression/test_bug_fixes.py
"""Regression tests for documented bugs.

Each test documents a specific bug that was fixed, with:
- Bug ID and original failure mode
- Parallel/CWD verification as appropriate
- Prevention of regression
"""

import pytest
from concurrent.futures import ThreadPoolExecutor
import os

class TestBug01CachePollution:
    """BUG-01: test_clear_cache parallel test pollution in classic-yaml-core.

    Original failure: Parallel tests loading YAML files would pollute the
    global YAML_CACHE, causing intermittent assertion failures in tests
    that expected specific cache states.

    Fix: Added #[serial] attribute and clear cache at test boundaries.
    """

    @pytest.mark.unit
    def test_parallel_cache_operations_isolated(self):
        """Verify cache operations don't pollute each other."""
        # Run multiple cache operations in parallel
        # Assert each sees consistent state
        pass


class TestBug02PathResolution:
    """BUG-02: classic_settings() resolves paths incorrectly when CWD differs.

    Original failure: GUI launched from non-project-root CWD would fail to
    find CLASSIC Settings.yaml because Path("CLASSIC Settings.yaml") resolved
    relative to CWD, not project root.

    Fix: Resolve paths relative to known anchors (ResourceLoader or __file__).
    """

    @pytest.mark.unit
    def test_classic_settings_works_from_different_cwd(self, tmp_path):
        """Verify classic_settings() works regardless of CWD."""
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)  # Change to temp directory
            # Call classic_settings() - should still work
        finally:
            os.chdir(original_cwd)
```

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Path resolution | `Path("file.yaml")` | `ResourceLoader.get_data_directory()` | Handles frozen, dev, package modes |
| Test cache reset | Manual clear in each test | `reset_all_singletons_impl()` fixture | Already handles all known singletons |
| Serial test execution | Custom locks | `#[serial_test::serial]` | Standard Rust pattern for global state |
| Parallel Python test isolation | Custom fixtures | pytest-xdist + autouse fixtures | Already configured in conftest.py |

**Key insight:** CLASSIC already has excellent test isolation infrastructure. The bugs exist because some edge cases weren't covered (Rust tests missing serial attribute, Python path not using ResourceLoader).

## Common Pitfalls

### Pitfall 1: Adding #[serial] Without Clearing Cache at Test Start

**What goes wrong:** Test assumes cache starts empty but previous serial test left data behind.
**Why it happens:** `#[serial]` only serializes execution, doesn't reset state.
**How to avoid:** Always `clear_cache()` at test START, not just END.
**Warning signs:** Tests pass with `--test-threads=1` but fail in serial batch.

### Pitfall 2: Fixing Path in One Location But Missing Others

**What goes wrong:** BUG-02 appears fixed but similar bugs exist in other files.
**Why it happens:** Grep for "Path(" misses some patterns; relative paths are common.
**How to avoid:** Use the audit table above. Fix all HIGH-risk items.
**Warning signs:** GUI still fails from certain shortcuts.

### Pitfall 3: Regression Tests That Only Run Sequentially

**What goes wrong:** Regression test for parallel pollution only runs sequentially.
**Why it happens:** Test doesn't actually exercise parallelism.
**How to avoid:** Use `ThreadPoolExecutor` or pytest-xdist to verify parallel behavior.
**Warning signs:** Regression test passes but original bug still reproducible.

### Pitfall 4: Changing CWD in Tests Without Cleanup

**What goes wrong:** `os.chdir()` in test affects subsequent tests.
**Why it happens:** Exception before cleanup or missing finally block.
**How to avoid:** Use pytest's `monkeypatch.chdir()` or try/finally.
**Warning signs:** Unrelated tests fail with "file not found" after CWD tests.

### Pitfall 5: Skipping Tests Instead of Fixing Them

**What goes wrong:** Flaky test gets `@pytest.mark.skip` instead of fix.
**Why it happens:** Time pressure, unclear root cause.
**How to avoid:** Per CONTEXT.md decision, fix or document reasoning.
**Warning signs:** `pytest --collect-only | grep skip` shows undocumented skips.

## Code Examples

### Rust: Adding Serial Test Attribute

```rust
// Source: Pattern from classic-settings-core/src/cache.rs

// Step 1: Add to Cargo.toml [dev-dependencies]
// serial_test = "3.2"

// Step 2: Import in test module
#[cfg(test)]
mod tests {
    use super::*;
    use serial_test::serial;  // Add this

    #[test]
    #[serial]  // Add this to tests touching YAML_CACHE
    fn test_clear_cache() {
        clear_cache();  // Start clean

        // Test logic here

        clear_cache();  // End clean
        assert_eq!(cache_size(), 0);
    }
}
```

### Python: Path Resolution Fix

```python
# Source: Pattern from ClassicLib/support/resources.py lines 324-351

# BEFORE (BUG-02):
settings_path = Path("CLASSIC Settings.yaml")

# AFTER (Fix option A - using ResourceLoader):
from ClassicLib.support.resources import ResourceLoader

def classic_settings[T](_type: type[T], setting: str) -> T | None:
    # Get project root through ResourceLoader
    data_dir = ResourceLoader.get_data_directory()  # Returns absolute path
    project_root = data_dir.parent  # CLASSIC Data is one level down
    settings_path = project_root / "CLASSIC Settings.yaml"

    if not settings_path.exists():
        # ... create from defaults ...

# AFTER (Fix option B - using __file__):
from pathlib import Path

# convenience.py is at ClassicLib/io/yaml/convenience.py
# Project root is 4 levels up: convenience.py -> yaml -> io -> ClassicLib -> root
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

def classic_settings[T](_type: type[T], setting: str) -> T | None:
    settings_path = _PROJECT_ROOT / "CLASSIC Settings.yaml"
    # ... rest of function ...
```

### Python: CWD-Independent Regression Test

```python
# Source: Pattern for BUG-02 regression test

import os
import pytest
from pathlib import Path
from unittest.mock import patch

@pytest.mark.unit
def test_classic_settings_cwd_independent(tmp_path: Path, monkeypatch):
    """Verify classic_settings() works regardless of CWD.

    BUG-02 regression test: classic_settings() used Path("CLASSIC Settings.yaml")
    which failed when CWD was not project root.
    """
    # Save original CWD
    original_cwd = Path.cwd()

    try:
        # Change to a completely different directory
        monkeypatch.chdir(tmp_path)
        assert Path.cwd() != original_cwd

        # Import after CWD change to ensure no caching of old paths
        from ClassicLib.io.yaml.convenience import classic_settings

        # Mock the underlying yaml_settings to avoid full initialization
        with patch('ClassicLib.io.yaml.convenience.yaml_settings') as mock:
            mock.return_value = True

            # This should NOT fail with FileNotFoundError
            result = classic_settings(bool, "VR Mode")

            # Verify the path used was absolute, not relative
            # (Implementation detail: check mock call args if needed)

    finally:
        # monkeypatch handles cleanup, but explicit for clarity
        pass
```

### Rust: Parallel Cache Regression Test

```rust
// Source: Pattern for BUG-01 regression test

/// BUG-01 regression test: verify cache operations don't pollute parallel tests.
///
/// Original failure: test_clear_cache failed intermittently due to parallel tests
/// loading files between clear_cache() and assertion.
#[test]
#[serial]  // Must be serial to verify isolation works
fn test_cache_isolation_under_parallel_load() {
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::thread;

    // Clear to known state
    clear_global_yaml_cache();
    reset_cache_stats();

    let ops = YamlOperations::new();
    let success_count = AtomicUsize::new(0);

    // Simulate what parallel tests would do
    thread::scope(|s| {
        // Writer threads (simulating parallel tests)
        for i in 0..5 {
            s.spawn(|| {
                let mut temp = tempfile::NamedTempFile::new().unwrap();
                writeln!(temp, "key{}: value{}", i, i).unwrap();

                let local_ops = YamlOperations::new();
                let _ = local_ops.load_yaml_file(temp.path());
            });
        }

        // Verifier thread (simulating test_clear_cache)
        s.spawn(|| {
            // Small delay to let some writers start
            std::thread::sleep(std::time::Duration::from_millis(5));

            // Clear and immediately verify - this was the race condition
            clear_global_yaml_cache();
            let stats = ops.get_cache_stats();

            // With proper serialization, this should always be 0
            if *stats.get("cached_files").unwrap() == 0 {
                success_count.fetch_add(1, Ordering::Relaxed);
            }
        });
    });

    // The verifier should have seen 0 files (proper isolation)
    assert_eq!(success_count.load(Ordering::Relaxed), 1,
        "Cache should be empty immediately after clear_global_yaml_cache()");
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tests assume clean start | Explicit `clear_cache()` at test start | This phase | Eliminates false assumptions |
| Relative paths for project files | ResourceLoader-based resolution | This phase | Works in all execution contexts |
| Individual singleton resets | `reset_all_singletons_impl()` fixture | v8.2.0 | Centralized, comprehensive |

**Deprecated/outdated:**
- Using bare `Path("filename")` for project-level files - use ResourceLoader or `__file__`-based resolution
- Assuming test order stability in Rust - use `#[serial]` for global state

## Open Questions

Things that couldn't be fully resolved:

1. **MEDIUM-risk relative paths**
   - What we know: backup_manager.py and orchestrator.py use relative paths
   - What's unclear: Are these always called from contexts where CWD is project root?
   - Recommendation: Audit call sites during implementation; fix if called from GUI

2. **Rust test parallelism settings**
   - What we know: cargo test runs parallel by default
   - What's unclear: Are there CI-specific parallelism settings that differ from local?
   - Recommendation: Run `cargo test --jobs 4` locally to verify serial attribute works

3. **Skipped/disabled tests inventory**
   - What we know: CONTEXT.md requires auditing skipped tests
   - What's unclear: Full list of skipped tests and their reasons
   - Recommendation: Run `pytest --collect-only -q | grep skip` at phase start

## Sources

### Primary (HIGH confidence)
- `classic-settings-core/src/cache.rs` - Working `#[serial]` pattern
- `ClassicLib/support/resources.py` - ResourceLoader implementation
- `tests/fixtures/singleton_fixtures.py` - Existing reset patterns
- `.planning/research/PITFALLS.md` - P3 (global state) and P14 (relative paths) analysis

### Secondary (MEDIUM confidence)
- serial_test crate documentation (verified in use)
- pytest-xdist parallel execution model

### Tertiary (LOW confidence)
- None - all patterns verified from existing codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in use in project
- Architecture: HIGH - patterns derived from existing working code
- Pitfalls: HIGH - documented in PITFALLS.md with specific line numbers

**Research date:** 2026-02-04
**Valid until:** Indefinite - test isolation patterns are stable
