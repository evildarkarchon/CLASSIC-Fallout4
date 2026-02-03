# Phase 10: Parity Validation - Context

**Gathered:** 2026-02-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Validate that Rust-generated output is functionally equivalent to Python implementation across scanning, report generation, and game detection. Golden files from Phase 6 are authoritative — Rust must match them exactly. This phase does NOT add new features; it validates that existing Rust code produces identical results.

</domain>

<decisions>
## Implementation Decisions

### Parity Definition
- Timestamps: Mask with `{{TIMESTAMP}}` placeholder before comparison
- Paths: Normalize to forward slashes for comparison (no masking)
- Whitespace: Strict matching — every space, tab, and newline must match exactly
- Ordering: Exact order required — items must appear in identical order in all sections

### Mismatch Handling
- Test failure: Hard fail — any mismatch fails the entire test suite
- Failure output: Full unified diff between expected (golden) and actual (Rust)
- Golden file updates: Not allowed — golden files are authoritative, Rust must match them
- Comparison scope: Whole-file comparison (entire report as one unit, not section-by-section)

### Golden File Baseline
- Source: Use existing Phase 6 golden files (do not regenerate)
- Coverage: 10+ representative logs covering error types, suspects, settings variations
- Storage: Committed to repository in `tests/golden/` directory
- Naming: Match source log name (e.g., `crash-2023-09-15.log` → `crash-2023-09-15.golden.md`)

### Test Organization
- Location: Dedicated `tests/parity/` directory
- Markers: Both `@pytest.mark.parity` AND `@pytest.mark.integration`
- CI: Required to pass — parity tests block merge on failure
- Performance: All parity tests must complete in < 30 seconds total

### Claude's Discretion
- Exact diff library/format for failure output
- How to load and apply masking patterns
- Test file organization within tests/parity/
- Whether to use pytest-golden or custom comparison

</decisions>

<specifics>
## Specific Ideas

- Golden files from Phase 6 are the source of truth — they capture Python's output before Rust migration
- The goal is character-for-character parity (after masking) so we can confidently remove Python code in Phase 11
- Strict matching chosen to catch subtle formatting differences that could affect user experience

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 10-parity-validation*
*Context gathered: 2026-02-03*
