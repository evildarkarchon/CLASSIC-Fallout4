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
| **Full suite command** | `cargo locate-project --workspace --message-format plain && cargo metadata --format-version 1 --no-deps && cargo check --workspace --all-targets && python -m pytest tests/planning/test_phase07_validation.py -q` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/planning/test_phase07_validation.py -q`
- **After every plan wave:** Run `cargo locate-project --workspace --message-format plain && cargo metadata --format-version 1 --no-deps && cargo check --workspace --all-targets && python -m pytest tests/planning/test_phase07_validation.py -q`
- **Before `/gsd-verify-work`:** `cargo locate-project --workspace --message-format plain && cargo metadata --format-version 1 --no-deps && cargo check --workspace --all-targets && python -m pytest tests/planning/test_phase07_validation.py -q` must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | MOVE-01, MOVE-02 | unit/file audit | `python -m pytest tests/planning/test_phase07_validation.py -q -k "relocation_audit_complete or mapping_matches_workspace_exactly or legacy_residue_inventory_matches_disk"` | ✅ | ✅ green |
| 07-01-02 | 01 | 1 | MOVE-01, MOVE-02 | unit/bootstrap audit | `python -m pytest tests/planning/test_phase07_validation.py -q -k "bootstrap or audit"` | ✅ | ✅ green |
| 07-02-01 | 02 | 2 | MOVE-01, MOVE-02 | integration/workspace audit | `cargo metadata --format-version 1 --no-deps && python -m pytest tests/planning/test_phase07_validation.py -q -k "workspace_members_relocated or moved_layer_directories"` | ✅ | ✅ green |
| 07-02-02 | 02 | 2 | MOVE-01, MOVE-02 | integration/manifest + benchmark fallout audit | `cargo metadata --format-version 1 --no-deps && cargo check --workspace --all-targets && python -m pytest tests/planning/test_phase07_validation.py -q -k "representative_manifest_paths or benchmark_include_path_fallout_rewired or cargo_root_detection"` | ✅ | ✅ green |
| 07-03-01 | 03 | 3 | MOVE-01, MOVE-02 | unit/audit artifact | `python -m pytest tests/planning/test_phase07_validation.py -q -k "relocation_audit_complete or mapping_matches_workspace_exactly or legacy_residue_inventory_matches_disk"` | ✅ | ✅ green |
| 07-03-02 | 03 | 3 | MOVE-01, MOVE-02 | phase-gate integration | `cargo locate-project --workspace --message-format plain && cargo metadata --format-version 1 --no-deps && cargo check --workspace --all-targets && python -m pytest tests/planning/test_phase07_validation.py -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/planning/test_phase07_validation.py` - Phase 7 audit for relocation, cargo-root proof, representative manifest edges, and legacy-boundary cleanup
- [x] `.planning/phases/07-crate-relocation-and-path-rewire/07-RELOCATION-AUDIT.md` - checked-in relocation mapping and stale-path audit artifact

---

## Manual-Only Verifications

None. Phase-local relocation, mapping, residue, and benchmark/include-path fallout checks are automated.

---

## Superseded Cross-Phase Contract Changes

| Surface | Command | Current State | Rationale |
|---------|---------|---------------|-----------|
| `validate_stubs.py` legacy-input contract | `python -m pytest tests/planning/test_phase06_validation.py -q -k stub_validator` | ℹ️ superseded | Phase 6 intentionally allowed explicit `ClassicLib-rs` normalization, but Phase 8 Plan 03 explicitly replaced that compatibility path with hard failure plus repo-root migration guidance. The failing Phase 6 test is stale against the completed Phase 8 policy and does not count against Phase 7 Nyquist coverage. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all Phase 7-local MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] No unresolved escalated regressions touching the validated move surface
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-12

---

## Validation Audit 2026-04-12

| Metric | Count |
|--------|-------|
| Gaps found | 2 |
| Resolved | 2 |
| Escalated | 0 |
| Superseded | 1 |

### Audit Updates

| Gap | Action | Outcome |
|-----|--------|---------|
| Relocation mapping exactness and residue inventory completeness were only checked by fragment presence | Added exact mapping-table parity and on-disk residue inventory assertions to `tests/planning/test_phase07_validation.py` | ✅ green |
| Benchmark/include-path relocation fallout was outside the Phase 7 gate | Added benchmark support and include-path assertions, and widened the full suite command to `cargo check --workspace --all-targets` | ✅ green |
| `validate_stubs.py` legacy-input contract drift was unclassified in the Phase 7 audit | Re-ran `python -m pytest tests/planning/test_phase06_validation.py -q -k stub_validator`, then reclassified the failure as a stale Phase 6 expectation superseded by completed Phase 8 policy | ℹ️ superseded |

### Commands Run

| Command | Result |
|---------|--------|
| `python -m pytest tests/planning/test_phase07_validation.py -q` | ✅ 10 passed |
| `cargo locate-project --workspace --message-format plain && cargo metadata --format-version 1 --no-deps && cargo check --workspace --all-targets && python -m pytest tests/planning/test_phase07_validation.py -q` | ✅ green |
| `python -m pytest tests/planning/test_phase06_validation.py -q -k stub_validator` | ℹ️ fails against a superseded Phase 6 expectation; Phase 8 now requires legacy `ClassicLib-rs` rejection |
