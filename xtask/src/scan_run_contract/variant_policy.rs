//! Crash Log Scan Run variant-evidence policy: for every contract variant in
//! `tests/fixtures/crash_log_scan_run/manifest.json`, the conformance scenario
//! that exercises it, or the reason it has none.
//!
//! `scan-run-contract` requires the policy's variant set to equal the
//! manifest's `contractVariants`, and every runtime target's `scenario_id` to
//! be a `scenarios[].id` in the crash-log-scan-run pack
//! (`tests/conformance/packs/crash_log_scan_run/v1.json`). Retained variants
//! are irreducibly structural: no scenario can reach them, so they carry a
//! label only and nothing verifies them beyond their presence here.
//!
//! This replaces the Python `variant_policy.py`, which also named one observed
//! fact ID per variant. Fact IDs are not part of the pack, so the evidence is
//! now keyed on scenario IDs alone.

/// Repo-relative path of this file, used as the path of policy findings.
pub const POLICY_PATH: &str = "xtask/src/scan_run_contract/variant_policy.rs";

/// Retained label: the variant is covered only by the contract validator.
pub const CONTRACT_VALIDATOR: &str = "scan-run-contract-validator";
/// Retained label: a structured failure that only an internal fault produces.
pub const FAILURE_INTERNAL_FAULTS: &str = "scan-run-structured-failure-internal-faults";
/// Retained label: a Local Ignore reset outcome that only an internal fault
/// produces.
pub const RESET_INTERNAL_FAULTS: &str = "scan-run-local-ignore-reset-internal-faults";

/// What evidences one contract variant.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Evidence {
    /// A crash-log-scan-run pack scenario exercises the variant.
    Runtime {
        /// A `scenarios[].id` in the crash-log-scan-run pack.
        scenario_id: &'static str,
    },
    /// No scenario can reach the variant. Being its own variant (with no
    /// scenario field) is what enforces "retained implies no scenario".
    Retained {
        /// Why the variant has no runtime evidence.
        label: &'static str,
    },
}

/// One row of the policy.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct VariantTarget {
    /// `category.variant`, as in the manifest's `contractVariants`.
    pub variant: &'static str,
    /// The variant's evidence.
    pub evidence: Evidence,
    /// Line of this row in [`POLICY_PATH`], so findings point at the row.
    pub line: u32,
}

/// A runtime row. `line!()` expands to the line of the macro invocation, so
/// each row records its own source line.
macro_rules! runtime {
    ($variant:literal, $scenario:literal) => {
        VariantTarget {
            variant: $variant,
            evidence: Evidence::Runtime {
                scenario_id: $scenario,
            },
            line: line!(),
        }
    };
}

/// A retained row; see [`runtime!`] for the line capture.
macro_rules! retained {
    ($variant:literal, $label:expr) => {
        VariantTarget {
            variant: $variant,
            evidence: Evidence::Retained { label: $label },
            line: line!(),
        }
    };
}

/// The exact partition of every contract variant into runtime or retained
/// evidence. Keep one row per line so each finding points at its row.
#[rustfmt::skip]
pub const TARGETS: &[VariantTarget] = &[
    runtime!("request.standard", "standard-happy-path"),
    runtime!("request.targeted", "targeted-happy-path"),
    runtime!("event.discovery_completed", "standard-happy-path"),
    runtime!("event.effective_concurrency_selected", "standard-happy-path"),
    runtime!("event.log_queued", "standard-happy-path"),
    runtime!("event.log_started", "standard-happy-path"),
    runtime!("event.log_phase", "standard-happy-path"),
    runtime!("event.log_finished", "standard-happy-path"),
    runtime!("run_status.completed", "standard-happy-path"),
    runtime!("run_status.no_crash_logs_found", "standard-no-crash-logs-found"),
    runtime!("run_status.setup_failed", "fcx-setup-failed"),
    runtime!("run_status.cancelled_before_discovery", "pre-discovery-cancelled"),
    runtime!("run_status.cancelled", "admitted-durable-cancelled"),
    runtime!("run_status.local_ignore_recovery_required", "proceed-without-ignore-recovery"),
    runtime!("discovery_source.standard", "standard-happy-path"),
    runtime!("discovery_source.targeted", "targeted-happy-path"),
    runtime!("log_disposition.succeeded", "standard-happy-path"),
    runtime!("log_disposition.failed", "report-write-failure"),
    runtime!("log_disposition.cancelled_before_start", "post-discovery-queued-cancelled"),
    retained!("log_failure_stage.analysis", FAILURE_INTERNAL_FAULTS),
    runtime!("log_failure_stage.report_write", "report-write-failure"),
    runtime!("log_failure_stage.unsolved_logs_finalization", "unsolved-logs-finalization-failure"),
    runtime!("infrastructure_error_stage.request_validation", "request-validation-failure"),
    runtime!("infrastructure_error_stage.discovery", "discovery-failure"),
    runtime!("infrastructure_error_stage.intake", "intake-failure"),
    runtime!("infrastructure_error_stage.formid_database_access", "formid-database-access-failure"),
    retained!("infrastructure_error_stage.initialization", FAILURE_INTERNAL_FAULTS),
    retained!("infrastructure_error_stage.internal_invariant", FAILURE_INTERNAL_FAULTS),
    runtime!("unsolved_logs_intent.leave_in_place", "standard-happy-path"),
    runtime!("unsolved_logs_intent.move_to_configured_or_default", "unsolved-logs-finalization-failure"),
    runtime!("unsolved_logs_intent.move_to_custom", "custom-unsolved-logs-moved"),
    runtime!("progress_phase.setup", "standard-happy-path"),
    runtime!("progress_phase.parse", "standard-happy-path"),
    runtime!("progress_phase.analyze", "standard-happy-path"),
    runtime!("progress_phase.finalize", "standard-happy-path"),
    runtime!("installed_yaml_data_role.main", "standard-happy-path"),
    runtime!("installed_yaml_data_role.game", "standard-happy-path"),
    retained!("installed_yaml_data_provenance.updated", CONTRACT_VALIDATOR),
    retained!("installed_yaml_data_provenance.previous", CONTRACT_VALIDATOR),
    runtime!("installed_yaml_data_provenance.bundled", "standard-happy-path"),
    retained!("installed_yaml_data_diagnostic_kind.cache_unavailable", CONTRACT_VALIDATOR),
    retained!("installed_yaml_data_diagnostic_kind.missing", CONTRACT_VALIDATOR),
    retained!("installed_yaml_data_diagnostic_kind.read", CONTRACT_VALIDATOR),
    retained!("installed_yaml_data_diagnostic_kind.invalid_utf8", CONTRACT_VALIDATOR),
    runtime!("installed_yaml_data_diagnostic_kind.parse", "proceed-without-ignore-recovery"),
    retained!("installed_yaml_data_diagnostic_kind.invalid_schema", CONTRACT_VALIDATOR),
    retained!("installed_yaml_data_diagnostic_kind.incompatible_schema", CONTRACT_VALIDATOR),
    retained!("installed_yaml_data_diagnostic_kind.invalid_role_data", CONTRACT_VALIDATOR),
    runtime!("installed_yaml_data_diagnostic_kind.local_ignore_generated", "generated-local-ignore"),
    runtime!("installed_yaml_data_diagnostic_kind.local_ignore_reset", "reset-to-default-recovery"),
    runtime!("local_ignore_yaml_data_state.existing", "standard-happy-path"),
    runtime!("local_ignore_yaml_data_state.generated", "generated-local-ignore"),
    runtime!("local_ignore_yaml_data_state.recovery_required", "proceed-without-ignore-recovery"),
    runtime!("local_ignore_yaml_data_state.proceed_without_ignore", "proceed-without-ignore-recovery"),
    runtime!("local_ignore_yaml_data_state.reset_to_default", "reset-to-default-recovery"),
    runtime!("local_ignore_recovery_decision.proceed_without_ignore", "proceed-without-ignore-recovery"),
    runtime!("local_ignore_recovery_decision.reset_to_default", "reset-to-default-recovery"),
    runtime!("resume_error_kind.continuation_consumed", "proceed-without-ignore-recovery"),
    runtime!("resume_error_kind.local_ignore_reset_conflict", "reset-intervening-change-conflict"),
    runtime!("resume_error_kind.local_ignore_reset_backup_failure", "reset-operational-failure"),
    retained!("resume_error_kind.local_ignore_reset_replacement_failure", RESET_INTERNAL_FAULTS),
    retained!("resume_error_kind.local_ignore_reset_durability_unknown", RESET_INTERNAL_FAULTS),
    runtime!("resume_error_kind.infrastructure", "reset-operational-failure"),
    runtime!("observer_failure_policy.continue_run", "observer-delivery-failure-continue-run"),
    runtime!("observer_failure_policy.cancel_run", "observer-delivery-failure"),
    runtime!("recovery_continuation.retained_snapshot", "proceed-without-ignore-recovery"),
    runtime!("recovery_continuation.single_use", "proceed-without-ignore-recovery"),
    runtime!("recovery_continuation.pre_resume_cancelled", "reset-pre-cancelled"),
    runtime!("recovery_continuation.reset_success", "reset-to-default-recovery"),
    runtime!("recovery_continuation.reset_conflict", "reset-intervening-change-conflict"),
    runtime!("recovery_continuation.reset_operational_failure", "reset-operational-failure"),
    runtime!("recovery_continuation.reset_post_critical_cancelled", "reset-post-critical-cancelled"),
    runtime!("cancellation_seam.pre_discovery", "pre-discovery-cancelled"),
    runtime!("cancellation_seam.post_discovery_queued", "post-discovery-queued-cancelled"),
    runtime!("cancellation_seam.admitted", "admitted-durable-cancelled"),
];

#[cfg(test)]
#[path = "variant_policy_tests.rs"]
mod tests;
