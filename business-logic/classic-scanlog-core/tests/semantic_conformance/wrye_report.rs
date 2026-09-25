//! Native Wrye HTML parsing and report assembly observations.

use super::{RunnerResult, text};
use classic_scangame_core::WryeBashParser;
use serde_json::{Value, json};

/// Executes parsing and optional formatting from only authored input HTML and warnings.
pub(super) fn observe(fixture: &Value) -> RunnerResult<Value> {
    let parser = WryeBashParser::new(serde_json::from_value(fixture["warnings"].clone())?);
    let issues = parser.parse(&text(&fixture["html"])?);
    let mut result = json!({"issues":issues.iter().map(|issue|json!({"section":issue.section_title,"plugins":issue.plugins,"warning":issue.warning_message,"severity":format!("{:?}",issue.severity)})).collect::<Vec<_>>()});
    if fixture["operation"] == "format" {
        result["report"] = json!(WryeBashParser::format_report(&issues));
    }
    Ok(result)
}
