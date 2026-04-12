---
phase: 3
slug: constants-version-registry-merge
status: partial
nyquist_compliant: false
wave_0_complete: true
created: 2026-04-12
audited: 2026-04-12
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Rust `cargo test` + Python `pytest` + Bun/Node binding tests + parity gates + repo PowerShell C++ wrappers |
| **Config file** | `ClassicLib-rs/Cargo.toml`, `ClassicLib-rs/node-bindings/classic-node/package.json`, `ClassicLib-rs/python-bindings/requirements-ci.txt` |
| **Quick run command** | `python -m pytest tests/planning/test_phase03_validation.py -q` |
| **Full suite command** | `cargo test -p classic-version-registry-core -p classic-settings-core -p classic-shared-core --manifest-path ClassicLib-rs/Cargo.toml && uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py -q && pwsh -Command "Set-Location 'ClassicLib-rs/node-bindings/classic-node'; bun run build; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; bun run test:bun; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; bun run test:node" && cargo build -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml && pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test && pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test && python tools/cxx_api_parity/check_parity_gate.py --repo-root . --update-baseline && python tools/python_api_parity/check_parity_gate.py --repo-root . --update-baseline && pwsh -Command "Set-Location 'ClassicLib-rs/node-bindings/classic-node'; bun run parity:gate:update-baseline; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; bun run parity:gate" && cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml && cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml && python -m pytest tests/planning/test_phase03_validation.py -q` |
| **Estimated runtime** | ~600 seconds |

---

## Sampling Rate

- **After every task commit:** Run the touched-surface command from the Per-Task Verification Map plus `python -m pytest tests/planning/test_phase03_validation.py -q` after doc/parity cleanup tasks.
- **After every plan wave:** Run the full suite command for the phase.
- **Before `/gsd-verify-work`:** Full suite must be green.
- **Max feedback latency:** 30 seconds for the planning audit test; 600 seconds for the full phase suite.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | CNST-01 | unit/integration | `cargo test -p classic-version-registry-core -p classic-settings-core -p classic-shared-core --manifest-path ClassicLib-rs/Cargo.toml && cargo check --workspace --manifest-path ClassicLib-rs/Cargo.toml` | ✅ `ClassicLib-rs/business-logic/classic-version-registry-core/src/fallout4_version.rs`, `ClassicLib-rs/business-logic/classic-settings-core/src/yaml_file.rs`, `ClassicLib-rs/foundation/classic-shared-core/src/game_id.rs` | ✅ green |
| 03-01-02 | 01 | 1 | CNST-02, CNST-03 | integration/structural | `cargo check -p classic-version-core -p classic-xse-core -p classic-web-core -p classic-resource-core -p classic-tui --manifest-path ClassicLib-rs/Cargo.toml` + crate-reference sweeps | N/A (command + tree sweep) | ✅ green |
| 03-02-01 | 02 | 2 | CNST-01 | integration/smoke | `pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_version_registry classic_settings classic_shared && python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out ClassicLib-rs/python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings` | ✅ `ClassicLib-rs/python-bindings/classic-version-registry-py/src/fallout4_version.rs`, `ClassicLib-rs/python-bindings/classic-settings-py/src/yaml_file.rs`, `ClassicLib-rs/foundation/classic-shared-py/src/game_id.rs` | ✅ green |
| 03-02-02 | 02 | 2 | CNST-02, CNST-03 | smoke + audit guard | `pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python && uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py -q && python -m pytest tests/planning/test_phase03_validation.py -q` | ✅ `ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py`, `tests/planning/test_phase03_validation.py` | ❌ red — automated guard added, but retired `classic-constants-py` directory still exists |
| 03-03-01 | 03 | 2 | CNST-01, CNST-02 | binding regression | `pwsh -Command "Set-Location 'ClassicLib-rs/node-bindings/classic-node'; bun run build; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; bun run test:bun; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; bun run test:node"` | ✅ `ClassicLib-rs/node-bindings/classic-node/__test__/constants.spec.ts` | ✅ green |
| 03-03-02 | 03 | 2 | CNST-01, CNST-02 | native integration | `cargo build -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml && pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test && pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test` + native path sweep | ✅ `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/shared.rs`, `classic-gui/src/app/mainwindow.cpp` | ✅ green |
| 03-04-01 | 04 | 3 | CNST-01, CNST-02, CNST-03 | doc audit | `python -m pytest tests/planning/test_phase03_validation.py -q` | ✅ `tests/planning/test_phase03_validation.py` | ❌ red — active doc still references retired `classic-constants-py` |
| 03-04-02 | 04 | 3 | CNST-01, CNST-02, CNST-03 | parity artifact audit | `python tools/cxx_api_parity/check_parity_gate.py --repo-root . --update-baseline && python tools/python_api_parity/check_parity_gate.py --repo-root . --update-baseline && pwsh -Command "Set-Location 'ClassicLib-rs/node-bindings/classic-node'; bun run parity:gate:update-baseline; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; bun run parity:gate" && cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml && cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml && python -m pytest tests/planning/test_phase03_validation.py -q` | ✅ `tests/planning/test_phase03_validation.py`, parity baselines in `docs/implementation/` | ❌ red — stale generated parity surfaces still reference retired owners |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/planning/test_phase03_validation.py` — new audit guard for retired constants doc/artifact/tree drift
- [x] Existing `tests/planning/` infrastructure reused — no framework/bootstrap changes required

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Retired `classic-constants-py` directory is fully gone from the repo tree | CNST-03 | Automated guard exists, but current repo state fails it; validate-phase cannot patch implementation/tree artifacts | Delete `ClassicLib-rs/python-bindings/classic-constants-py/` leftovers, then run `python -m pytest tests/planning/test_phase03_validation.py -q` |
| Active contributor docs do not reference retired constants bindings | CNST-01, CNST-02, CNST-03 | Automated guard exists, but current repo state fails it because `docs/api/classic-version-registry-core.md` still mentions `classic-constants-py` | Fix the stale doc reference, then run `python -m pytest tests/planning/test_phase03_validation.py -q` |
| Committed parity surface artifacts are refreshed and free of retired constants/yaml/crashgen references | CNST-01, CNST-02, CNST-03 | Automated guard exists, but current repo state fails it because stale generated artifacts were committed | Regenerate and commit the affected parity surfaces, then run `python -m pytest tests/planning/test_phase03_validation.py -q` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s for the planning audit test
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** partial 2026-04-12 — automated guards added, but 3 escalated gaps remain red until implementation cleanup lands.

---

## Validation Audit 2026-04-12

| Metric | Count |
|--------|-------|
| Tasks audited | 8 |
| Gaps found | 3 |
| Resolved | 0 |
| Escalated to manual-only | 3 |
| Tests generated this audit | 1 |

**Audit method:** Reconstructed coverage from all four Phase 3 plans and summaries, cross-referenced live test surfaces (`test_promoted_residuals_smoke.py`, `constants.spec.ts`, native wrapper runs, parity gates), then spawned `gsd-nyquist-auditor` to fill uncovered closure gaps. The auditor added `tests/planning/test_phase03_validation.py` and ran `python -m pytest tests/planning/test_phase03_validation.py -q`, which failed `3` tests and passed `1`, confirming the remaining gaps are real implementation/doc/artifact defects rather than missing automation.

**Nyquist-compliance verdict:** PARTIAL. Core Phase 3 behavior has automated coverage across Rust, Python, Node, CXX, and parity workflows, but the phase is not Nyquist-compliant until the new planning audit test is green.
