---
phase: 6
reviewers: [claude, codex]
reviewed_at: "2026-04-10T06:15:00-05:00"
plans_reviewed: [06-01-PLAN.md, 06-02-PLAN.md]
review_round: 1
---

# Cross-AI Plan Review — Phase 6

## Claude Review

### Plan 06-01: Gate Script Cleanup + Promotion Audit Trail

**Summary**

A well-specified plan that surgically removes all deferred-registry logic from three Python scripts, deletes three dead Tier-2 scripts, and creates an audit trail archiving all 8 governance files. Line numbers and variable names are verified accurate against source. The plan correctly satisfies the D-19 ordering constraint (gate cleanup + audit trail before any governance deletion). One significant gap: running the gate scripts as verification will regenerate parity artifact files (removing the "deferred" column), but those artifact changes are neither mentioned in the plan nor listed in `files_modified`.

**Strengths**

- Line-number accuracy is excellent. Every line reference in the shared helper and both gate scripts verified correct against live source.
- Acceptance criteria are thorough and mechanically verifiable. Negative assertions ("does NOT contain the string") plus positive gate-exit-zero checks cover both the deletion and the liveness aspects.
- The `VALID_CLASSIFICATIONS` cleanup is correctly scoped. Removing `"deferred"` while keeping `"runtime_verified"`, `"contract_mapped"`, `"newly_uncovered"` matches the post-Phase-3/4 reality.
- Dead script deletion list is complete. All three Tier-2 scripts exist and are correctly identified as dead.
- Audit trail structure (D-01 through D-05) is faithfully reflected.

**Concerns**

- **HIGH: Parity artifact regeneration not accounted for.** Running the gate scripts writes updated `runtime_coverage_summary.json`, `runtime_coverage_summary.md`, `parity_diff_report.json`, `parity_diff_report.md`, and `tier1_gate_report.md` to parity-artifacts directories. The Python artifacts currently contain entries classified as `"deferred"` — after the plan's changes, these will be regenerated without the "deferred" column. These files are committed artifacts and `files_modified` omits them entirely. The executor may produce uncommitted parity artifact changes. **Fix:** Add the parity artifact directories to `files_modified`, and add a note to stage regenerated artifacts after gate runs.
- **MEDIUM: Large-file audit trail creation strategy is implicit.** The Python `tier2_wave_manifest.json` is ~13,253 lines. Task 2 instructs the executor to read each governance file and concatenate it, but reading a 13K-line JSON file through the Read tool may stress the executor's context window. A pragmatic alternative (bash concatenation with markdown headers) would be more reliable.
- **LOW: No mention of `runtime_coverage_registry.json` stale entries.** Registry files may still contain `"classification": "deferred"` entries. After removing `"deferred"` from `VALID_CLASSIFICATIONS`, these entries could fail classification validation.

**Suggestions**

- Add parity artifact directories to `files_modified` and tell executor to stage any changes produced by gate verification runs.
- Add a brief executor hint for Task 2: use bash concatenation for the large JSON manifests rather than Read tool.
- Add a defensive pre-check: `grep -c '"deferred"'` against the runtime coverage registry JSON files.

**Risk Assessment:** LOW-MEDIUM.

### Plan 06-02: Governance Deletion + Doc Rewrite + New Docs

**Summary**

A comprehensive plan covering governance file deletion, three new/rewritten doc files, and cross-reference cleanup. Technical references to error-handling source code are verified accurate with one factual error in the `FormIdEntryDto` description that would propagate to the error-contract doc. The automated verification commands have a filesystem vs git-tracking edge case.

**Strengths**

- Dependency ordering is correctly enforced. `depends_on: [06-01]` plus explicit `read_first` of the audit trail ensures D-19 is satisfied.
- Error-contract source examples are real and verified: `db_pool_get_entry()` returns empty string, `config_error_to_napi_err()` exists, `config_error_to_pyerr()` exists, `define_exceptions!`/`ToPyErr` exist.
- The per-crate table mapping is reasonable and the plan instructs executor to verify from `lib.rs`.
- The `node-python-contract-map.md` fixes at lines 144, 146, 155, 158 are verified correct.
- Cross-reference hygiene is thorough.

**Concerns**

- **HIGH: `db_pool_get_entry_typed()` description is factually wrong.** The plan says it "returns a `FormIdEntryDto` with `status: "not_found"`" — but the actual DTO has fields `{formid, plugin, value, found}` where `found` is a `bool` (set to `false` on miss), not a `status` string. If the executor follows the plan verbatim, the error-contract doc will contain an inaccuracy. **Fix:** Change to: "`db_pool_get_entry_typed()` returns a `FormIdEntryDto` with `found: false` for lookup misses."
- **MEDIUM: `test ! -d` will likely fail after `git rm`.** `git rm` removes files from git tracking but does not delete the empty parent directory from the filesystem. The empty `governance/` directory will still exist on disk. **Fix:** Replace `test ! -d` with `test -z "$(git ls-files docs/implementation/python_api_parity/governance/)"` or add `rmdir` after `git rm`.
- **MEDIUM: `node-python-contract-map.md` may have additional stale references** beyond the 4 identified lines. A broader grep sweep should be added.
- **LOW: Per-crate table has unverified "(via X)" mappings.** Several "(via X)" claims are plausible but not source-verified. The plan does instruct executor to verify from `lib.rs`, which mitigates this.

**Suggestions**

- Fix the `FormIdEntryDto` description to use `found: bool` instead of `status: "not_found"`.
- Replace `test ! -d` with a git-aware check or explicitly `rmdir` empty directories.
- Add a broader grep sweep of `node-python-contract-map.md`.
- Consider adding `docs/api/cxx-parity-gate.md` to the cross-reference sweep.

**Risk Assessment:** LOW-MEDIUM.

---

## Codex Review

### Plan 06-01

**Summary**

The sequencing is good: clean the gate tooling first, archive the governance files before deletion, then hand off to Plan 02. The problem is completeness. As written, this plan removes deferred logic from the two gate entrypoints and the shared helper, but it does not cover the other scripts, baseline artifacts, and tests that still depend on deferred registries. In the current repo state, that makes the "both gates exit zero" acceptance target unlikely to be reachable.

**Strengths**

- Puts DOC-01 and DOC-04 in the right order, which matches the explicit deletion prerequisite.
- Scopes the helper cleanup to the shared runtime coverage layer instead of duplicating logic in each gate.
- Treats the audit trail as a raw archive rather than a summary, which matches the stated requirement.
- Makes the dead Tier-2 generators explicit instead of leaving them as orphaned tooling.

**Concerns**

- **HIGH: `generate_baseline.py` scripts also have `--deferred-registry`.** Both `tools/python_api_parity/generate_baseline.py` and `tools/node_api_parity/generate_baseline.py` accept `--deferred-registry` and read governance files. The plan does not clean these scripts. After Plan 02 deletes governance files, the baseline refresh workflow would be broken.
- **HIGH: The plan does not refresh committed baseline artifacts.** Both gates perform stale-artifact checks against `docs/implementation/*/baseline/`, and the current baseline runtime coverage summaries still include `deferred_registry` and `deferred_total`. Removing those fields from generated output without updating baseline JSON/Markdown will make the gates fail on staleness.
- **MEDIUM: Tests assert deferred behavior.** `test_binding_coverage_tooling.py` passes `deferred_registry` to `build_coverage_summary()`, asserts `deferred_total == 1`, and tests `"deferred"` classification. After removing the parameter, these tests will fail.
- **MEDIUM: `files_modified` is incomplete.** It omits the three deleted scripts, baseline runtime coverage artifacts, and impacted tests.
- **LOW: Audit header hardcodes `2026-04-10` — should be execution-date driven.

**Suggestions**

- Add both `generate_baseline.py` scripts to this plan and remove deferred-registry handling there too.
- Add baseline runtime coverage artifacts to the write set, then refresh them as part of verification.
- Add the affected Python tooling tests to the plan and run them alongside the gates.
- Change verification to make explicit whether gate runs should use baseline refresh or expect already-refreshed artifacts.

**Risk Assessment:** HIGH because the plan currently misses dependencies that are on the critical path to its own acceptance criteria.

### Plan 06-02

**Summary**

Well-structured at a phase level: delete governance, rewrite the overview, add policy and error-contract docs, then repair cross-references. The main issue is source accuracy. Several proposed doc claims and examples do not match the current repository, and the plan misses remaining references outside the named files.

**Strengths**

- Correctly depends on Plan 01 before deleting governance files.
- Separates destructive cleanup from doc creation, which reduces rollback risk.
- Pushes toward a single policy doc instead of scattering process across governance leftovers.
- Requires README indexing and cross-links, so the new docs are discoverable.

**Concerns**

- **HIGH: Overview may over-assert parity.** The proposed intro says all 19 business crates plus `classic-shared-core` are exposed through all three bindings, but `classic-resource-core` has no evident C++ bridge module (`grep` of `classic-cpp-bridge/src/` returns no `resource` matches). The table should be derived from source, not assumed from milestone intent.
- **HIGH: Source examples in `error-contract.md` are wrong.** There is no `run_scan()` in `scanner.rs`, and `db_pool_get_entry_typed()` returns a DTO with `found: bool`, not `status: "not_found"`.
- **HIGH: Plan misses governance references in `docs/development/ci_cd_guide.md`.** Line 257 says "If the change promotes deferred APIs to Tier-1, also update: docs/implementation/node_api_parity/governance/tier2_backlog_and_governance.md". The grep success criteria will find this.
- **MEDIUM: The proposed C++ refresh workflow conflicts with `cxx-parity-gate.md`.** Normal refresh is `check_parity_gate.py --update-baseline`; `generate_baseline.py --write-baseline` is documented as bootstrap, not standard contributor flow.
- **MEDIUM: `test ! -d` verification will fail on empty directories after `git rm`.**
- **LOW: README update instructions are inconsistent about numbering.

**Suggestions**

- Derive crate-to-binding table from actual wrapper imports/exports and `build.rs`, not from milestone expectations.
- Add `docs/development/ci_cd_guide.md` and baseline runtime coverage summaries to the plan's write set.
- Align parity-policy and refresh-note docs with the existing CXX gate workflow in `cxx-parity-gate.md`.
- Replace directory-existence verification with either "directory empty" or explicitly remove empty governance directories.
- Re-verify every error-contract example against concrete function names and return shapes.

**Risk Assessment:** HIGH because the plan mixes correct phase intent with source-level inaccuracies and misses files that still reference deleted governance artifacts.

---

## Consensus Summary

### Agreed Strengths

- **Ordering constraint D-19 is correctly enforced** — both reviewers agree Plan 01 (Wave 1) before Plan 02 (Wave 2) is correct
- **Dead script deletion is complete** — both reviewers agree the three Tier-2 scripts are correctly identified as dead
- **Audit trail structure follows CONTEXT.md decisions faithfully** — raw archive in combined doc with context header
- **Cross-reference hygiene is thorough** — README, node-python-contract-map, and binding-contract-refresh-note are all covered

### Agreed Concerns

1. **HIGH: `FormIdEntryDto` factual error (Claude + Codex).** Both independently found that `db_pool_get_entry_typed()` returns `found: bool`, not `status: "not_found"`. The error-contract doc would ship an inaccuracy. Additionally, Codex found `run_scan()` does not exist in `scanner.rs`.
2. **HIGH: Parity artifact regeneration / baseline staleness (Claude + Codex).** Both found that removing deferred fields from output without refreshing committed baseline artifacts will cause gate staleness failures. Claude focused on parity-artifacts directories; Codex focused on baseline runtime coverage summaries.
3. **HIGH: `generate_baseline.py` scripts also need cleanup (Codex).** Both `generate_baseline.py` scripts accept `--deferred-registry` and read governance files. Plan 01 only cleans `check_parity_gate.py`. Verified: Python line 794, Node line 700.
4. **HIGH: Tests assert deferred behavior (Codex).** `test_binding_coverage_tooling.py` passes `deferred_registry` to `build_coverage_summary()` and asserts `deferred_total == 1`. These tests will fail after the parameter is removed.
5. **HIGH: `docs/development/ci_cd_guide.md` references governance files (Codex).** Line 257 references `docs/implementation/node_api_parity/governance/tier2_backlog_and_governance.md`. The plan's grep verification would catch this, but the fix is not in the plan's write set.
6. **HIGH: Per-crate table may over-assert C++ parity for `classic-resource-core` (Codex).** No `resource` matches in `classic-cpp-bridge/src/`. The "(via files.rs)" claim is unverified. The overview rewrite should derive the table from source.
7. **MEDIUM: `test ! -d` verification will fail on empty dirs (Claude + Codex).** Both found that `git rm` leaves empty parent directories. Fix: `rmdir` or use git-aware check.

### Divergent Views

- **Overall risk assessment diverges.** Claude rates both plans LOW-MEDIUM; Codex rates both HIGH. The difference is that Codex found more missing dependencies (generate_baseline.py, tests, ci_cd_guide.md) while Claude focused on the factual accuracy of the plan's technical content. Both approaches are valid — the plans need both broader file coverage AND factual corrections.
- **Scope of cleanup.** Claude suggests adding parity artifact dirs to `files_modified`; Codex suggests a broader rethinking of the gate verification strategy. The practical fix is the same — refresh baselines after gate runs — but the framing differs.
