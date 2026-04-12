---
phase: 4
slug: gate-validation-documentation
status: passed
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-11
audited: 2026-04-11
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python stdlib `unittest` via `pytest` runner + Rust `cargo test` + Python parity/stub validation + Bun/Node parity/runtime tests + CXX parity gate + repo PowerShell native wrappers |
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
| 04-01-01 | 01 | 1 | GATE-05, GATE-06 | doc audit regression | `python -m pytest tests/planning/test_phase04_validation.py -q` | ✅ `tests/planning/test_phase04_validation.py` | ✅ green |
| 04-01-02 | 01 | 1 | GATE-05, GATE-06 | doc sweep | `pwsh -NoProfile -Command "$files = @('CLAUDE.md','.planning/PROJECT.md','.planning/ROADMAP.md','.planning/REQUIREMENTS.md','.planning/codebase/ARCHITECTURE.md','.planning/codebase/STRUCTURE.md','.planning/codebase/STACK.md','docs/api/README.md','docs/api/binding-parity-overview.md','docs/api/binding-contract-refresh-note.md','docs/api/QUICK_START.md','docs/api/classic-config-core.md'); if ((Select-String -Path $files -Pattern 'parity:gate:local|deferred_total' -SimpleMatch -ErrorAction SilentlyContinue)) { exit 1 }"` | N/A (command audit) | ✅ green |
| 04-02-01 | 02 | 1 | GATE-02, GATE-03, GATE-04 | integration | `python tools/cxx_api_parity/check_parity_gate.py --repo-root . && python tools/python_api_parity/check_parity_gate.py --repo-root . && pwsh -Command "Set-Location 'ClassicLib-rs/node-bindings/classic-node'; bun run parity:gate"` | ✅ parity gate tooling + baselines | ✅ green |
| 04-02-02 | 02 | 1 | GATE-02, GATE-03, GATE-04 | integration/runtime | `pwsh -NoProfile -Command "Set-Location 'ClassicLib-rs/node-bindings/classic-node'; bun run build; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; bun run test:bun; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; bun run test:node; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; Set-Location ../../..; python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out ClassicLib-rs/python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings"` | ✅ `ClassicLib-rs/python-bindings/tests/test_parity_gate_tooling.py`, `ClassicLib-rs/node-bindings/classic-node/__test__/parity_tier1.spec.ts` | ✅ green |
| 04-03-01 | 03 | 2 | GATE-01, GATE-02, GATE-03, GATE-04 | closure suite | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml && pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test && pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test && python tools/cxx_api_parity/check_parity_gate.py --repo-root . && python tools/python_api_parity/check_parity_gate.py --repo-root . && pwsh -Command "Set-Location 'ClassicLib-rs/node-bindings/classic-node'; bun run parity:gate"` | ✅ wrappers + parity gates | ✅ green |
| 04-03-02 | 03 | 2 | GATE-01, GATE-02, GATE-03, GATE-04, GATE-05, GATE-06 | closure artifact audit | `python -m pytest tests/planning/test_phase04_validation.py -q` | ✅ `tests/planning/test_phase04_validation.py`, `.planning/phases/04-gate-validation-documentation/04-VERIFICATION.md` | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/planning/test_phase04_validation.py` — dedicated regression audit for GATE-05/GATE-06 doc truth, Phase 4 verification artifact structure/evidence, and requirements traceability
- [x] Existing `tests/planning/` stdlib `unittest` pattern reused — no framework/bootstrap changes required

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s for the planning audit test
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** passed 2026-04-11 — Phase 4 now has a dedicated planning regression test, corrected Plan 03 closure rows, and an updated Nyquist audit trail.

---

## Validation Audit 2026-04-11

| Metric | Count |
|--------|-------|
| Tasks audited | 6 |
| Gaps found | 3 |
| Resolved | 3 |
| Escalated to manual-only | 0 |
| Tests generated this audit | 1 |

**Audit method:** Re-read all Phase 4 plans, summaries, requirements, and the existing closure artifact; compared them against the live planning-test conventions in `tests/planning/`; then added a single focused `tests/planning/test_phase04_validation.py` regression file to cover the missing persistent GATE-05/GATE-06 doc audit and the missing post-phase verification/traceability audit. The per-task verification map was also corrected so the wave-2 closure rows now point to Plan 03 (`04-03-*`) instead of stale Plan 02 labels.

**Command evidence:** `python -m pytest tests/planning/test_phase04_validation.py -q` is the dedicated automated command for the previously missing doc/closure regression coverage.

**Nyquist-compliance verdict:** PASSED. The prior validation gaps are now covered by a persistent planning regression test, the closure-artifact audit is automated, and the Phase 4 validation map matches the implemented plan structure.
