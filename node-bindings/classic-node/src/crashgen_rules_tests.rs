use super::{
    JsCheckRule, JsCrashgenSettingsRules, JsExpectedValue, JsPreflightAction, JsPreflightRule,
    JsRuleMessages, JsRuleTarget, js_rules_to_core,
};
use classic_config_core::{AutoscanReportPlacement, ExpectedValue, Predicate, TargetValueType};
use serde_json::json;

#[test]
fn js_rules_to_core_uses_shared_crashgen_expectation_parser() {
    let rules = JsCrashgenSettingsRules {
        version: 2,
        preflight: vec![JsPreflightRule {
            id: "bucket_fallback".to_string(),
            when: json!({"plugin_any": ["Addictol.dll"]}),
            action: JsPreflightAction {
                kind: "notice".to_string(),
                placement: Some("not_valid".to_string()),
                bucket: Some("error_information".to_string()),
                severity: "info".to_string(),
                message: "bucket fallback".to_string(),
                fix: None,
            },
        }],
        checks: vec![JsCheckRule {
            id: "value_type_alias".to_string(),
            target: JsRuleTarget {
                section: "Compatibility".to_string(),
                key: "Mode".to_string(),
                value_type: "string".to_string(),
            },
            when: json!({}),
            expect: JsExpectedValue {
                equals: json!("Enabled"),
            },
            messages: JsRuleMessages {
                fail: "bad".to_string(),
                fix: None,
                pass: None,
            },
            severity: "warning".to_string(),
        }],
    };

    let parsed = js_rules_to_core(Some(rules)).expect("rules should parse");

    assert_eq!(parsed.version, 2);
    assert_eq!(
        parsed.preflight[0].when,
        Predicate::PluginAny(vec!["addictol.dll".to_string()])
    );
    assert_eq!(
        parsed.preflight[0].action.bucket,
        AutoscanReportPlacement::ErrorInformation
    );
    assert_eq!(parsed.checks[0].target.value_type, TargetValueType::String);
    assert_eq!(
        parsed.checks[0].expect,
        ExpectedValue::String("Enabled".to_string())
    );
}
