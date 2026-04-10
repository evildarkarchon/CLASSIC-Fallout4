---
phase: 06
slug: documentation-reset
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-10
---

# Phase 06 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (parity tooling tests), structural assertions (doc content verification) |
| **Config file** | `pyrightconfig.json` (repo root), no dedicated pytest config |
| **Quick run command** | `uv run pytest ClassicLib-rs/python-bindings/tests/test_binding_coverage_tooling.py -q` |
| **Full suite command** | `python tools/python_api_parity/check_parity_gate.py --repo-root . && python tools/node_api_parity/check_parity_gate.py --repo-root . && uv run pytest ClassicLib-rs/python-bindings/tests/test_binding_coverage_tooling.py -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick run command (tooling tests)
- **After every plan wave:** Run full suite command (both gates + tests)
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-T1 | 01 | 1 | DOC-01 | integration | `python tools/python_api_parity/check_parity_gate.py --repo-root . && python tools/node_api_parity/check_parity_gate.py --repo-root .` | ✅ | ✅ green |
| 06-01-T1 | 01 | 1 | DOC-01 | unit | `uv run pytest ClassicLib-rs/python-bindings/tests/test_binding_coverage_tooling.py -q` | ✅ | ✅ green |
| 06-01-T2 | 01 | 1 | DOC-04 | structural | `test -f .planning/milestones/v9.1.0-bindings-promotion-audit.md` | ✅ | ✅ green |
| 06-02-T1 | 02 | 2 | DOC-02 | structural | `test -z "$(git ls-files docs/implementation/python_api_parity/governance/)"` | ✅ | ✅ green |
| 06-02-T1 | 02 | 2 | DOC-03 | structural | `test -z "$(git ls-files docs/implementation/node_api_parity/governance/)"` | ✅ | ✅ green |
| 06-02-T1 | 02 | 2 | DOC-07 | structural | `grep -q "C++ Bridge" docs/api/binding-contract-refresh-note.md && grep -q "cxx_api_parity" docs/api/binding-contract-refresh-note.md` | ✅ | ✅ green |
| 06-02-T2 | 02 | 2 | DOC-05 | structural | `grep -q "Not exposed" docs/api/binding-parity-overview.md && ! grep -qi "tier.2" docs/api/binding-parity-overview.md` | ✅ | ✅ green |
| 06-02-T2 | 02 | 2 | DOC-06 | structural | `grep -q "One-Tier" docs/api/binding-parity-policy.md && grep -c "check_parity_gate" docs/api/binding-parity-policy.md` | ✅ | ✅ green |
| 06-02-T2 | 02 | 2 | HARM-05 | structural | `grep -q "Why They Differ" docs/api/error-contract.md && grep -q "found: false" docs/api/error-contract.md && grep -q "orchestrator_process_log" docs/api/error-contract.md` | ✅ | ✅ green |
| 06-02-T2 | 02 | 2 | DOC-05 | structural | `grep -q "binding-parity-policy.md" docs/api/README.md && grep -q "error-contract.md" docs/api/README.md` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

Phase 6 is a documentation phase. Verification is structural (file existence, content assertions, grep sweeps) plus integration (gate script execution). No new test framework or test scaffold was needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Gate scripts pass end-to-end with Rust bindings | DOC-01 | Requires Python venv with maturin-built wheels | Run `python tools/python_api_parity/check_parity_gate.py --repo-root .` and `python tools/node_api_parity/check_parity_gate.py --repo-root .` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-10

---

## Validation Audit 2026-04-10

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

All 8 Phase 6 requirements (DOC-01..07, HARM-05) have automated or structural verification coverage. Phase 6 is a documentation-only phase where the primary verification mechanism is file-state assertions and content grep sweeps rather than behavioral unit tests.
