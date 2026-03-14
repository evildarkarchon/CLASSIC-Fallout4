use classic_crashgen_settings_core::{
    CheckRule, ConfigLayout, CrashgenSettingsRules, ExpectedValue, Predicate, PreflightAction,
    PreflightActionKind, PreflightRule, RuleMessages, RuleReportBucket, RuleSeverity, RuleTarget,
    TargetValueType,
};
use serde_json::{Value, json};

#[derive(Clone)]
#[napi(object)]
pub struct JsPreflightAction {
    pub kind: String,
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
    pub checks: Vec<String>,
    pub settings_rules_version: Option<u32>,
    pub settings_rules: Option<JsCrashgenSettingsRules>,
}

fn parse_severity(value: &str, default: RuleSeverity) -> RuleSeverity {
    RuleSeverity::parse(value).unwrap_or(default)
}

fn severity_to_str(value: RuleSeverity) -> String {
    match value {
        RuleSeverity::Info => "info".to_string(),
        RuleSeverity::Warning => "warning".to_string(),
        RuleSeverity::Error => "error".to_string(),
    }
}

fn bucket_to_str(value: RuleReportBucket) -> String {
    match value {
        RuleReportBucket::Settings => "settings".to_string(),
        RuleReportBucket::ErrorInformation => "error_information".to_string(),
    }
}

fn parse_predicate(value: &Value) -> Option<Predicate> {
    let map = value.as_object()?;

    if let Some(all) = map.get("all").and_then(Value::as_array) {
        return Some(Predicate::All(
            all.iter().filter_map(parse_predicate).collect(),
        ));
    }
    if let Some(any) = map.get("any").and_then(Value::as_array) {
        return Some(Predicate::Any(
            any.iter().filter_map(parse_predicate).collect(),
        ));
    }
    if let Some(not) = map.get("not") {
        return parse_predicate(not).map(|p| Predicate::Not(Box::new(p)));
    }
    if let Some(plugins) = map.get("plugin_any").and_then(Value::as_array) {
        return Some(Predicate::PluginAny(
            plugins
                .iter()
                .filter_map(Value::as_str)
                .map(|v| v.to_lowercase())
                .collect(),
        ));
    }
    if let Some(layout) = map
        .get("config_layout_is")
        .and_then(Value::as_str)
        .and_then(ConfigLayout::parse)
    {
        return Some(Predicate::ConfigLayoutIs(layout));
    }
    if let Some(version) = map.get("crashgen_version_lt").and_then(Value::as_str) {
        let parts = version
            .split('.')
            .map(|p| p.trim().parse::<u32>().ok())
            .collect::<Vec<_>>();
        if parts.len() == 3 {
            return Some(Predicate::CrashgenVersionLt((
                parts[0]?, parts[1]?, parts[2]?,
            )));
        }
    }

    None
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

pub fn js_rules_to_core(rules: Option<JsCrashgenSettingsRules>) -> Option<CrashgenSettingsRules> {
    let rules = rules?;

    let preflight = rules
        .preflight
        .into_iter()
        .map(|rule| PreflightRule {
            id: rule.id,
            when: parse_predicate(&rule.when).unwrap_or(Predicate::Always),
            action: PreflightAction {
                kind: PreflightActionKind::parse(&rule.action.kind)
                    .unwrap_or(PreflightActionKind::Notice),
                bucket: rule
                    .action
                    .bucket
                    .as_deref()
                    .and_then(RuleReportBucket::parse)
                    .unwrap_or_default(),
                severity: parse_severity(&rule.action.severity, RuleSeverity::Info),
                message: rule.action.message,
                fix: rule.action.fix,
            },
        })
        .collect();

    let checks = rules
        .checks
        .into_iter()
        .filter_map(|rule| {
            let expect = rule.expect.equals;
            let expected = if let Some(value) = expect.as_bool() {
                Some(ExpectedValue::Bool(value))
            } else if let Some(value) = expect.as_i64() {
                Some(ExpectedValue::Int(value))
            } else {
                expect
                    .as_str()
                    .map(|value| ExpectedValue::String(value.to_string()))
            }?;

            Some(CheckRule {
                id: rule.id,
                target: RuleTarget {
                    section: rule.target.section,
                    key: rule.target.key,
                    value_type: TargetValueType::parse(&rule.target.value_type)
                        .unwrap_or(TargetValueType::Bool),
                },
                when: parse_predicate(&rule.when).unwrap_or(Predicate::Always),
                expect: expected,
                messages: RuleMessages {
                    fail: rule.messages.fail,
                    fix: rule.messages.fix,
                    pass: rule.messages.pass,
                },
                severity: parse_severity(&rule.severity, RuleSeverity::Warning),
            })
        })
        .collect();

    Some(CrashgenSettingsRules {
        version: rules.version,
        preflight,
        checks,
    })
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
                    bucket: Some(bucket_to_str(rule.action.bucket)),
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
