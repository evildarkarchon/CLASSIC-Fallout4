use super::parse_crashgen_registry;
use crate::RuleReportBucket;
use classic_settings_core::{merge_yaml_documents, parse_yaml_content};
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
        RuleReportBucket::ErrorInformation
    );
    assert_eq!(rules.checks[0].target.key, "Achievements");
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
    assert_eq!(rules.preflight[0].action.bucket, RuleReportBucket::Settings);
    assert!(rules.checks.is_empty());
}
