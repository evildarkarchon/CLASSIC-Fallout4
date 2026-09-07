//! Input-only shared string and registry transports using their separate core owners.

use super::{RunnerResult, invalid, strings, text};
use classic_registry_core as registry;
use classic_shared_core::strings_core::{StringOperation, StringProcessor};
use serde_json::{Value, json};

/// Reset dedicated-process registry state on success and early failure alike.
struct RegistryReset;

impl Drop for RegistryReset {
    fn drop(&mut self) {
        registry::clear_all();
    }
}

/// Observe public operations without receiving authored expected values.
pub(super) fn execute(family: &str, fixture: &Value) -> RunnerResult<Value> {
    let request = &fixture["request"];
    if family == "string-operations" {
        let processor = StringProcessor::new();
        let values = strings(&request["values"])?;
        let refs: Vec<_> = values.iter().map(String::as_str).collect();
        let interned: Vec<_> = values.iter().map(|value| processor.intern(value)).collect();
        let normalized: Vec<_> = values
            .iter()
            .map(|value| processor.normalize_string(value))
            .collect();
        return Ok(json!({"interned": interned, "normalized": normalized,
            "batch": processor.process_batch(&refs, StringOperation::Normalize)}));
    }
    if family != "registry-operations" {
        return Err(invalid("unsupported shared/registry family").into());
    }
    // This executable runs one plan serially in its own process. The guard keeps
    // a failed scenario from leaking global entries into the next observation.
    registry::clear_all();
    let _reset = RegistryReset;
    let initially_present = registry::is_registered("conformance.stringValue");
    registry::register("conformance.stringValue", text(&request["stringValue"])?);
    registry::register(
        "conformance.boolValue",
        request["boolValue"]
            .as_bool()
            .ok_or_else(|| invalid("expected boolean"))?,
    );
    let integer = i32::try_from(
        request["intValue"]
            .as_i64()
            .ok_or_else(|| invalid("expected integer"))?,
    )?;
    registry::register("conformance.intValue", integer);
    let stored = json!({"stringValue": registry::get::<_, String>("conformance.stringValue"),
        "boolValue": registry::get::<_, bool>("conformance.boolValue"),
        "intValue": registry::get::<_, i32>("conformance.intValue")});
    registry::register("conformance.stringValue", text(&request["replacement"])?);
    let replacement = registry::get::<_, String>("conformance.stringValue");
    registry::unregister("conformance.stringValue");
    let after_remove = registry::is_registered("conformance.stringValue");
    registry::clear_all();
    let after_clear = registry::is_registered("conformance.boolValue")
        || registry::is_registered("conformance.intValue");
    Ok(
        json!({"initiallyPresent": initially_present, "stored": stored, "replacement": replacement,
        "afterRemovePresent": after_remove, "afterClearPresent": after_clear}),
    )
}
