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
| `scanlog_formid_resolution/cold_small_32` | `classic-scanlog-core` | FormID extract + DB-backed resolve with cold cache | `FormIDAnalyzerCore::extract_formids` + `formid_match` (`show_formid_values=true`) | 32 FormIDs |
| `scanlog_formid_resolution/cold_medium_128` | `classic-scanlog-core` | FormID extract + DB-backed resolve with cold cache | Same as above | 128 FormIDs |
| `scanlog_formid_resolution/cold_large_512` | `classic-scanlog-core` | FormID extract + DB-backed resolve with cold cache | Same as above | 512 FormIDs |
| `scanlog_formid_resolution/warm_medium_128` | `classic-scanlog-core` | FormID extract + DB-backed resolve with warm cache | Same as above | 128 FormIDs |

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
