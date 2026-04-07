---
phase: 07-consistency-sweep
verified: 2026-04-06T12:06:34.5788349Z
status: passed
score: 6/6 must-haves verified
---

# Phase 7: Consistency Sweep Verification Report

**Phase Goal:** The codebase uses only `std::sync::LazyLock` for lazy statics, eliminating the `once_cell` dependency where it is no longer needed.
**Verified:** 2026-04-06T12:06:34.5788349Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | `classic-scanlog-core` no longer imports `once_cell::sync::Lazy` or `once_cell::sync::OnceCell` directly | ✓ VERIFIED | Workspace audit found no direct runtime `once_cell` usage; `cargo test -p classic-scanlog-core` passed including `lazylock_static_audit` and `once_lock_migration_audit` |
| 2 | `RecordScanner` keeps its existing lazy per-instance matcher behavior via `std::sync::OnceLock` | ✓ VERIFIED | `record_scanner.rs` uses `OnceLock` fields plus `get_or_init(...)` with `AhoCorasickBuilder`; crate tests include `test_matchers_are_built_lazily_once_per_scanner_instance` |
| 3 | The scanlog contributor doc and crate manifest move in the same change as the source sweep | ✓ VERIFIED | `classic-scanlog-core/Cargo.toml` has no direct `once_cell`; `docs/api/classic-scanlog-core.md` documents `OnceLock`/`LazyLock` behavior |
| 4 | `classic-registry-core` and `classic-perf-core` use `std::sync::LazyLock` for their process-global stores | ✓ VERIFIED | `registry.rs` and `metrics.rs` both define `LazyLock<DashMap<...>> = LazyLock::new(DashMap::new)`; both crate test suites passed |
| 5 | No owned workspace manifest in the Phase 7 target set retains a direct `once_cell` declaration | ✓ VERIFIED | `ClassicLib-rs/Cargo.toml`, `classic-scanlog-core`, `classic-registry-core`, `classic-perf-core`, `classic-yaml-core`, `classic-settings-core`, and `classic-scangame-core` manifests contain no direct `once_cell` entry |
| 6 | The touched `docs/api` pages stop describing scanlog, registry, perf, or settings internals in terms of `once_cell` | ✓ VERIFIED | `classic-scanlog-core.md`, `classic-registry-core.md`, `classic-perf-core.md`, and `classic-settings-core.md` now describe `LazyLock`/`OnceLock`/`quick_cache` internals |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `ClassicLib-rs/business-logic/classic-scanlog-core/src/record_scanner.rs` | `OnceLock` matcher cache with lazy `get_or_init` flow | ✓ VERIFIED | Exists; substantive implementation; `OnceLock::new()` and `get_or_init(...)` present |
| `ClassicLib-rs/business-logic/classic-scanlog-core/src/fcx_handler.rs` | Global FCX handler migrated to std lazy static | ✓ VERIFIED | Exists; `GLOBAL_FCX_HANDLER: LazyLock<Mutex<FcxModeHandler>> = LazyLock::new(...)` |
| `ClassicLib-rs/business-logic/classic-scanlog-core/Cargo.toml` | Direct `once_cell` dependency removed | ✓ VERIFIED | Exists; no direct `once_cell` dependency remains |
| `docs/api/classic-scanlog-core.md` | Scanlog docs aligned to std lazy primitives | ✓ VERIFIED | Exists; documents `OnceLock` matcher caches and `LazyLock` caches |
| `ClassicLib-rs/business-logic/classic-registry-core/src/registry.rs` | Registry singleton migrated to std lazy initialization | ✓ VERIFIED | Exists; `static REGISTRY: LazyLock<DashMap<...>> = LazyLock::new(DashMap::new)` |
| `ClassicLib-rs/business-logic/classic-perf-core/src/metrics.rs` | Perf metrics singleton migrated to std lazy initialization | ✓ VERIFIED | Exists; `static METRICS: LazyLock<DashMap<...>> = LazyLock::new(DashMap::new)` |
| `ClassicLib-rs/Cargo.toml` | Workspace direct `once_cell` declaration removed | ✓ VERIFIED | Exists; `[workspace.dependencies]` no longer includes `once_cell` |
| `docs/api/classic-registry-core.md` | Registry docs aligned to std lazy storage | ✓ VERIFIED | Exists; describes `std::sync::LazyLock` global registry storage |
| `docs/api/classic-perf-core.md` | Perf docs aligned to std lazy storage | ✓ VERIFIED | Exists; describes `std::sync::LazyLock` global metrics storage |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `record_scanner.rs` | `aho_corasick::AhoCorasickBuilder` | `get_or_init` | ✓ WIRED | gsd-tools verified pattern `OnceLock|get_or_init`; builder closure still initializes lazily from instance data |
| `fcx_handler.rs` | `parking_lot::Mutex` | `LazyLock::new` | ✓ WIRED | gsd-tools verified `LazyLock::new`; global FCX handler remains a lazy process-global mutex |
| `classic-scanlog-core.md` | `record_scanner.rs` | std primitive wording | ✓ WIRED | gsd-tools verified `LazyLock|OnceLock` wording in docs |
| `registry.rs` | `dashmap::DashMap` | `LazyLock::new(DashMap::new)` | ✓ WIRED | gsd-tools verified exact lazy-init pattern |
| `metrics.rs` | `dashmap::DashMap` | `LazyLock::new(DashMap::new)` | ✓ WIRED | gsd-tools verified exact lazy-init pattern |
| `classic-settings-core.md` | `classic-settings-core/src/cache.rs` | `LazyLock`/`quick_cache` wording | ✓ WIRED | gsd-tools verified doc wording matches implementation |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `record_scanner.rs` | `record_matcher`, `ignore_matcher` | `self.lower_records` / `self.lower_ignore` via `get_or_init` + `AhoCorasickBuilder` | Yes | ✓ FLOWING |
| `registry.rs` | `REGISTRY` | `DashMap::new` process-global store used by `register/get/...` | Yes | ✓ FLOWING |
| `metrics.rs` | `METRICS` | `DashMap::new` process-global store used by `record_timing/get_summary` | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Scanlog crate still works after LazyLock/OnceLock migration | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml` | 298 unit tests + 2 migration audit tests + 58 doctests passed | ✓ PASS |
| Registry global store still works after LazyLock migration | `cargo test -p classic-registry-core --manifest-path ClassicLib-rs/Cargo.toml` | 25 unit tests + 18 doctests passed | ✓ PASS |
| Perf global store still works after LazyLock migration | `cargo test -p classic-perf-core --manifest-path ClassicLib-rs/Cargo.toml` | 16 unit tests + 9 doctests passed | ✓ PASS |
| Manifest cleanup still allows integrated workspace build | `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml` | Build completed successfully | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| `CONS-01` | `07-01-PLAN.md`, `07-02-PLAN.md` | Replace `once_cell::sync::Lazy` with `std::sync::LazyLock` across all crates still using `once_cell` | ✓ SATISFIED | No direct runtime source or manifest `once_cell` usage remains in workspace crates; scanlog/registry/perf source migrated; root and target manifests cleaned; touched docs aligned |

Orphaned requirements for Phase 7: none. `REQUIREMENTS.md` maps only `CONS-01` to Phase 7, and both Phase 7 plans account for it.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| — | — | None found in phase files after targeted scan | — | No blocker stub/placeholder patterns detected |

### Human Verification Required

None.

### Gaps Summary

No gaps found. Phase 7 achieved its goal: lazy statics across the workspace use `std::sync::LazyLock`, the remaining per-instance `OnceCell` case was migrated to `std::sync::OnceLock`, and direct `once_cell` dependency declarations were removed from the phase target manifests and root workspace manifest.

---

_Verified: 2026-04-06T12:06:34.5788349Z_
_Verifier: the agent (gsd-verifier)_
