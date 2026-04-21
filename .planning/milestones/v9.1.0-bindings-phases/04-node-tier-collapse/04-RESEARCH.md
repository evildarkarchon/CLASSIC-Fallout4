# Phase 4: Node Tier Collapse - Research

**Researched:** 2026-04-08
**Domain:** Node parity tooling + NAPI-RS bindings + parity artifact cascade
**Confidence:** HIGH (all findings cross-verified against live source files)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**PE-version API shape (HARM-01, HARM-02):**

- **D-PE-01** — `extractPeVersion(path: string)` returns a typed object `{ major: number, minor: number, patch: number, build: number }` (all widen from Rust `u16` to JS `number`). Intentionally diverges from Python tuple and C++ string shapes per the "document, don't standardize" Pitfall 7 stance.
- **D-PE-02** — Failure throws `napi::Error` via the existing `to_napi_err()` pattern (`napi::Error::from_reason(format!("{err}"))`). No `.code` field. Message-only convention, consistent with all `version.rs` exports.
- **D-PE-03** — `isValidPePath(path: string) -> boolean` exported as a sibling NAPI function. Synchronous, never throws; returns `false` for unreadable/non-existent/wrong-extension paths.
- **D-PE-04** — Both functions live in existing `ClassicLib-rs/node-bindings/classic-node/src/version.rs` (append at bottom). No new `mod pe_version;`. Tests append to `__test__/version.spec.ts` as new `describe` blocks.

**Plan decomposition:**

- **D-PLAN-01** — 5–7 plans total. Provisional skeleton: (1) Tooling expansion + camelCase guard + A10 sizing + env smoke, (2) scanlog promotion, (3) config promotion, (4) version_registry + HARM-01/02 PE-version, (5) aux promotion, (6) Tier-2 cleanup atomic cascade. Plan count may grow to 7 if A10 sizing reveals residual rows that warrant a dedicated wave.
- **D-PLAN-02** — Scanlog's 67 deferred rows land in a single plan. No sub-module slicing.
- **D-PLAN-03** — HARM-01/02 bundles with version_registry promotion plan (Plan 4). PE-version contract rows land in the same refresh as version_registry's 4 promoted rows.
- **D-PLAN-04** — Tier-2 cleanup is a single M7-style atomic cascade in the final plan. Bisect-clean: every commit fully passes or fully fails the gate.
- **D-PLAN-05** — Plan 1 delivers an A10-style sizing report (per-owner deferred-row count after the `RUST_TARGET_CRATES` expansion) so downstream plans size their task budgets before starting.

**Tooling expansion + camelCase guard:**

- **D-TOOL-01** — `RUST_TARGET_CRATES` expands from 10 to 18 entries matching Phase 3's set, explicitly excluding `classic-crashgen-settings-core`. Plan 1 verifies each candidate has a corresponding `classic-node/src/<crate>.rs` before adding. _(Research note: this exclusion is questionable — see Open Question 1.)_
- **D-TOOL-02** — `RUST_FULL_INVENTORY_CRATES` and `include_rust_symbol()` are deleted entirely. Every tracked crate produces full public-symbol output. `tier='tier2'` label assignments at lines 190/210/230/250 stay temporarily — Phase 6 sweeps them.
- **D-TOOL-03** — `check_parity_gate.py` gains a bidirectional `validate_contract_surface()` helper asserting both `rustSymbol ∈ rust_api_surface` AND `nodeExport ∈ node_api_surface`. Single function, single walk, two-direction error messages. Modeled on Phase 3 D-05 but extended for Node's bidirectional case.
- **D-TOOL-04** — The `validate_contract_surface()` guard runs **unconditionally** on every invocation including CI. No `--strict` flag. Diagnostic output names the missing side explicitly.

**`index.d.ts` regeneration + smoke test discipline:**

- **D-DTS-01** — `index.d.ts` regeneration is **atomic with Rust source change**. Each wave plan commit includes: `src/<module>.rs` edits + regenerated `index.d.ts` + contract row(s) + runtime coverage registry row(s) + smoke test(s) + baseline artifacts refresh.
- **D-DTS-02** — Plan 1 runs `bun run build` end-to-end as a smoke test to verify `napi build --release --platform --manifest-path ./Cargo.toml` + `tsc -p tsconfig.json` + `bun run dts:freshness:check` succeed before any promotion plan depends on the build chain.
- **D-TEST-01** — Smoke tests for promoted entries append to existing `__test__/<module>.spec.ts` files as new `describe` blocks. No new sibling test files.
- **D-TEST-02** — `bun:test` for every promoted entry + one representative entry per promoted module added to `__test__/runtime.node.test.mjs` (`node:test`).

**Error shape, review, execution, hash:**

- **D-ERR-01** — Preserve existing `to_napi_err()` message-only pattern for all promoted error types. No `.code` field on promoted errors. PE-version errors follow the same rule.
- **D-REVIEW-01** — Cross-AI review (`/gsd:review --phase 4 --claude --codex`) is pre-scheduled for two specific plans before `/gsd:execute-phase`: Plan 1 (tooling expansion + camelCase guard) and final cleanup plan (M7 atomic cascade). Other plans use the per-plan feedback rule.
- **D-EXEC-01** — Phase 4 plans execute **sequentially on main** — no worktrees. Every plan touches `parity_contract.json` and `index.d.ts`. Drop `<parallel_execution>` blocks and `--no-verify` flags.
- **D-HASH-01** — All `runtime_coverage_registry.json` selectors use full 64-char SHA-256 via `tools/binding_parity_runtime_coverage.py::_stable_id_hash` — mandatory import, no truncation, no inline reimplementation.

### Claude's Discretion

- Owner module reassignment for newly-tracked crates (collapse to `aux` or split into distinct owners).
- Atomic commit granularity within a wave plan (per sub-module / per ~10 rows / per owner module).
- Per-class smoke test grouping inside `describe` blocks.
- `runtime.node.test.mjs` representative entry selection (criterion: exercises a real method, not a no-op import).
- A10 sizing report format (markdown / JSON / both).
- `generate_baseline.py::SQUAD_BY_OWNER` expansion mechanics.
- Whether the final cleanup plan also strips dead code from `generate_wave_manifest.py` and `generate_deferred_backlog.py` or leaves entirely for Phase 6.

### Deferred Ideas (OUT OF SCOPE)

- Tier-2 governance file deletion (Phase 6 DOC-02/03/04).
- `--deferred-registry` argument optional/missing-tolerant behavior (Phase 6 DOC-01).
- Rewriting `docs/api/binding-parity-overview.md` (Phase 6 DOC-05).
- Per-binding error-contract documentation (Phase 6 HARM-05).
- Standardizing error conventions across bindings (explicit anti-feature).
- Adding `.code` field to any Node error types (rejected via D-ERR-01).
- Adding new Cargo workspace dependencies — `pelite` stays confined to `classic-version-core`; no direct `pelite` dep in `classic-node`.
- `classic-shared-core` exposure as a standalone Node binding (HARM-03/04 was Python-only).
- Auto-generating Node binding code from a schema.
- Splitting scanlog promotions across multiple plans.
- Worktree-based parallel execution.
- Per-plan cross-AI review for every plan.
- Stringified PE version return.
- CI workflow file edits for Node parity gate (Phase 5 owns).
- Promoting more entries than the deferred backlog contains _unless_ Plan 1's A10 sizing surfaces residuals from newly-tracked crates.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| NODE-01 | `tools/node_api_parity/generate_baseline.py` `RUST_TARGET_CRATES` and `RUST_FULL_INVENTORY_CRATES` expanded to cover every business-logic crate that has a Node binding module | Plan 1; see `## Standard Stack` and `## Architecture Patterns` |
| NODE-02 | All 109 currently-deferred entries promoted; every `nodeExport` uses the camelCase identifier produced by NAPI auto-conversion | Plans 2–5; see `## Deferred Entry Inventory` and `## Don't Hand-Roll` |
| NODE-03 | `check_parity_gate.py` Tier-2 skip logic removed; script enforces every contract row as Tier-1 | Final cleanup plan; the "Tier-2 skip" logic actually lives in `generate_baseline.py` (gap_type branches), not `check_parity_gate.py` |
| NODE-04 | `index.d.ts` regenerated, committed, freshness gate passes against the expanded contract | Atomic `index.d.ts` commits per D-DTS-01; existing `check_dts_freshness.py` uses `bun run build:debug` + `git diff` |
| NODE-05 | `bun run test:bun && bun run test:node` pass with smoke tests for at least one method per promoted module | D-TEST-01/02; see `## Validation Architecture` |
| NODE-06 | `bun run parity:gate:local` exits zero; deferred-entry count drops to 0 in `runtime_coverage_summary.md` | Final cleanup plan; see `## Deferred Entry Inventory` — the load-bearing 109 number comes from `tracked_surface` classifications that flow from `deferred_runtime_backlog.json` |
| HARM-01 | `classic-node/src/version.rs` exposes `extractPeVersion(path)` and `isValidPePath(path)` delegating to `classic_version_core::pe_version::{extract_pe_version, is_valid_executable_path}` | Plan 4; see `## Code Examples` |
| HARM-02 | `extractPeVersion` returns a typed object `{ major, minor, patch, build }`; return shape is in `index.d.ts` and runtime-tested for parity against Python/Rust PE-version API | Plan 4; see `## Code Examples` |

</phase_requirements>

## Project Constraints (from CLAUDE.md and AGENTS.md)

- **Business logic stays in Rust `-core` crates.** Node bindings in `classic-node/` are thin NAPI-RS wrappers that delegate to `classic_<crate>_core::*` directly. No business logic in the binding layer.
- **Single shared Tokio runtime** — `classic_shared_core::get_runtime()` is the only runtime. PE-version extraction is synchronous and does not touch the runtime.
- **All binding changes must pass existing parity gates** — `bun run parity:gate:local` for Node.
- **NAPI conventions** — `#[napi]` / `#[napi(object)]` attributes; `Js` prefix for NAPI wrapper types; `snake_case` Rust → auto-converted to `camelCase` on JS side; all exports flow through `index.js` / `index.d.ts`.
- **Never write to `nul` / `NUL` on Windows** — creates an undeletable file on system drives. Use `/dev/null` in Git Bash or explicit file paths.
- **Git Bash MSVC linker shadowing** — source `tools/use_msvc_from_git_bash.sh` before Rust or MSVC C++ commands so Git's `link.exe` does not shadow the Visual Studio linker.
- **Never run C++ tests via raw `ctest`** — not relevant to Phase 4 (Node-only), but part of the always-on rules.
- **Prefer PowerShell over Bash** (user's global CLAUDE.md) — all terminal operations in plan tasks should use PowerShell where feasible; the existing `classic-node/package.json` scripts run via `bun` / `python` which work in either shell.
- **Commit prefixes** — `Feat:`, `Fix:`, `Docs:`, `Refactor:`, `Chore:`, `Update:` — first word capitalized. Phase 4 commits use these prefixes.
- **Test API verification first** — verify APIs of what is going to be tested before writing tests (user memory rule `feedback_verify_apis_first`). Phase 4 must read each `-core` symbol's real signature before authoring smoke tests.

## Summary

Phase 4 mirrors Phase 3's Python Tier Collapse for Node, but on a much smaller surface (109 deferred vs 289 Python, 261 current tier-1 vs ~300 Python pre-Phase-3). The structural pattern is identical: expand target crates → bidirectional contract↔surface guard → wave promotions → atomic M7 cleanup. The two biggest Phase 4-specific complications are (1) **`index.d.ts` must be regenerated and committed atomically with every Rust source change** — unlike Phase 3's hand-edited `.pyi` stubs — and (2) **roughly 58 of 67 scanlog "deferred" symbols are Rust-only with no Node binding** and must be promoted via `@rust`-suffix proxy rows using the Phase 3 Plan 02 precedent.

The PE-version extraction is a small, well-scoped addition: the Rust API already exists in `classic_version_core::pe_version::{extract_pe_version, is_valid_executable_path}`, is already bound to Python as `classic_version.{extract_pe_version, is_valid_pe_path}`, and just needs two new `#[napi]` functions in `classic-node/src/version.rs` plus a new `#[napi(object)] JsPeVersion` return type. No new Cargo dependencies; `classic-node` already depends on `classic-version-core`.

**Primary recommendation:** Front-load Plan 1's A10 sizing pass and `bun run build` smoke test. Phase 3 Plan 09a's 593-row residual surprise was caused by skipping the sizing pass; Phase 4's scanlog also has a 58-symbol "Rust-only" backlog that is invisible until the target crates are expanded. Catch it in Plan 1, not Plan 6.

## Standard Stack

### Core (all versions verified against `Cargo.toml` / `package.json` / lockfiles on 2026-04-08)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `napi` (Rust) | 3.x (`"3", features=["async","napi9","serde-json"]`) | NAPI-RS binding core | Already pinned in `classic-node/Cargo.toml` line 15. Phase 4 MUST NOT bump this. |
| `napi-derive` (Rust) | 3.x | `#[napi]` / `#[napi(object)]` proc-macros; auto-converts snake_case → camelCase | Already pinned at line 16. |
| `napi-build` (Rust) | 2.x | `build.rs` entry point for napi-rs code generation | Already pinned at line 63. |
| `@napi-rs/cli` (Node) | ^3.0.0 | `napi build --release --platform` — produces the native `.node` file and `index.d.ts` | Already pinned in `package.json` devDependencies. Phase 4 MUST NOT bump. |
| `typescript` (Node) | ^5.8.2 | `tsc -p tsconfig.json` produces `dist/cli/*.js` from the TS wrapper | Already pinned. `tsconfig.json` uses `strict: true`, `target: ES2022`, `module: CommonJS`. |
| `bun-types` (Node) | latest | Type definitions for `bun:test` | Already pinned. Phase 4 tests use `import { describe, test, expect } from "bun:test"`. |
| `classic-version-core` (Rust) | path dep | Source-of-truth for PE version extraction | Already in `classic-node/Cargo.toml` line 37 as `path = "../../business-logic/classic-version-core"`. |
| `pelite` (Rust) | workspace dep of `classic-version-core` | PE file parsing for `VS_VERSIONINFO` extraction | Stays confined to `classic-version-core` per HARM-01 requirement text. Node reaches it transitively through the delegated function call. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `thiserror` (Rust) | in core crates | `PeVersionError` enum lives in `classic_version_core::pe_version` | Already present in `classic-version-core`; Phase 4 consumes it via `err.to_string()` in `to_napi_err()`. |
| `python` | any | Runs `tools/node_api_parity/*.py` parity tooling | Phase 4 tooling is pure Python, no extra deps beyond what Phase 3 already required. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Append PE-version to existing `version.rs` (D-PE-04) | New `src/pe_version.rs` sibling module | Explicitly rejected by D-PE-04; appending keeps the binding-to-core mapping 1:1 and avoids adding a new `mod` entry in `lib.rs`. |
| Object return `{ major, minor, patch, build }` (D-PE-01) | Tuple `[major, minor, patch, build]` (Python parity) or stringified `"M.m.p.b"` (C++ parity) | Rejected by D-PE-01. Object form is HARM-02's preferred shape and idiomatic for TS/NAPI; future-proof if Rust adds a 5th component. |
| `to_napi_err()` message-only errors (D-ERR-01) | Throw with `.code` field populated | Rejected by D-ERR-01. Every current `classic-node/src/*.rs` uses the message-only helper; adding `.code` to promoted entries alone would split the Node convention. |
| Include `classic-crashgen-settings-core` in `RUST_TARGET_CRATES` (research recommendation) | Exclude it, matching Phase 3 D-PLAN-01 wording | See Open Question 1. Python excludes it because its symbols flow through wrappers; Node has a direct `crashgen_rules.rs` binding that IS `classic-crashgen-settings-core`'s Node surface. |

**Installation:** No new packages to install. All dependencies already present.

**Version verification:** Verified on 2026-04-08 from live `Cargo.toml`, `package.json`, and `Cargo.lock` contents. `napi=3.x`, `napi-derive=3.x`, `napi-build=2.x`, `@napi-rs/cli=^3.0.0`, `typescript=^5.8.2`. **Phase 4 MUST NOT change any dependency versions** — the milestone is parity/harmonization, not dep maintenance.

## Architecture Patterns

### Recommended Project Structure

Phase 4 touches an existing structure; it does not create new files outside of:

- `.planning/phases/04-node-tier-collapse/04-XX-<name>-PLAN.md` — plan files (per-plan)
- `.planning/phases/04-node-tier-collapse/04-XX-<name>-SUMMARY.md` — per-plan summaries
- `.planning/phases/04-node-tier-collapse/04-01-A10-sizing.{json,md}` — Plan 1 sizing artifact
- `.planning/phases/04-node-tier-collapse/04-01-CONSTRUCTOR-INVENTORY.md` — Plan 1 / per-promotion plan inventory (Phase 3 precedent)
- `.planning/phases/04-node-tier-collapse/04-06-TIER2-CASCADE-AUDIT.md` — final cleanup plan pre-deletion audit (Phase 3 Plan 09b precedent)

Existing file layout the phase modifies:

```
tools/node_api_parity/
├── generate_baseline.py              # Plan 1: expand RUST_TARGET_CRATES 10→18, delete RUST_FULL_INVENTORY_CRATES; Plan 6: delete gap_type=rust_unmapped / node_unmapped branches (L456-491), delete tier2_gap_total (L511), delete Tier 2 Gaps markdown column (L558), delete handoff_map tier column (L623)
├── check_parity_gate.py              # Plan 1: add validate_contract_surface() bidirectional guard (Phase 3 pattern at L31-76)
├── check_dts_freshness.py            # read-only; runs bun run build:debug + git diff on index.d.ts
├── generate_deferred_backlog.py      # read-only (Phase 6 owns deletion)
└── generate_wave_manifest.py         # read-only (Phase 6 owns deletion)

ClassicLib-rs/node-bindings/classic-node/
├── Cargo.toml                        # no changes (no new deps)
├── package.json                      # no changes (scripts already defined)
├── src/
│   ├── lib.rs                        # no changes (all 20 modules already declared)
│   ├── version.rs                    # Plan 4: append extract_pe_version + is_valid_pe_path NAPI functions + JsPeVersion struct (HARM-01/02)
│   ├── scanlog.rs                    # Plan 2: add #[napi] exports for 9 Node-side deferred, proxy 58 Rust-only
│   ├── config.rs                     # Plan 3: add #[napi] exports for 23 Node-side deferred, proxy 12 Rust-only
│   ├── version_registry.rs           # Plan 4: add #[napi] exports for 4 deferred
│   ├── crashgen_rules.rs             # Plan 5: aux promotion (the JsCheckRule, JsPreflightAction, etc., items)
│   ├── {other 15 modules}            # Plan 5: residual aux promotions per A10 sizing
│   └── logging_contract.rs           # INTERNAL module, non-public NAPI; NO phase 4 changes
├── index.d.ts                        # auto-regenerated per wave commit via napi build --release
├── __test__/
│   ├── fixtures/runtime_coverage_registry.json   # per-plan: add/update entries per promoted contract rows
│   ├── fixtures/runtime_coverage_registry.ts     # read-only (helper function)
│   ├── parity_tier1.spec.ts                      # auto-grows as contract rows land (imports list expands)
│   ├── <module>.spec.ts (20 files)               # per-plan: append new describe blocks per D-TEST-01
│   └── runtime.node.test.mjs                     # per-plan: append one representative test per promoted module per D-TEST-02
└── parity-artifacts/                             # ephemeral; refreshed by parity:gate:local

docs/implementation/node_api_parity/
├── baseline/
│   ├── parity_contract.json          # per-plan: add contract rows; final plan deletes tierDefinitions.tier2
│   ├── parity_contract.md            # per-plan auto-refresh
│   ├── parity_diff_report.{json,md}  # per-plan refresh via --update-baseline
│   ├── rust_api_surface.json         # per-plan refresh
│   ├── node_api_surface.json         # per-plan refresh
│   ├── runtime_coverage_summary.{json,md}  # per-plan refresh; deferred_total is the load-bearing NODE-06 metric
│   └── tier1_gate_report.md          # per-plan refresh
└── governance/
    ├── deferred_runtime_backlog.json # Plan 6 empties entries to [] (file shape preserved for Phase 6 deletion)
    ├── tier2_backlog_and_governance.md     # read-only until Phase 6 deletion
    ├── tier2_wave_manifest.json            # read-only until Phase 6 deletion
    ├── gate_contract_baseline.md           # read-only until Phase 6 deletion
    └── per_wave_acceptance_template.md     # read-only until Phase 6 deletion
```

### Pattern 1: `#[napi]` free function with delegation to `-core`

**What:** Every Node binding function carries the `#[napi]` attribute and delegates entirely to `classic_<crate>_core::*`. No business logic in `classic-node/src/`.

**When to use:** Every new promoted free function and every new HARM-01/02 PE-version function.

**Example:**

```rust
// Source: J:/CLASSIC-Fallout4/ClassicLib-rs/node-bindings/classic-node/src/version.rs (existing)
use napi::bindgen_prelude::*;

fn to_napi_err(err: impl std::fmt::Display) -> napi::Error {
    napi::Error::from_reason(format!("{err}"))
}

/// Parse and normalize a version string.
/// @throws if the input is not a valid version string.
#[napi]
pub fn parse_version(input: String) -> Result<String> {
    let version = classic_version_core::parse_version(&input).map_err(to_napi_err)?;
    Ok(version.to_string())
}
```

Rust identifier `parse_version` → NAPI auto-converts to TypeScript export `parseVersion`.

### Pattern 2: `#[napi(object)]` shared DTO

**What:** A plain Rust struct with `#[napi(object)]` produces a TypeScript `interface` in `index.d.ts`. Field names auto-convert snake_case → camelCase on the JS side.

**When to use:** The new `JsPeVersion` return type for HARM-02.

**Example:**

```rust
// Source: J:/CLASSIC-Fallout4/ClassicLib-rs/node-bindings/classic-node/src/scanlog.rs:170-189 (existing)
#[napi(object)]
pub struct JsAnalysisConfig {
    pub game: String,
    pub game_version: String,
    pub crashgen_name: String,
    pub xse_acronym: String,
    // ...
}
```

Rust `game_version: String` → TypeScript `gameVersion: string`.

### Pattern 3: Bidirectional contract↔surface guard (D-TOOL-03, modeled on Phase 3 D-05)

**What:** `check_parity_gate.py` calls `validate_contract_surface(contract, rust_manifest, node_manifest)` before generating the diff report. For every `tier1Mappings` row, it asserts both sides: `rustSymbol ∈ rust_surface` AND `nodeExport ∈ node_surface`. Failing rows print an actionable remediation message.

**When to use:** Plan 1 adds this guard. Runs unconditionally on every `check_parity_gate.py` invocation (including CI).

**Example** (adapted from Python's Phase 3 D-05 at `tools/python_api_parity/check_parity_gate.py:31-76`):

```python
# Target shape for tools/node_api_parity/check_parity_gate.py
def validate_contract_surface(
    contract: dict[str, Any],
    rust_manifest: dict[str, Any],
    node_manifest: dict[str, Any],
) -> list[str]:
    """Bidirectional guard: every tier1 row's rustSymbol must be in rust surface
    AND every tier1 row's nodeExport must be in node surface (index.d.ts).
    """
    rust_symbols: set[str] = {item["symbol"] for item in rust_manifest.get("symbols", [])}
    node_exports: set[str] = {item["export"] for item in node_manifest.get("exports", [])}
    diagnostics: list[str] = []
    for mapping in contract.get("tier1Mappings", []):
        row_id = mapping.get("id", "<unknown>")
        rust_symbol = mapping.get("rustSymbol")
        node_export = mapping.get("nodeExport")

        if not rust_symbol:
            diagnostics.append(f"Row '{row_id}' is missing 'rustSymbol'.")
        elif rust_symbol not in rust_symbols:
            diagnostics.append(
                f"Row '{row_id}' rustSymbol '{rust_symbol}' not in rust surface. "
                f"Add 'pub use <sub_module>::{rust_symbol};' to the owning crate's lib.rs."
            )

        if not node_export:
            diagnostics.append(f"Row '{row_id}' is missing 'nodeExport'.")
        elif node_export not in node_exports:
            diagnostics.append(
                f"Row '{row_id}' nodeExport '{node_export}' not in node surface (index.d.ts). "
                f"Either the Rust function still uses snake_case (NAPI auto-converts to camelCase), "
                f"or '{node_export}' is a typo. Run `bun run build` to refresh index.d.ts and check "
                f"whether the export was actually generated."
            )
    return diagnostics
```

### Pattern 4: `@rust`-suffix proxy rows for Rust-only deferred symbols

**What:** When a Rust symbol exists but has no Node binding (no entry in `index.d.ts`), Phase 3 Python Wave 1 used a contract row with ID ending in `@rust`, a `rustSymbol` field populated, and a `nodeExport` field pointing at the **nearest existing Node anchor** for the same sub-module. This keeps the row's presence "countable" (the rust_unmapped gap branch no longer fires) without requiring new `#[napi]` wrappers.

**When to use:** Phase 4 Plan 2 (scanlog) for the 58 Rust-only deferred scanlog symbols that have NO matching Node binding in `index.d.ts`. Also Plan 3 (config) for the 12 Rust-only deferred config symbols.

**Example** (Python precedent, from `parity_contract.json`):

```json
{
  "id": "config.config.config@rust",
  "tier": "tier1",
  "ownerModule": "config",
  "rustCrate": "classic-config-core",
  "rustSymbol": "config",
  "pythonModule": "classic_config",
  "pythonExportPath": "ClassicConfig",
  "pythonKind": "class"
}
```

Node equivalent shape (proposal for Phase 4):

```json
{
  "id": "scanlog.formid.FormIDAnalyzer@rust",
  "tier": "tier1",
  "ownerModule": "scanlog",
  "rustCrate": "classic-scanlog-core",
  "rustSymbol": "FormIDAnalyzer",
  "nodeExport": "<nearest existing scanlog anchor, e.g. 'parseLogSegments' or 'JsAnalysisConfig'>",
  "nodeKind": "<matching kind from index.d.ts>"
}
```

**CRITICAL:** Node's current contract rows do NOT carry a `rustCrate` field (verified at `docs/implementation/node_api_parity/baseline/parity_contract.json`, 261 rows, all missing `rustCrate`). Phase 4 Plan 1 must decide whether to add `rustCrate` to new rows only (backward-compatible but inconsistent) or retrofit existing rows (cleaner but more churn). **Recommendation:** Add `rustCrate` to new rows and leave existing rows alone — consistent with Phase 3's "A10 amendment" style, where the research discovers mechanics mid-phase.

### Pattern 5: Per-plan baseline artifact refresh (Phase 2 D-09 / Phase 3 D-03)

**What:** Each plan's final commit runs `bun run parity:gate:local` (which is `dts:freshness:local && parity:gate:update-baseline`) to refresh all baseline artifacts and commits them alongside the Rust source changes. This keeps every commit individually green.

**Commands:**

```bash
# From ClassicLib-rs/node-bindings/classic-node/
bun run build                       # napi build + tsc — regenerates index.d.ts + dist/
bun run parity:gate:local          # dts:freshness:local + parity:gate:update-baseline
bun run test:bun && bun run test:node  # per-module smoke verification
```

### Anti-Patterns to Avoid

- **Hand-edit `index.d.ts`.** `index.d.ts` is auto-generated by `napi build`. Any manual edit will be overwritten and will fail the freshness gate. Plan tasks MUST regenerate, not edit.
- **Inline reimplementation of `_stable_id_hash`.** Phase 3 R8 hit this with a `sha256[:16]` truncation bug. D-HASH-01 mandates `from binding_parity_runtime_coverage import _stable_id_hash`.
- **Adding `pelite` as a direct `classic-node` dep.** Explicitly rejected by HARM-01 requirement text. `pelite` stays confined to `classic-version-core`.
- **Writing contract rows with snake_case `nodeExport`.** NAPI auto-converts to camelCase. Rust `extract_pe_version` → TypeScript `extractPeVersion`. A contract row with `"nodeExport": "extract_pe_version"` will FAIL the bidirectional guard.
- **Skipping `RUST_TARGET_CRATES` per-crate verification.** Plan 1 must run `parse_rust_surface()` against each new crate entry and confirm non-empty symbol lists. An empty list signals a path typo or an empty `lib.rs`.
- **Running multiple plans in parallel worktrees.** Rejected by D-EXEC-01. Every plan touches `parity_contract.json`, `index.d.ts`, and the baseline artifacts — these are merge-conflict magnets.
- **Creating intermediate states where `tierDefinitions.tier2` is deleted but `gap_type=rust_unmapped` branches still fire.** Non-atomic final cleanup = bisect-broken gate. Phase 3 Plan 09b's M7 atomic commit is the precedent.
- **Writing to `nul` / `NUL` on Windows.** Creates an undeletable file on system drives. Use `/dev/null` in Git Bash or real paths.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Selector hash for runtime coverage registry | `hashlib.sha256(...)[:16]` or `hash(...)` | `from binding_parity_runtime_coverage import _stable_id_hash` (mandatory per D-HASH-01) | Phase 3 R8 regressed on sha256[:16] truncation; the helper returns the full 64-char hex so `registry_mismatch_total` stays 0. |
| Rust surface parsing | Custom regex / ast parser | `tools/node_api_parity/generate_baseline.py::parse_rust_surface` (lines 169-262) | Already handles `pub mod`, `pub fn`, `pub struct/enum/type/trait/const/static`, and the full `pub use` expansion (including grouped `pub use foo::{a, b as c};`). |
| Node surface parsing | Custom TypeScript parser | `parse_node_surface` (lines 284-360) | Already parses `export declare class/function/const enum/interface`, `export type`, `export const` via regex. |
| `pub use` expansion | Custom string-splitting | `expand_pub_use_statement` (lines 122-166) | Already handles grouped `pub use foo::{a, b, c}`, nested `pub use foo::{bar as baz}`, and prefix-less cases. |
| Parity gate cycle (gen + diff + coverage + stale-check) | Call subprocesses manually | `check_parity_gate.py::main()` (lines 113-282) | Already wires up rust_manifest → node_manifest → diff_report → coverage_summary → baseline sync in one pass. Just add `validate_contract_surface()` at the same position as Python's Pitfall 2 guard (between `parse_node_surface` and `generate_diff_report`). |
| PE version extraction | pelite boilerplate in `classic-node` | `classic_version_core::pe_version::{extract_pe_version, is_valid_executable_path}` | Already does: path validation, `std::fs::read`, `pelite::PeFile::from_bytes`, `resources().version_info().fixed()`, returns `(u16, u16, u16, u16)`. Handles both PE32 and PE64 automatically via `pelite::PeFile` wrap type. |
| NAPI error conversion | Custom error match | Module-local `to_napi_err()` helper (already in every `classic-node/src/*.rs`) | Every module has `fn to_napi_err(err: impl std::fmt::Display) -> napi::Error { napi::Error::from_reason(format!("{err}")) }`. Consistent with D-ERR-01. |
| Runtime coverage summary / markdown | Custom template | `build_coverage_summary` + `render_coverage_summary_markdown` in `tools/binding_parity_runtime_coverage.py` (lines 221-371) | Already emits the load-bearing `deferred_total`, `registry_mismatch_total`, `tier1_missing_runtime_total` metrics. |
| Atomic cleanup commits | Multiple commits | Single M7 atomic commit (Phase 3 Plan 09b precedent at `.planning/phases/03-python-tier-collapse/03-09b-tier2-cleanup-and-final-sweep-PLAN.md`) | Intermediate states break the gate. The M7 pattern groups generate_baseline.py edits + test updates + parity_contract.json edits + deferred_runtime_backlog.json empty + baseline refresh into one commit. |

**Key insight:** Phase 4 is a **tooling and promotion exercise**, not a library/framework build. There is effectively nothing to "build custom" — every mechanic already exists in Phase 3's Python tooling or Phase 4's existing Node tooling. The work is reading it, modifying it in the same shape, and extending it for Node's index.d.ts bidirectional guard.

## Runtime State Inventory

Phase 4 is a code/config-only phase: tooling edits, parity artifact refreshes, Rust source additions in `src/version.rs` + 19 other binding modules, TypeScript `index.d.ts` regeneration (from Rust, auto-generated), JSON baseline refreshes. There is NO stored data migration, no live service config, no OS-registered state, no secrets rename, and no package rename/refactor. The Runtime State Inventory categories are therefore all "None":

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | **None** — Phase 4 touches no databases, datastores, or persistent caches. Parity artifacts (parity_contract.json, runtime_coverage_summary.json) are not "data" in this sense — they are generated from source by tooling and committed. | None |
| Live service config | **None** — No CI/CD workflow edits (Phase 5 owns CI). No external service configuration (no n8n, Datadog, Tailscale, etc. in Phase 4 scope). | None |
| OS-registered state | **None** — No Windows Task Scheduler tasks, pm2 processes, launchd plists, or systemd units. The Node binding ships as a `.node` native file and is called via `require('../index.js')` at test time; no OS registration. | None |
| Secrets / env vars | **None** — Phase 4 does not add, rename, or read any secret/env var. `classic-node` tests don't consume any env vars during promotion. | None |
| Build artifacts / installed packages | **Transient only** — `napi build --release` produces `classic-node.win32-x64-msvc.node` and regenerates `index.d.ts`. These are committed (`.node` is gitignored, but `index.d.ts` is committed as the source-of-truth contract). `dist/cli/*.js` is regenerated by `bun run build:cli`. No globally-installed packages, no egg-info directories, no stale pip/npm global state. The only "gotcha" is that an out-of-date local `classic-node.win32-x64-msvc.node` file from a prior build can confuse `require('../index.js')` if `bun run build` has not been re-run after a Rust source change — Plan 1's D-DTS-02 smoke test catches this. | Run `bun run build` in Plan 1 to establish a clean executor-side build state. |

**Verification:** Cross-checked by inspecting `.gitignore`, `ClassicLib-rs/node-bindings/classic-node/Cargo.toml`, `package.json`, and the 04-CONTEXT.md scope block. Phase 4 has zero runtime state to migrate.

## Environment Availability

Phase 4 depends on the following local toolchain. All are expected to be present in the CLASSIC dev environment; Plan 1's `bun run build` smoke test (D-DTS-02) is the single gate that verifies availability before promotion plans start.

| Dependency | Required By | Typical Command | Notes / Fallback |
|------------|------------|-----------------|------------------|
| Rust stable (≥1.85.0 MSRV) | `napi build --release` (Rust side) | `rustc --version` | Required. No fallback — Phase 4 cannot proceed without it. |
| `cargo` + workspace lockfile | Rust compilation | `cargo --version` | Part of stable Rust. |
| MSVC toolchain (VS 2022) | Native `.node` linking | `cl.exe --help` inside a VS developer shell | Required on Windows. If Git Bash is used, source `tools/use_msvc_from_git_bash.sh` first. Plan 1's smoke test catches shadowing failures. |
| `VCPKG_ROOT` env var | C++ deps transitively required by napi-rs native link step | `echo $VCPKG_ROOT` or `$env:VCPKG_ROOT` | Required for C++ builds; Phase 4 doesn't build C++ but the Node build may touch vcpkg-installed libs. |
| `bun` (latest) | `bun run build`, `bun run test:bun`, `bun run parity:gate:local` | `bun --version` | Required. Node bindings test runner is Bun. |
| Node 22+ (for `node:test`) | `bun run test:node` (via `node --test`) | `node --version` | Required. Cross-runtime verification uses node:test. |
| `python` (3.10+) | `tools/node_api_parity/*.py` scripts | `python --version` | Required. Gate scripts are Python. |
| `@napi-rs/cli` (^3.0.0) | `napi build --release --platform` | already in `package.json` devDependencies | Installed via `bun install`. |
| `typescript` (^5.8.2) | `bun run build:cli` | already in devDependencies | Installed via `bun install`. |
| `git` | `check_dts_freshness.py` runs `git diff -- index.d.ts` | `git --version` | Required — the freshness gate is literally "does `git diff` report any change?" |

**Missing dependencies with no fallback:** None — all items above are already required by other active work in the repo (Phase 3 Python Collapse shipped with this same toolchain).

**Missing dependencies with fallback:** None.

**Plan 1 verification sequence:**

```powershell
# From ClassicLib-rs/node-bindings/classic-node/
bun install                               # refresh node_modules if needed
bun run build                             # napi build + tsc — full smoke test
bun run parity:gate:local                 # dts:freshness:local + parity:gate:update-baseline
bun run test:bun && bun run test:node     # both runtimes run clean
python ../../../tools/node_api_parity/check_parity_gate.py --repo-root ../../.. --update-baseline
```

If ANY of the above fails in Plan 1, the failure becomes a Plan 1 fix — not a downstream blocker.

## Deferred Entry Inventory

The authoritative count for NODE-06 is **109**, as reported by `docs/implementation/node_api_parity/baseline/runtime_coverage_summary.md::deferred`. This number does NOT match the 101 entries in `deferred_runtime_backlog.json` because the coverage helper expands each registry entry's `bindingIdentifiers` + `rustSymbols` list into individual tracked-surface items:

**101 registry entries → sum of identifiers+symbols = 109 tracked "deferred" items.**

Breakdown by owner (verified by live JSON inspection on 2026-04-08):

| Owner | Deferred registry entries | Rust symbols (need `pub use` or `@rust` proxy) | Node bindingIdentifiers (exports needing contract rows) | Total tracked |
|-------|--------------------------:|-----------------------------------------------:|--------------------------------------------------------:|--------------:|
| `scanlog` | 67 | 58 | 9 | 67 |
| `config` | 23 | 12 | 23 | 35 (per diff report) or 26 (per summary) |
| `version_registry` | 4 | 0 | 4 | 4 |
| `aux` | 7 | 0 | 12 | 12 |
| **Total** | **101** | **70** | **48** | **109** (from coverage summary) / **128** (from diff report total gaps) |

**The 109 vs 128 discrepancy** is because the coverage summary dedupes identifiers across tracked-surface rows, while the diff report counts raw gaps. NODE-06's load-bearing metric is the 109 (from `runtime_coverage_summary.json::summary.deferred_total`), and it is driven by the `build_coverage_summary` classifier in `tools/binding_parity_runtime_coverage.py`.

**Research resolution of the 101-vs-109 Pitfall** (from CONTEXT.md Specific Ideas): the authoritative count is **109** per `runtime_coverage_summary.md::deferred`. Empirically, emptying `deferred_runtime_backlog.json::entries` to `[]` AND deleting the `gap_type=rust_unmapped` / `gap_type=node_unmapped` branches in `generate_baseline.py` together drive `deferred_total` to 0 (Phase 3 Plan 09b Scenario E empirical proof). Emptying the backlog alone is NOT sufficient — the gap branches still emit rows that become "newly_uncovered". The final cleanup plan MUST do both in one atomic commit.

### scanlog deferred entries (67 total)

**9 Node-exports needing only contract rows** (verified in `index.d.ts`):

| Coverage ID | Node export | Current kind in index.d.ts |
|-------------|-------------|-----|
| `node-deferred-scanlog-060` | `CRASH_LOG_PATTERN` | const |
| `node-deferred-scanlog-064` | `JsAnalysisBuildOptions` | interface |
| `node-deferred-scanlog-066` | `JsAnalysisResult` | interface |
| `node-deferred-scanlog-075` | `JsGpuInfo` | interface |
| `node-deferred-scanlog-078` | `JsLogErrorEntry` | interface |
| `node-deferred-scanlog-080` | `JsLogSegments` | interface |
| `node-deferred-scanlog-082` | `JsPapyrusStats` | interface |
| `node-deferred-scanlog-092` | `checkXsePlugins` | function |
| `node-deferred-scanlog-100` | `parseXseLog` | function |

**58 Rust-only symbols** requiring `@rust`-suffix proxy rows pairing with the nearest existing scanlog Node anchor:

Classes: `AnalysisResult`, `CheckId`, `ConfigIssue`, `CrashgenEntry`, `CrashgenRegistry`, `FcxModeHandler`, `FcxResetError`, `FormIDAnalyzer`, `FormIDAnalyzerCore`, `GpuDetector`, `GpuVendor`, `PapyrusAnalyzer`, `PapyrusError`, `PluginAnalyzer`, `RecordScanner`, `ReportComposer`, `ReportFragment`, `ReportGenerator`, `RustFormIDAnalyzer`, `ScanLogError`, `SettingsValidator`, `StreamingIteratorParser`, `StreamingLogParser`, `StringPool`, `SuspectScanner`, `ScanProgressPhase`.

Free functions: `contains_plugin`, `contains_record`, `crashgen_version_gen`, `detect_mods_batch`, `detect_mods_double`, `detect_mods_important`, `detect_mods_single`, `detect_plugins_batch`, `extract_formids_batch`, `is_valid_formid`, `scan_records_batch`, `validate_formids_batch`, `resolve_batch_concurrency`.

`pub mod` declarations (module markers): `crashgen_registry`, `error`, `fcx_handler`, `formid`, `formid_analyzer`, `gpu_detector`, `mod_detector`, `orchestrator`, `papyrus`, `parser`, `patterns`, `plugin_analyzer`, `record_scanner`, `report`, `segment_key`, `settings_validator`, `suspect_scanner`, `version`.

Static: `GLOBAL_FCX_HANDLER`.

**Critical Phase 3 precedent** (`[Phase 03-python-tier-collapse]: R9 exclusion: GLOBAL_FCX_HANDLER LazyLock static is not tier1-promotable; Wave 2 lands 57 rows not 58`): `GLOBAL_FCX_HANDLER` was explicitly excluded from Python Wave 2 as non-promotable. Phase 4 Plan 2 must decide whether to replicate this exclusion (expected) or handle it differently.

### config deferred entries (23 total, registry) / 35 (diff report) / 26 (coverage summary per-owner)

**12 Rust-only symbols needing `@rust` proxy rows:**

Classes/enums: `ConfigError`, `CoreModEntry`, `CoreModExclude`, `CrashgenEntryRaw`, `ModConflictEntry`, `ModSolutionCriteria`, `ModSolutionEntry`, `SuspectErrorRule`, `SuspectStackCountRule`, `SuspectStackRule`.

Free functions: `format_registry_game_version`, `resolve_registry_version_info`.

**23 Node-exports needing contract rows** — mix of consts, interfaces, functions, and classes:

Consts: `DEFAULT_CACHE_CLEANUP_INTERVAL`, `DEFAULT_CACHE_CLEANUP_THRESHOLD`, `DEFAULT_QUERY_CACHE_CAPACITY`.

Interfaces: `HashCacheStats`, `JsAnalysisConfig`, `JsConfigIssue`, `JsFcxConfigIssue`, `JsGameScanConfig`, `JsIntegrityConfig`, `JsPathDetectionResult`, `JsTomlConfigIssue`, `JsXseConfig`.

const_enum: `JsEnbConfigResult`.

Class: `JsConfigDuplicateDetector`.

Functions: `clearHashCache`, `detectConfigDuplicates`, `getDefaultCacheCleanupInterval`, `getDefaultCacheCleanupThreshold`, `getDefaultQueryCacheCapacity`, `getFcxConfigIssues`, `getHashCacheStats`, `needsPathDetection`, `resetHashCacheStats`.

### version_registry deferred entries (4 total)

All are existing Node exports in `index.d.ts` needing contract rows:

| bindingIdentifier | Kind in index.d.ts |
|---|---|
| `JsCrashgenRegistryEntry` | interface |
| `JsCrashgenSettingsRules` | interface |
| `checkCrashgenConfigWithRules` | function |
| `checkCrashgenFullWithRules` | function |

Plus 1 extra `migrateGameVersionSetting` (function) classified as version_registry in the diff report but which may overlap with aux — research finds the coverage summary says 4 but the diff report node_unmapped is 5. Plan 4 should reconcile.

### aux deferred entries (7 registry entries → 12 tracked identifiers)

All 7 entries map to `crashgen_rules.rs` exports (verified in `index.d.ts`):

| Coverage ID | bindingIdentifiers |
|---|---|
| `node-deferred-aux-067` | `JsCheckRule` |
| `node-deferred-aux-073` | `JsExpectedValue` |
| `node-deferred-aux-084` | `JsPreflightAction` |
| `node-deferred-aux-085` | `JsPreflightRule` |
| `node-deferred-aux-086` | `JsRuleMessages` |
| `node-deferred-aux-087` | `JsRuleTarget` |
| `node-deferred-aux-108` | `JsModSolutionCriteria`, `JsModSolutionEntry`, `JsSuspectErrorRule`, `JsSuspectStackCountRule`, `JsSuspectStackRule` |

Plus diff report shows 4 aux functions (`getApplicationDir`, `resetFcxGlobalState`, `setApplicationDir`, `writeAutoscanReport`) and `JsModConflictEntry` (interface) as `node_unmapped` — these may be cross-owner overlap with the scanlog/config lists. Plan 5 reconciles.

**All 12 aux "deferred" items are already exported from `crashgen_rules.rs` via `#[napi(object)]` and are present in `index.d.ts`** — no Rust changes needed, contract rows only.

### Post-Plan-1 A10 sizing risk

Phase 3's equivalent Plan 01 sizing report surfaced **1212 total tier-2 gaps across 19 owners** when `RUST_TARGET_CRATES` was expanded from 3 to 19. Phase 4's current gap count is only 128 with `RUST_TARGET_CRATES=10`. **When Plan 1 expands to 18 (or 19), the Node gap count will likely grow significantly** — all pre-existing `-core` symbols that have no Node binding will become `rust_unmapped` gaps.

Plan 1's A10 sizing report (D-PLAN-05) MUST capture this delta before Plan 2 starts. Phase 3 Plan 09a's 593-row residual surprise was caused by deferring this sizing pass. Expected Phase 4 residual count is lower than Phase 3's because Node already has more binding surface per crate, but the actual number is unknown until Plan 1 runs — the A10 report IS the measurement.

## Common Pitfalls

### Pitfall 1: Snake_case `nodeExport` in contract rows

**What goes wrong:** A contract row is authored with `"nodeExport": "extract_pe_version"` (Rust shape). NAPI auto-converts Rust function names to camelCase, so `index.d.ts` actually contains `extractPeVersion`. The bidirectional guard (D-TOOL-03) fires on every gate run, and the row is an instant blocker.

**Why it happens:** Copying the Rust function name into `nodeExport` without remembering the NAPI naming convention. Phase 4 promotes ~109 rows and the habit slippage is high.

**How to avoid:** Plan 1's `validate_contract_surface()` guard detects this on the first failing row with the exact diagnostic. Additionally, plan writers should use a helper script that takes the Rust function name and applies the NAPI snake→camel rule before authoring the row.

**Warning signs:** Gate failure `row '<id>' nodeExport '<snake_case_name>' not in node surface (index.d.ts). Either the Rust function still uses snake_case or '<name>' is a typo.`

### Pitfall 2: Stale `index.d.ts` committed with Rust source

**What goes wrong:** A plan task edits `src/version.rs` to add `extract_pe_version`, commits the Rust change, but forgets to run `bun run build` to regenerate `index.d.ts`. The commit lands, `bun run dts:freshness:check` fails (`git diff` shows pending changes), and the bisect surface is dirty.

**Why it happens:** Phase 3 plans never touched `.pyi` regeneration (`.pyi` stubs are hand-edited). Phase 4 plans MUST regenerate `index.d.ts` after every Rust source change. The habit is new.

**How to avoid:** D-DTS-01 mandates atomic commits: Rust source + regenerated `index.d.ts` + contract row(s) + smoke test(s) + baseline refresh in ONE commit. Plan tasks should be scripted as "run `bun run build`, then stage both the Rust file and `index.d.ts` in the same `git add`".

**Warning signs:** `bun run dts:freshness:check` exits 1 with "index.d.ts is stale. Regenerate bindings and commit updated declarations."

### Pitfall 3: MSVC linker shadowing from Git Bash

**What goes wrong:** Running `bun run build` from Git Bash hits `link.exe` from Git's `/usr/bin` instead of the MSVC linker. The NAPI native build fails with cryptic linker errors. Phase 3 documented a similar `rebuild_rust.ps1 -Target python` `NativeCommandError` PowerShell wrapper failure.

**Why it happens:** Git's `usr/bin` is on PATH ahead of the MSVC toolchain.

**How to avoid:** Source `tools/use_msvc_from_git_bash.sh` before running any build command from Git Bash. Plan 1's D-DTS-02 smoke test catches this — if `bun run build` fails in Plan 1, the plan fails and the root cause is investigated before any promotion plan is attempted. Prefer PowerShell for Phase 4 execution (user's global rule).

**Warning signs:** `napi build` fails with `link: extra operand`, `LINK : fatal error LNK1104`, or unresolved symbol errors for MSVC intrinsics.

### Pitfall 4: `_stable_id_hash` truncation regression

**What goes wrong:** A selector-writing helper reimplements the hash inline as `sha256[:16]` or similar, producing a 16-char hash that disagrees with the 64-char hash stored in `runtime_coverage_registry.json`. The gate fails with `registry_mismatch_total > 0`.

**Why it happens:** Phase 3 R8 bug: a developer reimplemented `_stable_id_hash` inline and truncated the digest. The registry selector `contractIdsHash` field now uses full 64-char; any truncation is instant mismatch.

**How to avoid:** D-HASH-01 mandates `from binding_parity_runtime_coverage import _stable_id_hash` in any selector-writing code. Phase 4 cross-AI review on Plan 1 catches inline reimplementations.

**Warning signs:** `check_parity_gate.py` reports `Node runtime coverage registry snapshot mismatch detected for N selector row(s).`

### Pitfall 5: Empty `RUST_TARGET_CRATES` entry causing silent symbol drops

**What goes wrong:** Plan 1 adds a new crate entry to `RUST_TARGET_CRATES` with a typo in the path (e.g., `classic-perf-core → ClassicLib-rs/business-logic/classic_perf_core/src/lib.rs` with underscore instead of hyphen). `parse_rust_surface()` reads the file, gets an empty symbol list, and silently excludes all that crate's public API from the gate. Downstream `tier1_missing_rust` errors are mis-attributed.

**Why it happens:** Path typos in dict literals. Phase 3 caught this via `test_generate_baseline_targets.py` unit test that asserts each `RUST_TARGET_CRATES` entry parses to a non-empty symbol list.

**How to avoid:** Plan 1 adds the equivalent test file `tools/node_api_parity/tests/test_generate_baseline_targets.py` that iterates `RUST_TARGET_CRATES` and asserts non-empty `parse_rust_surface()` output per crate. Run it in Plan 1 before advancing.

**Warning signs:** `tier1_missing_rust > 0` with Rust symbols that DO exist in the `-core/lib.rs`.

### Pitfall 6: `#[napi]` attribute missing on promoted Rust function

**What goes wrong:** A Rust function in `classic-node/src/<module>.rs` is `pub` but lacks the `#[napi]` attribute. The function is not exposed in `index.d.ts`. Promoting a contract row referencing it fails the bidirectional guard because the `nodeExport` (camelCased function name) does not exist in `node_api_surface.json`.

**Why it happens:** Forgetting the attribute when adding new bindings, especially if the Rust function already exists for another caller.

**How to avoid:** Every promoted row's Plan task MUST verify the function has `#[napi]` before committing. Grep for `#[napi]` count in the target file and confirm it increased. Plan 1's bidirectional guard (D-TOOL-03) is the runtime check.

**Warning signs:** Gate diagnostic: `row '<id>' nodeExport '<camelCase>' not in node surface (index.d.ts)`.

### Pitfall 7: Intermediate state breaking bisect during Tier-2 cleanup

**What goes wrong:** The final cleanup plan splits the atomic cascade across multiple commits. Commit 1 deletes `tierDefinitions.tier2` from `parity_contract.json`; commit 2 deletes the `gap_type=rust_unmapped` branches in `generate_baseline.py`. Between those commits, the gate is broken: the generated diff report references a `tier2` tier that no longer exists in the contract.

**Why it happens:** Splitting "logical" cleanup steps into separate commits for clarity. Bisect-clean commits require every intermediate to be gate-green.

**How to avoid:** D-PLAN-04 mandates a single M7-style atomic cascade commit. Phase 3 Plan 09b is the precedent. The commit includes: generate_baseline.py edits + test assertion updates + parity_contract.json edits + deferred_runtime_backlog.json empty + baseline refresh.

**Warning signs:** Any Phase 4 git log entry showing "part 1 of 2" or "step 1 of cleanup" in the cleanup plan.

### Pitfall 8: Missing `pub use` re-export at `-core/lib.rs`

**What goes wrong:** A promoted Rust symbol lives in a sub-module (e.g., `classic_scanlog_core::formid::FormIDAnalyzer`) that is reachable internally but not re-exported at `lib.rs`. The `parse_rust_surface()` regex only reads `lib.rs`, so it cannot see the symbol. The bidirectional guard fires with a missing `rustSymbol` diagnostic.

**Why it happens:** Rust crates commonly keep a rich sub-module structure without flattening everything at the crate root. Phase 3's Pitfall 2 guard caught many of these.

**How to avoid:** The `validate_contract_surface()` guard's diagnostic explicitly suggests adding `pub use <sub_module>::<symbol>;` at the `-core/lib.rs`. Plan task pre-verification: before authoring a contract row, grep the target crate's `lib.rs` for the symbol; if absent, either add the `pub use` in the same commit or use an `@rust`-suffix proxy row.

**Warning signs:** Gate diagnostic: `row '<id>' rustSymbol '<name>' not in rust surface. Add 'pub use <sub_module>::<name>;' to...`.

### Pitfall 9: Cross-runtime test failure (Bun passes, Node fails)

**What goes wrong:** A Tier-1 row's bun:test passes (`bun run test:bun`) but `node --test` fails (`bun run test:node`) because the native .node file has a Bun-specific feature or a race condition that manifests only under Node's scheduler.

**Why it happens:** Bun and Node have different module loader behavior, different `require()` resolution timing, and slightly different native addon lifecycle semantics. NAPI-RS v3 / napi9 is stable on both but edge cases exist.

**How to avoid:** D-TEST-02 adds one representative test per promoted module to `runtime.node.test.mjs`. This catches Bun-vs-Node divergence early. Plan tasks should NOT rely on bun-only features in promoted smoke tests.

**Warning signs:** `bun run test:bun` passes; `bun run test:node` fails with a different error. Investigate first before adding bun-specific code.

### Pitfall 10: pelite PE parse cross-platform behavior

**What goes wrong:** The PE-version extraction uses `pelite::PeFile::from_bytes`, which handles both PE32 and PE64 via the `Wrap` type. A test that assumes kernel32.dll is always present will break on non-Windows CI. Phase 4 is Windows-only in practice but the Rust crate is cross-platform at source level.

**Why it happens:** The Rust `pe_version.rs` test uses `#[cfg(target_os = "windows")]` for the kernel32.dll integration test (line 222). Phase 4 Node smoke tests should do the same.

**How to avoid:** PE-version smoke tests in `__test__/version.spec.ts` use:
1. A temp `.exe` file (fake, for `isValidPePath` true case).
2. A temp `.txt` file (for `isValidPePath` false case).
3. A non-existent path (for `isValidPePath` false case).
4. On Windows only (guarded by `process.platform === "win32"`), a real call against `C:\\Windows\\System32\\kernel32.dll` for `extractPeVersion`.

**Warning signs:** Test passes locally on Windows, fails in Linux CI (if Phase 5 CI ever runs Linux). Phase 4 CI is Windows-only per milestone scope, so this is a defensive guard.

## Code Examples

### Example 1: HARM-01/02 Node `extractPeVersion` implementation

**Source:** Phase 4 Plan 4 will append to `ClassicLib-rs/node-bindings/classic-node/src/version.rs` at the bottom.

```rust
// APPENDED at end of version.rs (after existing format_version function at line 99)

use std::path::Path;

/// PE file version components (4-part file version from VS_VERSIONINFO).
///
/// Returned by `extractPeVersion`. All fields are `u16` in the underlying Rust
/// crate but widened to `u32` to match the established NAPI convention
/// (e.g. `JsGpuInfo`, `JsPoolStats`). JavaScript receives plain numbers.
#[napi(object)]
pub struct JsPeVersion {
    /// Major version number (e.g. 10 for Windows 10's kernel32.dll).
    pub major: u32,
    /// Minor version number.
    pub minor: u32,
    /// Patch / revision number.
    pub patch: u32,
    /// Build number.
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

**NAPI auto-conversion:**
- Rust `extract_pe_version` → TypeScript `extractPeVersion`
- Rust `is_valid_pe_path` → TypeScript `isValidPePath`
- Rust `JsPeVersion { major, minor, patch, build }` → TypeScript `interface JsPeVersion { major: number; minor: number; patch: number; build: number }`

**Expected `index.d.ts` additions after `bun run build`:**

```typescript
/** PE file version components (4-part file version from VS_VERSIONINFO). */
export interface JsPeVersion {
  major: number
  minor: number
  patch: number
  build: number
}

/**
 * Extract a PE file's version from its VS_VERSIONINFO resource.
 * @throws napi::Error on invalid path or parse failure.
 */
export declare function extractPeVersion(path: string): JsPeVersion

/** Check whether a path points to a valid executable or DLL file. Never throws. */
export declare function isValidPePath(path: string): boolean
```

### Example 2: Contract rows for HARM-01/02

**Target:** `docs/implementation/node_api_parity/baseline/parity_contract.json::tier1Mappings` — Plan 4 append.

```json
{
  "id": "version-pe-extract",
  "tier": "tier1",
  "ownerModule": "version_registry",
  "rustSymbol": "extract_pe_version",
  "nodeExport": "extractPeVersion",
  "nodeKind": "function",
  "nodeArity": 1
},
{
  "id": "version-pe-is-valid-path",
  "tier": "tier1",
  "ownerModule": "version_registry",
  "rustSymbol": "is_valid_executable_path",
  "nodeExport": "isValidPePath",
  "nodeKind": "function",
  "nodeArity": 1
},
{
  "id": "version-pe-shape",
  "tier": "tier1",
  "ownerModule": "version_registry",
  "rustSymbol": "PeVersionResult",
  "nodeExport": "JsPeVersion",
  "nodeKind": "interface"
}
```

**Note:** `is_valid_executable_path` must be `pub use`-re-exported from `classic-version-core/src/lib.rs` — the current lib.rs at line 43 only re-exports `{PeVersionError, PeVersionResult, extract_pe_version}`, NOT `is_valid_executable_path`. Plan 4 either (a) adds the re-export OR (b) uses the full path `classic_version_core::pe_version::is_valid_executable_path` in version.rs (which the `parse_rust_surface()` regex won't see at `lib.rs`, so the bidirectional guard fails). **Recommendation (a):** add the `pub use` in the same commit.

### Example 3: PE-version smoke test for `__test__/version.spec.ts`

**Target:** Plan 4 appends new `describe` blocks to existing `version.spec.ts`.

```typescript
// APPENDED to existing version.spec.ts
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

  // Windows-only integration test against a real system DLL
  if (process.platform === "win32") {
    test("extracts version from kernel32.dll", () => {
      const version = extractPeVersion("C:\\Windows\\System32\\kernel32.dll");
      expect(version.major).toBeGreaterThanOrEqual(6);
      expect(typeof version.minor).toBe("number");
      expect(typeof version.patch).toBe("number");
      expect(typeof version.build).toBe("number");
    });
  }
});
```

### Example 4: Runtime coverage registry entry for PE-version

**Target:** `ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json` — Plan 4 appends an entry.

```json
{
  "coverageId": "node-tier1-version-registry-pe",
  "classification": "runtime_verified",
  "ownerModule": "version_registry",
  "tier": "tier1",
  "bindingIdentifiers": [
    "extractPeVersion",
    "isValidPePath",
    "JsPeVersion"
  ],
  "rustSymbols": [
    "extract_pe_version",
    "is_valid_executable_path",
    "PeVersionResult"
  ],
  "verificationMode": "workflow_smoke",
  "testSuite": "ClassicLib-rs/node-bindings/classic-node/__test__/version.spec.ts",
  "testCaseId": "pe-version-smoke"
}
```

Alternatively, bump the existing `node-tier1-version-registry` selector's `contractCount` (55 → 58) and recompute `contractIdsHash` via `_stable_id_hash` after PE rows are added. **Recommendation:** use a separate explicit-bindingIdentifiers entry (cleaner, more discoverable; matches the Python Plan 02 precedent pattern).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Two-tier parity gate (tier1 enforced + tier2 deferred backlog) | One-tier parity gate (tier1 only; no deferral concept) | Phase 3 (Python) shipped 2026-04-08; Phase 4 (Node) targeting 2026-04-09+ | Gate fails immediately on any public API drift. No "promise to fix later" escape hatch. |
| Node RUST_TARGET_CRATES covers 3 crates (scanlog, config, version_registry); rest hidden behind `RUST_FULL_INVENTORY_CRATES` filter | 18 (or 19) business-logic crates fully tracked; `include_rust_symbol()` becomes a tautology | Phase 4 Plan 1 | Every public Rust symbol in a tracked crate enters the gate immediately. Drift detection matches Phase 3 Python coverage. |
| Node gate has no `rustSymbol → rust_surface` or `nodeExport → node_surface` guard — relies on diff report to surface mismatches | Bidirectional `validate_contract_surface()` helper fires unconditionally on every gate run | Phase 4 Plan 1 | Contract authoring errors are caught at commit time, not after running the full diff. Error messages are actionable. |
| `index.d.ts` is an auto-generated artifact treated as "eventually consistent" with Rust source | `index.d.ts` regeneration is atomic with Rust source commit (D-DTS-01) | Phase 4 | Every commit is bisect-clean; no intermediate state where `index.d.ts` is stale. |
| PE-version extraction only exposed via Rust + Python + C++ (C++ returns a string) | Also exposed in Node via `extractPeVersion` returning `{ major, minor, patch, build }` (HARM-01/02) | Phase 4 Plan 4 | Node consumers can detect Fallout 4 game versions without going through the config pipeline. Parity-verified against Python/Rust. |
| Node error convention uncertain — some exports throw, some return null, some have `.code` fields | Documented convention: message-only `napi::Error` via `to_napi_err()` helper; no `.code` fields (HARM-05 will document this in Phase 6) | Phase 4 D-ERR-01 | Consistent within the Node binding. Diverges intentionally from Python typed exceptions and C++ `rust::Error` per the "document, don't standardize" milestone philosophy. |
| Runtime coverage registry selectors use inconsistent hash algorithms (some truncated) | Full 64-char SHA-256 via `_stable_id_hash` mandatory (D-HASH-01) | Phase 4 codifies; Phase 3 fixed per-symbol | Prevents Phase 3 R8 recurrence. |

**Deprecated / outdated:**
- Tier-2 backlog concept (`tierDefinitions.tier2`, `gap_type=rust_unmapped`, `gap_type=node_unmapped`) — deleted in Phase 4 final cleanup plan. Phase 6 deletes the governance files.
- `RUST_FULL_INVENTORY_CRATES` selective filter — deleted in Phase 4 Plan 1.
- `include_rust_symbol()` filter function — deleted (becomes tautology, then removed).

## Open Questions

1. **Should `classic-crashgen-settings-core` be included in `RUST_TARGET_CRATES`?**
   - What we know: CONTEXT D-TOOL-01 and D-PLAN-01 both say "exclude `classic-crashgen-settings-core` matching Phase 3". Phase 3 excluded it because its Python symbols flow through `classic_config` / `classic_scanlog` / `classic_scangame` wrappers and have no direct `classic-crashgen-settings-py` binding crate. BUT: Node's `classic-node/src/crashgen_rules.rs` is literally the direct NAPI binding for `classic-crashgen-settings-core` — 8 `#[napi(object)]` wrapper types plus 2 helper functions (lines 10-235). The 7 aux deferred entries are all from this module.
   - What's unclear: if Phase 4 follows CONTEXT.md and excludes it, then `RUST_TARGET_CRATES` has 18 entries and the crashgen_settings Rust symbols (CheckRule, PreflightRule, RuleSeverity, etc.) remain invisible to `parse_rust_surface()`. The Node `@rust`-suffix proxy pattern cannot be applied because the Rust symbols have no visible `rustSymbol` anchor. The aux contract rows would need `rustCrate: "classic-crashgen-settings-core"` but no matching `rustSymbol` entry in the surface JSON.
   - **Recommendation:** **Include it.** Plan 1 should add `"classic-crashgen-settings-core": "ClassicLib-rs/business-logic/classic-crashgen-settings-core/src/lib.rs"` to `RUST_TARGET_CRATES` and `"classic-crashgen-settings-core": "aux"` (or a new owner) to `RUST_OWNER_BY_CRATE`. Update CONTEXT D-TOOL-01 wording via a Phase 4 research amendment if the user confirms. Total target crates becomes **19** (matching Phase 3 PYTHON_TARGET_MODULES count) OR **18** (matching D-TOOL-01 literal wording with the exclusion). This is a **research-found correction** the user should see before Plan 1 starts.

2. **Resolution of scanlog `GLOBAL_FCX_HANDLER` promotability**
   - What we know: Phase 3 `[Phase 03-python-tier-collapse]: R9 exclusion: GLOBAL_FCX_HANDLER LazyLock static is not tier1-promotable; Wave 2 lands 57 rows not 58`. Python Wave 2 explicitly excluded it.
   - What's unclear: whether Node Plan 2 should also exclude it (replicating Phase 3) or whether Node has a different constraint.
   - **Recommendation:** Exclude it. Phase 4 scanlog plan lands 66 rows, not 67, for this reason. Document in the Plan 2 SUMMARY as "Phase 3 R9 precedent".

3. **`rustCrate` field retrofit policy**
   - What we know: Python contract rows carry `rustCrate` field (verified: 1098/1098 rows). Node contract rows do NOT (verified: 0/261 rows). Phase 4 is adding `validate_contract_surface()` which uses `rustCrate` for actionable error messages.
   - What's unclear: whether Plan 1 should retrofit all 261 existing Node rows to add `rustCrate` (cleaner, more churn) or add it to new rows only (less churn, inconsistent). The bidirectional guard works without `rustCrate` — that field is only used for the diagnostic message.
   - **Recommendation:** Add `rustCrate` to NEW rows only (all Plan 2-5 promotions + Plan 4 HARM-01/02 rows). Leave existing 261 rows untouched. The guard's error message falls back to `<unknown>` for rows without `rustCrate`, which is acceptable for rows that are already passing. Plan 1 includes a note: "future Phase 6 or a follow-up can retrofit existing rows if needed."

4. **Diff report 128 vs coverage summary 109 reconciliation**
   - What we know: `parity_diff_report.json::summary.tier2_gap_total = 128`, `runtime_coverage_summary.json::summary.deferred_total = 109`. The 109 comes from 101 registry entries × sum of `bindingIdentifiers + rustSymbols` = 109 tracked-surface items. The 128 counts raw gaps without registry cross-reference.
   - What's unclear: whether NODE-06's success criterion is truly just "`deferred_total == 0`" or also "`tier2_gap_total == 0`" (implied by "0 deferred entries and 0 Tier-1 drift" wording in ROADMAP). The `tier2_gap_total` field is deleted in the final cleanup per CONTEXT, so this self-resolves once Phase 4 lands. But during promotion plans (2-5), `tier2_gap_total` will still be meaningful and should decrease monotonically.
   - **Recommendation:** Track both metrics in each plan's SUMMARY.md. `deferred_total` is the authoritative NODE-06 metric; `tier2_gap_total` is the sanity check that no new gaps surface. Plan 6 deletes the latter.

5. **Which Node module owns each of the 18+ new tier-tracked crates in Owner map?**
   - What we know: CONTEXT Claude's Discretion: "Owner module reassignment for newly-tracked crates. Plan 1 may either preserve the `aux` collapse (smaller table) or split them into 7 distinct owner modules (better gap reporting per crate). The planner decides based on gap-report readability. Either choice is acceptable."
   - What's unclear: the right owner labels for Node's `shared.rs`-driven `classic-perf-core`, `classic-registry-core`, AND `classic-shared-core`. Python splits these into `perf`, `registry`, `shared` owner labels. Node's `shared.rs` combines all three. Should Node have one `shared` owner or three distinct owners matching Python?
   - **Recommendation:** Match Phase 3's Python owner structure (19 distinct owners including `aux` catch-all). Even though Node's `shared.rs` is one file, the Rust surface parser reads 3 distinct `-core/lib.rs` files and attributes symbols per crate. The owner label is for **gap reporting**, not for runtime organization. Matching Python makes Phase 6's `binding-parity-overview.md` rewrite trivially comparable.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Primary framework | `bun:test` (Bun's built-in test runner) + `node:test` (Node's built-in test runner) |
| bun version | latest (devDependency `bun-types: latest` in package.json) |
| Node version | 22+ (implied by `--test` flag usage; test runner needs Node >= 18) |
| Config file | `package.json::scripts` section (no separate config) |
| Quick run command (per-module bun) | `bun test __test__/<module>.spec.ts` from `ClassicLib-rs/node-bindings/classic-node/` |
| Full Bun suite | `bun run test:bun` → `bun run build:cli && bun test` |
| Full Node suite | `bun run test:node` → `bun run build:cli && node --test __test__/runtime.node.test.mjs` |
| Combined | `bun run test:bun && bun run test:node` |
| Parity gate | `bun run parity:gate:local` (runs `dts:freshness:local && parity:gate:update-baseline`) |
| Freshness check | `bun run dts:freshness:check` (python script comparing committed `index.d.ts` against a fresh debug build) |
| Rust-level test (PE-version integration) | `cargo test -p classic-version-core --lib pe_version --manifest-path ClassicLib-rs/Cargo.toml` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NODE-01 | Expanded `RUST_TARGET_CRATES` resolves to 18 non-empty crates | unit | `python -m pytest tools/node_api_parity/tests/test_generate_baseline_targets.py -q` | **Wave 0** — test file does not yet exist, Plan 1 creates it |
| NODE-02 | 109 deferred entries promoted; gate exits 0 | integration | `bun run parity:gate:local` | ✅ (package.json script exists) |
| NODE-02 | Every `nodeExport` is camelCase | unit (guard) | Bidirectional `validate_contract_surface()` fires on any snake_case | **Wave 0** — Plan 1 creates the guard |
| NODE-03 | Tier-2 skip logic removed from gate | snapshot | `tests/test_check_parity_gate.py::test_tier2_definition_removed_after_plan_6` (new, xfail→passing flip like Phase 3) | **Wave 0** |
| NODE-04 | `index.d.ts` matches fresh build | integration | `bun run dts:freshness:check` | ✅ |
| NODE-05 | Smoke tests pass for each promoted module (Bun) | unit | `bun run test:bun` | ✅ (20 existing spec files + new describe blocks) |
| NODE-05 | Smoke tests pass for each promoted module (Node) | unit | `bun run test:node` | ✅ (existing `runtime.node.test.mjs` + new test blocks) |
| NODE-06 | `runtime_coverage_summary.md::deferred_total == 0` | integration | `python ../../../tools/node_api_parity/check_parity_gate.py --repo-root ../../.. && grep -E "Deferred: \*\*0\*\*" docs/implementation/node_api_parity/baseline/runtime_coverage_summary.md` | ✅ (gate script); validation grep in each SUMMARY.md |
| HARM-01 | `extractPeVersion` exists as export in `index.d.ts` | unit | `bun test __test__/version.spec.ts -t "extractPeVersion"` | ✅ (file exists, new describe added by Plan 4) |
| HARM-01 | `isValidPePath` exists as export in `index.d.ts` | unit | `bun test __test__/version.spec.ts -t "isValidPePath"` | ✅ |
| HARM-02 | Returned object has `{ major, minor, patch, build }` numeric fields | unit | Assertion on type-of each field in the kernel32.dll test | ✅ |
| HARM-02 | Parity with Python's `classic_version.extract_pe_version("...")` result | manual-only (cross-binding) | Run both bindings on the same path; compare. Not automated because it requires both Python venv and Node native build in one shell. | **Manual** (documented in Plan 4 SUMMARY) |

### Sampling Rate

- **Per task commit:** `bun test __test__/<module>.spec.ts` (per-module bun test, < 10 seconds for a single module)
- **Per plan wave commit:** `bun run parity:gate:local && bun run test:bun && bun run test:node` (full gate + full test suite, ~1–2 minutes on Windows)
- **Phase gate (before `/gsd:verify-work`):** full suite green + `runtime_coverage_summary.md::deferred_total == 0`

### Wave 0 Gaps

Tests that must be created in Plan 1 BEFORE Plan 2 starts:

- [ ] `tools/node_api_parity/tests/__init__.py` — empty (new test dir)
- [ ] `tools/node_api_parity/tests/conftest.py` — central `sys.path` bootstrap (Phase 3 precedent at `tools/python_api_parity/tests/conftest.py`)
- [ ] `tools/node_api_parity/tests/test_generate_baseline_targets.py` — asserts every `RUST_TARGET_CRATES` entry parses to a non-empty symbol list (NODE-01 guard)
- [ ] `tools/node_api_parity/tests/test_check_parity_gate.py` — includes `test_tier1_contract_total_baseline_floor` (Plan 1 snapshot at 261) and `test_tier2_definition_removed_after_plan_6` (strict xfail, flipped to passing in Plan 6)
- [ ] `tools/node_api_parity/tests/test_validate_contract_surface.py` — D-TOOL-03 unit test with synthetic contract asserting both directions fire on correct rows

Phase 4 does NOT need to create:
- New per-module spec files (all 20 exist)
- New fixture types (`runtime_coverage_registry.ts` exists)
- New test runners (bun + node already wired)

## Sources

### Primary (HIGH confidence — direct live source reads, verified 2026-04-08)

- `.planning/phases/04-node-tier-collapse/04-CONTEXT.md` — user's locked decisions (D-PE-01..D-PE-04, D-PLAN-01..05, D-TOOL-01..04, D-DTS-01..02, D-TEST-01..02, D-ERR-01, D-REVIEW-01, D-EXEC-01, D-HASH-01)
- `.planning/phases/04-node-tier-collapse/04-DISCUSSION-LOG.md` — alternatives considered per area
- `.planning/REQUIREMENTS.md` §"Node Tier Collapse (NODE)" + §"Cross-Binding Harmonization (HARM)"
- `.planning/ROADMAP.md` §"Phase 4: Node Tier Collapse"
- `.planning/STATE.md` — Phase 3 closed, Phase 4 context gathered
- `CLAUDE.md` — build commands, key gotchas, commit conventions
- `AGENTS.md` — always-on repository rules, project skill reference
- `docs/api/binding-parity-overview.md` line 95 — "C++ has PE probing that Node does not expose" — the explicit gap Phase 4 closes
- `docs/api/README.md` — API doc table of contents
- `ClassicLib-rs/business-logic/classic-version-core/src/pe_version.rs` lines 1–245 — source of truth for `extract_pe_version` + `is_valid_executable_path` + `PeVersionError` enum + `PeVersionResult` type alias
- `ClassicLib-rs/business-logic/classic-version-core/src/lib.rs` lines 35–43 — `pub mod pe_version;` and `pub use pe_version::{PeVersionError, PeVersionResult, extract_pe_version};` (NOTE: `is_valid_executable_path` NOT re-exported)
- `ClassicLib-rs/python-bindings/classic-version-py/src/lib.rs` lines 300–398 — Python reference implementation for `extract_pe_version` + `is_valid_pe_path` (error classification via `PyFileNotFoundError` / `PyValueError`)
- `ClassicLib-rs/node-bindings/classic-node/src/version.rs` lines 1–99 — existing version binding; Phase 4 appends to this file
- `ClassicLib-rs/node-bindings/classic-node/src/lib.rs` — all 20 modules already declared (no changes needed)
- `ClassicLib-rs/node-bindings/classic-node/src/crashgen_rules.rs` — direct Node binding for `classic-crashgen-settings-core` (contradicts CONTEXT D-TOOL-01 exclusion)
- `ClassicLib-rs/node-bindings/classic-node/src/shared.rs` lines 1–10 — combines `classic-shared-core` + `classic-perf-core` + `classic-registry-core`
- `ClassicLib-rs/node-bindings/classic-node/Cargo.toml` lines 15, 16, 37, 63 — napi=3.x, napi-derive=3.x, classic-version-core path dep, napi-build=2.x
- `ClassicLib-rs/node-bindings/classic-node/package.json` lines 17–33 — full scripts section (build, parity:gate:local, test:bun, test:node, dts:freshness:check)
- `ClassicLib-rs/node-bindings/classic-node/index.d.ts` — 3977 lines; 235 `export declare`, 75 `export interface`
- `ClassicLib-rs/node-bindings/classic-node/__test__/version.spec.ts` — existing bun:test shape for describe/test/expect pattern
- `ClassicLib-rs/node-bindings/classic-node/__test__/parity_tier1.spec.ts` lines 1–220 — imports-all pattern with activeCoverageCases guard via `getRuntimeCoverageEntries(THIS_SUITE)`
- `ClassicLib-rs/node-bindings/classic-node/__test__/runtime.node.test.mjs` — `node:test` conventions
- `ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json` — 11 entries (4 tier1 selector + 7 tier2 runtime); verified full 64-char `contractIdsHash` at line 15 (D-HASH-01 precedent)
- `ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.ts` — `getRuntimeCoverageEntries(testSuite)` helper
- `tools/node_api_parity/generate_baseline.py` lines 1–737 — all parity tooling internals; line 24 (RUST_TARGET_CRATES), line 50 (RUST_FULL_INVENTORY_CRATES), line 64 (include_rust_symbol), line 169 (parse_rust_surface), line 284 (parse_node_surface), line 380 (generate_diff_report), line 456 (rust_unmapped branch), line 475 (node_unmapped branch), line 511 (tier2_gap_total), line 558 (Tier 2 Gaps markdown column)
- `tools/node_api_parity/check_parity_gate.py` lines 1–286 — current Node gate; line 116 main(), line 174–180 parse surfaces, line 181 generate_diff_report, no validate_contract_surface() guard yet (Plan 1 adds it around line 174)
- `tools/node_api_parity/check_dts_freshness.py` lines 1–120 — runs `bun run build:debug` + `git diff -- index.d.ts`
- `tools/python_api_parity/check_parity_gate.py` lines 31–76 — reference implementation of `validate_contract_rust_symbols` (Pitfall 2 guard) that Phase 4 extends to bidirectional
- `tools/python_api_parity/generate_baseline.py` lines 24–150 — Python RUST_TARGET_CRATES (19 entries) + SQUAD_BY_OWNER + _OWNER_RENDER_ORDER precedent
- `tools/binding_parity_runtime_coverage.py` lines 1–377 — shared helper; line 57 `_stable_id_hash` (mandatory per D-HASH-01), lines 221–330 `build_coverage_summary` (where `deferred_total` is computed)
- `docs/implementation/node_api_parity/baseline/parity_contract.json` — 261 tier1Mappings verified; 0 rows with `rustCrate` field
- `docs/implementation/node_api_parity/baseline/parity_diff_report.json` — 128 total gaps (70 rust_unmapped + 58 node_unmapped)
- `docs/implementation/node_api_parity/baseline/runtime_coverage_summary.md` — deferred_total=109 (authoritative NODE-06 metric)
- `docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json` — per-owner breakdown (aux=12, config=26, scanlog=67, version_registry=4)
- `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json` — 101 entries verified; sum of bindingIdentifiers + rustSymbols = 109 (explaining the 101-vs-109 mystery)
- `.planning/phases/03-python-tier-collapse/03-01-tooling-expansion-PLAN.md` — Phase 3 Plan 1 precedent for Phase 4 Plan 1 structure
- `.planning/phases/03-python-tier-collapse/03-01-A10-sizing.json` — Phase 3 A10 sizing output format
- `.planning/phases/03-python-tier-collapse/03-02-scanlog-wave1-parsing-primitives-SUMMARY.md` — Phase 3 scanlog 74-row plan precedent; @rust-suffix proxy rows documented here
- `.planning/phases/03-python-tier-collapse/03-09b-tier2-cleanup-and-final-sweep-PLAN.md` — Phase 3 M7 atomic cleanup precedent
- `ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py` line 650 — Python `is_valid_pe_path` smoke test shape

### Secondary (MEDIUM confidence — verified inference from live sources)

- NAPI-RS 3.x auto-conversion rules (snake_case → camelCase) — inferred from the existing `classic-node` binding where every Rust `pub fn foo_bar` corresponds to `fooBar` in `index.d.ts`. Confirmed by spot-check across scanlog.rs/version.rs bindings.
- `pelite` PE32/PE64 handling via `Wrap` type — from `classic_version_core::pe_version::extract_pe_version` docstring and source.
- The 101-vs-109 mystery mechanics — verified empirically by summing `bindingIdentifiers + rustSymbols` across `deferred_runtime_backlog.json::entries` (result: 109, exactly matching the coverage summary).

### Tertiary (LOW confidence — flagged for validation during planning)

- Phase 3's exact scanlog Wave 1 commit sizing ("11 minutes to promote 74 rows") — read from the SUMMARY file; not re-verified against git log. Phase 4 may take longer because `index.d.ts` regeneration adds a step per commit.
- Whether `migrateGameVersionSetting` is attributed to `version_registry` or `config` in the coverage summary — diff report owner is one thing, coverage summary may reconcile differently. Plan 4 reconciles during the version_registry promotion.

## Metadata

**Confidence breakdown:**
- User constraints: HIGH — copied verbatim from CONTEXT.md after reading the full file
- Phase requirements: HIGH — ID list provided by prompt, cross-referenced against REQUIREMENTS.md
- Standard stack: HIGH — all versions verified against live `Cargo.toml` + `package.json` on 2026-04-08
- Architecture patterns: HIGH — all patterns verified against live source files with line numbers
- Deferred entry inventory: HIGH — counts and symbol lists cross-verified across `deferred_runtime_backlog.json`, `parity_diff_report.json`, `runtime_coverage_summary.json`, and spot-checks against `index.d.ts`
- Pitfalls: HIGH — each pitfall traced to either a Phase 3 SUMMARY entry, a CONTEXT specifics block, or a live source read
- Code examples: HIGH for Rust shape (mirrors existing pattern in version.rs); MEDIUM for the full `index.d.ts` output — NAPI regeneration will confirm the exact shape
- Validation architecture: HIGH — all commands verified in `package.json::scripts`
- Open questions: HIGH — questions are raised where research hit a real contradiction between CONTEXT.md and the live source

**Research date:** 2026-04-08
**Valid until:** 2026-04-15 (7 days) — Phase 4 is expected to execute within this window. The two biggest drift risks: (1) a CLASSIC dependency version bump (napi, typescript) before execution — unlikely this week but possible; (2) a Phase 3 follow-up landing more changes to `tools/binding_parity_runtime_coverage.py` that affects Node. If either happens, refresh this research before `/gsd:execute-phase`.
