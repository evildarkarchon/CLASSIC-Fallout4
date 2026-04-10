# Requirements: CLASSIC v9.1.0-consolidation

**Defined:** 2026-04-10
**Core Value:** The Rust workspace has minimal, well-bounded crates with no redundant boundaries — every crate earns its compilation unit, and all binding surfaces remain at full parity with zero drift.

## v1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### YAML -> Settings Merge

- [ ] **YAML-01**: classic-yaml-core source modules are relocated into classic-settings-core with the same public API surface preserved
- [ ] **YAML-02**: All workspace crates that imported from classic-yaml-core import from classic-settings-core instead
- [ ] **YAML-03**: classic-yaml-core crate is removed from Cargo.toml workspace members and its directory deleted
- [ ] **YAML-04**: Binding crates (C++, Node, Python) that referenced yaml-core types are updated to the settings-core import path

### Crashgen -> Config Merge

- [ ] **CGEN-01**: classic-crashgen-settings-core source modules are relocated into classic-config-core with the same public API surface preserved
- [ ] **CGEN-02**: All workspace crates that imported from classic-crashgen-settings-core import from classic-config-core instead
- [ ] **CGEN-03**: classic-crashgen-settings-core crate is removed from Cargo.toml workspace members and its directory deleted

### Constants -> Version Registry Merge

- [ ] **CNST-01**: classic-constants-core source modules are relocated into classic-version-registry-core with the same public API surface preserved
- [ ] **CNST-02**: All workspace crates that imported from classic-constants-core import from classic-version-registry-core instead
- [ ] **CNST-03**: classic-constants-core crate is removed from Cargo.toml workspace members and its directory deleted

### Parity & Validation

- [ ] **GATE-01**: `cargo test --workspace` passes with no failures after all merges
- [ ] **GATE-02**: CXX parity gate baseline regenerated and exits 0
- [ ] **GATE-03**: Python parity gate exits 0 with `deferred_total == 0`
- [ ] **GATE-04**: Node parity gate exits 0
- [ ] **GATE-05**: API docs under `docs/api/` updated for merged crates (absorbed crate pages removed or consolidated, references updated)
- [ ] **GATE-06**: `CLAUDE.md` technology stack section updated to reflect 16 business-logic crates

## Future Requirements

None for this milestone -- consolidation is self-contained.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Merging path-core, file-io-core, or resource-core | Well-bounded crates with distinct responsibilities |
| Merging web-core, update-core, or database-core | Infrastructure crates with clean separation |
| New public API surface | Pure structural refactor, no behavioral changes |
| Binding API redesigns | Parity is achieved; consumer-facing APIs stay identical |
| Major binding API redesigns | Already out of scope from previous milestone |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| YAML-01 | Phase 1 | Pending |
| YAML-02 | Phase 1 | Pending |
| YAML-03 | Phase 1 | Pending |
| YAML-04 | Phase 1 | Pending |
| CGEN-01 | Phase 2 | Pending |
| CGEN-02 | Phase 2 | Pending |
| CGEN-03 | Phase 2 | Pending |
| CNST-01 | Phase 3 | Pending |
| CNST-02 | Phase 3 | Pending |
| CNST-03 | Phase 3 | Pending |
| GATE-01 | Phase 4 | Pending |
| GATE-02 | Phase 4 | Pending |
| GATE-03 | Phase 4 | Pending |
| GATE-04 | Phase 4 | Pending |
| GATE-05 | Phase 4 | Pending |
| GATE-06 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0

---
*Requirements defined: 2026-04-10*
*Last updated: 2026-04-10 after roadmap creation*
