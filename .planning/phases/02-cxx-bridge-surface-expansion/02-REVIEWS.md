---
phase: 2
reviewers: [codex]
reviewed_at: 2026-04-07T03:09:18-07:00
plans_reviewed:
  - 02-01-path-promotion-and-widening-PLAN.md
  - 02-02-constants-bridge-PLAN.md
  - 02-03-web-bridge-PLAN.md
  - 02-04-xse-and-version-registry-split-PLAN.md
  - 02-05-scangame-widening-ba2-ini-enb-PLAN.md
  - 02-06-scangame-widening-toml-wrye-integrity-setup-PLAN.md
  - 02-07-config-suspect-rules-and-database-typed-PLAN.md
  - 02-08-fcx-getter-and-final-verification-PLAN.md
---

# Cross-AI Plan Review — Phase 2: CXX Bridge Surface Expansion

## Codex Review

*Model: `gpt-5.4` via `codex exec` (codex-cli 0.117.0), sandbox `read-only`, reasoning effort `high`*

### Plan 01 — 02-01-path-promotion-and-widening-PLAN.md

**Summary**
This is the best-sequenced plan in the set: promoting `path.rs` early and preserving shims is the right dependency move. The main blind spot is that the plan's path INI design is anchored to a nonexistent core API and an incorrect DTO shape, so a large chunk of the implementation path is currently wrong.

**Strengths**
- Promotes `path.rs` before downstream consumer work, which matches D-03 and reduces later churn.
- Keeps backward-compatible shims in `game.rs`, consistent with D-08.
- Explicitly accounts for `build.rs`/header-generation risk and clean-build cadence.

**Concerns**
- **HIGH** The planned `IniCheckResultDto` and `check_ini_files(...)` flow do not match `ClassicLib-rs/business-logic/classic-path-core/src/checker.rs`: the real type is `IniCheckResult { ini_name, exists, is_valid, message, issue }`, and the core path is `DocumentsChecker::validate_ini_file` / `run_all_checks`, not the six-flag DTO described in the plan.
- **MEDIUM** D-11 caller coverage is incomplete. The plan treats `classic-gui/src/app/pathdialog.cpp` as the only migration site, but `classic-gui/src/app/mainwindow.cpp` still calls `classic::game::check_restricted_path` for custom scan paths.
- **MEDIUM** The plan is string-heavy, but the underlying validators are `&Path`-based. It does not spell out the UTF-8 / normalization / empty-path policy across the C++→Rust boundary, which matters for Windows path security and fail-soft behavior.

**Suggestions**
- Rework the INI subtask against `classic-path-core/src/checker.rs`, not the current DTO sketch in the plan.
- Add an explicit D-11 migration task for `classic-gui/src/app/mainwindow.cpp`, not just `pathdialog.cpp`.
- Add a short contract section covering `std::filesystem::path` / `QString` to Rust `Path` conversion, plus how `Option<String>` issues surface to C++.

**Risk Assessment** — **HIGH** — the sequencing is good, but the core DTO/API mismatch means the plan will not execute cleanly as written.

---

### Plan 02 — 02-02-constants-bridge-PLAN.md

**Summary**
This is a relatively low-complexity bridge split, and the parity/build discipline is solid. The weakness is that it underestimates the enum surface and does not prove the roadmap's "new `classic::constants` namespace callable from C++" outcome with a real consumer.

**Strengths**
- Good isolation of a small surface area into its own bridge file.
- D-09 parity artifact discipline is explicit.
- Compatible with D-08: existing call sites can remain untouched while the namespace grows.

**Concerns**
- **MEDIUM** The plan's example enum coverage is incomplete. `classic-constants-core/src/lib.rs` includes `Main`, `Settings`, `Ignore`, `Game`, `GameLocal`, `Test`, and `Cache`; the plan examples only reflect a subset.
- **MEDIUM** The plan appears to treat D-11 as effectively N/A, but the roadmap explicitly calls out `classic::constants` as a new namespace C++ should be able to call.
- **LOW** Version-string handling needs to match the real source of truth. `Fallout4Version::as_str()` returns `"VR"` for `Vr`; if tests/examples normalize this differently, parity will drift silently.

**Suggestions**
- Add an enum audit checklist tied to `classic-constants-core/src/lib.rs` before freezing wrapper signatures.
- Add one concrete CLI/GUI caller migration so roadmap success criterion 2 is actually demonstrated, not inferred.
- Make the plan state how unknown enum values and `"VR"` string mapping are handled at the bridge boundary.

**Risk Assessment** — **MEDIUM** — likely implementable, but it currently under-proves the user-visible outcome the phase says it delivers.

---

### Plan 03 — 02-03-web-bridge-PLAN.md

**Summary**
The module split is sensible, but the plan leans too hard on string dispatch and gives up too much type safety relative to the Rust API. It also repeats the phase-wide pattern of treating new namespace exposure as complete without a concrete production caller.

**Strengths**
- Keeps web behavior in its own namespace instead of bloating `game.rs`.
- Clean-build and parity expectations are clear.
- Compatible with the "thin C++ wrapper over Rust" repo rule.

**Concerns**
- **MEDIUM** The design is too stringly-typed. `classic-web-core/src/lib.rs` already has typed `ModSite` variants; the plan's string dispatch creates invalid-input states that do not exist in Rust.
- **MEDIUM** `validate_url` in core returns a parsed `Url`, not just pass/fail. If the bridge collapses that to a bool or plain error string, it loses canonicalization and weakens validation semantics.
- **MEDIUM** There is no concrete D-11 migration for `classic::web`, so roadmap success criterion 2 is still unproven.

**Suggestions**
- Replace raw string dispatch with a shared enum or a strict conversion table derived from `classic-web-core/src/lib.rs`.
- Decide explicitly whether `validate_url` returns the normalized URL string, the original string, or only an error.
- Add one real caller in `classic-cli` or `classic-gui` before treating the namespace as complete.

**Risk Assessment** — **MEDIUM** — the code can likely be written, but the current plan gives away too much type safety and consumer proof.

---

### Plan 04 — 02-04-xse-and-version-registry-split-PLAN.md

**Summary**
Splitting `xse` and version-registry out of `game.rs` is directionally right, but this plan still contains unresolved implementation debt inside the plan itself. It reads more like a design stub than an execution-ready sequence.

**Strengths**
- Correctly targets one of the highest-bloat bridge modules.
- Preserves D-08 compatibility via shims.
- Calls out `build.rs` ordering risk and clean-build requirements.

**Concerns**
- **MEDIUM** The plan still contains unresolved placeholders such as `todo!()` in its implementation path, which means important signature/mapping choices are not actually locked.
- **MEDIUM** D-11 is effectively skipped, even though the roadmap expects `classic::xse` / registry namespaces to be usable from C++.
- **LOW** Wrapper assumptions should stay source-truthful: `classic-xse-core/src/lib.rs` has `XseType::from_game_id` as a total mapping, and `dll_prefix()` includes trailing underscores like `"f4se_"`; the plan should not invent optional/error paths that do not exist.

**Suggestions**
- Replace the placeholder sections around line 545 of `02-04-xse-and-version-registry-split-PLAN.md` with concrete wrapper signatures tied to `classic-xse-core/src/lib.rs` and `classic-version-registry-core/src/registry.rs`.
- Add one exercised caller for either `classic::xse` or registry before calling the split "done".
- Make the plan explicit about deriving IDs from existing registry iteration instead of implying missing core helpers.

**Risk Assessment** — **MEDIUM** — feasible, but not execution-grade yet.

---

### Plan 05 — 02-05-scangame-widening-ba2-ini-enb-PLAN.md

**Summary**
This plan has the right tranche boundary, but it is built on incorrect assumptions about the Rust APIs. The BA2, INI, and ENB designs are not minor DTO issues; they are modeling functions and result shapes that do not exist.

**Strengths**
- Splits `scangame` into a manageable first wave.
- Keeps parity artifacts and verification in scope.
- At least attempts to think about DTO flattening up front.

**Concerns**
- **HIGH** The plan assumes top-level `run_ba2_check`, `run_ini_check`, and `run_enb_check` APIs, but the real code paths are `classic-scangame-core/src/ba2.rs`, `ini.rs`, and `enb.rs`, each with different entry points and types.
- **HIGH** The planned INI DTO is materially wrong. The real `ConfigIssue` includes `file_path`, `setting`, and `description`; the plan's DTO renames and drops fields, so it cannot be a faithful bridge of the current source.
- **HIGH** The ENB model does not match `classic-scangame-core/src/enb.rs`: actual output is `EnbValidationResult { binaries, config }` with `EnbResult` / `EnbConfigResult`, not the states and `errors` field the plan sketches.
- **MEDIUM** D-11 coverage is thin. Adding a new helper method in `classic-gui/src/workers/gamefilesworker.cpp` is not enough if no existing product flow actually invokes it.

**Suggestions**
- Re-derive the entire wrapper surface directly from `classic-scangame-core/src/{ba2,ini,enb}.rs` before locking DTOs.
- Require one exercised GUI/CLI path, not just a dormant worker method.
- Add a performance note to avoid `block_on`-per-file wrappers when the Rust side already offers batch/orchestrated checks.

**Risk Assessment** — **HIGH** — this plan is currently aimed at the wrong APIs.

---

### Plan 06 — 02-06-scangame-widening-toml-wrye-integrity-setup-PLAN.md

**Summary**
This is the highest-risk plan in the phase. It repeats the same source-truth problem as Plan 05, but across more domains, and it adds a direct Pitfall 6 hazard in the likely Wrye DTO shape.

**Strengths**
- Sensible second-half grouping of the remaining `scangame` domains.
- Verification discipline is carried forward.
- Correct instinct to think about DTO flattening before coding.

**Concerns**
- **HIGH** The plan's TOML, Wrye, integrity, setup, and crashgen wrapper signatures do not match the source in `classic-scangame-core/src/{toml,wrye,integrity,setup,crashgen_orchestrator}.rs`.
- **HIGH** The likely `WryeIssueDto` shape is a direct Pitfall 6 risk: real `WryeIssue` contains `plugins: Vec<String>`, so returning `Vec<WryeIssueDto>` would be `Vec<StructWithVec>`, the exact ABI pattern the phase says is forbidden.
- **HIGH** The integrity and setup models are wrong at the field/enum level. `IntegrityCheckResult` uses `is_valid` and `CheckType { ExecutableVersion, InstallationLocation }`; `SetupCheckResults` is vector-based, not pre-counted.
- **MEDIUM** The plan again relies on helper-method additions in `gamefilesworker.cpp` rather than a clearly exercised product flow.
- **LOW** The dependency reference to `02-05-PLAN.md` is stale, which suggests the cross-plan dependency chain has not been revalidated carefully.

**Suggestions**
- Rebuild the DTO design from the actual source files above; do not keep the current invented intermediate model.
- Flatten Wrye into a row-oriented DTO or split it into two APIs, rather than returning `Vec<WryeIssueDto>` with embedded vectors.
- Derive setup counts from the real `Vec<String>` fields in `classic-scangame-core/src/setup.rs`, and require one invoked caller path.

**Risk Assessment** — **HIGH** — as written, this plan is more likely to discover redesign work than to execute predictably.

---

### Plan 07 — 02-07-config-suspect-rules-and-database-typed-PLAN.md

**Summary**
This plan is closer to source truth than the `scangame` plans, but it has a serious Pitfall 6 problem in the suspect-rule DTO shape and still treats production-caller proof too casually.

**Strengths**
- Builds on real existing bridge precedent in `classic-cpp-bridge/src/config.rs` and `database.rs`.
- Targets real remaining gaps from the phase scope.
- Keeps the work isolated from tier-collapse and doc-rewrite scope.

**Concerns**
- **HIGH** If the plan returns `Vec<SuspectStackRuleDto>` and `SuspectStackRuleDto` itself contains `Vec<SuspectStackCountRuleDto>`, that is `Vec<StructWithVec>`, which is the exact Pitfall 6 ABI shape the phase says must be flattened away.
- **MEDIUM** D-11 is treated as N/A, but typed suspect-rule/database APIs are still new bridge surface and should land with at least one production caller.
- **MEDIUM** Batch DB miss semantics are underspecified. `classic-database-core/src/pool_sqlx.rs` returns only hits for batch lookups; a typed bridge API can easily mislead C++ callers into assuming positional completeness if that contract is not explicit.
- **LOW** Large batch requests could turn into long UI stalls if the plan does not specify practical limits or chunking guidance.

**Suggestions**
- Replace nested suspect-rule DTOs with a flattened row DTO or a two-step API keyed by rule identity.
- Add a contract section tied to `classic-database-core/src/pool_sqlx.rs` defining single-hit, miss, and batch-hit semantics.
- Add one real consumer migration for either typed suspect rules or typed database lookup.

**Risk Assessment** — **HIGH** — the nested DTO design can fail at the ABI layer even if the Rust logic is otherwise correct.

---

### Plan 08 — 02-08-fcx-getter-and-final-verification-PLAN.md

**Summary**
The FCX getter itself is straightforward and grounded in a real remaining requirement. The problem is the completion logic: the plan overclaims phase closure without proving the new namespace is exercised in production C++.

**Strengths**
- Targets a roadmap-explicit gap: `classic::scanner::get_fcx_config_issues()`.
- Leverages an existing bridge area in `classic-cpp-bridge/src/scanner.rs`.
- Includes an end-of-phase verification sweep rather than stopping at code compile.

**Concerns**
- **HIGH** There is no concrete C++ caller migration for the new getter, even though ROADMAP.md explicitly calls out this namespace in Phase 2 success criteria.
- **MEDIUM** The final verification reads too parity-centric. Zero drift and clean builds prove surface existence, not that the new namespaces are wired into exercised product flows.
- **MEDIUM** The plan should explicitly define empty/uninitialized FCX-state behavior to match the bridge's existing fail-soft reset semantics in `classic-cpp-bridge/src/scanner.rs` and the global-handler behavior in `classic-scanlog-core/src/fcx_handler.rs`.

**Suggestions**
- Add a real CLI/GUI consumer for `classic::scanner::get_fcx_config_issues()` before phase sign-off.
- Anchor `FcxIssueDto` exactly to `classic-scanlog-core/src/fcx_handler.rs`, not a convenience reshaping that drops fields.
- Make final sign-off require at least one exercised caller per newly introduced namespace, not just parity zero-drift.

**Risk Assessment** — **HIGH** — the wrapper is easy, but the completion criteria are too weak for the claim being made.

---

### Phase-Level Review

**Sequencing / cross-plan dependencies**
The overall order is mostly right: `path` first, then small namespace splits, then the heavier `scangame` tranche, then final FCX verification. The weak point is not ordering between plans so much as proof quality within plans: Plans 02, 03, 04, 07, and 08 largely assume "bridge exists" equals "phase outcome achieved," which is not what D-11 or the roadmap says. Plans 05 and 06 should not proceed as written until their wrapper/API assumptions are revalidated against source.

**Pitfall 6 DTO verification**
- Confirmed risk: Plan 07's likely `Vec<SuspectStackRuleDto>` with nested `Vec<SuspectStackCountRuleDto>` is the exact forbidden `Vec<StructWithVec>` pattern.
- Confirmed risk: Plan 06's likely `Vec<WryeIssueDto>` with `plugins: Vec<String>` is also `Vec<StructWithVec>`.
- Likely safe if kept flat: Plan 08's FCX issue DTO, because `fcx_handler.rs` is scalar/optional-scalar only.
- Broader issue: several DTOs in Plans 05 and 06 are not just ABI-risky; they are sourced from the wrong Rust shapes entirely, so Pitfall 6 checking alone is not enough.

**D-11 production-caller coverage**
- Real but incomplete: Plan 01, because `mainwindow.cpp` is still missed.
- Thin / symbolic: Plans 05 and 06, which mostly add helper methods in `gamefilesworker.cpp` without proving an exercised UI path.
- Missing / waived: Plans 02, 03, 04, 07, and 08. That directly conflicts with D-11 and undercuts roadmap success criterion 2.

**D-10 clean-build cadence**
The plans that add new bridge modules generally do acknowledge mandatory clean builds after `build.rs` changes, which is good. Codex did not see a major silent reliance on incremental builds; the bigger risk is source-model mismatch, not build cadence.

**D-09 parity-artifact commit discipline**
This is one of the strongest parts of the phase. The plans consistently treat `parity_contract.json`, `cxx_diff_report.{json,md}`, and `cxx_gate_report.md` as per-plan deliverables. The only caveat is that parity artifacts cannot substitute for exercised caller coverage.

**Coverage of the 5 Phase 2 success criteria**
- Build scripts pass: well covered.
- `classic::constants`, `classic::web`, and `classic::scanner::get_fcx_config_issues()` callable from C++: under-covered, because Plans 02, 03, and 08 do not include real consumer migrations.
- Parity gate at zero drift: strongly covered.
- `scangame` exposes the same orchestration entry points as Python/Node: not convincingly covered, because Plans 05 and 06 are not grounded in the actual Rust APIs and do not show a direct Python/Node parity audit.
- `database`, `registry`, `config`, `path`, `xse` gaps closed: conceptually covered, but weakened by missing D-11 proof and, for Plan 07, a likely ABI failure.

**Missing scope or scope creep**
Missing scope:
- Plan 01 misses `classic-gui/src/app/mainwindow.cpp` as a restricted-path migration site.
- The phase as planned does not require a real consumer for `classic::constants`, `classic::web`, or `classic::scanner::get_fcx_config_issues()`, despite the roadmap doing so.
- Plans 05 and 06 do not explicitly validate against Python/Node binding surface, even though that is the stated parity target.

Scope creep:
- Plans 05 and 06 drift into "add helper methods to `GameFilesWorker`" without proving those helpers participate in a real product flow. That is symbolic integration, not meaningful consumer migration.

**Overall phase risk** — **HIGH**
The parity/build discipline is strong, but too many plans are either under-proving D-11 or, in the `scangame` tranche, designed against the wrong Rust APIs. The phase can likely reach "compiles and parity is green" without actually satisfying the roadmap's consumer-facing success criteria.

---

## Consensus Summary

*Only one reviewer (Codex) was invoked via `--codex`, so "consensus" reflects that single reviewer's findings grouped by theme. When Gemini/Claude are added later via `/gsd:review --phase 2 --gemini --claude`, re-run to cross-validate.*

### Top Concerns (HIGH severity)

1. **Source-of-truth drift in scangame plans (Plans 05 and 06)** — DTO designs and function names are anchored to Rust APIs that do not exist in `classic-scangame-core/src/{ba2,ini,enb,toml,wrye,integrity,setup,crashgen_orchestrator}.rs`. Plans must be rederived directly from source before implementation.
2. **Pitfall 6 violations in Plans 06 and 07** — `Vec<WryeIssueDto>` (Plan 06) and `Vec<SuspectStackRuleDto>` (Plan 07) are `Vec<StructWithVec>` patterns explicitly forbidden by the phase's own pitfall rules. Flatten to row-oriented DTOs or split into two APIs.
3. **D-11 production-caller coverage is missing or symbolic across 5+ plans** — Plans 02, 03, 04, 07, 08 waive D-11 entirely; Plans 05, 06 add dormant helper methods in `gamefilesworker.cpp` without a real product flow. This undercuts ROADMAP success criterion 2 ("C++ frontend code can call into `classic::constants`, `classic::web`, and `classic::scanner::get_fcx_config_issues()`").
4. **Plan 01 core-API mismatch** — The `IniCheckResultDto` / `check_ini_files` design in Plan 01 does not match `classic-path-core/src/checker.rs` (real type is `IniCheckResult { ini_name, exists, is_valid, message, issue }`; real entry points are `DocumentsChecker::validate_ini_file` / `run_all_checks`).
5. **Plan 04 still has `todo!()` placeholders** — Not execution-ready; key wrapper signatures are unresolved.

### Agreed Strengths

- **D-09 parity-artifact commit discipline is strong** — all plans treat `parity_contract.json` + diff + gate report as per-plan deliverables.
- **D-10 clean-build cadence is acknowledged** — plans that add new `build.rs` entries explicitly schedule clean `build_cli.ps1 -Clean -Test` + `build_gui.ps1 -Clean -Test` pairs.
- **Overall sequencing is correct** — `path` → small namespace splits → `scangame` tranche → FCX verification is the right order.
- **D-08 backward-compat shim strategy is consistently applied** — existing `game.rs` callers remain unbroken.

### Agreed Concerns (cross-cutting)

- **Plans confuse "parity-green" with "phase outcome achieved."** Zero parity drift only proves surface existence; it does not prove D-11 or roadmap success criterion 2.
- **Plan 01 misses `mainwindow.cpp`** as an additional D-11 migration site for `check_restricted_path`.
- **Plans 05 and 06 do not explicitly validate against Python/Node binding surface**, despite CXXS-04's literal wording "orchestration entry points used by Python/Node bindings."

### Divergent Views

N/A — single reviewer.

### Recommended Next Actions

1. **Block execution of Plans 05 and 06** until DTOs and wrapper signatures are rebuilt from `classic-scangame-core/src/` source files.
2. **Fix Plan 07's nested `SuspectStackRuleDto`** — flatten to a row-oriented DTO keyed by rule identity to clear Pitfall 6.
3. **Add mandatory "exercised C++ caller" tasks** to Plans 02, 03, 04, 07, 08 — one real production call site per new namespace, not a dormant helper.
4. **Correct Plan 01's INI section** to use `DocumentsChecker::validate_ini_file` / `run_all_checks` and the real `IniCheckResult` shape.
5. **Add `mainwindow.cpp` migration task** to Plan 01 for `check_restricted_path` on custom scan paths.
6. **Resolve `todo!()` placeholders in Plan 04** before execution.
7. **Re-run `/gsd:review --phase 2 --gemini --claude`** to cross-validate Codex's findings with independent reviewers.
8. **Feed this review back into planning** via `/gsd:plan-phase 2 --reviews` to incorporate corrections.
