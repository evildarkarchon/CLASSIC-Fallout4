//! Shared token and legacy main-error parsing observations from native Rust APIs.

use super::{RunnerResult, invalid, text};
use classic_scanlog_core::{LogParser, detect_crash_pattern};
use serde_json::{Value, json};

/// Executes the input-selected native classifier or compatibility main-error projection.
pub(super) fn observe(fixture: &Value) -> RunnerResult<Value> {
    let content = text(&fixture["content"])?;
    match fixture["operation"].as_str() {
        Some("vr") => Ok(json!({"vr":classic_scanlog_core::detect_vr_log(&content)})),
        Some("classify") => Ok(json!({"token":detect_crash_pattern(&content)})),
        Some("legacy") => {
            let parser = LogParser::new(None)?;
            let lines = content.lines().map(str::to_owned).collect::<Vec<_>>();
            Ok(
                json!({"mainError":parser.parse_crash_header(&lines)?.get("main_error").cloned().unwrap_or_default()}),
            )
        }
        _ => Err(invalid("unknown crash-pattern operation").into()),
    }
}
