# Phase 6 Benchmark Proof

**Captured:** 2026-04-06  
**Harness:** `ClassicLib-rs/business-logic/classic-file-io-core/benches/file_io_benchmarks.rs`  
**Mode:** `BENCH_MODE=thorough`  
**Scope:** `phase6_mmap_variants`

## Commands

```powershell
$env:BENCH_MODE = "thorough"
cargo bench -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml --bench file_io_benchmarks phase6_mmap_variants -- --save-baseline phase6-mmap-baseline
cargo bench -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml --bench file_io_benchmarks phase6_mmap_variants -- --baseline phase6-mmap-baseline
cargo bench -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml --bench file_io_benchmarks phase6_mmap_variants -- --test
```

## Benchmark Group Covered

- `phase6_mmap_variants`

## Tested Sizes

- `1_048_576 + 4_096` bytes (`1mb_plus_4kb`) — just above the 1 MiB mmap threshold
- `4 * 1_048_576` bytes (`4mb`)
- `16 * 1_048_576` bytes (`16mb`)

## Results

The benchmark compares the three file-backed mmap constructors the Phase 6 research called out for Windows validation: `map()`, `map_copy()`, and `map_copy_read_only()`. Setup stays outside the timed loop: synthetic UTF-8 crash-log-like files are written once, then each iteration measures the mapping plus the same encoding-detect/decode path production pays.

The `--save-baseline` / `--baseline` rerun is treated as a reproducibility check, not a before/after proof, because both runs use the same checked-out implementation. The first thorough capture below is the source of truth for the throughput comparison.

| Size | `map` median | `map_copy` median | `map_copy_read_only` median | `map_copy_read_only` vs best | Call |
| --- | ---: | ---: | ---: | ---: | --- |
| `1mb_plus_4kb` | 507.86 µs / 1.9304 GiB/s | 505.87 µs / 1.9380 GiB/s | **500.72 µs / 1.9579 GiB/s** | Best in run | PASS |
| `4mb` | 1.9126 ms / 2.0424 GiB/s | 1.9192 ms / 2.0354 GiB/s | **1.9010 ms / 2.0549 GiB/s** | Best in run | PASS |
| `16mb` | 7.6840 ms / 2.0334 GiB/s | **7.6505 ms / 2.0423 GiB/s** | 8.3040 ms / 1.8816 GiB/s | **8.5% slower** than best | WARN, still acceptable |

## Windows Acceptability Call

`map_copy_read_only()` is acceptable for Phase 6 Windows validation.

- It was the fastest variant on the near-threshold and 4 MiB cases, so the safer mapping does **not** impose a measurable penalty where the mmap branch first becomes relevant.
- On the 16 MiB case it trailed the best result (`map_copy`) by about **8.5%**, which exceeds the repo's existing `warning > 5%` bar from the performance baseline guidance but stays below a `fail > 10%` style regression line.
- Because Phase 6 is a safety-hardening change rather than a pure throughput optimization, that largest-input slowdown is still within the repo's acceptable tradeoff range for adopting the safer snapshot-style mapping on Windows.

This is intentionally conservative wording: the benchmark shows the repository's chosen `map_copy_read_only()` strategy is acceptable on the measured Windows host, not that upstream `memmap2` universally guarantees concurrent-modification safety.

## Reproducibility Notes

- Raw Criterion artifacts remain local-only under `ClassicLib-rs/target/criterion/`.
- Do **not** commit the `phase6-mmap-baseline` directory by default.
- `gnuplot` was not installed locally, so Criterion used its fallback plotting backend; this does not affect the markdown proof.
- `cargo bench ... phase6_mmap_variants -- --test` passed after the benchmark group landed.
