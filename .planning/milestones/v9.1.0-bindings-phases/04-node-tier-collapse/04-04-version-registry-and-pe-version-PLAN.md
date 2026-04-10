---
phase: 04-node-tier-collapse
plan: 04
plan_id: 04-04
title: Version Registry Promotion + HARM-01/02 PE-Version (4 rows + 3 new = 7 total)
type: execute
wave: 3
depends_on: [04-03]
files_modified:
  - ClassicLib-rs/business-logic/classic-version-core/src/lib.rs
  - ClassicLib-rs/node-bindings/classic-node/src/version.rs
  - ClassicLib-rs/node-bindings/classic-node/index.d.ts
  - ClassicLib-rs/node-bindings/classic-node/__test__/version.spec.ts
  - ClassicLib-rs/node-bindings/classic-node/__test__/version_registry.spec.ts
  - ClassicLib-rs/node-bindings/classic-node/__test__/runtime.node.test.mjs
  - ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json
  - docs/implementation/node_api_parity/baseline/parity_contract.json
  - docs/implementation/node_api_parity/baseline/parity_contract.md
  - docs/implementation/node_api_parity/baseline/parity_diff_report.json
  - docs/implementation/node_api_parity/baseline/parity_diff_report.md
  - docs/implementation/node_api_parity/baseline/rust_api_surface.json
  - docs/implementation/node_api_parity/baseline/node_api_surface.json
  - docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json
  - docs/implementation/node_api_parity/baseline/runtime_coverage_summary.md
  - docs/implementation/node_api_parity/baseline/tier1_gate_report.md
autonomous: false
requirements_addressed: [NODE-02, NODE-04, NODE-05, HARM-01, HARM-02]
requirements: [NODE-02, NODE-04, NODE-05, HARM-01, HARM-02]
must_haves:
  truths:
    - "Task 1 FIRST adds `pub use pe_version::is_valid_executable_path;` to the existing re-export line (43) of `ClassicLib-rs/business-logic/classic-version-core/src/lib.rs` BEFORE any NAPI wrapper is added. Without this, the bidirectional guard fails when HARM-01 contract rows land (A6 load-bearing prerequisite). Task 1 ALSO runs the Python parity gate as a cross-binding regression probe per U1 — adding `is_valid_executable_path` to the Rust public surface affects BOTH Node AND Python parity gates."
    - "Task 2 adds `#[napi]` wrappers `extract_pe_version` and `is_valid_pe_path` in `ClassicLib-rs/node-bindings/classic-node/src/version.rs` PLUS a `JsPeVersion` `#[napi(object)]` struct returning `{ major: u32, minor: u32, patch: u32, build: u32 }` (widened from u16 per D-PE-01). Both functions delegate directly to `classic_version_core::pe_version::*` — no business logic in the binding."
    - "Task 2 regenerates `index.d.ts` via `bun run build` atomically in the same commit as the Rust source edit (D-DTS-01). Post-build, `index.d.ts` contains `export declare function extractPeVersion(path: string): JsPeVersion`, `export declare function isValidPePath(path: string): boolean`, and `export interface JsPeVersion { major: number; minor: number; patch: number; build: number }`."
    - "3 new HARM-01/02 contract rows added (D1 adjudication 2026-04-09 reverted the iteration-1 Issue 9 edit: `version-pe-shape` MUST be restored because `parse_node_surface()` emits a standalone `{ export: 'JsPeVersion', kind: 'interface' }` entry for every `export interface` independent of any function that returns it — without the row, JsPeVersion becomes a new deferred backlog entry and regresses deferred_total). The 3 PE rows are: version-pe-extract (extract_pe_version → extractPeVersion), version-pe-is-valid-path (is_valid_executable_path → isValidPePath), version-pe-shape (PeVersionResult → JsPeVersion, nodeKind: interface). All carry rustCrate: 'classic-version-core'. Total Plan 4 rows = 4 version_registry + 3 PE-version = **7** (2 PE function rows + 1 PE shape row + 4 version_registry rows)."
    - "4 existing Node exports for version_registry get normal contract rows: JsCrashgenRegistryEntry (interface), JsCrashgenSettingsRules (interface), checkCrashgenConfigWithRules (function), checkCrashgenFullWithRules (function). All carry rustCrate: 'classic-version-registry-core'. No @rust proxy rows — all four already exist in index.d.ts."
    - "PE-version smoke tests append to `__test__/version.spec.ts` as new `describe('extractPeVersion', ...)` and `describe('isValidPePath', ...)` blocks. Windows-only real-file test against `C:\\Windows\\System32\\kernel32.dll` is guarded by `process.platform === 'win32'`."
    - "Cross-runtime test appended to `__test__/runtime.node.test.mjs` — one extractPeVersion call (Windows-guarded) AND one checkCrashgenConfigWithRules call covering both version_registry and PE-version domains."
    - "runtime_coverage_registry.json has a new dedicated selector for the 7 new rows (3 PE + 4 version_registry) with contractIdsHash computed via _stable_id_hash (D-HASH-01)."
    - "bun run parity:gate:local, bun run test:bun, bun run test:node all exit 0. `bun run dts:freshness:check` exits 0 (index.d.ts regenerated + committed atomically)."
    - "U1 cross-binding regression probe: after A6 `pub use` commit lands, BOTH `bun run parity:gate:local` AND `python tools/python_api_parity/check_parity_gate.py --repo-root .` MUST exit zero. If Python gate fires a new `gap_type=rust_unmapped` row for `is_valid_executable_path`, Plan 4 MUST include a companion Python binding addition in the same atomic commit OR narrow the `pub use` to a feature gate."
    - "per_owner.version_registry.deferred drops to 0 post-commit."
    - "version-pe-shape row exists in parity_contract.json with rustCrate: classic-version-core, rustSymbol: PeVersionResult, nodeExport: JsPeVersion, nodeKind: interface (D1 adjudication precedent: `Fallout4VersionInfo` row already uses this shape for a type-aliased interface target)."
  artifacts:
    - path: "ClassicLib-rs/business-logic/classic-version-core/src/lib.rs"
      provides: "Line 43 re-export extended with `is_valid_executable_path` (A6 load-bearing)"
      contains: "is_valid_executable_path"
    - path: "ClassicLib-rs/node-bindings/classic-node/src/version.rs"
      provides: "JsPeVersion struct + extract_pe_version + is_valid_pe_path NAPI wrappers delegating to classic_version_core::pe_version::*"
      contains: "JsPeVersion"
      min_lines: 50
    - path: "ClassicLib-rs/node-bindings/classic-node/index.d.ts"
      provides: "Regenerated with extractPeVersion, isValidPePath, JsPeVersion exports"
      contains: "extractPeVersion"
    - path: "ClassicLib-rs/node-bindings/classic-node/__test__/version.spec.ts"
      provides: "New describe blocks for extractPeVersion + isValidPePath (with Windows kernel32.dll integration test guarded by process.platform)"
      min_lines: 40
    - path: "docs/implementation/node_api_parity/baseline/parity_contract.json"
      provides: "tier1Mappings grows by 7 rows (3 PE-version + 4 version_registry); version-pe-shape row restored per D1 adjudication 2026-04-09; all new rows carry rustCrate"
      contains: "extractPeVersion"
  key_links:
    - from: "classic-node/src/version.rs::extract_pe_version"
      to: "classic_version_core::pe_version::extract_pe_version"
      via: "direct delegation with to_napi_err error conversion"
      pattern: "classic_version_core::pe_version::extract_pe_version"
    - from: "classic-version-core/src/lib.rs line 43"
      to: "pe_version::is_valid_executable_path"
      via: "pub use re-export (A6 prerequisite — MUST land BEFORE NAPI wrapper commit)"
      pattern: "pub use pe_version::\\{?[^}]*is_valid_executable_path"
    - from: "parity_contract.json version-pe-* rows"
      to: "index.d.ts extractPeVersion/isValidPePath/JsPeVersion exports"
      via: "bidirectional guard validates both sides"
      pattern: "version-pe-(extract|is-valid-path|shape)"
    - from: "parity_contract.json version-pe-shape row"
      to: "node_api_surface.json JsPeVersion interface entry"
      via: "parse_node_surface() emits standalone interface entries; tier1Mappings row prevents JsPeVersion from becoming a deferred backlog entry (D1 adjudication)"
      pattern: "\"nodeExport\":\\s*\"JsPeVersion\""
---

<objective>
Plan 4 accomplishes TWO coupled promotions:

1. **Version Registry** — Promote 4 deferred entries (JsCrashgenRegistryEntry, JsCrashgenSettingsRules, checkCrashgenConfigWithRules, checkCrashgenFullWithRules). All 4 are already exposed in `index.d.ts` via existing NAPI wrappers; Plan 4 only authors contract rows + smoke tests. No Rust source changes for the version_registry portion.

2. **HARM-01/02 PE-Version** — Add `extractPeVersion`, `isValidPePath`, and `JsPeVersion` NAPI exports to `src/version.rs`. Requires a load-bearing `pub use` pre-flight commit to `classic-version-core/src/lib.rs` line 43 BEFORE the NAPI wrapper lands (A6).

Per A6: The `pub use` re-export is a CRITICAL prerequisite. The current `classic-version-core/src/lib.rs` line 43 reads `pub use pe_version::{PeVersionError, PeVersionResult, extract_pe_version};` — it does NOT re-export `is_valid_executable_path`. Without the re-export, Plan 1's bidirectional `validate_contract_surface()` guard fails when the `version-pe-is-valid-path` contract row lands because the parser walks `lib.rs` re-exports, not sub-module public items.

Per U1 (cross-binding regression probe): Adding `is_valid_executable_path` to `classic-version-core`'s public Rust surface affects ALL binding parity gates, not just Node. Python's Phase 3 parity gate also reads this crate's surface. Task 1 MUST verify `python tools/python_api_parity/check_parity_gate.py --repo-root .` still exits zero after the `pub use` lands. If Python gate fires a new `gap_type=rust_unmapped` row, Plan 4 must include a companion Python binding addition in the same atomic commit OR narrow the `pub use` to a feature gate.

Per D1 adjudication (2026-04-09): Plan 4 authors **7 rows total**, NOT 6. The iteration-1 plan-checker's Issue 9 drop of `version-pe-shape` was mechanically wrong. Empirical probe against the live `parse_node_surface()` regex (`tools/node_api_parity/generate_baseline.py` line 301) proves that every `export interface` in `index.d.ts` gets its own standalone `{ export, kind: "interface" }` entry in `node_api_surface.json`, independent of any function that returns it. Without a `version-pe-shape` contract row, `JsPeVersion` becomes a new deferred backlog entry and REGRESSES `deferred_total` (empirically precedented by `node-deferred-aux-108` which tracks 5 already-existing `export interface` entries as deferred). The restored row uses the `Fallout4VersionInfo` precedent shape: `{ id: "version-pe-shape", rustSymbol: "PeVersionResult", nodeExport: "JsPeVersion", nodeKind: "interface", rustCrate: "classic-version-core" }`. `PeVersionResult` IS on the Rust surface at `classic-version-core/src/lib.rs:43` — the bidirectional guard's `parse_rust_surface()` regex matches `pub use` re-exports so the row passes the Rust-side check.

Task 1 lands the pub use re-export in its own commit (keeps the Rust source change atomic with the NAPI addition inside Task 2's commit, OR in a separate pre-flight commit if the user prefers bisect-granular). Task 2 adds the NAPI wrappers + regenerates index.d.ts + authors all 7 new contract rows + appends smoke tests + updates runtime coverage registry.

Purpose:
- Close HARM-01 + HARM-02 requirements (PE-version parity with Python/Rust/C++ bindings)
- Drop version_registry.deferred count to 0
- Demonstrate the first plan in Phase 4 that regenerates index.d.ts (D-DTS-01 atomic-with-Rust-source pattern)

Output:
- `classic-version-core/src/lib.rs` re-export extended (A6)
- Python parity gate verified green post-A6 (U1 cross-binding regression probe)
- `classic-node/src/version.rs` appended with ~50 lines (JsPeVersion + 2 #[napi] fns)
- `index.d.ts` regenerated with 3 new exports (extractPeVersion, isValidPePath, JsPeVersion)
- 7 new tier1Mappings rows (3 PE + 4 version_registry; D1 adjudication restored version-pe-shape)
- New describe blocks in `version.spec.ts` (+ Windows-only integration test)
- New cross-runtime tests in `runtime.node.test.mjs`
- Updated runtime coverage registry with _stable_id_hash
- Gate green with version_registry.deferred == 0
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/04-node-tier-collapse/04-CONTEXT.md
@.planning/phases/04-node-tier-collapse/04-RESEARCH.md
@.planning/phases/04-node-tier-collapse/04-VALIDATION.md
@.planning/phases/04-node-tier-collapse/04-REVIEWS.md
@.planning/phases/04-node-tier-collapse/04-02-scanlog-promotion-SUMMARY.md
@.planning/phases/04-node-tier-collapse/04-03-config-promotion-SUMMARY.md
@./CLAUDE.md
@./AGENTS.md

<interfaces>
<!-- A6 Current state of lib.rs (verified 2026-04-09 by planner) -->
**Current `classic-version-core/src/lib.rs` line 42-43:**
```rust
// Re-export PE version types for convenience
pub use pe_version::{PeVersionError, PeVersionResult, extract_pe_version};
```

**Target state after Task 1:**
```rust
// Re-export PE version types for convenience
pub use pe_version::{PeVersionError, PeVersionResult, extract_pe_version, is_valid_executable_path};
```

**Rust source of truth for PE-version** (`classic-version-core/src/pe_version.rs`):
- `pub fn extract_pe_version(path: &Path) -> PeVersionResult` → returns `Result<(u16, u16, u16, u16), PeVersionError>` (i.e. `PeVersionResult = Result<(u16, u16, u16, u16), PeVersionError>`)
- `pub fn is_valid_executable_path(path: &Path) -> bool` → synchronous, never throws
- `PeVersionError` enum with variants for invalid path, IO error, parse error, missing version info
- `pub type PeVersionResult = Result<(u16, u16, u16, u16), PeVersionError>;` — `parse_rust_surface()` regex matches `pub type` declarations AND `pub use` re-exports, so `PeVersionResult` appears in `rust_api_surface.json` via the line 43 re-export (D1 adjudication finding 6).

**D1 adjudication precedent — `Fallout4VersionInfo` row (verified 2026-04-09 at `parity_contract.json::tier1Mappings`)**:
```json
{
  "id": "version-registry-promote-fallout4-version-info",
  "rustSymbol": "VersionInfo",
  "nodeExport": "Fallout4VersionInfo",
  "nodeKind": "interface"
}
```
This is the canonical precedent for wrapping an `export interface` target with a Rust struct / type-alias source. The `version-pe-shape` row MUST mirror this shape exactly.

**Node binding target** (append to `classic-node/src/version.rs` after existing `format_version` function at line ~99):

```rust
use std::path::Path;

/// PE file version components (4-part file version from VS_VERSIONINFO).
#[napi(object)]
pub struct JsPeVersion {
    pub major: u32,
    pub minor: u32,
    pub patch: u32,
    pub build: u32,
}

/// Extract a PE file's version from its VS_VERSIONINFO resource.
#[napi]
pub fn extract_pe_version(path: String) -> Result<JsPeVersion> {
    let (major, minor, patch, build) =
        classic_version_core::pe_version::extract_pe_version(Path::new(&path))
            .map_err(to_napi_err)?;
    Ok(JsPeVersion {
        major: u32::from(major),
        minor: u32::from(minor),
        patch: u32::from(patch),
        build: u32::from(build),
    })
}

/// Check whether a path points to a valid executable or DLL file.
#[napi]
pub fn is_valid_pe_path(path: String) -> bool {
    classic_version_core::pe_version::is_valid_executable_path(Path::new(&path))
}
```

**NAPI auto-conversion** (verified pattern from existing version.rs):
- Rust `extract_pe_version` → TS `extractPeVersion`
- Rust `is_valid_pe_path` → TS `isValidPePath`
- Rust `JsPeVersion { major: u32, ... }` → TS `interface JsPeVersion { major: number; ... }`

**Version Registry 4 deferred entries** (verified in index.d.ts):
| bindingIdentifier | nodeKind |
|-------------------|----------|
| `JsCrashgenRegistryEntry` | interface |
| `JsCrashgenSettingsRules` | interface |
| `checkCrashgenConfigWithRules` | function |
| `checkCrashgenFullWithRules` | function |

Note on `migrateGameVersionSetting` (Round 2 Fix 4.4 handoff rationale — codebase-verified 2026-04-09): Research noted a diff-report discrepancy (5 node_unmapped vs 4 in coverage summary) — the fifth candidate is `migrateGameVersionSetting`. Plan 4 does NOT promote this symbol even though `parity_diff_report.json::gaps` attributes it to `owner_module: version_registry, squad: Squad B (version-registry/aux)`. The diff report's `owner_module` field is a parity-tracking HEURISTIC grouping (Squad B == version-registry/aux), NOT a direct reflection of where the symbol's Rust source actually lives. Live codebase grep confirms: (a) the NAPI wrapper `migrate_game_version_setting` lives in `classic-node/src/scangame.rs` (line ~1553), NOT in `src/version_registry.rs`, and (b) the core function `migrate_game_version_setting` lives in `classic-scangame-core/src/setup.rs` (line ~225), NOT in `classic-version-registry-core`. The CORRECT `rustCrate` value is `classic-scangame-core` (reflecting the actual source crate) — NOT `classic-version-registry-core` (which is only a parity-tracking grouping artifact). Plan 5 owns the row because Plan 5 is the designated cross-owner reconciliation plan for symbols whose diff-report `owner_module` doesn't match their actual source crate — this is exactly the kind of residual routing Plan 5 exists to handle. If Plan 4's execution-time re-read of `deferred_runtime_backlog.json` shows `migrateGameVersionSetting` still in the version_registry owner bucket, document this in the SUMMARY and escalate to Plan 5 — do NOT silently add it as a fifth row in Plan 4.

**Row shape examples**:
```json
{
  "id": "version-pe-extract",
  "tier": "tier1",
  "ownerModule": "version_registry",
  "rustCrate": "classic-version-core",
  "rustSymbol": "extract_pe_version",
  "nodeExport": "extractPeVersion",
  "nodeKind": "function"
},
{
  "id": "version-pe-is-valid-path",
  "tier": "tier1",
  "ownerModule": "version_registry",
  "rustCrate": "classic-version-core",
  "rustSymbol": "is_valid_executable_path",
  "nodeExport": "isValidPePath",
  "nodeKind": "function"
},
{
  "id": "version-pe-shape",
  "tier": "tier1",
  "ownerModule": "version_registry",
  "rustCrate": "classic-version-core",
  "rustSymbol": "PeVersionResult",
  "nodeExport": "JsPeVersion",
  "nodeKind": "interface"
},
// D1 adjudication 2026-04-09: RESTORED. parse_node_surface() emits a standalone interface entry
// for every `export interface` in index.d.ts (regex at generate_baseline.py line 301). Without this
// contract row, JsPeVersion becomes a new deferred backlog entry (empirically precedented by
// node-deferred-aux-108 tracking 5 existing interfaces as deferred) and Plan 4 regresses
// deferred_total by 1. The rustSymbol PeVersionResult is on the Rust surface via the `pub use`
// re-export at classic-version-core/src/lib.rs:43 (parse_rust_surface() handles both `pub use`
// and `pub type` regex paths). Follows the Fallout4VersionInfo precedent exactly.
{
  "id": "version-registry.crashgen-entry",
  "tier": "tier1",
  "ownerModule": "version_registry",
  "rustCrate": "classic-version-registry-core",
  "rustSymbol": "CrashgenRegistryEntry",
  "nodeExport": "JsCrashgenRegistryEntry",
  "nodeKind": "interface"
}
// ... 3 more for version_registry
```

**Python reference** (`ClassicLib-rs/python-bindings/classic-version-py/src/lib.rs` lines 300-398) — Python already exposes `extract_pe_version` and `is_valid_pe_path`. Node shape matches but with object return instead of tuple.

**U1 Python parity regression probe commands**:
```powershell
# After A6 pub use lands and generate_baseline.py runs for the Node gate,
# verify Python's shipped gate still exits zero:
cd J:/CLASSIC-Fallout4
python tools/python_api_parity/check_parity_gate.py --repo-root .
```
If Python's gate fails with a new `gap_type=rust_unmapped` row referencing `is_valid_executable_path`, investigate:
1. Does `classic-version-py` already bind `is_valid_executable_path`? If yes, the Python gate should already map it and stay green.
2. If not, either add a Python binding in the same commit as A6, OR narrow the Rust `pub use` to a feature gate (e.g., `#[cfg(feature = "node-bindings")]`).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: [A6 PREREQUISITE + U1 cross-binding probe] Add pub use is_valid_executable_path to classic-version-core/src/lib.rs AND verify Python parity gate stays green</name>
  <read_first>
    - `ClassicLib-rs/business-logic/classic-version-core/src/lib.rs` (confirm line 43 current state — `pub use pe_version::{PeVersionError, PeVersionResult, extract_pe_version};` — read the full file to find exact line; line number may shift slightly)
    - `ClassicLib-rs/business-logic/classic-version-core/src/pe_version.rs` (confirm `pub fn is_valid_executable_path` exists — line references in Research)
    - `ClassicLib-rs/python-bindings/classic-version-py/src/lib.rs` (U1 — check whether `is_valid_executable_path` is already bound to Python; if not, Python gate will fire)
    - `tools/python_api_parity/check_parity_gate.py` (U1 — understand the Python gate's invocation shape; it's analogous to the Node gate)
    - `.planning/phases/04-node-tier-collapse/04-CONTEXT.md` §Research Amendments A6 (load-bearing)
    - `.planning/phases/04-node-tier-collapse/04-RESEARCH.md` §Example 2 note ("is_valid_executable_path must be pub use-re-exported")
    - `.planning/phases/04-node-tier-collapse/04-REVIEWS.md` §"U1 — Plan 04 A6 cross-binding regression risk" (review rationale for the probe)
  </read_first>
  <action>
    Step 1 — Read `ClassicLib-rs/business-logic/classic-version-core/src/lib.rs` to find the exact line (expected around line 42-43):
    ```rust
    // Re-export PE version types for convenience
    pub use pe_version::{PeVersionError, PeVersionResult, extract_pe_version};
    ```

    Step 2 — Edit using the `Edit` tool to add `is_valid_executable_path` to the re-export list:
    ```rust
    // Re-export PE version types for convenience
    pub use pe_version::{PeVersionError, PeVersionResult, extract_pe_version, is_valid_executable_path};
    ```

    Step 3 — Verify the `classic-version-core` crate still compiles:
    ```powershell
    cd J:/CLASSIC-Fallout4
    cargo check -p classic-version-core --manifest-path ClassicLib-rs/Cargo.toml
    ```
    MUST exit 0 (the function already exists in the sub-module; re-exporting it is non-breaking).

    Step 4 — Refresh Node parity baselines so `rust_api_surface.json` picks up the new re-export (this is the bidirectional-guard probe path — it MUST run in the verify pipeline, NOT just in the action per Issue 2):
    ```powershell
    cd J:/CLASSIC-Fallout4
    python tools/node_api_parity/generate_baseline.py --repo-root . --write-baseline
    python tools/node_api_parity/check_parity_gate.py --repo-root . --update-baseline
    ```
    Gate still exits 0 (no contract rows reference `is_valid_executable_path` yet). Then verify the symbol lands in the parsed Rust surface:
    ```powershell
    python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/rust_api_surface.json')); syms = {s['symbol'] for s in d.get('symbols', []) if s.get('crate') == 'classic-version-core'}; assert 'is_valid_executable_path' in syms, 'A6 re-export missing from rust_api_surface.json'; print('A6 re-export probe PASSED')"
    ```

    Step 4.5 — **U1 cross-binding regression probe (CRITICAL)**: run the Python parity gate against the post-A6 Rust source to confirm Python's shipped Phase 3 gate still exits zero:
    ```powershell
    cd J:/CLASSIC-Fallout4
    python tools/python_api_parity/check_parity_gate.py --repo-root .
    ```
    **Expected behavior (PASS path)**: Python gate exits 0. `is_valid_executable_path` is either already exposed in Python bindings OR Python's tier1 mapping already accommodates it. Proceed to Step 5.

    **If Python gate FAILS** with a new `gap_type=rust_unmapped` row referencing `is_valid_executable_path` (U1 FAIL path):
    1. **Option A (PREFERRED)**: Add a Python binding in `ClassicLib-rs/python-bindings/classic-version-py/src/lib.rs` exposing `is_valid_executable_path`, update the Python `tier1Mappings` in the Python parity contract, regenerate Python baselines via `python tools/python_api_parity/generate_baseline.py --repo-root . --write-baseline`, and include the Python changes in the SAME atomic commit as the A6 re-export. Re-run BOTH Node and Python gates before staging.
    2. **Option B (FALLBACK)**: Narrow the Rust re-export to a feature gate. Revert the `lib.rs` edit and replace with:
       ```rust
       #[cfg(feature = "node-bindings-surface")]
       pub use pe_version::is_valid_executable_path;
       ```
       This requires adding a `node-bindings-surface` feature to `classic-version-core/Cargo.toml` and enabling it at `classic-node/Cargo.toml`. Document the choice in the SUMMARY.
    3. **Option C (ESCALATE)**: If neither A nor B is workable, STOP and surface as a checkpoint for user decision. Do NOT commit the failing state.

    Probe both gates one more time before proceeding:
    ```powershell
    cd J:/CLASSIC-Fallout4
    python tools/node_api_parity/check_parity_gate.py --repo-root .          # Node — MUST exit 0
    python tools/python_api_parity/check_parity_gate.py --repo-root .         # Python — MUST exit 0
    ```
    BOTH must exit 0 before the Task 1 commit lands.

    Step 5 — Commit as: `Feat: re-export is_valid_executable_path from classic-version-core (Phase 4 Plan 4 Task 1; A6 prerequisite for HARM-01; U1 cross-binding regression probed)` with the lib.rs edit + refreshed Node baselines (and any companion Python binding change if Option A was required).

    **Rationale in commit message:** Cite A6 and U1 and explain: "Prerequisite for the upcoming Node NAPI wrapper `isValidPePath` — the Node parity gate's bidirectional guard reads `lib.rs` re-exports, not sub-module public items, so the Node contract row for `is_valid_executable_path` would fail without this re-export. Cross-binding regression probe (U1) confirmed Python parity gate still exits zero after the re-export lands — no Phase 3 regression."
  </action>
  <verify>
    <automated>cargo check -p classic-version-core --manifest-path ClassicLib-rs/Cargo.toml && python tools/node_api_parity/generate_baseline.py --repo-root . --write-baseline && python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/rust_api_surface.json')); syms = {s['symbol'] for s in d.get('symbols', []) if s.get('crate') == 'classic-version-core'}; assert 'is_valid_executable_path' in syms, f'A6 re-export missing from rust_api_surface.json classic-version-core symbols: {sorted(syms)}'" && python tools/python_api_parity/check_parity_gate.py --repo-root .</automated>
  </verify>
  <acceptance_criteria>
    - `Select-String -Path ClassicLib-rs/business-logic/classic-version-core/src/lib.rs -Pattern 'pub use pe_version::.*is_valid_executable_path' -Quiet` returns `True` (confirms re-export lands; PowerShell-native per user rule)
    - `cargo check -p classic-version-core --manifest-path ClassicLib-rs/Cargo.toml` exits 0 (crate still compiles)
    - **Positive bidirectional-guard probe (Issue 2 fix)**: `python tools/node_api_parity/generate_baseline.py --repo-root . --write-baseline` exits 0, then `python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/rust_api_surface.json')); syms = {s['symbol'] for s in d.get('symbols', []) if s.get('crate') == 'classic-version-core'}; assert 'is_valid_executable_path' in syms, 'A6 re-export missing from rust_api_surface.json'"` exits 0. This verifies the A6 re-export flows into the parsed Rust surface via `generate_baseline.py --write-baseline` — the guard's probe path. Schema confirmed from live file: top-level `symbols` array, each entry has `{"symbol": str, "crate": str, "kind": str, ...}`.
    - `python tools/node_api_parity/check_parity_gate.py --repo-root .` exits 0 (Node gate still green since no contract rows reference the symbol yet)
    - **U1 cross-binding regression probe**: `python tools/python_api_parity/check_parity_gate.py --repo-root .` exits 0. If it fails, the executor MUST apply Option A/B/C from Step 4.5 before committing and re-run both gates before staging.
  </acceptance_criteria>
  <done>
    `is_valid_executable_path` is re-exported at `classic-version-core/src/lib.rs`. Crate compiles. Rust parity surface includes the symbol. BOTH Node AND Python parity gates exit 0 (U1 cross-binding regression probed). A6 prerequisite satisfied.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add NAPI wrappers (extract_pe_version, is_valid_pe_path, JsPeVersion) + regenerate index.d.ts + 7 contract rows + smoke tests</name>
  <read_first>
    - `ClassicLib-rs/node-bindings/classic-node/src/version.rs` (entire file — confirm existing pattern: `to_napi_err` helper at line 12, existing `#[napi] pub fn` wrappers, currently ~99 lines total — you are appending to the bottom)
    - `ClassicLib-rs/business-logic/classic-version-core/src/pe_version.rs` (lines 1-245 — confirm exact signature of `extract_pe_version` and `is_valid_executable_path` AND the type definition of `PeVersionResult` — it is `pub type PeVersionResult = Result<(u16, u16, u16, u16), PeVersionError>;`)
    - `ClassicLib-rs/node-bindings/classic-node/index.d.ts` (verify existing version.rs exports shape: parseVersion, tryParseVersion, etc. — your new exports will follow this pattern; also grep for `Fallout4VersionInfo` to see the existing interface row precedent for the D1 restoration)
    - `ClassicLib-rs/node-bindings/classic-node/__test__/version.spec.ts` (existing bun:test pattern — you append new describe blocks)
    - `ClassicLib-rs/node-bindings/classic-node/__test__/version_registry.spec.ts` (existing pattern for the 4 version_registry rows' tests)
    - `ClassicLib-rs/node-bindings/classic-node/__test__/runtime.node.test.mjs`
    - `ClassicLib-rs/python-bindings/classic-version-py/src/lib.rs` lines 300-398 (Python reference implementation for error classification pattern)
    - `.planning/phases/04-node-tier-collapse/04-RESEARCH.md` §Code Examples 1-4 (exact expected shape of JsPeVersion, the NAPI wrappers, the version.spec.ts tests, and the runtime_coverage_registry entry)
    - `.planning/phases/04-node-tier-collapse/04-CONTEXT.md` §D-PE-01..04 (PE-version API decisions)
    - `.planning/phases/04-node-tier-collapse/04-REVIEWS.md` §"D1 Adjudication" (proves `version-pe-shape` row is required; do NOT skip — this is load-bearing)
    - `docs/implementation/node_api_parity/baseline/parity_contract.json` (grep for `Fallout4VersionInfo` to find the existing interface-row precedent for D1; verify the exact JSON shape before authoring `version-pe-shape`)
    - `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json` (filter ownerModule: "version_registry" to get the authoritative 4-vs-5 count)
    - `tools/binding_parity_runtime_coverage.py::_stable_id_hash` (D-HASH-01 mandatory)
    - `ClassicLib-rs/node-bindings/classic-node/src/scangame.rs` (source the rustSymbol values for the 4 version_registry rows; grep for `check_crashgen_config_with_rules`, `check_crashgen_full_with_rules`, etc. to confirm the exact snake_case signatures)
  </read_first>
  <behavior>
    - `src/version.rs` grows by ~40-50 lines appended at the bottom: `use std::path::Path;` (if not already imported), `#[napi(object)] pub struct JsPeVersion` with `major/minor/patch/build: u32`, `#[napi] pub fn extract_pe_version(path: String) -> Result<JsPeVersion>`, `#[napi] pub fn is_valid_pe_path(path: String) -> bool`.
    - The NAPI wrappers delegate to `classic_version_core::pe_version::extract_pe_version(Path::new(&path))` and `classic_version_core::pe_version::is_valid_executable_path(Path::new(&path))` with no business logic in the binding.
    - Errors convert via the existing `to_napi_err()` helper (message-only, no `.code` field per D-PE-02/D-ERR-01).
    - `bun run build` regenerates `index.d.ts` with the 3 new exports (`extractPeVersion`, `isValidPePath`, `JsPeVersion`). The regenerated file is committed atomically in the same commit as the Rust source edit (D-DTS-01).
    - **7 new tier1Mappings rows added**: 3 PE-version (version-pe-extract, version-pe-is-valid-path, version-pe-shape) + 4 version_registry. All carry rustCrate field. The `version-pe-shape` row follows the `Fallout4VersionInfo` precedent exactly (rustSymbol: "PeVersionResult", nodeExport: "JsPeVersion", nodeKind: "interface").
    - `__test__/version.spec.ts` gains `describe("extractPeVersion", ...)` and `describe("isValidPePath", ...)` blocks. Windows-only `kernel32.dll` integration test is guarded by `if (process.platform === "win32") { ... }`.
    - `__test__/version_registry.spec.ts` gains describe blocks for the 4 version_registry exports. Signatures verified against `index.d.ts` BEFORE test authoring (Medium concern: no pseudo-signatures).
    - `__test__/runtime.node.test.mjs` gains at least 2 new tests: one for PE-version (Windows-guarded), one for checkCrashgenConfigWithRules.
    - `runtime_coverage_registry.json` has a new dedicated selector for the 7 new rows with contractIdsHash via `_stable_id_hash`.
  </behavior>
  <action>
    Step 1 — Append to `ClassicLib-rs/node-bindings/classic-node/src/version.rs` at the end of file (after existing `format_version` function around line 99):
    ```rust

    use std::path::Path;

    /// PE file version components (4-part file version from VS_VERSIONINFO).
    ///
    /// Returned by `extractPeVersion`. All fields are `u16` in the underlying Rust
    /// crate but widened to `u32` for NAPI convention. JavaScript receives plain numbers.
    #[napi(object)]
    pub struct JsPeVersion {
        pub major: u32,
        pub minor: u32,
        pub patch: u32,
        pub build: u32,
    }

    /// Extract a PE file's version from its VS_VERSIONINFO resource.
    ///
    /// Accepts `.exe` and `.dll` files. Delegates to
    /// `classic_version_core::pe_version::extract_pe_version`.
    ///
    /// @param path  Filesystem path to a PE file (absolute or relative).
    /// @returns     Object `{ major, minor, patch, build }`.
    /// @throws      napi::Error if the path is not a valid PE file, the file
    ///              cannot be read, or no version resource is present.
    #[napi]
    pub fn extract_pe_version(path: String) -> Result<JsPeVersion> {
        let (major, minor, patch, build) =
            classic_version_core::pe_version::extract_pe_version(Path::new(&path))
                .map_err(to_napi_err)?;
        Ok(JsPeVersion {
            major: u32::from(major),
            minor: u32::from(minor),
            patch: u32::from(patch),
            build: u32::from(build),
        })
    }

    /// Check whether a path points to a valid executable or DLL file.
    ///
    /// Delegates to `classic_version_core::pe_version::is_valid_executable_path`.
    /// Never throws — returns `false` for unreadable, non-existent, or
    /// wrong-extension paths.
    ///
    /// @param path  Filesystem path to check.
    /// @returns     `true` if the path exists, is a file, and ends in `.exe` or `.dll`.
    #[napi]
    pub fn is_valid_pe_path(path: String) -> bool {
        classic_version_core::pe_version::is_valid_executable_path(Path::new(&path))
    }
    ```
    Check whether `use std::path::Path;` is already imported at the top — if yes, omit the duplicate import.

    Step 2 — Regenerate `index.d.ts` via `bun run build`. Prefer PowerShell per user rule. If invoking from Git Bash, source `tools/use_msvc_from_git_bash.sh` first to prevent Git's `link.exe` from shadowing the MSVC linker (CLAUDE.md Key Gotcha):
    ```powershell
    # PowerShell entry point (preferred):
    cd J:/CLASSIC-Fallout4/ClassicLib-rs/node-bindings/classic-node
    bun run build
    ```
    Git Bash equivalent (only if PowerShell unavailable):
    ```bash
    cd J:/CLASSIC-Fallout4
    source tools/use_msvc_from_git_bash.sh
    cd ClassicLib-rs/node-bindings/classic-node
    bun run build
    ```
    MUST exit 0. Verify (PowerShell-native):
    ```powershell
    cd J:/CLASSIC-Fallout4/ClassicLib-rs/node-bindings/classic-node
    Select-String -Path index.d.ts -Pattern 'export declare function extractPeVersion' -Quiet
    Select-String -Path index.d.ts -Pattern 'export declare function isValidPePath' -Quiet
    Select-String -Path index.d.ts -Pattern 'export interface JsPeVersion' -Quiet
    ```
    All three MUST return `True`.

    Step 3 — Append PE-version describe blocks to `__test__/version.spec.ts`:
    ```typescript
    import { extractPeVersion, isValidPePath } from "../index.js";
    import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
    import { join } from "node:path";
    import { tmpdir } from "node:os";

    describe("isValidPePath", () => {
      test("returns false for non-existent path", () => {
        expect(isValidPePath("/definitely/not/real.exe")).toBe(false);
      });

      test("returns false for wrong extension", () => {
        const dir = mkdtempSync(join(tmpdir(), "classic-pe-"));
        const txtPath = join(dir, "readme.txt");
        writeFileSync(txtPath, "not a pe file");
        try {
          expect(isValidPePath(txtPath)).toBe(false);
        } finally {
          rmSync(dir, { recursive: true, force: true });
        }
      });

      test("returns true for .exe file that exists", () => {
        const dir = mkdtempSync(join(tmpdir(), "classic-pe-"));
        const exePath = join(dir, "fake.exe");
        writeFileSync(exePath, Buffer.alloc(0));
        try {
          expect(isValidPePath(exePath)).toBe(true);
        } finally {
          rmSync(dir, { recursive: true, force: true });
        }
      });

      test("returns true for .dll file that exists (case-insensitive)", () => {
        const dir = mkdtempSync(join(tmpdir(), "classic-pe-"));
        const dllPath = join(dir, "fake.DLL");
        writeFileSync(dllPath, Buffer.alloc(0));
        try {
          expect(isValidPePath(dllPath)).toBe(true);
        } finally {
          rmSync(dir, { recursive: true, force: true });
        }
      });
    });

    describe("extractPeVersion", () => {
      test("throws on non-existent path", () => {
        expect(() => extractPeVersion("/definitely/not/real.exe")).toThrow();
      });

      test("throws on bytes that aren't a PE file", () => {
        const dir = mkdtempSync(join(tmpdir(), "classic-pe-"));
        const fakeExe = join(dir, "fake.exe");
        writeFileSync(fakeExe, Buffer.from("not a real PE file"));
        try {
          expect(() => extractPeVersion(fakeExe)).toThrow();
        } finally {
          rmSync(dir, { recursive: true, force: true });
        }
      });

      if (process.platform === "win32") {
        test("extracts version from kernel32.dll (Windows integration)", () => {
          const version = extractPeVersion("C:\\Windows\\System32\\kernel32.dll");
          expect(version.major).toBeGreaterThanOrEqual(6);
          expect(typeof version.minor).toBe("number");
          expect(typeof version.patch).toBe("number");
          expect(typeof version.build).toBe("number");
        });
      }
    });
    ```

    Step 4 — Append version_registry describe blocks to `__test__/version_registry.spec.ts`.

    **Pre-authoring signature verification (MEDIUM concern fix)**: BEFORE writing any test body that invokes `checkCrashgenConfigWithRules` or `checkCrashgenFullWithRules`, extract the live signatures from the Rust source and from `index.d.ts`:
    ```powershell
    cd J:/CLASSIC-Fallout4
    # Confirm Rust signature
    Select-String -Path ClassicLib-rs/node-bindings/classic-node/src/scangame.rs -Pattern 'fn check_crashgen_config_with_rules|fn check_crashgen_full_with_rules' -Context 0,5
    # Confirm TypeScript signature
    Select-String -Path ClassicLib-rs/node-bindings/classic-node/index.d.ts -Pattern 'checkCrashgenConfigWithRules|checkCrashgenFullWithRules' -Context 0,3
    ```
    Record the live signatures. DO NOT author tests against guessed signatures — if the live signature does not match what the test body below assumes, update the test body to match before running. Block on signature mismatch.

    Test body (adjust argument shape to match the actual verified signatures):
    ```typescript
    import { describe, test, expect } from "bun:test";
    import {
      JsCrashgenRegistryEntry,
      JsCrashgenSettingsRules,
      checkCrashgenConfigWithRules,
      checkCrashgenFullWithRules,
    } from "../index.js";

    describe("version_registry: crashgen registry entry + rules interfaces", () => {
      test("JsCrashgenRegistryEntry has expected field types", () => {
        // Shape assertion — use real expected field check rather than toBeDefined
        const entry = {
          game: "fallout4",
          game_id: "Fallout4",
          name: "Buffout 4",
          // ... populate per verified interface shape from index.d.ts
        } as unknown as JsCrashgenRegistryEntry;
        expect(typeof entry.game).toBe("string");
      });
      test("JsCrashgenSettingsRules has expected field types", () => {
        // Round 2 LOW sweep: replaced `{} as JsCrashgenSettingsRules` + `toBeDefined()` with
        // a minimal literal matching the Round 2 verified core type at classic-crashgen-settings-core/src/lib.rs:226.
        // Pre-authoring: grep the live `pub struct CrashgenSettingsRules` fields and adjust the literal below.
        const rules = {
          check_rules: [],
          preflight_rules: [],
        } as unknown as JsCrashgenSettingsRules;
        // Assert typed fields exist on the literal (runtime check; the type binding ensures
        // these field names match the NAPI-generated interface at compile time)
        expect(Array.isArray(rules.check_rules) || rules.check_rules === undefined).toBe(true);
      });
    });

    describe("version_registry: checkCrashgen*WithRules functions", () => {
      test("checkCrashgenConfigWithRules callable with verified signature", () => {
        // Use the signature verified via Select-String above
        try {
          const result = checkCrashgenConfigWithRules("fallout4", {} as JsCrashgenSettingsRules);
          expect(result).toBeDefined();
        } catch (e) {
          // Function may reject empty rules — assert the error shape rather than silently pass
          expect(e).toBeInstanceOf(Error);
        }
      });
      test("checkCrashgenFullWithRules callable with verified signature", () => {
        try {
          const result = checkCrashgenFullWithRules("fallout4", {} as JsCrashgenSettingsRules);
          expect(result).toBeDefined();
        } catch (e) {
          expect(e).toBeInstanceOf(Error);
        }
      });
    });
    ```

    Step 5 — Append to `__test__/runtime.node.test.mjs`. The must_have requires BOTH PE-version AND version_registry runtime test coverage, so BOTH are MANDATORY (Round 2 Fix 4.3 — removed "if practical" downgrade):
    ```javascript
    import { test } from "node:test";
    import assert from "node:assert/strict";
    import {
      isValidPePath,
      extractPeVersion,
      checkCrashgenConfigWithRules,
    } from "../index.js";

    test("version: isValidPePath returns false for nonexistent (cross-runtime D-TEST-02)", () => {
      assert.strictEqual(isValidPePath("/nonexistent/path.exe"), false);
    });

    if (process.platform === "win32") {
      test("version: extractPeVersion against kernel32.dll (Windows-only D-TEST-02)", () => {
        const version = extractPeVersion("C:\\\\Windows\\\\System32\\\\kernel32.dll");
        assert.ok(version !== undefined);
        assert.strictEqual(typeof version.major, "number");
      });
    }

    // MANDATORY per Round 2 Fix 4.3 — not "if practical". The must_have requires version_registry
    // runtime coverage alongside PE-version coverage. The executor uses the signatures locked by
    // Task 2 Step 4's pre-authoring verification (same live grep as the bun:test test body).
    test("version_registry: checkCrashgenConfigWithRules callable with typed return (cross-runtime D-TEST-02)", () => {
      // Use the LOCKED signature from the scangame.rs Pre-Step 6a grep.
      // The function signature is: checkCrashgenConfigWithRules(pluginsPath, crashgenName, settingsRules?)
      // Passing minimal valid arguments. On empty plugins path, the function either returns a
      // result object or throws — either outcome is an acceptable typed signal.
      try {
        const result = checkCrashgenConfigWithRules("", "Buffout4");
        assert.ok(result !== undefined, "result must be defined");
        assert.ok(typeof result === "object", "result must be an object");
      } catch (e) {
        // A thrown Error is acceptable — signals the function is callable and validates input
        assert.ok(e instanceof Error, "thrown value must be an Error");
      }
    });
    ```

    Step 6 — Author **7 new contract rows** in `parity_contract.json::tier1Mappings` (D1 adjudication 2026-04-09: was 6, restored to 7):

    **3 PE-version rows** with rustCrate: "classic-version-core":
    ```json
    {
      "id": "version-pe-extract",
      "tier": "tier1",
      "ownerModule": "version_registry",
      "rustCrate": "classic-version-core",
      "rustSymbol": "extract_pe_version",
      "nodeExport": "extractPeVersion",
      "nodeKind": "function"
    },
    {
      "id": "version-pe-is-valid-path",
      "tier": "tier1",
      "ownerModule": "version_registry",
      "rustCrate": "classic-version-core",
      "rustSymbol": "is_valid_executable_path",
      "nodeExport": "isValidPePath",
      "nodeKind": "function"
    },
    {
      "id": "version-pe-shape",
      "tier": "tier1",
      "ownerModule": "version_registry",
      "rustCrate": "classic-version-core",
      "rustSymbol": "PeVersionResult",
      "nodeExport": "JsPeVersion",
      "nodeKind": "interface"
    }
    ```
    **D1 adjudication rationale (do NOT remove `version-pe-shape`)**: The iteration-1 plan-checker dropped this row on the theory that `PeVersionResult` is a `Result<>` type alias and therefore "covered implicitly" via `extractPeVersion`'s typed return. Cross-AI review (Claude vs Codex) empirically proved this is mechanically wrong: `parse_node_surface()` (generate_baseline.py line 301) emits a standalone `{ export: "JsPeVersion", kind: "interface" }` entry for every `export interface` in `index.d.ts`, and `node-deferred-aux-108` in the deferred backlog empirically proves that such standalone interface entries without tier1Mappings rows become `classification=deferred, tier=tier2` — regressing `deferred_total`. The `Fallout4VersionInfo` row at `parity_contract.json::tier1Mappings` is the canonical precedent for this shape (a Rust struct/type-alias source mapped to a Node interface export). The row MUST be present for Plan 4's plan-local invariant (`deferred_total` drops by exactly the row count added) to hold.

    **Pre-Step 6a (Round 2 Fix 4.2) — Lock rustSymbol AND rustCrate via live grep (NO "likely" language, mirrors D-07 signature-verification pattern)**:

    Before authoring any of the 4 version_registry rows, the executor MUST run the following greps to LOCK the exact rustSymbol AND rustCrate values. Round 1's plan used "likely `CrashgenRegistryEntry` in `classic-version-registry-core`" which is exactly the kind of guessing U5 was meant to eliminate. Round 2 empirical codebase verification found:

    - `check_crashgen_config_with_rules` + `check_crashgen_full_with_rules`: NAPI wrappers live in `classic-node/src/scangame.rs`, NOT `src/version_registry.rs`. There are no matching core functions with those exact names — the NAPI functions compose `JsCrashgenChecker::new(...).check()` which internally uses `classic-crashgen-settings-core::CrashgenSettingsRules` plus the scangame crashgen orchestrator. The executor must grep to determine the correct rustSymbol.
    - `JsCrashgenRegistryEntry`: NAPI struct lives in `classic-node/src/crashgen_rules.rs`. There is NO core `CrashgenRegistryEntry` struct in any Rust crate — it's a pure NAPI wrapper.
    - `JsCrashgenSettingsRules`: NAPI struct lives in `classic-node/src/crashgen_rules.rs`. The underlying core type IS `CrashgenSettingsRules` in `classic-crashgen-settings-core/src/lib.rs`.

    Run (PowerShell):
    ```powershell
    cd J:/CLASSIC-Fallout4
    # Find the NAPI function definitions
    Select-String -Path ClassicLib-rs/node-bindings/classic-node/src/scangame.rs -Pattern 'pub fn check_crashgen_config_with_rules|pub fn check_crashgen_full_with_rules' -Context 0,6
    # Find the NAPI struct definitions
    Select-String -Path ClassicLib-rs/node-bindings/classic-node/src/crashgen_rules.rs -Pattern 'pub struct JsCrashgenRegistryEntry|pub struct JsCrashgenSettingsRules' -Context 0,12
    # Find the core CrashgenSettingsRules struct
    Select-String -Path ClassicLib-rs/business-logic/classic-crashgen-settings-core/src/lib.rs -Pattern '^pub struct CrashgenSettingsRules' -Context 0,2
    # Confirm there is NO CrashgenRegistryEntry in any -core crate (should return zero matches)
    Select-String -Path ClassicLib-rs/business-logic/*/src/*.rs -Pattern '^pub struct CrashgenRegistryEntry' -Recurse
    ```

    **Locking decisions the executor MUST make from the grep output**:

    1. For `checkCrashgenConfigWithRules` + `checkCrashgenFullWithRules`:
       - rustSymbol: MUST be the actual `pub fn <name>` found in scangame.rs (expected: `check_crashgen_config_with_rules` / `check_crashgen_full_with_rules`).
       - rustCrate: Because these are NAPI-only composing functions (no matching core function), EITHER (a) use `classic-scangame-core` if a matching core helper exists after a recursive grep, OR (b) use an `@rust`-suffix proxy row per the Phase 3 Scenario E pattern, OR (c) return `## CHECKPOINT REACHED` escalating to user for routing decision. Document the choice in the SUMMARY.
    2. For `JsCrashgenRegistryEntry`:
       - There is NO core type with the exact name `CrashgenRegistryEntry`. The NAPI struct fields are composed from `CrashgenSettingsRules` + raw string fields.
       - OPTIONS: (a) use `@rust`-suffix proxy row with rustSymbol `JsCrashgenRegistryEntry@rust` and rustCrate `<choose a natural owning crate or classic-node>`, OR (b) if a matching core type is found via recursive grep at Pre-Step 6a execution time, use that, OR (c) escalate to user.
    3. For `JsCrashgenSettingsRules`:
       - rustSymbol: `CrashgenSettingsRules` (verified at `classic-crashgen-settings-core/src/lib.rs:226`).
       - rustCrate: `classic-crashgen-settings-core`.

    If ANY symbol cannot be unambiguously located by Pre-Step 6a's grep, return `## CHECKPOINT REACHED` escalating to the user for rustCrate clarification. Do NOT author a row with a guessed rustCrate value.

    **4 version_registry rows** — exact nodeExport values and locked rustSymbol/rustCrate per Pre-Step 6a:
    - `JsCrashgenRegistryEntry`: nodeKind=interface; rustSymbol/rustCrate LOCKED via Pre-Step 6a
    - `JsCrashgenSettingsRules`: nodeKind=interface; rustSymbol=`CrashgenSettingsRules`, rustCrate=`classic-crashgen-settings-core` (verified Round 2 codebase grep)
    - `checkCrashgenConfigWithRules`: nodeKind=function; rustSymbol/rustCrate LOCKED via Pre-Step 6a
    - `checkCrashgenFullWithRules`: nodeKind=function; rustSymbol/rustCrate LOCKED via Pre-Step 6a

    NO "likely" language may appear in the row authoring — every field must be grep-verified.

    Step 7 — Update `runtime_coverage_registry.json`. Add new selector `node-tier1-version-registry-plan04-promoted` with bindingIdentifiers covering all 7 new rows (3 PE + 4 version_registry). Compute contractIdsHash via `_stable_id_hash`.

    Step 8 — Full verification:
    ```powershell
    cd J:/CLASSIC-Fallout4/ClassicLib-rs/node-bindings/classic-node
    bun run parity:gate:local
    bun run test:bun
    bun run test:node
    ```
    All three MUST exit 0. `dts:freshness:check` (part of parity:gate:local) MUST pass because the regenerated index.d.ts is staged atomically.

    Step 9 — Commit as: `Feat: add extractPeVersion + isValidPePath NAPI exports + promote 4 version_registry entries (Phase 4 Plan 4 Task 2; HARM-01, HARM-02, NODE-02, NODE-04, NODE-05; D1 version-pe-shape restored)` in one atomic commit containing:
    - src/version.rs (new NAPI wrappers)
    - index.d.ts (regenerated)
    - __test__/version.spec.ts (new PE describe blocks)
    - __test__/version_registry.spec.ts (new version_registry describe blocks)
    - __test__/runtime.node.test.mjs (new cross-runtime tests)
    - __test__/fixtures/runtime_coverage_registry.json (new selector)
    - docs/implementation/node_api_parity/baseline/*.json and *.md (refreshed)
  </action>
  <verify>
    <automated>cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local && bun run test:bun && bun run test:node</automated>
  </verify>
  <acceptance_criteria>
    - `Select-String -Path ClassicLib-rs/node-bindings/classic-node/src/version.rs -Pattern 'pub fn extract_pe_version' -Quiet` returns `True`
    - `Select-String -Path ClassicLib-rs/node-bindings/classic-node/src/version.rs -Pattern 'pub fn is_valid_pe_path' -Quiet` returns `True`
    - `Select-String -Path ClassicLib-rs/node-bindings/classic-node/src/version.rs -Pattern 'pub struct JsPeVersion' -Quiet` returns `True`
    - `Select-String -Path ClassicLib-rs/node-bindings/classic-node/index.d.ts -Pattern 'extractPeVersion' -Quiet` returns `True`
    - `Select-String -Path ClassicLib-rs/node-bindings/classic-node/index.d.ts -Pattern 'isValidPePath' -Quiet` returns `True`
    - `Select-String -Path ClassicLib-rs/node-bindings/classic-node/index.d.ts -Pattern 'interface JsPeVersion' -Quiet` returns `True`
    - **D1 row-count enforcement**: `python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/parity_contract.json')); ids = {r['id'] for r in d['tier1Mappings']}; assert {'version-pe-extract', 'version-pe-is-valid-path', 'version-pe-shape'}.issubset(ids), f'D1: all 3 PE rows must be present; missing: {set([\"version-pe-extract\", \"version-pe-is-valid-path\", \"version-pe-shape\"]) - ids}'"` exits 0
    - **D1 row shape enforcement**: `python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/parity_contract.json')); shape = next(r for r in d['tier1Mappings'] if r.get('id') == 'version-pe-shape'); assert shape['rustSymbol'] == 'PeVersionResult', f'version-pe-shape.rustSymbol must be PeVersionResult, got {shape[\"rustSymbol\"]}'; assert shape['nodeExport'] == 'JsPeVersion', f'version-pe-shape.nodeExport must be JsPeVersion'; assert shape['nodeKind'] == 'interface'; assert shape['rustCrate'] == 'classic-version-core'"` exits 0
    - **A3 rustCrate enforcement for PE rows (MEDIUM concern fix)**: `python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/parity_contract.json')); pe_rows = [r for r in d['tier1Mappings'] if r.get('id', '').startswith('version-pe-')]; assert len(pe_rows) == 3, f'expected 3 PE rows, got {len(pe_rows)}'; assert all(r.get('rustCrate') == 'classic-version-core' for r in pe_rows), 'all 3 PE rows must carry rustCrate classic-version-core'"` exits 0
    - **Fix 4.1 rustCrate enforcement for version_registry rows (Round 2)**: The 4 version_registry rows (JsCrashgenRegistryEntry / JsCrashgenSettingsRules / checkCrashgenConfigWithRules / checkCrashgenFullWithRules) must carry the rustCrate field per A3, mirroring the 3 PE rows' enforcement pattern. The exact rustCrate value is LOCKED via Fix 4.2 Pre-Step 6a grep below (the earlier draft said "classic-version-registry-core" but the live symbols actually live in `classic-crashgen-settings-core` and `classic-node/src/scangame.rs` — the executor MUST verify via grep before authoring, NOT assume). After the executor's grep locks the correct rustCrate value(s), assert that every version_registry row carries a non-empty rustCrate field: `python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/parity_contract.json')); vr_rows = [r for r in d['tier1Mappings'] if r.get('nodeExport') in ('JsCrashgenRegistryEntry', 'JsCrashgenSettingsRules', 'checkCrashgenConfigWithRules', 'checkCrashgenFullWithRules')]; assert len(vr_rows) == 4, f'expected 4 version_registry rows, got {len(vr_rows)}'; assert all(r.get('rustCrate') for r in vr_rows), 'all 4 version_registry rows must have a non-empty rustCrate'; assert all(r.get('rustCrate', '').startswith('classic-') for r in vr_rows), 'all 4 version_registry rows rustCrate must name a real classic-* crate'"` exits 0
    - `python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json')); per_owner = d.get('per_owner', {}); assert per_owner.get('version_registry', {}).get('deferred', -1) == 0"` exits 0
    - **Fix 4.2 rustSymbol lock-via-grep (Round 2)**: Pre-Step 6a's Select-String output was used to lock the rustSymbol AND rustCrate values for the 4 version_registry rows. No "likely" language remains in the plan action. The locked rustSymbol values match the exact symbols output by Pre-Step 6a grep: `Select-String -Path ClassicLib-rs/node-bindings/classic-node/src/scangame.rs -Pattern 'pub fn check_crashgen_config_with_rules' -Quiet` returns `True` AND `Select-String -Path ClassicLib-rs/business-logic/classic-crashgen-settings-core/src/lib.rs -Pattern 'pub struct CrashgenSettingsRules' -Quiet` returns `True`.
    - `cd ClassicLib-rs/node-bindings/classic-node && bun run dts:freshness:check` exits 0 (confirms committed index.d.ts matches fresh build)
    - `cd ClassicLib-rs/node-bindings/classic-node && bun run test:bun` exits 0
    - `cd ClassicLib-rs/node-bindings/classic-node && bun run test:node` exits 0
    - **Fix 4.3 mandatory version_registry runtime coverage (Round 2)**: `runtime.node.test.mjs` contains a test that calls `checkCrashgenConfigWithRules(...)` with minimal valid input and asserts a typed return shape (object or Error). Verified via: `Select-String -Path ClassicLib-rs/node-bindings/classic-node/__test__/runtime.node.test.mjs -Pattern 'checkCrashgenConfigWithRules\(' -Quiet` returns `True`. The must_have's "both PE-version AND version_registry runtime coverage" requirement is satisfied with NO "if practical" downgrade.
  </acceptance_criteria>
  <done>
    extractPeVersion + isValidPePath NAPI exports exist, index.d.ts regenerated + committed atomically, **7** new contract rows land (3 PE with version-pe-shape restored per D1 + 4 version_registry), smoke tests pass in both runtimes, version_registry.deferred == 0. HARM-01 and HARM-02 satisfied.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Verify PE-version parity against Python binding</name>
  <what-built>
    - A6 pub use prerequisite landed (with U1 cross-binding regression probe confirmed green for both Node AND Python gates)
    - extractPeVersion, isValidPePath, JsPeVersion NAPI exports in classic-node
    - 7 new contract rows (3 PE including version-pe-shape per D1 adjudication + 4 version_registry)
    - Smoke tests in bun:test + node:test (with Windows-only kernel32.dll integration)
    - Updated runtime coverage registry
  </what-built>
  <action>
    Run Node and Python PE-version smoke tests and compare results. Present both outputs to the user for explicit approval. This is the HARM-02 parity verification that cannot be automated because it needs both runtimes in one shell.
  </action>
  <how-to-verify>
    1. Run Node PE-version smoke: `cd ClassicLib-rs/node-bindings/classic-node && bun test __test__/version.spec.ts -t "extractPeVersion"` — Windows integration test should print a real kernel32.dll version tuple.
    2. Run Python PE-version smoke (from any Windows shell with the `uv` venv active):
       ```powershell
       cd J:/CLASSIC-Fallout4
       uv run python -c "import classic_version; v = classic_version.extract_pe_version('C:\\Windows\\System32\\kernel32.dll'); print(f'python: {v}')"
       ```
       Record the Python tuple.
    3. Compare the two versions — they MUST be identical. The Node object `{major: X, minor: Y, patch: Z, build: W}` must match the Python tuple `(X, Y, Z, W)` component-for-component.
    4. If they differ, something is wrong with the widening (u16 → u32) or the delegation — investigate before proceeding.
    5. Run the full Node test suite: `bun run parity:gate:local && bun run test:bun && bun run test:node` — all exit 0.
    6. Confirm per_owner.version_registry.deferred == 0 in the refreshed runtime_coverage_summary.json.
    7. Confirm `version-pe-shape` row is present in parity_contract.json with the exact D1 shape (rustSymbol: PeVersionResult, nodeExport: JsPeVersion, rustCrate: classic-version-core).
  </how-to-verify>
  <verify>
    <automated>cd ClassicLib-rs/node-bindings/classic-node &amp;&amp; bun run parity:gate:local &amp;&amp; bun run test:bun &amp;&amp; bun run test:node</automated>
  </verify>
  <done>User confirms that Node and Python PE-version outputs match component-for-component; per_owner.version_registry.deferred == 0; version-pe-shape row is present per D1 adjudication.</done>
  <resume-signal>Type "approved" (or provide the parity comparison result) to proceed to Plan 5 (aux promotion).</resume-signal>
</task>

</tasks>

<verification>
1. `Select-String -Path ClassicLib-rs/business-logic/classic-version-core/src/lib.rs -Pattern 'pub use pe_version::.*is_valid_executable_path' -Quiet` returns `True` (A6)
2. `bun run parity:gate:local && bun run test:bun && bun run test:node` all exit 0
3. `bun run dts:freshness:check` exits 0
4. Per-owner.version_registry.deferred == 0
5. `tier1Mappings` count grew by **7** from the Plan 3 baseline (3 PE + 4 version_registry; D1 adjudication 2026-04-09 restored version-pe-shape)
6. Cross-runtime tests pass in both bun and node runners
7. **U1 cross-binding probe**: `python tools/python_api_parity/check_parity_gate.py --repo-root .` exits 0 (no Phase 3 Python parity regression)
8. **D1 row presence**: `version-pe-shape` row exists in `parity_contract.json::tier1Mappings` with `rustSymbol: PeVersionResult`, `nodeExport: JsPeVersion`, `nodeKind: interface`, `rustCrate: classic-version-core`
</verification>

<success_criteria>
- HARM-01 satisfied: extractPeVersion and isValidPePath exist in index.d.ts
- HARM-02 satisfied: extractPeVersion returns `{major, minor, patch, build}` typed object
- NODE-02 incrementally satisfied: 7 new rows landed (3 PE + 4 version_registry; D1 adjudication restored version-pe-shape)
- NODE-04 satisfied for this plan's scope: index.d.ts regenerated + committed atomically
- NODE-05 satisfied: smoke tests pass in both runtimes
- A6 prerequisite landed first (bisect-clean)
- U1 cross-binding regression probe: Python parity gate exits 0 post-A6
- version_registry.deferred drops to 0
</success_criteria>

<output>
Create `.planning/phases/04-node-tier-collapse/04-04-version-registry-and-pe-version-SUMMARY.md` with:
- Confirmation the A6 pub use landed in a separate commit OR in the Task 2 atomic commit (document choice)
- Confirmation that U1 cross-binding regression probe passed (Python gate exit code + whether Option A companion Python binding was required)
- Manual Python vs Node parity check result (the two version tuples)
- Any NAPI build surprises (Pitfall 2/3 — stale index.d.ts, MSVC shadowing)
- Final version_registry row count in tier1Mappings (**should be +7 from Plan 3 baseline, not +6**)
- Windows-only kernel32.dll test result (version tuple printed)
- Explicit confirmation that `version-pe-shape` row is present per D1 adjudication 2026-04-09
</output>
