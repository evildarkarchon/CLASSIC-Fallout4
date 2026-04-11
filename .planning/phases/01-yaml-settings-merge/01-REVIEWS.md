---
phase: 1
review_round: 2
reviewers: [gemini, claude, codex]
reviewed_at: 2026-04-10T20:30:00-07:00
plans_reviewed: [01-01-PLAN.md, 01-02-PLAN.md, 01-03-PLAN.md]
verdicts:
  gemini: READY-TO-EXECUTE
  claude: REVISE-AGAIN (narrow)
  codex: REVISE-AGAIN
consensus: REVISE-AGAIN (2-of-3 reviewers)
supersedes: "Round 1 REVIEWS.md (committed 2026-04-10 as 98f598d6) which reviewed the initial 01-01/02/03 plans. That review's 5 HIGH blockers and 15 MEDIUM concerns drove the targeted revisions verified here. The Round 1 content is preserved in git history."
---

# Cross-AI Plan Review — Phase 1 (YAML -> Settings Merge), Round 2

Round 2 re-review of the revised plans after Round 1 drove a full replan via `/gsd:plan-phase 1 --reviews`. Three independent reviewers (Google Gemini, Anthropic Claude CLI, OpenAI Codex CLI) ran in parallel against the same prompt, each with the Round 2 focus directive: **confirm blockers closed, flag new issues, do not re-litigate Round 1**.

## Gemini Review

### Summary

The Implementation Plans for Phase 1 (YAML -> Settings Merge) have been successfully revised to address all 5 HIGH blockers and 15 MEDIUM concerns identified in the Round 1 review. The planner correctly adopted "Option A" for the buildability blocker (revoking `classic-yaml-py` workspace membership in Wave 1) and introduced a robust, reusable Python helper script for parity contract merges. The C++ bridge expansion spec now accurately reflects the ground truth of `classic-settings-core::validators`. No significant new defects or regressions were introduced by the revisions.

### Round 1 Blocker Closure

| Blocker # | Status | Evidence | Notes |
| :--- | :--- | :--- | :--- |
| 1 | **CLOSED** | 01-01 Task 2, Sec H | Revokes `classic-yaml-py` workspace membership in the same commit as `classic-yaml-core` deletion, ensuring `cargo build --workspace` passes. |
| 2 | **CLOSED** | 01-02 Task 1, Sec C.6 | Shared structs for CXX now match `validators.rs` (no `path` field, correct severities/types, preserves `Path` variant). |
| 3 | **CLOSED** | 01-03 Task 2, Sec D | `tools/*/generate_baseline.py` scripts updated to remove hardcoded `classic-yaml-core` and `classic_yaml` modules. |
| 4 | **CLOSED** | 01-03 Task 2, Sec C | Both `runtime_coverage_registry.json` fixtures updated to reparent `yaml` selectors to `settings`. |
| 5 | **CLOSED** | 01-03 Task 2, Sec A | Introduces a reusable `tools/parity_contract_merge_owner.py` helper script with detailed deterministic semantics. |

### Round 1 Medium Concern Closure

| Concern # | Status | Evidence |
| :--- | :--- | :--- |
| 6 | **CLOSED** | 01-02 Task 3.A.2 (Correctly identifies 3 exceptions; no `SerializeError`). |
| 7 | **CLOSED** | 01-02 Task 1.C.2 (Added grep check for `tempfile` dev-dependency). |
| 8 | **CLOSED** | 01-02 Task 1.B.0 (Mandatory grep verification for C++ consumers). |
| 9 | **CLOSED** | 01-02 Task 2.A.0 (Mandatory grep verification for Node CLI wrapper). |
| 10 | **CLOSED** | 01-02 Task 1.C.1 (Existing bridge struct renamed to `YamlCacheStatsDto` to avoid collision). |
| 11 | **CLOSED** | 01-01 Task 2.F.5 (Added grep verification for `scanlog-core` direct usage). |
| 12 | **CLOSED** | 01-02 Objective (Corrected scope language to "FFI-safe surface plus documented exceptions"). |
| 13 | **CLOSED** | 01-02 Task 3.A.2 (Explicit method call update for `PyYamlOperations::get_cache_stats`). |
| 14 | **CLOSED** | 01-02 Task 3.A.3 (Python foundation dependencies marked as mandatory). |
| 15 | **CLOSED** | 01-03 Task 2.A.2/B.3 (Helper handles top-level `ownerModules` and squads metadata). |

### NEW Concerns Introduced by Revisions

- **LOW** (01-02 Task 3.D redundant instruction): Task 3.D repeats the removal of `classic-yaml-py` from workspace members already performed in 01-01 Task 2.H. This is harmless but technically redundant.
- **LOW** (01-01 Task 2.I.2 path reconciling): The root `.iml` file is noted as already modified in git status; the plan correctly instructs the executor to reconcile edits, but this increases the manual attention requirement for that specific file.

### Helper Script Review (tools/parity_contract_merge_owner.py spec)

The spec provided in Plan 01-03 Task 2 Section A is technically sound and comprehensive.

- **Interface**: The parameter set (`--source-owner`, `--rust-crate-old`, etc.) is sufficient for the structural merges required in this phase and reusable for Phase 2/3.
- **Semantics**: The 9-step walk (Step 5 recursive walk, Step 4 path prefix replacement) is essential for maintaining contract integrity.
- **Safety**: The Key Collision Detection (Step 7) ensures the script will abort rather than produce a corrupt or ambiguous contract.
- **Conclusion**: The interface and steps are sufficient and safe.

### Risk Assessment

**LOW Risk.** The planner has effectively converted a high-risk consolidation into a well-sequenced series of buildable commits. The addition of mandatory grep verification steps (`B.0`, `F.5`, `A.0`) and the move to a scripted contract merge significantly reduce the likelihood of human error during execution. The C++ bridge expansion is now anchored to actual source types, removing the contract-mismatch risk from Round 1.

### Verdict

**READY-TO-EXECUTE**

---

## Claude Review

### Summary

Round 1 closed cleanly overall. All 5 HIGH blockers and 15 MEDIUM concerns are addressed with explicit, well-cited edits. The helper script spec (blocker 5 fix) is sound in concept and semantics. However, the revisions introduced **one MEDIUM regression** around task ordering in Plan 01-02 Task 1 that will cause a deterministic C++ compile error, and **one MEDIUM latent risk** around runtime coverage registry stable-ID hashing that wasn't surfaced in Round 1. One small revision pass is warranted.

### Round 1 Blocker Closure

| # | Blocker | Status | Evidence | Notes |
|---|---------|--------|----------|-------|
| 1 | Wave 1 not buildable (yaml-py->yaml-core dangling dep) | CLOSED | 01-01 Task 2 §H.3 removes yaml-py from `members`; §H.5 keeps directory on disk; acceptance criterion "Wave 1 acceptance gate: cargo build --workspace exits 0" | Clean fix via Option A. The stranded yaml-py directory with broken path dep is invisible to cargo because it's no longer a workspace member. |
| 2 | D-09 validator DTO spec factually wrong | CLOSED | 01-02 Task 1 §C.0 mandates re-Read of `validators.rs`; interface block now shows verified `ValidationIssue` (severity+message only), `IssueSeverity::{Warning,Error}`, 5-variant `SettingType`, `CoercedValue::Path(String)` distinct from `String(String)`; §C.6 shared structs match 1:1; §C.5 type-token mapping is exactly 5 tokens | Acceptance criteria include an explicit "NO `path` field" assertion and "NO `info` token" assertion |
| 3 | Parity gate generators hardcode yaml-core | CLOSED | 01-03 Task 2 §D.1 lists exact lines 30/56/78/100 in `tools/python_api_parity/generate_baseline.py`; §D.2 lists lines 40/69 in Node script; §D.3 word-boundary grep verification | Line-number citations are precise and source-backed |
| 4 | Runtime coverage registries have yaml owner selectors | CLOSED | 01-03 Task 2 §C covers both registry files with grep-first verification and post-edit grep check | See NEW concern below about stable-ID hashing |
| 5 | Parity contract owner-group merge underspecified | CLOSED | 01-03 Task 2 §A delivers `tools/parity_contract_merge_owner.py` with 9-step semantics, key collision abort, idempotency, and reuse plan for Phases 2/3 | Helper approach (Claude's suggestion option b) is the right call |

### Round 1 Medium Concern Closure

| # | Concern | Status | Evidence |
|---|---------|--------|----------|
| 6 | `RustYamlSerializeError` doesn't exist | CLOSED | 01-02 Task 3 §A.1 explicitly lists the three real exceptions and notes `SerializeError` maps to `RustYamlParseError` in `to_pyerr` |
| 7 | `tempfile` dev-dep check | CLOSED | 01-02 Task 1 §C.2 adds grep verification; acceptance criterion verifies match under `[dev-dependencies]` |
| 8 | C++ consumer grep-first | CLOSED | 01-02 Task 1 §B.0 mandates `grep -rl "classic::yaml\|classic_cxx_bridge/yaml.h"` as authoritative consumer set |
| 9 | Node CLI wrapper grep | CLOSED | 01-02 Task 2 §A.0 adds CLI wrapper grep; notes typical result is zero hits due to NAPI regeneration |
| 10 | Two `CacheStats` collision | CLOSED | 01-02 Task 1 §C.1 renames pre-existing `CacheStats` -> `YamlCacheStatsDto` in same commit; acceptance criterion prohibits any `CacheStats` struct in `ffi` block | See NEW concern 1 below — closure created a task-ordering bug |
| 11 | scanlog-core direct usage grep | CLOSED | 01-01 Task 2 §F.5 adds mandatory grep of `classic-scanlog-core/src/` |
| 12 | "full settings-core surface" language | CLOSED | 01-02 objective now says "all FFI-safe settings-core surface plus documented exceptions" and explicitly documents `get_cached` skip and `load_*` returning `u32` |
| 13 | `PyYamlOperations.get_cache_stats` silently wrong | CLOSED | 01-02 Task 3 §A.2 mandates rewriting `core::cache_stats()` -> `yaml_cache_stats()`; acceptance criterion verifies it |
| 14 | Python shared deps "likely needs" | CLOSED | 01-02 Task 3 §A.3 labels deps MANDATORY with grep verification step |
| 15 | Node contract top-level `ownerModules` | CLOSED | Helper script step A.2.2 handles `ownerModules.<source>` deletion; step A.2.3 walks `squads.<name>.ownerModules` arrays |
| LOW | IDE metadata cleanup incomplete | CLOSED | 01-01 Task 2 §I.1/I.2/I.3 covers both `.iml` files + `workspace.xml` with element-content edits (not line numbers); 01-02 Task 3 §E covers yaml-py entries in same three files |

### NEW Concerns Introduced by Revisions

- **[MEDIUM] Plan 01-02 Task 1 §C.1 step 5 grep pattern is stale after §B.1 runs** — This is a closure-induced regression. The task order is A (rename file) → B (C++ consumer namespace flip) → C (bridge expansion including C.1 `CacheStats` -> `YamlCacheStatsDto` rename). Section B.1 mechanically replaces `classic::yaml::` -> `classic::settings::` in all C++ consumer files, which turns every `classic::yaml::CacheStats` reference into `classic::settings::CacheStats`. Then §C.1 step 5 grep searches for `classic::yaml::CacheStats\|yaml_ops_cache_stats` — the first pattern finds zero hits post-flip, so the executor will miss the references that need renaming to `YamlCacheStatsDto`. After §C.1 renames the Rust struct, `classic::settings::CacheStats` becomes a dangling C++ symbol and `cargo test -p classic-cpp-bridge` will fail with an undefined-symbol link error against the generated CXX header. **Fix:** either (a) change the §C.1 step 5 grep pattern to `classic::settings::CacheStats\|classic::yaml::CacheStats\|yaml_ops_cache_stats` (covers both pre- and post-B states), or (b) move the `CacheStats` rename into §B.1's C++ replacement pass as a special case (rewrite `classic::yaml::CacheStats` -> `classic::settings::YamlCacheStatsDto` before the general `classic::yaml::` -> `classic::settings::` substitution). Option (a) is less invasive.

- **[MEDIUM] Plan 01-03 Task 2 §C does not address stable-ID hash regeneration in runtime coverage registries** — User memory notes (`project_python_parity_tooling_internals.md`) record that `_stable_id_hash` uses full-SHA and that the Python parity tooling computes stable IDs from `(owner, symbol)` tuples. §C manually rewrites `"ownerModule": "yaml"` -> `"ownerModule": "settings"` but does NOT rehash any dependent stable-ID fields in the same row. If the registry stores `"stableId"` or `"hashKey"` fields computed from owner+symbol, the hash-of-(yaml,X) will no longer match the recomputed hash-of-(settings,X), and the parity runtime coverage check will report `registry_mismatch_total > 0`, failing Task 3 Section C (Python gate). §C.1 handwaves this with "If any row contains a stable-id hash field keyed on the owner module... update those too" but doesn't specify HOW (re-hashing requires running the same SHA function the generator uses). **Fix:** either (a) add an explicit step that regenerates stable IDs via a purpose-built helper or by re-running the registry generator after the owner rewrites, or (b) confirm by inspection that the registries do NOT use owner-keyed hashes and remove the ambiguous paragraph. Without one of these, Task 3 gate-regeneration may fail in a way the plan does not predict.

- **[LOW] Plan 01-02 Task 1 §C.3 bridge signature type widths** — `fn settings_cache_size() -> u64` and `SettingsCacheStats { size: u64, capacity: u64 }` use `u64` but the underlying Rust cache functions return `usize`. Requires explicit `as u64` casts in the adapter layer. Most executors will handle this automatically, but it's unspecified. Not a blocker.

- **[LOW] Helper script Python-version dependency unstated** — `tools/parity_contract_merge_owner.py` relies on Python 3.7+ dict-insertion order preservation (step A.2.1: "preserving key order via `object_pairs_hook=dict` (Python 3.7+ dicts are insertion-ordered, so this is free)"). Helper has no `#!/usr/bin/env python3` shebang or version check in its spec. CLASSIC standard env uses `uv` with Python 3.12, so this is fine in practice. Add a one-line version assert for defensive measure in future phases.

- **[LOW] Plan 01-03 Task 2 file list includes `.md` companions but §B.5 defers their edits to Task 3** — Listing them in `files_modified` frontmatter while also saying "leave them in files_modified frontmatter because Task 3's --update-baseline run still modifies them" creates a documentation inconsistency with Task 2's actual scope. Trivially correct but a potential confusion point for Task 2 acceptance review.

### Helper Script Review (`tools/parity_contract_merge_owner.py`)

**Interface (step A.1):** Correct shape — source/target owner, old/new crate, old/new binding module, optional binding-key-name flags for Python vs Node asymmetry. Reusable for Phase 2 (crashgen->config, `classic-crashgen-settings-core` -> `classic-config-core`) and Phase 3 (constants->version-registry) without modification. Good.

**Semantic steps (step A.2):**

1. **JSON load with order preservation** — relies on Python 3.7+ dict ordering (see LOW concern above). Sufficient.
2. **Top-level `ownerModules` merge** — correct: deletes source entry, leaves target alone, handles degenerate "target doesn't exist" case. Good.
3. **Squad metadata update** — covers `squads.<name>.ownerModules` array mutation with dedup logic. Correct.
4. **Tier mapping row updates** — covers `ownerModule`, `rustCrate`, `<binding_module_key>`, `pythonExportPath`, `nodeExportPath` with dot-suffix prefix matching to prevent false positives. The dot suffix is critical (prevents `classic_yaml_core.X` from matching `classic_yaml.` pattern). Good.
5. **Nested owner-group recursive walk** — defensive, idempotent (already-target rows pass through untouched). Good.
6. **Scope block (Python-only)** — removes `scope.target_crates` entry and `scope.source_files` entries matching the crate directory segment. Correct, though depends on Python contract actually having a `scope` block.
7. **Key collision detection** — uses `(ownerModule, rustSymbol, <binding_module_key>_value)` triple as dedup key. For Phase 1, no overlap is expected between existing `settings`-owned rows and yaml rows being reparented (Plan 01-02 already proves this at the binding layer — yaml-py and settings-py expose disjoint function sets). Correct. **Gap:** if Phase 2 or 3 does cause a collision, the helper aborts but provides no merge-hint — the executor must resolve manually. Acceptable for a first-cut helper; Phase 2/3 can extend.
8. **Output** — `json.dump(indent=2, ensure_ascii=False)` with trailing newline. Matches CLASSIC parity contract formatting conventions.
9. **Exit code** — 0/1 with summary line. Good.

**Overall assessment of helper:** Interface correct. Semantics sound. Key-collision abort rule is safe. The 9 steps are sufficient for deterministic owner-group merges in the CLASSIC parity contract structure. **Will not break existing contract structure** — the helper is purely additive (rewrites values in-place, deletes source owner) and preserves all unrelated rows.

**Minor recommendation:** consider adding a `--dry-run` flag for Phase 2/3 validation before committing. Not blocking.

### Risk Assessment

**MEDIUM** (down from HIGH in Round 1). Both Round 1 HIGH-level structural blockers (Wave 1 buildability, D-09 factual errors, parity-gate generator hardcoding, runtime registry selectors, parity merge underspecification) are closed with concrete, source-cited edits. The two new MEDIUM concerns are narrower:

- The CacheStats grep-pattern regression is a deterministic compile error but has a one-line fix.
- The stable-ID hash regeneration concern is conditional on the registry structure and may be a non-issue if the registries use opaque (non-derived) stable IDs.

Neither new concern represents a re-plan-level failure. Both can be addressed with small targeted edits in a 3rd revision pass, or with explicit executor-time guidance if the user accepts the risk.

### Verdict

**REVISE-AGAIN** (narrowly)

The Round 1 closure work is strong — all 5 blockers and 15 concerns are demonstrably fixed with source-cited evidence, and the helper script spec is sound. But the new MEDIUM regression in Plan 01-02 Task 1 §C.1 step 5 (stale grep pattern after §B.1 namespace flip) will deterministically fail the `cargo test -p classic-cpp-bridge` verify step during execution — exactly the kind of "encoded logic" issue the cross-AI review process is meant to catch. Fix that one grep pattern (add `classic::settings::CacheStats` as an alternate) and either resolve or explicitly acknowledge the stable-ID hash concern in Plan 01-03 Task 2 §C, and the plans should be ready to execute without a further cross-AI round.

If the user prefers to move forward without a 3rd revision, they should add these two notes as executor-time guidance in `/gsd:execute-phase` and accept the small risk that the stable-ID path may need a follow-up commit.

---

## Codex Review

### Summary

Round 2 closes most of the Wave 1 / bindings issues from Round 1, but Wave 3 is still not execution-safe. Blockers 1 and 3 are effectively closed, blocker 2 is closed at the DTO/type level, but blockers 4 and 5 are only partially closed because the new parity-helper path is modeled against the wrong schema in a few key places and still misses the selector-hash mechanics the runtime coverage gate enforces.

### Round 1 Blocker Closure

| blocker # | status | evidence | notes |
|---|---|---|---|
| 1. Wave 1 not buildable because `classic-yaml-py` still points at deleted `classic-yaml-core` | CLOSED | `01-01 Task 2.H`; `must_haves.truths` in `01-01-PLAN.md` explicitly remove `python-bindings/classic-yaml-py` from workspace members in the same commit as yaml-core removal and gate on `cargo build --workspace` | This addresses the actual compile-atomicity failure. |
| 2. D-09 validator DTO spec was factually wrong | CLOSED | `01-02 <interfaces>` validator block; `01-02 Task 1.C.0`, `C.4`, `C.5`, `C.6` | The revised plan now matches `classic-settings-core/src/validators.rs` on `ValidationIssue`, `IssueSeverity`, `SettingType`, and `CoercedValue`. A new token-synonym mismatch exists (see NEW concerns), but the original blocker is closed. |
| 3. Parity generator scripts still hardcode `classic-yaml-core` / `classic_yaml` | CLOSED | `01-03 files_modified`; `01-03 Task 2.D.1-D.3` | This closes the deleted-path/generator hardcoding blocker. |
| 4. Runtime coverage registries still have `ownerModule: "yaml"` selectors | **PARTIALLY-CLOSED** | `01-03 Task 2.C.1-C.3` | The plan now touches both registry files, but it only rewrites `ownerModule`. The gate also validates selector-based `contractCount` and `contractIdsHash`; those are not recomputed here, so `registry_mismatch_total` can still fail. |
| 5. Parity-contract owner merge was underspecified | **PARTIALLY-CLOSED** | `01-03 Task 2.A.1-A.2` | Adding `tools/parity_contract_merge_owner.py` is the right direction, but the spec is still wrong for the live schema in several places: collision key is too coarse, Node schema assumptions are off, and the Python contract does not contain the `scope` block the helper expects. |

### Round 1 Medium Concern Closure

| concern # | status | evidence |
|---|---|---|
| 6. `RustYamlSerializeError` does not exist | CLOSED | `01-02 Task 3.A.1-A.2` explicitly says only `RustYamlError`, `RustYamlIOError`, `RustYamlParseError` exist |
| 7. `tempfile` dev-dep may be missing in `classic-cpp-bridge` | CLOSED | `01-02 Task 1.C.2` adds explicit grep/conditional add |
| 8. C++ consumer file list not grep-verified | CLOSED | `01-02 Task 1.B.0` mandatory grep-first step |
| 9. Node CLI wrapper not inspected | CLOSED | `01-02 Task 2.A.0` grep on `classic-node/cli/` |
| 10. Two `CacheStats` types in `classic::settings` namespace | CLOSED | `01-02 Task 1.C.1` renames bridge DTO to `YamlCacheStatsDto` |
| 11. `scanlog-core` direct yaml-core usage not grep-verified | CLOSED | `01-01 Task 2.F.5` explicit grep gate before dep removal |
| 12. "Full settings-core surface" language inconsistent with exceptions | CLOSED | `01-02 objective` and `must_haves.truths` now say "all FFI-safe surface plus documented exceptions" |
| 13. Python `get_cache_stats()` would silently call wrong cache API | CLOSED | `01-02 Task 3.A.2` explicitly rewrites to `yaml_cache_stats()` / `reset_yaml_cache_stats()` |
| 14. Python dependency additions were treated as optional | CLOSED | `01-02 Task 3.A.3` makes `classic-shared-py` mandatory |
| 15. Node contract has top-level owner metadata, not just row-level `ownerModule` | **PARTIALLY-CLOSED** | `01-03 Task 2.A.2` adds `ownerModules` / `squads` handling, but `01-03 Task 2.B.3` explicitly leaves the live Node contract's top-level metadata incoherent when `yaml` is absent |

### NEW Concerns Introduced by Revisions

- **`HIGH`** `01-03 Task 2.A.2 step 7`: the helper's collision key is unusable for the live Python contract. It proposes `(ownerModule, rustSymbol, <binding_module_key>_value)`, but many legitimate rows already share that triple. In the current contract, `settings` rows for `validators` under `classic_settings` already collide. This helper would abort on valid data before doing any merge.
- **`HIGH`** `01-03 Task 2.A.2 step 6` and Task 2 acceptance: the plan targets `scope.target_crates` inside `docs/implementation/python_api_parity/baseline/parity_contract.json`, but that file has no `scope` block. `scope` lives in generated `ClassicLib-rs/python-bindings/parity-artifacts/rust_api_surface.json`. The current acceptance criterion is impossible as written.
- **`MEDIUM`** `01-03 Task 2.B.5` and `01-03 Task 3`: the plan now defers `parity_contract.md` edits because it assumes `--update-baseline` regenerates them. Both `tools/python_api_parity/check_parity_gate.py` and `tools/node_api_parity/check_parity_gate.py` only sync `parity_diff_report.*` and `runtime_coverage_summary.*`; they do not rewrite `parity_contract.md`.
- **`MEDIUM`** `01-02 Task 1.C.5`: the plan says the C++ setting-type parser must match Python `parse_setting_type()` "1:1", but then only accepts `int`, `bool`, `float`, `path`, `string`. The live Python helper in `classic-settings-py/src/lib.rs` also accepts `integer`, `boolean`, `double`, and `str`. This would introduce a new C++/Python mismatch.
- **`MEDIUM`** `01-03 Task 2.A.2 step 4`: the helper spec still talks about `jsModule` and `nodeExportPath`, but the live Node contract rows use `nodeExport` and have no module field. That indicates the merge logic is still partially modeled against the wrong schema.

### Helper Script Review (`tools/parity_contract_merge_owner.py` spec)

Interface: not quite correct for the live contracts.

- Python contract: `pythonModule` / `pythonExportPath` exist, but no `scope` block exists in `parity_contract.json`.
- Node contract: `rustCrate` exists, but there is no `jsModule` and no `nodeExportPath`; rows use `nodeExport`.
- The current CLI could work if the implementation treats binding-module keys as truly optional and schema-driven, but the spec text does not.

Nine semantic steps: not sufficient yet.

- Step 2/3 on `ownerModules` and `squads` is directionally good.
- Step 4 needs to understand actual field names per contract.
- Step 6 is pointed at the wrong file.
- The spec does not address contract row IDs such as `yaml.*`, which remain inconsistent after owner reparenting.
- Most importantly, it does not cover the runtime-registry selector hashes/counts that must move with the owner merge if the gates are expected to pass end-to-end.

Key-collision abort rule: unsafe as specified.

- Abort-on-collision is reasonable in principle.
- The chosen key is wrong. For Python it will false-positive on ordinary class/method rows because many mappings legitimately share `ownerModule + rustSymbol + pythonModule`.
- A safe key would need the binding export identity too, e.g. include `pythonExportPath` / `nodeExport`, and likely `rustCrate` or `id`.

Could this break existing contract structure: yes.

- The helper would preserve JSON validity, but it can still leave semantic drift:
  - row owners reparented without corresponding selector hash/count refresh,
  - IDs still prefixed `yaml.*`,
  - Node schema fields not actually touched because the spec names the wrong keys.

### Risk Assessment

Still **`HIGH`**.

Wave 1 and most Wave 2 issues are in good shape now. The remaining risk is concentrated in Wave 3, and it is material: the new helper spec is not executable against the live schema as written, and the runtime coverage registry plan still does not fully satisfy the gate's selector-mismatch logic.

### Verdict

**REVISE-AGAIN**

---

## Consensus Summary

### Verdict Tally

| Reviewer | Risk | Verdict |
|----------|------|---------|
| Gemini | LOW | READY-TO-EXECUTE |
| Claude | MEDIUM | REVISE-AGAIN (narrow) |
| Codex | HIGH | REVISE-AGAIN |

**Consensus: REVISE-AGAIN** (2-of-3). Gemini's LOW-risk assessment is discounted because it did not inspect the live parity contract JSON files during review — it evaluated the helper script spec against the prompt text, while Codex inspected the actual `docs/implementation/*/baseline/parity_contract.json` files and found multiple schema mismatches.

### Agreed Round 1 Closure (all 3 reviewers agree)

**HIGH blockers fully closed (3):**
- **Blocker 1** — Wave 1 buildability via `yaml-py` workspace member removal in 01-01 Task 2 §H
- **Blocker 2** — D-09 validator DTO spec matches `classic-settings-core/src/validators.rs` in 01-02 Task 1 §C.0/C.4/C.5/C.6 (Codex flags a new token-synonym issue as separate)
- **Blocker 3** — Parity generator scripts de-yaml'd in 01-03 Task 2 §D

**MEDIUM concerns fully closed (12 of 15):** concerns 6, 7, 8, 9, 10, 11, 12, 13, 14 — all three reviewers agree.

### Disputed Closures

**Blocker 4 — Runtime coverage registries**
- Gemini + Claude: CLOSED
- Codex: **PARTIALLY-CLOSED**. Claim: plan rewrites `ownerModule` but doesn't recompute selector-based `contractCount` and `contractIdsHash` fields — gate may still fail on `registry_mismatch_total`.
- Claude raises the same underlying concern as a separate "NEW MEDIUM" (stable-ID hashing) rather than calling blocker 4 partially closed.
- **Consensus:** NEEDS VERIFICATION. The user's memory `project_python_parity_tooling_internals.md` records that `_stable_id_hash` uses full-SHA — if the registries contain owner-keyed hashes, the plan must regenerate them. If not, a one-line note to 01-03 Task 2 §C suffices.

**Blocker 5 — Parity contract owner merge helper**
- Gemini + Claude: CLOSED (helper spec is sound)
- Codex: **PARTIALLY-CLOSED**. Claim: helper spec is modeled against a schema that does not match the live parity_contract.json files in two concrete ways (see NEW HIGH concerns below).
- Codex used live file inspection during review; Gemini and Claude evaluated the spec text in isolation.
- **Consensus:** Codex's findings are specific and testable. The helper spec must be re-aligned to the actual JSON schema before execution.

**Concern 15 — Node contract top-level `ownerModules`**
- Gemini + Claude: CLOSED
- Codex: **PARTIALLY-CLOSED**. Claim: 01-03 Task 2 §B.3 explicitly leaves the live Node contract's top-level metadata incoherent when `yaml` is absent (the live Node contract currently has no top-level `yaml` entry, only row-level `yaml` selectors).
- **Consensus:** Minor inconsistency in plan text; does not block execution but should be reconciled with Codex's HIGH-3 schema finding.

### Agreed NEW Concerns (2+ reviewers)

**NONE.** Each reviewer found distinct new issues. This is expected — different reviewers stress different aspects of the plan. Below are the union of new findings.

### NEW Concerns — Union of All Reviewers (to address in Round 3)

**HIGH severity (all from Codex — surfaced via live file inspection):**

1. **Helper collision key is too coarse for live Python contract** (Codex, 01-03 Task 2.A.2 step 7)
   The proposed key `(ownerModule, rustSymbol, <binding_module_key>_value)` false-positives on valid data — `settings` rows for `validators` under `classic_settings` already share this triple in the current contract. Helper would abort on valid input.
   **Fix:** Extend collision key to include binding export identity. Recommended key: `(ownerModule, rustSymbol, pythonExportPath_or_nodeExport, rustCrate)` or just use the row `id` field if present.

2. **Python contract has no `scope` block** (Codex, 01-03 Task 2.A.2 step 6)
   Helper spec targets `scope.target_crates` inside `docs/implementation/python_api_parity/baseline/parity_contract.json`, but `scope` lives in the generated `ClassicLib-rs/python-bindings/parity-artifacts/rust_api_surface.json` instead. Acceptance criterion is impossible as written.
   **Fix:** Either (a) point the helper at `rust_api_surface.json` for scope updates, or (b) remove step 6 entirely and document that `scope` is regenerated automatically by `--update-baseline`.

3. **Node contract schema mismatch: `nodeExport` not `jsModule`/`nodeExportPath`** (Codex, 01-03 Task 2.A.2 step 4)
   Helper spec uses `jsModule` and `nodeExportPath` but live Node contract rows use only `nodeExport`. Merge logic targets fields that don't exist.
   **Fix:** Update helper step 4 field list to match actual Node contract schema: `ownerModule`, `rustCrate`, `nodeExport` (no module field, no export-path field).

**MEDIUM severity:**

4. **01-02 Task 1 §C.1 step 5 grep pattern stale after §B.1** (Claude) — deterministic compile-time regression. Section B.1 already rewrote `classic::yaml::CacheStats` -> `classic::settings::CacheStats` before §C.1 step 5 runs, so the grep pattern `classic::yaml::CacheStats\|yaml_ops_cache_stats` misses all post-B references. Result: `cargo test -p classic-cpp-bridge` fails with undefined-symbol link error.
   **Fix:** Change §C.1 step 5 grep pattern to `classic::settings::CacheStats\|classic::yaml::CacheStats\|yaml_ops_cache_stats`.

5. **01-03 Task 2 §C stable-ID hash regeneration unspecified** (Claude) — Runtime coverage registries may contain stable IDs hashed from `(owner, symbol)` tuples. Plan rewrites `ownerModule` but doesn't address hash regeneration. Could cause `registry_mismatch_total > 0` on gate run. This is the same issue Codex flagged as making Blocker 4 "PARTIALLY-CLOSED".
   **Fix:** Inspect registry structure. If stable IDs are owner-keyed, add explicit regeneration step (run the registry generator or a purpose-built hash helper). If not, add a one-line confirmation note.

6. **01-03 Task 2 §B.5 + Task 3 `.md` companion regeneration assumption is wrong** (Codex) — Plan defers `parity_contract.md` edits because it assumes `--update-baseline` regenerates them, but `check_parity_gate.py` only syncs `parity_diff_report.*` and `runtime_coverage_summary.*`, not `parity_contract.md`.
   **Fix:** Either (a) add explicit `.md` companion edits back to Task 2 action, or (b) verify by reading `check_parity_gate.py --update-baseline` behavior and document the actual regeneration scope.

7. **01-02 Task 1.C.5 C++/Python type-token mismatch** (Codex) — Plan says C++ parser matches Python `parse_setting_type()` "1:1" but only accepts the 5 canonical tokens. Live Python helper in `classic-settings-py/src/lib.rs` also accepts aliases: `integer`, `boolean`, `double`, `str`. This introduces a new C++/Python mismatch.
   **Fix:** Read `classic-settings-py/src/lib.rs` `parse_setting_type()` and copy the full token list (canonical + aliases) into the C++ parser.

**LOW severity:**

8. **01-02 Task 3.D redundant yaml-py workspace member removal** (Gemini) — Task 3.D repeats what 01-01 Task 2.H already did. Harmless (idempotent) but worth marking as verify-only.
9. **01-01 Task 2.I.2 root `.iml` already modified in git status** (Gemini) — Plan correctly instructs executor to reconcile, but increases manual attention.
10. **01-02 Task 1 §C.3 `u64` vs `usize` width casts unspecified** (Claude) — Minor adapter-layer detail; most executors handle automatically.
11. **Helper script Python version assert unstated** (Claude) — Relies on Python 3.7+ dict ordering without explicit version check. Fine in practice under `uv` + Python 3.12.
12. **01-03 Task 2 `.md` files in `files_modified` frontmatter but deferred in §B.5** (Claude) — Documentation inconsistency with Task 2's actual scope.

### Divergent Views

- **Risk assessment spread:** Gemini=LOW, Claude=MEDIUM, Codex=HIGH. The spread reflects how deeply each reviewer inspected the actual live contract JSON files during review. Codex used tool access to read the schemas; Gemini did not.
- **Helper script verdict:** Gemini + Claude say "sound and comprehensive"; Codex says "wrong schema in multiple places". Resolving this means reading the actual `parity_contract.json` files against the helper's 9-step spec — which the planner should do in Round 3.
- **Blocker 4/5/Concern 15 status:** Gemini + Claude marked CLOSED; Codex marked PARTIALLY-CLOSED. Codex's findings are concrete and source-cited (file paths, field names, row examples), so they should be treated as authoritative pending verification.

### Recommended Next Action

**Run `/gsd:plan-phase 1 --reviews` one more time** to close the 3 NEW HIGH and 4 NEW MEDIUM concerns. The revision pass should be small and targeted:

1. Re-align helper script spec with actual `parity_contract.json` schemas (HIGH 1, HIGH 2, HIGH 3, MEDIUM 6) — planner must Read both contract files during revision.
2. Fix the `CacheStats` grep pattern stale-after-flip regression (MEDIUM 4) — one-line change.
3. Resolve stable-ID hash regeneration for runtime coverage registries (MEDIUM 5) — inspect registry structure and either add a regeneration step or confirm no-op.
4. Correct the C++ setting-type parser token list to include Python aliases (MEDIUM 7) — read `classic-settings-py/src/lib.rs`.
5. LOW concerns can be addressed opportunistically or deferred.

This is still a "targeted edits" round, not a full replan. The structural decomposition (Wave 1 / 2 / 3, D-15 git mv discipline, D-09 bridge expansion scope) remains correct.

**Alternative:** If the user chooses to proceed directly to execution, add items 1-7 above as executor-time guidance in `/gsd:execute-phase 1` and accept the risk that Wave 3 may need follow-up commits before the parity gates pass. Wave 1 and most of Wave 2 are solid; the residual risk is concentrated in Plan 01-03 (parity gate regeneration).

## Next Steps

Run: `/gsd:plan-phase 1 --reviews` to incorporate Round 2 feedback into a final revised plan set, OR proceed to `/gsd:execute-phase 1` with manual executor guidance for the 7 Round 2 items.
