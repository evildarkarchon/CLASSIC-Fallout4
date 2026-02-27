## Why

Current Rust database optimization work lacks a stable baseline for measuring wins and detecting regressions. We need repeatable, versioned benchmarks before stacking additional performance changes.

## What Changes

- Add a Rust-first benchmark baseline for database-heavy paths in `classic-database-core` and scan-time FormID resolution paths in `classic-scanlog-core`.
- Define standard benchmark scenarios (single lookup, batch lookup, cache warm/cold behavior, multi-db behavior) with consistent dataset sizes.
- Define baseline output artifacts and comparison guidance so follow-up changes can report deltas against a known reference.
- Add lightweight guardrails for regression detection in local/CI-oriented benchmark runs (non-blocking by default unless explicitly enabled).

## Capabilities

### New Capabilities
- `rust-db-performance-baseline`: Provide reproducible benchmark scenarios, baseline metrics, and comparison workflow for Rust database and FormID lookup paths.

### Modified Capabilities
- (none)

## Impact

- Affected code:
  - `ClassicLib-rs/business-logic/classic-database-core/`
  - `ClassicLib-rs/business-logic/classic-scanlog-core/`
  - `tests/benchmarks/` and related benchmark docs
- Affected workflows:
  - Local performance validation for all future Rust DB optimization changes
  - Optional CI/regression verification path for benchmark drift
- No runtime behavior change to production scanning logic in this change; this establishes measurement infrastructure only.
