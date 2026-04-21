use classic_config_core::{
    CheckRule, ConfigLayout, CrashgenSettingsRules, ExpectedValue, Predicate, PreflightAction,
    PreflightActionKind, PreflightRule, RuleMessages, RuleReportBucket, RuleSeverity, RuleTarget,
    TargetValueType,
};
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict};

fn as_dict<'py>(value: &Bound<'py, PyAny>) -> Option<Bound<'py, PyDict>> {
    value.cast::<PyDict>().ok().cloned()
}

fn get_opt_str(map: &Bound<'_, PyDict>, key: &str) -> Option<String> {
    map.get_item(key)
        .ok()
        .flatten()
        .and_then(|v| v.extract::<String>().ok())
}

fn parse_predicate(value: &Bound<'_, PyAny>) -> Option<Predicate> {
    let map = as_dict(value)?;

    if let Some(items) = map
        .get_item("all")
        .ok()
        .flatten()
        .and_then(|v| v.extract::<Vec<Bound<'_, PyAny>>>().ok())
    {
        return Some(Predicate::All(
            items.iter().filter_map(parse_predicate).collect(),
        ));
    }

    if let Some(items) = map
        .get_item("any")
        .ok()
        .flatten()
        .and_then(|v| v.extract::<Vec<Bound<'_, PyAny>>>().ok())
    {
        return Some(Predicate::Any(
            items.iter().filter_map(parse_predicate).collect(),
        ));
    }

    if let Some(inner) = map.get_item("not").ok().flatten() {
        return parse_predicate(&inner).map(|p| Predicate::Not(Box::new(p)));
    }

    if let Some(plugins) = map
        .get_item("plugin_any")
        .ok()
        .flatten()
        .and_then(|v| v.extract::<Vec<String>>().ok())
    {
        return Some(Predicate::PluginAny(
            plugins.into_iter().map(|p| p.to_lowercase()).collect(),
        ));
    }

    if let Some(layout) =
        get_opt_str(&map, "config_layout_is").and_then(|v| ConfigLayout::parse(&v))
    {
        return Some(Predicate::ConfigLayoutIs(layout));
    }

    if let Some(version) = get_opt_str(&map, "crashgen_version_lt") {
        let parts = version
            .split('.')
            .map(|part| part.trim().parse::<u32>().ok())
            .collect::<Vec<_>>();
        if parts.len() == 3 {
            return Some(Predicate::CrashgenVersionLt((
                parts[0]?, parts[1]?, parts[2]?,
            )));
        }
    }

    None
}

fn parse_expected_value(value: &Bound<'_, PyAny>) -> Option<ExpectedValue> {
    let map = as_dict(value)?;
    let equals = map.get_item("equals").ok().flatten()?;
    if let Ok(v) = equals.extract::<bool>() {
        return Some(ExpectedValue::Bool(v));
    }
    if let Ok(v) = equals.extract::<i64>() {
        return Some(ExpectedValue::Int(v));
    }
    equals.extract::<String>().ok().map(ExpectedValue::String)
}

/// Parse a Python mapping into typed crashgen settings rules.
///
/// The expected input shape mirrors the `CrashgenSettingsRules` schema used by
/// `classic_config_core` and returns `None` when required fields are
/// missing or invalid.
pub fn parse_settings_rules(value: &Bound<'_, PyAny>) -> Option<CrashgenSettingsRules> {
    let map = as_dict(value)?;

    let version = map
        .get_item("version")
        .ok()
        .flatten()
        .and_then(|v| v.extract::<u32>().ok())
        .unwrap_or(1);

    let preflight = map
        .get_item("preflight")
        .ok()
        .flatten()
        .and_then(|v| v.extract::<Vec<Bound<'_, PyAny>>>().ok())
        .unwrap_or_default()
        .into_iter()
        .filter_map(|item| {
            let item_map = as_dict(&item)?;
            let id = get_opt_str(&item_map, "id")?;
            let when = item_map
                .get_item("when")
                .ok()
                .flatten()
                .and_then(|v| parse_predicate(&v))
                .unwrap_or(Predicate::Always);
            let action_obj = item_map.get_item("action").ok().flatten()?;
            let action_map = as_dict(&action_obj)?;

            let kind = get_opt_str(&action_map, "kind")
                .and_then(|v| PreflightActionKind::parse(&v))
                .unwrap_or(PreflightActionKind::Notice);
            let bucket = get_opt_str(&action_map, "bucket")
                .and_then(|v| RuleReportBucket::parse(&v))
                .unwrap_or_default();
            let severity = get_opt_str(&action_map, "severity")
                .and_then(|v| RuleSeverity::parse(&v))
                .unwrap_or(RuleSeverity::Info);
            let message = get_opt_str(&action_map, "message")?;
            let fix = get_opt_str(&action_map, "fix");

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
        })
        .collect();

    let checks = map
        .get_item("checks")
        .ok()
        .flatten()
        .and_then(|v| v.extract::<Vec<Bound<'_, PyAny>>>().ok())
        .unwrap_or_default()
        .into_iter()
        .filter_map(|item| {
            let item_map = as_dict(&item)?;
            let id = get_opt_str(&item_map, "id")?;

            let target_obj = item_map.get_item("target").ok().flatten()?;
            let target_map = as_dict(&target_obj)?;
            let section = get_opt_str(&target_map, "section")?;
            let key = get_opt_str(&target_map, "key")?;
            let value_type = get_opt_str(&target_map, "value_type")
                .and_then(|v| TargetValueType::parse(&v))
                .unwrap_or(TargetValueType::Bool);

            let when = item_map
                .get_item("when")
                .ok()
                .flatten()
                .and_then(|v| parse_predicate(&v))
                .unwrap_or(Predicate::Always);

            let expect = item_map
                .get_item("expect")
                .ok()
                .flatten()
                .and_then(|v| parse_expected_value(&v))?;

            let messages_obj = item_map.get_item("messages").ok().flatten()?;
            let messages_map = as_dict(&messages_obj)?;
            let fail = get_opt_str(&messages_map, "fail")?;
            let fix = get_opt_str(&messages_map, "fix");
            let pass = get_opt_str(&messages_map, "pass");

            let severity = get_opt_str(&item_map, "severity")
                .and_then(|v| RuleSeverity::parse(&v))
                .unwrap_or(RuleSeverity::Warning);

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
        })
        .collect();

    Some(CrashgenSettingsRules {
        version,
        preflight,
        checks,
    })
}
