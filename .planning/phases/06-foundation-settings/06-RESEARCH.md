# Phase 6: Foundation & Settings - Research

**Researched:** 2026-02-02
**Domain:** Rust Settings Cache Migration + Golden File Testing Infrastructure
**Confidence:** HIGH

## Summary

This phase migrates the Python YAML settings cache (`YamlSettingsCache`) to delegate entirely to the existing Rust `classic-settings-core` crate via `classic-settings-py` bindings. The Rust implementation is complete (DashMap-based cache, sync/async APIs, batch loading). The Python side currently maintains its own `AsyncYamlSettingsCore` with Python dictionaries for caching - this layer becomes a thin wrapper.

Additionally, this phase establishes golden file infrastructure for parity testing. Golden files capture Python crash log analysis output (intermediate and final) before subsequent migration phases, enabling byte-for-byte comparison to validate Rust parity.

**Primary recommendation:** Wire Python `YamlSettingsCache` to call `classic_settings` module functions directly, remove Python caching logic, and create a `tests/golden/` directory with a fixture-based capture/compare framework using a `@pytest.mark.parity` marker.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| classic-settings-core | 8.2.0 | Rust YAML cache (DashMap, tokio) | Already exists, tested, production-ready |
| classic-settings-py | 8.2.0 | PyO3 bindings for settings | Already exists with full API |
| DashMap | 6.1 | Lock-free concurrent HashMap | Project standard, verified in workspace |
| yaml-rust2 | 0.11.0 | YAML parsing (Rust) | Project standard, YAML 1.2 compliant |
| pytest | project version | Test framework | Project standard |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-regressions | existing or 3.x | Golden file framework | Optional - can use custom fixture instead |
| difflib | stdlib | Text diff generation | Parity test failure diagnostics |
| re | stdlib | Timestamp/path masking | Pre-comparison normalization |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom golden fixture | pytest-golden/pytest-regressions | Custom gives full control over masking; plugins may not support custom normalization |
| DashMap | RwLock<HashMap> | DashMap already in use, lock-free reads are faster |

**Installation:**
No new dependencies required - all libraries already in project.

## Architecture Patterns

### Recommended Project Structure
```
ClassicLib/
└── io/yaml/
    ├── cache.py              # YamlSettingsCache - thin Rust wrapper
    ├── convenience.py        # yaml_settings(), classic_settings() - unchanged API
    └── async_/
        └── core.py           # AsyncYamlSettingsCore - delegates to Rust

tests/
├── golden/
│   ├── __init__.py
│   ├── conftest.py           # Golden file fixtures (autouse for cleanup)
│   ├── captured/             # Golden output files (git-tracked)
│   │   ├── crash_log_001_segments.json
│   │   ├── crash_log_001_analysis.json
│   │   └── crash_log_001_report.txt
│   ├── test_settings_parity.py
│   └── test_scanlog_parity.py  # Future phases
└── fixtures/
    └── golden_fixtures.py    # Centralized golden file logic
```

### Pattern 1: Thin Python Wrapper over Rust
**What:** Python class that delegates all cache operations to Rust module
**When to use:** Migration from Python implementation to Rust
**Example:**
```python
# Source: Existing classic_settings.pyi API
import classic_settings

class YamlSettingsCache:
    """Thin wrapper delegating to Rust classic_settings module."""

    def load_yaml(self, yaml_path: Path) -> YAMLMapping:
        """Load YAML using Rust cache."""
        key = str(yaml_path)
        docs = classic_settings.load_settings_sync(key, str(yaml_path))
        return docs[0] if docs else {}

    def invalidate(self, key: str) -> bool:
        """Invalidate specific cache entry in Rust."""
        return classic_settings.invalidate(key)

    @staticmethod
    def debug_info() -> dict[str, Any]:
        """Return cache statistics for debugging."""
        return {
            "cache_size": classic_settings.cache_size(),
            "cache_keys": classic_settings.cache_keys(),
        }
```

### Pattern 2: Golden File Capture Fixture
**What:** pytest fixture that captures output and compares to stored golden files
**When to use:** Parity testing between implementations
**Example:**
```python
# Source: pytest-regressions patterns + custom masking
import json
import re
from pathlib import Path
from typing import Any

GOLDEN_DIR = Path(__file__).parent / "captured"
TIMESTAMP_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}")
PATH_PATTERN = re.compile(r"[A-Za-z]:\\[^\s\"']+|/[^\s\"']+")

def mask_dynamic(text: str) -> str:
    """Replace timestamps and paths with placeholders."""
    text = TIMESTAMP_PATTERN.sub("{{TIMESTAMP}}", text)
    text = PATH_PATTERN.sub("{{PATH}}", text)
    return text

@pytest.fixture
def golden_file(request):
    """Fixture for golden file comparison."""
    def check(output: str | dict, name: str) -> None:
        golden_path = GOLDEN_DIR / f"{name}.golden"

        if isinstance(output, dict):
            output = json.dumps(output, indent=2, sort_keys=True)

        masked = mask_dynamic(output)

        if request.config.getoption("--update-golden"):
            golden_path.write_text(masked, encoding="utf-8")
            return

        expected = golden_path.read_text(encoding="utf-8")
        assert masked == expected, _generate_diff(expected, masked)

    return check
```

### Pattern 3: Targeted Cache Invalidation
**What:** Invalidate only changed settings, not entire cache
**When to use:** Settings file updates
**Example:**
```python
# Source: Decision from CONTEXT.md
def on_settings_changed(yaml_store: YAML, changed_keys: list[str]) -> None:
    """Invalidate only affected cache entries."""
    for key in changed_keys:
        cache_key = f"{yaml_store.value}:{key}"
        if classic_settings.is_cached(cache_key):
            classic_settings.invalidate(cache_key)
            logger.debug(f"Invalidated cache key: {cache_key}")
```

### Anti-Patterns to Avoid
- **Dual caching:** Don't maintain Python dict cache alongside Rust DashMap - causes sync issues
- **Silent fallback:** Don't silently fall back to Python on Rust errors - surface them
- **Full cache clear on any change:** Use targeted invalidation per CONTEXT.md decision
- **Ignoring dynamic data in golden files:** Always mask timestamps and paths

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Thread-safe settings cache | Custom locking dict | classic_settings (DashMap) | DashMap handles all concurrency |
| YAML parsing | Custom parser | yaml-rust2 via classic_settings | YAML 1.2 edge cases, anchors, multi-doc |
| Async batch loading | asyncio.gather with locks | classic_settings.load_batch_async | Rust handles tokio concurrency properly |
| Text diff for test failures | Custom diff | difflib.unified_diff | Standard library, well-tested |

**Key insight:** The Rust cache is complete. Python's job is wiring, not reimplementing.

## Common Pitfalls

### Pitfall 1: Event Loop Conflicts with AsyncBridge
**What goes wrong:** Calling sync wrapper from async context causes deadlock or "no running event loop" errors
**Why it happens:** AsyncBridge creates its own event loop for GUI contexts
**How to avoid:** Keep existing pattern - detect async context with `asyncio.get_running_loop()`, raise clear error directing to async methods
**Warning signs:** "Cannot call sync methods from async context" exception, GUI freezes

### Pitfall 2: Cache Key Inconsistency
**What goes wrong:** Python uses Path objects as keys, Rust uses strings - cache misses
**Why it happens:** Rust `classic_settings.load_settings_sync(key, path)` takes string key
**How to avoid:** Normalize to strings consistently: `key = str(yaml_path.resolve())`
**Warning signs:** Settings loaded multiple times, cache_size growing unexpectedly

### Pitfall 3: Golden File Non-Determinism
**What goes wrong:** Tests pass locally, fail in CI (or vice versa)
**Why it happens:** Unmasked timestamps, paths with different separators, dict ordering
**How to avoid:**
  - Mask all timestamps with `{{TIMESTAMP}}`
  - Mask all paths with `{{PATH}}`
  - Use `json.dumps(sort_keys=True)` for JSON golden files
**Warning signs:** Flaky parity tests, diffs showing only timestamps/paths

### Pitfall 4: Rust Error Swallowed
**What goes wrong:** Rust cache fails but Python continues with stale data
**Why it happens:** Overly broad exception handling
**How to avoid:** Per CONTEXT.md - hard error on Rust failure, include Rust error details in message
**Warning signs:** Unexpected None values, silent cache misses

### Pitfall 5: Batch Loading Order Dependency
**What goes wrong:** Batch load returns results in different order than requested
**Why it happens:** Using JoinSet::join_next() (completion order) instead of tokio::join! (input order)
**How to avoid:** This is already fixed in classic-settings-core - verify batch results match input order
**Warning signs:** Wrong settings applied to wrong keys (per project memory 05-memories.md)

## Code Examples

Verified patterns from official sources:

### Rust Cache API (from classic_settings.pyi)
```python
# Source: j:\CLASSIC-Fallout4\rust\python-bindings\classic-settings-py\classic_settings.pyi
import classic_settings

# Sync loading
docs = classic_settings.load_settings_sync("my_config", "/path/to/config.yaml")
value = docs[0]["section"]["key"]

# Async loading
async def load():
    docs = await classic_settings.load_settings_async("my_config", "/path/to/config.yaml")
    return docs[0]

# Batch loading (sync)
count = classic_settings.load_batch_sync(["/path/a.yaml", "/path/b.yaml"])

# Cache management
if classic_settings.is_cached("my_config"):
    cached = classic_settings.get_cached("my_config")

classic_settings.invalidate("my_config")  # Targeted
classic_settings.clear_cache()            # Full clear

# Debug info
size = classic_settings.cache_size()
keys = classic_settings.cache_keys()
```

### Debug Info Method (new - for CONTEXT.md requirement)
```python
# Source: Decision from CONTEXT.md - expose cache.debug_info()
@staticmethod
def debug_info() -> dict[str, Any]:
    """Return cache debugging information.

    Returns:
        Dictionary with cache state for debugging:
        - cache_size: Number of entries
        - cache_keys: List of all cached keys
        - hit_rate: Cache hit percentage (if tracked)
    """
    return {
        "cache_size": classic_settings.cache_size(),
        "cache_keys": classic_settings.cache_keys(),
        # Note: Hit rate would require adding to Rust side
    }
```

### Placeholder Format for Masking (Claude's Discretion)
```python
# Recommended placeholder formats for golden file masking
TIMESTAMP_PLACEHOLDER = "{{TIMESTAMP}}"  # Replaces 2024-01-15T10:30:45, etc.
PATH_PLACEHOLDER = "{{PATH}}"            # Replaces C:\Users\..., /home/user/...
UUID_PLACEHOLDER = "{{UUID}}"            # If UUIDs appear in output

# Regex patterns
TIMESTAMP_PATTERNS = [
    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?",  # ISO 8601
    r"\d{4}-\d{2}-\d{2}",  # Date only
]
PATH_PATTERNS = [
    r"[A-Za-z]:\\(?:[^\s\"'<>|]+)",  # Windows path
    r"/(?:home|tmp|var|usr|Users)[^\s\"'<>|]+",  # Unix common paths
]
```

### Pytest Marker for Parity Tests (Claude's Discretion)
```python
# Recommended marker name: parity
# Add to pyproject.toml [tool.pytest.ini_options] markers:
# "parity: Parity tests comparing Python and Rust implementations"

@pytest.mark.parity
@pytest.mark.slow  # May take time to process real logs
def test_crash_log_analysis_parity(golden_file, sample_log):
    """Verify crash log analysis matches golden output."""
    result = analyze_crash_log(sample_log)
    golden_file(result, f"crash_analysis_{sample_log.name}")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Python dict cache in AsyncYamlSettingsCore | Rust DashMap via classic_settings | v8.2.0 | Lock-free concurrent access |
| Python fallback on Rust failure | Hard error (CONTEXT.md decision) | This phase | Surfaces issues immediately |
| Full cache clear on settings change | Targeted invalidation | This phase | Preserves unaffected entries |

**Deprecated/outdated:**
- `YamlCache.cache` (Python dict) - Being replaced by Rust DashMap
- `YamlCache.settings_cache` (Python dict) - Being replaced by Rust DashMap
- Dual Python/Rust validation mode - Not needed per CONTEXT.md decision

## Open Questions

Things that couldn't be fully resolved:

1. **Cache Hit Rate Tracking**
   - What we know: CONTEXT.md requires DEBUG-level performance metrics including hit rate
   - What's unclear: Rust classic-settings-core doesn't currently track hits/misses
   - Recommendation: Add hit/miss counters to Rust side, expose via debug_info(). Low priority - can add in follow-up if needed.

2. **Intermediate Output Format for Golden Files**
   - What we know: CONTEXT.md says capture intermediate outputs (parsed segments, analysis results)
   - What's unclear: Exact serialization format for complex objects (ParsedSegments, etc.)
   - Recommendation: Use JSON with `sort_keys=True`. For non-serializable objects, define `to_dict()` methods.

## Sources

### Primary (HIGH confidence)
- `j:\CLASSIC-Fallout4\rust\business-logic\classic-settings-core\src\*.rs` - Full Rust implementation reviewed
- `j:\CLASSIC-Fallout4\rust\python-bindings\classic-settings-py\classic_settings.pyi` - Complete Python API
- `j:\CLASSIC-Fallout4\ClassicLib\io\yaml\cache.py` - Current Python implementation to replace
- `j:\CLASSIC-Fallout4\.planning\phases\06-foundation-settings\06-CONTEXT.md` - User decisions

### Secondary (MEDIUM confidence)
- [DashMap GitHub](https://github.com/xacrimon/dashmap) - Concurrent HashMap patterns
- [DashMap docs.rs](https://docs.rs/dashmap/latest/dashmap/struct.DashMap.html) - API reference
- [pytest-regressions patterns](https://medium.com/@jarifibrahim/golden-files-why-you-should-use-them-47087ec994bf) - Golden file methodology

### Tertiary (LOW confidence)
- WebSearch results on timestamp masking - General patterns, verified against project needs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in project and verified working
- Architecture: HIGH - Patterns derived from existing codebase and CONTEXT.md decisions
- Pitfalls: HIGH - Based on project memories (05-memories.md) and code review

**Research date:** 2026-02-02
**Valid until:** 2026-03-02 (30 days - stable domain, no fast-moving dependencies)
