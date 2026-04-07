---
phase: 08-workspace-and-infrastructure
plan: 02
subsystem: classic-path-core
tags: [linux, proton, docs-path, rust, docs]
requires: [08-01]
provides:
  - Shared Proton-aware Linux documents-path selection in `DocsPathFinder`
  - Crate-level integration proof for Proton ordering and fallback behavior
  - Updated contributor docs for Linux documents-path ordering
affects: [INFRA-03, TEST-03, docs]
tech-stack:
  added: []
  patterns: [shared Linux workflow, tempdir integration proof]
key-files:
  created:
    - ClassicLib-rs/business-logic/classic-path-core/tests/linux_proton_docs_path.rs
    - .planning/phases/08-workspace-and-infrastructure/08-02-SUMMARY.md
  modified:
    - ClassicLib-rs/business-logic/classic-path-core/src/docs_path.rs
    - ClassicLib-rs/business-logic/classic-path-core/src/platform/linux.rs
    - ClassicLib-rs/business-logic/classic-path-core/src/platform/mod.rs
    - docs/api/classic-path-core.md
    - docs/api/game-setup-workflow.md
key-decisions:
  - "Kept Linux documents-path ownership in `DocsPathFinder` and reused the existing Proton helpers instead of duplicating logic in bindings."
  - "Added one injected Linux helper on `DocsPathFinder` so crate-level integration proof can run on this Windows-hosted workflow."
patterns-established:
  - "Linux documents-path selection is cached path first, valid Proton path second, and local-share fallback third."
  - "Cross-platform proof for Linux-only behavior can use tempdir-backed injected inputs without changing binding surfaces."
requirements-completed: [INFRA-03, TEST-03]
duration: 19min
completed: 2026-04-06
---

# Phase 8 Plan 02: Linux Proton documents-path wiring Summary

**Shared Linux documents-path discovery now prefers a valid Fallout 4 Proton documents path before falling back to the legacy local-share path, with crate-level integration proof and aligned docs.**

## Accomplishments

- Wired `DocsPathFinder` through `parse_steam_library_vdf()` and `construct_proton_docs_path()` for non-Windows detection.
- Added `classic-path-core/tests/linux_proton_docs_path.rs` covering the happy path, Steam lookup failure fallback, invalid Proton fallback, and the legacy local-share regression.
- Updated the contributor docs so the documented documents-path order matches the implemented shared Rust workflow.

## Verification

- `cargo test -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml proton`
- `cargo test -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml`

## Self-Check: PASSED
