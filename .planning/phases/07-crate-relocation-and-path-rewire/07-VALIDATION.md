---
phase: 7
slug: crate-relocation-and-path-rewire
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-12
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python `unittest` under `pytest` + Cargo workspace proof |
| **Config file** | none - per-phase audit file under `tests/planning/` |
| **Quick run command** | `python -m pytest tests/planning/test_phase07_validation.py -q` |
| **Full suite command** | `cargo locate-project --workspace --message-format plain && cargo metadata --format-version 1 --no-deps && cargo check --workspace && python -m pytest tests/planning/test_phase07_validation.py -q` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/planning/test_phase07_validation.py -q`
- **After every plan wave:** Run `cargo locate-project --workspace --message-format plain && cargo metadata --format-version 1 --no-deps && cargo check --workspace && python -m pytest tests/planning/test_phase07_validation.py -q`
- **Before `/gsd-verify-work`:** `cargo locate-project --workspace --message-format plain && cargo metadata --format-version 1 --no-deps && cargo check --workspace && python -m pytest tests/planning/test_phase07_validation.py -q` must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | MOVE-01, MOVE-02 | unit/file audit | `python -c "from pathlib import Path; text = Path('.planning/phases/07-crate-relocation-and-path-rewire/07-RELOCATION-AUDIT.md').read_text(encoding='utf-8'); required = ['# Phase 7 Relocation Audit', '## Old to New Crate Mapping', '## Cargo Root Proof', '## Stale Member and Manifest Sweep', '## Legacy ClassicLib-rs Residue']; missing = [item for item in required if item not in text]; raise SystemExit(1 if missing else 0)"` | ✅ | ✅ green |
| 07-01-02 | 01 | 1 | MOVE-01, MOVE-02 | unit/bootstrap audit | `python -m pytest tests/planning/test_phase07_validation.py -q -k "bootstrap or audit"` | ✅ | ✅ green |
| 07-02-01 | 02 | 2 | MOVE-01, MOVE-02 | integration/workspace audit | `cargo metadata --format-version 1 --no-deps && python -m pytest tests/planning/test_phase07_validation.py -q -k "workspace_members_relocated or moved_layer_directories"` | ✅ | ✅ green |
| 07-02-02 | 02 | 2 | MOVE-01, MOVE-02 | integration/manifest audit | `cargo metadata --format-version 1 --no-deps && python -m pytest tests/planning/test_phase07_validation.py -q -k "representative_manifest_paths or cargo_root_detection"` | ✅ | ✅ green |
| 07-03-01 | 03 | 3 | MOVE-01, MOVE-02 | unit/audit artifact | `python -c "from pathlib import Path; text = Path('.planning/phases/07-crate-relocation-and-path-rewire/07-RELOCATION-AUDIT.md').read_text(encoding='utf-8'); required = ['## Old to New Crate Mapping', '## Cargo Root Proof', '## Stale Member and Manifest Sweep', '## Legacy ClassicLib-rs Residue']; missing = [item for item in required if item not in text]; raise SystemExit(1 if missing else 0)"` | ✅ | ✅ green |
| 07-03-02 | 03 | 3 | MOVE-01, MOVE-02 | phase-gate integration | `cargo locate-project --workspace --message-format plain && cargo metadata --format-version 1 --no-deps && cargo check --workspace && python -m pytest tests/planning/test_phase07_validation.py -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/planning/test_phase07_validation.py` - Phase 7 audit for relocation, cargo-root proof, representative manifest edges, and legacy-boundary cleanup
- [x] `.planning/phases/07-crate-relocation-and-path-rewire/07-RELOCATION-AUDIT.md` - checked-in relocation mapping and stale-path audit artifact

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-12

---

## Validation Audit 2026-04-12

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
