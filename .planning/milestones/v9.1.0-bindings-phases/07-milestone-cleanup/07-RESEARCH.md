# Phase 7: Milestone Cleanup - Research

**Researched:** 2026-04-10
**Domain:** Documentation/tracking artifact cleanup (no code logic changes)
**Confidence:** HIGH

## Summary

Phase 7 is a pure cosmetic and tracking cleanup phase. The milestone audit (`v9.1.0-bindings-MILESTONE-AUDIT.md`) identified 14 tech debt items across 5 phases. This phase closes all items that are documentation, label, comment, and traceability fixes -- no functional code changes are involved.

All 6 success criteria have been investigated. Each involves a specific file edit with a concrete before/after value. The changes are small, isolated, and independently verifiable with grep or visual inspection. There is zero risk of build breakage or parity gate regression since no Rust, Python, Node, or C++ runtime code is modified (only doc comments, Python string literals in baseline generators, and markdown tracking files).

**Primary recommendation:** Execute all 6 fixes in a single plan with one task per success criterion. No waves needed -- all edits are independent.

## Project Constraints (from CLAUDE.md)

- Commit prefix convention: `Docs:`, `Fix:`, `Refactor:`, `Chore:` etc. -- this phase should use `Chore:` or `Docs:` prefix
- Never output to `nul` on Windows
- Use PowerShell wrappers for C++ tests (not applicable -- no C++ tests needed)
- Pre-commit: `cargo fmt` and `ruff format` (not applicable -- no Rust/Python logic changes, only string edits)
- Trailing whitespace is intentionally NOT trimmed in markdown files

## Current vs. Expected State (All 6 Success Criteria)

### SC-1: REQUIREMENTS.md Traceability Staleness

**File:** `.planning/REQUIREMENTS.md`

**Current state (checkboxes, lines 60-65):**
```markdown
- [ ] **CI-01**: The Python parity gate runs in CI on every PR...
- [ ] **CI-02**: The Node parity gate runs in CI on every PR...
- [ ] **CI-03**: A new CI job runs `tools/cxx_api_parity/check_parity_gate.py`...
- [ ] **CI-04**: The new C++ parity gate is added to branch-protection required checks...
- [ ] **CI-05**: All three parity gates are wired into CI...
- [ ] **CI-06**: A `.gitignore`-respecting freshness gate...
```

**Current state (DOC-01 checkbox, line 69):**
```markdown
- [ ] **DOC-01**: Python and Node parity gate scripts make the deferred-registry...
```

**Current state (traceability table, lines 142-147):**
```markdown
| CI-01 | Phase 5 | Pending |
| CI-02 | Phase 5 | Pending |
| CI-03 | Phase 5 | Pending |
| CI-04 | Phase 5 | Pending |
| CI-05 | Phase 5 | Pending |
| CI-06 | Phase 5 | Pending |
```

**Expected state (checkboxes):**
```markdown
- [x] **CI-01**: ...
- [x] **CI-02**: ...
- [x] **CI-03**: ...
- [ ] **CI-04**: ...  (remains unchecked -- user-deferred)
- [x] **CI-05**: ...
- [x] **CI-06**: ...
- [x] **DOC-01**: ...
```

**Expected state (traceability table):**
```markdown
| CI-01 | Phase 5 | Complete |
| CI-02 | Phase 5 | Complete |
| CI-03 | Phase 5 | Complete |
| CI-04 | Phase 5 | Deferred |
| CI-05 | Phase 5 | Complete |
| CI-06 | Phase 5 | Complete |
```

**Also update:** `*Last updated:` line at bottom from `2026-04-06` to `2026-04-10`.

---

### SC-2: Wrong CXX Baseline Path in binding-parity-policy.md

**File:** `docs/api/binding-parity-policy.md`

**Current state (line 19):**
```markdown
- **Baseline:** `tools/cxx_api_parity/cxx_baseline_surface.json`
```

**Expected state:**
```markdown
- **Baseline:** `docs/implementation/cxx_api_parity/baseline/parity_contract.json`
```

**Verification:** The actual baseline file exists at `docs/implementation/cxx_api_parity/baseline/parity_contract.json` (confirmed via glob). The path `tools/cxx_api_parity/cxx_baseline_surface.json` does not exist.

---

### SC-3: Vestigial tier2 Labels in Baseline Generators

**File 1:** `tools/python_api_parity/generate_baseline.py`

7 active tier2 label sites at lines 277, 294, 312, 330, 419, 473, 506.

Each follows the pattern:
```python
"tier": "tier1" if symbol in tier1_rust_symbols else "tier2",
```

**Expected:** Since all entries are now Tier-1 (Phase 3 promoted everything), the fallback `"tier2"` label is vestigial. Replace with unconditional `"tier1"` assignment OR keep the ternary but change the else-branch to `"tier1"` (effectively making it always tier1).

**Recommended approach:** Replace each occurrence with:
```python
"tier": "tier1",
```

This is the cleanest fix. The `tier1_rust_symbols` / `tier1_python_exports` sets are still used elsewhere for contract matching, so only the `"tier"` field assignment changes.

**Note:** Lines 672-677 contain a comment that references "Tier-2 gap emission branches" -- this is an explanatory comment about *why* those branches were removed, and does NOT emit `tier2` labels. The grep pattern `tier.*2` matches it, but this is a historical note, not a vestigial label. **The success criterion is `grep -c "tier.*2"` returning 0**, so this comment ALSO needs to be removed or reworded to avoid the pattern match.

**File 2:** `tools/node_api_parity/generate_baseline.py`

5 active tier2 label sites at lines 228, 246, 264, 282, 382.

Same pattern as Python -- each uses:
```python
"tier": "tier1" if symbol in tier1_rust_symbols else "tier2",
```
or:
```python
"tier": "tier1" if name in tier1_node_exports else "tier2",
```

3 additional tier2 references in reporting functions:
- Line 565: `f"- Total gaps (Tier-1 + Tier-2): **{summary['total_gaps']}**"`
- Line 639: `tier2_count = sum(1 for gap in module_gaps if gap["tier"] == "tier2")`
- Line 646: `f"- Tier 2 gaps: **{tier2_count}**"`

**Expected:** Replace all label assignments with `"tier": "tier1",`. For the reporting lines:
- Line 565: Change to `f"- Total gaps: **{summary['total_gaps']}**"` (remove tier language)
- Lines 639-646: Remove the `tier2_count` variable and its display line entirely

---

### SC-4: Stale Governance Comment in test_triple_gate_failure.py

**File:** `tools/test_triple_gate_failure.py`

**Current state (lines 40-44):**
```python
# NOTE: The Node gate requires
# docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json
# to exist. Phase 6 (Documentation Reset) will make the --deferred-registry
# argument optional before deleting governance files. If this script fails on
# the Node gate after Phase 6, verify DOC-01 was applied.
```

**Expected:** Remove these 5 comment lines entirely. DOC-01 was applied in Phase 6; the governance files are deleted; the `--deferred-registry` argument is already optional. This comment is fully obsolete.

---

### SC-5: ROADMAP Progress Table Phase 1 and Phase 5

**File:** `.planning/ROADMAP.md`

**Current state (progress table, lines 171-179):**
```markdown
| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. CXX Parity Gate Tooling | 3/3 | Complete | 2026-04-07 |
...
| 5. CI Enforcement | 1/2 | Complete (CI-04 deferred) | 2026-04-09 |
```

**Analysis:** Phase 1 already shows "3/3" and Phase 5 already shows "1/2" with "Complete (CI-04 deferred)". The success criterion says the progress table should show "Phase 1 as '3/3 Complete' and Phase 5 as '1/2 Complete (CI-04 deferred)'". **This is already the case.** The milestone audit noted "Phase 1 progress row in ROADMAP says '1/3 Plans Complete'" but this appears to have been fixed between the audit and now (or the audit was examining a different location).

**Expected:** No change needed for the progress table. Verify at plan execution time and skip if already correct.

---

### SC-6: Stale "Placeholder" Doc Comment in scanner.rs

**File:** `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs`

**Current state (lines 1-5):**
```rust
//! Crash log scanning bridge for CXX FFI.
//!
//! Bridges `classic_scanlog_core::OrchestratorCore` for crash log analysis.
//! This is the PRIMARY FEATURE of the CLASSIC application.
//! Placeholder — will be implemented by Wave 2 agent.
```

**Expected state:**
```rust
//! Crash log scanning bridge for CXX FFI.
//!
//! Bridges `classic_scanlog_core::OrchestratorCore` for crash log analysis.
//! This is the PRIMARY FEATURE of the CLASSIC application.
```

Simply remove line 5 (`//! Placeholder -- will be implemented by Wave 2 agent.`). The module is fully implemented.

---

## Architecture Patterns

### Recommended Edit Organization

All 6 success criteria are independent file edits. They touch different files with no overlapping dependencies:

```
.planning/REQUIREMENTS.md         (SC-1: traceability + checkboxes)
docs/api/binding-parity-policy.md (SC-2: CXX baseline path)
tools/python_api_parity/generate_baseline.py (SC-3: tier2 labels)
tools/node_api_parity/generate_baseline.py   (SC-3: tier2 labels)
tools/test_triple_gate_failure.py (SC-4: stale comment)
.planning/ROADMAP.md              (SC-5: progress table -- verify-only)
ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs (SC-6: doc comment)
```

### Pattern: Single Plan, Sequential Tasks

Since all edits are small and independent, a single plan with one task per success criterion is appropriate. No wave structure needed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Automated tier label migration | Script to find-and-replace tier labels | Manual Edit tool changes at known line numbers | Only 7+8 sites total; scripting adds complexity for no value |

## Common Pitfalls

### Pitfall 1: grep -c "tier.*2" Matching Comments

**What goes wrong:** The Python baseline generator has a comment block (lines 672-677) that mentions "Tier-2" in a historical note. The success criterion uses `grep -c "tier.*2"` which will match this comment even though it is not a label assignment.
**Why it happens:** The grep pattern is intentionally broad to catch all vestiges.
**How to avoid:** Reword the comment to avoid the pattern (e.g., use "former deferred tier" instead of "Tier-2").
**Warning signs:** `grep -c` returns non-zero after fixing only the label assignments.

### Pitfall 2: CI-04 Should Remain Unchecked/Pending

**What goes wrong:** Accidentally marking CI-04 as Complete when it was explicitly user-deferred.
**Why it happens:** Batch editing CI-01 through CI-06 without reading the deferred status.
**How to avoid:** CI-04 stays `- [ ]` in the checkbox list. In the traceability table, change its status to `Deferred` (not `Complete`, not `Pending`).
**Warning signs:** Audit says "user-deferred" -- any other status is wrong.

### Pitfall 3: SC-5 May Already Be Correct

**What goes wrong:** Making an unnecessary edit to the ROADMAP progress table that introduces a diff for no reason.
**Why it happens:** The audit identified the issue, but it may have been fixed in a subsequent commit.
**How to avoid:** Verify current state before editing. If already correct, skip the edit and note in verification that it was pre-satisfied.

### Pitfall 4: Node Baseline Generator Has More tier2 Sites Than Audit Listed

**What goes wrong:** Fixing only the 3 sites listed in the audit frontmatter (L228/246/264/282/382) but missing the reporting function references at L565/639/646.
**Why it happens:** The audit yaml listed "3 vestigial tier2 references" but the actual count is 8 grep matches.
**How to avoid:** Use the full grep output from this research as the source of truth. Fix ALL sites that match `tier.*2`.

## Code Examples

### SC-1: REQUIREMENTS.md Checkbox Fix Pattern

```markdown
<!-- Before -->
- [ ] **CI-01**: The Python parity gate runs in CI...

<!-- After -->
- [x] **CI-01**: The Python parity gate runs in CI...
```

### SC-3: Tier Label Simplification Pattern

```python
# Before (7 sites in Python, 5 in Node)
"tier": "tier1" if symbol in tier1_rust_symbols else "tier2",

# After
"tier": "tier1",
```

### SC-3: Node Reporting Cleanup Pattern

```python
# Before (line 565)
f"- Total gaps (Tier-1 + Tier-2): **{summary['total_gaps']}**",

# After
f"- Total gaps: **{summary['total_gaps']}**",
```

```python
# Before (lines 639-646) -- remove these entirely
tier2_count = sum(1 for gap in module_gaps if gap["tier"] == "tier2")
...
f"- Tier 2 gaps: **{tier2_count}**",

# After -- remove both lines; keep tier1_count line if present
```

### SC-4: Comment Removal

```python
# Before (lines 40-44) -- remove these 5 lines entirely
# NOTE: The Node gate requires
# docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json
# to exist. Phase 6 (Documentation Reset) will make the --deferred-registry
# argument optional before deleting governance files. If this script fails on
# the Node gate after Phase 6, verify DOC-01 was applied.
```

### SC-6: Doc Comment Cleanup

```rust
// Before (line 5) -- remove this line
//! Placeholder — will be implemented by Wave 2 agent.
```

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | grep + visual inspection (no test framework needed) |
| Config file | N/A |
| Quick run command | `grep -c "tier.*2" tools/python_api_parity/generate_baseline.py tools/node_api_parity/generate_baseline.py` |
| Full suite command | Run all 6 success criteria verification commands |

### Phase Requirements -> Test Map

No formal requirement IDs for this phase (gap closure only). Verification is against the 6 success criteria:

| SC | Behavior | Test Type | Automated Command |
|----|----------|-----------|-------------------|
| SC-1 | CI-01/02/03/05/06 Complete, DOC-01 [x] | grep | `grep -E "CI-0[1-356].*Complete" .planning/REQUIREMENTS.md` |
| SC-2 | Correct CXX baseline path | grep | `grep "parity_contract.json" docs/api/binding-parity-policy.md` |
| SC-3 | No tier2 labels | grep | `grep -c "tier.*2" tools/python_api_parity/generate_baseline.py tools/node_api_parity/generate_baseline.py` returns 0 |
| SC-4 | No stale governance comment | grep | `grep -c "deferred_runtime_backlog" tools/test_triple_gate_failure.py` returns 0 |
| SC-5 | Progress table correct | visual | Already correct -- verify only |
| SC-6 | No Placeholder comment | grep | `grep -c "Placeholder" ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs` returns 0 |

### Wave 0 Gaps

None -- no test infrastructure needed. All verification is via grep commands.

## Environment Availability

Step 2.6: SKIPPED (no external dependencies identified). This phase is purely code/config/doc edits with no build or runtime requirements.

## Sources

### Primary (HIGH confidence)
- Direct file reads of all 7 target files in the repository
- `.planning/v9.1.0-bindings-MILESTONE-AUDIT.md` -- the authoritative gap list
- grep results against `tools/python_api_parity/generate_baseline.py` and `tools/node_api_parity/generate_baseline.py`
- glob results confirming actual CXX baseline path at `docs/implementation/cxx_api_parity/baseline/parity_contract.json`

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no libraries involved; pure file edits
- Architecture: HIGH -- all files read, all current values documented
- Pitfalls: HIGH -- all edge cases identified from direct source inspection

**Research date:** 2026-04-10
**Valid until:** 2026-05-10 (stable -- tracking artifacts don't change unless plans run)
