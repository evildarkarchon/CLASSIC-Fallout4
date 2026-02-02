---
status: resolved
trigger: "grep -r DEPRECATED ClassicLib/ --include=*.py -l returns FormIDAnalyzer.py - Phase 1 success criterion failure"
created: 2026-02-01T00:00:00Z
updated: 2026-02-01T00:00:00Z
---

## Investigation Summary

**Finding:** FormIDAnalyzer.py contains "DEPRECATED" markers in docstrings, NOT deprecated code to be removed in Phase 1.

**Conclusion:** **OUT OF SCOPE for Phase 1**. This is a **Phase 4 target**, correctly marked for future removal.

---

## Evidence

### What "DEPRECATED" Text Exists

**File:** `ClassicLib/scanning/logs/analyzers/FormIDAnalyzer.py`

**Lines 114-115:**
```python
        DEPRECATED: Use FormIDAnalyzerCore directly in async contexts.
        This sync wrapper only works in GUI mode and will error in CLI/TUI mode.
```

**Lines 137-138:**
```python
        DEPRECATED: Use FormIDAnalyzerCore directly in async contexts.
        This sync wrapper only works in GUI mode and will error in CLI/TUI mode.
```

### What the File Is

`FormIDAnalyzer.py` is an **active, live sync wrapper class** that:
- **Is NOT deprecated code** (not dead code to be removed)
- **Contains deprecation warnings** describing its future removal
- Provides GUI-compatible synchronous methods wrapping FormIDAnalyzerCore async methods
- Uses `create_sync_wrapper(strict=True)` for Phase 2 context-aware bridging

**Architecture:**
- `FormIDAnalyzerCore` = async-first implementation (production/CLI/TUI)
- `FormIDAnalyzer` = sync wrapper for GUI contexts only (backward compatibility)

### Phase Scope Analysis

**Phase 1 (Foundation Cleanup) targets:**
- Dead code with zero callers (`database_rust.py`)
- Deprecated code blocks within mixed files (`constants.py` deprecated version block)
- **Criterion:** "No file contains DEPRECATED markers after cleanup"

**Phase 4 (Interface Consolidation) targets:**
- Sync wrapper removal (`FormIDAnalyzer.py`)
- YAML sync/async consolidation
- Bridge helper removal
- **Success criterion:** "FormIDAnalyzer.py sync wrapper file does not exist"

### Why This Is Correct

From `.planning/phases/01-foundation-cleanup/01-RESEARCH.md`:
> "there are actually 2 clearly deprecated modules (one file with deprecated re-exports, one file with deprecated version constants)"

The two Phase 1 targets were:
1. `ClassicLib/io/database/database_rust.py` (deleted)
2. `ClassicLib/core/constants.py` deprecated block (removed)

From `.planning/ROADMAP.md` Phase 4 success criteria:
> "FormIDAnalyzer.py sync wrapper file does not exist (156-line deprecated wrapper removed)"

**FormIDAnalyzer.py is explicitly scoped to Phase 4.**

---

## Interpretation of Phase 1 Success Criterion

**Original criterion:**
> "`grep -r 'DEPRECATED' ClassicLib/ --include='*.py' -l` returns 0 files"

**Problem:** This criterion is **overly broad**. It was intended to verify removal of:
- Files marked as entirely deprecated (dead code)
- Code blocks marked DEPRECATED within mixed files

**It was NOT intended to catch:**
- Docstring deprecation warnings about future Phase 4 work
- Active code with deprecation notices for users

**Evidence this is a criterion bug:**
- Phase 1 research identified exactly 2 deprecated targets
- Both were removed successfully
- FormIDAnalyzer.py was never mentioned in Phase 1 plans
- FormIDAnalyzer.py is explicitly listed as Phase 4 scope in ROADMAP.md

---

## Recommendation

### Option 1: Refine Phase 1 Criterion (Recommended)

**Change from:**
```
`grep -r "DEPRECATED" ClassicLib/ --include="*.py" -l` returns 0 files
```

**Change to:**
```
No deprecated modules or code blocks remain per Phase 1 scope (database_rust.py deleted, constants.py block removed)
```

**Rationale:**
- Reflects actual Phase 1 scope
- Doesn't conflate dead code removal with future architectural work
- Allows deprecation warnings to exist for Phase 4 targets

### Option 2: Exclude Phase 4 Targets from Grep

**Add to Phase 1 verification:**
```bash
# Verify no DEPRECATED markers except Phase 4 targets
grep -r "DEPRECATED" ClassicLib/ --include="*.py" -l | grep -v "FormIDAnalyzer.py"
```

**Rationale:**
- Keeps the grep-based verification
- Explicitly excludes known future work

### Option 3: Accept Phase 1 as Complete (Alternative)

**Argument:**
- Phase 1 successfully removed the 2 identified deprecated targets
- FormIDAnalyzer.py is documented as Phase 4 scope
- The criterion was a verification mechanism, not the goal itself
- The actual goal (remove dead code) is complete

---

## Resolution

**Status:** Phase 1 is **functionally complete**. The grep criterion caught a **false positive**.

**Action Required:** None for Phase 1 code. Update Phase 1 verification criterion to match actual scope (Option 1 recommended).

**Root Cause:** Phase 1 success criterion was overly broad, using a text search that couldn't distinguish between:
- Deprecated code to remove NOW (Phase 1 scope)
- Active code marked for removal LATER (Phase 4 scope)

**Files Involved:**
- `.planning/phases/01-foundation-cleanup/01-01-PLAN.md` - Verification criterion line 79
- `.planning/phases/01-foundation-cleanup/01-VERIFICATION.md` - If it exists and contains the same criterion

**Phase 4 Work:** FormIDAnalyzer.py removal is correctly scoped and documented in ROADMAP.md Phase 4 plan 04-01.
