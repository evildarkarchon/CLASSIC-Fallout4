//! Read-only Windows platform comparisons without exposing personal path values.

use super::{RunnerResult, invalid};
use serde_json::Value;

/// Compare actual core results to a .NET registry oracle; only equality/absence reaches the receipt.
#[cfg(windows)]
pub(super) fn observe(fixture: &Value) -> RunnerResult<Value> {
    use classic_path_core::{DocsPathError, GamePathError};
    let oracle = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../tools/binding_compliance/platform_path_oracle.ps1");
    let child = std::process::Command::new("pwsh")
        .args(["-NoProfile", "-ExecutionPolicy", "Bypass", "-File"])
        .arg(oracle)
        .output()?;
    if !child.status.success() {
        return Err(invalid("read-only Windows reference lookup failed").into());
    }
    // Parse errors intentionally omit the response, which contains a private host path.
    let expected: Value = serde_json::from_slice(&child.stdout)
        .map_err(|_| invalid("invalid Windows reference JSON"))?;
    let actual = classic_path_core::get_system_documents_path()
        .ok()
        .map(|path| path.to_string_lossy().into_owned());
    let reference = expected["documents"].as_str().map(str::to_owned);
    let registry_missing = expected["missingKeyAbsent"] == true
        && matches!(
            classic_path_core::query_game_registry(
                fixture["registryGame"]
                    .as_str()
                    .ok_or_else(|| invalid("registry input"))?,
                "",
                false
            ),
            Err(GamePathError::RegistryNotFound)
        );
    let steam_unavailable = matches!(
        classic_path_core::parse_steam_library(
            fixture["steamId"]
                .as_u64()
                .ok_or_else(|| invalid("steam input"))? as u32
        ),
        Err(DocsPathError::NotFound)
    );
    Ok(
        serde_json::json!({"documentsAgree": actual == reference, "registryMissing": registry_missing, "steamUnavailable": steam_unavailable}),
    )
}

/// This platform-specific family has no non-Windows execution contract.
#[cfg(not(windows))]
pub(super) fn observe(_fixture: &Value) -> RunnerResult<Value> {
    Err(invalid("Windows platform conformance requires Windows").into())
}
