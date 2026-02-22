## Why

`classic-pybridge-core` is a pure-Rust `rlib` placed in `business-logic/` whose sole consumer is `classic-pybridge-py` — it contains no domain logic, only Python bridge metrics and runtime coordination helpers. The two-crate split creates a redundant indirection layer (duplicate type definitions, `From` conversion boilerplate, extra crate compilation) with no architectural benefit, since the functionality is exclusively Python-facing and too thin to warrant isolation.

## What Changes

- **Remove** `classic-pybridge-core` crate from `ClassicLib-rs/business-logic/`
- **Remove** `"business-logic/classic-pybridge-core"` from workspace `Cargo.toml` members
- **Absorb** `metrics.rs` and `runtime.rs` modules directly into `classic-pybridge-py/src/`
- **Delete** all `From<classic_pybridge_core::X>` conversion impls in `classic-pybridge-py/src/lib.rs` (types now defined locally)
- **Update** `classic-pybridge-py/Cargo.toml` to depend on `classic-shared-core`, `classic-perf-core`, and shared workspace deps directly (replacing the single `classic-pybridge-core` dep)
- **Fix** redundant nested lock in `metrics.rs`: remove outer `parking_lot::RwLock<ThreadMetrics>` wrapping a `DashMap` — the `DashMap` handles concurrent access alone
- **Migrate** tests from `classic-pybridge-core` to `classic-pybridge-py`
- **Document** the exception in `CLAUDE.md`, `AGENTS.md`, and `GEMINI.md`

## Capabilities

### New Capabilities

- `pybridge-self-contained`: `classic-pybridge-py` owns its bridge metrics and runtime helpers directly, with no `-core` counterpart crate

### Modified Capabilities

*(none — no spec-level behavior changes; the Python API surface of `classic_pybridge` is unchanged)*

## Impact

- **Deleted**: `ClassicLib-rs/business-logic/classic-pybridge-core/` (entire crate)
- **Modified**: `ClassicLib-rs/python-bindings/classic-pybridge-py/` (absorbs logic, new sub-modules)
- **Modified**: `ClassicLib-rs/Cargo.toml` (workspace member removed)
- **Modified**: `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` (architecture exception documented)
- **Python API**: unchanged — `import classic_pybridge` continues to work identically
- **Performance**: minor improvement — removes one `From` conversion chain per call and one unnecessary lock acquisition per metric record
