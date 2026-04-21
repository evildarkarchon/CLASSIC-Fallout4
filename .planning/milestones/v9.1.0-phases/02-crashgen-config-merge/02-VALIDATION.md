---
phase: 2
slug: crashgen-config-merge
status: passed
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-11
updated: 2026-04-11
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | cargo test (workspace) + parity gates (Python/Node/CXX) |
| **Config file** | ClassicLib-rs/Cargo.toml |
| **Quick run command (package-scoped, Tasks 2-3)** | `cargo build -p <crate> --manifest-path ClassicLib-rs/Cargo.toml` |
| **Quick run command (full workspace, Task 4+)** | `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml` |
| **Full suite command** | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` |
| **Estimated runtime** | ~180 seconds (build) + ~300 seconds (test) |

---

## Sampling Rate (revised per H1 ordering fix)

**Plan 02-01 uses a staged verification strategy because D-13 creates an intentional intermediate non-building state between Task 1 and Task 4.**

- **After Task 1 (git mv rename-only commit):** NO cargo build — workspace is intentionally broken per D-13. This is not a failure.
- **After Task 2 (Rust core content edits):** `cargo build -p classic-config-core -p classic-scanlog-core -p classic-scangame-core --manifest-path ClassicLib-rs/Cargo.toml` (package-scoped only — old crate directory still on disk, so `--workspace` would still fail).
- **After Task 3 (binding migrations):** `cargo build -p classic-node -p classic-config-py -p classic-scanlog-py -p classic-scangame-py --manifest-path ClassicLib-rs/Cargo.toml` (package-scoped only, same reason).
- **After Task 4 (delete old crate directory + remove workspace member):** FIRST FULL-WORKSPACE SAMPLE —
  - `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml`
  - `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml`
  - `cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings`
- **After Task 5 (yamldata.rs.bak cleanup):** `cargo build --workspace` as a defensive post-commit check.
- **Before `/gsd:verify-work`:** Full suite must be green + all 3 parity gates (CXX, Python, Node) exit 0 with zero drift. Python gate requires `./rebuild_rust.ps1 -Target python` to have succeeded first.
- **Max feedback latency:** 180 seconds (quick build, post-Task-4)

**Why staged sampling:** Tasks 1-3 of Plan 02-01 leave the workspace in an intentional intermediate state where the old `classic-crashgen-settings-core/` directory still exists on disk while its contents have been moved/migrated. Workspace-wide cargo commands cannot succeed until Task 4 removes the directory. Per-task sampling is therefore scoped to the packages each task actually touches. The first full-workspace sample happens at Task 4 once the workspace is coherent again. This honors the H1 sequencing fix from the cross-AI review.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status | Evidence |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|----------|
| 02-01 Task 1 | 02-01 | 1 | CGEN-01 | rename-only | `git log -1 --name-status` rename check | N/A | ✅ green | Commit `68fe50d9` — pure R100 rename, blame preserved |
| 02-01 Task 2 | 02-01 | 1 | CGEN-01, CGEN-02 | package build | `cargo build -p classic-config-core -p classic-scanlog-core -p classic-scangame-core` | ✅ | ✅ green | Commit `48f1958d` — built after stub lib.rs fix (Deviation #1 auto-applied) |
| 02-01 Task 3 | 02-01 | 1 | CGEN-02 | package build | `cargo build -p classic-node -p classic-config-py -p classic-scanlog-py -p classic-scangame-py` | ✅ | ✅ green | Commit `e1db8e49` — 4 binding migrations |
| 02-01 Task 4 | 02-01 | 1 | CGEN-03 | **FULL workspace** | `cargo build --workspace` + `cargo test --workspace` + `cargo clippy --workspace -- -D warnings` | ✅ | ✅ green | Commit `a8b8f6bd` — build 54.82s, clippy 33.50s, `cargo test --workspace` 0 failed |
| 02-01 Task 5 | 02-01 | 1 | (cleanup D-17) | workspace build | `cargo build --workspace` | N/A | ⚪ N/A | No commit produced: `yamldata.rs.bak` was gitignored (`*.bak` in `.gitignore:47`), filesystem delete only (Deviation #2 — documented). Sampling continuity preserved by flanking Task 4 and 02-02 Task 1. |
| 02-02 Task 1 | 02-02 | 2 | CGEN-02/03 tooling | pytest | `uv run pytest tools/node_api_parity/tests/ -q` + generator dry-run | ✅ | ✅ green | Commit `58274042` — floor test renamed to `test_rust_target_crates_floor_is_seventeen` (Rule-1 deviation, floor 19→17 to match actual post-Phase-2 count) |
| 02-02 Task 2 | 02-02 | 2 | CGEN-01/02/03 docs | doc grep | `Select-String 'Crashgen rule model'` in config-core doc | ✅ | ✅ green | Commit `5c7bf726` — 1 match in `docs/api/classic-config-core.md` + full D-15 cross-ref sweep |
| 02-02 Task 3 | 02-02 | 2 | CGEN-01/02/03 parity | parity gates | CXX + (`rebuild_rust.ps1 -Target python`) + Python + Node gates | ✅ | ✅ green | CXX exit 0; `rebuild_rust.ps1` exit 0 (18/18 modules); Python exit 0 (tier1_gap_total=0); Node exit 0 (705/705 after reparent via `parity_contract_merge_owner.py`, commit `57d93ef1` — Deviation #2 auto-applied per Phase 1 precedent) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · ⚪ N/A*

---

## Wave 0 Requirements

- Existing infrastructure covers all phase requirements. Phase 2 is a strict structural refactor with zero new behavior — the 4 inline unit tests inside the moved `crashgen_rules.rs` carry forward via `git mv` and continue to run under `cargo test --workspace` at Task 4. No new test files, no new fixtures.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | — | All behavior preserved by cargo + parity gates | — |

*All phase behaviors have automated verification via cargo build/test and the three parity gates.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (Task 5 is N/A filesystem-only but flanked by Task 4 full-workspace sample and 02-02 Task 1 pytest — sampling rate satisfied)
- [x] Wave 0 covers all MISSING references (N/A — none needed; inline unit tests in `crashgen_rules.rs` carried forward via `git mv`)
- [x] No watch-mode flags
- [x] Feedback latency < 180s (package-scoped builds for Tasks 2-3 under ~60s; full workspace build at Task 4 54.82s)
- [x] `nyquist_compliant: true` set in frontmatter
- [x] Python parity gate was preceded by `./rebuild_rust.ps1 -Target python` (H4 fix honored — 18/18 modules rebuilt before Python gate)

**Approval:** passed — audited 2026-04-11 via `/gsd:validate-phase 2`

---

## Validation Audit 2026-04-11

| Metric | Count |
|--------|-------|
| Tasks audited | 8 |
| Gaps found | 0 |
| Resolved | 0 (no gaps to resolve) |
| Escalated | 0 |
| Deviations auto-fixed in SUMMARY | 5 (3 in 02-01, 2 in 02-02) |
| Out-of-scope deferred items | 1 (pre-existing `test_tier1_contract_total_baseline_floor` 705<711) |

**Audit method:** Cross-referenced the Per-Task Verification Map against `02-01-SUMMARY.md` and `02-02-SUMMARY.md` Verification Results tables. Every task ID has a corresponding commit hash and evidence line; every automated command has documented exit status; every deviation is recorded with Rule classification (Rule 1 / Rule 3).

**Nyquist-compliance verdict:** PASSED. Phase 2 is a pure structural refactor — every moved symbol is covered by `cargo test --workspace` + 3 parity gates. No new test files required; the `test_rust_target_crates_floor_is_seventeen` tripwire provides structural drift detection for the 17-crate topology.

**Pattern captured for Phase 3:** Crate-merge phases should add a floor-tripwire test asserting the post-merge workspace-member count BEFORE the merge commit, so the tripwire fires on any future regression back to the pre-merge crate count.
