---
phase: 4
slug: bounded-cache-replacement
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-05
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Rust `cargo test` + Rust bridge tests + Bun runtime/parity + Python parity/stub/smoke validation |
| **Config file** | `ClassicLib-rs/Cargo.toml`, `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/Cargo.toml`, `ClassicLib-rs/node-bindings/classic-node/package.json`, `ClassicLib-rs/python-bindings/requirements-ci.txt` |
| **Quick run command** | Run the touched task's listed `<automated>` command |
| **Full suite command** | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml && cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml --lib && cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml -- --check && cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings && bun run parity:gate:local && bun run test:bun && bun run test:node && python tools/python_api_parity/check_parity_gate.py --repo-root . && python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out ClassicLib-rs/python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings && uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py -q` |
| **Estimated runtime** | ~240 seconds |

---

## Sampling Rate

- **After every task commit:** Run the task's listed `<automated>` command for the touched surface.
- **After every plan wave:** Run `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml && cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml --lib && cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml -- --check && cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings && bun run parity:gate:local && bun run test:bun && bun run test:node && python tools/python_api_parity/check_parity_gate.py --repo-root . && python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out ClassicLib-rs/python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings && uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 240 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | CACHE-01, CONS-03 | unit | `cargo test -p classic-yaml-core --manifest-path ClassicLib-rs/Cargo.toml` | ✅ | ✅ green |
| 04-01-02 | 01 | 1 | CACHE-01, CONS-03 | integration + docs-contract | `cargo test -p classic-yaml-core --manifest-path ClassicLib-rs/Cargo.toml` | ✅ | ✅ green |
| 04-02-01 | 02 | 1 | CACHE-02, CONS-03 | unit | `cargo test -p classic-settings-core --manifest-path ClassicLib-rs/Cargo.toml` | ✅ | ✅ green |
| 04-02-02 | 02 | 1 | CACHE-02, CONS-03 | lifecycle + docs-contract | `cargo test -p classic-settings-core --manifest-path ClassicLib-rs/Cargo.toml` | ✅ | ✅ green |
| 04-03-01 | 03 | 1 | CACHE-03, CONS-03 | unit | `cargo test -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml -- hash` | ✅ | ✅ green |
| 04-03-02 | 03 | 1 | CACHE-03, CONS-03 | lifecycle + docs-contract | `cargo test -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml -- hash` | ✅ | ✅ green |
| 04-04-01 | 04 | 2 | CONS-03 | node runtime | `bun test __test__/yaml.spec.ts __test__/settings.spec.ts` | ✅ | ✅ green |
| 04-04-02 | 04 | 2 | CONS-03 | node runtime + parity | `bun test __test__/fileio.spec.ts __test__/parity_tier1.spec.ts` | ✅ | ✅ green |
| 04-05-01 | 05 | 2 | CONS-03 | python stubs | `python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out ClassicLib-rs/python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings` | ✅ | ✅ green |
| 04-05-02 | 05 | 2 | CONS-03 | python smoke | `uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py -q` | ✅ | ✅ green |
| 04-06-01 | 06 | 2 | CONS-03 | bridge unit | `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml --lib` | ✅ | ✅ green |
| 04-06-02 | 06 | 2 | CONS-03 | bridge build + docs-contract | `cargo build -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml` | ✅ | ✅ green |

*Status: ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing Rust, Node, Python, and C++ bridge infrastructure covers all phase requirements. No new validation infrastructure is required before execution.

---

## Manual-Only Verifications

All required phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 240s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

## Validation Audit 2026-04-07

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

Out-of-scope note: `python tools/python_api_parity/check_parity_gate.py --repo-root .` still reports one newly uncovered surface, `binding:rust:FcxResetError`, tied to Phase 3 scanlog parity drift rather than Phase 4 cache-validation coverage.
