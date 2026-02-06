# Phase 27: Test Coverage Evaluation and Improvement - Context

**Gathered:** 2026-02-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Evaluate test coverage across all Rust crates in the workspace, identify gaps, and write tests until every crate meets a 60% line coverage minimum. Python modules are explicitly out of scope (deferred to a future phase). Coverage tooling infrastructure (cargo-llvm-cov, reporting scripts) is included.

</domain>

<decisions>
## Implementation Decisions

### Coverage Scope & Priorities
- **Rust crates only** -- all crates in the workspace (foundation, business-logic, ui-applications)
- Python testing deferred to a separate future phase
- Slint GUI crate (classic-gui) IS in scope -- test Rust logic behind the GUI
- No pre-identified gap modules -- let coverage tools reveal the gaps

### Coverage Tooling & Reporting
- **cargo-llvm-cov** as the coverage tool (LLVM native instrumentation, good Windows support)
- **Dual report format**: HTML for local browsing + lcov/cobertura for future CI integration
- **Per-crate breakdown** -- individual coverage numbers for each crate, not just workspace aggregate
- Installation/scripting approach: Claude's discretion

### Test Strategy by Layer
- **Unit + integration tests** for gap-filling (not unit-only)
- GUI crate: Both direct logic tests AND trait-based mock tests (MockDispatcher, ScanWindowProperties)
- **Exclude generated code** from coverage metrics (Slint bindings, PyO3 generated code)
- **Error paths included** -- test error handling, edge cases, and boundary conditions alongside happy paths

### Quality Bar Definition
- **60% minimum line coverage** target for all crates
- **Uniform target** -- same bar for every crate, no tiered requirements
- **Advisory only** -- report coverage but don't enforce as CI gate
- **Full coverage push** -- measure, write tests, iterate until all crates meet 60%

### Claude's Discretion
- Coverage tooling installation approach (cargo install vs script)
- Test file organization within each crate
- Prioritization order when filling gaps across crates
- Specific exclusion patterns for generated code in cargo-llvm-cov config

</decisions>

<specifics>
## Specific Ideas

- User wants Python coverage handled as its own separate phase -- clean separation of concerns
- GUI testing should leverage existing patterns from Phase 26 (MockDispatcher, EventLoopDispatcher trait, ScanWindowProperties trait)
- Coverage reports should support future CI integration even though enforcement is advisory for now

</specifics>

<deferred>
## Deferred Ideas

- Python module test coverage -- separate future phase
- CI enforcement of coverage thresholds -- after baseline is established and stable

</deferred>

---

*Phase: 27-test-coverage*
*Context gathered: 2026-02-06*
