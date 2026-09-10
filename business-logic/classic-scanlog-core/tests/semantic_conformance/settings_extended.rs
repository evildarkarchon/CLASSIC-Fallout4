//! Public validator and cached-document observations without host settings.
use super::{RunnerResult, invalid, text};
use classic_settings_core as settings;
use serde_json::{Value, json};

/// Reset the process-global cache even when a fixture or native operation fails.
struct CacheReset;
impl Drop for CacheReset {
    fn drop(&mut self) {
        settings::clear_cache();
    }
}

/// Exercise public operations and retain exact coerced values or cached payloads.
pub(super) fn execute(family: &str, fixture: &Value) -> RunnerResult<Value> {
    if family == "settings-validation" {
        use settings::validators::{
            CoercedValue, SettingType, coerce_setting_value, validate_setting_value,
        };
        let mut results = Vec::new();
        for item in fixture["cases"]
            .as_array()
            .ok_or_else(|| invalid("missing validation cases"))?
        {
            let value = text(&item["value"])?;
            let kind = match text(&item["type"])?.as_str() {
                "int" => SettingType::Int,
                "float" => SettingType::Float,
                "bool" => SettingType::Bool,
                "path" => SettingType::Path,
                "string" => SettingType::String,
                _ => return Err(invalid("unsupported setting type").into()),
            };
            let valid = validate_setting_value(&value, kind);
            let (value, error) = match coerce_setting_value(&value, kind) {
                Ok(value) => (
                    match value {
                        CoercedValue::Int(v) => json!(v),
                        // Receipt JSON excludes floating numbers; retain the numeric kind explicitly.
                        CoercedValue::Float(v) => json!({"float":format!("{v:e}")}),
                        CoercedValue::Bool(v) => json!(v),
                        CoercedValue::Path(v) | CoercedValue::String(v) => json!(v),
                    },
                    None,
                ),
                Err(error) => (Value::Null, Some(error)),
            };
            results.push(json!({"valid":valid,"value":value,"error":error}));
        }
        return Ok(json!({"results":results}));
    }
    settings::clear_cache();
    let _reset = CacheReset;
    let temporary = tempfile::tempdir()?;
    let path = temporary.path().join("input.yaml");
    let key = "conformance.cached-docs";
    let before = cached(key)?;
    std::fs::write(&path, text(&fixture["content"])?)?;
    settings::load_settings_sync(key, &path)?;
    let loaded = cached(key)?;
    std::fs::write(&path, text(&fixture["replacement"])?)?;
    let after = cached(key)?;
    settings::invalidate(key);
    let after_invalidate = cached(key)?;
    // Inspect after the final public read so even invalidation-time writeback is visible.
    let mut files = serde_json::Map::new();
    super::settings_load::inventory(temporary.path(), temporary.path(), &mut files)?;
    Ok(
        json!({"before":before,"cached":loaded,"afterFileChange":after,"afterInvalidate":after_invalidate,"files":files}),
    )
}

/// Normalize public YAML values while preserving absent and cached-empty results.
fn cached(key: &str) -> RunnerResult<Value> {
    match settings::get_cached(key) {
        None => Ok(Value::Null),
        Some(docs) => Ok(Value::Array(
            docs.iter()
                .map(super::settings_load::yaml_json)
                .collect::<RunnerResult<Vec<_>>>()?,
        )),
    }
}
