//! Crashgen Expectation Parser.
//!
//! This module owns the carrier-neutral parsing rules for Crashgen Expectation
//! payloads. YAML, Node, and Python adapters translate their local carrier into
//! a JSON-like document before crossing this seam.

use crate::{
    AutoscanReportPlacement, CheckRule, ConfigLayout, CrashgenSettingsRules, ExpectedValue,
    Predicate, PreflightAction, PreflightActionKind, PreflightRule, RuleMessages, RuleSeverity,
    RuleTarget, TargetValueType,
};
use serde_json::{Map, Value};

/// A non-fatal issue observed while parsing a Crashgen Expectation payload.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CrashgenExpectationParseDiagnostic {
    /// JSONPath-like location of the malformed or defaulted field.
    pub path: String,
    /// Human-readable reason the parser skipped or defaulted the field.
    pub message: String,
}

/// Result of parsing a carrier-neutral Crashgen Expectation document.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct CrashgenExpectationParseResult {
    /// Parsed rules, or `None` when the root payload is not a mapping.
    pub rules: Option<CrashgenSettingsRules>,
    /// Non-fatal parse diagnostics accumulated while preserving tolerant behavior.
    pub diagnostics: Vec<CrashgenExpectationParseDiagnostic>,
}

/// Parse a carrier-neutral Crashgen Expectation document into typed rules.
///
/// The parser preserves the historical tolerant behavior: malformed optional
/// values are defaulted, malformed rules are skipped, and diagnostics describe
/// what happened for conformance tests and internal logs. `default_version`
/// carries the sibling `settings_rules_version` metadata used by YAML Data.
pub fn parse_crashgen_expectations(
    document: &Value,
    default_version: Option<u32>,
) -> CrashgenExpectationParseResult {
    let mut parser = Parser::default();
    let rules = parser.parse_root(document, default_version);
    CrashgenExpectationParseResult {
        rules,
        diagnostics: parser.diagnostics,
    }
}

#[derive(Default)]
struct Parser {
    diagnostics: Vec<CrashgenExpectationParseDiagnostic>,
}

impl Parser {
    fn parse_root(
        &mut self,
        document: &Value,
        default_version: Option<u32>,
    ) -> Option<CrashgenSettingsRules> {
        let Some(root) = document.as_object() else {
            self.diagnostic("$", "expected settings_rules mapping");
            return None;
        };

        let version = root
            .get("version")
            .and_then(|value| self.parse_u32_value(value, "$.version"))
            .or(default_version)
            .unwrap_or(1);

        let preflight =
            self.parse_rule_array(root, "preflight", "$.preflight", |parser, item, path| {
                parser.parse_preflight_rule(item, path)
            });
        let checks = self.parse_rule_array(root, "checks", "$.checks", |parser, item, path| {
            parser.parse_check_rule(item, path)
        });

        Some(CrashgenSettingsRules {
            version,
            preflight,
            checks,
        })
    }

    fn parse_rule_array<T>(
        &mut self,
        root: &Map<String, Value>,
        field: &str,
        path: &str,
        parse_item: impl Fn(&mut Self, &Value, &str) -> Option<T>,
    ) -> Vec<T> {
        let Some(value) = root.get(field) else {
            return Vec::new();
        };
        let Some(items) = value.as_array() else {
            self.diagnostic(path, "expected array; using empty list");
            return Vec::new();
        };

        items
            .iter()
            .enumerate()
            .filter_map(|(index, item)| parse_item(self, item, &format!("{path}[{index}]")))
            .collect()
    }

    fn parse_preflight_rule(&mut self, value: &Value, path: &str) -> Option<PreflightRule> {
        let Some(rule) = value.as_object() else {
            self.diagnostic(path, "expected preflight rule mapping; skipping rule");
            return None;
        };
        let id = self.required_string(rule, "id", &format!("{path}.id"), "preflight rule")?;
        let when = rule
            .get("when")
            .and_then(|value| self.parse_predicate(value, &format!("{path}.when")))
            .unwrap_or(Predicate::Always);
        let action_value = match rule.get("action") {
            Some(value) => value,
            None => {
                self.diagnostic(
                    &format!("{path}.action"),
                    "missing action; skipping preflight rule",
                );
                return None;
            }
        };
        let Some(action_map) = action_value.as_object() else {
            self.diagnostic(
                &format!("{path}.action"),
                "expected action mapping; skipping preflight rule",
            );
            return None;
        };

        let kind = self.parse_optional_enum(
            action_map,
            "kind",
            &format!("{path}.action.kind"),
            PreflightActionKind::parse,
            PreflightActionKind::Notice,
            "invalid action kind; defaulting to notice",
        );
        let bucket = self.parse_autoscan_report_placement(action_map, &format!("{path}.action"));
        let severity = self.parse_optional_enum(
            action_map,
            "severity",
            &format!("{path}.action.severity"),
            RuleSeverity::parse,
            RuleSeverity::Info,
            "invalid severity; defaulting to info",
        );
        let message = self.required_string(
            action_map,
            "message",
            &format!("{path}.action.message"),
            "preflight action",
        )?;
        let fix = self.optional_string(action_map, "fix", &format!("{path}.action.fix"));

        Some(PreflightRule {
            id,
            when,
            action: PreflightAction {
                kind,
                bucket,
                severity,
                message,
                fix,
            },
        })
    }

    fn parse_check_rule(&mut self, value: &Value, path: &str) -> Option<CheckRule> {
        let Some(rule) = value.as_object() else {
            self.diagnostic(path, "expected check rule mapping; skipping rule");
            return None;
        };
        let id = self.required_string(rule, "id", &format!("{path}.id"), "check rule")?;
        let target_value = match rule.get("target") {
            Some(value) => value,
            None => {
                self.diagnostic(
                    &format!("{path}.target"),
                    "missing target; skipping check rule",
                );
                return None;
            }
        };
        let Some(target_map) = target_value.as_object() else {
            self.diagnostic(
                &format!("{path}.target"),
                "expected target mapping; skipping check rule",
            );
            return None;
        };
        let section = self.required_string(
            target_map,
            "section",
            &format!("{path}.target.section"),
            "check target",
        )?;
        let key = self.required_string(
            target_map,
            "key",
            &format!("{path}.target.key"),
            "check target",
        )?;
        let value_type = self.parse_target_value_type(target_map, &format!("{path}.target"));

        let when = rule
            .get("when")
            .and_then(|value| self.parse_predicate(value, &format!("{path}.when")))
            .unwrap_or(Predicate::Always);
        let expect = rule
            .get("expect")
            .and_then(|value| self.parse_expected_value(value, &format!("{path}.expect")))?;
        let messages_value = match rule.get("messages") {
            Some(value) => value,
            None => {
                self.diagnostic(
                    &format!("{path}.messages"),
                    "missing messages; skipping check rule",
                );
                return None;
            }
        };
        let Some(messages_map) = messages_value.as_object() else {
            self.diagnostic(
                &format!("{path}.messages"),
                "expected messages mapping; skipping check rule",
            );
            return None;
        };
        let fail = self.required_string(
            messages_map,
            "fail",
            &format!("{path}.messages.fail"),
            "check messages",
        )?;
        let fix = self.optional_string(messages_map, "fix", &format!("{path}.messages.fix"));
        let pass = self.optional_string(messages_map, "pass", &format!("{path}.messages.pass"));
        let severity = self.parse_optional_enum(
            rule,
            "severity",
            &format!("{path}.severity"),
            RuleSeverity::parse,
            RuleSeverity::Warning,
            "invalid severity; defaulting to warning",
        );

        Some(CheckRule {
            id,
            target: RuleTarget {
                section,
                key,
                value_type,
            },
            when,
            expect,
            messages: RuleMessages { fail, fix, pass },
            severity,
        })
    }

    fn parse_predicate(&mut self, value: &Value, path: &str) -> Option<Predicate> {
        let Some(map) = value.as_object() else {
            self.diagnostic(path, "expected predicate mapping; defaulting to always");
            return None;
        };

        if let Some(all) = map.get("all") {
            let Some(items) = all.as_array() else {
                self.diagnostic(
                    &format!("{path}.all"),
                    "expected array; defaulting predicate to always",
                );
                return None;
            };
            return Some(Predicate::All(
                items
                    .iter()
                    .enumerate()
                    .filter_map(|(index, item)| {
                        self.parse_predicate(item, &format!("{path}.all[{index}]"))
                    })
                    .collect(),
            ));
        }

        if let Some(any) = map.get("any") {
            let Some(items) = any.as_array() else {
                self.diagnostic(
                    &format!("{path}.any"),
                    "expected array; defaulting predicate to always",
                );
                return None;
            };
            return Some(Predicate::Any(
                items
                    .iter()
                    .enumerate()
                    .filter_map(|(index, item)| {
                        self.parse_predicate(item, &format!("{path}.any[{index}]"))
                    })
                    .collect(),
            ));
        }

        if let Some(not) = map.get("not") {
            return self
                .parse_predicate(not, &format!("{path}.not"))
                .map(|item| Predicate::Not(Box::new(item)));
        }

        if let Some(plugin_any) = map.get("plugin_any") {
            let Some(items) = plugin_any.as_array() else {
                self.diagnostic(
                    &format!("{path}.plugin_any"),
                    "expected array; defaulting predicate to always",
                );
                return None;
            };
            let plugins = items
                .iter()
                .enumerate()
                .filter_map(|(index, item)| match item.as_str() {
                    Some(value) => Some(value.to_lowercase()),
                    None => {
                        self.diagnostic(
                            &format!("{path}.plugin_any[{index}]"),
                            "expected string; skipping plugin predicate item",
                        );
                        None
                    }
                })
                .collect();
            return Some(Predicate::PluginAny(plugins));
        }

        if let Some(layout) = map.get("config_layout_is") {
            let Some(text) = layout.as_str() else {
                self.diagnostic(
                    &format!("{path}.config_layout_is"),
                    "expected string; defaulting predicate to always",
                );
                return None;
            };
            return match ConfigLayout::parse(text) {
                Some(value) => Some(Predicate::ConfigLayoutIs(value)),
                None => {
                    self.diagnostic(
                        &format!("{path}.config_layout_is"),
                        "invalid config layout; defaulting predicate to always",
                    );
                    None
                }
            };
        }

        if let Some(version) = map.get("crashgen_version_lt") {
            let Some(text) = version.as_str() else {
                self.diagnostic(
                    &format!("{path}.crashgen_version_lt"),
                    "expected version string; defaulting predicate to always",
                );
                return None;
            };
            return self
                .parse_version_tuple(text, &format!("{path}.crashgen_version_lt"))
                .map(Predicate::CrashgenVersionLt);
        }

        if !map.is_empty() {
            self.diagnostic(path, "unrecognized predicate; defaulting to always");
        }
        None
    }

    fn parse_expected_value(&mut self, value: &Value, path: &str) -> Option<ExpectedValue> {
        let Some(map) = value.as_object() else {
            self.diagnostic(path, "expected expect mapping; skipping check rule");
            return None;
        };
        let Some(equals) = map.get("equals") else {
            self.diagnostic(
                &format!("{path}.equals"),
                "missing expected value; skipping check rule",
            );
            return None;
        };

        if let Some(value) = equals.as_bool() {
            return Some(ExpectedValue::Bool(value));
        }
        if let Some(value) = equals.as_i64() {
            return Some(ExpectedValue::Int(value));
        }
        if let Some(value) = equals.as_str() {
            return Some(ExpectedValue::String(value.to_string()));
        }

        self.diagnostic(
            &format!("{path}.equals"),
            "expected bool, integer, or string; skipping check rule",
        );
        None
    }

    fn parse_autoscan_report_placement(
        &mut self,
        action_map: &Map<String, Value>,
        path: &str,
    ) -> AutoscanReportPlacement {
        if let Some(placement) = action_map.get("placement") {
            match self.parse_optional_string_value(placement, &format!("{path}.placement")) {
                Some(text) => {
                    if let Some(value) = AutoscanReportPlacement::parse(&text) {
                        return value;
                    }
                    self.diagnostic(
                        &format!("{path}.placement"),
                        "invalid placement; trying bucket alias",
                    );
                }
                None => {
                    self.diagnostic(
                        &format!("{path}.placement"),
                        "expected placement string; trying bucket alias",
                    );
                }
            }
        }

        if let Some(bucket) = action_map.get("bucket") {
            match self.parse_optional_string_value(bucket, &format!("{path}.bucket")) {
                Some(text) => {
                    if let Some(value) = AutoscanReportPlacement::parse(&text) {
                        return value;
                    }
                    self.diagnostic(
                        &format!("{path}.bucket"),
                        "invalid bucket alias; defaulting to settings placement",
                    );
                }
                None => {
                    self.diagnostic(
                        &format!("{path}.bucket"),
                        "expected bucket string; defaulting to settings placement",
                    );
                }
            }
        }

        AutoscanReportPlacement::Settings
    }

    fn parse_target_value_type(
        &mut self,
        target_map: &Map<String, Value>,
        path: &str,
    ) -> TargetValueType {
        if let Some(value) = target_map.get("type") {
            match self.parse_optional_string_value(value, &format!("{path}.type")) {
                Some(text) => {
                    if let Some(value_type) = TargetValueType::parse(&text) {
                        return value_type;
                    }
                    self.diagnostic(
                        &format!("{path}.type"),
                        "invalid target type; trying value_type alias",
                    );
                }
                None => {
                    self.diagnostic(
                        &format!("{path}.type"),
                        "expected target type string; trying value_type alias",
                    );
                }
            }
        }

        if let Some(value) = target_map.get("value_type") {
            match self.parse_optional_string_value(value, &format!("{path}.value_type")) {
                Some(text) => {
                    if let Some(value_type) = TargetValueType::parse(&text) {
                        return value_type;
                    }
                    self.diagnostic(
                        &format!("{path}.value_type"),
                        "invalid value_type alias; defaulting to bool",
                    );
                }
                None => {
                    self.diagnostic(
                        &format!("{path}.value_type"),
                        "expected value_type string; defaulting to bool",
                    );
                }
            }
        }

        TargetValueType::Bool
    }

    fn parse_optional_enum<T: Copy>(
        &mut self,
        map: &Map<String, Value>,
        field: &str,
        path: &str,
        parse: impl Fn(&str) -> Option<T>,
        default: T,
        invalid_message: &str,
    ) -> T {
        let Some(value) = map.get(field) else {
            return default;
        };
        match self.parse_optional_string_value(value, path) {
            Some(text) => parse(&text).unwrap_or_else(|| {
                self.diagnostic(path, invalid_message);
                default
            }),
            None => {
                self.diagnostic(path, invalid_message);
                default
            }
        }
    }

    fn parse_version_tuple(&mut self, value: &str, path: &str) -> Option<(u32, u32, u32)> {
        let parts = value
            .split('.')
            .map(|part| part.trim().parse::<u32>().ok())
            .collect::<Vec<_>>();
        if parts.len() == 3 {
            return Some((parts[0]?, parts[1]?, parts[2]?));
        }
        self.diagnostic(path, "expected version string MAJOR.MINOR.PATCH");
        None
    }

    fn parse_u32_value(&mut self, value: &Value, path: &str) -> Option<u32> {
        if let Some(number) = value.as_u64() {
            return u32::try_from(number).ok();
        }
        if let Some(text) = value.as_str() {
            return text.trim().parse::<u32>().ok();
        }
        self.diagnostic(path, "expected non-negative integer; defaulting version");
        None
    }

    fn required_string(
        &mut self,
        map: &Map<String, Value>,
        field: &str,
        path: &str,
        owner: &str,
    ) -> Option<String> {
        let Some(value) = map.get(field) else {
            self.diagnostic(path, &format!("missing required {owner} field; skipping"));
            return None;
        };
        let Some(text) = self.parse_optional_string_value(value, path) else {
            self.diagnostic(
                path,
                &format!("expected string for required {owner} field; skipping"),
            );
            return None;
        };
        Some(text)
    }

    fn optional_string(
        &mut self,
        map: &Map<String, Value>,
        field: &str,
        path: &str,
    ) -> Option<String> {
        let value = map.get(field)?;
        match self.parse_optional_string_value(value, path) {
            Some(text) => Some(text),
            None => {
                self.diagnostic(path, "expected string; ignoring optional field");
                None
            }
        }
    }

    fn parse_optional_string_value(&self, value: &Value, _path: &str) -> Option<String> {
        value.as_str().map(ToString::to_string)
    }

    fn diagnostic(&mut self, path: &str, message: &str) {
        self.diagnostics.push(CrashgenExpectationParseDiagnostic {
            path: path.to_string(),
            message: message.to_string(),
        });
    }
}

#[cfg(test)]
#[path = "crashgen_expectation_parser_tests.rs"]
mod tests;
