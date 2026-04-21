---
phase: 08
slug: workspace-and-infrastructure
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-06
updated: 2026-04-06
---

# Phase 08 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Rust built-in test harness plus Bun/Node parity and freshness scripts |
| **Config file** | `ClassicLib-rs/Cargo.toml`, `ClassicLib-rs/node-bindings/classic-node/package.json`, `.github/workflows/ci-rust.yml`, `.github/workflows/ci-typescript.yml` |
| **Quick run command** | `cargo test -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml proton && cd ClassicLib-rs/node-bindings/classic-node && bun run dts:freshness:check` |
| **Full suite command** | `cargo test --workspace --release --all-features --manifest-path ClassicLib-rs/Cargo.toml && cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local && bun run test:bun && bun run test:node && bun run dts:freshness:check` |
| **Estimated runtime** | ~8-15 minutes |

---

## Sampling Rate

- **After every task commit:** Run the task's listed `<automated>` command.
- **After every plan wave:** Run that wave's Rust verification plus `bun run dts:freshness:check` if Node artifacts or docs changed.
- **Before `/gsd-verify-work`:** Full suite must be green.
- **Max feedback latency:** 10 minutes.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | INFRA-01, INFRA-02 | manifest-build | `cargo check -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml && cargo check -p classic-constants-core --manifest-path ClassicLib-rs/Cargo.toml` | ✅ | ✅ green |
| 08-01-02 | 01 | 1 | INFRA-04 | crate-test, workspace-suite | `cargo test -p classic-shared-core --features gui-bridge --manifest-path ClassicLib-rs/Cargo.toml && cargo test --workspace --release --all-features --manifest-path ClassicLib-rs/Cargo.toml` | ✅ | ✅ green |
| 08-02-01 | 02 | 2 | INFRA-03 | focused-integration | `cargo test -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml proton -- --nocapture` | ✅ | ✅ green |
| 08-02-02 | 02 | 2 | TEST-03 | crate-test, doc-alignment | `cargo test -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml proton && cargo test -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml` | ✅ | ✅ green |
| 08-03-01 | 03 | 3 | INFRA-05 | freshness-check | `cd ClassicLib-rs/node-bindings/classic-node && bun run dts:freshness:check` | ✅ | ✅ green |
| 08-03-02 | 03 | 3 | INFRA-05 | parity-and-runtime | `cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local && bun run test:bun && bun run test:node && bun run dts:freshness:check` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] Create `ClassicLib-rs/business-logic/classic-path-core/tests/linux_proton_docs_path.rs` so the Proton happy path, both fallback branches, and the local-share regression have executable proof.
- [x] Existing Bun freshness/parity commands already exist in `ClassicLib-rs/node-bindings/classic-node/package.json`.
- [x] Existing Rust and TypeScript CI jobs already provide the phase gate structure.

---

## Manual-Only Verifications

All required phase behaviors have an automated verification path. Native Linux runtime proof is deferred because the planned injected integration tests are designed to execute in the current Windows-hosted workflow.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10 minutes for task-level checks
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

---

## Validation Audit 2026-04-06

| Metric | Count |
|--------|-------|
| Gaps found | 1 |
| Resolved | 1 |
| Escalated | 0 |

- The draft Wave 0 entries for `INFRA-03` and `TEST-03` were stale. `ClassicLib-rs/business-logic/classic-path-core/tests/linux_proton_docs_path.rs` exists and its focused plus crate-level commands now run green.
- The only audit gap was a transient `bun run test:bun` timeout in `ClassicLib-rs/node-bindings/classic-node/__test__/fileio.spec.ts` during the `INFRA-05` parity/runtime gate.
- The Nyquist auditor revalidated the Node contract path with the non-mutating sequence `bun run parity:gate:ci && bun run test:bun && bun run test:node`; it passed without test or implementation changes, so no manual-only exceptions remain.
