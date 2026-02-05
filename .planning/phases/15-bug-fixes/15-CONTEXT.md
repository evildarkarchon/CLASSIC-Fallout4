# Phase 15: Bug Fixes & Test Stabilization - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix two known bugs (BUG-01: test_clear_cache pollution, BUG-02: classic_settings() path resolution) and stabilize the test suite. Address any flaky tests discovered during investigation. Phase delivers reliable, parallel-safe tests.

</domain>

<decisions>
## Implementation Decisions

### Fix Approach
- **Broader improvement preferred** — Use BUG-01 as opportunity to improve test isolation patterns suite-wide, not just fix the one test
- **Audit path functions** — For BUG-02, check all path-related functions for similar CWD dependencies, not just classic_settings()
- **Fix related issues** — Address similar problems discovered during investigation (don't defer)
- **Refactoring allowed** — Okay to update test setup/teardown patterns, fixtures, and conftest if it improves isolation

### Regression Testing
- **Dedicated regression tests required** — Every bug fix gets a specific test documenting the failure mode
- **BUG-01 parallel verification** — Regression test must run multiple cache operations in parallel to verify no pollution
- **BUG-02 multi-CWD verification** — Regression test must call classic_settings() from multiple working directories
- **Dedicated regression file** — Create `tests/regression/test_bug_fixes.py` for explicit regression tracking

### Scope Boundaries
- **Fix all flaky tests** — Any flaky test found during investigation gets fixed in this phase
- **Python and Rust tests** — Both pytest and cargo test are in scope
- **Mark slow tests** — Add `@pytest.mark.slow` to tests taking >1 second
- **Audit skipped tests** — Review skipped/disabled tests: re-enable if fixable, document reasoning if intentional

### Claude's Discretion
- Specific implementation approach for test isolation improvements
- Order of bug fixes and test stabilization work
- Which test isolation patterns to adopt

</decisions>

<specifics>
## Specific Ideas

- Regression tests should be explicit about what they're guarding against (docstrings explaining the original bug)
- Test isolation improvements should benefit future test development, not just fix the immediate issue

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 15-bug-fixes*
*Context gathered: 2026-02-04*
