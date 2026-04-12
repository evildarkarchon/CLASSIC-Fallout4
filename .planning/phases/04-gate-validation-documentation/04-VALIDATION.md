---
phase: 4
slug: gate-validation-documentation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Rust `cargo test` + Python parity/stub validation + Bun/Node parity/runtime tests + CXX parity gate + repo PowerShell native wrappers |
| **Config file** | `ClassicLib-rs/Cargo.toml`, `ClassicLib-rs/node-bindings/classic-node/package.json`, `ClassicLib-rs/python-bindings/requirements-ci.txt` |
| **Quick run command** | `python -m pytest tests/planning/test_phase04_validation.py -q` |
| **Full suite command** | `python tools/cxx_api_parity/check_parity_gate.py --repo-root . && python tools/python_api_parity/check_parity_gate.py --repo-root . && pwsh -Command "Set-Location 'ClassicLib-rs/node-bindings/classic-node'; bun run parity:gate" && cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml && pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test && pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test && python -m pytest tests/planning/test_phase04_validation.py -q` |
| **Estimated runtime** | ~600 seconds |

---

## Sampling Rate

- **After every task commit:** Run the touched-surface command from the Per-Task Verification Map plus `python -m pytest tests/planning/test_phase04_validation.py -q` after doc/parity cleanup tasks.
- **After every plan wave:** Run the full suite command for the phase.
- **Before `/gsd-verify-work`:** Full suite must be green.
- **Max feedback latency:** 30 seconds for the planning audit test; 600 seconds for the full phase suite.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | GATE-05, GATE-06 | doc audit | `python -m pytest tests/planning/test_phase04_validation.py -q` | ❌ Wave 0 | ⬜ pending |
| 04-01-02 | 01 | 1 | GATE-02, GATE-03, GATE-04 | integration | `python tools/cxx_api_parity/check_parity_gate.py --repo-root . && python tools/python_api_parity/check_parity_gate.py --repo-root . && pwsh -Command "Set-Location 'ClassicLib-rs/node-bindings/classic-node'; bun run parity:gate"` | ✅ | ⬜ pending |
| 04-02-01 | 02 | 2 | GATE-01, GATE-02, GATE-03, GATE-04 | integration | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml && pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test && pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test` | ✅ | ⬜ pending |
| 04-02-02 | 02 | 2 | GATE-01, GATE-02, GATE-03, GATE-04, GATE-05, GATE-06 | closure audit | `python tools/cxx_api_parity/check_parity_gate.py --repo-root . && python tools/python_api_parity/check_parity_gate.py --repo-root . && pwsh -Command "Set-Location 'ClassicLib-rs/node-bindings/classic-node'; bun run parity:gate" && cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml && pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test && pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test && python -m pytest tests/planning/test_phase04_validation.py -q` | ❌ Wave 0 for audit test | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/planning/test_phase04_validation.py` — add only if execution reveals a real closure gap not already covered by existing parity gates and doc sweeps

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s for the planning audit test
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
