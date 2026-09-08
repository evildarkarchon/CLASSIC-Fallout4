use super::parse_crashgen_registry;
use crate::AutoscanReportPlacement;
use classic_settings_core::{merge_yaml_documents, parse_yaml_content};
use std::collections::HashSet;
use yaml_rust2::Yaml;

fn parse_yaml_document(yaml_content: &str) -> Yaml {
    let docs = parse_yaml_content("memory://crashgen_registry", yaml_content).unwrap();
    merge_yaml_documents("memory://crashgen_registry", &docs).unwrap()
}

#[test]
fn test_parse_crashgen_registry_parses_valid_entry() {
    let game_data = parse_yaml_document(
        r#"
Crashgen_Registry:
  crash-og:
    display_section: "[Compatibility]"
    ignore_keys:
      - "Achievements"
      - "MemoryManager"
    checks:
      - "achievements"
      - "memory_management"
"#,
    );

    let registry = parse_crashgen_registry(&game_data);
    let entry = registry.get("crash-og").expect("missing crash-og entry");

    assert_eq!(entry.display_section, "[Compatibility]");
    assert_eq!(
        entry.ignore_keys,
        vec!["Achievements".to_string(), "MemoryManager".to_string()]
    );
    assert_eq!(
        entry.checks,
        vec!["achievements".to_string(), "memory_management".to_string()]
    );
    assert_eq!(entry.settings_rules_version, None);
    assert!(entry.settings_rules.is_none());
}

#[test]
fn test_parse_crashgen_registry_skips_malformed_keys_and_entries() {
    let game_data = parse_yaml_document(
        r#"
Crashgen_Registry:
  valid:
    display_section: "[Valid]"
  123:
    display_section: "[InvalidKey]"
  malformed_entry: "not-a-mapping"
"#,
    );

    let registry = parse_crashgen_registry(&game_data);

    assert_eq!(registry.len(), 1);
    assert!(registry.contains_key("valid"));
    assert!(!registry.contains_key("malformed_entry"));
}

#[test]
fn test_parse_crashgen_registry_non_array_fields_default_to_empty_lists() {
    let game_data = parse_yaml_document(
        r#"
Crashgen_Registry:
  crash-og:
    display_section: "[Compatibility]"
    ignore_keys: "not-an-array"
    checks: 99
"#,
    );

    let registry = parse_crashgen_registry(&game_data);
    let entry = registry.get("crash-og").expect("missing crash-og entry");

    assert!(entry.ignore_keys.is_empty());
    assert!(entry.checks.is_empty());
    assert!(entry.settings_rules.is_none());
}

#[test]
fn test_parse_crashgen_registry_mixed_array_types_keep_only_strings() {
    let game_data = parse_yaml_document(
        r#"
Crashgen_Registry:
  crash-og:
    ignore_keys:
      - "AchievementWarnings"
      - 42
      - true
      - "MemoryManager"
    checks:
      - "achievements"
      - false
      - "memory_management"
"#,
    );

    let registry = parse_crashgen_registry(&game_data);
    let entry = registry.get("crash-og").expect("missing crash-og entry");

    assert_eq!(
        entry.ignore_keys,
        vec![
            "AchievementWarnings".to_string(),
            "MemoryManager".to_string()
        ]
    );
    assert_eq!(
        entry.checks,
        vec!["achievements".to_string(), "memory_management".to_string()]
    );
    assert!(entry.settings_rules.is_none());
}

#[test]
fn test_parse_crashgen_registry_parses_settings_rules() {
    let game_data = parse_yaml_document(
        r#"
Crashgen_Registry:
  crash-og:
    settings_rules_version: 2
    settings_rules:
      preflight:
        - id: addictol_skip
          when:
            plugin_any: ["addictol.dll"]
          action:
            kind: notice_and_skip_remaining
            bucket: error_information
            severity: info
            message: "skip"
      checks:
        - id: achievements
          target:
            section: "Patches"
            key: "Achievements"
            type: "bool"
          when:
            plugin_any: ["achievements.dll"]
          expect:
            equals: false
          messages:
            fail: "bad"
            fix: "fix"
            pass: "ok"
          severity: warning
"#,
    );

    let registry = parse_crashgen_registry(&game_data);
    let entry = registry.get("crash-og").expect("missing crash-og entry");
    assert_eq!(entry.settings_rules_version, Some(2));
    let rules = entry
        .settings_rules
        .as_ref()
        .expect("expected parsed settings rules");
    assert_eq!(rules.version, 2);
    assert_eq!(rules.preflight.len(), 1);
    assert_eq!(rules.checks.len(), 1);
    assert_eq!(
        rules.preflight[0].action.bucket,
        AutoscanReportPlacement::ErrorInformation
    );
    assert_eq!(rules.checks[0].target.key, "Achievements");
}

#[test]
fn test_parse_crashgen_registry_prefers_placement_over_bucket() {
    let game_data = parse_yaml_document(
        r#"
Crashgen_Registry:
  crash-og:
    settings_rules:
      preflight:
        - id: placement_wins
          action:
            kind: notice
            placement: settings
            bucket: error_information
            severity: info
            message: "placement wins"
"#,
    );

    let registry = parse_crashgen_registry(&game_data);
    let rules = registry
        .get("crash-og")
        .and_then(|entry| entry.settings_rules.as_ref())
        .expect("expected parsed settings rules");

    assert_eq!(
        rules.preflight[0].action.bucket,
        AutoscanReportPlacement::Settings
    );
}

#[test]
fn test_parse_crashgen_registry_falls_back_to_bucket_when_placement_is_invalid() {
    let game_data = parse_yaml_document(
        r#"
Crashgen_Registry:
  crash-og:
    settings_rules:
      preflight:
        - id: bucket_fallback
          action:
            kind: notice
            placement: definitely_not_a_placement
            bucket: error_information
            severity: info
            message: "bucket fallback"
"#,
    );

    let registry = parse_crashgen_registry(&game_data);
    let rules = registry
        .get("crash-og")
        .and_then(|entry| entry.settings_rules.as_ref())
        .expect("expected parsed settings rules");

    assert_eq!(
        rules.preflight[0].action.bucket,
        AutoscanReportPlacement::ErrorInformation
    );
}

#[test]
fn test_parse_crashgen_registry_defaults_invalid_placement_and_bucket_to_settings() {
    let game_data = parse_yaml_document(
        r#"
Crashgen_Registry:
  crash-og:
    settings_rules:
      preflight:
        - id: default_settings
          action:
            kind: notice
            placement: not_valid
            bucket: also_not_valid
            severity: info
            message: "default settings"
"#,
    );

    let registry = parse_crashgen_registry(&game_data);
    let rules = registry
        .get("crash-og")
        .and_then(|entry| entry.settings_rules.as_ref())
        .expect("expected parsed settings rules");

    assert_eq!(
        rules.preflight[0].action.bucket,
        AutoscanReportPlacement::Settings
    );
}

#[test]
fn test_parse_crashgen_registry_settings_rules_default_version_when_missing() {
    let game_data = parse_yaml_document(
        r#"
Crashgen_Registry:
  crash-og:
    settings_rules:
      preflight:
        - id: addictol_skip
          when:
            plugin_any: ["addictol.dll"]
          action:
            kind: notice_and_skip_remaining
            severity: info
            message: "skip"
"#,
    );

    let registry = parse_crashgen_registry(&game_data);
    let entry = registry.get("crash-og").expect("missing crash-og entry");
    assert_eq!(entry.settings_rules_version, None);
    let rules = entry
        .settings_rules
        .as_ref()
        .expect("expected parsed settings rules");
    assert_eq!(rules.version, 1);
    assert_eq!(rules.preflight.len(), 1);
    assert_eq!(
        rules.preflight[0].action.bucket,
        AutoscanReportPlacement::Settings
    );
    assert!(rules.checks.is_empty());
}

#[test]
fn shipped_fallout4_yaml_carries_required_crashgen_expectations() {
    let yaml_path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("CLASSIC Data")
        .join("databases")
        .join("CLASSIC Fallout4.yaml");
    let yaml_content = std::fs::read_to_string(&yaml_path)
        .unwrap_or_else(|error| panic!("failed to read {}: {error}", yaml_path.display()));
    let game_data = parse_yaml_document(&yaml_content);

    let registry = parse_crashgen_registry(&game_data);

    let buffout = registry
        .get("Buffout 4")
        .expect("Buffout 4 registry entry must exist");
    assert!(
        !buffout.checks.is_empty(),
        "deprecated checks metadata should still be accepted from shipped YAML"
    );
    let buffout_rules = buffout
        .settings_rules
        .as_ref()
        .expect("Buffout 4 must carry Crashgen Expectations");
    let rule_ids: HashSet<&str> = buffout_rules
        .checks
        .iter()
        .map(|rule| rule.id.as_str())
        .collect();
    for required_id in [
        "achievements_conflict",
        "memory_manager_xcell",
        "havok_xcell",
        "bstexture_xcell",
        "scaleform_xcell",
        "smallblock_xcell",
        "archive_limit",
        "looksmenu_f4ee",
    ] {
        assert!(
            rule_ids.contains(required_id),
            "Buffout 4 settings_rules missing {required_id}"
        );
    }

    let addictol = registry
        .get("Addictol")
        .expect("Addictol registry entry must exist");
    let addictol_rules = addictol
        .settings_rules
        .as_ref()
        .expect("Addictol must carry a Crashgen Expectations block");
    assert!(
        !addictol_rules.preflight.is_empty(),
        "Addictol compatibility guidance should live in preflight expectations"
    );
    assert!(addictol_rules.checks.is_empty());

    let default = registry
        .get("default")
        .expect("default registry entry must exist");
    let default_rules = default
        .settings_rules
        .as_ref()
        .expect("default must carry an explicit empty Crashgen Expectations block");
    assert!(default_rules.preflight.is_empty());
    assert!(default_rules.checks.is_empty());
}
