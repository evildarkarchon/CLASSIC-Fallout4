use super::parse_crashgen_expectations;
use crate::{AutoscanReportPlacement, ExpectedValue, Predicate, RuleSeverity, TargetValueType};
use serde_json::json;

#[test]
fn parses_canonical_crashgen_expectation_document() {
    let document = json!({
        "version": 2,
        "preflight": [{
            "id": "addictol_skip",
            "when": { "plugin_any": ["Addictol.dll"] },
            "action": {
                "kind": "notice_and_skip_remaining",
                "placement": "error_information",
                "severity": "info",
                "message": "skip",
                "fix": "remove Addictol"
            }
        }],
        "checks": [{
            "id": "achievements_conflict",
            "target": {
                "section": "Patches",
                "key": "Achievements",
                "type": "bool"
            },
            "when": { "crashgen_version_lt": "1.28.6" },
            "expect": { "equals": false },
            "messages": {
                "fail": "bad",
                "fix": "fix",
                "pass": "ok"
            },
            "severity": "warning"
        }]
    });

    let result = parse_crashgen_expectations(&document, None);
    let rules = result.rules.expect("rules should parse");

    assert!(result.diagnostics.is_empty());
    assert_eq!(rules.version, 2);
    assert_eq!(rules.preflight.len(), 1);
    assert_eq!(
        rules.preflight[0].when,
        Predicate::PluginAny(vec!["addictol.dll".to_string()])
    );
    assert_eq!(
        rules.preflight[0].action.bucket,
        AutoscanReportPlacement::ErrorInformation
    );
    assert_eq!(rules.checks.len(), 1);
    assert_eq!(rules.checks[0].target.value_type, TargetValueType::Bool);
    assert_eq!(
        rules.checks[0].when,
        Predicate::CrashgenVersionLt((1, 28, 6))
    );
    assert_eq!(rules.checks[0].expect, ExpectedValue::Bool(false));
    assert_eq!(rules.checks[0].severity, RuleSeverity::Warning);
}

#[test]
fn accepts_compatibility_aliases_with_canonical_precedence() {
    let document = json!({
        "preflight": [
            {
                "id": "placement_wins",
                "action": {
                    "kind": "notice",
                    "placement": "settings",
                    "bucket": "error_information",
                    "severity": "info",
                    "message": "placement wins"
                }
            },
            {
                "id": "bucket_fallback",
                "action": {
                    "kind": "notice",
                    "placement": "not_valid",
                    "bucket": "error_information",
                    "severity": "info",
                    "message": "bucket fallback"
                }
            }
        ],
        "checks": [{
            "id": "value_type_alias",
            "target": {
                "section": "Compatibility",
                "key": "Mode",
                "type": "not_valid",
                "value_type": "string"
            },
            "expect": { "equals": "Enabled" },
            "messages": { "fail": "bad" }
        }]
    });

    let result = parse_crashgen_expectations(&document, None);
    let rules = result.rules.expect("rules should parse");

    assert_eq!(
        rules.preflight[0].action.bucket,
        AutoscanReportPlacement::Settings
    );
    assert_eq!(
        rules.preflight[1].action.bucket,
        AutoscanReportPlacement::ErrorInformation
    );
    assert_eq!(rules.checks[0].target.value_type, TargetValueType::String);
    assert!(
        result
            .diagnostics
            .iter()
            .any(|diagnostic| diagnostic.path == "$.preflight[1].action.placement")
    );
    assert!(
        result
            .diagnostics
            .iter()
            .any(|diagnostic| diagnostic.path == "$.checks[0].target.type")
    );
}

#[test]
fn preserves_tolerant_defaults_and_reports_diagnostics() {
    let document = json!({
        "version": "3",
        "preflight": [
            { "id": "missing_action" },
            {
                "id": "defaults",
                "when": { "unknown": true },
                "action": {
                    "kind": "not_valid",
                    "severity": "not_valid",
                    "message": "defaults"
                }
            }
        ],
        "checks": [
            {
                "id": "missing_expect",
                "target": { "section": "Patches", "key": "Achievements" },
                "messages": { "fail": "bad" }
            }
        ]
    });

    let result = parse_crashgen_expectations(&document, None);
    let rules = result.rules.expect("rules should parse");

    assert_eq!(rules.version, 3);
    assert_eq!(rules.preflight.len(), 1);
    assert_eq!(rules.preflight[0].when, Predicate::Always);
    assert_eq!(rules.checks.len(), 0);
    assert!(result.diagnostics.len() >= 4);
}

#[test]
fn uses_yaml_sibling_version_when_document_version_is_missing() {
    let document = json!({
        "preflight": [],
        "checks": []
    });

    let result = parse_crashgen_expectations(&document, Some(4));
    let rules = result.rules.expect("rules should parse");

    assert_eq!(rules.version, 4);
}

#[test]
fn rejects_non_mapping_root_with_diagnostic() {
    let result = parse_crashgen_expectations(&json!(["not", "a", "mapping"]), None);

    assert!(result.rules.is_none());
    assert_eq!(result.diagnostics[0].path, "$");
}
