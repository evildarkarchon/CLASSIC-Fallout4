# Phase 18: Tech Debt Cleanup - Research

**Researched:** 2026-02-04
**Domain:** Code quality, documentation, API consistency
**Confidence:** HIGH

## Summary

This phase addresses four specific tech debt items identified in the v8.3.0 milestone audit. All items are well-defined code changes with minimal risk.

The tech debt consists of:
1. **GIL benchmarks not using shared config** - Three benchmark files use `Criterion::default()` instead of `configure_criterion()` from Phase 13
2. **Missing doc comments in GIL benchmarks** - Compiler warnings due to `missing_docs = "warn"` lint
3. **Deprecated API in dump_cache_stats.ps1** - Script uses `RustYamlOperations` instead of current `YamlOperations`
4. **Missing profiling workflow documentation** - No guide connecting profiling to benchmarking for optimization

**Primary recommendation:** Execute as four parallel tasks since items are independent.

## Standard Stack

### Core (No new libraries needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| criterion | 0.5 | Benchmark framework | Already in use, configure_criterion() provides shared config |

### Supporting

No additional libraries required. All changes use existing infrastructure:
- `#[path]` attribute for shared benchmark config (established in Phase 13)
- PowerShell for script updates
- Markdown for documentation

### Alternatives Considered

Not applicable - tech debt cleanup uses existing patterns.

## Architecture Patterns

### Pattern 1: Shared Benchmark Configuration via #[path]

**What:** Include shared benchmark config module using `#[path]` attribute
**When to use:** All Criterion benchmarks in the workspace
**Example:**
```rust
// Source: rust/business-logic/classic-yaml-core/benches/yaml_benchmarks.rs
// Import shared benchmark configuration from workspace benches/common/
#[path = "../../../benches/common/mod.rs"]
mod common;

criterion_group! {
    name = benches;
    config = common::config::configure_criterion();
    targets = my_benchmark
}
```

**Current state (GIL benchmarks):**
```rust
// rust/python-bindings/classic-yaml-py/benches/gil_benchmarks.rs
criterion_group!(
    benches,
    bench_yaml_parsing,
    // ... targets
);
criterion_main!(benches);  // Uses Criterion::default()
```

**Correct path for GIL benchmarks:**
```rust
// From: rust/python-bindings/classic-yaml-py/benches/gil_benchmarks.rs
// To:   rust/benches/common/mod.rs
// Path: ../../../../benches/common/mod.rs
#[path = "../../../../benches/common/mod.rs"]
mod common;
```

### Pattern 2: Crate-Level Doc Comments

**What:** Module-level `//!` documentation at top of file
**When to use:** Every Rust file, especially benchmark files with `missing_docs = "warn"`
**Example:**
```rust
//! GIL Release Audit Benchmarks - YAML operations
//!
//! These benchmarks measure pure Rust compute time for YAML-related
//! operations to establish baselines for GIL release decisions.
//!
//! # Running Benchmarks
//!
//! ```bash
//! # Quick mode (development)
//! BENCH_MODE=quick cargo bench --bench gil_benchmarks
//!
//! # Thorough mode (baseline establishment)
//! BENCH_MODE=thorough cargo bench --bench gil_benchmarks
//! ```
```

### Pattern 3: Current API Usage

**What:** Use current module API names, not legacy names
**When to use:** All scripts and documentation referencing Rust Python bindings
**Example:**
```python
# Deprecated:
ops = classic_yaml.RustYamlOperations()

# Current:
ops = classic_yaml.YamlOperations()
```

### Anti-Patterns to Avoid

- **Using Criterion::default():** Always use configure_criterion() for BENCH_MODE consistency
- **Using deprecated API names:** Always use current class names from .pyi stubs

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Benchmark configuration | Custom config per file | configure_criterion() | BENCH_MODE consistency |
| API documentation | Inline comments | Module-level `//!` docs | Rust convention, suppresses warnings |

## Common Pitfalls

### Pitfall 1: Incorrect #[path] Depth

**What goes wrong:** Wrong relative path breaks compilation
**Why it happens:** GIL benchmarks are one level deeper than core benchmarks
**How to avoid:** Count directory levels carefully:
- Core benchmarks: `rust/business-logic/classic-yaml-core/benches/` → `../../../benches/common/`
- GIL benchmarks: `rust/python-bindings/classic-yaml-py/benches/` → `../../../../benches/common/`
**Warning signs:** Compilation error "can't find crate" or "module not found"

### Pitfall 2: Breaking Existing Benchmark Behavior

**What goes wrong:** Adding shared config changes benchmark execution time
**Why it happens:** configure_criterion() changes sample_size and measurement_time
**How to avoid:** This is intentional - GIL benchmarks will now respect BENCH_MODE
**Warning signs:** None - this is the desired outcome

### Pitfall 3: Incomplete API Migration

**What goes wrong:** Updating one reference but missing others in same file
**Why it happens:** Multiple API references in scripts
**How to avoid:** Search entire file for deprecated name before updating
**Warning signs:** Script partially works but fails on some operations

## Code Examples

### GIL Benchmark Config Update

```rust
// Source: Pattern from rust/business-logic/classic-yaml-core/benches/yaml_benchmarks.rs
// Target files:
//   - rust/python-bindings/classic-yaml-py/benches/gil_benchmarks.rs
//   - rust/python-bindings/classic-scanlog-py/benches/gil_benchmarks.rs
//   - rust/python-bindings/classic-file-io-py/benches/gil_benchmarks.rs

//! GIL Release Audit Benchmarks - [YAML/Scanlog/File I/O] operations
//!
//! These benchmarks measure pure Rust compute time for [domain]-related
//! operations to establish baselines for GIL release decisions.
//!
//! # Running Benchmarks
//!
//! ```bash
//! # Quick mode (development)
//! BENCH_MODE=quick cargo bench --bench gil_benchmarks
//!
//! # Thorough mode (baseline establishment)
//! BENCH_MODE=thorough cargo bench --bench gil_benchmarks
//! ```

use criterion::{criterion_group, criterion_main, BenchmarkId, Criterion};
// ... other imports ...

// Import shared benchmark configuration from workspace benches/common/
#[path = "../../../../benches/common/mod.rs"]
mod common;

// ... benchmark functions ...

criterion_group! {
    name = benches;
    config = common::config::configure_criterion();
    targets =
        bench_function_1,
        bench_function_2
}
criterion_main!(benches);
```

### dump_cache_stats.ps1 API Update

```python
# Current (deprecated):
import classic_yaml
ops = classic_yaml.RustYamlOperations()
yaml_stats = ops.get_cache_stats()

# Updated (current API):
import classic_yaml
ops = classic_yaml.YamlOperations()  # Changed: RustYamlOperations → YamlOperations
yaml_stats = ops.get_cache_stats()   # Method name unchanged
```

### Profiling Workflow Documentation Structure

```markdown
# Profiling to Optimization Workflow

## Overview
Developer guide connecting profiling tools to benchmark validation.

## Steps

### 1. Identify Hot Path (Phase 14 tools)
- Run flamegraph: `./scripts/profile/run_flamegraph.ps1 -Mode quick`
- Run py-spy: `./scripts/profile/run_pyspy.ps1 -Mode quick`
- Run dhat: `./scripts/profile/run_dhat.ps1`

### 2. Establish Baseline (Phase 13 tools)
- Run benchmarks: `./scripts/bench/run_benchmarks.ps1 -Mode thorough`
- Save baseline: `./scripts/bench/run_benchmarks.ps1 -SaveBaseline pre-optimization`

### 3. Implement Optimization
- Make targeted changes based on profiling data

### 4. Verify Improvement (Phase 13 tools)
- Run benchmarks: `./scripts/bench/run_benchmarks.ps1 -Mode thorough`
- Compare: `./scripts/bench/compare_baselines.ps1 pre-optimization`
- Verify no regressions in other paths
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| RustYamlOperations | YamlOperations | Phase 5 (v1.0) | API simplification |
| Criterion::default() | configure_criterion() | Phase 13 | Consistent BENCH_MODE |

**Deprecated/outdated:**
- `RustYamlOperations`: Replaced by `YamlOperations` in Phase 5 cleanup
- Hardcoded benchmark configs: Replaced by environment-driven config in Phase 13

## Open Questions

None - all tech debt items are well-defined with clear solutions.

## Sources

### Primary (HIGH confidence)

- `rust/benches/common/config.rs` - configure_criterion() implementation
- `rust/benches/common/mod.rs` - Module structure for #[path] import
- `rust/business-logic/classic-yaml-core/benches/yaml_benchmarks.rs` - Reference implementation
- `rust/python-bindings/classic-yaml-py/classic_yaml.pyi` - Current API (YamlOperations)
- `rust/python-bindings/classic-yaml-py/src/lib.rs:135` - Class named `YamlOperations`

### Verified File Locations

| GIL Benchmark File | Line for criterion_group! |
|-------------------|---------------------------|
| `rust/python-bindings/classic-yaml-py/benches/gil_benchmarks.rs` | Line 227 |
| `rust/python-bindings/classic-scanlog-py/benches/gil_benchmarks.rs` | Line 211 |
| `rust/python-bindings/classic-file-io-py/benches/gil_benchmarks.rs` | Line 208 |

| Script to Update | API Reference Line |
|------------------|-------------------|
| `scripts/profile/dump_cache_stats.ps1` | Line 72 |

## Metadata

**Confidence breakdown:**
- GIL benchmark config: HIGH - Direct code inspection, established pattern
- Doc comments: HIGH - Rust lint configuration verified
- API update: HIGH - Verified in lib.rs and .pyi
- Workflow docs: HIGH - Existing scripts and patterns documented

**Research date:** 2026-02-04
**Valid until:** No expiration - tech debt items are stable

## Implementation Notes

### Task Independence

All four tech debt items are independent:
1. GIL benchmark config changes don't affect dump_cache_stats.ps1
2. Doc comments don't affect benchmark behavior
3. API update in PowerShell script is isolated
4. Documentation is additive, no code changes

**Recommendation:** Execute as four parallel tasks in a single plan.

### Files to Modify

1. `rust/python-bindings/classic-yaml-py/benches/gil_benchmarks.rs`
2. `rust/python-bindings/classic-scanlog-py/benches/gil_benchmarks.rs`
3. `rust/python-bindings/classic-file-io-py/benches/gil_benchmarks.rs`
4. `scripts/profile/dump_cache_stats.ps1`
5. `docs/development/profiling_workflow.md` (new file)

### Verification Approach

1. **GIL benchmarks:** `BENCH_MODE=quick cargo bench --bench gil_benchmarks -p classic-yaml-py -- --test`
2. **Doc comments:** `cargo clippy --all-targets -p classic-yaml-py` (no warnings)
3. **API update:** `.\scripts\profile\dump_cache_stats.ps1` (runs without error)
4. **Workflow docs:** File exists and follows established doc patterns
