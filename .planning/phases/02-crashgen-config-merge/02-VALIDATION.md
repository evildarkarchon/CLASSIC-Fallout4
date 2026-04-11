---
phase: 2
slug: crashgen-config-merge
status: draft
nyquist_compliant: false
wave_0_complete: false
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

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01 Task 1 | 02-01 | 1 | CGEN-01 | rename-only | `git log -1 --name-status` rename check | N/A | ⬜ pending |
| 02-01 Task 2 | 02-01 | 1 | CGEN-01, CGEN-02 | package build | `cargo build -p classic-config-core -p classic-scanlog-core -p classic-scangame-core` | ✅ | ⬜ pending |
| 02-01 Task 3 | 02-01 | 1 | CGEN-02 | package build | `cargo build -p classic-node -p classic-config-py -p classic-scanlog-py -p classic-scangame-py` | ✅ | ⬜ pending |
| 02-01 Task 4 | 02-01 | 1 | CGEN-03 | **FULL workspace** | `cargo build --workspace` + `cargo test --workspace` + `cargo clippy --workspace -- -D warnings` | ✅ | ⬜ pending |
| 02-01 Task 5 | 02-01 | 1 | (cleanup D-17) | workspace build | `cargo build --workspace` | ✅ | ⬜ pending |
| 02-02 Task 1 | 02-02 | 2 | CGEN-02/03 tooling | pytest | `uv run pytest tools/node_api_parity/tests/ -q` + generator dry-run | ✅ | ⬜ pending |
| 02-02 Task 2 | 02-02 | 2 | CGEN-01/02/03 docs | doc grep | `Select-String 'Crashgen rule model'` in config-core doc | ✅ | ⬜ pending |
| 02-02 Task 3 | 02-02 | 2 | CGEN-01/02/03 parity | parity gates | CXX + (rebuild_rust.ps1) + Python + Node gates | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

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

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify (Task 1 is rename-only, Tasks 2-3 have package-scoped builds, Task 4 is the first full-workspace sample — all satisfy sampling rate)
- [ ] Wave 0 covers all MISSING references (N/A — none needed)
- [ ] No watch-mode flags
- [ ] Feedback latency < 180s (package-scoped builds for Tasks 2-3 are faster; full workspace at Task 4)
- [ ] `nyquist_compliant: true` set in frontmatter (pending execution)
- [ ] Python parity gate is preceded by `./rebuild_rust.ps1 -Target python` (H4 fix)

**Approval:** pending
