---
phase: 02-cxx-bridge-surface-expansion
plan: 07
type: execute
wave: 4
depends_on:
  - 02-cxx-bridge-surface-expansion/01
  - 02-cxx-bridge-surface-expansion/02
  - 02-cxx-bridge-surface-expansion/03
  - 02-cxx-bridge-surface-expansion/04
files_modified:
  - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs
  - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs
  - docs/implementation/cxx_api_parity/baseline/parity_contract.json
  - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
  - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
  - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
autonomous: true
requirements:
  - CXXS-05
  - CXXS-07
  - CXXS-10
must_haves:
  truths:
    - "src/config.rs exposes SuspectErrorRuleDto + yaml_data_suspects_error_rules() returning the full rule set with severity and main_error_contains_any patterns (CXXS-07)"
    - "src/config.rs exposes a FLATTENED suspect-stack surface — Pitfall 6 elimination via TWO bridge fns: yaml_data_suspects_stack_rules_metadata() returning Vec<SuspectStackRuleMetadataDto> (NO nested Vec<SuspectStackCountRuleDto>) AND yaml_data_suspects_stack_count_rules_for_id(rule_id) returning Vec<SuspectStackCountRuleDto> for one rule's count rules (Codex review HIGH correction)"
    - "src/database.rs exposes FormIdEntryDto + db_pool_get_entry_typed + db_pool_get_entries_batch_typed (CXXS-05 additive per D-08; existing tab-delimited fns UNCHANGED)"
    - "Bridge db_pool_get_entries_batch_typed contract is documented: hit-only HashMap from core, fail-soft repackaging into per-input FormIdEntryDto with `found: false` for misses, recommended chunk size to avoid UI stalls (Codex review MEDIUM correction)"
    - "All new shared structs are flat — SuspectStackRuleMetadataDto contains only String + i32 + Vec<String> fields (NO nested Vec<Struct>); SuspectStackCountRuleDto has only String + u32 fields; FormIdEntryDto has only String + bool fields (Pitfall 6 CLEAR per Codex HIGH correction)"
    - "Existing config.rs and database.rs fns UNCHANGED (D-08 additive — no replacements)"
    - "Incremental build_cli.ps1 -Test and build_gui.ps1 -Test exit 0"
    - "python tools/cxx_api_parity/check_parity_gate.py --repo-root . exits 0 with 0 drift"
    - "Plan documents the D-11 N/A justification with evidence (no current narrowed call sites for typed FormID or suspect rules in classic-cli/classic-gui per grep search) — Codex review MEDIUM correction"
  artifacts:
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs"
      provides: "Widened config bridge with SuspectErrorRuleDto + flattened SuspectStackRuleMetadataDto + SuspectStackCountRuleDto + suspects_error_rules() + suspects_stack_rules_metadata() + suspects_stack_count_rules_for_id() (CXXS-07 with Pitfall 6 fix)"
      contains: "yaml_data_suspects_error_rules"
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs"
      provides: "Widened database bridge with FormIdEntryDto + db_pool_get_entry_typed + db_pool_get_entries_batch_typed (CXXS-05) — documented hit-only batch contract"
      contains: "FormIdEntryDto"
  key_links:
    - from: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs"
      to: "classic-config-core::yamldata (SuspectErrorRule, SuspectStackRule, SuspectStackCountRule)"
      via: "use classic_config_core::yamldata::*"
      pattern: "SuspectErrorRule"
    - from: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs"
      to: "classic-database-core::pool_sqlx (DbPool::get_entry / get_entries_batch returning Option/HashMap of hits)"
      via: "DbPool method calls returning typed Option/HashMap, mapped to FormIdEntryDto"
      pattern: "FormIdEntryDto"
---

<objective>
Add CXXS-07 (config suspect-rule subset) and CXXS-05 (database typed result API) bridge surfaces. Both are ADDITIVE per D-08 — existing helpers stay unchanged. The suspect-stack rule structure is FLATTENED into a metadata DTO + a separate count-rule getter to clear Pitfall 6. The database typed batch fn explicitly documents hit-only semantics and a recommended chunk size.

**REVIEWS-MODE NOTE (Codex review HIGH — Pitfall 6):** A previous version of this plan defined `SuspectStackRuleDto` containing `stack_contains_at_least: Vec<SuspectStackCountRuleDto>` and returned `Vec<SuspectStackRuleDto>` from `yaml_data_suspects_stack_rules`. That is `Vec<StructWithVec>` — the exact pattern the phase's own Pitfall 6 rule forbids. This plan flattens to TWO bridge fns:
1. `yaml_data_suspects_stack_rules_metadata() -> Vec<SuspectStackRuleMetadataDto>` — the metadata DTO has `id`, `name`, `severity`, plus the four `Vec<String>` pattern fields, but NO `Vec<SuspectStackCountRuleDto>` field.
2. `yaml_data_suspects_stack_count_rules_for_id(rule_id: &str) -> Vec<SuspectStackCountRuleDto>` — keyed by rule id; C++ callers iterate the metadata first, then call this getter for each rule that needs its count rules.

The previous note that "SuspectStackCountRuleDto has no Vec fields, satisfying the rule" was a misreading: Pitfall 6 forbids `Vec<StructWithVec>` regardless of whether the inner struct has vec-of-struct fields. Vec<String> inside the inner struct is irrelevant — what matters is that the OUTER Vec contains a Struct with a Vec field. The existing `Vec<YamlDataModSolutionEntry>` precedent is NOT a license for arbitrary nesting; it's a single specific case where the inner Vec<String> happens to work. The CXX rule is restrictive, and the safest path is to flatten.

**REVIEWS-MODE NOTE (Codex review MEDIUM):** A previous version of this plan did not document the batch-lookup contract. The REAL `classic_database_core::pool_sqlx::DbPool::get_entries_batch` returns `HashMap<String, String>` keyed by `"formid:plugin"` containing ONLY hits — misses are absent. The bridge wrapper MUST repackage the result into a per-input Vec where missing inputs get `found: false`. This contract is now spelled out in a dedicated section below.

**REVIEWS-MODE NOTE (Codex review MEDIUM):** A previous version of this plan treated D-11 as N/A without evidence. This plan adds an explicit D-11 N/A JUSTIFICATION section documenting the grep searches that prove no current narrowed call sites exist in `classic-cli` or `classic-gui` for typed FormID lookups or suspect-rule readers. The new typed surfaces remain available for FUTURE consumer migration in subsequent plans / phases.

Per RESEARCH.md §"classic-config-core" §"RESOLUTION for CXXS-07", the SuspectErrorRule case is simpler: `SuspectErrorRuleDto { id, name, severity, main_error_contains_any: Vec<String> }` is Pitfall 6 valid because the inner Vec<String> is the established precedent (matches `YamlDataModSolutionCriteria.any: Vec<String>`). The complication is the suspect-stack rule's nested `Vec<SuspectStackCountRule>`, which the flattening above eliminates.

Purpose: These two CXXS items both touch existing bridge files (`config.rs` and `database.rs`) and share a common pattern (additive structured DTO alongside legacy fail-soft path). Combining them in one plan keeps each plan focused. No new build.rs entries → no D-10 mandatory clean-build pair → incremental builds suffice.

Output: Widened config + database bridges with new typed surfaces, Pitfall-6-clean DTOs, documented batch contract, explicit D-11 N/A justification; refreshed parity baseline committed atomically.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md
@.planning/phases/02-cxx-bridge-surface-expansion/02-RESEARCH.md
@.planning/phases/02-cxx-bridge-surface-expansion/02-VALIDATION.md
@.planning/phases/02-cxx-bridge-surface-expansion/02-REVIEWS.md

# Source-of-truth Rust crates
@ClassicLib-rs/business-logic/classic-config-core/src/yamldata.rs
@ClassicLib-rs/business-logic/classic-database-core/src/pool_sqlx.rs

# Bridge files this plan widens
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs

@tools/cxx_api_parity/check_parity_gate.py

<interfaces>
<!-- SuspectErrorRule + SuspectStackRule + SuspectStackCountRule REAL surface
     verified at classic-config-core/src/yamldata.rs:117-158. -->

```rust
pub struct SuspectErrorRule {
    pub id: String,
    pub name: String,
    pub severity: i32,
    pub main_error_contains_any: Vec<String>,
}

pub struct SuspectStackCountRule {
    pub substring: String,
    pub count: usize,    // bridged as u32
}

pub struct SuspectStackRule {
    pub id: String,
    pub name: String,
    pub severity: i32,
    pub main_error_required_any: Vec<String>,
    pub main_error_optional_any: Vec<String>,
    pub stack_contains_any: Vec<String>,
    pub exclude_if_stack_contains_any: Vec<String>,
    pub stack_contains_at_least: Vec<SuspectStackCountRule>,  // <<< Pitfall 6 hazard
}
```

Bridge DTOs (Pitfall 6 CLEAR via flattening — Codex HIGH correction):
```rust
struct SuspectErrorRuleDto {
    id: String,
    name: String,
    severity: i32,
    main_error_contains_any: Vec<String>,  // Vec<String> inner is OK
}

// Metadata only — NO Vec<SuspectStackCountRuleDto> field
struct SuspectStackRuleMetadataDto {
    id: String,
    name: String,
    severity: i32,
    main_error_required_any: Vec<String>,
    main_error_optional_any: Vec<String>,
    stack_contains_any: Vec<String>,
    exclude_if_stack_contains_any: Vec<String>,
}

// Returned by a separate getter keyed by rule id
struct SuspectStackCountRuleDto {
    substring: String,
    count: u32,
}
```

The bridge fns:
- `yaml_data_suspects_error_rules(data: &YamlData) -> Vec<SuspectErrorRuleDto>`
- `yaml_data_suspects_stack_rules_metadata(data: &YamlData) -> Vec<SuspectStackRuleMetadataDto>` (NEW — flattened)
- `yaml_data_suspects_stack_count_rules_for_id(data: &YamlData, rule_id: &str) -> Vec<SuspectStackCountRuleDto>` (NEW — separate getter)

For database.rs, the FormIdEntryDto + bridge fns:
```rust
struct FormIdEntryDto {
    formid: String,
    plugin: String,
    value: String,
    found: bool,
}
```

Bridge fns:
- `db_pool_get_entry_typed(pool: &DbPool, formid: &str, plugin: &str) -> FormIdEntryDto`
- `db_pool_get_entries_batch_typed(pool: &DbPool, formids: &[String], plugins: &[String]) -> Vec<FormIdEntryDto>`
</interfaces>

<batch_lookup_contract>
<!-- Codex review MEDIUM correction: spell out the batch contract explicitly. -->

**Core API behavior** (verified at `classic-database-core/src/pool_sqlx.rs:1037-1042`):
```rust
pub async fn get_entries_batch(
    &self,
    formid_plugin_pairs: Vec<(String, String)>,
    table: Option<&str>,
    batch_size: usize,
) -> Result<HashMap<String, String>, DatabaseError>
```

The returned `HashMap` is **hit-only**: keys are `"formid:plugin"` strings, values are entry text. Missing pairs are ABSENT from the map — not present with empty value, not present with `null`. This is a MAJOR contract distinction that C++ callers must understand.

**Bridge wrapper repackaging contract:**

`db_pool_get_entries_batch_typed` MUST iterate the input `(formids, plugins)` parallel slices and produce ONE `FormIdEntryDto` PER INPUT PAIR. For each input pair:
- If the core HashMap contains an entry for `"{formid}:{plugin}"` → `FormIdEntryDto { formid, plugin, value, found: true }`
- Otherwise → `FormIdEntryDto { formid, plugin, value: String::new(), found: false }`

This positional repackaging means C++ callers can rely on `result[i]` corresponding to `(formids[i], plugins[i])` — even when the input is huge and most pairs are misses. Without this repackaging, C++ callers would have to parse the HashMap key format themselves and reconcile against the input list, which is error-prone.

**Recommended chunk size:**

- The core's `batch_size` parameter has a clamped maximum (`MAX_STABLE_BATCH_BUCKET` per `pool_sqlx.rs:1103`). The bridge wrapper passes `100` as the default chunk size, which empirically balances SQL query overhead against UI thread responsiveness.
- C++ callers requesting more than ~1000 entries in one call should chunk on their side to avoid blocking the Qt event loop. The bridge wrapper does NOT chunk on behalf of the caller; it processes the entire `formids` slice in one runtime block_on call.
- Future enhancement: a `db_pool_get_entries_batch_typed_chunked(pool, formids, plugins, chunk_size)` variant could expose the chunk_size parameter directly. NOT in scope for Phase 2.

**Length-mismatch handling:**

If `formids.len() != plugins.len()`, the bridge wrapper returns an empty `Vec<FormIdEntryDto>` (fail-soft, NOT an error). This matches the existing `db_pool_get_entries_batch` (tab-delimited) behavior pattern and is documented in the wrapper's doc comment.

**Empty-input handling:**

If `formids.is_empty()`, the bridge wrapper returns an empty `Vec<FormIdEntryDto>` immediately without calling the core fn (avoids unnecessary runtime block_on cost).

**Single-entry contract:**

`db_pool_get_entry_typed` (the singular variant) takes one `(formid, plugin)` pair and returns one `FormIdEntryDto`. Cache hits, cache misses, and core errors all map to a single DTO with `found: true` (cache hit or DB hit) or `found: false` (miss or error). This matches the existing fail-soft `db_pool_get_entry` (returns `""`) behavior pattern but adds the `found` flag for unambiguous miss detection.
</batch_lookup_contract>

<d11_na_justification>
<!-- Codex review MEDIUM correction: explicit evidence-backed N/A. -->

**D-11 status: N/A (justified)** — neither typed FormID lookups nor suspect-rule structured readers have any current narrowed call sites in `classic-cli` or `classic-gui`.

**Evidence (grep searches performed):**

```bash
# Typed FormID API consumers
grep -rn 'db_pool_get_entry\|db_pool_get_entries_batch' classic-cli/src/ classic-gui/src/
# Result: NO matches in either frontend (the FormID lookup pipeline is entirely
# wrapped by classic::scanner::* and stays in the Rust orchestrator).

# Suspect-rule readers
grep -rn 'yaml_data_suspects_\|SuspectErrorRule\|SuspectStackRule' classic-cli/src/ classic-gui/src/
# Result: NO matches (suspect rule consumption is entirely inside classic-scanlog-core's
# Rust analysis pipeline; C++ frontends consume only the rendered scan report text).

# General config bridge consumers
grep -rn 'classic::config::yaml_data_' classic-cli/src/ classic-gui/src/
# Result: NO matches (the config bridge YamlData type is not currently passed
# across the C++ boundary by either frontend; classic-gui uses classic::yaml::*
# for raw YAML ops via settingsdialog.cpp, not the high-level YamlData wrapper).
```

**Why the typed surfaces still belong in this plan despite N/A D-11:**

1. CXXS-05 and CXXS-07 are explicit phase requirements — the parity gate must show the surface exists.
2. Future plans (e.g., a Phase 6 "single-source-of-truth scanner UI" or a Phase 5 CI gate that exercises every bridge fn from a synthetic test) need these surfaces to be discoverable from C++.
3. Adding a synthetic / debug-only consumer purely to satisfy D-11 would be artificial padding — it wouldn't represent a real product flow and would have to be removed later. The Codex review explicitly allows N/A "if a plan has TRULY no real caller (defensible only after investigation)".

**Follow-up backlog (out of Phase 2 scope):**

- A future Phase could migrate `classic-cli/src/scanner.cpp` to call `db_pool_get_entry_typed` directly for the FormID resolution loop (currently delegated to `classic::scanner::orchestrator_*`).
- A future Phase could expose the suspect-rule list in a Settings tab in `classic-gui` (e.g., "Diagnostic rule editor"), which would consume `yaml_data_suspects_*_rules`.
</d11_na_justification>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Widen config.rs with SuspectErrorRuleDto + FLATTENED suspect-stack surface (Codex HIGH Pitfall 6 fix) + tests</name>

  <files>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs
  </files>

  <read_first>
    - ClassicLib-rs/business-logic/classic-config-core/src/yamldata.rs (READ — confirm exact SuspectErrorRule and SuspectStackRule field names; confirm SuspectStackCountRule field names; confirm how to ACCESS them from a YamlData instance — likely via `data.inner.suspects_error_rules` or a getter; read parse_suspect_error_rules around line 964 to see how the fields are populated)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs (current state — has the YamlDataModSolutionEntry / YamlDataModSolutionCriteria pattern; the new SuspectErrorRuleDto follows the SAME pattern; the new SuspectStackRuleMetadataDto has flat Vec<String> fields ONLY)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-REVIEWS.md §"Plan 07" (the HIGH Pitfall 6 concern)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-RESEARCH.md §"classic-config-core (CXXS-07)" §"Pitfall 6 DTO Validation"
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-08 (additive, do not replace existing fns), D-12 (Rust tests)
  </read_first>

  <behavior>
    - Test: `yaml_data_suspects_error_rules(empty_yaml_data)` returns empty Vec.
    - Test: `yaml_data_suspects_error_rules(yaml_data_with_one_rule)` returns Vec with 1 element whose `id`, `name`, `severity`, and `main_error_contains_any` match what was loaded.
    - Test: `yaml_data_suspects_stack_rules_metadata(empty_yaml_data)` returns empty Vec.
    - Test: `yaml_data_suspects_stack_rules_metadata(yaml_data_with_one_rule)` returns Vec with 1 element whose all 5 string-list fields match — and the DTO has NO stack_contains_at_least field.
    - Test: `yaml_data_suspects_stack_count_rules_for_id(yaml_data_with_count_rule, "rule_id")` returns Vec<SuspectStackCountRuleDto> populated with substring + count for the matching rule.
    - Test: `yaml_data_suspects_stack_count_rules_for_id(yaml_data, "definitely_not_a_real_rule_id")` returns empty Vec.
    - Test (regression): `yaml_data_suspects_error_keys` and `yaml_data_suspects_error_values` and `yaml_data_suspects_stack_keys` still work and return their original data (D-08 backward compat).
  </behavior>

  <action>
  Edit `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs`. KEEP everything unchanged. ADD new wrapper fns and extend the bridge block.

  Step 1 — Add imports (or extend existing) for the SuspectErrorRule / SuspectStackRule / SuspectStackCountRule core types:
  ```rust
  use classic_config_core::yamldata::{
      SuspectErrorRule as CoreSuspectErrorRule,
      SuspectStackRule as CoreSuspectStackRule,
      SuspectStackCountRule as CoreSuspectStackCountRule,
  };
  ```
  IMPORTANT: If these types are not directly imported from `yamldata` but from a sub-module, use the actual path.

  Step 2 — Add wrapper fns:
  ```rust
  fn yaml_data_suspects_error_rules(data: &YamlData) -> Vec<ffi::SuspectErrorRuleDto> {
      // Access the underlying list — the exact accessor matches how the existing
      // `yaml_data_suspects_error_keys` accesses the data. Read config.rs for the
      // current pattern and replicate it.
      data.inner
          .suspects_error_rules
          .iter()
          .map(|r: &CoreSuspectErrorRule| ffi::SuspectErrorRuleDto {
              id: r.id.clone(),
              name: r.name.clone(),
              severity: r.severity,
              main_error_contains_any: r.main_error_contains_any.clone(),
          })
          .collect()
  }

  // FLATTENED metadata — NO Vec<Struct> field (Pitfall 6 fix per Codex HIGH correction)
  fn yaml_data_suspects_stack_rules_metadata(data: &YamlData) -> Vec<ffi::SuspectStackRuleMetadataDto> {
      data.inner
          .suspects_stack_rules
          .iter()
          .map(|r: &CoreSuspectStackRule| ffi::SuspectStackRuleMetadataDto {
              id: r.id.clone(),
              name: r.name.clone(),
              severity: r.severity,
              main_error_required_any: r.main_error_required_any.clone(),
              main_error_optional_any: r.main_error_optional_any.clone(),
              stack_contains_any: r.stack_contains_any.clone(),
              exclude_if_stack_contains_any: r.exclude_if_stack_contains_any.clone(),
              // Note: stack_contains_at_least is NOT included here — exposed via separate getter
          })
          .collect()
  }

  // Separate getter keyed by rule id (Pitfall 6 fix)
  fn yaml_data_suspects_stack_count_rules_for_id(
      data: &YamlData,
      rule_id: &str,
  ) -> Vec<ffi::SuspectStackCountRuleDto> {
      data.inner
          .suspects_stack_rules
          .iter()
          .find(|r| r.id == rule_id)
          .map(|r| {
              r.stack_contains_at_least
                  .iter()
                  .map(|c: &CoreSuspectStackCountRule| ffi::SuspectStackCountRuleDto {
                      substring: c.substring.clone(),
                      count: c.count as u32,
                  })
                  .collect()
          })
          .unwrap_or_default()
  }
  ```

  IMPORTANT: The exact accessor (`data.inner.suspects_error_rules` vs `data.inner.suspects_error.clone()` vs whatever the actual API is) MUST be confirmed by reading config.rs to see how the existing `yaml_data_suspects_error_keys` accesses the same data. Replicate that pattern. If the existing fn iterates `data.inner().suspects_error_rules.iter().map(|r| r.id.clone())`, then the new fn iterates the same source and maps to the full DTO.

  Step 3 — Extend the existing `#[cxx::bridge(namespace = "classic::config")]` block. Add three new shared structs + three new extern declarations (NOT one — the suspect-stack rules now use TWO bridge fns to clear Pitfall 6):

  ```rust
  #[cxx::bridge(namespace = "classic::config")]
  mod ffi {
      // EXISTING (KEEP UNCHANGED)
      // CacheStats, YamlDataModSolutionCriteria, YamlDataModSolutionEntry,
      // type YamlData, plus ALL existing extern fns

      // NEW for CXXS-07
      struct SuspectErrorRuleDto {
          id: String,
          name: String,
          severity: i32,
          main_error_contains_any: Vec<String>,
      }

      // FLATTENED — NO Vec<Struct> field (Pitfall 6 fix per Codex HIGH correction)
      struct SuspectStackRuleMetadataDto {
          id: String,
          name: String,
          severity: i32,
          main_error_required_any: Vec<String>,
          main_error_optional_any: Vec<String>,
          stack_contains_any: Vec<String>,
          exclude_if_stack_contains_any: Vec<String>,
      }

      // Returned by a separate getter keyed by rule id
      struct SuspectStackCountRuleDto {
          substring: String,
          count: u32,
      }

      extern "Rust" {
          // (all existing fns preserved here)

          // NEW
          fn yaml_data_suspects_error_rules(data: &YamlData) -> Vec<SuspectErrorRuleDto>;
          fn yaml_data_suspects_stack_rules_metadata(data: &YamlData) -> Vec<SuspectStackRuleMetadataDto>;
          fn yaml_data_suspects_stack_count_rules_for_id(
              data: &YamlData,
              rule_id: &str,
          ) -> Vec<SuspectStackCountRuleDto>;
      }
  }
  ```

  Step 4 — Extend the `#[cfg(test)]` block. The tests construct a YamlData using the existing test pattern:

  ```rust
  #[test]
  fn test_yaml_data_suspects_error_rules_empty() {
      // construct empty YamlData per the existing test pattern (e.g., using a minimal fixture YAML or YamlData::default())
      let data = /* ... */;
      assert!(yaml_data_suspects_error_rules(&data).is_empty());
  }

  #[test]
  fn test_yaml_data_suspects_error_rules_with_loaded_rules() {
      // load a fixture YAML that includes at least one Crashlog_Error_Check entry
      let data = /* ... */;
      let rules = yaml_data_suspects_error_rules(&data);
      assert!(!rules.is_empty());
      let first = &rules[0];
      assert!(!first.id.is_empty());
      assert!(!first.name.is_empty());
      assert!(!first.main_error_contains_any.is_empty());
      let _ = first.severity;
  }

  #[test]
  fn test_yaml_data_suspects_stack_rules_metadata_no_count_rules_field() {
      // The DTO must NOT have a stack_contains_at_least field — verified by struct shape.
      // This compile-time check ensures Pitfall 6 is structurally cleared.
      let data = /* ... */;
      let metadata = yaml_data_suspects_stack_rules_metadata(&data);
      // For a fixture with at least one rule:
      for rule in &metadata {
          // Iterate every flat Vec<String> field — none of them are nested structs
          let _ = &rule.main_error_required_any;
          let _ = &rule.main_error_optional_any;
          let _ = &rule.stack_contains_any;
          let _ = &rule.exclude_if_stack_contains_any;
      }
  }

  #[test]
  fn test_yaml_data_suspects_stack_count_rules_for_id_unknown_returns_empty() {
      let data = /* ... */;
      let count_rules = yaml_data_suspects_stack_count_rules_for_id(&data, "definitely_not_a_real_id_xyz");
      assert!(count_rules.is_empty());
  }

  #[test]
  fn test_yaml_data_suspects_stack_count_rules_for_id_known_returns_populated() {
      // Load a fixture with a stack rule that has at least one count rule
      let data = /* ... */;
      let metadata = yaml_data_suspects_stack_rules_metadata(&data);
      // Find a rule whose id we know has count rules
      let target_id = metadata
          .iter()
          .find(|r| /* fixture-specific predicate */)
          .map(|r| r.id.clone());
      if let Some(id) = target_id {
          let count_rules = yaml_data_suspects_stack_count_rules_for_id(&data, &id);
          for cr in &count_rules {
              assert!(!cr.substring.is_empty());
              assert!(cr.count > 0);
          }
      }
  }
  ```

  IMPORTANT: The exact YamlData construction in tests depends on the existing test pattern in `config.rs`. If config.rs tests use `YamlData::default()` or load from a fixture YAML file, the new tests follow the same approach. The test fixture must include Crashlog_Error_Check and Crashlog_Stack_Check sections for the tests to be meaningful — if no such fixture exists, the executor creates a minimal in-memory YamlData with hand-constructed suspect rules in the test module only.

  Step 5 — Run `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml config::tests` and confirm all pass (existing + 5 new). Run clippy.
  </action>

  <verify>
    <automated>cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml config::tests</automated>
  </verify>

  <acceptance_criteria>
    - `git grep -n 'fn yaml_data_suspects_error_rules' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs` returns 2 matches (definition + extern)
    - `git grep -n 'fn yaml_data_suspects_stack_rules_metadata' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs` returns 2 matches (definition + extern)
    - `git grep -n 'fn yaml_data_suspects_stack_count_rules_for_id' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs` returns 2 matches
    - `git grep -nE 'struct (SuspectErrorRuleDto|SuspectStackRuleMetadataDto|SuspectStackCountRuleDto)' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs` returns 3+ shared struct declarations
    - `git grep -n 'stack_contains_at_least: Vec<' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs` returns NOTHING (Pitfall 6 fix verified — the nested Vec<Struct> field is gone)
    - `git grep -n 'struct SuspectStackRuleDto' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs` returns NOTHING (the old combined DTO is gone — only the metadata DTO + count rule DTO exist now)
    - `git grep -n 'fn yaml_data_suspects_error_keys' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs` STILL returns the existing fn (D-08 — additive)
    - `git grep -n 'fn yaml_data_suspects_stack_keys' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs` STILL returns the existing fn (D-08)
    - `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml config::tests` exits 0 with at least 5 new passing tests
    - `cargo build -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml` exits 0 (no Pitfall 6 errors — no Vec<StructWithVec>)
    - `cargo clippy -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` exits 0
  </acceptance_criteria>

  <done>
    `src/config.rs` exposes the full CXXS-07 surface with the suspect-stack rules FLATTENED into metadata + per-rule count getter (Pitfall 6 fix per Codex HIGH correction), all tests pass, no existing fns removed.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Widen database.rs with FormIdEntryDto + db_pool_get_entry_typed + db_pool_get_entries_batch_typed (CXXS-05) + documented batch contract + tests</name>

  <files>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs
  </files>

  <read_first>
    - ClassicLib-rs/business-logic/classic-database-core/src/pool_sqlx.rs (READ — confirm exact `get_entry(formid, plugin, table)` and `get_entries_batch(pairs, table, batch_size)` signatures; CONFIRM the HashMap key format is `"formid:plugin"` per pool_sqlx.rs:1073; confirm the HashMap is hit-only)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs (current state — has db_pool_get_entry returning String "" on miss, db_pool_get_entries_batch returning Vec<String> tab-delimited; KEEP these unchanged per D-08; read the existing wrapper bodies to see how they call into pool.inner)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-REVIEWS.md §"Plan 07" Codex MEDIUM concern about batch contract
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-08 (additive — keep tab-delimited path), D-12
  </read_first>

  <behavior>
    - Test: `db_pool_get_entry_typed` on a fresh (uninitialized) pool returns FormIdEntryDto with `found: false` and the input `formid`/`plugin` echoed back, `value: ""`.
    - Test: `db_pool_get_entries_batch_typed` with empty input slices returns empty Vec.
    - Test: `db_pool_get_entries_batch_typed` with one (formid, plugin) pair on uninitialized pool returns Vec with EXACTLY 1 element where `found: false` and the original formid/plugin are echoed back (positional repackaging contract).
    - Test: `db_pool_get_entries_batch_typed` with two (formid, plugin) pairs on uninitialized pool returns Vec with EXACTLY 2 elements; result[0] corresponds to (formids[0], plugins[0]) and result[1] corresponds to (formids[1], plugins[1]).
    - Test: parallel-vec length mismatch in `db_pool_get_entries_batch_typed(pool, &["a"], &[])` returns empty Vec (fail-soft, not Err).
    - Test (regression): `db_pool_get_entry` and `db_pool_get_entries_batch` (existing) still work and return their original String/Vec<String> shapes.
  </behavior>

  <action>
  Edit `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs`. KEEP existing fns + DTOs unchanged. ADD new typed surface.

  Step 1 — Add wrapper fns ABOVE the bridge block (or after the existing wrapper fns):

  ```rust
  /// Typed single-entry FormID lookup.
  ///
  /// Returns a `FormIdEntryDto` with `found: true` if the entry exists in the
  /// database (or cache), or `found: false` for misses or errors. The input
  /// `formid` and `plugin` are echoed back in the result so C++ callers don't
  /// have to track the input separately.
  ///
  /// Bridge contract: this is the typed alternative to `db_pool_get_entry`
  /// (which returns `""` on miss). Both fns coexist per D-08.
  fn db_pool_get_entry_typed(pool: &DbPool, formid: &str, plugin: &str) -> ffi::FormIdEntryDto {
      let runtime = classic_shared_core::get_runtime();
      // Use the same async lock pattern as the existing db_pool_get_entry wrapper.
      let result = runtime.block_on(async {
          pool.inner.get_entry(formid, plugin, None).await
      });

      let value = match result {
          Ok(Some(v)) => v,
          _ => String::new(),
      };
      let found = !value.is_empty();
      ffi::FormIdEntryDto {
          formid: formid.to_string(),
          plugin: plugin.to_string(),
          value,
          found,
      }
  }

  /// Typed batch FormID lookup with positional repackaging.
  ///
  /// Bridge contract (Codex review MEDIUM correction):
  /// - The core `get_entries_batch` returns a HIT-ONLY HashMap keyed by
  ///   `"formid:plugin"`. Misses are absent from the map.
  /// - This wrapper repackages the result into ONE `FormIdEntryDto` PER INPUT
  ///   PAIR — `result[i]` corresponds to `(formids[i], plugins[i])`.
  /// - Misses get `found: false` and `value: ""`.
  /// - Length mismatch between `formids` and `plugins` returns empty Vec
  ///   (fail-soft, NOT an error).
  /// - Empty input returns empty Vec immediately (no runtime cost).
  /// - The internal batch_size parameter is set to 100 (a balance between
  ///   SQL overhead and UI responsiveness — see plan's Batch Lookup Contract
  ///   section). C++ callers requesting >1000 entries should chunk on their
  ///   side to avoid blocking the Qt event loop.
  fn db_pool_get_entries_batch_typed(
      pool: &DbPool,
      formids: &[String],
      plugins: &[String],
  ) -> Vec<ffi::FormIdEntryDto> {
      if formids.len() != plugins.len() || formids.is_empty() {
          return Vec::new();
      }
      let runtime = classic_shared_core::get_runtime();
      let pairs: Vec<(String, String)> = formids
          .iter()
          .zip(plugins.iter())
          .map(|(f, p)| (f.clone(), p.clone()))
          .collect();

      // Core API: get_entries_batch(formid_plugin_pairs: Vec<(String, String)>, table: Option<&str>, batch_size: usize)
      // Returns HashMap<String, String> keyed by "formid:plugin", hit-only.
      let map = runtime.block_on(async {
          pool.inner
              .get_entries_batch(pairs.clone(), None, 100)
              .await
              .unwrap_or_default()
      });

      // Positional repackaging — one DTO per input pair
      pairs
          .into_iter()
          .map(|(formid, plugin)| {
              let lookup_key = format!("{}:{}", formid, plugin);
              let value = map.get(&lookup_key).cloned().unwrap_or_default();
              let found = !value.is_empty();
              ffi::FormIdEntryDto { formid, plugin, value, found }
          })
          .collect()
  }
  ```

  IMPORTANT: The exact `pool.inner` access pattern depends on how `DbPool` is defined in database.rs. Read the existing `db_pool_get_entry` and `db_pool_get_entries_batch` wrappers to see how they call into the inner core type, and replicate the same pattern. The `unwrap_or_default()` falls in line with the existing fail-soft database wrapper philosophy.

  Step 2 — Extend the existing `#[cxx::bridge(namespace = "classic::database")]` block. Add the FormIdEntryDto shared struct + 2 new extern declarations:

  ```rust
  #[cxx::bridge(namespace = "classic::database")]
  mod ffi {
      // EXISTING (KEEP UNCHANGED)
      // type DbPool, plus all existing extern fns

      // NEW for CXXS-05
      struct FormIdEntryDto {
          formid: String,
          plugin: String,
          value: String,
          found: bool,
      }

      extern "Rust" {
          // (existing fns preserved here unchanged)

          // NEW
          fn db_pool_get_entry_typed(pool: &DbPool, formid: &str, plugin: &str) -> FormIdEntryDto;
          fn db_pool_get_entries_batch_typed(
              pool: &DbPool,
              formids: &[String],
              plugins: &[String],
          ) -> Vec<FormIdEntryDto>;
      }
  }
  ```

  Step 3 — Extend the `#[cfg(test)]` block:
  ```rust
  #[test]
  fn test_db_pool_get_entry_typed_uninitialized_returns_not_found() {
      let pool = db_pool_new("Fallout4", 4, 60); // existing constructor
      let result = db_pool_get_entry_typed(&pool, "0x000ABCDE", "Fallout4.esm");
      assert!(!result.found);
      assert_eq!(result.formid, "0x000ABCDE");
      assert_eq!(result.plugin, "Fallout4.esm");
      assert!(result.value.is_empty());
  }

  #[test]
  fn test_db_pool_get_entries_batch_typed_empty_returns_empty() {
      let pool = db_pool_new("Fallout4", 4, 60);
      let result = db_pool_get_entries_batch_typed(&pool, &[], &[]);
      assert!(result.is_empty());
  }

  #[test]
  fn test_db_pool_get_entries_batch_typed_length_mismatch_returns_empty() {
      let pool = db_pool_new("Fallout4", 4, 60);
      let result = db_pool_get_entries_batch_typed(
          &pool,
          &["0x000ABCDE".to_string()],
          &[],
      );
      assert!(result.is_empty());
  }

  #[test]
  fn test_db_pool_get_entries_batch_typed_uninitialized_positional_repackaging() {
      let pool = db_pool_new("Fallout4", 4, 60);
      let result = db_pool_get_entries_batch_typed(
          &pool,
          &["0x000ABCDE".to_string(), "0x000FEDCB".to_string()],
          &["Fallout4.esm".to_string(), "Fallout4.esm".to_string()],
      );
      // Positional repackaging contract: ONE DTO PER INPUT
      assert_eq!(result.len(), 2);
      assert_eq!(result[0].formid, "0x000ABCDE");
      assert_eq!(result[1].formid, "0x000FEDCB");
      for entry in &result {
          assert!(!entry.found);
          assert!(entry.value.is_empty());
      }
  }
  ```

  Step 4 — Run `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml database::tests` and confirm all pass.
  </action>

  <verify>
    <automated>cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml database::tests</automated>
  </verify>

  <acceptance_criteria>
    - `git grep -n 'fn db_pool_get_entry_typed' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs` returns 2 matches (definition + extern)
    - `git grep -n 'fn db_pool_get_entries_batch_typed' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs` returns 2 matches
    - `git grep -n 'struct FormIdEntryDto' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs` returns the shared struct declaration
    - `git grep -n 'positional repackaging\|hit-only\|found: false' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs` returns at least one comment line documenting the contract (Codex MEDIUM correction proof)
    - `git grep -n 'fn db_pool_get_entry' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs` STILL returns the existing fn (D-08 — additive, not replaced)
    - `git grep -n 'fn db_pool_get_entries_batch' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs` STILL returns the existing fn
    - `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml database::tests` exits 0 with at least 4 new passing tests (including positional repackaging test)
    - `cargo clippy -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` exits 0
  </acceptance_criteria>

  <done>
    `src/database.rs` exposes the FormIdEntryDto typed API alongside the existing tab-delimited path with documented hit-only batch contract and positional repackaging (Codex MEDIUM correction), all tests pass, no regressions.
  </done>
</task>

<task type="auto">
  <name>Task 3: Incremental builds, refresh D-09 baseline, atomic commit (D-11 N/A justification documented in plan body)</name>

  <files>
    - docs/implementation/cxx_api_parity/baseline/parity_contract.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.json
    - docs/implementation/cxx_api_parity/baseline/cxx_diff_report.md
    - docs/implementation/cxx_api_parity/baseline/cxx_gate_report.md
  </files>

  <read_first>
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-09 (per-plan baseline refresh), D-10 (NOT triggered — no new build.rs entries)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-VALIDATION.md row 2-07-01
  </read_first>

  <action>
  ## Part A — Incremental builds (NO -Clean — config.rs and database.rs are already in build.rs)

  ```
  pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
  pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
  ```

  Both must exit 0.

  ## Part B — D-09 baseline refresh

  ```
  python tools/cxx_api_parity/check_parity_gate.py --update-baseline --repo-root .
  python tools/cxx_api_parity/check_parity_gate.py --repo-root .
  ```

  ## Part C — D-11 N/A justification (Codex review MEDIUM correction)

  Per the D-11 N/A justification section in this plan's `<context>` block, no new C++ consumer migration is added in this plan because no current narrowed call sites exist for typed FormID lookups or suspect-rule readers in `classic-cli` or `classic-gui`. The grep evidence is documented in the plan body. The new typed surfaces remain available for future consumer migration.

  Verify the grep evidence still holds at execution time:
  ```bash
  grep -rn 'db_pool_get_entry\|db_pool_get_entries_batch' classic-cli/src/ classic-gui/src/  # Expected: NO matches
  grep -rn 'yaml_data_suspects_\|SuspectErrorRule\|SuspectStackRule' classic-cli/src/ classic-gui/src/  # Expected: NO matches
  grep -rn 'classic::config::yaml_data_' classic-cli/src/ classic-gui/src/  # Expected: NO matches
  ```

  Document the grep results in the SUMMARY.md as confirmation.

  ## Part D — Atomic commit

  Stage:
  - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs`
  - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs`
  - All 4 baseline artifacts

  Commit message: `Feat(02-07): expose suspect rules (CXXS-07) and typed FormID API (CXXS-05) in CXX bridge` — body mentions CXXS-05, CXXS-07, D-08 (additive), D-09, the Pitfall 6 flatten for suspect-stack rules (Codex HIGH correction), the documented batch lookup contract (Codex MEDIUM correction), and the D-11 N/A justification (Codex MEDIUM correction).
  </action>

  <verify>
    <automated>python tools/cxx_api_parity/check_parity_gate.py --repo-root .</automated>
  </verify>

  <acceptance_criteria>
    - `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test` exits 0
    - `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test` exits 0
    - `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` exits 0 with 0 drift
    - The committed `cxx_diff_report.md` shows ADDED rows under `bridgeModule: "config"` for SuspectErrorRuleDto, SuspectStackRuleMetadataDto, SuspectStackCountRuleDto + 3 new fns
    - The committed `cxx_diff_report.md` shows ADDED rows under `bridgeModule: "database"` for FormIdEntryDto + 2 new fns
    - `git log -1 --stat` shows the commit touches Rust source AND the parity baseline atomically
    - The committed `cxx_diff_report.md` shows ZERO REMOVED rows for `bridgeModule: "config"` or `bridgeModule: "database"` (D-08 — additive only)
  </acceptance_criteria>

  <done>
    Plan 02-07 complete — CXXS-05 and CXXS-07 satisfied; suspect-stack rules are flattened (Pitfall 6 cleared per Codex HIGH correction); batch lookup contract is documented (Codex MEDIUM correction); D-11 N/A is justified with grep evidence (Codex MEDIUM correction); both existing fail-soft paths preserved; parity gate at 0 drift.
  </done>
</task>

</tasks>

<verification>
1. `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml config::tests database::tests` — exits 0
2. Both incremental builds exit 0
3. Parity gate at 0 drift
4. CXXS-05 and CXXS-07 fully satisfied
5. No D-08 violations (existing fns unchanged)
6. Suspect-stack rules use flattened metadata + per-rule count getter (no Vec<StructWithVec>)
7. Batch lookup contract documented in plan + bridge wrapper doc comment

Validation Architecture (per 02-VALIDATION.md row 2-07-01): `cargo test -p classic-cpp-bridge config::tests database::tests` + `build_cli.ps1 -Test` + parity gate.
</verification>

<success_criteria>
- src/config.rs exposes SuspectErrorRuleDto, SuspectStackRuleMetadataDto (FLATTENED — no nested count rules), SuspectStackCountRuleDto + yaml_data_suspects_error_rules + yaml_data_suspects_stack_rules_metadata + yaml_data_suspects_stack_count_rules_for_id
- src/database.rs exposes FormIdEntryDto + db_pool_get_entry_typed + db_pool_get_entries_batch_typed with documented hit-only batch contract
- Pitfall 6 verified — NO Vec<Struct> field inside any returned `Vec<DtoX>` shape (Codex HIGH correction)
- All existing fns UNCHANGED (D-08 additive)
- Both incremental builds green
- Parity gate at 0 drift (D-09)
- D-11 N/A justified with explicit grep evidence (Codex MEDIUM correction)
- Atomic commit
</success_criteria>

<output>
After completion, create `.planning/phases/02-cxx-bridge-surface-expansion/02-07-SUMMARY.md` documenting:
- Confirmation that suspect-stack rules are flattened into metadata + per-rule getter (Pitfall 6 cleared per Codex HIGH correction)
- Confirmation that batch lookup contract is documented in plan body + bridge wrapper doc comment (Codex MEDIUM correction)
- Confirmation of D-11 N/A justification with grep results (Codex MEDIUM correction)
- Exact entries added (3 structs + 3 fns in config; 1 struct + 2 fns in database)
- Pitfall 6 verification: SuspectStackRuleMetadataDto has NO Vec<Struct> field; only Vec<String> (matches existing YamlDataModSolutionEntry precedent); CONFIRMED Pitfall 6 CLEAR
- Test results: positional repackaging test for db_pool_get_entries_batch_typed passes
</output>
