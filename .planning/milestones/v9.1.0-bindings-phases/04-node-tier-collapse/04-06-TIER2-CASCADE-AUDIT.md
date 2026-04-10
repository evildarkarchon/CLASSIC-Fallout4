# Plan 06 -- Tier-2 Cascade Audit (M7 recursive search)

**Generated:** 2026-04-10T01:36Z (Task 1)
**Plan:** 04-node-tier-collapse / 06-tier2-cleanup-cascade
**Purpose:** Enumerate every reader/writer of `tier2_gap_total` / `rust_unmapped` / `node_unmapped` / `tierDefinitions.*tier2` / `Tier 2 Gaps` / `GLOBAL_FCX_HANDLER` across the Node parity scope BEFORE Task 2 deletes them, so no consumer is silently broken (Phase 3 Plan 09b M7 precedent).

## Search command

```
rg --line-number --no-heading \
  "tier2_gap_total|rust_unmapped|node_unmapped|tierDefinitions\.?tier2|tierDefinitions\[.tier2.\]|Tier 2 Gaps|GLOBAL_FCX_HANDLER" \
  --glob "!**/node_modules/**" --glob "!**/target/**" --glob "!**/.git/**" --glob "!**/dist/**" --glob "!**/*.lock" \
  tools/node_api_parity/ docs/implementation/node_api_parity/ ClassicLib-rs/node-bindings/classic-node/ .github/workflows/ *.ps1
```

## Total hits: **361** across **16 files** (0 in .github/workflows/, 0 in *.ps1)

| File | Hits |
|---|---:|
| `tools/node_api_parity/generate_baseline.py` | 6 |
| `tools/node_api_parity/check_parity_gate.py` | 1 |
| `tools/node_api_parity/tests/test_check_parity_gate.py` | 5 |
| `docs/implementation/node_api_parity/baseline/parity_diff_report.json` | 3 |
| `docs/implementation/node_api_parity/baseline/parity_diff_report.md` | 1 |
| `docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json` | 3 |
| `docs/implementation/node_api_parity/baseline/rust_api_surface.json` | 6 |
| `docs/implementation/node_api_parity/baseline/handoff_map.md` | 1 |
| `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json` | 1 |
| `docs/implementation/node_api_parity/governance/tier2_wave_manifest.json` | 316 |
| `docs/implementation/node_api_parity/governance/per_wave_acceptance_template.md` | 2 |
| `ClassicLib-rs/node-bindings/classic-node/src/scanlog.rs` | 3 |
| `ClassicLib-rs/node-bindings/classic-node/parity-artifacts/parity_diff_report.json` | 3 |
| `ClassicLib-rs/node-bindings/classic-node/parity-artifacts/parity_diff_report.md` | 1 |
| `ClassicLib-rs/node-bindings/classic-node/parity-artifacts/runtime_coverage_summary.json` | 3 |
| `ClassicLib-rs/node-bindings/classic-node/parity-artifacts/rust_api_surface.json` | 6 |

## Hits by file (classified with remediation status)

### `tools/node_api_parity/generate_baseline.py` -- 6 hits

- **L406**: `rust_unmapped bucketing` -- **HISTORICAL_COMMENT** in docstring.
  - Remediation: Harmless prose in a comment; does not drive code behavior. Stays.
- **L444**: `tier1-mapped for the rust_unmapped gap calculation below` -- **HISTORICAL_COMMENT** in code comment.
  - Remediation: Comment references a loop that Task 2 deletes. Comment will be orphaned but harmless. Stays (Phase 6 DOC cleanup scope).
- **L526**: `"gap_type": "rust_unmapped",` -- **CODE_WRITE (emission branch)**.
  - Remediation: **MUST DELETE in Task 2.** The entire `for rust_item in rust_symbols:` loop emitting rust_unmapped gaps.
- **L545**: `"gap_type": "node_unmapped",` -- **CODE_WRITE (emission branch)**.
  - Remediation: **MUST DELETE in Task 2.** The entire `for node_item in node_exports:` loop emitting node_unmapped gaps.
- **L574**: `"tier2_gap_total": sum(1 for gap in gaps if gap["tier"] == "tier2"),` -- **CODE_WRITE (summary dict key)**.
  - Remediation: **MUST DELETE in Task 2.** Remove this line from the summary dict.
- **L621**: `"| Owner Module | Tier 1 Gaps | Tier 2 Gaps |"` -- **CODE_WRITE (markdown table header)**.
  - Remediation: **MUST DELETE in Task 2.** Remove the `| Tier 2 Gaps |` column from header AND the corresponding cell expression. MEDIUM concern: both must be edited atomically.

### `tools/node_api_parity/check_parity_gate.py` -- 1 hit

- **L322**: `rust_unmapped gap calculation` -- **HISTORICAL_COMMENT** in a code comment.
  - Remediation: Harmless comment reference. Stays.

### `tools/node_api_parity/tests/test_check_parity_gate.py` -- 5 hits

- **L12**: `tierDefinitions.tier2` in module docstring -- **DOCS_PROSE**.
  - Remediation: Describes purpose of the xfail test. Stays as documentation.
- **L15**: `tierDefinitions.tier2` in module docstring -- **DOCS_PROSE**.
  - Remediation: Same. Stays.
- **L61**: `Plan 6 atomic cascade deletes tierDefinitions.tier2` -- **TEST_ASSERTION** (xfail reason string).
  - Remediation: **MUST EDIT in Task 2.** Remove `@pytest.mark.xfail(strict=True, ...)` decorator.
- **L67**: `tierDefinitions.tier2` in test docstring -- **DOCS_PROSE**.
  - Remediation: Stays as documentation of the test's purpose.
- **L75**: `tierDefinitions.tier2 still present` -- **TEST_ASSERTION** (assert message).
  - Remediation: **MUST EDIT in Task 2.** Update assert message to reflect post-cascade state.

### `docs/implementation/node_api_parity/baseline/parity_diff_report.json` -- 3 hits

- `rust_unmapped` gap entries (3 occurrences in gap list) -- **BASELINE_JSON**.
  - Remediation: Refreshed by `bun run parity:gate:local` pipeline in Task 2. No manual edit needed.

### `docs/implementation/node_api_parity/baseline/parity_diff_report.md` -- 1 hit

- **L729**: `| Owner Module | Tier 1 Gaps | Tier 2 Gaps |` -- **BASELINE_JSON** (generated markdown).
  - Remediation: Refreshed by pipeline regeneration. No manual edit needed.

### `docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json` -- 3 hits

- `deferred` count entries including GLOBAL_FCX_HANDLER -- **BASELINE_JSON**.
  - Remediation: Refreshed by pipeline. After emptying backlog, `deferred_total` becomes 0.

### `docs/implementation/node_api_parity/baseline/rust_api_surface.json` -- 6 hits

- Various `"tier": "tier2"` annotations on Rust symbols -- **BASELINE_JSON**.
  - Remediation: These are tier classification labels produced by `parse_rust_surface()`. The tier field is a LOAD_BEARING_EXCLUDED label used by the parser internally; it persists in the surface JSON but no longer drives gap emission once the `rust_unmapped` loop is deleted. Refreshed by pipeline.

### `docs/implementation/node_api_parity/baseline/handoff_map.md` -- 1 hit

- **L16**: `| rust_unmapped | tier2 | GLOBAL_FCX_HANDLER | - |` -- **BASELINE_JSON** (generated).
  - Remediation: Refreshed by pipeline regeneration.

### `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json` -- 1 hit

- **L15**: `"GLOBAL_FCX_HANDLER"` -- **CODE_READ** (last backlog entry, the A2 target).
  - Remediation: **MUST EDIT in Task 2.** Empty `entries` to `[]` (clears GLOBAL_FCX_HANDLER per A2). Preserve file shape for Phase 6 DOC-03.

### `docs/implementation/node_api_parity/governance/tier2_wave_manifest.json` -- 316 hits

- `rust_unmapped` and `node_unmapped` gap_type labels across manifest entries -- **OUT_OF_SCOPE_PHASE_6**.
  - Remediation: Phase 6 DOC-03 deletes this governance file entirely. No Task 2 action.

### `docs/implementation/node_api_parity/governance/per_wave_acceptance_template.md` -- 2 hits

- `rust_unmapped` and `node_unmapped` in template prose -- **OUT_OF_SCOPE_PHASE_6**.
  - Remediation: Phase 6 deletes governance files. No Task 2 action.

### `ClassicLib-rs/node-bindings/classic-node/src/scanlog.rs` -- 3 hits

- **L23**: `use classic_scanlog_core::{..., GLOBAL_FCX_HANDLER};` -- **LOAD_BEARING_EXCLUDED** (Rust source using the singleton).
  - Remediation: This is live production Rust code importing the singleton. NOT a cascade target. The singleton itself is not being deleted; only its parity backlog entry is being cleared. No edit needed.
- **L129**: `GLOBAL_FCX_HANDLER.lock()` -- **LOAD_BEARING_EXCLUDED** (runtime usage).
  - Remediation: No edit needed. Live production code.
- **L302**: `GLOBAL_FCX_HANDLER.lock()` -- **LOAD_BEARING_EXCLUDED** (runtime usage).
  - Remediation: No edit needed. Live production code.

### `ClassicLib-rs/node-bindings/classic-node/parity-artifacts/parity_diff_report.json` -- 3 hits

- `rust_unmapped` gap entries -- **BASELINE_JSON** (parity-artifacts mirror).
  - Remediation: Refreshed by `bun run parity:gate:local` pipeline. No manual edit.

### `ClassicLib-rs/node-bindings/classic-node/parity-artifacts/parity_diff_report.md` -- 1 hit

- `Tier 2 Gaps` column in generated markdown -- **BASELINE_JSON** (parity-artifacts mirror).
  - Remediation: Refreshed by pipeline regeneration.

### `ClassicLib-rs/node-bindings/classic-node/parity-artifacts/runtime_coverage_summary.json` -- 3 hits

- Deferred count entries -- **BASELINE_JSON** (parity-artifacts mirror).
  - Remediation: Refreshed by pipeline.

### `ClassicLib-rs/node-bindings/classic-node/parity-artifacts/rust_api_surface.json` -- 6 hits

- `"tier": "tier2"` annotations -- **BASELINE_JSON** (parity-artifacts mirror).
  - Remediation: Refreshed by pipeline. Same LOAD_BEARING_EXCLUDED label as the docs/baseline version.

## Task 2 Action Plan

The following files MUST be edited manually in Task 2 (Phase 2a), all within ONE atomic commit:

1. **`tools/node_api_parity/generate_baseline.py`** (4 edits):
   - Delete `for rust_item in rust_symbols:` loop emitting `gap_type=rust_unmapped` (around L520-535)
   - Delete `for node_item in node_exports:` loop emitting `gap_type=node_unmapped` (around L536-555)
   - Delete `"tier2_gap_total": ...` from summary dict (L574)
   - Delete `| Tier 2 Gaps |` column from header AND cell expression (L621 + cell below)

2. **`docs/implementation/node_api_parity/baseline/parity_contract.json`**:
   - Delete `tierDefinitions.tier2` (keep `tier1`)

3. **`docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json`**:
   - Set `entries` to `[]` (clears GLOBAL_FCX_HANDLER per A2)

4. **`tools/node_api_parity/tests/test_check_parity_gate.py`** (2 edits):
   - Remove `@pytest.mark.xfail(strict=True, ...)` decorator from `test_tier2_definition_removed_after_plan_6`
   - Replace `test_tier1_contract_total_baseline_floor` assertion with fail-loud placeholder (Phase 2c.1 resolves)

The following files are refreshed automatically by `bun run parity:gate:local` (Phase 2b):
- All `docs/implementation/node_api_parity/baseline/*.json` and `*.md`
- All `ClassicLib-rs/node-bindings/classic-node/parity-artifacts/*`

The following files are **NOT touched** by Task 2:
- `ClassicLib-rs/node-bindings/classic-node/src/scanlog.rs` (LOAD_BEARING_EXCLUDED -- live production code)
- `docs/implementation/node_api_parity/governance/tier2_wave_manifest.json` (OUT_OF_SCOPE_PHASE_6)
- `docs/implementation/node_api_parity/governance/per_wave_acceptance_template.md` (OUT_OF_SCOPE_PHASE_6)
