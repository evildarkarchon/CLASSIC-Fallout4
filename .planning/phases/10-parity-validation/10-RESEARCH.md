# Phase 10: Parity Validation - Research

**Researched:** 2026-02-03
**Domain:** Rust-Python output parity testing with golden files
**Confidence:** HIGH

## Summary

Phase 10 validates that Rust-generated output matches Python implementation character-for-character for scanning, report generation, and game detection. The project already has substantial infrastructure from Phase 6:

1. **Existing golden files** - 16 logs captured in `tests/golden/captured/` with segments and analysis JSON
2. **Golden fixtures module** - `tests/fixtures/golden_fixtures.py` with masking and diff utilities
3. **Parity fixtures module** - `tests/fixtures/parity_fixtures.py` with comparison infrastructure

The primary work is creating the `tests/parity/` directory with tests that:
- Load golden files as expected output
- Run Rust orchestrator with identical inputs
- Compare masked outputs character-for-character
- Fail hard with unified diff on any mismatch

**Primary recommendation:** Build on existing `golden_fixtures.py` infrastructure - use `GoldenFileChecker` class with custom comparison logic for whole-file matching per CONTEXT.md decisions.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 9.0.2+ | Test framework | Already in pyproject.toml, standard for Python testing |
| difflib | stdlib | Unified diff generation | Built-in, no external dependency |
| pathlib | stdlib | Path handling | Project standard per rules |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-timeout | 2.4+ | Test timeout enforcement | Already in pyproject.toml; 30s limit per CONTEXT.md |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom comparison | pytest-golden | Project already has custom `GoldenFileChecker`; external plugin adds complexity |
| Custom comparison | pytest-regressions | Same - existing infrastructure is sufficient |
| difflib | deepdiff | difflib.unified_diff gives familiar unified diff format |

**Installation:**
No additional packages required - all dependencies already in `pyproject.toml`.

## Architecture Patterns

### Recommended Project Structure
```
tests/parity/
    __init__.py                  # Package marker
    conftest.py                  # Local fixtures, --update-golden hook
    test_scanning_parity.py      # VAL-02: Scanning output parity
    test_report_parity.py        # VAL-03: Report generation parity
    test_game_detection_parity.py # VAL-04: Game detection parity
```

### Pattern 1: Golden File Test Pattern
**What:** Load golden file, run Rust implementation, mask dynamic data, compare whole-file
**When to use:** Every parity test
**Example:**
```python
# Source: Existing tests/fixtures/golden_fixtures.py pattern
@pytest.mark.parity
@pytest.mark.integration
def test_scanning_parity_log_001(golden_file, rust_orchestrator, sample_log_path):
    """Rust scanning matches golden file for log 001."""
    # Load and process log with Rust
    result = rust_orchestrator.process_log(sample_log_path)

    # Compare against golden file (whole-file comparison)
    golden_file.check(result.report_lines, "crash_2022_06_05_12_52_17_report")
```

### Pattern 2: Timestamp and Path Masking
**What:** Replace dynamic data before comparison using regex patterns
**When to use:** All golden file comparisons involving timestamps or absolute paths
**Example:**
```python
# Source: Existing tests/fixtures/golden_fixtures.py
TIMESTAMP_PATTERNS = [
    re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?"),
    re.compile(r"\d{4}-\d{2}-\d{2}"),
    re.compile(r"\d{2}:\d{2}:\d{2}"),
]

def mask_dynamic_data(text: str) -> str:
    """Replace timestamps with {{TIMESTAMP}}, normalize paths to forward slashes."""
    result = text
    for pattern in TIMESTAMP_PATTERNS:
        result = pattern.sub("{{TIMESTAMP}}", result)
    # Normalize paths to forward slashes (per CONTEXT.md - no masking, just normalization)
    result = result.replace("\\", "/")
    return result
```

### Pattern 3: Whole-File Comparison with Diff
**What:** Compare entire masked output as single unit, show unified diff on failure
**When to use:** Per CONTEXT.md decision - no section-by-section comparison
**Example:**
```python
# Source: Derived from tests/fixtures/golden_fixtures.py
def compare_with_golden(actual: str, expected_path: Path) -> None:
    """Compare actual output against golden file, hard fail on mismatch."""
    expected = expected_path.read_text(encoding="utf-8")

    masked_actual = mask_dynamic_data(actual)
    masked_expected = mask_dynamic_data(expected)  # Already masked if captured properly

    if masked_actual != masked_expected:
        diff = generate_diff(masked_expected, masked_actual)
        pytest.fail(f"Golden file mismatch:\n\n{diff}")
```

### Anti-Patterns to Avoid
- **Section-by-section comparison:** CONTEXT.md specifies whole-file comparison
- **Updating golden files automatically:** Golden files are authoritative; Rust must match them
- **Floating-point tolerance:** Whitespace is strict; no fuzzy matching per CONTEXT.md
- **Order-independent comparison:** Exact order required per CONTEXT.md

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Diff generation | Custom diff algorithm | `difflib.unified_diff()` | Standard, familiar format, built-in |
| Timestamp masking | One-off regex | Existing `mask_dynamic_data()` | Already tested in `tests/golden/test_golden_infrastructure.py` |
| Golden file storage | Custom format | Existing `.json` format | Phase 6 already captured in this format |
| Test parametrization | Manual test duplication | `@pytest.mark.parametrize` | pytest standard, reduces code |

**Key insight:** Phase 6 already built the golden file infrastructure. Phase 10 should reuse it, not rebuild.

## Common Pitfalls

### Pitfall 1: Path Normalization vs Masking
**What goes wrong:** Masking paths with `{{PATH}}` placeholder loses path structure information
**Why it happens:** Original Phase 6 design used `{{PATH}}` placeholders
**How to avoid:** Per CONTEXT.md, normalize to forward slashes only - do NOT mask paths
**Warning signs:** Test failures due to path structure differences

### Pitfall 2: Whitespace Variations
**What goes wrong:** Trailing spaces, different newline counts cause false failures
**Why it happens:** Rust and Python string formatting may differ subtly
**How to avoid:** Strict whitespace matching per CONTEXT.md; fix Rust output if different
**Warning signs:** Diffs showing only whitespace differences

### Pitfall 3: Timestamp Format Variations
**What goes wrong:** Different timestamp formats between Python and Rust
**Why it happens:** Datetime formatting code may use different defaults
**How to avoid:** Mask ALL timestamp formats before comparison
**Warning signs:** Timestamps appearing in diffs

### Pitfall 4: Test Isolation
**What goes wrong:** Tests pass individually but fail together due to shared state
**Why it happens:** GlobalRegistry, singletons not cleared between tests
**How to avoid:** Use existing `reset_all_singletons` autouse fixture from conftest.py
**Warning signs:** Flaky tests, order-dependent failures

### Pitfall 5: Performance Budget Exceeded
**What goes wrong:** Parity tests take > 30 seconds total
**Why it happens:** Too many logs, serial execution, slow I/O
**How to avoid:** Limit to 10-16 representative logs; ensure Rust async processing
**Warning signs:** CI timeout warnings

## Code Examples

Verified patterns from official sources:

### Parity Test with Markers
```python
# Source: Derived from pyproject.toml marker definitions and CONTEXT.md
import pytest
from pathlib import Path
from tests.fixtures.golden_fixtures import mask_dynamic_data, generate_diff, GOLDEN_DIR

@pytest.mark.parity
@pytest.mark.integration
class TestScanningParity:
    """VAL-02: Rust scanning output matches Python golden files."""

    @pytest.mark.parametrize("log_stem", [
        "crash_2022_06_05_12_52_17",
        "crash_2022_06_12_07_11_38",
        "crash_2022_06_24_07_23_35",
        # ... more log stems
    ])
    def test_segments_parity(self, log_stem, rust_parser, sample_logs_dir):
        """Rust segment parsing matches golden segments."""
        # Load golden segments
        golden_path = GOLDEN_DIR / f"{log_stem}_segments.json"
        expected = json.loads(golden_path.read_text(encoding="utf-8"))

        # Parse with Rust
        log_path = sample_logs_dir / expected["log_file"]
        log_content = log_path.read_text(encoding="utf-8", errors="ignore")
        segments = rust_parser.find_segments(log_content.splitlines(), ...)

        # Compare (masking applied)
        actual = self._format_segments(segments)
        masked_actual = mask_dynamic_data(json.dumps(actual, indent=2, sort_keys=True))
        masked_expected = mask_dynamic_data(golden_path.read_text(encoding="utf-8"))

        if masked_actual != masked_expected:
            diff = generate_diff(masked_expected, masked_actual)
            pytest.fail(f"Segments mismatch for {log_stem}:\n\n{diff}")
```

### Unified Diff for Failure Output
```python
# Source: Python difflib documentation + existing golden_fixtures.py
from difflib import unified_diff

def generate_diff(expected: str, actual: str) -> str:
    """Generate unified diff for debugging parity failures.

    Args:
        expected: Expected (golden) content.
        actual: Actual (current) content.

    Returns:
        Unified diff string showing differences.
    """
    expected_lines = expected.splitlines(keepends=True)
    actual_lines = actual.splitlines(keepends=True)

    diff = unified_diff(
        expected_lines,
        actual_lines,
        fromfile="expected (golden)",
        tofile="actual (Rust)",
        lineterm=""
    )
    return "".join(diff)
```

### Path Normalization (Not Masking)
```python
# Source: CONTEXT.md decision - normalize paths, don't mask
def normalize_paths(text: str) -> str:
    """Normalize path separators to forward slashes for cross-platform comparison.

    Per CONTEXT.md: Paths are normalized to forward slashes, NOT masked with placeholder.
    """
    return text.replace("\\", "/")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pytest-golden plugin | Custom `GoldenFileChecker` | Phase 6 (2026-02) | More control over comparison logic |
| Path masking with `{{PATH}}` | Forward slash normalization | Phase 10 CONTEXT.md | Preserves path structure in diffs |
| Section-by-section comparison | Whole-file comparison | Phase 10 CONTEXT.md | Catches subtle formatting differences |

**Deprecated/outdated:**
- `{{PATH}}` placeholder masking: Replaced with forward slash normalization per CONTEXT.md

## Open Questions

Things that couldn't be fully resolved:

1. **Report generation golden files**
   - What we know: Phase 6 captured segments and analysis JSON
   - What's unclear: Were full AUTOSCAN.md reports captured? Inspection shows segments/analysis, not full reports
   - Recommendation: May need to capture full report golden files from Python before migration, or generate from existing segment data

2. **Game detection test strategy**
   - What we know: VAL-04 requires identical paths from game detection
   - What's unclear: How to test registry-based detection portably
   - Recommendation: Focus on mock-based tests for detection strategy, verify path format consistency

## Sources

### Primary (HIGH confidence)
- `tests/fixtures/golden_fixtures.py` - Existing masking and comparison infrastructure
- `tests/fixtures/parity_fixtures.py` - Existing parity validation framework
- `tests/golden/captured/` - Existing golden file corpus (16 logs)
- `pyproject.toml` - Existing pytest configuration and markers

### Secondary (MEDIUM confidence)
- [pytest-golden documentation](https://github.com/oprypin/pytest-golden) - Alternative approach considered
- [Python difflib documentation](https://docs.python.org/3/library/difflib.html) - unified_diff API reference

### Tertiary (LOW confidence)
- Web search results on golden file testing best practices - General patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in project
- Architecture: HIGH - Builds on existing Phase 6 infrastructure
- Pitfalls: HIGH - Based on codebase analysis and CONTEXT.md decisions

**Research date:** 2026-02-03
**Valid until:** 2026-03-03 (30 days - stable domain)
