//! Public registry key constants shared with Python.
use super::{RunnerResult, invalid};
use classic_registry_core::Keys;
use serde_json::{Value, json};

/// Read every common public key directly; no fixture-authored result enters execution.
pub(super) fn execute(fixture: &Value) -> RunnerResult<Value> {
    if fixture != &json!({"request":{}}) {
        return Err(invalid("unexpected registry keys input").into());
    }
    Ok(
        json!({"keys":{"YAML_CACHE":Keys::YAML_CACHE,"MANUAL_DOCS_GUI":Keys::MANUAL_DOCS_GUI,"GAME_PATH_GUI":Keys::GAME_PATH_GUI,"GAME_PATH":Keys::GAME_PATH,"DOCS_PATH":Keys::DOCS_PATH,"IS_GUI_MODE":Keys::IS_GUI_MODE,"OPEN_FILE_FUNC":Keys::OPEN_FILE_FUNC,"GAME":Keys::GAME,"GAME_VERSION":Keys::GAME_VERSION,"VERSION_AUTO_DETECTED":Keys::VERSION_AUTO_DETECTED,"LOCAL_DIR":Keys::LOCAL_DIR,"IS_PRERELEASE":Keys::IS_PRERELEASE,"XSE_VALID":Keys::XSE_VALID,"XSE_VERSION":Keys::XSE_VERSION,"ENB_PRESENT":Keys::ENB_PRESENT,"GAME_VERSION_DETECTED":Keys::GAME_VERSION_DETECTED}}),
    )
}
