# Phase 11: Integration & Cleanup - Context

**Gathered:** 2026-02-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Finalize the Rust migration by:
1. Addressing parity differences identified in Phase 10 validation
2. Removing Python business logic files (not just deprecating)
3. Simplifying factory to return Rust directly (no fallbacks)
4. Verifying PyInstaller build works with all Rust modules

This is cleanup work — no new features, no new capabilities.

</domain>

<decisions>
## Implementation Decisions

### Parity Difference Handling
- Fix Rust to match Python version string format exactly (character-for-character)
- Fix Rust to match Python whitespace/blank lines exactly
- Implement missing settings validation section in Rust output
- Claude's Discretion: Whether to keep additional suspect detections found by Rust (evaluate if valid improvements)

### Python Removal Scope
- Delete Python files immediately once Rust replacement validated (no deprecation period)
- Remove wrapper files too — callers import Rust modules directly
- Delete tests for removed Python code (obsolete)
- Remove incrementally by component (not all at once) — easier to bisect issues

### Factory Simplification
- Hard fail on import errors — if Rust import fails, raise ImportError immediately
- Keep factory as import hub — provides single import point for components
- Keep current function names (get_parser(), get_yamldata(), etc.) — API stability
- Remove RUST_AVAILABLE flags and availability checks — Rust is always available

### Build Verification
- CLI scan with sample crash log as smoke test — verify AUTOSCAN.md output
- Manual verification only — no CI automation for builds
- Block release if PyInstaller build fails — build must succeed
- Update CLASSIC.spec file — ensure all Rust .pyd modules in hiddenimports

### Claude's Discretion
- Order of component removal within incremental approach
- Specific Rust fixes for version string and whitespace parity
- CLASSIC.spec hiddenimports entries needed for Rust modules

</decisions>

<specifics>
## Specific Ideas

- Incremental removal allows git bisect if issues found after deletion
- Factory stays as ergonomic import point even though it just re-exports Rust
- Settings validation section is user-visible — must be in Rust output

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 11-integration-cleanup*
*Context gathered: 2026-02-03*
