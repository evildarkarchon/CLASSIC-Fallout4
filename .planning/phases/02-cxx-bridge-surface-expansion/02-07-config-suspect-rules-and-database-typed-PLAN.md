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
    - "src/config.rs exposes SuspectStackRuleDto + SuspectStackCountRuleDto + yaml_data_suspects_stack_rules() returning the full rule set with all match patterns and count rules (CXXS-07)"
    - "src/database.rs exposes FormIdEntryDto + db_pool_get_entry_typed + db_pool_get_entries_batch_typed (CXXS-05 additive per D-08; existing tab-delimited fns UNCHANGED)"
    - "All new shared structs are valid CXX shared types — SuspectStackRuleDto contains Vec<SuspectStackCountRuleDto> where SuspectStackCountRuleDto has NO Vec fields (Pitfall 6 CLEAR per RESEARCH.md DTO table)"
    - "Existing config.rs and database.rs fns UNCHANGED (D-08 additive — no replacements)"
    - "Incremental build_cli.ps1 -Test and build_gui.ps1 -Test exit 0"
    - "python tools/cxx_api_parity/check_parity_gate.py --repo-root . exits 0 with 0 drift"
  artifacts:
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs"
      provides: "Widened config bridge with SuspectErrorRuleDto + SuspectStackRuleDto + suspects_error_rules() + suspects_stack_rules() (CXXS-07)"
      contains: "yaml_data_suspects_error_rules"
    - path: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs"
      provides: "Widened database bridge with FormIdEntryDto + db_pool_get_entry_typed + db_pool_get_entries_batch_typed (CXXS-05)"
      contains: "FormIdEntryDto"
  key_links:
    - from: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs"
      to: "classic-config-core::yamldata (SuspectErrorRule, SuspectStackRule, SuspectStackCountRule)"
      via: "use classic_config_core::yamldata::*"
      pattern: "SuspectErrorRule"
    - from: "ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs"
      to: "classic-database-core::pool_sqlx (typed get_entry / get_entries_batch returns)"
      via: "DbPool method calls returning typed Option/HashMap, mapped to FormIdEntryDto"
      pattern: "FormIdEntryDto"
---

<objective>
Add CXXS-07 (config suspect-rule subset) and CXXS-05 (database typed result API) bridge surfaces. Both are ADDITIVE per D-08 — existing helpers stay unchanged. Per RESEARCH.md §"classic-config-core" §"RESOLUTION for CXXS-07", `SuspectErrorRuleDto { id, name, severity, main_error_contains_any: Vec<String> }` is Pitfall 6 valid (Vec<String> inner is OK), and `SuspectStackRuleDto` contains a `Vec<SuspectStackCountRuleDto>` where `SuspectStackCountRuleDto` has only String + u32 fields (no Vecs) — also valid. Per RESEARCH.md §"classic-database-core pool_sqlx.rs (CXXS-05)", `FormIdEntryDto { formid, plugin, value, found }` is a flat additive complement to the existing tab-delimited path.

Purpose: These two CXXS items both touch existing bridge files (`config.rs` and `database.rs`) and share a common pattern (additive structured DTO alongside legacy fail-soft path). Combining them in one plan keeps each plan focused and within context budget. No new build.rs entries → no D-10 mandatory clean-build pair → incremental builds suffice.

Output: Widened config + database bridges with new typed surfaces; refreshed parity baseline committed atomically.
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

# Source-of-truth Rust crates
@ClassicLib-rs/business-logic/classic-config-core/src/yamldata.rs
@ClassicLib-rs/business-logic/classic-database-core/src/pool_sqlx.rs

# Bridge files this plan widens
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs
@ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs

@tools/cxx_api_parity/check_parity_gate.py

<interfaces>
<!-- Per RESEARCH.md §"classic-config-core" and §"classic-database-core pool_sqlx.rs". -->

SuspectErrorRule (per RESEARCH.md):
```rust
pub struct SuspectErrorRule {
    pub id: String,
    pub name: String,
    pub severity: i32,
    pub main_error_contains_any: Vec<String>,
}
```

SuspectStackRule:
```rust
pub struct SuspectStackRule {
    pub id: String,
    pub name: String,
    pub severity: i32,
    pub main_error_required_any: Vec<String>,
    pub main_error_optional_any: Vec<String>,
    pub stack_contains_any: Vec<String>,
    pub exclude_if_stack_contains_any: Vec<String>,
    pub stack_contains_at_least: Vec<SuspectStackCountRule>,
}
pub struct SuspectStackCountRule {
    pub substring: String,
    pub count: usize,
}
```

Bridge DTOs (Pitfall 6 CLEAR per RESEARCH.md DTO table):
```rust
struct SuspectErrorRuleDto {
    id: String,
    name: String,
    severity: i32,
    main_error_contains_any: Vec<String>,  // VALID — Vec<String> inner is OK (matches YamlDataModSolutionCriteria precedent)
}

struct SuspectStackCountRuleDto {
    substring: String,
    count: u32,  // narrowed from usize
}

struct SuspectStackRuleDto {
    id: String,
    name: String,
    severity: i32,
    main_error_required_any: Vec<String>,
    main_error_optional_any: Vec<String>,
    stack_contains_any: Vec<String>,
    exclude_if_stack_contains_any: Vec<String>,
    stack_contains_at_least: Vec<SuspectStackCountRuleDto>,  // VALID — SuspectStackCountRuleDto has NO Vec fields
}
```

The yamldata.rs accessors must expose the underlying SuspectErrorRule and SuspectStackRule lists. Look for fields like `data.suspects_error: Vec<SuspectErrorRule>` and `data.suspects_stack: Vec<SuspectStackRule>` (or whatever the actual field names are — confirm via direct read of yamldata.rs).

The existing bridge fns `yaml_data_suspects_error_keys/values/stack_keys` only expose the IDs/names — these stay UNCHANGED. The new fns return the full structured rules.

Bridge fns to add to config.rs:
- `yaml_data_suspects_error_rules(data: &YamlData) -> Vec<SuspectErrorRuleDto>`
- `yaml_data_suspects_stack_rules(data: &YamlData) -> Vec<SuspectStackRuleDto>`

For database.rs, add to the existing `#[cxx::bridge(namespace = "classic::database")]` block:

```rust
struct FormIdEntryDto {
    formid: String,
    plugin: String,
    value: String,
    found: bool,
}
```

Bridge fns to add:
- `db_pool_get_entry_typed(pool: &DbPool, formid: &str, plugin: &str) -> FormIdEntryDto`
- `db_pool_get_entries_batch_typed(pool: &DbPool, formids: &[String], plugins: &[String]) -> Vec<FormIdEntryDto>`

The existing `db_pool_get_entry` (returns `String`, "" on miss) and `db_pool_get_entries_batch` (returns `Vec<String>` tab-delimited) are UNCHANGED.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Widen config.rs with SuspectErrorRuleDto + SuspectStackRuleDto + new suspects_error_rules / suspects_stack_rules bridge fns + tests (CXXS-07)</name>

  <files>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs
  </files>

  <read_first>
    - ClassicLib-rs/business-logic/classic-config-core/src/yamldata.rs (READ — confirm exact SuspectErrorRule and SuspectStackRule field names; confirm SuspectStackCountRule field names; confirm how to ACCESS them from a YamlData instance — likely a getter or a public field like `data.suspects_error: Vec<SuspectErrorRule>`)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs (current state — has the YamlDataModSolutionEntry / YamlDataModSolutionCriteria pattern as the precedent for nested Vec<String> shared structs; the new SuspectErrorRuleDto follows the SAME pattern)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-RESEARCH.md §"classic-config-core (CXXS-07)" §"RESOLUTION for CXXS-07" §"Pitfall 6 DTO Validation"
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-08 (additive, do not replace existing fns), D-12 (Rust tests)
  </read_first>

  <behavior>
    - Test: `yaml_data_suspects_error_rules(empty_yaml_data)` returns empty Vec.
    - Test: `yaml_data_suspects_error_rules(yaml_data_with_one_rule)` returns Vec with 1 element whose `id`, `name`, `severity`, and `main_error_contains_any` match what was loaded.
    - Test: `yaml_data_suspects_stack_rules(empty_yaml_data)` returns empty Vec.
    - Test: `yaml_data_suspects_stack_rules(yaml_data_with_one_rule)` returns Vec with 1 element whose all 5 string-list fields match and whose `stack_contains_at_least` Vec is correctly populated.
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
      // Access the underlying list — exact accessor name confirmed via direct read
      // (e.g., data.inner.suspects_error or data.inner.get_suspects_error())
      data.suspects_error()
          .iter()
          .map(|r: &CoreSuspectErrorRule| ffi::SuspectErrorRuleDto {
              id: r.id.clone(),
              name: r.name.clone(),
              severity: r.severity,
              main_error_contains_any: r.main_error_contains_any.clone(),
          })
          .collect()
  }

  fn yaml_data_suspects_stack_rules(data: &YamlData) -> Vec<ffi::SuspectStackRuleDto> {
      data.suspects_stack()
          .iter()
          .map(|r: &CoreSuspectStackRule| ffi::SuspectStackRuleDto {
              id: r.id.clone(),
              name: r.name.clone(),
              severity: r.severity,
              main_error_required_any: r.main_error_required_any.clone(),
              main_error_optional_any: r.main_error_optional_any.clone(),
              stack_contains_any: r.stack_contains_any.clone(),
              exclude_if_stack_contains_any: r.exclude_if_stack_contains_any.clone(),
              stack_contains_at_least: r.stack_contains_at_least
                  .iter()
                  .map(|c: &CoreSuspectStackCountRule| ffi::SuspectStackCountRuleDto {
                      substring: c.substring.clone(),
                      count: c.count as u32,
                  })
                  .collect(),
          })
          .collect()
  }
  ```

  IMPORTANT: The exact accessor (`data.suspects_error()` vs `data.inner().suspects_error.clone()` vs whatever the actual API is) MUST be confirmed by reading config.rs to see how the existing `yaml_data_suspects_error_keys` accesses the same data. Replicate that pattern. If the existing fn iterates `data.inner().suspects_error.iter().map(|r| r.id.clone())`, then the new fn iterates the same source and maps to the full DTO.

  Step 3 — Extend the existing `#[cxx::bridge(namespace = "classic::config")]` block. Add three new shared structs + two new extern declarations:

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

      struct SuspectStackCountRuleDto {
          substring: String,
          count: u32,
      }

      struct SuspectStackRuleDto {
          id: String,
          name: String,
          severity: i32,
          main_error_required_any: Vec<String>,
          main_error_optional_any: Vec<String>,
          stack_contains_any: Vec<String>,
          exclude_if_stack_contains_any: Vec<String>,
          stack_contains_at_least: Vec<SuspectStackCountRuleDto>,
      }

      extern "Rust" {
          // (all existing fns preserved here)

          // NEW
          fn yaml_data_suspects_error_rules(data: &YamlData) -> Vec<SuspectErrorRuleDto>;
          fn yaml_data_suspects_stack_rules(data: &YamlData) -> Vec<SuspectStackRuleDto>;
      }
  }
  ```

  Step 4 — Extend the `#[cfg(test)]` block. The tests need a way to construct a YamlData with known suspect rules; the existing config.rs tests already do this — copy the pattern.

  ```rust
  #[test]
  fn test_yaml_data_suspects_error_rules_empty() {
      let data = /* construct empty YamlData per existing test pattern */;
      assert!(yaml_data_suspects_error_rules(&data).is_empty());
  }

  #[test]
  fn test_yaml_data_suspects_error_rules_with_loaded_rules() {
      let data = /* construct YamlData with at least one suspect_error rule using existing test fixture */;
      let rules = yaml_data_suspects_error_rules(&data);
      assert!(!rules.is_empty());
      let first = &rules[0];
      assert!(!first.id.is_empty());
      assert!(!first.name.is_empty());
      // severity is i32; can be any value, just verify access works
      let _ = first.severity;
  }

  #[test]
  fn test_yaml_data_suspects_stack_rules_empty() {
      let data = /* construct empty YamlData */;
      assert!(yaml_data_suspects_stack_rules(&data).is_empty());
  }

  #[test]
  fn test_yaml_data_suspects_stack_rules_count_rule_field_populated() {
      let data = /* construct YamlData with at least one stack rule that has a stack_contains_at_least entry */;
      let rules = yaml_data_suspects_stack_rules(&data);
      // Find a rule with non-empty count rules and verify the inner DTO is populated
      for rule in &rules {
          for count_rule in &rule.stack_contains_at_least {
              assert!(!count_rule.substring.is_empty());
              assert!(count_rule.count > 0);
          }
      }
  }
  ```

  IMPORTANT: The exact YamlData construction in tests depends on the existing test pattern in `config.rs`. If config.rs tests use `YamlData::default()` or load from a fixture YAML file, the new tests follow the same approach. If no test fixture provides suspect rules, the executor may need to create a minimal in-memory YamlData with suspect rules injected — only if necessary, and only as part of the test module.

  Step 5 — Run `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml config::tests` and confirm all pass (existing + 4 new). Run clippy.
  </action>

  <verify>
    <automated>cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml config::tests</automated>
  </verify>

  <acceptance_criteria>
    - `git grep -nE 'fn yaml_data_suspects_(error|stack)_rules' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs` returns 2+ wrapper definitions and 2+ extern declarations
    - `git grep -nE 'struct (SuspectErrorRuleDto|SuspectStackRuleDto|SuspectStackCountRuleDto)' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs` returns 3+ shared struct declarations
    - `git grep -n 'fn yaml_data_suspects_error_keys' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs` STILL returns the existing fn (D-08 — additive)
    - `git grep -n 'fn yaml_data_suspects_stack_keys' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs` STILL returns the existing fn (D-08)
    - `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml config::tests` exits 0 with at least 4 new passing tests
    - `cargo build -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml` exits 0 (no Pitfall 6 — SuspectStackCountRuleDto has no Vec fields, validating the Vec<SuspectStackCountRuleDto> usage is safe)
    - `cargo clippy -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` exits 0
  </acceptance_criteria>

  <done>
    `src/config.rs` exposes the full CXXS-07 surface (suspect error rules + suspect stack rules + count rules), all tests pass, no existing fns removed.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Widen database.rs with FormIdEntryDto + db_pool_get_entry_typed + db_pool_get_entries_batch_typed (CXXS-05) + tests</name>

  <files>
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs
  </files>

  <read_first>
    - ClassicLib-rs/business-logic/classic-database-core/src/pool_sqlx.rs (READ — confirm exact get_entry / get_entries_batch signatures returning typed Option/HashMap; confirm DbPool method names)
    - ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs (current state — has db_pool_get_entry returning String "" on miss, db_pool_get_entries_batch returning Vec<String> tab-delimited; KEEP these unchanged per D-08)
    - .planning/phases/02-cxx-bridge-surface-expansion/02-RESEARCH.md §"classic-database-core pool_sqlx.rs (CXXS-05)" §"Pitfall 6 DTO Validation"
    - .planning/phases/02-cxx-bridge-surface-expansion/02-CONTEXT.md decisions D-08 (additive — keep tab-delimited path), D-12
  </read_first>

  <behavior>
    - Test: `db_pool_get_entry_typed` on a fresh (uninitialized) pool returns FormIdEntryDto with `found: false` and empty value/formid/plugin echoed back as input.
    - Test: `db_pool_get_entries_batch_typed` with empty input slices returns empty Vec.
    - Test: `db_pool_get_entries_batch_typed` with one (formid, plugin) pair on uninitialized pool returns Vec with 1 element where `found: false` and the original formid/plugin are echoed back.
    - Test: parallel-vec length mismatch in `db_pool_get_entries_batch_typed(pool, &["a"], &[])` returns either empty Vec or fails-soft with one entry — confirm behavior and assert what core actually does. Recommend: align lengths before processing; mismatched returns empty Vec.
    - Test (regression): `db_pool_get_entry` and `db_pool_get_entries_batch` (existing) still work.
  </behavior>

  <action>
  Edit `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs`. KEEP existing fns + DTOs unchanged. ADD new typed surface.

  Step 1 — Add wrapper fns ABOVE the bridge block (or after the existing wrapper fns):
  ```rust
  fn db_pool_get_entry_typed(pool: &DbPool, formid: &str, plugin: &str) -> ffi::FormIdEntryDto {
      // The existing db_pool_get_entry calls into pool.get_entry(...) and returns String "" on miss.
      // For the typed variant, we want to know whether the result was a hit or a miss.
      // If pool.get_entry returns Result<Option<String>, _>, we can map None->found:false and Some(v)->found:true.
      // The exact core call shape is confirmed by reading pool_sqlx.rs.

      // Pattern (executor adapts to actual core API):
      let runtime = classic_shared_core::get_runtime();
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

      // The core get_entries_batch signature is something like:
      //   pub async fn get_entries_batch(&self, pairs: &[(String, String)], _, _) -> Result<HashMap<(String,String), String>>
      // (executor reads pool_sqlx.rs to confirm exact shape)
      let map = runtime.block_on(async {
          pool.inner.get_entries_batch(&pairs, None, 50).await.unwrap_or_default()
      });

      pairs
          .into_iter()
          .map(|(formid, plugin)| {
              let value = map.get(&(formid.clone(), plugin.clone())).cloned().unwrap_or_default();
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
  fn test_db_pool_get_entries_batch_typed_uninitialized_returns_not_found_for_each() {
      let pool = db_pool_new("Fallout4", 4, 60);
      let result = db_pool_get_entries_batch_typed(
          &pool,
          &["0x000ABCDE".to_string(), "0x000FEDCB".to_string()],
          &["Fallout4.esm".to_string(), "Fallout4.esm".to_string()],
      );
      assert_eq!(result.len(), 2);
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
    - `git grep -nE 'fn db_pool_get_entry_typed|fn db_pool_get_entries_batch_typed' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs` returns 2+ wrapper definitions and 2+ extern declarations
    - `git grep -n 'struct FormIdEntryDto' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs` returns the shared struct declaration
    - `git grep -n 'fn db_pool_get_entry' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs` STILL returns the existing fn (D-08 — additive, not replaced)
    - `git grep -n 'fn db_pool_get_entries_batch' ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs` STILL returns the existing fn
    - `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml database::tests` exits 0 with at least 4 new passing tests
    - `cargo clippy -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` exits 0
  </acceptance_criteria>

  <done>
    `src/database.rs` exposes the FormIdEntryDto typed API alongside the existing tab-delimited path, all tests pass, no regressions.
  </done>
</task>

<task type="auto">
  <name>Task 3: Incremental builds, refresh D-09 baseline, atomic commit</name>

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

  ## Part C — D-11 consumer migration note

  Per RESEARCH.md §"D-11 Consumer Migration Enumeration", neither classic-cli nor classic-gui currently has a hand-rolled suspect-rule reader or typed FormID lookup that would qualify as a narrowed-bridge migration target. The existing C++ code paths use the tab-delimited DB API and the keys-only suspect getters; both paths continue to work via D-08 backward compat. The new typed/structured surfaces are available for FUTURE consumer migration but no Phase 2 plan is required to add a caller for them. The CXXS-10 success criterion is satisfied by `build_cli.ps1 -Test` and `build_gui.ps1 -Test` passing — which they will, because the new bridge fns are additive.

  ## Part D — Atomic commit

  Stage:
  - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs`
  - `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs`
  - All 4 baseline artifacts

  Commit message: `Feat(02-07): expose suspect rules (CXXS-07) and typed FormID API (CXXS-05) in CXX bridge` — body mentions CXXS-05, CXXS-07, D-08 (additive), D-09.
  </action>

  <verify>
    <automated>python tools/cxx_api_parity/check_parity_gate.py --repo-root .</automated>
  </verify>

  <acceptance_criteria>
    - `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test` exits 0
    - `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test` exits 0
    - `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` exits 0 with 0 drift
    - The committed `cxx_diff_report.md` shows ADDED rows under `bridgeModule: "config"` for SuspectErrorRuleDto, SuspectStackRuleDto, SuspectStackCountRuleDto + 2 new fns
    - The committed `cxx_diff_report.md` shows ADDED rows under `bridgeModule: "database"` for FormIdEntryDto + 2 new fns
    - `git log -1 --stat` shows the commit touches Rust source AND the parity baseline atomically
    - The committed `cxx_diff_report.md` shows ZERO REMOVED rows for `bridgeModule: "config"` or `bridgeModule: "database"` (D-08 — additive only)
  </acceptance_criteria>

  <done>
    Plan 02-07 complete — CXXS-05 and CXXS-07 satisfied; both existing fail-soft paths preserved; parity gate at 0 drift.
  </done>
</task>

</tasks>

<verification>
1. `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml config::tests database::tests` — exits 0
2. Both incremental builds exit 0
3. Parity gate at 0 drift
4. CXXS-05 and CXXS-07 fully satisfied
5. No D-08 violations (existing fns unchanged)

Validation Architecture (per 02-VALIDATION.md row 2-07-01): `cargo test -p classic-cpp-bridge config::tests database::tests` + `build_cli.ps1 -Test` + parity gate.
</verification>

<success_criteria>
- src/config.rs exposes SuspectErrorRuleDto, SuspectStackCountRuleDto, SuspectStackRuleDto + yaml_data_suspects_error_rules + yaml_data_suspects_stack_rules
- src/database.rs exposes FormIdEntryDto + db_pool_get_entry_typed + db_pool_get_entries_batch_typed
- Pitfall 6 verified — SuspectStackRuleDto.stack_contains_at_least is a Vec<SuspectStackCountRuleDto> where SuspectStackCountRuleDto has NO Vec fields, satisfying the rule
- All existing fns UNCHANGED (D-08 additive)
- Both incremental builds green
- Parity gate at 0 drift (D-09)
- D-11 N/A (no narrowed call sites currently exist for these surfaces — documented in commit body)
- Atomic commit
</success_criteria>

<output>
After completion, create `.planning/phases/02-cxx-bridge-surface-expansion/02-07-SUMMARY.md` documenting:
- Exact entries added (3 structs + 2 fns in config; 1 struct + 2 fns in database)
- Pitfall 6 verification: SuspectStackRuleDto contains Vec<SuspectStackCountRuleDto>; SuspectStackCountRuleDto has only String + u32 fields; CONFIRMED Pitfall 6 CLEAR
- D-11 N/A note (no current narrowed call sites)
- Note: CXXS-05 and CXXS-07 are now both complete
</output>