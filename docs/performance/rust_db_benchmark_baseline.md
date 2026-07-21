# Rust DB Benchmark Baseline

This document defines the canonical scenario IDs, metric schema, and comparison format for the Rust DB baseline work in:

- `classic-database-core`
- `classic-scanlog-core` (FormID resolution paths that perform DB lookups)

## Scope

The baseline covers DB-heavy Rust paths only. It does not change production scanning behavior; it standardizes measurement and regression reporting.

## Canonical Scenario Matrix

Use these scenario IDs exactly in benchmark output and comparison reports.

| Scenario ID | Crate | Intent | Primary API Path | Input Class |
|---|---|---|---|---|
| `db_single_lookup/cold_hit` | `classic-database-core` | Single hit with cache reset each iteration | `DatabasePool::get_entry` | 1 lookup |
| `db_single_lookup/warm_hit` | `classic-database-core` | Single hit from warm cache | `DatabasePool::get_entry` | 1 lookup |
| `db_single_lookup/cold_miss` | `classic-database-core` | Single miss across DB set | `DatabasePool::get_entry` | 1 lookup |
| `db_batch_lookup/small_32` | `classic-database-core` | Batch lookup, small class | `DatabasePool::get_entries_batch` | 32 pairs |
| `db_batch_lookup/medium_256` | `classic-database-core` | Batch lookup, medium class | `DatabasePool::get_entries_batch` | 256 pairs |
| `db_batch_lookup/large_1024` | `classic-database-core` | Batch lookup, large class | `DatabasePool::get_entries_batch` | 1024 pairs |
| `db_multi_db_fallback/secondary_only_hit` | `classic-database-core` | Multi-DB lookup with result present in non-primary fixture DB | `DatabasePool::get_entries_batch` | 1 pair |
| `db_multi_db_fallback/miss_all` | `classic-database-core` | Multi-DB miss path (all DBs checked) | `DatabasePool::get_entry` | 1 lookup |
| `db_multi_db_budget/secondary_only_hit/budget_1` | `classic-database-core` | Multi-DB lookup under low global budget (clamped) | `DatabasePool::get_entries_batch` | 1 pair |
| `db_multi_db_budget/secondary_only_hit/budget_2` | `classic-database-core` | Multi-DB lookup at floor-equivalent global budget | `DatabasePool::get_entries_batch` | 1 pair |
| `db_multi_db_budget/secondary_only_hit/budget_8` | `classic-database-core` | Multi-DB lookup with higher global budget | `DatabasePool::get_entries_batch` | 1 pair |
| `db_multi_db_budget/miss_all/budget_1` | `classic-database-core` | Multi-DB miss path under low global budget (clamped) | `DatabasePool::get_entry` | 1 lookup |
| `db_multi_db_budget/miss_all/budget_2` | `classic-database-core` | Multi-DB miss path at floor-equivalent global budget | `DatabasePool::get_entry` | 1 lookup |
| `db_multi_db_budget/miss_all/budget_8` | `classic-database-core` | Multi-DB miss path with higher global budget | `DatabasePool::get_entry` | 1 lookup |
| `scanlog_formid_resolution/cold_small_32` | `classic-scanlog-core` | Aggregate semantic FormID extract + strict DB-backed resolve with cold cache | `FormIDFindingAnalyzer::analyze` over `FormIdValueLookup` | 32 FormIDs |
| `scanlog_formid_resolution/cold_medium_128` | `classic-scanlog-core` | Aggregate semantic FormID extract + strict DB-backed resolve with cold cache | Same as above | 128 FormIDs |
| `scanlog_formid_resolution/cold_large_512` | `classic-scanlog-core` | Aggregate semantic FormID extract + strict DB-backed resolve with cold cache | Same as above | 512 FormIDs |
| `scanlog_formid_resolution/warm_medium_128` | `classic-scanlog-core` | Aggregate semantic FormID extract + strict DB-backed resolve with warm cache | Same as above | 128 FormIDs |

## Deterministic Fixture Contract

Benchmark fixtures must be deterministic and locally generated:

- Use generated temporary SQLite files (no random data, no network I/O).
- Use a fixed plugin/prefix map and deterministic FormID suffix generation.
- Keep fixture DBs local-only; do not commit captured run artifacts.
- Keep scenario IDs stable even if fixture internals evolve.

## Baseline Metric Schema

Per-scenario metrics should be represented with these fields:

| Field | Type | Description |
|---|---|---|
| `scenario_id` | string | Canonical scenario ID from matrix above |
| `metric_unit` | string | Always `ns` for Criterion point estimates |
| `mean_ns` | number | Criterion mean point estimate (nanoseconds) |
| `median_ns` | number | Criterion median point estimate (nanoseconds) |
| `std_dev_ns` | number | Criterion standard deviation point estimate (nanoseconds) |
| `sample_count` | number | Sample count from Criterion estimate data |

## Run Metadata Schema

Every baseline/comparison report should include:

| Field | Type | Description |
|---|---|---|
| `baseline_name` | string | Baseline identifier used by Criterion |
| `candidate_name` | string | Candidate run identifier (typically `new`) |
| `bench_mode` | string | `quick` or `thorough` |
| `generated_at_utc` | string | ISO-8601 timestamp |
| `toolchain` | string | `rustc --version` summary |
| `os` | string | Host OS summary |
| `workspace_root` | string | Repository root used for execution |

## Comparison Record Schema

Per-scenario comparison records should include:

| Field | Type | Description |
|---|---|---|
| `scenario_id` | string | Canonical scenario ID |
| `baseline_mean_ns` | number | Baseline mean point estimate |
| `current_mean_ns` | number | Candidate mean point estimate |
| `delta_ns` | number | `current_mean_ns - baseline_mean_ns` |
| `delta_percent` | number | Relative change percentage |
| `classification` | string | `improved`, `within_threshold`, `warning`, or `fail` |

Classification thresholds use repository policy defaults:

- Warning: regression `> 5%`
- Fail: regression `> 10%`

## Local Artifact Policy

Baseline capture artifacts are local-only:

- Keep Criterion baselines in `ClassicLib-rs/target/criterion/` (gitignored).
- Optional exported comparison JSON files are local workflow artifacts unless a PR explicitly requests committing reports.

## Standard Command Set

Run all commands from repository root:

```powershell
# 1) Fast compile/smoke check for the DB baseline suite
pwsh -ExecutionPolicy Bypass -File scripts/bench/run_benchmarks.ps1 -Suite rust-db-baseline -Mode quick

# 2) Capture or refresh local baseline (thorough mode)
pwsh -ExecutionPolicy Bypass -File scripts/bench/run_benchmarks.ps1 -Suite rust-db-baseline -Mode thorough -SaveBaseline -BaselineName "db-baseline-main"

# 3) Compare candidate run against baseline with per-scenario deltas
pwsh -ExecutionPolicy Bypass -File scripts/bench/compare_baselines.ps1 -Suite rust-db-baseline -Mode thorough -Baseline "db-baseline-main" -ExportJson "ClassicLib-rs/target/criterion/db-delta-report.json"
```

Fast-path command set limited to canonical DB baseline scenarios:

```powershell
pwsh -ExecutionPolicy Bypass -File scripts/bench/run_benchmarks.ps1 -Suite rust-db-baseline -Mode quick -Filter "db_|scanlog_formid_resolution"
pwsh -ExecutionPolicy Bypass -File scripts/bench/compare_baselines.ps1 -Suite rust-db-baseline -Mode quick -Baseline "db-baseline-main" -BenchFilter "db_|scanlog_formid_resolution" -ScenarioFilter "^(db_|scanlog_formid_resolution)"
```

## Delta Workflow

`compare_baselines.ps1` reports one record per scenario with:

- `baseline_mean_ns`
- `current_mean_ns`
- `delta_ns` (absolute)
- `delta_percent` (relative)
- `classification` (`improved` / `within_threshold` / `warning` / `fail`)

The script can run the candidate benchmark pass automatically, then parse Criterion's
`new/estimates.json` and `<baseline>/estimates.json` files for each matching scenario.

## Threshold Policy

Thresholds remain:

- Warning if regression is `> 5%`
- Fail if regression is `> 10%`

Interpretation:

- Positive `delta_percent` means slower than baseline.
- Negative `delta_percent` means faster than baseline.

## Reproducibility Validation Procedure

When validating reproducibility on one host:

1. Use the same machine, power profile, and benchmark mode (`thorough` for baseline-quality runs).
2. Run baseline capture once, then run at least two candidate comparisons against the same baseline.
3. Confirm scenario IDs are unchanged and review per-scenario `delta_percent`.
4. Treat runs as comparable when the majority of scenarios stay within the configured threshold band.

### Validation Notes (Local quick-mode check)

Two repeated local quick-mode comparisons were executed against the same baseline:

- Scenario set remained stable (`12/12` scenario IDs matched across runs).
- Artifacts remained structurally comparable (same schema and scenario keys).
- Quick mode showed expected variance on short-running scenarios.

Interpretation: use quick mode for smoke checks, but use thorough mode for baseline-quality acceptance decisions.

## Baseline Refresh and Reporting Rules

Refresh baseline when at least one of these changes:

- Scenario matrix changes (new/removed/renamed scenario IDs)
- Fixture contract changes that alter benchmark inputs materially
- Major toolchain/runtime environment shifts that make old baselines non-comparable

For follow-up Rust DB optimization work:

- Include a benchmark delta report against the latest agreed baseline.
- Call out any `warning` or `fail` scenarios and planned follow-up actions.

### Tuning Notes: FormID Batch Lookup Integration (2026-02-26)

- `FormIDFindingAnalyzer::analyze` now stages resolved identifiers and performs one strict `FormIdValueLookup::lookup_batch` operation.
- Query chunking and its bounded defaults belong to `classic-database-core`; scanlog no longer owns a separate FormID batch-size constant.
- Quick-mode comparison against baseline `db-baseline-local-v2` (export: `ClassicLib-rs/target/criterion/formid-batch-delta.json`) showed large cold-path gains:
  - `cold_small_32`: `-89.44%`
  - `cold_medium_128`: `-90.25%`
  - `cold_large_512`: `-90.67%`
- Trade-off observed: `warm_medium_128` regressed (`+98.62%`, classified `fail`), likely from fixed batch orchestration overhead when cache is already hot.
- Follow-up tuning direction: add adaptive fast-path gating (e.g., bypass batching for very small/hot candidate sets) and re-run thorough-mode comparisons before changing thresholds.

### Tuning Notes: Bounded Query Cache Lifecycle (2026-02-27)

`classic-database-core::DatabasePool` now enforces a bounded cache with deterministic eviction and hybrid proactive cleanup. New `get_stats()` lifecycle fields:

- `cache_evictions`: Entries evicted to enforce cache capacity.
- `cleanup_runs`: Number of proactive expired-entry cleanup passes.
- `cleanup_removed`: Total expired entries removed by proactive cleanup.
- `cache_capacity`: Active cache capacity setting.
- `cleanup_threshold`: Active lookup-operation threshold before cleanup is considered.
- `cleanup_interval_seconds`: Active minimum interval gate between cleanup runs.

#### Safe defaults for long-running scans

- `cache_capacity`: `20_000` entries.
- `cleanup_threshold`: `2048` lookup operations.
- `cleanup_interval_seconds`: `30` seconds.

These defaults cap memory growth while avoiding over-aggressive cleanup churn in hot paths.

#### Operational guidance

- If `cache_evictions` climbs rapidly with stable/low `cache_hits`, increase `cache_capacity` to preserve reuse.
- If stale entries accumulate (high `cache_size`, low `cleanup_removed`), reduce `cleanup_threshold` or shorten `cleanup_interval_seconds`.
- If CPU overhead increases from maintenance work, raise `cleanup_threshold` and/or `cleanup_interval_seconds` first before raising capacity.

#### Benchmark delta snapshot (quick mode)

Run:

```powershell
pwsh -ExecutionPolicy Bypass -File scripts/bench/compare_baselines.ps1 -Suite rust-db-baseline -Mode quick -Baseline "db-baseline-main" -BenchFilter "db_|scanlog_formid_resolution" -ScenarioFilter "^(db_|scanlog_formid_resolution)" -ExportJson "ClassicLib-rs/target/criterion/db-delta-report.json"
```

Result summary from `ClassicLib-rs/target/criterion/db-delta-report.json`:

- Total scenarios: `12`
- `improved`: `6`
- `within_threshold`: `4`
- `warning`: `1` (`db_single_lookup/cold_miss`, `+7.00%`)
- `fail`: `1` (`db_multi_db_fallback/miss_all`, `+16.88%`)

Interpretation: bounded-cache changes improve most cold/warm scanlog formid-resolution scenarios, but miss-heavy multi-db fallback paths need follow-up tuning before treating the change as a net benchmark win.

### Tuning Notes: Global DB Connection Budgeting (2026-02-26)

`classic-database-core::DatabasePool` now treats `max_connections` as a global budget distributed deterministically across active DB pools, with low-budget clamp to keep each active pool nonzero.

#### Multi-DB budget scenario sweep (quick mode)

Run:

```powershell
pwsh -ExecutionPolicy Bypass -File scripts/bench/run_benchmarks.ps1 -Suite rust-db-baseline -Mode quick -Filter "db_multi_db_budget"
```

Observed timing bands (quick mode):

- `db_multi_db_budget/secondary_only_hit/budget_1`: ~`120-123 us`
- `db_multi_db_budget/secondary_only_hit/budget_2`: ~`122-127 us`
- `db_multi_db_budget/secondary_only_hit/budget_8`: ~`108-113 us`
- `db_multi_db_budget/miss_all/budget_1`: ~`189-198 us`
- `db_multi_db_budget/miss_all/budget_2`: ~`202-210 us`
- `db_multi_db_budget/miss_all/budget_8`: ~`199-202 us`

Interpretation: higher budget improves secondary-hit throughput; miss-all paths remain sensitive and should be tracked with baseline comparisons.

#### Baseline comparison focus (`db_multi_db_fallback`)

Run:

```powershell
pwsh -ExecutionPolicy Bypass -File scripts/bench/compare_baselines.ps1 -Suite rust-db-baseline -Mode quick -Baseline "db-baseline-main" -BenchFilter "db_multi_db_fallback" -ScenarioFilter "^db_multi_db_fallback/" -ExportJson "ClassicLib-rs/target/criterion/db-multi-db-delta-report.json"
```

Quick-mode result summary (`db-multi-db-delta-report.json`):

- `db_multi_db_fallback/secondary_only_hit`: `+0.73%` (`within_threshold`)
- `db_multi_db_fallback/miss_all`: `+14.13%` (`fail`)

Operational guidance: keep global-budget allocator enabled for safety and determinism; prioritize follow-up optimization on miss-heavy multi-db fallback path before raising regression thresholds.
