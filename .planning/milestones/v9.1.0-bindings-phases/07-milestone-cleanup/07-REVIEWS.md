---
phase: 7
reviewers: [claude, codex]
reviewed_at: 2026-04-10
plans_reviewed: [07-01-PLAN.md]
---

# Cross-AI Plan Review — Phase 7

## Claude Review

This is a high-quality, low-risk cleanup plan that addresses all 6 milestone audit success criteria with surgical precision. The research phase correctly identified the current state of every target file, including the critical subtlety that SC-5 is pre-satisfied. The plan consolidates 6 independent file edits into 3 well-scoped tasks with concrete acceptance criteria backed by grep commands. The tier2 cleanup in Task 2 is the most complex part and is handled thoroughly, including the Python historical comment (pitfall 1) and the Node reporting function vestiges (pitfall 4). The plan correctly preserves CI-04 as Deferred rather than Complete.

### Strengths

- Thorough research-to-plan traceability: Every grep hit from research maps to a specific line-level edit in the plan. The 8 Python hits and 7+1 Node hits are all accounted for.
- CI-04 handling is correct and well-guarded: Explicitly marked as "DO NOT change" in the action block, and the acceptance criteria includes a dedicated check (`grep -c "\[ \] \*\*CI-04\*\*"` returns 1).
- SC-5 pre-satisfaction handled cleanly: The plan includes a verify-then-skip strategy rather than making an unnecessary edit to ROADMAP.md.
- Acceptance criteria go beyond the success criteria: Task 2 includes a case-insensitive check (`grep -ci "tier.2"`) to catch Node line 565's `Tier-2` (uppercase T) which the phase's case-sensitive SC-3 criterion would miss. Good defense-in-depth.
- Python syntax validation: Both generator files get `ast.parse()` checks post-edit, catching potential indentation or trailing-comma issues from multi-line ternary removal.
- No scope creep: The plan does not touch any functional code, build systems, or parity gates themselves.
- Single wave, autonomous execution: Appropriate for the risk level.
- Explicit `read_first` directives: Each task specifies which files to read and which lines to inspect before editing.

### Concerns

- **LOW** -- Research line number discrepancy for SC-2: The research document says "line 19" for the wrong CXX baseline path, but the actual file shows it on line 20. The plan correctly says "line 20", so execution won't be affected.
- **LOW** -- Node line 565 grep pattern nuance: SC-3 uses case-sensitive `grep -c "tier.*2"`. Line 565 contains `Tier-1 + Tier-2` (uppercase T), which does NOT match the case-sensitive pattern. The plan fixes it anyway (good), but the acceptance criteria's case-insensitive check is stricter than what the success criterion demands.
- **LOW** -- Node generator grep count discrepancy: The research claims "8 grep hits" for the Node generator, but case-sensitive `grep -c "tier.*2"` returns only 7. Line 565 only matches case-insensitively.
- **LOW** -- DOC-01 traceability table already shows "Complete": The plan changes the DOC-01 checkbox but not the table row (correct behavior, since the table row is already correct). Could be more explicit about why.
- **LOW** -- `Last updated` date is hardcoded to 2026-04-10: If execution slips, the timestamp will be stale.

### Suggestions

- Add a post-edit verification for DOC-01 table row consistency
- Consider running `ruff format` on both Python files post-edit to catch formatting drift from multi-line ternary removal
- Fix the research document's line-number discrepancy (line 19 -> line 20)
- Use `$(date +%Y-%m-%d)` or equivalent for the last-updated timestamp

### Risk Assessment: LOW

All edits are to documentation, markdown tracking files, Python string literals, and Rust doc comments. Zero functional code is modified. The verification suite is comprehensive. Worst-case failure: a multi-line ternary removal introduces a Python syntax error, caught immediately by `ast.parse()`.

---

## Codex Review

Plan `07-01` is well-scoped and largely complete for the actual Phase 7 cleanup work. It hits all six audited success criteria, correctly treats `CI-04` as deferred rather than complete, and resolves the real repo paths instead of the shorthand wording in the roadmap. The main weakness is not task coverage but verification quality: several grep checks are too loose to prove the intended rows changed, and the generator cleanup is only syntax-checked rather than exercised end-to-end.

### Strengths

- The plan maps cleanly to all six success criteria with no obvious missing file.
- `CI-04` handling is correct: it stays unchecked in the checklist and becomes `Deferred` in traceability.
- It correctly recognizes `SC-5` as verify-only, avoiding unnecessary edits to the roadmap.
- Task 2 accounts for all known `tier.*2` hits, including the Python historical comment and the Node reporting text beyond the raw ternaries.
- The plan resolves the real repo targets correctly.
- Scope is appropriately narrow for a cleanup phase; it does not drift into broader parity or architecture work.

### Concerns

- **MEDIUM** -- The ROADMAP verification for Phase 1 is too weak. `grep "3/3" .planning/ROADMAP.md | head -1` can match unrelated archived rows, not specifically the active-milestone Phase 1 row.
- **MEDIUM** -- The binding policy verification is too weak. `grep "parity_contract.json"` will match the existing Python and Node baseline lines even if the CXX line stays wrong.
- **MEDIUM** -- Task 2 only proves Python syntax / zero grep hits, not that the modified generators still run correctly. Removing `tier2_count` and related strings could still leave a runtime bug in rendering paths that syntax parsing would miss.
- **LOW** -- The `tier.*2` acceptance check is case-sensitive and pattern-specific. It proves the exact roadmap grep criterion, but it does not fully prove all vestigial "Tier 2" wording is gone in alternate casing/punctuation.
- **LOW** -- The plan updates the `Last updated` footer in `.planning/REQUIREMENTS.md`, which is reasonable, but outside the explicit success criteria.
- **LOW** -- The plan does not say whether generated parity artifacts should be refreshed after changing generator output behavior.

### Suggestions

- Tighten ROADMAP verification to the exact row, e.g. `| 1. CXX Parity Gate Tooling | 3/3 | Complete |`
- Tighten binding-policy verification to the CXX line specifically, and also assert `cxx_baseline_surface.json` is absent
- After Task 2, run the generator scripts themselves, not just `ast.parse`:
  - `python tools/python_api_parity/generate_baseline.py --repo-root .`
  - `python tools/node_api_parity/generate_baseline.py --repo-root .`
- Add one explicit note on generated artifacts: either "refresh not required" or "refresh if generator output changes"
- Use `grep -F` or more anchored regexes for exact table-row checks

### Risk Assessment: LOW

The implementation risk is low because the plan is narrow, the affected files are mostly docs/tooling comments/labels, and `CI-04` is handled correctly. The only real weakness is verification rigor around Task 2 and the loose grep checks.

---

## Consensus Summary

### Agreed Strengths

- **All 6 success criteria are covered** -- both reviewers confirm complete mapping from SC-1 through SC-6 to plan tasks
- **CI-04 handling is correct** -- both reviewers independently verified that CI-04 stays Deferred/unchecked, not Complete
- **SC-5 pre-satisfaction handled cleanly** -- verify-only approach avoids unnecessary edits
- **Tier2 cleanup is comprehensive** -- all grep hits (Python comment, Node reporting vestiges) are accounted for
- **Appropriate scope** -- no scope creep into functional code or parity gates

### Agreed Concerns

- **Verification grep patterns are too loose** (Claude: LOW, Codex: MEDIUM) -- both reviewers note that `grep "3/3"` and `grep "parity_contract.json"` could match unintended rows. Codex specifically flags ROADMAP and binding-policy greps as too weak.
- **Generator runtime not exercised** (Codex: MEDIUM) -- `ast.parse()` catches syntax errors but not runtime rendering bugs from removed `tier2_count` variables. Both reviewers suggest running the generators end-to-end.

### Divergent Views

- **Severity of loose greps**: Claude rates all concerns LOW (the individual acceptance criteria catch the specifics even if the automated verify is loose). Codex rates the loose greps as MEDIUM (the automated verify should be self-sufficient).
- **ruff format suggestion**: Claude suggests running `ruff format` post-edit. Codex does not mention formatting but suggests running the generators themselves.
- **Generated artifacts refresh**: Codex flags that the plan should explicitly state whether generated parity artifacts need refreshing. Claude does not raise this.
