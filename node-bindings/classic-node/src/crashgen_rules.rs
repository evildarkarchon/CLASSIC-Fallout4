use classic_config_core::{
    AutoscanReportPlacement, ConfigLayout, CrashgenSettingsRules, ExpectedValue, Predicate,
    PreflightActionKind, RuleSeverity, TargetValueType, parse_crashgen_expectations,
};
use serde_json::{Map, Value, json};

#[derive(Clone)]
#[napi(object)]
pub struct JsPreflightAction {
    pub kind: String,
    pub placement: Option<String>,
    pub bucket: Option<String>,
    pub severity: String,
    pub message: String,
    pub fix: Option<String>,
}

#[derive(Clone)]
#[napi(object)]
pub struct JsPreflightRule {
    pub id: String,
    pub when: Value,
    pub action: JsPreflightAction,
}

#[derive(Clone)]
#[napi(object)]
pub struct JsRuleTarget {
    pub section: String,
    pub key: String,
    pub value_type: String,
}

#[derive(Clone)]
#[napi(object)]
pub struct JsExpectedValue {
    pub equals: Value,
}

#[derive(Clone)]
#[napi(object)]
pub struct JsRuleMessages {
    pub fail: String,
    pub fix: Option<String>,
    pub pass: Option<String>,
}

#[derive(Clone)]
#[napi(object)]
pub struct JsCheckRule {
    pub id: String,
    pub target: JsRuleTarget,
    pub when: Value,
    pub expect: JsExpectedValue,
    pub messages: JsRuleMessages,
    pub severity: String,
}

#[derive(Clone)]
#[napi(object)]
pub struct JsCrashgenSettingsRules {
    pub version: u32,
    pub preflight: Vec<JsPreflightRule>,
    pub checks: Vec<JsCheckRule>,
}

#[derive(Clone)]
#[napi(object)]
pub struct JsCrashgenRegistryEntry {
    pub display_section: String,
    pub ignore_keys: Vec<String>,
    /// Deprecated inert metadata retained for YAML compatibility; settings_rules drives validation.
    pub checks: Vec<String>,
    pub settings_rules_version: Option<u32>,
    pub settings_rules: Option<JsCrashgenSettingsRules>,
}

fn severity_to_str(value: RuleSeverity) -> String {
    match value {
        RuleSeverity::Info => "info".to_string(),
        RuleSeverity::Warning => "warning".to_string(),
        RuleSeverity::Error => "error".to_string(),
    }
}

fn placement_to_str(value: AutoscanReportPlacement) -> String {
    value.as_str().to_string()
}

fn predicate_to_json(predicate: &Predicate) -> Value {
    match predicate {
        Predicate::Always => json!({}),
        Predicate::PluginAny(plugins) => json!({"plugin_any": plugins}),
        Predicate::ConfigLayoutIs(layout) => {
            let text = match layout {
                ConfigLayout::Og => "og",
                ConfigLayout::Vr => "vr",
                ConfigLayout::Unknown => "unknown",
            };
            json!({"config_layout_is": text})
        }
        Predicate::CrashgenVersionLt((a, b, c)) => {
            json!({"crashgen_version_lt": format!("{a}.{b}.{c}")})
        }
        Predicate::All(items) => {
            json!({"all": items.iter().map(predicate_to_json).collect::<Vec<_>>()})
        }
        Predicate::Any(items) => {
            json!({"any": items.iter().map(predicate_to_json).collect::<Vec<_>>()})
        }
        Predicate::Not(item) => json!({"not": predicate_to_json(item)}),
    }
}

fn optional_string_value(value: Option<String>) -> Value {
    value.map(Value::String).unwrap_or(Value::Null)
}

fn js_rules_to_document(rules: JsCrashgenSettingsRules) -> Value {
    let mut root = Map::new();
    root.insert("version".to_string(), json!(rules.version));
    root.insert(
        "preflight".to_string(),
        Value::Array(
            rules
                .preflight
                .into_iter()
                .map(js_preflight_rule_to_document)
                .collect(),
        ),
    );
    root.insert(
        "checks".to_string(),
        Value::Array(
            rules
                .checks
                .into_iter()
                .map(js_check_rule_to_document)
                .collect(),
        ),
    );
    Value::Object(root)
}

fn js_preflight_rule_to_document(rule: JsPreflightRule) -> Value {
    let mut action = Map::new();
    action.insert("kind".to_string(), Value::String(rule.action.kind));
    action.insert(
        "placement".to_string(),
        optional_string_value(rule.action.placement),
    );
    action.insert(
        "bucket".to_string(),
        optional_string_value(rule.action.bucket),
    );
    action.insert("severity".to_string(), Value::String(rule.action.severity));
    action.insert("message".to_string(), Value::String(rule.action.message));
    action.insert("fix".to_string(), optional_string_value(rule.action.fix));

    json!({
        "id": rule.id,
        "when": rule.when,
        "action": Value::Object(action),
    })
}

fn js_check_rule_to_document(rule: JsCheckRule) -> Value {
    json!({
        "id": rule.id,
        "target": {
            "section": rule.target.section,
            "key": rule.target.key,
            "value_type": rule.target.value_type,
        },
        "when": rule.when,
        "expect": {
            "equals": rule.expect.equals,
        },
        "messages": {
            "fail": rule.messages.fail,
            "fix": rule.messages.fix,
            "pass": rule.messages.pass,
        },
        "severity": rule.severity,
    })
}

#[cfg(test)]
#[path = "crashgen_rules_tests.rs"]
mod tests;

pub fn js_rules_to_core(rules: Option<JsCrashgenSettingsRules>) -> Option<CrashgenSettingsRules> {
    let rules = rules?;
    parse_crashgen_expectations(&js_rules_to_document(rules), None).rules
}

pub fn core_rules_to_js(rules: Option<&CrashgenSettingsRules>) -> Option<JsCrashgenSettingsRules> {
    let rules = rules?;

    Some(JsCrashgenSettingsRules {
        version: rules.version,
        preflight: rules
            .preflight
            .iter()
            .map(|rule| JsPreflightRule {
                id: rule.id.clone(),
                when: predicate_to_json(&rule.when),
                action: JsPreflightAction {
                    kind: match rule.action.kind {
                        PreflightActionKind::NoticeAndSkipRemaining => {
                            "notice_and_skip_remaining".to_string()
                        }
                        PreflightActionKind::Notice => "notice".to_string(),
                        PreflightActionKind::Issue => "issue".to_string(),
                    },
                    placement: Some(placement_to_str(rule.action.bucket)),
                    bucket: Some(placement_to_str(rule.action.bucket)),
                    severity: severity_to_str(rule.action.severity),
                    message: rule.action.message.clone(),
                    fix: rule.action.fix.clone(),
                },
            })
            .collect(),
        checks: rules
            .checks
            .iter()
            .map(|rule| JsCheckRule {
                id: rule.id.clone(),
                target: JsRuleTarget {
                    section: rule.target.section.clone(),
                    key: rule.target.key.clone(),
                    value_type: match rule.target.value_type {
                        TargetValueType::Bool => "bool".to_string(),
                        TargetValueType::Int => "int".to_string(),
                        TargetValueType::String => "string".to_string(),
                    },
                },
                when: predicate_to_json(&rule.when),
                expect: JsExpectedValue {
                    equals: match &rule.expect {
                        ExpectedValue::Bool(v) => json!(v),
                        ExpectedValue::Int(v) => json!(v),
                        ExpectedValue::String(v) => json!(v),
                    },
                },
                messages: JsRuleMessages {
                    fail: rule.messages.fail.clone(),
                    fix: rule.messages.fix.clone(),
                    pass: rule.messages.pass.clone(),
                },
                severity: severity_to_str(rule.severity),
            })
            .collect(),
    })
}
