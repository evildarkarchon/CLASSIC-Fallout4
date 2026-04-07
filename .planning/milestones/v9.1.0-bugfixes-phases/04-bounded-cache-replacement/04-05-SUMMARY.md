---
phase: 04-bounded-cache-replacement
plan: 05
subsystem: api
tags: [python, cache, parity, pyo3, stubs]
requires:
  - phase: 04-01
    provides: YAML cache stats and bounded core contract
  - phase: 04-02
    provides: settings cache stats and canonical field set
  - phase: 04-03
    provides: hash cache stats/reset helpers in Rust core
provides:
  - canonical Python cache stats contracts for YAML, settings, and hash helpers
  - Python file-io hash cache smoke coverage and refreshed parity governance metadata
  - registry-only runtime coverage generation for Python cache helper tracking
affects: [04-06, python-bindings, parity]
tech-stack:
  added: []
  patterns: [typed dict cache contracts, registry-only runtime coverage entries, thin PyO3 cache adapters]
key-files:
  created:
    - .planning/phases/04-bounded-cache-replacement/deferred-items.md
  modified:
    - ClassicLib-rs/python-bindings/classic-yaml-py/src/lib.rs
    - ClassicLib-rs/python-bindings/classic-yaml-py/classic_yaml.pyi
    - ClassicLib-rs/python-bindings/classic-settings-py/src/lib.rs
    - ClassicLib-rs/python-bindings/classic-settings-py/classic_settings.pyi
    - ClassicLib-rs/python-bindings/classic-file-io-py/src/hash.rs
    - ClassicLib-rs/python-bindings/classic-file-io-py/classic_file_io.pyi
    - ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py
    - ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json
    - docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json
    - docs/implementation/python_api_parity/baseline/runtime_coverage_summary.md
    - docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json
    - docs/implementation/python_api_parity/governance/tier2_wave_manifest.json
    - tools/binding_parity_runtime_coverage.py
key-decisions:
  - "Use explicit TypedDict cache stats aliases in Python stubs so the canonical five-field contract is visible to static tooling."
  - "Track Python hash cache helpers as registry-only Tier-2 runtime coverage instead of broadening the Python parity parser to every aux module."
  - "Keep FileHasher.cache_size() as a deferred compatibility adapter while cache_stats/reset_cache_stats own the Phase 4 runtime smoke contract."
patterns-established:
  - "Python cache adapters should expose only hits, misses, hit_rate, size, and capacity on the shared stats object."
  - "Registry-only parity entries are acceptable for Python aux exports when the baseline parser does not model that module family yet."
requirements-completed: [CONS-03]
duration: 15 min
completed: 2026-04-06
---

# Phase 04 Plan 05: Python Cache Contract Alignment Summary

**Python now exposes the Phase 4 cache stats contract for YAML, settings, and hashes, with typed stubs, hash-cache smoke coverage, and parity metadata that tracks the new helper surface.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-04-06T04:48:32Z
- **Completed:** 2026-04-06T05:03:23Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments
- Replaced Python YAML/settings cache stats drift with the canonical `hits`/`misses`/`hit_rate`/`size`/`capacity` contract and documented it in `.pyi` files.
- Added Python `FileHasher.cache_stats()` and `FileHasher.reset_cache_stats()` plus smoke coverage for miss/hit/reset/capacity behavior.
- Refreshed Python runtime coverage and governance artifacts so cache helper coverage is classified immediately instead of remaining implicit.

## Task Commits

Each task was committed atomically:

1. **Task 1: Normalize Python YAML and settings cache stats adapters and stubs** - `26411f5f` (feat)
2. **Task 2: Add Python hash cache stats helpers and refresh parity artifacts with the repo binding workflow** - `ba9af442` (feat)
3. **Follow-up fix: Keep cache parity verification buildable** - `c5eff9be` (fix)

## Files Created/Modified
- `ClassicLib-rs/python-bindings/classic-yaml-py/src/lib.rs` - Switched YAML cache stats exposure to the canonical five-field dict.
- `ClassicLib-rs/python-bindings/classic-yaml-py/classic_yaml.pyi` - Declared a `YamlCacheStats` TypedDict and removed the old `entries`/`memory_bytes` contract.
- `ClassicLib-rs/python-bindings/classic-settings-py/src/lib.rs` - Removed settings-specific `keys` leakage from `cache_stats()` and returned `capacity` instead.
- `ClassicLib-rs/python-bindings/classic-settings-py/classic_settings.pyi` - Declared the settings cache stats/reset helpers explicitly.
- `ClassicLib-rs/python-bindings/classic-file-io-py/src/hash.rs` - Added `cache_stats()` and `reset_cache_stats()` thin adapters over `FileHasher`.
- `ClassicLib-rs/python-bindings/classic-file-io-py/classic_file_io.pyi` - Declared the hash cache stats contract in the Python stub.
- `ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py` - Added runtime smoke coverage for the hash cache helper lifecycle.
- `ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json` - Classified the new Python hash cache helpers as runtime-verified Tier-2 aux coverage.
- `docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json` - Updated tracked/runtime/deferred totals for the cache helper additions.
- `docs/implementation/python_api_parity/baseline/runtime_coverage_summary.md` - Updated the human-readable Python runtime coverage summary.
- `docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json` - Recorded `FileHasher.cache_size()` as a deferred compatibility adapter.
- `docs/implementation/python_api_parity/governance/tier2_wave_manifest.json` - Added the aux wave entry for the deferred cache-size adapter.
- `tools/binding_parity_runtime_coverage.py` - Allowed runtime summaries to retain registry-only Python cache helper entries.

## Decisions Made
- Used TypedDict aliases instead of loose `dict[str, int]` stubs so Python callers see the exact cache stats shape.
- Kept cache-specific extras outside the canonical stats object; settings keys stay on `cache_keys()` and hash compatibility size stays on `cache_size()`.
- Solved Python aux parity tracking by extending runtime coverage summary generation, not by expanding the parity contract parser to every aux module in one plan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Restored YAML binding imports after broader crate build verification**
- **Found during:** Final verification
- **Issue:** `cargo build -p classic-yaml-py -p classic-settings-py -p classic-file-io-py` failed because `classic-yaml-py/src/lib.rs` still used `HashMap` elsewhere after the cache-stats refactor removed its import.
- **Fix:** Reintroduced the `std::collections::HashMap` import and rebuilt the Python binding crates.
- **Files modified:** `ClassicLib-rs/python-bindings/classic-yaml-py/src/lib.rs`
- **Verification:** `cargo build -p classic-yaml-py -p classic-settings-py -p classic-file-io-py --manifest-path ClassicLib-rs/Cargo.toml`
- **Committed in:** `c5eff9be`

**2. [Rule 3 - Blocking] Preserved aux cache helper coverage in generated Python runtime summaries**
- **Found during:** Final verification
- **Issue:** Python parity summary generation dropped the new cache helper registry rows because they were registry-only aux bindings outside the existing contract parser scope.
- **Fix:** Extended `tools/binding_parity_runtime_coverage.py` to keep unmatched registry entries as `registry_only` tracked surfaces so baseline summaries reflect the committed cache helper metadata.
- **Files modified:** `tools/binding_parity_runtime_coverage.py`
- **Verification:** `python tools/python_api_parity/check_parity_gate.py --repo-root .` regenerated runtime coverage artifacts with the aux cache helper rows present.
- **Committed in:** `c5eff9be`

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes were required to keep verification aligned with the updated Python cache helper surface. No scope creep beyond build/parity correctness.

## Issues Encountered
- `uv venv ClassicLib-rs/python-bindings/.venv` reported that the bindings-local environment already existed, so the task reused the existing `.venv` and continued with dependency installation, rebuild, and smoke testing.
- `python tools/python_api_parity/check_parity_gate.py --repo-root .` still reports one newly uncovered surface, `binding:rust:FcxResetError`, from unrelated in-flight scanlog workspace changes. This out-of-scope issue was logged to `.planning/phases/04-bounded-cache-replacement/deferred-items.md` and not fixed in this plan.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- C++ parity work can now mirror the same canonical cache stats keys already committed for Node and Python.
- Python stubs and runtime metadata are aligned for cache helpers, but the unrelated `FcxResetError` parity drift should be resolved by the owner of the scanlog workspace changes before relying on a clean global Python parity gate.

## Self-Check: PASSED

- FOUND: .planning/phases/04-bounded-cache-replacement/04-05-SUMMARY.md
- FOUND: 26411f5f
- FOUND: ba9af442
- FOUND: c5eff9be
