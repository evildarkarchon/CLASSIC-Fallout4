---
phase: 06-foundation-settings
plan: 02
subsystem: testing-infrastructure
tags: [golden-files, parity, pytest, testing]

dependency-graph:
  requires: []
  provides: [golden-file-framework, parity-marker, golden-files]
  affects: [10-validation]

tech-stack:
  added: []
  patterns: [golden-file-testing, dynamic-data-masking]

key-files:
  created:
    - tests/fixtures/golden_fixtures.py
    - tests/golden/__init__.py
    - tests/golden/conftest.py
    - tests/golden/captured/.gitkeep
    - tests/golden/test_golden_infrastructure.py
    - tests/golden/GOLDEN_LOG_SELECTION.md
    - tests/golden/capture_golden_files.py
    - tests/golden/captured/*.json (32 files)
  modified:
    - pyproject.toml

decisions:
  - name: "Timestamp and path masking"
    choice: "{{TIMESTAMP}} and {{PATH}} placeholders"
    reason: "Consistent with plan specification, enables cross-environment golden file comparison"
  - name: "Golden file format"
    choice: "JSON for structured data, .golden for text"
    reason: "JSON allows easy diffing of structured output, text for unstructured content"
  - name: "Capture intermediate outputs"
    choice: "Separate segments and analysis files per log"
    reason: "Enables pinpointing which processing stage diverges during parity testing"

metrics:
  duration: "8m"
  completed: "2026-02-03"
---

# Phase 06 Plan 02: Golden File Infrastructure Summary

**One-liner:** Golden file framework with GoldenFileChecker class, @pytest.mark.parity marker, and 16 crash logs captured as baseline for Rust parity validation.

## Objective

Create golden file test infrastructure for parity validation and capture Python output for representative crash logs to establish baseline for Phase 10 Rust comparison.

## What Was Built

### Golden File Framework (tests/fixtures/golden_fixtures.py)
- `GoldenFileChecker` class for comparing output against stored golden files
- `mask_dynamic_data()` function replacing timestamps and paths with placeholders
- `generate_diff()` function providing full unified diff on parity failure
- `--update-golden` pytest option for regenerating golden files

### Test Infrastructure (tests/golden/)
- `conftest.py` importing fixtures for pytest discovery
- `test_golden_infrastructure.py` with 20 tests verifying framework works
- `GOLDEN_LOG_SELECTION.md` documenting 18 selected logs
- `capture_golden_files.py` script for generating golden files

### Captured Golden Files (tests/golden/captured/)
- 32 JSON files (16 logs x 2 output types)
- Segments output: parsed crash log segments with metadata
- Analysis output: file metadata and section detection results
- All files masked with {{TIMESTAMP}} and {{PATH}} placeholders

### Pytest Marker
- `@pytest.mark.parity` registered in pyproject.toml
- Marked as slow to enable skipping in fast test runs

## VAL-01 Satisfaction

**Requirement:** Capture Python output for 10+ logs in Phase 6
**Achieved:** 16 logs captured with 32 golden files total

Selected logs cover:
- 10 common cases (typical crashes, varied sizes 24KB-83KB)
- 5 edge cases (special chars, hex names, alphanumeric mixes)
- 1 minimal content (61 bytes, header only)

## Key Decisions Made

1. **Masking approach:** Use {{TIMESTAMP}} and {{PATH}} regex-based placeholders
2. **Output format:** JSON for structured data enables deterministic comparison
3. **Capture strategy:** Two files per log (segments + analysis) for debugging parity issues at each stage

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 0640fffd | feat | Create golden file fixture framework |
| b54da8fe | feat | Register parity marker and add infrastructure tests |
| 8f4be309 | docs | Document golden log selection criteria |
| c66c0b7e | feat | Capture golden files for 16 crash logs (VAL-01) |

## Next Phase Readiness

Phase 10 (Validation) can now:
- Run Rust parser on same 16 crash logs
- Compare output against golden files using `golden_file.check()`
- Use `@pytest.mark.parity` to identify parity tests
- Use `--update-golden` to regenerate baselines after intentional changes

## Deviations from Plan

None - plan executed exactly as written.

## Files Summary

| Category | Count | Description |
|----------|-------|-------------|
| Fixture files | 1 | tests/fixtures/golden_fixtures.py |
| Test files | 2 | conftest.py, test_golden_infrastructure.py |
| Documentation | 1 | GOLDEN_LOG_SELECTION.md |
| Scripts | 1 | capture_golden_files.py |
| Golden files | 32 | 16 logs x 2 output types |
| Config changes | 1 | pyproject.toml (parity marker) |
