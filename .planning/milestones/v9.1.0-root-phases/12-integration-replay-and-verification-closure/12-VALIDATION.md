---
phase: 12
slug: integration-replay-and-verification-closure
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-10
updated: 2026-05-10
---

# Phase 12 - Validation Strategy

Per-phase validation contract for the archived integration replay and verification closure phase.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest with unittest-style assertions |
| **Config file** | none - direct planning audit |
| **Quick run command** | `uv run --with pytest python -m pytest tests/planning/test_phase12_validation.py -q` |
| **Full suite command** | `uv run --with pytest python -m pytest tests/planning/test_phase12_validation.py -q` |
| **Estimated runtime** | < 10 seconds after uv resolves pytest |

## Sampling Rate

- **After every task commit:** Run `uv run --with pytest python -m pytest tests/planning/test_phase12_validation.py -q`.
- **After every plan wave:** Run `uv run --with pytest python -m pytest tests/planning/test_phase12_validation.py -q`.
- **Before `$gsd-verify-work`:** Full suite must be green.
- **Max feedback latency:** < 10 seconds after uv resolves pytest.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 1 | INTG-01, INTG-04 | N/A | Clean-replay closure remains traceable through Phase 9 audit evidence and Phase 12 summary metadata. | planning audit | `uv run --with pytest python -m pytest tests/planning/test_phase12_validation.py -q` | yes | green |
| 12-02-01 | 02 | 1 | INTG-01, INTG-02 | N/A | Phase 8 wrapper/parity verification and summaries keep direct integration coverage. | planning audit | `uv run --with pytest python -m pytest tests/planning/test_phase12_validation.py -q` | yes | green |
| 12-03-01 | 03 | 2 | INTG-03, INTG-04 | N/A | Phase 9 CI/clean-state verification and summaries keep direct integration coverage. | planning audit | `uv run --with pytest python -m pytest tests/planning/test_phase12_validation.py -q` | yes | green |
| 12-99-01 | audit | 2 | INTG-01..INTG-04 | N/A | Archived milestone surfaces no longer report the missing Phase 12 Nyquist contract. | planning audit | `uv run --with pytest python -m pytest tests/planning/test_phase12_validation.py -q` | yes | green |

## Wave 0 Requirements

Existing infrastructure covers all Phase 12 requirements.

## Manual-Only Verifications

All phase behaviors have automated verification.

## Validation Audit 2026-05-10

| Metric | Count |
|--------|-------|
| Gaps found | 2 |
| Resolved | 2 |
| Escalated | 0 |

### Resolved Gaps

| Gap | Resolution |
|-----|------------|
| `12-VALIDATION.md` was missing, leaving the archived milestone audit with partial Nyquist coverage. | Added this validation contract and updated the archived milestone status surfaces to treat Phase 12 as Nyquist-compliant. |
| Phase 12 verification text referenced migration tests and the clean replay harness that were later deleted by `244935ff` (`Remove obsolete migration tests`). | Added `tests/planning/test_phase12_validation.py` as the current lightweight guard over the canonical archived closure artifacts instead of resurrecting obsolete migration tests. |

### Current Evidence Model

Phase 12 now validates the current archived state:

- `.planning/phases/12-integration-replay-and-verification-closure/12-01-SUMMARY.md` through `12-03-SUMMARY.md`
- `.planning/phases/08-wrapper-and-parity-rewire/08-VERIFICATION.md`
- `.planning/phases/09-clean-validation-and-ci-refresh/09-VERIFICATION.md`
- `.planning/milestones/v9.1.0-root-MILESTONE-AUDIT.md`
- `.planning/milestones/v9.1.0-root-ROADMAP.md`
- `.planning/PROJECT.md`, `.planning/STATE.md`, and `.planning/MILESTONES.md`

The deleted migration tests remain historical proof from the original execution window. The current Nyquist guard checks the durable archived closure contract and metadata that still exist in this checkout.

## Validation Sign-Off

- [x] All tasks have automated verify or Wave 0 dependencies.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify.
- [x] Wave 0 covers all MISSING references.
- [x] No watch-mode flags.
- [x] Feedback latency < 10 seconds after uv resolves pytest.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** approved 2026-05-10
