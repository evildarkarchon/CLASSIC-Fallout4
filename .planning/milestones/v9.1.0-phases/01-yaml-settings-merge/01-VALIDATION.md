---
phase: 1
slug: yaml-settings-merge
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-10
audited: 2026-04-10
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Rust `cargo test` + Criterion 0.6 benchmarks + binding-specific test runners |
| **Config file** | `ClassicLib-rs/Cargo.toml` (workspace) |
| **Quick run command** | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` |
| **Full suite command** | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml && cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml`
- **After every plan wave:** Run `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml && cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings`
- **Before `/gsd:verify-work`:** Full suite must be green + all three parity gates pass
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | YAML-01 | unit | `cargo test -p classic-settings-core --manifest-path ClassicLib-rs/Cargo.toml` | ✅ `tests/yaml_integration_tests.rs`, `tests/yaml_dead_code_audit.rs`, `benches/yaml_benchmarks.rs` (git-mv'd from yaml-core, blame preserved) | ✅ green (171 + 1 + 13 passing per 01-01 SUMMARY) |
| 01-02-01 | 02 | 1 | YAML-02 | integration | `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml && cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` | N/A (build + workspace test) | ✅ green (105 test binaries, 0 failures per 01-02 SUMMARY) |
| 01-03-01 | 03 | 2 | YAML-03 | integration | `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml && cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` | N/A (build + lint check) | ✅ green (yaml-core dir deleted, clippy zero warnings per 01-01 + 01-03 SUMMARYs) |
| 01-04-01 | 02+03 | 2–3 | YAML-04 | integration | Node: `cd ClassicLib-rs/node-bindings/classic-node && bun run test:bun && bun run test:node && bun run parity:gate:local`; Python: `python tools/python_api_parity/check_parity_gate.py --repo-root .`; CXX: `python tools/cxx_api_parity/check_parity_gate.py`; C++ CLI: `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test` | ✅ `__test__/settings.spec.ts` (merged yaml.spec.ts), `classic-settings-py/classic_settings.pyi` (absorbed YamlOperations class), `cpp-bindings/classic-cpp-bridge/src/settings.rs` | ✅ green (bun 986 / node 17 / CLI 17 unit + 24 integration / CXX 333 entries / Python 613 tier1 rows / Node 705 tier1 rows — all three parity gates passing per 01-02 + 01-03 SUMMARYs) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `ClassicLib-rs/business-logic/classic-settings-core/tests/` directory — created via `mkdir -p` + `git mv` in plan 01-01 (Windows git similarity detection did not auto-create parents)
- [x] `ClassicLib-rs/business-logic/classic-settings-core/benches/` directory — created during source migration
- [x] `[[bench]]` entry in settings-core `Cargo.toml` for `yaml_benchmarks` — verified by `cargo bench -p classic-settings-core --no-run` exit 0
- [x] Criterion `0.6.0` dev-dependency in settings-core `Cargo.toml`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| git blame preservation | YAML-01 | `git mv` history check | Run `git log --follow ClassicLib-rs/business-logic/classic-settings-core/src/yaml_ops.rs` — should show history from original yaml-core lib.rs |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (all four items checked)
- [x] No watch-mode flags
- [x] Feedback latency < 60s (Rust quick-run ~60s; binding gates run per-wave)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-04-10 — all four requirement rows green post-execution, no gaps surfaced.

---

## Validation Audit 2026-04-10

Retroactive audit after phase execution (all three plans completed 2026-04-10 / 2026-04-11). Evidence sourced from `01-01-SUMMARY.md`, `01-02-SUMMARY.md`, and `01-03-SUMMARY.md` validation-commands tables.

| Metric | Count |
|--------|-------|
| Requirements audited | 4 (YAML-01..04) |
| Gaps found | 0 |
| Resolved (already covered) | 4 |
| Escalated to manual-only | 0 |
| New manual-only added | 0 |
| Tests generated this audit | 0 |

**Summary:** Phase 1 shipped with full automated verification across Rust workspace, all three binding surfaces, and all three parity gates (CXX 333 entries, Python 613 tier1 rows, Node 705 tier1 rows — all green). The pre-execution VALIDATION.md was a draft with `⬜ pending` statuses; this audit flips statuses to `✅ green` based on SUMMARY-documented evidence and marks the phase Nyquist-compliant. No auditor subagent was spawned — there was nothing to fill.

**Notable evidence chains:**
- YAML-01 Rust merge: `cargo test -p classic-settings-core` → 185 tests green; blame preserved via `git log --follow` against yaml_ops.rs (manual spot-check retained).
- YAML-04 binding parity: all three gates regenerated baselines in plan 01-03, including a root-cause fix for a pre-existing parity-generator bug (sub-module scan) that unblocked both Python and Node gates post-merge.
- Two pre-existing pytest failures in `test_parity_gate_tooling.py` are documented as inherited (unsupported `--deferred-registry` flag) and out of Phase 1 scope; not a Nyquist gap.
