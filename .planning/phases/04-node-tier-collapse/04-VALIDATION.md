---
phase: 4
slug: node-tier-collapse
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
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

**Working directory:** All commands run from `ClassicLib-rs/node-bindings/classic-node/`. On Git Bash, source `tools/use_msvc_from_git_bash.sh` first to avoid linker shadowing on the `napi build --release` step.

---

## Sampling Rate

- **After every task commit:** Run `bun run parity:gate:local` — proves the gate stays green and the `index.d.ts` matches the committed contract after each atomic Rust change
- **After every plan wave:** Run `bun run parity:gate:local && bun run test:bun && bun run test:node` — proves runtime coverage (spec.ts smoke tests) and cross-runtime compatibility (runtime.node.test.mjs)
- **Before `/gsd:verify-work`:** Full suite green + `bun run dts:freshness:check` exits zero + `runtime_coverage_summary.md` shows `deferred_total == 0`
- **Max feedback latency:** 60 seconds for the quick command (below Nyquist threshold of 120s)

---

## Per-Task Verification Map

*Populated by `gsd-planner` during plan creation. Each task must have either an `<automated>` verify command or an explicit Wave 0 dependency.*

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 0 | NODE-01, NODE-02 | tooling | `python tools/node_api_parity/check_parity_gate.py --dry-run` | ✅ | ⬜ pending |
| 04-01-02 | 01 | 0 | NODE-01, NODE-02 | environment | `bun run build` (regenerates `index.d.ts`) | ✅ | ⬜ pending |
| 04-01-03 | 01 | 0 | NODE-05 | sizing report | `python tools/node_api_parity/generate_baseline.py --report-owners` (new flag) | ❌ W0 | ⬜ pending |
| 04-02-XX | 02 | 1 | NODE-03 | smoke | `bun test __test__/scanlog.spec.ts` | ✅ | ⬜ pending |
| 04-03-XX | 03 | 2 | NODE-03 | smoke | `bun test __test__/config.spec.ts` | ✅ | ⬜ pending |
| 04-04-XX | 04 | 2 | HARM-01, HARM-02 | smoke + runtime | `bun test __test__/version.spec.ts` + `node --test __test__/runtime.node.test.mjs` | ✅ | ⬜ pending |
| 04-05-XX | 05 | 3 | NODE-03 | smoke | `bun test __test__/{fileio,path,settings,message,resource,shared,perf,registry,crashgen_rules}.spec.ts` | ✅ | ⬜ pending |
| 04-06-01 | 06 | 4 | NODE-04, NODE-06 | gate green | `bun run parity:gate:local && python -c "import json; assert json.load(open('docs/implementation/node_api_parity/baseline/runtime_coverage_summary.json'))['deferred_total'] == 0"` | ✅ | ⬜ pending |

*Task ID format: `{phase}-{plan}-{task}`. `XX` placeholders are filled by the planner after task decomposition. The planner MUST keep a sampling-continuous fill — no 3 consecutive tasks without automated verify.*

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Wave 0 is Plan 1's scope. It MUST create or verify the following before any promotion wave runs:

- [ ] **Tooling diagnostic fixture** — `tools/node_api_parity/test_validate_contract_surface.py` (new file) with pytest tests proving the bidirectional `validate_contract_surface()` guard catches:
  - Missing `rustSymbol` in `rust_api_surface.json` (diagnostic message includes `rustCrate` hint for new rows)
  - Missing `nodeExport` in `node_api_surface.json` (diagnostic message includes `index.d.ts` regeneration hint)
  - Stale entries after a Rust function rename (simulated by editing a fixture JSON)
- [ ] **Environment smoke** — Plan 1 task that runs `bun run build` end-to-end and asserts exit 0 + `index.d.ts` mtime updated. Proves Node build env (Bun, napi, MSVC linker) is functional before any wave depends on it.
- [ ] **A10-style sizing report** — `tools/node_api_parity/generate_baseline.py --report-owners` emits per-owner deferred row counts after `RUST_TARGET_CRATES` expands 10 → 19. Written to `.planning/phases/04-node-tier-collapse/04-01-sizing-report.md` or `.json`. Plans 2–5 read this to size their task budgets before starting (D-PLAN-05).
- [ ] **Rust re-export pre-flight** — Plan 4's first task adds `pub use pe_version::is_valid_executable_path;` to `ClassicLib-rs/business-logic/classic-version-core/src/lib.rs` (line 43). Without this, the bidirectional guard fails when HARM-01 contract rows land. Verification: `grep -q "pub use pe_version::is_valid_executable_path" ClassicLib-rs/business-logic/classic-version-core/src/lib.rs`.
- [ ] **Existing framework** — Bun, `@napi-rs/cli`, node test runner already installed via `bun install` (no new framework install needed). Verified by `bun run build` success.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PE-version runtime smoke against a real Windows PE | HARM-01 | Requires a real `kernel32.dll`-class binary; portable fixture in-repo |  `bun test __test__/runtime.node.test.mjs -t "extractPeVersion: kernel32.dll"` — asserts the returned object matches `{ major, minor, patch, build }` with all values > 0 for `C:\Windows\System32\kernel32.dll` on the test machine. Windows-only; skipped on non-Windows CI. |
| Cross-runtime parity (Bun vs Node.js) for promoted scanlog wrappers | NODE-03 | `bun test` and `node --test` use different module-resolution and NAPI bootstrap paths; one can pass while the other fails | `bun run test:bun && bun run test:node` — both must exit zero. Sample size: one representative entry per promoted module in `runtime.node.test.mjs`. |
| Bisect-clean commit history across Plan 6's atomic cascade | NODE-04 | `git bisect` proof of "every commit passes or fails the gate cleanly" cannot be automated without running the gate on every commit | Manual: after Plan 6 merges, run `git log --oneline phase-04-start..phase-04-end`, check out each commit, run `bun run parity:gate:local`, record PASS/FAIL. Verified in `04-VERIFICATION.md`. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (tooling diagnostic fixture, sizing report, re-export pre-flight)
- [ ] No watch-mode flags (`bun test --watch`, `node --test --watch`) in any task command
- [ ] Feedback latency < 60s for quick runs (`bun run parity:gate:local`)
- [ ] `nyquist_compliant: true` set in frontmatter (flipped after gsd-planner fills the verification map and gsd-plan-checker passes Dimension 8)

**Approval:** pending
