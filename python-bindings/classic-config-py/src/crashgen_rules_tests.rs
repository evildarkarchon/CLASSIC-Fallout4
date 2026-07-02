use super::parse_settings_rules;
use classic_config_core::{
    AutoscanReportPlacement, ExpectedValue, Predicate, RuleSeverity, TargetValueType,
};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

#[test]
fn parse_settings_rules_reads_preflight_and_check_rules() {
    Python::initialize();
    Python::attach(|py| {
        let rules = PyDict::new(py);
        rules.set_item("version", 2).unwrap();

        let when = PyDict::new(py);
        when.set_item("plugin_any", vec!["Addictol.dll"]).unwrap();
        let action = PyDict::new(py);
        action
            .set_item("kind", "notice_and_skip_remaining")
            .unwrap();
        action.set_item("placement", "error_information").unwrap();
        action.set_item("bucket", "error_information").unwrap();
        action.set_item("severity", "info").unwrap();
        action.set_item("message", "skip").unwrap();
        action.set_item("fix", "remove Addictol").unwrap();
        let preflight = PyDict::new(py);
        preflight.set_item("id", "addictol_skip").unwrap();
        preflight.set_item("when", &when).unwrap();
        preflight.set_item("action", &action).unwrap();
        rules
            .set_item("preflight", PyList::new(py, [&preflight]).unwrap())
            .unwrap();

        let target = PyDict::new(py);
        target.set_item("section", "Patches").unwrap();
        target.set_item("key", "Achievements").unwrap();
        target.set_item("value_type", "bool").unwrap();
        let expect = PyDict::new(py);
        expect.set_item("equals", false).unwrap();
        let messages = PyDict::new(py);
        messages.set_item("fail", "bad").unwrap();
        messages.set_item("fix", "fix").unwrap();
        messages.set_item("pass", "ok").unwrap();
        let check = PyDict::new(py);
        check.set_item("id", "achievements").unwrap();
        check.set_item("target", &target).unwrap();
        check.set_item("expect", &expect).unwrap();
        check.set_item("messages", &messages).unwrap();
        check.set_item("severity", "warning").unwrap();
        rules
            .set_item("checks", PyList::new(py, [&check]).unwrap())
            .unwrap();

        let parsed = parse_settings_rules(rules.as_any()).expect("rules should parse");

        assert_eq!(parsed.version, 2);
        assert_eq!(parsed.preflight.len(), 1);
        assert_eq!(
            parsed.preflight[0].action.bucket,
            AutoscanReportPlacement::ErrorInformation
        );
        assert_eq!(
            parsed.preflight[0].when,
            Predicate::PluginAny(vec!["addictol.dll".to_string()])
        );
        assert_eq!(parsed.checks.len(), 1);
        assert_eq!(parsed.checks[0].target.value_type, TargetValueType::Bool);
        assert_eq!(parsed.checks[0].expect, ExpectedValue::Bool(false));
        assert_eq!(parsed.checks[0].severity, RuleSeverity::Warning);
    });
}

#[test]
fn parse_settings_rules_prefers_placement_and_falls_back_to_bucket() {
    Python::initialize();
    Python::attach(|py| {
        let rules = PyDict::new(py);

        let action_with_placement = PyDict::new(py);
        action_with_placement.set_item("kind", "notice").unwrap();
        action_with_placement
            .set_item("placement", "settings")
            .unwrap();
        action_with_placement
            .set_item("bucket", "error_information")
            .unwrap();
        action_with_placement.set_item("severity", "info").unwrap();
        action_with_placement
            .set_item("message", "placement wins")
            .unwrap();
        let placement_rule = PyDict::new(py);
        placement_rule.set_item("id", "placement_wins").unwrap();
        placement_rule
            .set_item("action", &action_with_placement)
            .unwrap();

        let action_with_invalid_placement = PyDict::new(py);
        action_with_invalid_placement
            .set_item("kind", "notice")
            .unwrap();
        action_with_invalid_placement
            .set_item("placement", "not_valid")
            .unwrap();
        action_with_invalid_placement
            .set_item("bucket", "error_information")
            .unwrap();
        action_with_invalid_placement
            .set_item("severity", "info")
            .unwrap();
        action_with_invalid_placement
            .set_item("message", "bucket fallback")
            .unwrap();
        let fallback_rule = PyDict::new(py);
        fallback_rule.set_item("id", "bucket_fallback").unwrap();
        fallback_rule
            .set_item("action", &action_with_invalid_placement)
            .unwrap();

        rules
            .set_item(
                "preflight",
                PyList::new(py, [&placement_rule, &fallback_rule]).unwrap(),
            )
            .unwrap();

        let parsed = parse_settings_rules(rules.as_any()).expect("rules should parse");

        assert_eq!(
            parsed.preflight[0].action.bucket,
            AutoscanReportPlacement::Settings
        );
        assert_eq!(
            parsed.preflight[1].action.bucket,
            AutoscanReportPlacement::ErrorInformation
        );
    });
}

#[test]
fn parse_settings_rules_defaults_missing_optional_values() {
    Python::initialize();
    Python::attach(|py| {
        let rules = PyDict::new(py);
        let parsed = parse_settings_rules(rules.as_any()).expect("empty rules should parse");

        assert_eq!(parsed.version, 1);
        assert!(parsed.preflight.is_empty());
        assert!(parsed.checks.is_empty());
    });
}
