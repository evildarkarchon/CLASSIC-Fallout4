# Phase 5 Benchmark Proof

**Captured:** 2026-04-06  
**Harness:** `ClassicLib-rs/business-logic/classic-scanlog-core/benches/scanlog_benchmarks.rs`  
**Mode:** `BENCH_MODE=thorough`  
**Scope:** `phase5_` benchmark groups only

## Commands

```powershell
$env:BENCH_MODE = "thorough"
cargo bench -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml --bench scanlog_benchmarks phase5_detect_mods_important -- --save-baseline phase5-important-followup
cargo bench -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml --bench scanlog_benchmarks phase5_detect_mods_important -- --baseline phase5-important-followup
cargo bench -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml --bench scanlog_benchmarks -- --test
```

## Benchmark Groups Covered

- `phase5_cached_regex_paths`
- `phase5_detect_mods_important`
- `phase5_bridge_crash_pattern_replica`

## Results

The save/compare workflow above was rerun with an important-mod-only filter to keep this follow-up focused on the remaining hotspot. Because the saved baseline was captured from the same checked-out implementation, the Criterion `change:` sections are treated as reproducibility/noise checks. The actual Phase 5 before/after proof comes from the paired benchmark variants inside each group (`*_uncached` vs `*_cached`, `legacy_regex_*` vs current matcher path, and `parser_per_call_*` vs `cached_parser_*`).

### `phase5_cached_regex_paths`

| Hotspot | Before (median) | After (median) | Delta | 5% bar |
| --- | ---: | ---: | ---: | --- |
| `detect_mods_single_synthetic_uncached` → `detect_mods_single_synthetic_cached` | 325.01 µs | 12.899 µs | **96.0% faster** (`25.2x`) | PASS |
| `detect_mods_batch_synthetic_uncached` → `detect_mods_batch_synthetic_cached` | 685.24 µs | 153.67 µs | **77.6% faster** (`4.46x`) | PASS |

**Interpretation:** The bounded matcher caches introduced in PERF-01 eliminate the repeated regex-compilation cost for reused normalized mod sets and clear the repo's `warning > 5%` threshold by a wide margin.

### `phase5_detect_mods_important`

| Hotspot | Before (median) | After (median) | Delta | 5% bar |
| --- | ---: | ---: | ---: | --- |
| `legacy_regex_plugin_and_xse_surface` → `synthetic_plugin_and_xse_surface` | 28.938 µs | 5.906 µs | **79.6% faster** (`4.90x`) | PASS |
| `legacy_regex_real_fixture_plugin_surface` → `real_fixture_plugin_surface` | 52.366 µs | 40.424 µs | **22.8% faster** (`1.30x`) | PASS |

**Interpretation:** The follow-up clears the Phase 5 no-regression bar on both tracked surfaces. Task 1's cost-center slices showed that one-per-call matcher construction dominated the synthetic regression (`aho_compile_only_synthetic_literals`: `34.261 µs`), which justified moving `detect_mods_important` onto the same bounded matcher-cache pattern used elsewhere in Phase 5. After that cache landed, the real-fixture residual cost was mostly haystack preparation rather than matching (`aho_build_haystack_only_real_fixture_plugin_surface`: `35.695 µs` vs `aho_cached_match_only_real_fixture_plugin_surface`: `11.012 µs`), so the final optimization cut avoidable lowercase/string-allocation work by building the haystack in one pass and skipping the plugin-name set unless `exclude_when` is actually present.

#### Important-mod root-cause slices

| Slice | Median | Notes |
| --- | ---: | --- |
| `aho_compile_only_synthetic_literals` | 34.261 µs | Matcher compilation alone was slower than the legacy synthetic comparator, so uncached Aho construction could not meet the bar. |
| `aho_uncached_plugin_and_xse_surface` | 34.554 µs | Confirms the synthetic path regresses when the matcher is rebuilt each call. |
| `aho_cached_match_only_plugin_and_xse_surface` | 2.588 µs | With compile and haystack setup removed, literal matching itself is cheap. |
| `aho_build_haystack_only_real_fixture_plugin_surface` | 35.695 µs | After caching, most of the real-fixture cost came from lowercasing and concatenating the large plugin/XSE surface. |
| `aho_cached_match_only_real_fixture_plugin_surface` | 11.012 µs | Cached matching stayed well below the full-path real-fixture time, confirming haystack prep as the remaining dominant cost center. |

### `phase5_bridge_crash_pattern_replica`

| Hotspot | Before (median) | After (median) | Delta | 5% bar |
| --- | ---: | ---: | ---: | --- |
| `parser_per_call_real_fixture` → `cached_parser_real_fixture` | 2.5926 µs | 597.62 ns | **76.9% faster** (`4.34x`) | PASS |
| `parser_per_call_header_excerpt` → `cached_parser_header_excerpt` | 2.6129 µs | 598.48 ns | **77.1% faster** (`4.37x`) | PASS |

**Interpretation:** Reusing a module-level `LogParser` removes the repeated parser-construction cost from the bridge-style crash-pattern helper and comfortably clears the repo threshold on both realistic and excerpt-sized inputs.

## Reproducibility Notes

- Raw Criterion artifacts remain local-only under `ClassicLib-rs/target/criterion/`.
- The focused `phase5_detect_mods_important` filter keeps the follow-up bounded to the residual hotspot instead of rerunning unrelated Phase 5 benches.
- `cargo bench ... -- --test` passed after the proof helpers and paired hotspot variants were added.

## Requirement Boundary Clarification

- `PERF-04` in Phase 5 now covers the hotspot groups actually implemented in `scanlog_benchmarks`.
- mmap throughput benchmarking is **not** part of this file or harness; that work belongs to **SAFE-05 / Phase 6**.
- `.planning/REQUIREMENTS.md` was updated in the same change so milestone traceability matches the benchmark artifact instead of implying missing mmap evidence in Phase 5.
