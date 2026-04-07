---
phase: 4
slug: bounded-cache-replacement
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | cargo test + Bun runtime/parity + Python parity/stub validation |
| **Config file** | `ClassicLib-rs/Cargo.toml`, `ClassicLib-rs/node-bindings/classic-node/package.json`, `ClassicLib-rs/python-bindings/requirements-ci.txt` |
| **Quick run command** | `cargo test -p classic-yaml-core -p classic-settings-core -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml` |
| **Full suite command** | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml && cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml -- --check && cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings && bun run parity:gate:local && bun run test:bun && bun run test:node && python tools/python_api_parity/check_parity_gate.py --repo-root . && python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out ClassicLib-rs/python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings` |
| **Estimated runtime** | ~180 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cargo test -p classic-yaml-core -p classic-settings-core -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml`
- **After every plan wave:** Run `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml && cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml -- --check && cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings && bun run parity:gate:local && bun run test:bun && bun run test:node && python tools/python_api_parity/check_parity_gate.py --repo-root . && python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out ClassicLib-rs/python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 180 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | CACHE-01 | unit | `cargo test -p classic-yaml-core --manifest-path ClassicLib-rs/Cargo.toml` | ✅ | ⬜ pending |
| 04-02-01 | 02 | 1 | CACHE-02 | unit | `cargo test -p classic-settings-core --manifest-path ClassicLib-rs/Cargo.toml` | ✅ | ⬜ pending |
| 04-03-01 | 03 | 1 | CACHE-03 | unit | `cargo test -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml` | ✅ | ⬜ pending |
| 04-04-01 | 04 | 2 | CONS-03 | parity + docs | `bun run parity:gate:local && bun run test:bun && bun run test:node && python tools/python_api_parity/check_parity_gate.py --repo-root . && python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out ClassicLib-rs/python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Bounded eviction semantics match phase intent without relying on exact victim order | CACHE-01, CACHE-02, CACHE-03 | `quick_cache` is officially documented as S3-FIFO, so exact LRU victim identity should not be asserted mechanically | Review the new cache-focused tests and confirm they validate bounded size/capacity and observable behavior rather than a specific oldest-key eviction order |
| C++ cache-stats scope matches the Phase 4 decision to align bindings | CONS-03 | Research identified ambiguity in how far C++ parity should go for cache stats | Inspect the resulting plans and implementation to confirm whether C++ gets explicit cache-stat entrypoints or an intentionally documented narrower surface, and ensure docs match |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 180s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
