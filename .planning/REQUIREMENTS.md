# Requirements: CLASSIC

**Defined:** 2026-04-11
**Milestone:** `v9.1.0-root` Move Crates to Project Root
**Core Value:** The Rust workspace has minimal, well-bounded crates with no redundant boundaries -- every crate earns its compilation unit, and all binding surfaces remain at full parity with zero drift.

## Milestone Requirements

Requirements for milestone `v9.1.0-root`. Each requirement maps to exactly one roadmap phase.

### Workspace Root

- [x] **ROOT-01**: Contributor can run the Rust workspace from the repository root without using `ClassicLib-rs/Cargo.toml` as the canonical workspace manifest
- [x] **ROOT-02**: Contributor can use repo-root Cargo workflows for the relocated workspace, including `cargo fmt --all`, `cargo clippy --workspace`, and `cargo test --workspace`

### Crate Relocation

- [ ] **MOVE-01**: Contributor can find every crate previously under `ClassicLib-rs/` at its new repository-root-relative location with each crate's internal directory structure preserved
- [ ] **MOVE-02**: Contributor can resolve all workspace members and local crate path dependencies after the relocation without keeping a second active workspace under `ClassicLib-rs/`

### Integrations

- [ ] **INTG-01**: Contributor can run the existing Rust-consuming wrapper entrypoints after relocation, including repo rebuild scripts and native CLI/GUI/TUI integration flows
- [ ] **INTG-02**: Contributor can run the Python, Node, and CXX parity gates against the relocated workspace without path drift or parity-contract changes
- [ ] **INTG-03**: Contributor can run CI and path-sensitive build or packaging jobs against the relocated workspace using the new repository-root layout
- [ ] **INTG-04**: Contributor can verify the relocation from a clean state with regenerated path-bearing artifacts instead of relying on stale caches or outputs

### Docs and Guidance

- [ ] **DOCS-01**: Contributor can follow active docs, skills, and agent context files without being routed to `ClassicLib-rs/` as the live workspace root
- [ ] **DOCS-02**: Contributor can use milestone migration notes or a verification matrix to map the old workspace-root workflows to the new repository-root workflows
- [ ] **DOCS-03**: Contributor gets regression protection against newly introduced active `ClassicLib-rs/` workspace-root references in validation-critical docs, scripts, or tests

## Future Requirements

None currently deferred.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Crate renames, merges, or splits during the move | This milestone is a relocation only; crate-graph redesign would make failures harder to attribute |
| Binding API redesign or parity-contract reshaping | Public surface changes are unrelated to the path migration and would create intentional drift |
| Moving non-Rust top-level product directories as part of this work | The milestone is scoped to the Rust workspace currently under `ClassicLib-rs/` |
| Dependency or toolchain upgrades unrelated to relocation blockers | Version churn would introduce independent failure modes during a path migration |
| Permanent support for both repo-root and `ClassicLib-rs/` workspace layouts | The new single source of truth must be the repository root |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ROOT-01 | Phase 6 | Complete |
| ROOT-02 | Phase 6 | Complete |
| MOVE-01 | Phase 7 | Pending |
| MOVE-02 | Phase 7 | Pending |
| INTG-01 | Phase 8 | Pending |
| INTG-02 | Phase 8 | Pending |
| INTG-03 | Phase 9 | Pending |
| INTG-04 | Phase 9 | Pending |
| DOCS-01 | Phase 10 | Pending |
| DOCS-02 | Phase 10 | Pending |
| DOCS-03 | Phase 10 | Pending |

**Coverage:**
- Milestone requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-11*
*Last updated: 2026-04-11 after roadmap creation*
