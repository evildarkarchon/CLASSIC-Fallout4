---
phase: 1
slug: deprecated-api-migration
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-05
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Rust `cargo test`, Python bindings `pytest` via `uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe` |
| **Config file** | `ClassicLib-rs/Cargo.toml`, `ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py` |
| **Quick run command** | `cargo test --manifest-path ClassicLib-rs/Cargo.toml -p classic-scanlog-core` |
| **Full suite command** | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml -- version::tests && uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py -q -k "parse_segments_parallel or generate_suspect_section or formid_analyzer_legacy_dict_deprecation_warning"` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run the task's targeted command for the touched Rust or Python surface.
- **After every plan wave:** Run the full suite command.
- **Before `/gsd:verify-work`:** Full suite must be green.
- **Max feedback latency:** 10 seconds.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | DEBT-07 | unit | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml -- version::tests` | ✅ | ✅ green |
| 01-02-02 | 02 | 1 | DEBT-05 | binding + warning | `uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py -q -k "parse_segments_parallel or generate_suspect_section or formid_analyzer_legacy_dict_deprecation_warning"` | ✅ | ✅ green |
| 01-02-02 | 02 | 1 | DEBT-06 | binding + warning | `uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py -q -k "parse_segments_parallel or generate_suspect_section or formid_analyzer_legacy_dict_deprecation_warning"` | ✅ | ✅ green |
| 01-02-02 | 02 | 1 | DEBT-10 | binding + warning | `uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py -q -k "parse_segments_parallel or generate_suspect_section or formid_analyzer_legacy_dict_deprecation_warning"` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements; no missing references remain after audit.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have automated verify commands or Wave 0 coverage.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify.
- [x] Wave 0 covers all MISSING references.
- [x] No watch-mode flags.
- [x] Feedback latency < 30s.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** audited 2026-04-06

---

## Validation Audit 2026-04-06

| Metric | Count |
|--------|-------|
| Gaps found | 2 |
| Resolved | 2 |
| Escalated | 0 |

- `DEBT-05`: strengthened `test_parse_segments_parallel_deprecation_warning` to compare deprecated output against `parse_all_sections(...)` and assert real plugin section content from `crash-12624.log`.
- `DEBT-06`: strengthened `test_generate_suspect_section_deprecation_warning` to verify exact delegation output for both empty and non-empty suspect inputs.
- `DEBT-07`: confirmed the Rust `check_version_status` replacement suite stays green.
- `DEBT-10`: confirmed the legacy `mods_single` warning path remains green under targeted pytest coverage.
