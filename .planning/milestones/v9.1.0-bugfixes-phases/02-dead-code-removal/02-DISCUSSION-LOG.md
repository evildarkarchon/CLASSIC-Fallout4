# Phase 2: Dead Code Removal - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 02-dead-code-removal
**Areas discussed:** Adjacent dead code scope, Deprecated shim test disposition, Legacy fallback elimination strategy

---

## Adjacent Dead Code Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Strict scope | Only delete the 4 items + 3 deprecated methods listed in requirements. Leave `fast_contains` and fix the broken test separately. | |
| Clean as you go | Also remove `fast_contains` and the `YamlFormatConfig` test since they're in files we're already editing. No point leaving known dead code behind. | Y |
| You decide | Claude picks based on what makes sense per file. | |

**User's choice:** Clean as you go
**Notes:** None

---

## Deprecated Shim Test Disposition

| Option | Description | Selected |
|--------|-------------|----------|
| Delete outright | The deprecated shims were wrappers around `parse_all_sections_arc`. If the underlying behavior is already tested via the current API, these tests are redundant. Just delete them. | |
| Migrate first, then delete shims | Port the 3 tests to use `parse_all_sections`/`parse_all_sections_arc` first (ensuring boundary parsing, patch ordering, and XSE slot behavior are covered under the current API), then delete the deprecated methods. | Y |
| You decide | Claude checks whether the behavior is already covered and acts accordingly. | |

**User's choice:** Migrate first, then delete shims
**Notes:** None

---

## Legacy Fallback Elimination Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Two-step: assert first, then remove | First add the assertion test proving production configs don't hit the legacy path (with the legacy code still present). Validate the test passes. Then remove the legacy code in a second step. This gives confidence before deletion. | Y |
| One-shot: remove and test together | Remove the legacy fallback path and add a test that verifies production configs always have structured `CrashgenEntry` rules. The test validates the precondition rather than the fallback. | |
| You decide | Claude picks the approach based on what the code reveals about how the fallback is triggered. | |

**User's choice:** Two-step: assert first, then remove
**Notes:** None

---

## Claude's Discretion

- Order of deletion within the phase
- Exact test structure for migrated deprecated shim tests
- PyGpuDetector constructor changes for stateless conversion
- Whether removing `SEGMENT_BOUNDARIES` also removes unused `once_cell::sync::Lazy` import

## Deferred Ideas

None -- discussion stayed within phase scope.
