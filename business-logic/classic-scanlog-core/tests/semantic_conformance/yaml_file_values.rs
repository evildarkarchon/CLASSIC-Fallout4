//! Direct canonical YAML file enum observations.

use super::{RunnerResult, invalid};
use classic_settings_core::YamlFile;
use serde_json::{Value, json};

/// Read every core enum value and its documented path description.
pub(super) fn observe(fixture: &Value) -> RunnerResult<Value> {
    if fixture != &json!({"request":{}}) {
        return Err(invalid("unsupported YAML file value request").into());
    }
    Ok(
        json!({"kinds":YamlFile::all().map(|value| json!({"token":value.as_str(),"description":value.description()}))}),
    )
}
