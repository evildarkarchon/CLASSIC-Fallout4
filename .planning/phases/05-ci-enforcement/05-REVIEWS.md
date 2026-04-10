---
phase: 5
reviewers: [claude, codex]
reviewed_at: 2026-04-09
review_round: 1
plans_reviewed: [05-01-PLAN.md, 05-02-PLAN.md]
---

# Cross-AI Plan Review -- Phase 5

## Claude Review

### Plan 01: CXX Gate CI Job + Triple-Gate Assertion Script

**Summary:** A well-scoped plan that adds one CI job (4 YAML steps) and one Python script to wire all three parity gates into enforcement. The plan correctly mirrors existing patterns from `ci-python-bindings.yml` and avoids over-engineering. The triple-gate script design is sound with proper `try/finally` cleanup. One actionable defect in the verification command, but overall this is low-risk work on a well-trodden path.

**Strengths:**
- Exact template fidelity: The CXX gate job structure precisely mirrors the existing Python gate in `ci-python-bindings.yml:14-39`, including the diagnostic upload pattern
- `needs:` dependency coverage is explicit: Both `cli-tests` AND `gui-tests` are called out individually
- `sys.executable` over bare `"python"`: The script correctly avoids the Windows PATH resolution pitfall
- Canary injection target is well-chosen: `classic-shared-core/src/lib.rs` is the foundation crate
- CI-06 handled correctly as no-op: The CXX gate script's `artifacts_match()` function already checks freshness
- Diagnostic artifact upload included: Good use of discretion, mirrors existing pattern

**Concerns:**
- **HIGH**: Verification command requires `pyyaml` which is not installed. Task 1's automated verify uses `import yaml` -- the project has NO `pyyaml` dependency. This verification step **will fail** during execution. Replace with stdlib-only string/regex check.
- **MEDIUM**: Node gate `--deferred-registry` default path dependency. After Phase 6 deletes governance files, re-running the triple-gate test will fail for infrastructure reasons (file-not-found), not because of canary detection. The script would incorrectly report PASS.
- **LOW**: No timeout on subprocess calls in triple-gate script. Consider `timeout=120` for safety.
- **LOW**: `submodules: recursive` not needed for CXX gate -- correctly omitted but could confuse future readers.

**Suggestions:**
- Replace Task 1 `<verify><automated>` with stdlib-only Python check (no `import yaml`). **Blocking.**
- Add comment in triple-gate script noting `deferred_runtime_backlog.json` must exist (Phase 6 dependency)
- Consider adding `timeout=300` to each `subprocess.run()` call
- Verify the job does NOT use `submodules: recursive` in checkout

**Risk Assessment:** LOW -- with the pyyaml fix applied.

### Plan 02: CI Run Verification + Branch Protection

**Summary:** Appropriately scoped manual verification plan. Correctly identifies CI-04 requires a human action and structures it as `checkpoint:human-verify` with clear instructions. The `autonomous: false` flag is correct.

**Strengths:**
- Correct sequencing: depends on Plan 01 (`depends_on: ["05-01"]`)
- D-13 timing handled correctly: explicit about CXX gate completing at least one run first
- Observational CI-01/CI-02 verification is appropriate
- Clear human instructions with correct status check name ("CXX Parity Gate" not `cxx-parity-gate`)
- No over-automation: respects D-11 manual configuration decision

**Concerns:**
- **MEDIUM**: `gh api` verification command has `{owner}/{repo}` template placeholders. Will return 404 if left as-is.
- **LOW**: No "what if the first CI run fails" contingency
- **LOW**: No distinction between "already present" and "newly added" checks for Python/Node

**Suggestions:**
- Replace `{owner}/{repo}` with actual repo path or use `gh api repos/:owner/:repo/...` auto-fill
- Add note: "If the CXX Parity Gate CI job fails on first run, fix the workflow YAML before configuring branch protection"
- Consider a final end-to-end verification: test branch with canary pub fn, open PR, confirm all three gates block merge

**Risk Assessment:** LOW -- manual configuration work with clear instructions.

**Overall Phase Risk:** LOW

---

## Codex Review

### Plan 01: CXX Gate CI Job + Triple-Gate Assertion Script

**Summary:** Plan 01 is mostly well-scoped and aligns with the repository's actual workflow patterns. The main weakness is in verification quality: the proposed triple-gate test proves "all three gates are non-zero after injection," but it does not prove the canary caused the failures unless it first establishes a clean baseline.

**Strengths:**
- Mirrors existing CI structure correctly: lightweight parity gate job first, expensive downstream jobs gated with `needs:`
- Keeps scope tight to two code artifacts for this wave
- Correctly reuses the existing CXX gate for both drift detection and stale-artifact freshness
- Uses `sys.executable`, the right Windows-safe choice
- Treats the triple-gate script as local-only
- Optional diagnostics upload is consistent with existing pattern

**Concerns:**
- **HIGH**: The triple-gate script can false-pass if one or more gates are already failing before the canary injection. As written, it only checks for non-zero after mutation, not a `0 -> non-zero` transition.
- **MEDIUM**: The script does not guard against `_ci05_canary` already existing in `lib.rs`
- **MEDIUM**: The YAML verification command depends on `import yaml` (PyYAML), not part of stdlib
- **MEDIUM**: Plan output requires `05-01-SUMMARY.md` but not listed in `files_modified`
- **LOW**: CI-01/CI-02 evidence path should be more explicit

**Suggestions:**
- Add a preflight step that runs all three gates before mutation and fails unless all return 0
- Add a collision guard: abort if `_ci05_canary` already exists in the target file
- Replace PyYAML-based verify with stdlib-only check
- Add explicit task to create `05-01-SUMMARY.md`

**Risk Assessment:** MEDIUM -- verification logic can produce false sense of correctness unless it proves the canary flips the gates.

### Plan 02: CI Run Verification + Branch Protection

**Summary:** Plan 02 has the right intent. The core issue is sequencing: the plan says to merge the PR first and then configure branch protection. That creates a real merge window where the new gate exists but is not yet required.

**Strengths:**
- Correctly recognizes branch protection is a manual GitHub configuration step
- Uses exact status-check display names (not job IDs)
- Separates CI-04 into human-controlled checkpoint
- Verifies Python and Node gates observationally

**Concerns:**
- **HIGH**: The sequence "merge first, protect immediately after" creates a gap and does not meet the "same PR" requirement
- **HIGH**: The `gh api` verification command has unresolved `{owner}/{repo}` placeholders and uses `2>/dev/null` (bash syntax, not PowerShell)
- **MEDIUM**: `files_modified: []` but output requires `05-02-SUMMARY.md`
- **MEDIUM**: No contingency for rulesets instead of classic branch protection, or missing admin permission
- **LOW**: Should capture exact check names confirmed green

**Suggestions:**
- Change sequence: open PR, wait for first successful CXX gate run on the PR, add required checks while PR is still open, then merge
- Drop or fix the `gh api` verify command for PowerShell compatibility
- Add fallback note for GitHub rulesets or insufficient admin rights
- Add explicit task to write `05-02-SUMMARY.md` with evidence

**Risk Assessment:** HIGH -- current sequencing does not actually close CI-04 and can leave an enforcement gap.

---

## Consensus Summary

### Agreed Strengths
- CXX gate job structure correctly mirrors existing Python/Node patterns (both reviewers)
- `sys.executable` is the right choice for Windows (both reviewers)
- Keeping triple-gate script as local-only is correct (both reviewers)
- Scope is tight and focused (both reviewers)
- CI-06 handled as no-op via existing stale-artifact detection (both reviewers)
- Branch protection as human checkpoint is appropriate (both reviewers)
- Status check names vs job IDs correctly handled (both reviewers)

### Agreed Concerns
1. **HIGH -- PyYAML dependency in verify command** (both reviewers): Task 1's automated verify uses `import yaml` which is not installed. Replace with stdlib-only string/regex check. **Blocking -- will fail during execution.**
2. **HIGH -- Triple-gate script needs preflight baseline** (Codex HIGH, Claude implicit): The script should verify all three gates pass BEFORE canary injection, not just check they fail AFTER. Without this, pre-existing gate failures produce false PASS results.
3. **MEDIUM-HIGH -- `gh api` verify command broken** (both reviewers): Unresolved `{owner}/{repo}` placeholders; Claude notes auto-fill option, Codex notes bash/PowerShell syntax mismatch.
4. **MEDIUM -- Node gate Phase 6 dependency** (Claude MEDIUM): After Phase 6 deletes governance files, the triple-gate test's Node invocation will fail for infrastructure reasons, not canary detection.

### Divergent Views
1. **Plan 02 sequencing / CI-04 gap**: Codex rates this HIGH (merge-first creates enforcement gap); Claude rates the plan LOW overall and says D-13 timing is handled correctly. The disagreement centers on whether "merge then immediately protect" satisfies CI-04's "same PR" wording. CONTEXT.md D-13 explicitly chose "after first successful run" -- both reviewers should be evaluated against this locked decision.
2. **Plan 02 risk level**: Claude says LOW (manual config, easily correctable); Codex says HIGH (sequencing flaw). The divergence reflects different interpretations of how strictly "same PR" should be read given the GitHub constraint that checks must complete once before they can be required.

---

*Review completed: 2026-04-09*
*Reviewers: Claude CLI (separate session), Codex CLI*
