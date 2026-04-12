---
phase: 1
review_round: 3
reviewers: [gemini, claude, codex]
reviewed_at: 2026-04-10T21:30:00-07:00
plans_reviewed: [01-01-PLAN.md, 01-02-PLAN.md, 01-03-PLAN.md]
verdicts:
  gemini: READY-TO-EXECUTE (LOW risk, 1 harmless LOW note)
  claude: READY-TO-EXECUTE (LOW risk, 3 LOW cleanup notes)
  codex: REVISE-TARGETED (MEDIUM risk, 2 MEDIUM + 2 LOW)
consensus: REVISE-TARGETED (Codex caught two genuine contradictions the cheaper reviewers missed)
supersedes: "Round 2 REVIEWS.md (committed 2026-04-10 as c8fcfde2) which flagged 3 HIGH + 4 MEDIUM + several LOW concerns. Round 3 revisions verified here closed all HIGH and all but one MEDIUM finding (MEDIUM-6 downgraded to PARTIALLY CLOSED by Codex due to stale parenthetical at 01-03-PLAN.md:767). Round 1 and Round 2 content preserved in git history."
---

# Cross-AI Plan Review — Phase 1 (YAML -> Settings Merge), Round 3

Round 3 re-review of the revised plans after Round 2 drove a targeted replan via `/gsd:plan-phase 1 --reviews`. Three independent reviewers (Google Gemini, Anthropic Claude CLI, OpenAI Codex CLI) ran in parallel against the same prompt, each with the Round 3 focus directive: **confirm Round 2 findings closed, flag new issues introduced by the Round 3 revisions, watch for encoded-logic drift (hash algorithms, grep patterns, JSON schemas, token tables)**.

Unlike Round 2 where all three reviewers reached rough consensus, Round 3 produced a notable verdict split: Gemini and Claude both rated LOW risk / all-closed, while Codex rated MEDIUM risk and flagged one Round 2 finding (MEDIUM-6) as only PARTIALLY CLOSED. Codex's finding was verified against live plan text by the orchestrator before writing this file — both contradictions Codex identified are real.

---

## Gemini Review

# Cross-AI Plan Review — Phase 1 (YAML -> Settings Merge) — Round 3

The Implementation Plans for Phase 1 (YAML -> Settings Merge) have been successfully revised to incorporate all feedback from Round 2. The structural decomposition remains sound, and the "encoded logic" (grep patterns, JSON schemas, hash algorithms) has been correctly aligned with the live codebase. The addition of the reusable `parity_contract_merge_owner.py` helper and the explicit registry recomputation scripts significantly reduces the execution risk for the parity gates.

## 1. Summary
The plans are of exceptional quality, demonstrating rigorous attention to the multi-language binding constraints of the CLASSIC project. Every identified blocker from previous rounds has been closed with source-cited evidence. The executor is provided with precise, idempotent scripts for complex JSON transformations, ensuring that the workspace remains buildable and that parity integrity is maintained throughout the consolidation.

## 2. Round 2 Closure Audit

| Finding # | Status | Evidence |
| :--- | :--- | :--- |
| **HIGH-1** | **CLOSED** | 01-03 Task 2.A.2 Step 7: "Corrected collision key uses the row id field... guaranteed unique by contract convention." |
| **HIGH-2** | **CLOSED** | 01-03 Task 2.A.1/A.2 Step 6: Explicitly documents that `scope` lives in `rust_api_surface.json` and is handled by `--update-baseline`. |
| **HIGH-3** | **CLOSED** | 01-03 Task 2.A.2 Step 4: Correctly identifies `nodeExport` field usage and avoids inventing a `jsModule` field. |
| **MEDIUM-4** | **CLOSED** | 01-02 Task 1.C.1 Step 5: Mandates a 3-way grep pattern (`classic::settings::CacheStats\|classic::yaml::CacheStats\|yaml_ops_cache_stats`) to catch post-flip references. |
| **MEDIUM-5** | **CLOSED** | 01-03 Task 2.C: Provides an inline Python helper that recomputes `contractCount` and SHA-256 `contractIdsHash` (newline-joined, sorted) byte-equivalently to the parity tooling. |
| **MEDIUM-6** | **CLOSED** | 01-03 Task 2.B.5: Explicitly edits `.md` companions in Task 2 because `--update-baseline` skips them. |
| **MEDIUM-7** | **CLOSED** | 01-02 Task 1.C.5: Bridge expansion now accepts exactly 9 tokens (`int`, `integer`, `bool`, `boolean`, `float`, `double`, `path`, `string`, `str`) matching `classic-settings-py`. |

## 3. New Concerns
- **LOW** (01-03 Task 2.A.2 Step 4 `pythonExportPath` logic): The plan instructs the helper to replace prefixes in `pythonExportPath` if they start with `<binding_module_old> + "."`. Live inspection shows that `pythonExportPath` in this contract is relative to the module (e.g., `"YamlOperations.clear_cache"`) and does not contain the module prefix. This logic will be a harmless no-op, as the `pythonModule` field correctly handles the rename.

## 4. Persistent Concerns
None. All 7 Round 2 findings and the original Round 1 blockers are fully addressed.

## 5. Suggestions
- **01-03 Task 2.C.1 (Registry recompute helper):** For absolute parity with `tools/binding_parity_runtime_coverage.py`, ensure the Python helper uses `chr(10)` (newline) as the joiner. The plan already specifies this in the code block.

## 6. Risk Assessment
**Risk Level: LOW**
The execution path is now highly deterministic. The use of `git mv` preserves history, the `CacheStats` naming collision is resolved via a thorough search-and-replace, and the parity gate validation includes re-hashing of stable IDs, which was the final high-complexity risk.

## REVIEW COMPLETE

---

## Claude Review

# Round 3 Cross-AI Review — Phase 1 (YAML → Settings Merge)

## 1. Summary

The Round 3 revisions comprehensively close all seven Round 2 findings with source-cited evidence. I independently verified every HIGH and MEDIUM finding against the live repository: the Python contract schema, Node contract schema, `parse_setting_type` token list, `_stable_id_hash` recipe, `check_parity_gate.py --update-baseline` file list, and generator script line numbers all match what the plans claim. The helper script spec at `tools/parity_contract_merge_owner.py` is now schema-correct. Residual risk is concentrated in three LOW-severity cleanup gaps (dead `"yaml"` entries in SQUAD_BY_OWNER maps, a potentially-hardcoded drift test, and one under-specified smoke-test case). None are blockers — all would surface deterministically during Task 3 execution and are fixable in follow-up commits.

## 2. Round 2 Closure Audit

| # | Finding | Status | Evidence |
|---|---------|--------|----------|
| HIGH-1 | Helper collision key too coarse | **CLOSED** | 01-03 Task 2.A.2 step 7 uses `row["id"]` as primary dedup key (unique by contract invariant). Verified live contract rows all have unique `id` fields like `yaml.lib.YamlCacheStats` (line 11081) and `settings.lib.CacheStats@rust` (line 8684). Disjoint prefixes eliminate collision risk. |
| HIGH-2 | Python `scope` block location | **CLOSED** | 01-03 Task 2.A.2 step 6 deleted entirely. Live verification: `grep -c '"scope"' docs/implementation/python_api_parity/baseline/parity_contract.json` → **0**; `grep -c '"scope"' ClassicLib-rs/python-bindings/parity-artifacts/rust_api_surface.json` → **1**. Plan correctly routes scope updates through `generate_baseline.py` → `check_parity_gate.py` regeneration. |
| HIGH-3 | Node `nodeExport` schema | **CLOSED** | 01-03 Task 2.A.2 step 4 uses `nodeExport` and explicitly does NOT rewrite export name strings. Live verification: `grep -c '"nodeExport"'` → **322**; `"jsModule"` → **0**; `"nodeExportPath"` → **0**. Plan matches actual schema. |
| MEDIUM-4 | `CacheStats` grep pattern stale after `§B.1` namespace flip | **CLOSED** | 01-02 Task 1.C.1 step 5 uses three-alternative pattern: `grep -rn "classic::settings::CacheStats\|classic::yaml::CacheStats\|yaml_ops_cache_stats"`. Catches both pre-flip and post-flip forms regardless of execution order. |
| MEDIUM-5 | `stable_id_hash` regeneration unspecified | **CLOSED** | 01-03 Task 2.C.1 includes explicit inline Python recompute helper. Verified byte-equivalent to `tools/binding_parity_runtime_coverage.py:56-58` (`_stable_id_hash`): both sort, `"\n".join`, encode UTF-8, SHA-256. Live registry entries confirmed at lines 449/464 (Python) and 336/432 (Node). |
| MEDIUM-6 | `parity_contract.md` not auto-regenerated | **CLOSED** | 01-03 Task 2.B.5 edits `.md` companions directly. Live verification: `tools/python_api_parity/check_parity_gate.py:258-264` copies only `parity_diff_report.{json,md}` and `runtime_coverage_summary.{json,md}` — confirms `parity_contract.md` is NOT regenerated by `--update-baseline`. |
| MEDIUM-7 | C++ setting-type token aliases | **CLOSED** | 01-02 Task 1.C.5 documents 9 tokens: `int`, `integer`, `bool`, `boolean`, `float`, `double`, `path`, `string`, `str`. Byte-matches live `parse_setting_type` at `classic-settings-py/src/lib.rs:557-567`. Plan correctly notes case-insensitive matching via `.to_lowercase()`. |

## 3. New Concerns (introduced or surfaced by Round 3 revisions)

- **[LOW] Dead `"yaml"` entries remain in both `SQUAD_BY_OWNER` maps after Task 2.D scrub.** Plan 01-03 Task 2 Section D instructs deletion of lines 30, 56, 78, 100 in the Python generator and lines 40, 69 in the Node generator, but **misses**:
  - `tools/python_api_parity/generate_baseline.py:124` → `"yaml": "Squad C (yaml/settings/registry)",`
  - `tools/node_api_parity/generate_baseline.py:98` → `"yaml": "Squad B (version-registry/aux)",`

  Not a runtime error (the key becomes unused after row reparenting), but it contradicts the plan's "fully scrub yaml references" narrative. The acceptance criterion `grep -nE "classic_yaml\b"` uses a word-boundary regex that does NOT match bare `"yaml"` string literals, so the gap passes verification silently. Recommend adding both deletions and tightening the acceptance grep to `grep -nE '"yaml"' tools/*_api_parity/generate_baseline.py` → 0.

- **[LOW] `tests/test_owner_render_drift.py` may have hardcoded `"yaml"` expectation.** `tools/python_api_parity/generate_baseline.py:148-150` references a drift-guard test: `_OWNER_RENDER_ORDER: tuple[str, ...] = tuple(RUST_OWNER_BY_CRATE.values()) + ("aux",)`. The comment explicitly mentions `tests/test_owner_render_drift.py` enforces this tuple. If that test hardcodes the expected tuple including `"yaml"`, Task 3's `uv run pytest` will fail with a drift mismatch. The plan does not inspect or update this test file.

- **[LOW/INFO] `yaml-residuals-smoke` test case fate unclear.** Live registry at `ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json:475-476` references `testSuite: test_promoted_residuals_smoke.py` and `testCaseId: yaml-residuals-smoke`. Plan 01-03 Task 2.C.1 deletes the `python-tier1-yaml` registry entry entirely but does NOT instruct Plan 01-02 Task 3.C (the only place `test_promoted_residuals_smoke.py` is edited) to delete a `yaml-residuals-smoke` test function if one exists. Plan 01-02 Task 3.C only rewrites `import classic_yaml` → `import classic_settings` symbol references. If the smoke test file has a registry-driven test case named `yaml-residuals-smoke`, it will fail at runtime after the registry entry is gone. Recommend Plan 01-03 Task 2.C.1 add a grep: `grep -n 'yaml-residuals-smoke\|test_yaml_residuals' ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py` and instruct deletion of any matching function alongside the registry entry deletion.

## 4. Persistent Concerns (Round 2 findings not adequately addressed)

**None.** All seven Round 2 findings (3 HIGH + 4 MEDIUM) are closed with independently verifiable evidence.

## 5. Suggestions (concrete improvements)

1. **Tighten Task 2.D scrub of generator scripts**. Add these deletions to 01-03 Task 2 Section D:
   - `tools/python_api_parity/generate_baseline.py` line 124: remove `"yaml": "Squad C (yaml/settings/registry)",`
   - `tools/node_api_parity/generate_baseline.py` line 98: remove `"yaml": "Squad B (version-registry/aux)",`

   Tighten acceptance criterion:
   ```
   grep -nE '"yaml"|classic-yaml-core|classic_yaml\b' tools/python_api_parity/generate_baseline.py tools/node_api_parity/generate_baseline.py
   # Expected: 0 matches
   ```

2. **Audit `test_owner_render_drift.py` before Task 3**. Add a pre-Task-3 step to 01-03:
   ```
   grep -rn "yaml\|_OWNER_RENDER_ORDER" tools/python_api_parity/tests/ ClassicLib-rs/python-bindings/tests/ 2>/dev/null
   ```
   If the test file exists and hardcodes a tuple including `"yaml"`, add it to `files_modified` for Task 2.D and remove the `"yaml"` entry.

3. **Add yaml-residuals-smoke audit to 01-03 Task 2.C.1**. Before deleting the `python-tier1-yaml` registry entry, grep:
   ```
   grep -n 'yaml-residuals-smoke\|test_yaml_residuals\|yaml.*residuals' ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py
   ```
   If a matching test case exists, document explicitly in Plan 01-02 Task 3.C that the case is to be deleted (not just import-rewritten).

4. **Helper script CLI help text**. Task 2.A mentions `--dry-run` but doesn't specify that `--help` must exit 0. The acceptance criterion "Running the helper script with `--help` exits 0 (basic smoke test)" is present — good, keep as-is.

5. **Node contract top-level `ownerModules` cosmetic inconsistency** (noted but correctly deferred). Round 3 Task 2.B.3 correctly identifies that post-merge, Node rows will have `ownerModule: settings` while the top-level map only declares `{scanlog, config, version_registry, aux}`. The plan explicitly documents this as a pre-existing schema quirk not to be fixed in Phase 1. Acceptable — no change recommended.

## 6. Risk Assessment

**LOW**.

The three Round 2 HIGH findings that depended on specific live schemas (collision key, scope block, Node nodeExport) have all been re-verified against the actual contract JSONs and show the plan's claims are correct. The four MEDIUM findings that depended on tool behavior (grep pattern ordering, hash recipe, `.md` regeneration, token aliases) have all been re-verified against the actual Python source at the exact line numbers the plan cites. The three new concerns are all LOW-severity cleanup items that would surface deterministically at Task 3 (cargo test / pytest will fail loudly if any of them matter) and can be resolved with targeted follow-up commits rather than another plan revision round.

**Recommendation:** This plan set is ready for execution. Address the three LOW concerns via executor-time guidance in `/gsd:execute-phase 1` (specifically: watch for test failures in `test_owner_render_drift.py` and `test_promoted_residuals_smoke.py`, and add the missed `SQUAD_BY_OWNER["yaml"]` deletions in the same commit as Task 2.D). A fourth cross-AI round is not warranted — the marginal value is below the cost.

## REVIEW COMPLETE

---

## Codex Review

*(Extracted from Codex streaming transcript — review lines 15242-15273 of the raw transcript, the canonical second copy per extraction convention. Raw transcript: 1.4 MB / 15275 lines.)*

# Round 3 Cross-AI Review — Phase 1 (YAML -> Settings Merge) — Codex

**Summary**
Round 3 materially improves the plans. The live-file checks back the big closures: the helper spec now matches the actual Python/Node contract schemas, the C++ token table matches the real Python parser, and the runtime-registry rehash plan matches the live hash/count semantics. The remaining risk is concentrated in `01-03`: one helper-spec contradiction and one stale acceptance statement.

**Round 2 Closure Audit**

| Finding | Status | Evidence |
|---|---|---|
| `HIGH-1` helper collision key | `CLOSED` | `01-03-PLAN.md:335-342` switches to primary dedup on `row["id"]` with fallback `(ownerModule, rustSymbol, pythonExportPath OR nodeExport, rustCrate)`. |
| `HIGH-2` Python scope block | `CLOSED` | `01-03-PLAN.md:331-333` explicitly removes `scope` work from the helper and points it to generated `ClassicLib-rs/python-bindings/parity-artifacts/rust_api_surface.json`; the live Python contract top keys are `contractVersion, phase, description, tierDefinitions, ownerModules, tier1Mappings` with no `scope`. |
| `HIGH-3` Node `nodeExport` schema | `CLOSED` | `01-03-PLAN.md:313-322` now treats Node rows as `nodeExport` only; the live Node contract uses `nodeExport` and has no `jsModule` / `nodeExportPath`. |
| `MEDIUM-4` CacheStats grep pattern | `CLOSED` | `01-02-PLAN.md:315` now requires `grep -rn "classic::settings::CacheStats\\|classic::yaml::CacheStats\\|yaml_ops_cache_stats" ...`, which covers both pre- and post-flip states. |
| `MEDIUM-5` stable_id_hash regeneration | `CLOSED` | `01-03-PLAN.md:475-527` deletes `*-tier1-yaml` and recomputes `contractCount` / `contractIdsHash`; live hash logic is `"\n".join(sorted(values))` + SHA-256 in `tools/binding_parity_runtime_coverage.py:56-58,79-90`, and a raw-contract recompute reproduces the current checked-in registry hashes exactly. |
| `MEDIUM-6` `parity_contract.md` not auto-regenerated | `PARTIALLY CLOSED` | `01-03-PLAN.md:51` and `01-03-PLAN.md:664` correctly state Task 2 must edit `.md` directly because `--update-baseline` does not sync it; but `01-03-PLAN.md:767` still says the `.md` companions are “fully regenerated ... by --update-baseline.” |
| `MEDIUM-7` C++ setting-type aliases | `CLOSED` | `01-02-PLAN.md:355-371,466` lists the 9-token superset; the live parser in `ClassicLib-rs/python-bindings/classic-settings-py/src/lib.rs:557-562` matches exactly: `int, integer, bool, boolean, float, double, path, string, str`. |

**New Concerns**
- `MEDIUM` `01-03-PLAN.md:304-306` is internally contradictory. Line 304 says missing `ownerModules[settings]` should abort; lines 305-306 say the live Node case should warn and continue. That ambiguity is in the helper’s core control flow.
- `LOW` `01-03-PLAN.md:563-576` cleans Python generator hardcodes for `classic-yaml-core` / `classic_yaml`, but the live `tools/python_api_parity/generate_baseline.py:124` still has `\"yaml\": \"Squad C (yaml/settings/registry)\"`. The planned verification would not catch that stale owner label.
- `LOW` `01-03-PLAN.md:388` expects the Node helper summary to report `22 rows updated`, but the live Node contract has `22` `ownerModule: "yaml"` rows and `26` `rustCrate: "classic-yaml-core"` rows. If the helper counts all mutated rows, the summary will be `26`, not `22`.

**Persistent Concerns**
- `MEDIUM` `MEDIUM-6` is not fully closed because `01-03-PLAN.md:767` still embeds the exact wrong assumption the revision was supposed to remove, even though the task body above it was corrected.

**Suggestions**
- In [01-03-PLAN.md](/abs/path/J:/CLASSIC-Fallout4/.planning/phases/01-yaml-settings-merge/01-03-PLAN.md:304), replace the missing-target rule with explicit branching: `Python contract: abort if ownerModules.settings missing`; `Node contract: warn and continue without top-level ownerModules edit`.
- In [01-03-PLAN.md](/abs/path/J:/CLASSIC-Fallout4/.planning/phases/01-yaml-settings-merge/01-03-PLAN.md:563), add removal of `tools/python_api_parity/generate_baseline.py:124` literal entry `\"yaml\": \"Squad C (yaml/settings/registry)\"`.
- In [01-03-PLAN.md](/abs/path/J:/CLASSIC-Fallout4/.planning/phases/01-yaml-settings-merge/01-03-PLAN.md:767), change the parenthetical to: `.md companions were edited directly in Task 2; --update-baseline does not regenerate them`.
- In [01-03-PLAN.md](/abs/path/J:/CLASSIC-Fallout4/.planning/phases/01-yaml-settings-merge/01-03-PLAN.md:388), change `22 rows updated` to either `26 rows updated` or `22 owner rows reparented`.
- Optional tightening: in [01-02-PLAN.md](/abs/path/J:/CLASSIC-Fallout4/.planning/phases/01-yaml-settings-merge/01-02-PLAN.md:470), add an explicit acceptance grep for `classic::settings::CacheStats` returning zero hits.

**Risk Assessment**
`MEDIUM`. The substantive Round 2 logic issues are mostly closed and the live files support the revised hash/token/schema claims, but `01-03` still has one real implementation ambiguity and one stale verification statement that should be cleaned up before execution.

## REVIEW COMPLETE

---

## Consensus Summary

### Verdict Distribution

| Reviewer | Risk | Verdict | Round 2 Findings Closed |
|----------|------|---------|-------------------------|
| Gemini   | LOW  | READY-TO-EXECUTE | 7/7 |
| Claude   | LOW  | READY-TO-EXECUTE | 7/7 |
| Codex    | MEDIUM | REVISE-TARGETED | 6/7 (MEDIUM-6 PARTIALLY CLOSED) |

### Agreed Strengths (2+ reviewers)

- **All 3 HIGH findings (HIGH-1, HIGH-2, HIGH-3) closed with schema-verified evidence** — all three reviewers independently spot-checked live contract JSON files and confirmed the helper spec, collision key, and Node `nodeExport` schema are correct.
- **Hash recompute helper is byte-equivalent to `tools/binding_parity_runtime_coverage.py:56-91`** — all three reviewers verified the SHA-256-of-newline-joined-sorted-row-IDs algorithm matches the live source.
- **9-token setting-type table matches `classic-settings-py/src/lib.rs:557-567`** — Gemini, Claude, and Codex all confirmed byte-match against live Python parser source.
- **CacheStats triple-grep pattern (MEDIUM-4) correctly catches both pre- and post-namespace-flip references.**
- **Git-history preservation via `git mv` is well-specified.**

### Agreed Concerns (2+ reviewers)

1. **[LOW → should fix] Missing `SQUAD_BY_OWNER["yaml"]` deletions in `generate_baseline.py` scrub.** Both Claude and Codex independently found that Plan 01-03 Task 2 Section D does not remove:
   - `tools/python_api_parity/generate_baseline.py:124` → `"yaml": "Squad C (yaml/settings/registry)",`
   - `tools/node_api_parity/generate_baseline.py:98` → `"yaml": "Squad B (version-registry/aux)",`

   The planned acceptance grep `grep -nE "classic_yaml\b"` uses a word boundary that does NOT match bare `"yaml"` string literals, so the gap would pass verification silently. Claude recommends tightening the grep to `grep -nE '"yaml"|classic-yaml-core|classic_yaml\b'`.

### Divergent Views (genuinely worth investigating)

1. **[MEDIUM — CODEX ONLY, VERIFIED REAL] MEDIUM-6 is only PARTIALLY CLOSED.** Gemini and Claude both marked MEDIUM-6 CLOSED based on the Task 2 §B.5 correction. Codex found that `01-03-PLAN.md:767` still has the stale parenthetical:

   > ``grep -c "classic-yaml-core\|classic_yaml" docs/implementation/python_api_parity/baseline/parity_contract.md docs/implementation/node_api_parity/baseline/parity_contract.md` returns 0 (`.md` companions fully regenerated from updated JSON by `--update-baseline`)``

   The parenthetical embeds the exact wrong mental model the Round 2 fix was supposed to remove. **Orchestrator verified the claim against live plan text — Codex is correct.** Gemini and Claude stopped reading the closure-audit body after the Task 2 §B.5 fix and did not scan downstream acceptance criteria for residual drift. Codex's suggested fix: change the parenthetical to `.md companions were edited directly in Task 2; --update-baseline does not regenerate them`.

2. **[MEDIUM — CODEX ONLY, VERIFIED REAL] Internal contradiction at `01-03-PLAN.md:304-306` in the helper's core control flow.** Codex flagged that:
   - Line 304 says: *"If `ownerModules[<target>]` does NOT exist: this is a degenerate schema. Abort with `sys.exit(1)` and a diagnostic"*
   - Line 305 says: *"The helper must handle BOTH cases: ... or log a warning that the target owner is missing from the top-level map and leave the file untouched for that specific edit (Node)"*
   - Line 306 says: *"This does NOT abort — subsequent row-level edits still run."*

   **Orchestrator verified the claim against live plan text — Codex is correct.** The "abort with sys.exit(1)" in line 304 directly contradicts "does NOT abort" in line 306. The executor writing the helper will see two mutually exclusive instructions. Codex's suggested fix: replace the missing-target rule with explicit per-contract branching: `Python contract: abort if ownerModules.settings missing`; `Node contract: warn and continue without top-level ownerModules edit`.

3. **[LOW — CODEX ONLY] Row-count mismatch at `01-03-PLAN.md:388`.** Codex claims the Node contract has 22 `"ownerModule": "yaml"` rows but 26 `"rustCrate": "classic-yaml-core"` rows. If the helper counts all mutated rows (not just the owner field), the summary will be `26 rows updated`, not `22`. The plan's expected-output text at line 388 should either be corrected to `26 rows updated` or clarified to `22 owner rows reparented`.

4. **[LOW — CLAUDE ONLY] `test_owner_render_drift.py` may hardcode `"yaml"` in `_OWNER_RENDER_ORDER` tuple.** Claude surfaced that `tools/python_api_parity/generate_baseline.py:148-150` references this drift-guard test. If the test hardcodes an expected tuple including `"yaml"`, Task 3's `uv run pytest` will fail. Plan does not currently audit this file.

5. **[LOW/INFO — CLAUDE ONLY] `yaml-residuals-smoke` test case fate unclear.** Live runtime registry at `runtime_coverage_registry.json:475-476` references `testCaseId: yaml-residuals-smoke` in `test_promoted_residuals_smoke.py`. Plan 01-03 deletes the `python-tier1-yaml` registry entry but does not instruct Plan 01-02 Task 3.C to delete any matching test function. Claude recommends adding a grep audit before the registry entry deletion.

6. **[LOW — GEMINI ONLY, HARMLESS] `pythonExportPath` prefix replace is a no-op.** Gemini noticed the helper's `pythonExportPath` prefix-rewrite logic will never trigger because live `pythonExportPath` values are already module-relative (e.g., `"YamlOperations.clear_cache"`) and do not contain the module prefix. The rename is handled correctly by the separate `pythonModule` field. Harmless, but the dead code branch could be removed or documented.

### Recommended Action

**REVISE-TARGETED with a small Round 4 pass.** Two real MEDIUM contradictions (not caught by Gemini/Claude) warrant fixing before execution. The divergence is a classic adversarial-review win: tool-heavy Codex caught internal plan-text contradictions that the cheaper no-tool reviewers missed. Suggested minimal edits for `/gsd:plan-phase 1 --reviews`:

1. **01-03-PLAN.md:767** — Rewrite acceptance parenthetical from `(.md companions fully regenerated from updated JSON by --update-baseline)` to `(.md companions were edited directly in Task 2; --update-baseline does not regenerate them)`. Fixes Codex MEDIUM-6 residual.
2. **01-03-PLAN.md:304-306** — Rewrite the missing-target rule as explicit per-contract branching: Python aborts, Node warns-and-continues. Remove the ambiguous language in line 304. Fixes Codex MEDIUM helper-control-flow contradiction.
3. **01-03-PLAN.md Task 2 §D** — Add deletion of `tools/python_api_parity/generate_baseline.py:124` (`"yaml": "Squad C (yaml/settings/registry)",`) and `tools/node_api_parity/generate_baseline.py:98` (`"yaml": "Squad B (version-registry/aux)",`). Tighten acceptance grep to `grep -nE '"yaml"|classic-yaml-core|classic_yaml\b' tools/*_api_parity/generate_baseline.py → 0`. Closes Claude + Codex joint LOW finding.
4. **01-03-PLAN.md:388** — Either correct `22 rows updated` to `26 rows updated` or clarify to `22 owner rows reparented`. Fixes Codex LOW row-count mismatch.
5. **[OPTIONAL] 01-03-PLAN.md Task 2.C.1** — Add audit grep for `yaml-residuals-smoke` / `test_yaml_residuals` in `test_promoted_residuals_smoke.py` before the registry entry deletion. Addresses Claude's LOW.
6. **[OPTIONAL] 01-03-PLAN.md pre-Task-3 step** — Add audit grep for `_OWNER_RENDER_ORDER` in `tools/python_api_parity/tests/` and `ClassicLib-rs/python-bindings/tests/`. Addresses Claude's LOW.

These are all targeted text edits — no structural replan, no research, no new tasks. Estimate: 5-10 minutes of planner work to apply. Round 4 should then execute directly.

