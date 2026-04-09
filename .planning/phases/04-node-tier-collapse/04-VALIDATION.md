---
phase: 4
slug: node-tier-collapse
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-09
updated: 2026-04-09
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `bun test` (Bun native, for `__test__/*.spec.ts`) + `node --test` (node:test, for `__test__/runtime.node.test.mjs`) + `pytest` for the parity gate's Python helpers |
| **Config file** | `ClassicLib-rs/node-bindings/classic-node/package.json` (scripts `parity:gate:local`, `test:bun`, `test:node`, `dts:freshness:check`, `build`); no `bun.test.ts` config needed |
| **Quick run command** | `bun run parity:gate:local` (covers gate + dts freshness + per-wave baseline refresh) |
| **Full suite command** | `bun run parity:gate:local && bun run test:bun && bun run test:node` |
| **Estimated runtime** | Quick: ~30–60 seconds (depends on `napi build --release` caching); Full: ~90–150 seconds |

**Working directory:** All `<verify>` commands in Plans 2-5 assume repo root (`J:/CLASSIC-Fallout4`) as the invoking cwd and use relative `cd ClassicLib-rs/node-bindings/classic-node && ...` to enter the Node bindings directory. The GSD framework's `execute-plan` workflow sets the repo root as cwd before running `<verify>` commands, so this is the correct convention. Plan 1 Task 3's PowerShell examples use absolute `cd J:/CLASSIC-Fallout4/ClassicLib-rs/node-bindings/classic-node` for clarity in interactive debugging. Issue 15 reconciliation: the `<verify>` relative paths are intentional and not a bug — they work from the GSD cwd contract. On Git Bash, source `tools/use_msvc_from_git_bash.sh` first to avoid linker shadowing on the `napi build --release` step.

---

## Sampling Rate

- **After every task commit:** Run `bun run parity:gate:local` — proves the gate stays green and the `index.d.ts` matches the committed contract after each atomic Rust change
- **After every plan wave:** Run `bun run parity:gate:local && bun run test:bun && bun run test:node` — proves runtime coverage (spec.ts smoke tests) and cross-runtime compatibility (runtime.node.test.mjs)
- **Before `/gsd:verify-work`:** Full suite green + `bun run dts:freshness:check` exits zero + `runtime_coverage_summary.md` shows `deferred_total == 0`
- **Max feedback latency:** 60 seconds for the quick command (below Nyquist threshold of 120s)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 0 | NODE-01 | tooling TDD | `python -m pytest tools/node_api_parity/tests/test_generate_baseline_targets.py -q` | Wave 0 (Plan 1 creates) | pending |
| 04-01-02 | 01 | 0 | NODE-01 | tooling TDD | `python -m pytest tools/node_api_parity/tests/test_validate_contract_surface.py -q` | Wave 0 (Plan 1 creates) | pending |
| 04-01-03 | 01 | 0 | NODE-01 | env smoke + scaffold | `cd ClassicLib-rs/node-bindings/classic-node && bun run build && bun run dts:freshness:check && python -m pytest tools/node_api_parity/tests/test_check_parity_gate.py -q` | Partial (Plan 1 creates test_check_parity_gate.py) | pending |
| 04-02-01 | 02 | 1 | NODE-02, NODE-03 | contract + gate | `python tools/node_api_parity/check_parity_gate.py --repo-root .` | yes | pending |
| 04-02-02 | 02 | 1 | NODE-02, NODE-04, NODE-05 | gate + bun:test + node:test | `cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local && bun run test:bun && bun run test:node` | yes | pending |
| 04-02-03 | 02 | 1 | NODE-02 | human-verify checkpoint | manual verification of proxy/normal split + gate green | n/a | pending |
| 04-03-01 | 03 | 2 | NODE-02, NODE-03 | contract + gate | `python tools/node_api_parity/check_parity_gate.py --repo-root .` | yes | pending |
| 04-03-02 | 03 | 2 | NODE-02, NODE-04, NODE-05 | gate + smoke | `cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local && bun run test:bun && bun run test:node` | yes | pending |
| 04-03-03 | 03 | 2 | NODE-02 | human-verify checkpoint | manual confirm config.deferred == 0 | n/a | pending |
| 04-04-01 | 04 | 3 | HARM-01 (A6) | re-export pre-flight | `grep -q "pub use pe_version::.*is_valid_executable_path" ClassicLib-rs/business-logic/classic-version-core/src/lib.rs && cargo check -p classic-version-core --manifest-path ClassicLib-rs/Cargo.toml` | yes | pending |
| 04-04-02 | 04 | 3 | HARM-01, HARM-02, NODE-02, NODE-04, NODE-05 | NAPI wrappers + index.d.ts + smoke | `cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local && bun run test:bun && bun run test:node && bun run dts:freshness:check` | yes | pending |
| 04-04-03 | 04 | 3 | HARM-02 | human-verify checkpoint | manual Python vs Node PE-version parity comparison (kernel32.dll) | n/a | pending |
| 04-05-01 | 05 | 4 | NODE-02, NODE-05 | gate + bun:test | `cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local && bun run test:bun` | yes | pending |
| 04-05-02 | 05 | 4 | NODE-02, NODE-03, NODE-05 | gate + full test suite | `cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local && bun run test:bun && bun run test:node` | yes | pending |
| 04-05-03 | 05 | 4 | NODE-02, NODE-06 | human-verify checkpoint | manual confirm deferred_total ≤ 1 | n/a | pending |
| 04-06-01 | 06 | 5 | NODE-03 | audit file exists | `test -f .planning/phases/04-node-tier-collapse/04-06-TIER2-CASCADE-AUDIT.md` | Wave 5 (Plan 6 creates) | pending |
| 04-06-02 | 06 | 5 | NODE-02, NODE-03, NODE-04, NODE-06 | M7 atomic cascade | `python -c "import json; d = json.load(open('docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json')); assert d.get('summary', {}).get('deferred_total') == 0" && cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local && bun run test:bun && bun run test:node` | yes | pending |
| 04-06-03 | 06 | 5 | all | Phase 4 CLOSED verification | `grep -q "Phase 4 CLOSED" .planning/phases/04-node-tier-collapse/04-06-tier2-cleanup-cascade-SUMMARY.md` | Wave 5 (Plan 6 creates) | pending |

*Task ID format: `{phase}-{plan}-{task}`. No gaps — every task has an `<automated>` verify command or is an explicit `checkpoint:human-verify` gate.*

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements (Plan 1 scope)

Wave 0 is Plan 1's scope. It MUST create or verify the following before any promotion wave runs:

- [ ] **Tooling diagnostic fixture** — `tools/node_api_parity/tests/test_validate_contract_surface.py` (new file) with pytest tests proving the bidirectional `validate_contract_surface()` guard catches:
  - Missing `rustSymbol` in `rust_api_surface.json` (diagnostic message includes `rustCrate` hint for new rows; `<unknown>` fallback for legacy rows without rustCrate)
  - Missing `nodeExport` in `node_api_surface.json` (diagnostic message includes `bun run build` / `index.d.ts` regeneration hint)
  - `@rust`-suffix proxy row handling (Rust-side only; suffix stripped before comparison; Node-side check skipped)
- [ ] **Environment smoke** — Plan 1 task that runs `bun run build` end-to-end from `ClassicLib-rs/node-bindings/classic-node/` and asserts exit 0 + `index.d.ts` mtime updated. Proves Node build env (Bun, napi, MSVC linker) is functional before any wave depends on it.
- [ ] **A10-style sizing report** — Per-owner deferred row counts after `RUST_TARGET_CRATES` expands 10 → 19 per A1. Written to `.planning/phases/04-node-tier-collapse/04-01-A10-sizing.{json,md}`. Plans 2–5 read this to size their task budgets before starting (D-PLAN-05).
- [ ] **Existing framework** — Bun, `@napi-rs/cli`, node test runner already installed via `bun install` (no new framework install needed). Verified by `bun run build` success.
- [ ] **Pytest baseline floor + xfail Plan 6 snapshot** — `tools/node_api_parity/tests/test_check_parity_gate.py` with `test_tier1_contract_total_baseline_floor` (snapshot at 261) and `test_tier2_definition_removed_after_plan_6` (`@pytest.mark.xfail(strict=True)` flipped in Plan 6).
- [ ] **`__test__/*.spec.ts` enumeration record** — Plan 1 Task 3 enumerates the 20 existing `ClassicLib-rs/node-bindings/classic-node/__test__/*.spec.ts` files and writes the discovered list into `04-01-A10-sizing.md` so Plan 5's per-owner test-append targets are pre-validated. Note: `crashgen_rules.spec.ts` does NOT exist today and will be created by Plan 5 Task 1 (recorded in the sizing report as `MISSING — Plan 5 creates`).

## Wave 3 Prerequisites (Plan 4 intra-plan)

Wave 3 is Plan 4's scope. The following prerequisite is intra-plan (Plan 4 Task 1 → Plan 4 Task 2), NOT Wave 0:

- [ ] **Rust re-export pre-flight** — Plan 4 Task 1 adds `pub use pe_version::is_valid_executable_path;` to `ClassicLib-rs/business-logic/classic-version-core/src/lib.rs` (current line 43). Without this, the bidirectional guard fails when HARM-01 contract rows land in Plan 4 Task 2. Verification: `grep -q "pub use pe_version::.*is_valid_executable_path" ClassicLib-rs/business-logic/classic-version-core/src/lib.rs`. This is a Plan 4 intra-plan prerequisite (Task 1 must commit before Task 2's NAPI wrappers + contract rows commit), not a Wave 0 item — Plan 1 cannot run it because Plan 1 is in Wave 0 and Plan 4 is in Wave 3.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PE-version runtime smoke against a real Windows PE | HARM-01 | Requires a real `kernel32.dll`-class binary; no portable fixture in-repo | `bun test __test__/version.spec.ts -t "extractPeVersion: kernel32.dll"` — asserts the returned object matches `{ major, minor, patch, build }` with all values > 0 for `C:\Windows\System32\kernel32.dll` on the test machine. Windows-only; skipped on non-Windows. |
| PE-version parity Python vs Node | HARM-02 | Requires both Python venv and Node native build in one shell — cross-runtime comparison not automatable via `bun` or `pytest` alone | Manual: run `uv run python -c "import classic_version; print(classic_version.extract_pe_version('C:\\\\Windows\\\\System32\\\\kernel32.dll'))"` and `bun test -t extractPeVersion` on the same file; compare outputs. Documented in Plan 4 Task 3 checkpoint. |
| Cross-runtime parity (Bun vs Node.js) for promoted scanlog wrappers | NODE-05 | `bun test` and `node --test` use different module-resolution and NAPI bootstrap paths; one can pass while the other fails | `bun run test:bun && bun run test:node` — both must exit zero. Sample size: one representative entry per promoted module in `runtime.node.test.mjs`. |
| Bisect-clean commit history across Plan 6's atomic cascade | NODE-03, NODE-04 | `git bisect` proof of "every commit passes or fails the gate cleanly" cannot be automated without running the gate on every commit | Manual: after Plan 6 merges, run `git log --oneline phase-04-start..phase-04-end`, check out each commit, run `bun run parity:gate:local`, record PASS/FAIL. Recorded in 04-06 SUMMARY. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or are explicit checkpoint gates
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers tooling diagnostic, sizing report, env smoke; Wave 3 covers A6 lib.rs re-export prerequisite (intra-plan to Plan 4)
- [x] No watch-mode flags (`bun test --watch`, `node --test --watch`) in any task command
- [x] Feedback latency < 60s for quick runs (`bun run parity:gate:local`)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned (ready for `/gsd:execute-phase 4`)
