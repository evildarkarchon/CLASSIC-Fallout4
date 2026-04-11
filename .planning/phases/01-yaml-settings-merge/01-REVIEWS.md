---
phase: 1
review_round: 1
reviewers: [claude, codex]
reviewed_at: 2026-04-10T12:00:00-07:00
plans_reviewed: [01-01-PLAN.md, 01-02-PLAN.md, 01-03-PLAN.md]
gemini_status: skipped (GEMINI_API_KEY not configured)
---

# Cross-AI Plan Review — Phase 1 (YAML -> Settings Merge)

## Claude Review

### Summary

Well-researched 3-plan phase with strong decision traceability (D-01..D-15 are all addressed in concrete tasks). The planner correctly identified atomicity boundaries for git mv (Plan 01-01 Task 1), correctly scoped the D-09 bridge expansion into Plan 01-02 Task 1 to land with the namespace rename, and correctly sequenced parity contract edits (Task 2) before gate regeneration (Task 3) in Plan 01-03. However, there is **one HIGH blocker that the internal checker missed**: Wave 1 leaves the workspace in a non-compilable state because `classic-yaml-py` is not handled until Wave 2. There are also several medium-severity underspecifications around the parity contract "yaml owner → settings owner" merge, C++ consumer file enumeration, and a factual error about Python exception type names.

### Strengths

- **D-15 git mv discipline is rigorously applied**: Plan 01-01 Task 1 is a pure rename commit with no content edits, and acceptance criteria explicitly verify `git log --follow` spans pre-rename history. Plan 01-02 Task 1 also uses `git mv` for the C++ bridge `yaml.rs → settings.rs` rename.
- **D-09 is correctly in scope**: Plan 01-02 Task 1 explicitly folds the D-09 expansion into the rename commit and cites the CONTEXT.md "Deferred Ideas" entry confirming this. 14 new bridge functions + 3 shared structs are enumerated.
- **`Vec<Yaml>` CXX limitation handled correctly**: Plan 01-02 Task 1 section C explicitly notes that `get_cached` cannot cross CXX and skips it with a documented workaround.
- **`include_str!` breakage addressed**: Plan 01-01 Task 2 section E fixes both `include_str!` paths in the migrated `yaml_dead_code_audit.rs`.
- **Parity contract editing before gate run**: Plan 01-03 Task 2 mandates contract edits land before Task 3 runs the gates — correct ordering to avoid "missing crate" failures.
- **CacheStats collision resolution is thorough**: D-03 renames land in Plan 01-01 Task 2 section A, test files are updated in section E, consumer imports in section G.

### Concerns

- **HIGH — Wave 1 does NOT leave workspace compilable**: Plan 01-01 Task 2 section H deletes `ClassicLib-rs/business-logic/classic-yaml-core/` and removes it from workspace members. But `classic-yaml-py` (still a workspace member at end of Wave 1) has `Cargo.toml` dependency `classic-yaml-core = { path = "../../business-logic/classic-yaml-core" }` — now pointing at a non-existent directory. `cargo build --workspace` will fail with "failed to load manifest for workspace member". The automated verify step in Task 2 cannot pass. **Fix options**: (a) also remove `classic-yaml-py` from workspace members in Plan 01-01 Task 2 (then Plan 01-02 Task 3 just deletes the directory), (b) update `classic-yaml-py/Cargo.toml` to depend on `classic-settings-core` instead, or (c) merge Plan 01-02 Task 3 into Plan 01-01. Option (a) is cleanest. Internal plan-checker missed this because it validates individual plans, not inter-plan compile atomicity.

- **HIGH — Parity contract "yaml owner group" merge is underspecified**: Plan 01-03 Task 2 section A steps 3 and 6 instruct the executor to "remove the yaml section wrapper" and "re-parent all rows under the settings owner group". This is not a mechanical `sed` — merging requires preventing key collisions between yaml entries and existing settings entries, preserving entry ordering if the schema is order-sensitive, and updating cross-references to the `yaml` owner group elsewhere. **Fix**: Plan 01-03 Task 2 should fetch and document the actual JSON schema before editing, or provide a small Python script that performs the structural merge deterministically.

- **MEDIUM — C++ consumer file list is not grep-verified**: Plan 01-02 Task 1 section B lists 5 C++ files that reference `classic::yaml::`. No grep step verifies no additional files reference the namespace. **Fix**: Add `grep -rl "classic::yaml\|classic_cxx_bridge/yaml.h" classic-cli/ classic-gui/` before editing.

- **MEDIUM — Factual error: `RustYamlSerializeError` does not exist in classic-yaml-py**: Plan 01-02 Task 3 section A step 2 instructs the executor to copy exception types `RustYamlParseError, RustYamlIOError, RustYamlSerializeError`. But yaml-py source (lib.rs lines 97-102) only defines `RustYamlError` (base), `RustYamlIOError`, `RustYamlParseError`. There is no `RustYamlSerializeError`. **Fix**: Correct the list to `RustYamlError, RustYamlIOError, RustYamlParseError`.

- **MEDIUM — `classic-cpp-bridge` may lack `tempfile` dev-dependency for new unit tests**: Plan 01-02 Task 1 section C adds unit tests using `tempfile::NamedTempFile` but does not check whether `classic-cpp-bridge/Cargo.toml` has `tempfile` as a dev-dep. **Fix**: Add a step to add `tempfile = { workspace = true }` to `classic-cpp-bridge/Cargo.toml` `[dev-dependencies]` if not already present.

- **MEDIUM — Node CLI wrapper at `classic-node/cli/` not inspected**: Plan 01-02 Task 2 deletes `src/yaml.rs`. Plan does not include a grep step for `classic-node/cli/` referencing yaml symbols. **Fix**: Add `grep -rl "parseYaml\|YamlDocument\|yamlCacheStats" ClassicLib-rs/node-bindings/classic-node/cli/`.

- **MEDIUM — D-09 naming collision: two `CacheStats` types in `classic::settings` namespace**: The existing bridge declares `struct CacheStats { hits, misses, hit_rate, size, capacity }` (for YAML file cache). Plan 01-02 Task 1 adds `struct SettingsCacheStats` with identical fields. Both live under `classic::settings::` after the namespace flip. **Fix**: Rename the existing `CacheStats` bridge struct to `YamlCacheStatsDto` in the same commit so the short name belongs to the settings cache.

- **MEDIUM — `scanlog-core` direct yaml-core usage relies on cargo build to catch errors**: Plan says no direct use statements but does not include an explicit pre-edit grep verification. **Fix**: Add `grep -r "classic_yaml_core\|classic-yaml-core" ClassicLib-rs/business-logic/classic-scanlog-core/` check before removing the dependency.

- **LOW — `.idea/ClassicLib-rs.iml` line numbers are approximate**: Plan 01-01 Task 2 section I says "remove lines ~33-35". Line-number-relative edits in XML are fragile. **Fix**: Describe edits by XML element content, not line numbers.

- **LOW — Plan 01-01 Task 2 is a 23-file, 10-section megaedit**: Goes against "each commit compilable" principle. Acknowledged tradeoff for atomicity.

- **LOW — Plan 01-03 Task 2 double-regenerates baselines**: Task 2 manually edits `.md` companions, then Task 3 runs `--update-baseline` which may clobber Task 2's edits. **Fix**: Verify whether `--update-baseline` touches the `.md` companions; if it does, skip Task 2's `.md` edits.

### Suggestions

- **Merge Plan 01-01 Task 2 and Plan 01-02 Task 3's yaml-py removal** into a single atomic step so Wave 1 ends with a compilable workspace.
- **Add a mandatory grep verification step** at the start of each file-editing task.
- **Replace the Python/Node parity contract manual edit with a small helper script** checked in under `tools/` that reads the contract and renames references deterministically. Reuse in Phases 2 and 3.
- **Add a CXX bridge smoke test for `settings_coerce_value`**: the tagged-struct return is the most error-prone new function.
- **Document the intentional name shadowing** in a comment at the top of the renamed `settings.rs` bridge file.

### Risk Assessment

**MEDIUM-HIGH risk** — primarily because of the Wave 1 compilation blocker. If that single issue is fixed, the phase drops to **MEDIUM** risk, bounded mostly by the parity contract JSON restructuring ambiguity. The D-09 bridge expansion is correctly scoped. The git mv sequencing is correct. Primary risks cluster around Plan 01-01 Task 2's scope and the parity contract restructuring.

---

## Codex Review

### Summary

The phase is well-structured at a high level: Wave 1 handles Rust-core consolidation and blame-preserving moves, Wave 2 handles binding churn, and Wave 3 reserves docs plus parity regeneration for the end, which matches D-12. The problem is that **three goal-backward blockers remain**: Wave 1 cannot actually end in a buildable workspace, the D-09 C++ expansion spec is partly modeled against the wrong validator contract, and Wave 3 updates the parity contracts but not the generator/runtime-coverage sources that still hardcode `classic-yaml-core` and `classic_yaml`.

### Strengths

- `01-01-PLAN.md` correctly treats D-15 as a rename-history problem, not just a file-layout problem. The dedicated `git mv` task for source, tests, and bench files is the right shape.
- `01-01-PLAN.md` explicitly fixes the two known `include_str!` path breaks in `yaml_dead_code_audit.rs`, and repo search supports that this is the only yaml-core audit file with those path-sensitive includes.
- The consumer audit for direct Rust/C++/Node source usage is mostly complete. In the live tree, the direct source consumers are the ones the plan names: `classic-config-core`, `classic-version-registry-core`, `classic-scanlog-core` (Cargo only), `classic-cpp-bridge`, `classic-node`, plus `classic-yaml-py`.
- `01-02-PLAN.md` correctly recognizes the CXX limitation around returning `Vec<Yaml>` directly and avoids pretending that raw `Yaml` can cross the bridge.
- `01-03-PLAN.md` is right to delay parity baseline regeneration until after all binding moves land; doing it earlier would just churn baselines twice.

### Concerns

- **HIGH** `01-01-PLAN.md`, Task 2, must-have truth "`cargo build --workspace succeeds`" is not achievable as written. Wave 1 deletes `ClassicLib-rs/business-logic/classic-yaml-core/`, but `ClassicLib-rs/python-bindings/classic-yaml-py/Cargo.toml` still depends on `classic-yaml-core`, and `classic-yaml-py` remains a workspace member until `01-02-PLAN.md` Task 3.

- **HIGH** `01-03-PLAN.md`, Task 2 and Task 3 assume that editing `parity_contract.json` is the only prerequisite for the parity gates. That is false in this repo. `tools/python_api_parity/generate_baseline.py` and `tools/node_api_parity/generate_baseline.py` still hardcode `classic-yaml-core` and `classic_yaml` in their `RUST_TARGET_CRATES` / module maps, so the gates will still try to read deleted paths even after the contract JSON is fixed.

- **HIGH** `01-03-PLAN.md`, files modified for Task 2/3 omit both runtime coverage registries, but the live registries still contain `ownerModule: "yaml"` selectors: `ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json` and `ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json`. Reparenting contract rows from `yaml` to `settings` without updating those registries risks `registry_mismatch_total` failures in the parity gates.

- **HIGH** `01-02-PLAN.md`, interface section plus Task 1.C specify the **wrong D-09 validator model**. In the actual code, `ValidationIssue` has `severity` and `message` only, `IssueSeverity` is `Warning | Error`, `SettingType` is `Int | Bool | Float | Path | String`, and `CoercedValue` includes `Path(String)`. The planned `SettingsValidationIssue.path`, `Info`, `List`, and `Map` variants would create a new C++ contract that does not match `classic-settings-core::validators`.

- **MEDIUM** `01-02-PLAN.md`, objective/must-haves say the C++ bridge will cover the "full classic-settings-core surface," but Task 1.C explicitly skips `get_cached` and downgrades `load_settings_*` from "return docs" to "return count." That may be the right compromise for CXX, but it is not "full surface" anymore and the success language should say so explicitly.

- **MEDIUM** `01-02-PLAN.md`, Task 3.A under-specifies the D-03 rename on the Python side. The task says to import `yaml_cache_stats` / `reset_yaml_cache_stats`, but the copied `classic-yaml-py` implementation currently calls `core::cache_stats()` inside `PyYamlOperations.get_cache_stats()`. If the executor just swaps crates, that method will start reporting settings-cache stats instead of YAML-cache stats.

- **MEDIUM** `01-02-PLAN.md`, Task 3.A.3 treats the extra Python dependencies as tentative ("Likely needs"). They are not optional in the current code: `classic-yaml-py/src/lib.rs` uses shared-path/exceptions/GIL helpers that come from the shared crates, while `classic-settings-py/Cargo.toml` currently lacks them.

- **MEDIUM** `01-03-PLAN.md`, Task 2.B reassigns Node yaml rows to `settings` but does not mention updating top-level owner metadata. The current Node contract already has both `settings` rows and separate `yaml` rows; if `yaml` is collapsed, `ownerModules` / squad metadata must be kept coherent, not just the per-row `ownerModule`.

- **LOW** `01-01-PLAN.md` Task 2.I and `01-02-PLAN.md` Task 3.E clean only `ClassicLib-rs/.idea/ClassicLib-rs.iml`, but the live repo also has stale yaml-core references in root IDE metadata like `.idea/CLASSIC-Fallout4.iml` and `ClassicLib-rs/.idea/workspace.xml`.

- **LOW** The verify commands in multiple plans use `source tools/use_msvc_from_git_bash.sh` inside commands even though the stated environment is PowerShell. That is a tooling mismatch that can create false-negative automation noise.

### Suggestions

- Move the `classic-yaml-py` crate fold-in/deletion into Wave 1, or keep `classic-yaml-core` on disk until Wave 2 completes. As written, you cannot satisfy Wave 1's workspace-build contract.
- Add `tools/python_api_parity/generate_baseline.py` and `tools/node_api_parity/generate_baseline.py` to `01-03-PLAN.md` and rewrite their crate/module maps in the same wave as the contract edits.
- Add both runtime coverage registry files to `01-03-PLAN.md` and update the `yaml` selectors/hashes when rows move under `settings`.
- Rewrite the D-09 C++ validator DTO spec to match the real Rust surface: no `path`, no `Info`, include `Path`, and map severities/types from actual `classic-settings-core::validators`.
- Narrow the C++ success claim from "full settings-core surface" to "all FFI-safe settings-core surface plus documented exceptions," unless you introduce a serialized-doc return shape for `get_cached` / load helpers.
- Make the Python D-03 rewrites explicit: `PyYamlOperations.get_cache_stats()` must call `yaml_cache_stats()`, and any YAML-cache reset helper must call `reset_yaml_cache_stats()`.
- Make the `classic-shared-core` / `classic-shared-py` dependency additions mandatory in `01-02-PLAN.md`, not discretionary.
- Expand IDE cleanup or explicitly defer the remaining `.idea` / workspace metadata so the plan does not imply all active IDE references are handled.

### Risk Assessment

**HIGH** — The phase decomposition is good, but there are still hard blockers on the critical path: Wave 1 is not buildable, Wave 3 parity regeneration will still read deleted yaml-core paths from generator code, and the D-09 bridge expansion spec does not match the real validator API. Those are not polish issues; they can stop execution or produce the wrong public contract.

---

## Consensus Summary

### Agreed Strengths (both reviewers)

- D-15 git mv discipline is correctly applied — pure rename commit separates from content edits to preserve blame history
- `include_str!` breakage in `yaml_dead_code_audit.rs` is correctly identified and fixed
- CXX `Vec<Yaml>` return limitation is correctly acknowledged and worked around in Plan 01-02 Task 1
- Consumer audit for direct Rust/C++/Node usage is mostly accurate (5 consumers + classic-yaml-py)
- Parity baseline regeneration timing at end of Phase 1 is correct per D-12

### Agreed Concerns — **BLOCKERS (must fix before execution)**

**1. HIGH — Wave 1 is not buildable (both reviewers independently flagged)**
- Plan 01-01 Task 2 deletes `classic-yaml-core` from disk and workspace members, but `classic-yaml-py` is still a workspace member pointing at a path dependency to the deleted crate.
- `cargo build --workspace` will fail at end of Wave 1 before Wave 2 even starts.
- **Fix:** Remove `classic-yaml-py` from workspace members in Plan 01-01 Task 2 section H (same commit as yaml-core removal). Plan 01-02 Task 3 then just needs to delete the directory. Alternatively, fold the yaml-py consolidation into Wave 1 entirely.

### Unique Concerns — **BLOCKERS from Codex**

**2. HIGH — D-09 validator DTO spec is factually wrong (Codex)**
- Plan 01-02 Task 1.C specifies `SettingsValidationIssue.path`, `Info` severity, `List`/`Map` setting types. None of these exist in the actual `classic-settings-core::validators` module.
- Real types: `ValidationIssue` has only `severity` + `message`; `IssueSeverity` is `Warning | Error`; `SettingType` is `Int | Bool | Float | Path | String`; `CoercedValue` includes `Path(String)`.
- **Fix:** Rewrite the D-09 CXX shared struct definitions to match the actual Rust API. Planner must Read `classic-settings-core/src/validators.rs` during revision.

**3. HIGH — Parity gate generator scripts hardcode yaml-core references (Codex)**
- `tools/python_api_parity/generate_baseline.py` and `tools/node_api_parity/generate_baseline.py` have `RUST_TARGET_CRATES` and module maps with `classic-yaml-core` / `classic_yaml` hardcoded.
- Editing `parity_contract.json` alone is insufficient — the baseline regeneration will still try to read the deleted crate.
- **Fix:** Add these two generator scripts to Plan 01-03 Task 2's files list and include crate-map edits.

**4. HIGH — Runtime coverage registries have yaml owner module selectors (Codex)**
- `ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json` and `ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json` contain `ownerModule: "yaml"` selectors.
- Reparenting contract rows without updating these registries will cause `registry_mismatch_total` failures in the parity gates.
- **Fix:** Add both registry files to Plan 01-03 Task 2's files list.

### Unique Concerns — **BLOCKERS from Claude**

**5. HIGH — Parity contract yaml owner group merge is underspecified (Claude)**
- Plan 01-03 Task 2 tells the executor to "remove the yaml section wrapper" and "re-parent rows under the settings owner group" without concrete handling for key collisions, ordering preservation, or cross-references.
- **Fix:** Read the actual JSON schema first and provide explicit merge instructions, or write a helper script under `tools/` that can be reused for Phases 2 and 3.

### Unique MEDIUM concerns (each worth addressing)

| # | Reviewer | Concern | Plan |
|---|----------|---------|------|
| 6 | Claude | `RustYamlSerializeError` doesn't exist in yaml-py source (factual error) | 01-02 T3.A |
| 7 | Claude | `tempfile` dev-dep may be missing from classic-cpp-bridge | 01-02 T1.C |
| 8 | Claude | C++ consumer file list not grep-verified before edits | 01-02 T1.B |
| 9 | Claude | Node CLI wrapper at `classic-node/cli/` not inspected | 01-02 T2 |
| 10 | Claude | Two `CacheStats` types in `classic::settings::` namespace (the old `CacheStats` from yaml bridge + new `SettingsCacheStats`) | 01-02 T1.C |
| 11 | Claude | `scanlog-core` direct usage claim not grep-verified | 01-01 T2.F |
| 12 | Codex | Plan 01-02 claims "full settings-core surface" but skips `get_cached` — language inconsistent | 01-02 objective |
| 13 | Codex | D-03 rename on Python side: `PyYamlOperations.get_cache_stats()` currently calls `core::cache_stats()` — will silently report wrong cache | 01-02 T3.A |
| 14 | Codex | Python dependency additions marked "likely needs" but are mandatory (shared-path/exceptions/GIL helpers) | 01-02 T3.A.3 |
| 15 | Codex | Node contract has top-level owner metadata (`ownerModules`, squad metadata) not just per-row `ownerModule` | 01-03 T2.B |

### Agreed LOW concerns

- IDE metadata cleanup is incomplete. Both reviewers flagged that only `ClassicLib-rs/.idea/ClassicLib-rs.iml` is cleaned, but `.idea/CLASSIC-Fallout4.iml` (root) and `ClassicLib-rs/.idea/workspace.xml` also have stale yaml-core references.

### Divergent Views

- **Claude** thinks Plan 01-01 Task 2's 23-file megaedit scope is acceptable (atomicity tradeoff). **Codex** does not comment on Task 2 scope. Both reviewers agree atomicity is the reason for the size.
- **Claude** flags the double-regeneration risk in Plan 01-03 (Task 2 edits `.md` companions, Task 3 `--update-baseline` may clobber). **Codex** does not comment on this specific mechanism.

### Final Verdict

**Both reviewers assign HIGH risk.** 4-5 HIGH blockers identified (1 overlapping, 4 unique). Plans require another revision round before execution. The most critical finding is that **both reviewers independently caught the Wave 1 compilability blocker** — this is the kind of inter-plan atomicity issue that single-plan validators miss.

The Codex review is particularly valuable for finding the D-09 validator DTO factual error — the planner invented fields and severity variants that don't exist in the actual Rust source. This matches the feedback memory pattern about "encoded logic reviews catching issues internal verification misses."

## Next Steps

Run: `/gsd:plan-phase 1 --reviews` to incorporate feedback into a revised plan set.
