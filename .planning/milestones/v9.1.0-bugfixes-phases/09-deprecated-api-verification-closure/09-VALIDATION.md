---
phase: 09
slug: deprecated-api-verification-closure
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-06
updated: 2026-04-06
---

# Phase 09 — Validation Strategy

> Reconstructed Nyquist validation contract for the Phase 1 verification-closure backfill.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Rust `cargo test`, Python bindings `pytest` via `uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe`, Python parity gate scripts, and Bun Node parity/freshness scripts |
| **Config file** | `ClassicLib-rs/Cargo.toml`, `ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py`, `tools/python_api_parity/check_parity_gate.py`, `ClassicLib-rs/node-bindings/classic-node/package.json` |
| **Quick run command** | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml -- version::tests` |
| **Focused binding command** | `uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py -q -k "parse_segments_parallel or generate_suspect_section or formid_analyzer_legacy_dict_deprecation_warning"` |
| **Focused parity commands** | `python tools/python_api_parity/check_parity_gate.py --repo-root .` and `cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local` |
| **Full suite command** | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml -- version::tests && uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py -q -k "parse_segments_parallel or generate_suspect_section or formid_analyzer_legacy_dict_deprecation_warning" && python tools/python_api_parity/check_parity_gate.py --repo-root . && cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local` |
| **Estimated runtime** | ~3 minutes |

---

## Sampling Rate

- **After every task commit:** Run the narrowest relevant command for the touched proof surface: Rust `version::tests`, the targeted deprecated-binding pytest selector, or the relevant parity gate.
- **After every plan wave:** Run the full suite command.
- **Before `/gsd-verify-work`:** Full suite must be green and the resulting evidence must be reflected in `.planning/phases/01-deprecated-api-migration/01-VERIFICATION.md`.
- **Max feedback latency:** 180 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | DEBT-05, DEBT-06, DEBT-07, DEBT-10 | rust + binding runtime + parity | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml -- version::tests && uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py -q -k "parse_segments_parallel or generate_suspect_section or formid_analyzer_legacy_dict_deprecation_warning" && python tools/python_api_parity/check_parity_gate.py --repo-root .` | ✅ | ✅ green |
| 09-01-02 | 01 | 1 | DEBT-05, DEBT-06, DEBT-07, DEBT-10 | cross-binding parity | `cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local` | ✅ | ✅ green |
| 09-AUDIT-01 | audit | post-phase | DEBT-05, DEBT-06, DEBT-07, DEBT-10 | reconstructed Nyquist audit | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml -- version::tests && uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py -q -k "parse_segments_parallel or generate_suspect_section or formid_analyzer_legacy_dict_deprecation_warning" && python tools/python_api_parity/check_parity_gate.py --repo-root . && cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements; no new test files, fixtures, or framework installs were required for Phase 09.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5 minutes
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-06

---

## Validation Audit 2026-04-06

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

- Reconstructed this file from `09-01-PLAN.md`, `09-01-SUMMARY.md`, `09-VERIFICATION.md`, and the refreshed Phase 1 validation and verification artifacts because no Phase 09 validation file existed.
- Cross-referenced each Phase 09 requirement against current executable proof: `test_parse_segments_parallel_deprecation_warning`, `test_generate_suspect_section_deprecation_warning`, `test_formid_analyzer_legacy_dict_deprecation_warning`, and the Rust `version::tests` suite.
- Recorded the Node local parity gate explicitly because Task 2 depends on fresh cross-binding proof, not on unchanged-file inference.
- No new tests were generated during this audit because every requirement already had automated coverage that reran green.

### Commands Re-run During Audit

| Command | Outcome |
|---------|---------|
| `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml -- version::tests` | PASS — 24 tests passed |
| `uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py -q -k "parse_segments_parallel or generate_suspect_section or formid_analyzer_legacy_dict_deprecation_warning"` | PASS — 3 passed, 11 deselected |
| `python tools/python_api_parity/check_parity_gate.py --repo-root .` | PASS — Tier-1 gate regenerated with 59/59 matched, 0 missing Rust, 0 missing Python, 0 signature mismatches; 1 newly uncovered non-gating Python surface |
| `cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local` | PASS — `index.d.ts` freshness check passed and the Tier-1 Node parity gate passed |

### Audit Notes

- Phase 09 is Nyquist-compliant in reconstructed state B form: all mapped requirements are covered by deterministic automated proof and no manual-only exceptions remain.
- The audit did not require implementation changes because the gap was missing validation documentation, not missing executable coverage.
