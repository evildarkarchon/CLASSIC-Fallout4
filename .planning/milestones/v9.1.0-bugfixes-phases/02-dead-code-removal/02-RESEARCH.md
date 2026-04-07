# Phase 2: Dead Code Removal - Research

**Researched:** 2026-04-05
**Domain:** Rust dead code removal, deprecated API deletion, Python binding simplification
**Confidence:** HIGH

## Summary

Phase 2 removes all dead code items identified in the codebase audit, deletes deprecated methods whose callers were migrated in Phase 1, eliminates the `scan_all_settings_legacy_bucketed` fallback path, and converts `PyGpuDetector` to a stateless class. The work is straightforward deletion with two nuances: (1) the three deprecated shim tests must be migrated to `parse_all_sections_arc` BEFORE the deprecated methods are deleted (because `deprecated = "deny"` is active workspace-wide), and (2) the legacy fallback elimination follows a two-step confidence-then-delete pattern per D-03.

**Primary recommendation:** Execute in strict order -- first migrate tests, then delete dead code items, then handle legacy fallback (test-then-remove), then clean up `PyGpuDetector`. Each step should be validated with `cargo build --workspace` and `cargo test --workspace`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Clean as you go -- also remove `fast_contains` (parser.rs:1208) and the `test_custom_format_config` integration test (integration_tests.rs:490) alongside the required dead code items, since we're already editing those files. No point leaving known dead code behind.
- **D-02:** Migrate the 3 remaining `#[allow(deprecated)]` tests (`test_segment_parsing_deprecated_shim`, `test_segment_parsing_with_patches_first_boundary`, `test_deprecated_parse_segments_preserves_xse_modules_slot`) to use `parse_all_sections`/`parse_all_sections_arc` first, ensuring segment boundary parsing, patch ordering, and XSE module slot preservation behavior are covered under the current API. Then delete the deprecated methods.
- **D-03:** Two-step approach. First add the assertion test (TEST-02) proving production configs never hit `scan_all_settings_legacy_bucketed` while the legacy code is still present. Validate the test passes. Then remove the legacy code in a second step. This gives confidence before deletion.

### Claude's Discretion
- Order of deletion within the phase (which dead code item first)
- Exact test structure for migrated deprecated shim tests
- How `PyGpuDetector` constructor changes when converting to stateless (no `inner` field)
- Whether `SEGMENT_BOUNDARIES` removal also removes the `once_cell::sync::Lazy` import if it becomes unused in that file (note: Phase 7 does a full `Lazy` -> `LazyLock` sweep, but removing an unused import is fine now)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEBT-01 | Remove `SEGMENT_BOUNDARIES` static from parser.rs | Dead code with `#[allow(dead_code)]` at line 70; safe to delete, `Lazy` import stays (used by 2 other statics) |
| DEBT-02 | Remove `YamlFormatConfig` struct and `format_config` field from `YamlOperations` | Struct at line 383, field at line 508; also remove `with_config()` method, update `new()`, clean module docs, benchmarks, and 3 internal tests |
| DEBT-03 | Remove `PluginAnalyzer.case_cache` field | Field at line 67; allocated at line 134 but never read/written; remove field, constructor init, and `Arc<DashMap>` import if unused |
| DEBT-04 | Remove `PyGpuDetector.inner` field and convert to stateless | Core `GpuDetector` is already a unit struct; PyO3 wrapper just needs `inner` field removed, constructor simplified, `.pyi` stub unchanged |
| DEBT-08 | Delete deprecated `parse_segments`, `parse_segments_parallel`, `is_outdated` | After D-02 test migration; also delete `named_sections_to_positional` (only used by deprecated methods) |
| DEBT-09 | Eliminate `scan_all_settings_legacy_bucketed` fallback | Two-step per D-03: assertion test first, then remove fallback branch and method |
| TEST-02 | Assertion test that production configs never hit legacy fallback | Test that all registered crashgen entries have `settings_rules.is_some()` OR test that `scan_all_settings_bucketed` never reaches the fallback branch with production config |
</phase_requirements>

## Standard Stack

No new libraries are needed for this phase. All work is deletion and test migration within existing code.

### Core (already in workspace)
| Library | Version | Purpose | Relevant To |
|---------|---------|---------|-------------|
| `cargo test` | built-in | Rust workspace tests | All requirement verification |
| PyO3 | 0.27.2 | Python bindings | DEBT-04 (PyGpuDetector) |
| `classic-crashgen-settings-core` | workspace | Settings rules types | DEBT-09/TEST-02 |

### Alternatives Considered
None -- this is pure deletion work, no new dependencies.

## Architecture Patterns

### Deletion Ordering Strategy

The workspace has `deprecated = "deny"` in `ClassicLib-rs/Cargo.toml` line 188. This means:
1. Tests that call deprecated methods MUST use `#[allow(deprecated)]` to compile
2. Migrating those tests away from deprecated methods must happen BEFORE deleting the deprecated methods
3. If deprecated methods are deleted first, any remaining `#[allow(deprecated)]` annotations become unnecessary but harmless

**Recommended execution order:**

```
Step 1: Migrate 3 deprecated shim tests to parse_all_sections_arc
Step 2: Delete deprecated methods (parse_segments, parse_segments_parallel, is_outdated)
         + Delete named_sections_to_positional (orphaned helper)
         + Delete SEGMENT_BOUNDARIES, fast_contains
Step 3: Delete YamlFormatConfig, format_config field, with_config method
         + Clean benchmarks, internal tests, module docs
         + Delete test_custom_format_config integration test
Step 4: Delete PluginAnalyzer.case_cache
Step 5: Add TEST-02 assertion test for legacy fallback
Step 6: Remove scan_all_settings_legacy_bucketed + fallback branch
Step 7: Convert PyGpuDetector to stateless
Step 8: Final verification (cargo build, cargo test, parity gates)
```

### Test Migration Pattern (D-02)

The three deprecated tests verify specific behaviors through the positional `Vec<Vec<Arc<str>>>` interface. Each must be translated to the named `HashMap<String, Vec<Arc<str>>>` interface:

| Old Test | Behavior Tested | New Assertion Strategy |
|----------|----------------|----------------------|
| `test_segment_parsing_deprecated_shim` | Basic segmentation produces non-empty results | `parse_all_sections_arc` returns non-empty map with known keys |
| `test_segment_parsing_with_patches_first_boundary` | `[Patches]` content lives in settings segment (not a boundary) | `sections["settings"]` contains `[Patches]` line |
| `test_deprecated_parse_segments_preserves_xse_modules_slot` | XSE modules separated from regular modules | `sections["modules"]` has `module.dll`, `sections["xse_modules"]` has `f4se_plugin.dll`, `sections["plugins"]` has `Fallout4.esm` |

The `segment_key` constants (`SETTINGS`, `MODULES`, `XSE_MODULES`, `PLUGINS`) should be used for key access to stay consistent with the rest of the codebase.

### Legacy Fallback Assertion Test (TEST-02)

The fallback in `settings_validator.rs:192` triggers when `self.entry.settings_rules` is `None`. The assertion test should prove this never happens with production-loaded configs.

**Two viable approaches:**

1. **Registry-level test (recommended):** Load the actual production YAML config files (from `sample_logs/FO4/` submodule or embedded test data), build the `CrashgenRegistry`, and assert that every registered entry has `settings_rules.is_some()`. This directly proves the `if let Some(rules)` branch always takes.

2. **Validator-level test:** Construct a `SettingsValidator` from each production registry entry and call `scan_all_settings_bucketed` with a minimal crashgen map, asserting no panic and no fallback. Less direct but tests the full code path.

Approach 1 is cleaner because it tests the invariant directly. The test belongs in `settings_validator.rs` or `crashgen_registry.rs` test module.

### YamlFormatConfig Removal Cascade

Removing `YamlFormatConfig` impacts these locations:

| File | What Changes |
|------|-------------|
| `classic-yaml-core/src/lib.rs` | Delete `YamlFormatConfig` struct (lines 338-394), `Default` impl (396-420), `format_config` field (508), `with_config()` method (549-554), module-level doc examples (lines 16-31), two internal tests at ~2395 and ~2413 |
| `classic-yaml-core/tests/integration_tests.rs` | Delete `test_custom_format_config` test (489-504), remove `YamlFormatConfig` from import (line 6) |
| `classic-yaml-core/benches/yaml_benchmarks.rs` | Remove `YamlFormatConfig` import (line 27), delete or simplify `yaml_config_benchmarks` function (298-344) that compares default vs custom config (both are functionally identical since `format_config` was never used) |
| `YamlOperations::new()` | Simplify to just `Self { cache_enabled: true }` |

### PyGpuDetector Stateless Conversion

The core `GpuDetector` is already a unit struct (`pub struct GpuDetector;`) with only static methods. The PyO3 wrapper simply removes the `inner` field:

**Before:**
```rust
pub struct PyGpuDetector {
    #[allow(dead_code)]
    inner: GpuDetector,
}
// constructor: Self { inner: GpuDetector::new() }
```

**After:**
```rust
pub struct PyGpuDetector;
// constructor: Self
```

The `Default` impl simplifies to `Self`. The `#[new]` method becomes `Self`. All methods (`extract_gpu_info`, `extract_gpu_info_batch`) already call static `GpuDetector::` methods and don't reference `self.inner`, so they need no changes.

The `.pyi` stub (`classic_scanlog.pyi` line 1740) does NOT need changes -- the Python-visible API (`__init__()`, `extract_gpu_info()`, `extract_gpu_info_batch()`) is unchanged.

### Anti-Patterns to Avoid
- **Deleting methods before migrating their test callers:** The `deprecated = "deny"` lint will cause build failures if deprecated method references remain in non-`#[allow(deprecated)]` code.
- **Removing `#[allow(dead_code)]` without removing the dead code:** Leaving the annotation but keeping the code creates a misleading signal.
- **Deleting the legacy fallback before the assertion test passes:** Per D-03, the test must prove the invariant while the code still exists.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Segment key strings | Bare string literals like `"settings"` | `segment_key::SETTINGS` constants | Compile-time verification, existing codebase pattern |
| Production config loading for TEST-02 | Manual YAML construction | Existing `YamlDataCore` loading + `CrashgenRegistry` construction from orchestrator | Tests the actual production path |

## Common Pitfalls

### Pitfall 1: Orphaned Helper Methods
**What goes wrong:** Deleting `parse_segments` and `parse_segments_parallel` but forgetting `named_sections_to_positional`, which is only called by them.
**Why it happens:** `named_sections_to_positional` is a private method with no `#[allow(dead_code)]` annotation -- it would cause a compiler warning (or error under strict lints) if left behind.
**How to avoid:** Delete `named_sections_to_positional` (parser.rs lines 412-450) in the same step as the deprecated methods.
**Warning signs:** `cargo build` warning about unused private method.

### Pitfall 2: Benchmark File Breakage
**What goes wrong:** Removing `YamlFormatConfig` from `lib.rs` but forgetting the benchmark file imports it.
**Why it happens:** Benchmarks are in a separate `benches/` directory, easy to miss during grep-driven deletion.
**How to avoid:** The `yaml_benchmarks.rs` file (line 27) imports `YamlFormatConfig` and the `yaml_config_benchmarks` function (line 298) uses it. Both need updating.
**Warning signs:** `cargo bench --no-run` fails to compile.

### Pitfall 3: DashMap Import Becomes Unused
**What goes wrong:** Removing `case_cache: Arc<DashMap<String, String>>` from `PluginAnalyzer` may leave unused imports.
**Why it happens:** Need to check whether `DashMap` and/or `Arc` are used elsewhere in `plugin_analyzer.rs`.
**How to avoid:** After removing the field, check if `DashMap` is still imported/used in the same file. If not, remove the import.
**Warning signs:** `cargo clippy` or `cargo build` warning about unused import.

### Pitfall 4: Test Fixtures with settings_rules: None
**What goes wrong:** Several existing test helpers in `settings_validator.rs` and `orchestrator.rs` construct `CrashgenEntry` with `settings_rules: None`. After removing the legacy fallback, tests that use these fixtures will hit the removed code path.
**Why it happens:** Test fixtures were written when the legacy path existed.
**How to avoid:** After removing the fallback, ensure all test `CrashgenEntry` fixtures either have `settings_rules: Some(...)` or that the code gracefully handles `None` (e.g., returning empty fragments instead of calling a deleted method).
**Warning signs:** `cargo test` panics or compile errors in `settings_validator::tests`.

### Pitfall 5: Module-Level Doc Examples
**What goes wrong:** The `classic-yaml-core/src/lib.rs` module doc (lines 16-31) contains a `YamlFormatConfig` usage example. If not updated, `cargo doc --workspace` or `cargo test --doc` will fail.
**Why it happens:** Doc examples are compiled and run as tests.
**How to avoid:** Update module-level docs to remove `YamlFormatConfig` and `with_config` references.
**Warning signs:** `cargo test --doc` fails on `classic-yaml-core`.

## Code Examples

### Migrating Deprecated Test: XSE Module Slot Preservation

The deprecated test at parser.rs:1642 uses positional indexing. The migrated version uses named keys:

```rust
// Source: parser.rs segment_key constants + parse_all_sections_arc API
use crate::segment_key;

#[test]
fn test_parse_all_sections_preserves_xse_modules_slot() {
    let parser = LogParser::new(None).unwrap();
    let log_lines = make_log_with_known_header();
    let sections = parser.parse_all_sections_arc(&log_lines);

    // Named sections replace positional indexing
    assert!(sections[segment_key::MODULES].iter().any(|line| line.contains("module.dll")));
    assert!(sections[segment_key::XSE_MODULES].iter().any(|line| line.contains("f4se_plugin.dll")));
    assert!(sections[segment_key::PLUGINS].iter().any(|line| line.contains("Fallout4.esm")));
}
```

### PyGpuDetector Stateless Conversion

```rust
// Source: classic-scanlog-py/src/gpu_detector.rs
#[pyclass(name = "GpuDetector")]
pub struct PyGpuDetector;

impl Default for PyGpuDetector {
    fn default() -> Self {
        Self
    }
}

#[pymethods]
impl PyGpuDetector {
    #[new]
    pub fn new() -> Self {
        Self
    }
    // extract_gpu_info and extract_gpu_info_batch unchanged
}
```

### Simplified YamlOperations After Removal

```rust
// Source: classic-yaml-core/src/lib.rs after removal
pub struct YamlOperations {
    cache_enabled: bool,
}

impl YamlOperations {
    pub fn new() -> Self {
        Self { cache_enabled: true }
    }
    // with_config() REMOVED
    // All other methods unchanged
}
```

### TEST-02: Production Config Legacy Fallback Assertion

```rust
// Source: settings_validator.rs or crashgen_registry.rs test module
#[test]
fn test_production_configs_never_hit_legacy_fallback() {
    // Load production YAML configs and build registry
    // For each registered entry:
    //   assert!(entry.settings_rules.is_some(),
    //     "Crashgen '{}' has no settings_rules -- would hit legacy fallback", name);
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `parse_segments` (positional Vec) | `parse_all_sections_arc` (named HashMap) | Phase 1 | All callers migrated; deprecated shim is now dead code |
| `is_outdated` (bool comparison) | `check_version_status` (list-based) | Phase 1 | All callers migrated; deprecated method is dead code |
| `scan_all_settings_legacy_bucketed` (hardcoded logic) | YAML-defined `settings_rules` evaluation | Pre-Phase 1 | Legacy path exists as fallback but is never hit in production |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Rust built-in `cargo test` |
| Config file | `ClassicLib-rs/Cargo.toml` (workspace test config) |
| Quick run command | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` |
| Full suite command | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml && cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEBT-01 | `SEGMENT_BOUNDARIES` removed, no `#[allow(dead_code)]` | build | `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml` | N/A (compile check) |
| DEBT-02 | `YamlFormatConfig` removed, no `#[allow(dead_code)]` on format_config | build + test | `cargo test -p classic-yaml-core --manifest-path ClassicLib-rs/Cargo.toml` | Existing tests remain |
| DEBT-03 | `case_cache` removed, no `#[allow(dead_code)]` | build | `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml` | N/A (compile check) |
| DEBT-04 | `PyGpuDetector` stateless, no `inner` field | build | `./rebuild_rust.ps1 -Target python -Crates classic-scanlog-py` | Existing Python tests |
| DEBT-08 | Deprecated methods deleted, no `#[allow(deprecated)]` in workspace | build + test | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml` | Migrated tests (Wave 0) |
| DEBT-09 | Legacy fallback removed | unit | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml` | Existing + new TEST-02 |
| TEST-02 | Production configs never hit legacy fallback | unit | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml -- test_production_configs` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml && cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml`
- **Per wave merge:** Full suite + parity gates (`python tools/python_api_parity/check_parity_gate.py --repo-root .` and `cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local`)
- **Phase gate:** Full suite green + clippy clean + both parity gates before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] 3 migrated tests replacing `test_segment_parsing_deprecated_shim`, `test_segment_parsing_with_patches_first_boundary`, `test_deprecated_parse_segments_preserves_xse_modules_slot` -- covers DEBT-08 precondition
- [ ] `test_production_configs_never_hit_legacy_fallback` -- covers TEST-02

## Project Constraints (from CLAUDE.md)

- **Build commands:** Use `cargo build/test/fmt/clippy --workspace --manifest-path ClassicLib-rs/Cargo.toml` for Rust workspace
- **Python bindings rebuild:** `./rebuild_rust.ps1 -Target python [-Crates <names>]`
- **Python parity gate:** `python tools/python_api_parity/check_parity_gate.py --repo-root .`
- **Node parity gate:** `bun run parity:gate:local` (from `ClassicLib-rs/node-bindings/classic-node/`)
- **Commit prefix:** `Feat:`, `Fix:`, `Docs:`, `Refactor:`, `Chore:`, `Update:`
- **No output to nul:** Never write to `nul` on Windows
- **Formatting:** `cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml` before commit
- **deprecated = "deny":** Workspace lint at `ClassicLib-rs/Cargo.toml:188` -- deprecated API usage is a compile error
- **API docs:** Consult `docs/api/README.md` before changing public APIs; update affected pages in same change
- **Python venv:** `ClassicLib-rs/python-bindings/.venv`, not repo root

## Sources

### Primary (HIGH confidence)
- Direct source code inspection of all files referenced in CONTEXT.md canonical_refs
- `ClassicLib-rs/Cargo.toml` line 188: `deprecated = "deny"` workspace lint verified
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/parser.rs`: All dead code items and deprecated methods verified at stated line numbers
- `ClassicLib-rs/business-logic/classic-yaml-core/src/lib.rs`: `YamlFormatConfig` full usage graph traced
- `ClassicLib-rs/python-bindings/classic-scanlog-py/src/gpu_detector.rs`: `PyGpuDetector` structure and method delegation verified
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/settings_validator.rs`: Legacy fallback trigger condition verified (`settings_rules.is_none()`)

### Secondary (MEDIUM confidence)
- None needed -- all findings from direct source inspection

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependencies, pure deletion work
- Architecture: HIGH - all code paths traced, deletion cascade fully mapped
- Pitfalls: HIGH - identified from direct code inspection, all impact points verified

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (stable -- deletion targets are static)
