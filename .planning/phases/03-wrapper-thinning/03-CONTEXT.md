# Phase 3: Wrapper Thinning - Context

**Gathered:** 2026-02-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Move business logic from fat Python wrappers in `ClassicLib/integration/rust/` into Rust `-core` crates. Python wrappers become thin type-conversion adapters only. Targets: `file_io_rust.py` (39KB) under 200 lines, `parser` and `formid` wrappers each under 150 lines. Application behavior must remain identical.

</domain>

<decisions>
## Implementation Decisions

### Migration boundary
- Python wrappers are **pure marshalling only** — zero logic, zero branching, just type conversion and Rust call delegation
- Wrapper accepts Pythonic types (pathlib.Path, etc.) and converts to Rust-friendly types internally — callers don't change their calling conventions
- Game-specific branching (Fallout4 vs Skyrim logic) **moves to Rust** — Python just passes the game identifier
- Rust exposes **async-compatible APIs** via PyO3 — Python wrappers just await and convert types

### Error handling at the boundary
- Rust errors map to **standard Python exceptions** (FileNotFoundError, ValueError, etc.) — callers catch familiar exceptions
- Rust error messages are **user-friendly**, suitable for direct MessageHandler display — no Python translation layer needed
- Batch operations use **collect-and-continue** pattern — process everything possible, return results + list of errors for partial success
- Rust uses its own **tracing crate** for internal logging — independent from Python's MessageHandler system

### Fallback behavior during migration
- Python fallback implementations **remain functional** throughout Phase 3 — safety net until Phase 5 handles fallback pruning
- Migration is **atomic per function** — each function migrates completely in one step, no partial migration states
- **Largest functions first** within each wrapper — maximum line-count reduction, highest impact early
- If Rust returns a better structure, **callers are updated in this phase** — no maintaining old return shapes in the wrapper

### Testing strategy
- **Golden file tests** verify Rust reimplementations match Python originals — capture Python outputs before migration as regression baseline
- **Golden files are mandatory** before every migration — no function migrates without a captured Python behavior baseline
- Full test coverage on **both Rust and Python sides** — Rust tests the logic in `-core` crates, Python tests verify the thin wrapper integration
- **Exact match required** between Python and Rust outputs — if Rust produces different output (formatting, encoding, paths), fix Rust to match Python exactly

</decisions>

<specifics>
## Specific Ideas

- Pure marshalling means the wrapper is literally: convert args, call Rust, convert return value. No conditionals, no error handling logic, no formatting.
- Async APIs from Rust means the existing async patterns in Python wrappers can be preserved without wrapper-level async coordination.
- "Collect and continue" for batch operations aligns with crash log scanning where you want all results even if some files have issues.
- Golden files before migration creates an auditable record of what Python produced, making it safe to delete Python logic after verified Rust migration.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-wrapper-thinning*
*Context gathered: 2026-02-02*
