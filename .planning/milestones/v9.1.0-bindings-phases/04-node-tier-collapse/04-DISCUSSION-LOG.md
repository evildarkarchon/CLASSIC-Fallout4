# Phase 4: Node Tier Collapse - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-09
**Phase:** 04-node-tier-collapse
**Areas discussed:** PE-version API shape, Plan decomposition / wave structure, Tooling expansion + camelCase guard, index.d.ts + smoke test discipline, Error shape / Cross-AI review / Execution / Hash algorithm

---

## Area Selection

Initial gray areas surfaced for selection (8 total, consolidated to 4 for AskUserQuestion's max-options limit):

| Area | Selected |
|---|---|
| PE-version API shape (HARM-01/02) | ✓ |
| Plan decomposition / wave structure | ✓ |
| Tooling expansion + camelCase guard (folded #5: nodeExport guard) | ✓ |
| index.d.ts + smoke test discipline (folded #6: test structure) | ✓ |

**Folded into Claude's Discretion (defaulted from prior phases / memory rules):**
- Cross-AI review cadence — defaulted to memory rule `feedback_review_before_execute_encoded_logic.md` (later partially re-discussed and locked in D-REVIEW-01)
- `classic-shared-core` Node exposure — defaulted to "skip, out of scope" per HARM-03/04 being Python-only

---

## PE-version API shape (HARM-01/02)

### Q1: Return shape for extractPeVersion(path)

| Option | Description | Selected |
|--------|-------------|----------|
| Typed object {major,minor,patch,build} | HARM-02 requirement text's preferred shape; idiomatic TS/NAPI; future-proof | ✓ |
| Tuple [major,minor,patch,build] | Mirrors Python tuple parity; less ergonomic for JS | |
| Stringified 'M.m.p.b' | Mirrors C++ extract_pe_version_string; awkward for JS callers | |

**User's choice:** Typed object {major,minor,patch,build}
**Captured as:** D-PE-01

### Q2: Error signaling

| Option | Description | Selected |
|--------|-------------|----------|
| Throw a typed Error with .code | Matches Phase 4 desire for richer error info | |
| Return null on error | Matches existing tryParseVersion / extractVersionFromFilename pattern | |
| Both: extractPeVersion throws, tryExtractPeVersion returns null | Mirror existing parseVersion / tryParseVersion pair | |
| (Locked via D-ERR-01 reconciliation): Throw via to_napi_err message-only | Existing version.rs convention | ✓ |

**User's choice:** Throw via existing to_napi_err pattern (recommended option) — later harmonized with D-ERR-01 to drop the .code field
**Captured as:** D-PE-02 (notes: D-ERR-01 supersedes the .code framing)

### Q3: isValidPePath sibling export

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — export isValidPePath alongside extractPeVersion | Required by HARM-01 explicitly | ✓ |
| No — internal validation only | Contradicts HARM-01 requirement text | |

**User's choice:** Yes — export isValidPePath
**Captured as:** D-PE-03

### Q4: Module placement

| Option | Description | Selected |
|--------|-------------|----------|
| Append to existing src/version.rs | 1:1 binding-to-core mapping; no new mod entry | ✓ |
| New src/pe_version.rs sibling module | Mirrors Rust core layout; more files | |

**User's choice:** Append to existing src/version.rs
**Captured as:** D-PE-04

---

## Plan decomposition / wave structure

### Q1: Overall plan count target

| Option | Description | Selected |
|--------|-------------|----------|
| 5–7 plans | Right-sized for 101-109 rows; matches Phase 3 lessons-learned | ✓ |
| 8–10 plans (mirror Phase 3) | Plan-for-plan replication; planning overhead exceeds execution overhead | |
| 3–4 plans (aggressive consolidation) | Loses bisect granularity; rolls back too much on retry | |

**User's choice:** 5–7 plans
**Captured as:** D-PLAN-01

### Q2: Scanlog 67-row split

| Option | Description | Selected |
|--------|-------------|----------|
| Single plan covering all scanlog | 67 rows is within plan capacity (Phase 3 Wave 1 was 74) | ✓ |
| Two plans by dependency layer | Wave A parsing / Wave B orchestration | |
| Three plans (Phase 3 mirror) | Maximum bisect granularity; overkill for 67 rows | |

**User's choice:** Single plan covering all scanlog
**Captured as:** D-PLAN-02

### Q3: HARM-01/02 placement

| Option | Description | Selected |
|--------|-------------|----------|
| Bundled with version_registry promotion plan | Both touch version-related Node bindings; reuses test fixtures | ✓ |
| Standalone plan | Cleaner conceptual boundary; adds one plan | |
| Folded into Plan 1 tooling | Risky — Plan 1 already has tooling expansion + camelCase guard work | |

**User's choice:** Bundled with version_registry promotion plan
**Captured as:** D-PLAN-03

### Q4: Final cleanup plan structure

| Option | Description | Selected |
|--------|-------------|----------|
| Atomic M7-style cascade in final plan | Bisect-clean; mirrors Phase 3 Plan 09b | ✓ |
| Spread across cleanup + verification plans | More commits, more bisect surface | |
| Inline cleanup at end of last promotion plan | Couples cleanup to promotion correctness; harder to revert | |

**User's choice:** Atomic M7-style cascade in final plan
**Captured as:** D-PLAN-04 (D-PLAN-05 for the front-loaded sizing report added during writeup)

---

## Tooling expansion + camelCase guard

### Q1: RUST_TARGET_CRATES expansion scope

| Option | Description | Selected |
|--------|-------------|----------|
| Match Python's 18 — all -core crates with a Node binding | Same exclusions as Python; verify each has src/<crate>.rs | ✓ |
| Selective expansion (only crates with deferred entries) | Future drift detection blind spot | |
| Match Python's 18 + classic-shared-core foundation | Foundation crate has no Node binding to enroll | |

**User's choice:** Match Python's 18 — all -core crates with a Node binding
**Captured as:** D-TOOL-01

### Q2: RUST_FULL_INVENTORY_CRATES disposition

| Option | Description | Selected |
|--------|-------------|----------|
| Delete the filter entirely | Aligns with one-tier philosophy; clean code | ✓ |
| Expand to all 18 (keep filter as scaling knob) | Dead code; contradicts milestone philosophy | |
| Leave at 3, rely on deferred backlog | Source of tier-2 carryover; Phase 3 explicitly rejected | |

**User's choice:** Delete the filter entirely
**Captured as:** D-TOOL-02

### Q3: camelCase guard implementation

| Option | Description | Selected |
|--------|-------------|----------|
| Bidirectional validate_contract_surface() helper | Single walk, two-direction errors; mirrors Phase 3 D-05 | ✓ |
| Two separate guards: one for Rust, one for Node | More granular but doubles call sites | |
| Defer to dts:freshness:check (existing tooling) | Wrong tool — checks staleness, not contract↔surface alignment | |

**User's choice:** Bidirectional validate_contract_surface() helper
**Captured as:** D-TOOL-03

### Q4: Guard timing

| Option | Description | Selected |
|--------|-------------|----------|
| Inside check_parity_gate.py main() unconditionally on every run | Catches drift the moment it lands; matches Phase 3 D-05 | ✓ |
| Only when --strict flag passed | Lets WIP slip through; Phase 3 explicitly rejected | |

**User's choice:** Inside check_parity_gate.py main() unconditionally
**Captured as:** D-TOOL-04

---

## index.d.ts + smoke test discipline

### Q1: index.d.ts regeneration cadence

| Option | Description | Selected |
|--------|-------------|----------|
| Within the same atomic commit as Rust #[napi] additions | Bisect-clean; every commit individually passes freshness gate | ✓ |
| Separate index.d.ts regeneration commit at end of plan | Easier recovery; intermediate commits fail freshness | |
| Once at phase close — single regeneration commit | Catastrophic if a single wave produces broken Rust | |

**User's choice:** Atomic with Rust source change
**Captured as:** D-DTS-01

### Q2: Plan 1 environment verification

| Option | Description | Selected |
|--------|-------------|----------|
| Plan 1 runs bun run build end-to-end as smoke test | Catches Phase 3-style PowerShell wrapper failures up front | ✓ |
| Defer environment verification to first promotion plan | Higher retry overhead if env breaks | |
| Skip explicit verification, trust existing CI gate | CI runs in different environment; may diverge | |

**User's choice:** Plan 1 runs bun run build end-to-end
**Captured as:** D-DTS-02

### Q3: Smoke test location

| Option | Description | Selected |
|--------|-------------|----------|
| Append to existing __test__/<module>.spec.ts files | Per-module convention already established | ✓ |
| New __test__/<module>_promoted.spec.ts sibling files | Doubles file count; splits coverage | |
| One large __test__/promoted.spec.ts | Single point of merge conflict | |

**User's choice:** Append to existing per-module spec files
**Captured as:** D-TEST-01

### Q4: Cross-runtime test coverage

| Option | Description | Selected |
|--------|-------------|----------|
| bun:test for every entry; node:test for one representative per module | Full bun coverage + cross-runtime parity proof at low cost | ✓ |
| bun:test only | Misses Bun-vs-Node divergence | |
| Both runtimes, every entry | Doubles maintenance for ~100 rows | |

**User's choice:** bun:test for every entry, node:test for representative per module
**Captured as:** D-TEST-02

---

## Error shape / Cross-AI review / Execution / Hash algorithm

### Q1: Error shape for ~67 promoted scanlog errors

| Option | Description | Selected |
|--------|-------------|----------|
| Preserve existing to_napi_err pattern — message only, no .code | Matches version.rs and every other current binding | ✓ |
| Add .code field to all promoted error types | Better cross-binding parity but splits the Node convention | |
| Add .code only to PE-version errors (HARM-01/02 scope only) | Inconsistent within Node itself | |

**User's choice:** Preserve existing to_napi_err pattern
**Captured as:** D-ERR-01

### Q2: Cross-AI review pre-scheduling

| Option | Description | Selected |
|--------|-------------|----------|
| Plan 1 (tooling) + final cleanup plan | Targeted protection on highest-risk plans | ✓ |
| Every plan (mirror Phase 3 late-stage discipline) | Maximum coverage; significant overhead per plan | |
| No pre-scheduling — decide per-plan during planning | Easy to forget; Phase 3 had to retroactively review | |

**User's choice:** Plan 1 + final cleanup plan
**Captured as:** D-REVIEW-01

### Q3: Worktree vs main repo execution

| Option | Description | Selected |
|--------|-------------|----------|
| Sequential on main, no worktrees | Avoids merge conflicts on shared parity_contract.json + index.d.ts | ✓ |
| Worktree per plan | Parallel capacity but high merge conflict risk | |
| Worktree only for non-overlapping plans | Hard to determine which plans qualify | |

**User's choice:** Sequential on main, no worktrees
**Captured as:** D-EXEC-01

### Q4: Lock contractIdsHash algorithm in CONTEXT.md

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — D-HASH-01: full 64-char SHA-256 via _stable_id_hash, mandatory import | Prevents Phase 3 R8 sha256[:16] truncation bug recurrence | ✓ |
| No — trust existing tool to enforce | Same bug recurs; cross-AI review catches it but at higher cost | |

**User's choice:** Yes — D-HASH-01
**Captured as:** D-HASH-01

---

## Claude's Discretion

The following areas were intentionally left flexible for the planner to decide during research/planning:

- Owner module reassignment for newly-tracked crates (collapse to `aux` or split into 7 distinct owners)
- Atomic commit granularity within a wave plan (per sub-module / per ~10 rows / per owner)
- Per-class smoke test grouping inside `describe` blocks
- `runtime.node.test.mjs` representative entry selection (criterion: exercises a real method)
- A10 sizing report format (markdown / JSON / both)
- `generate_baseline.py::SQUAD_BY_OWNER` expansion mechanics
- Whether the final cleanup plan also strips dead code from `generate_wave_manifest.py` and `generate_deferred_backlog.py` (or leaves entirely for Phase 6)

## Deferred Ideas

See CONTEXT.md `<deferred>` section for the full list. Notable deferrals:

- Tier-2 governance file deletion (Phase 6 DOC-02/03/04)
- `--deferred-registry` argument tolerance (Phase 6 DOC-01)
- `binding-parity-overview.md` rewrite (Phase 6 DOC-05)
- Per-binding error-contract documentation (Phase 6 HARM-05)
- Standardizing error conventions across bindings (anti-feature, Pitfall 7)
- `.code` field on Node error types (rejected via D-ERR-01)
- New Cargo dependencies including direct `pelite` in `classic-node` (rejected per HARM-01 requirement text)
- `classic-shared-core` Node exposure (HARM-03/04 was Python-only)
- Scanlog promotion split across multiple plans (rejected via D-PLAN-02)
- Worktree-based parallel execution (rejected via D-EXEC-01)
- Per-plan cross-AI review for every plan (rejected via D-REVIEW-01)
