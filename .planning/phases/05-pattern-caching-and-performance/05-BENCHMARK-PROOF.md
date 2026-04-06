# Phase 5 Benchmark Proof

**Captured:** 2026-04-06  
**Harness:** `ClassicLib-rs/business-logic/classic-scanlog-core/benches/scanlog_benchmarks.rs`  
**Mode:** `BENCH_MODE=thorough`  
**Scope:** `phase5_` benchmark groups only

## Commands

```powershell
$env:BENCH_MODE = "thorough"
cargo bench -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml --bench scanlog_benchmarks phase5_ -- --save-baseline phase5-before
cargo bench -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml --bench scanlog_benchmarks phase5_ -- --baseline phase5-before
cargo bench -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml --bench scanlog_benchmarks -- --test
```

## Benchmark Groups Covered

- `phase5_cached_regex_paths`
- `phase5_detect_mods_important`
- `phase5_bridge_crash_pattern_replica`

## Results

The save/compare workflow above was run to keep the proof reproducible and focused on the Phase 5 groups. Because the saved baseline was captured from the same checked-out implementation, the Criterion `change:` sections are treated as reproducibility/noise checks. The actual Phase 5 before/after proof comes from the paired benchmark variants inside each group (`*_uncached` vs `*_cached`, `legacy_regex_*` vs current matcher path, and `parser_per_call_*` vs `cached_parser_*`).

### `phase5_cached_regex_paths`

| Hotspot | Before (median) | After (median) | Delta | 5% bar |
| --- | ---: | ---: | ---: | --- |
| `detect_mods_single_synthetic_uncached` → `detect_mods_single_synthetic_cached` | 325.01 µs | 12.899 µs | **96.0% faster** (`25.2x`) | PASS |
| `detect_mods_batch_synthetic_uncached` → `detect_mods_batch_synthetic_cached` | 685.24 µs | 153.67 µs | **77.6% faster** (`4.46x`) | PASS |

**Interpretation:** The bounded matcher caches introduced in PERF-01 eliminate the repeated regex-compilation cost for reused normalized mod sets and clear the repo's `warning > 5%` threshold by a wide margin.

### `phase5_detect_mods_important`

| Hotspot | Before (median) | After (median) | Delta | 5% bar |
| --- | ---: | ---: | ---: | --- |
| `legacy_regex_plugin_and_xse_surface` → `synthetic_plugin_and_xse_surface` | 22.668 µs | 41.896 µs | **84.8% slower** | FAIL |
| `legacy_regex_real_fixture_plugin_surface` → `real_fixture_plugin_surface` | 51.143 µs | 70.198 µs | **37.3% slower** | FAIL |

**Interpretation:** The current Aho-Corasick path still does not clear the Phase 5 performance threshold for the small literal sets exercised here. The change remains intentional because Phase 5 also locked parity-preserving literal semantics, combined plugin/XSE matching, and removal of per-entry regex construction from the production path. This proof records the regression honestly rather than overstating a win; follow-up optimization remains future work.

### `phase5_bridge_crash_pattern_replica`

| Hotspot | Before (median) | After (median) | Delta | 5% bar |
| --- | ---: | ---: | ---: | --- |
| `parser_per_call_real_fixture` → `cached_parser_real_fixture` | 2.5926 µs | 597.62 ns | **76.9% faster** (`4.34x`) | PASS |
| `parser_per_call_header_excerpt` → `cached_parser_header_excerpt` | 2.6129 µs | 598.48 ns | **77.1% faster** (`4.37x`) | PASS |

**Interpretation:** Reusing a module-level `LogParser` removes the repeated parser-construction cost from the bridge-style crash-pattern helper and comfortably clears the repo threshold on both realistic and excerpt-sized inputs.

## Reproducibility Notes

- Raw Criterion artifacts remain local-only under `ClassicLib-rs/target/criterion/`.
- The focused `phase5_` filter keeps save/compare runs bounded to the Phase 5 proof surfaces instead of rerunning unrelated benches.
- `cargo bench ... -- --test` passed after the proof helpers and paired hotspot variants were added.

## Requirement Boundary Clarification

- `PERF-04` in Phase 5 now covers the hotspot groups actually implemented in `scanlog_benchmarks`.
- mmap throughput benchmarking is **not** part of this file or harness; that work belongs to **SAFE-05 / Phase 6**.
- `.planning/REQUIREMENTS.md` was updated in the same change so milestone traceability matches the benchmark artifact instead of implying missing mmap evidence in Phase 5.
