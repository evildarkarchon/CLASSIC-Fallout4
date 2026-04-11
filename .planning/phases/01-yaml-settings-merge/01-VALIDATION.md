---
phase: 1
slug: yaml-settings-merge
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-10
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
| 01-01-01 | 01 | 1 | YAML-01 | unit | `cargo test -p classic-settings-core --manifest-path ClassicLib-rs/Cargo.toml` | ❌ W0 (tests migrate with source) | ⬜ pending |
| 01-02-01 | 02 | 1 | YAML-02 | integration | `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml` | N/A (build check) | ⬜ pending |
| 01-03-01 | 03 | 2 | YAML-03 | integration | `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml` | N/A (build check) | ⬜ pending |
| 01-04-01 | 04 | 2 | YAML-04 | integration | Node: `bun run test:bun`; Python: `uv run pytest ClassicLib-rs/python-bindings/tests -q`; C++: `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `ClassicLib-rs/business-logic/classic-settings-core/tests/` directory — created during source migration
- [ ] `ClassicLib-rs/business-logic/classic-settings-core/benches/` directory — created during source migration
- [ ] `[[bench]]` entry in settings-core `Cargo.toml` for `yaml_benchmarks`
- [ ] Criterion `0.6.0` dev-dependency in settings-core `Cargo.toml`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| git blame preservation | YAML-01 | `git mv` history check | Run `git log --follow ClassicLib-rs/business-logic/classic-settings-core/src/yaml_ops.rs` — should show history from original yaml-core lib.rs |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
