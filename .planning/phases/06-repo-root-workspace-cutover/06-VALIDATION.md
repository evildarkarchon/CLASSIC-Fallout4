---
phase: 6
slug: repo-root-workspace-cutover
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-12
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python `unittest` planning audit + direct Cargo command checks |
| **Config file** | none - per-phase audit file under `tests/planning/` |
| **Quick run command** | `python -m pytest tests/planning/test_phase06_validation.py -q` |
| **Full suite command** | `cargo fmt --all -- --check && cargo clippy --workspace --all-targets --all-features -- -D warnings && cargo test --workspace --release -- --nocapture && python -m pytest tests/planning/test_phase06_validation.py -q` |
| **Estimated runtime** | ~180 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/planning/test_phase06_validation.py -q`
- **After every plan wave:** Run `cargo fmt --all -- --check && cargo clippy --workspace --all-targets --all-features -- -D warnings && cargo test --workspace --release -- --nocapture && python -m pytest tests/planning/test_phase06_validation.py -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 180 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-00-01 | 00 | 0 | ROOT-01, ROOT-02 | unit/bootstrap audit | `python -m pytest tests/planning/test_phase06_validation.py -q -k "validation_bootstrap or clean_target_guard"` | ❌ / ❌ | ⬜ pending |
| 06-01-01 | 01 | 1 | ROOT-01 | unit/file audit | `python -m pytest tests/planning/test_phase06_validation.py -q -k "workspace_root_manifest or core_root_files"` | ❌ Wave 0 | ⬜ pending |
| 06-01-02 | 01 | 1 | ROOT-02 | unit/workflow audit | `python -m pytest tests/planning/test_phase06_validation.py -q -k "stub_validator or rebuild_script or cargo_aliases"` | ❌ Wave 0 | ⬜ pending |
| 06-02-01 | 02 | 2 | ROOT-01, ROOT-02 | unit/file audit | `python -m pytest tests/planning/test_phase06_validation.py -q -k "benchmark_support_set"` | ❌ Wave 0 | ⬜ pending |
| 06-03-01 | 03 | 3 | ROOT-01, ROOT-02 | unit/workflow audit | `python -m pytest tests/planning/test_phase06_validation.py -q -k repo_root_workflows` | ❌ Wave 0 | ⬜ pending |
| 06-03-02 | 03 | 3 | ROOT-01, ROOT-02 | phase-gate integration | `pwsh -File tests/planning/phase06_clean_run.ps1` | ❌ / ❌ Wave 0 | ⬜ pending |
| 06-03-03 | 03 | 3 | ROOT-01, ROOT-02 | unit/doc audit | `python -m pytest tests/planning/test_phase06_validation.py -q -k "readme_sync or agents_sync"` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/planning/test_phase06_validation.py` - planning audit for repo-root workspace detection, old-manifest retirement, and active workflow/doc audits
- [ ] `tests/planning/phase06_clean_run.ps1` - clean-state proof helper that renames or bypasses `ClassicLib-rs/target` before repo-root cargo validation

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Benchmark workflow path audit after moving `criterion.toml`, `benchmark-config.yaml`, and `benches/` | ROOT-02 | Phase 6 only requires minimum path-fix classification for `benchmarks.yml`; full benchmark CI closure is deferred | Read `.github/workflows/benchmarks.yml` after the move and confirm any required edits are limited to repo-root working directory, `target/...` paths, and repo-root Cargo discovery |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 180s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
