# Phase 1: Deprecated API Migration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 01-deprecated-api-migration
**Areas discussed:** Return type migration, Deprecation warning strategy, Lint handling, Test migration ambition

---

## Return Type for `parse_segments_parallel`

| Option | Description | Selected |
|--------|-------------|----------|
| Keep `list[list[str]]` return | Convert named dict back to positional list internally. Preserves backward compat until Phase 2 deletion. | |
| Change to `dict[str, list[str]]` | Return named sections directly, matching `parse_all_sections_arc`. Breaks positional callers but method is deleted in Phase 2 anyway. | ✓ |
| You decide | Claude picks simplest approach. | |

**User's choice:** Change to `dict[str, list[str]]`
**Notes:** Short breakage window since method is deleted in Phase 2. Cleaner alignment with the new API.

---

## Deprecation Warnings on Legacy Python Methods

| Option | Description | Selected |
|--------|-------------|----------|
| Warn on all three legacy methods | `parse_segments_parallel`, `generate_suspect_section`, and FormID `new` all emit `DeprecationWarning` pointing to replacement API. | ✓ |
| Warn only on FormID (DEBT-10) | Other two methods silently delegate. Less noise for soon-to-be-removed methods. | |
| You decide | Claude picks based on PyO3 conventions. | |

**User's choice:** Warn on all three legacy methods
**Notes:** Consistent deprecation surface -- every legacy path tells callers to migrate.

---

## `deprecated = "deny"` Lint Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Surgical `#[allow(deprecated)]` | Keep workspace lint at `deny`. Each migration call site gets temporary `#[allow(deprecated)]` removed after replacement. | ✓ |
| Temporary workspace `warn` | Relax to `warn` at phase start, restore `deny` at end. Simpler but weakens lint workspace-wide. | |
| You decide | Claude picks best sequencing approach. | |

**User's choice:** Surgical `#[allow(deprecated)]`
**Notes:** Keeps the workspace lint tight throughout. No risk of new deprecated usages slipping in.

---

## Test Migration Ambition

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal rewrite | Convert three `is_outdated` tests to equivalent `check_version_status` assertions. Quick, literal DEBT-07 compliance. | |
| Delete the three tests entirely | Existing `check_version_status` tests already cover same scenarios. Avoids redundant cases. | |
| Expand coverage | Rewrite tests AND add VR-specific `NewerThanKnown`, empty valid lists in VR mode, and other edge cases. | ✓ |

**User's choice:** Expand coverage
**Notes:** Use the migration as an opportunity to strengthen the test suite with VR-specific and edge case scenarios.

---

## Claude's Discretion

- Exact deprecation warning message wording
- Internal conversion logic for `generate_suspect_section` -> header + footer delegation
- Specific expanded VR test scenarios
- Migration ordering within the phase

## Deferred Ideas

None -- discussion stayed within phase scope.
