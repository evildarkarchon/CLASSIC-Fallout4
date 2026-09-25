//! Observes public Vocabulary resolution without reading labels from expectations.

use super::{RunnerResult, invalid, strings, text};
use classic_config_core::{
    InstalledYamlDataDiagnosticKind, InstalledYamlDataProvenance, LocalIgnoreYamlDataState,
};
use classic_scanlog_core::scan_run::contract::{
    InfrastructureErrorStage, InstalledYamlDataRunDiagnosticKind, LocalIgnoreResetFailureStage,
    LocalIgnoreRunState, LogDisposition, LogFailureStage,
};
use classic_vocabulary::{Vocabulary, from_token};
use serde_json::{Value, json};

/// Identifies the two independently owned label-resolution contracts.
pub(super) fn is_family(family: &Value) -> bool {
    family == "config-vocabulary" || family == "scan-run-vocabulary"
}

/// Resolves each input against the actual owner, retaining unknown tokens and order.
fn entries<T: Vocabulary>(tokens: &[String]) -> Vec<Value> {
    tokens
        .iter()
        .map(|token| {
            let label = from_token::<T>(token).map(Vocabulary::label);
            json!({"token": token, "label": label, "rejected": label.is_none()})
        })
        .collect()
}

/// Invokes one core-owned resolver from a direct input-only scenario.
pub(super) fn execute(family: &str, scenario: &Value) -> RunnerResult<Value> {
    if scenario["action"] != "vocabulary.resolve" || scenario["fixtureRefs"] != json!([]) {
        return Err(
            invalid("vocabulary scenarios require direct inputs and vocabulary.resolve").into(),
        );
    }
    let operation = text(&scenario["input"]["operation"])?;
    let tokens = strings(&scenario["input"]["tokens"])?;
    let entries = match (family, operation.as_str()) {
        (
            "config-vocabulary",
            "installed_yaml_data_provenance_label"
            | "scan_run_installed_yaml_data_provenance_label",
        ) => entries::<InstalledYamlDataProvenance>(&tokens),
        ("config-vocabulary", "installed_yaml_data_diagnostic_kind_label") => {
            entries::<InstalledYamlDataDiagnosticKind>(&tokens)
        }
        ("config-vocabulary", "local_ignore_yaml_data_state_label") => {
            entries::<LocalIgnoreYamlDataState>(&tokens)
        }
        ("scan-run-vocabulary", "scan_run_installed_yaml_data_diagnostic_kind_label") => {
            entries::<InstalledYamlDataRunDiagnosticKind>(&tokens)
        }
        ("scan-run-vocabulary", "scan_run_local_ignore_yaml_data_state_label") => {
            entries::<LocalIgnoreRunState>(&tokens)
        }
        ("scan-run-vocabulary", "scan_run_log_disposition_label") => {
            entries::<LogDisposition>(&tokens)
        }
        ("scan-run-vocabulary", "scan_run_log_failure_stage_label") => {
            entries::<LogFailureStage>(&tokens)
        }
        ("scan-run-vocabulary", "scan_run_infrastructure_error_stage_label") => {
            entries::<InfrastructureErrorStage>(&tokens)
        }
        ("scan-run-vocabulary", "scan_run_local_ignore_reset_failure_stage_label") => {
            entries::<LocalIgnoreResetFailureStage>(&tokens)
        }
        _ => return Err(invalid("unsupported vocabulary operation for family").into()),
    };
    Ok(json!({"operation": operation, "entries": entries}))
}
