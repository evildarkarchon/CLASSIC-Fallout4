---
phase: 5
slug: ci-enforcement
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (via uv) + manual CI observation |
| **Config file** | none — pytest discovers via conftest.py in each test directory |
| **Quick run command** | `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` |
| **Full suite command** | `python tools/test_triple_gate_failure.py --repo-root .` |
| **Estimated runtime** | ~30 seconds (all three gates combined) |

---

## Sampling Rate

- **After every task commit:** Run `python tools/cxx_api_parity/check_parity_gate.py --repo-root .`
- **After every plan wave:** Run all three gate scripts + triple-gate test
- **Before `/gsd:verify-work`:** Full suite must be green + CI run verified
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | CI-03 | integration | `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` | Exists (Phase 1) | pending |
| 05-01-02 | 01 | 1 | CI-06 | unit | `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` | Exists (Phase 1) | pending |
| 05-02-01 | 02 | 1 | CI-05 | integration | `python tools/test_triple_gate_failure.py --repo-root .` | Wave 0 | pending |
| 05-03-01 | 03 | 2 | CI-01 | observational | `gh run list --workflow ci-python-bindings.yml --limit 1` | N/A (manual) | pending |
| 05-03-02 | 03 | 2 | CI-02 | observational | `gh run list --workflow ci-typescript.yml --limit 1` | N/A (manual) | pending |
| 05-03-03 | 03 | 2 | CI-04 | manual | GitHub Settings UI verification | N/A (manual) | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tools/test_triple_gate_failure.py` — triple-gate canary assertion script (CI-05)
- No framework install needed — pytest and Python already available via project environment

*Existing infrastructure covers most phase requirements; only the triple-gate test is new.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Python gate stays green after Phase 3 | CI-01 | Requires live CI run observation | Check latest `ci-python-bindings.yml` run via GitHub Actions UI or `gh run list` |
| Node gate stays green after Phase 4 | CI-02 | Requires live CI run observation | Check latest `ci-typescript.yml` run via GitHub Actions UI or `gh run list` |
| Branch protection includes all three gates | CI-04 | GitHub Settings UI action | Go to Settings > Branches > main > Edit, verify all three check names appear as required |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
