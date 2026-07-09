use classic_scanlog_core::{
    AnalysisResult, ConfigIssue as CoreFcxConfigIssue, CrashLogScanDiscoveryResult,
    CrashLogScanOutcome, CrashLogScanRunLogOutcome, CrashLogScanRunResult, CrashLogScanSetupResult,
};
use std::path::PathBuf;

use super::ffi;

pub(super) fn fcx_issue_to_dto(issue: &CoreFcxConfigIssue) -> ffi::FcxIssueDto {
    let has_section = issue.section.is_some();
    ffi::FcxIssueDto {
        file_path: issue.file_path.clone(),
        section_or_empty: issue.section.clone().unwrap_or_default(),
        has_section,
        setting: issue.setting.clone(),
        current_value: issue.current_value.clone(),
        recommended_value: issue.recommended_value.clone(),
        description: issue.description.clone(),
        severity: issue.severity.clone(),
    }
}

pub(super) fn batch_reset_failure_result(
    log_path: String,
    error_message: String,
) -> ffi::ScanResult {
    ffi::ScanResult {
        log_path,
        success: false,
        report_lines: Vec::new(),
        error_message,
        processing_time_ms: 0,
        formid_count: 0,
        plugin_count: 0,
        suspect_count: 0,
    }
}

pub(super) fn batch_progress_reset_failure_result(
    input_index: u32,
    total: u32,
    log_path: String,
    error_message: String,
) -> ffi::BatchScanResult {
    ffi::BatchScanResult {
        input_index,
        completed: 0,
        total,
        log_path,
        success: false,
        report_lines: Vec::new(),
        error_message,
        processing_time_ms: 0,
        formid_count: 0,
        plugin_count: 0,
        suspect_count: 0,
    }
}

pub(super) fn analysis_result_to_dto(r: AnalysisResult) -> ffi::ScanResult {
    ffi::ScanResult {
        log_path: r.log_path,
        success: r.success,
        report_lines: r.report_lines,
        error_message: r.error.unwrap_or_default(),
        processing_time_ms: r.processing_time_ms,
        formid_count: r.formid_count as u32,
        plugin_count: r.plugin_count as u32,
        suspect_count: r.suspect_count as u32,
    }
}

pub(super) fn analysis_result_to_batch_dto(
    input_index: u32,
    completed: u32,
    total: u32,
    r: AnalysisResult,
) -> ffi::BatchScanResult {
    ffi::BatchScanResult {
        input_index,
        completed,
        total,
        log_path: r.log_path,
        success: r.success,
        report_lines: r.report_lines,
        error_message: r.error.unwrap_or_default(),
        processing_time_ms: r.processing_time_ms,
        formid_count: r.formid_count as u32,
        plugin_count: r.plugin_count as u32,
        suspect_count: r.suspect_count as u32,
    }
}

pub(super) fn scan_run_log_outcome_to_dto(
    outcome: CrashLogScanRunLogOutcome,
) -> ffi::ScanRunLogResult {
    let success = outcome.outcome == CrashLogScanOutcome::Succeeded;
    let cancelled = outcome.outcome == CrashLogScanOutcome::CancelledBeforeStart;
    ffi::ScanRunLogResult {
        input_index: outcome.input_index as u32,
        log_path: outcome.crash_log.to_string_lossy().to_string(),
        autoscan_report_path: outcome
            .autoscan_report
            .map(|path| path.to_string_lossy().to_string())
            .unwrap_or_default(),
        success,
        report_write_failed: outcome.report_write_failed,
        cancelled,
        moved_to_unsolved_logs: outcome.moved_to_unsolved_logs,
        error_message: outcome.error.unwrap_or_default(),
        processing_time_ms: outcome.processing_time_ms,
        formid_count: outcome.formid_count as u32,
        plugin_count: outcome.plugin_count as u32,
        suspect_count: outcome.suspect_count as u32,
    }
}

fn path_to_string(path: PathBuf) -> String {
    path.to_string_lossy().to_string()
}

fn empty_scan_run_discovery_dto() -> ffi::ScanRunDiscoveryResult {
    ffi::ScanRunDiscoveryResult {
        source: String::new(),
        accepted_logs: Vec::new(),
        rejected_paths: Vec::new(),
        rejected_reasons: Vec::new(),
        searched_locations: Vec::new(),
    }
}

fn scan_run_discovery_to_dto(
    discovery: CrashLogScanDiscoveryResult,
) -> ffi::ScanRunDiscoveryResult {
    let mut rejected_paths = Vec::with_capacity(discovery.rejected_inputs.len());
    let mut rejected_reasons = Vec::with_capacity(discovery.rejected_inputs.len());
    for rejected in discovery.rejected_inputs {
        rejected_paths.push(path_to_string(rejected.path));
        rejected_reasons.push(rejected.reason);
    }

    ffi::ScanRunDiscoveryResult {
        source: discovery.source.as_str().to_string(),
        accepted_logs: discovery
            .accepted_logs
            .into_iter()
            .map(path_to_string)
            .collect(),
        rejected_paths,
        rejected_reasons,
        searched_locations: discovery
            .searched_locations
            .into_iter()
            .map(path_to_string)
            .collect(),
    }
}

fn empty_scan_run_setup_dto() -> ffi::ScanRunSetupResultDto {
    ffi::ScanRunSetupResultDto {
        status: String::new(),
        message: String::new(),
        rendered_report: String::new(),
        checks: Vec::new(),
        path_updates: Vec::new(),
        configuration_issues: Vec::new(),
        actions: Vec::new(),
        fatal_errors: Vec::new(),
    }
}

fn scan_run_setup_to_dto(setup: CrashLogScanSetupResult) -> ffi::ScanRunSetupResultDto {
    ffi::ScanRunSetupResultDto {
        status: setup.status,
        message: setup.message.unwrap_or_default(),
        rendered_report: setup.rendered_report,
        checks: setup
            .checks
            .into_iter()
            .map(|check| ffi::ScanRunSetupCheckDto {
                kind: check.kind,
                state: check.state,
                message: check.message,
                details: check.details,
            })
            .collect(),
        path_updates: setup
            .path_updates
            .into_iter()
            .map(|update| ffi::ScanRunSetupPathUpdateDto {
                kind: update.kind,
                path: path_to_string(update.path),
            })
            .collect(),
        configuration_issues: setup
            .configuration_issues
            .iter()
            .map(fcx_issue_to_dto)
            .collect(),
        actions: setup.actions,
        fatal_errors: setup.fatal_errors,
    }
}

pub(super) fn scan_run_result_to_dto(result: CrashLogScanRunResult) -> ffi::ScanRunResult {
    let discovery = result
        .discovery
        .map(scan_run_discovery_to_dto)
        .unwrap_or_else(empty_scan_run_discovery_dto);
    let (has_setup, setup) = result
        .setup
        .map(|setup| (true, scan_run_setup_to_dto(setup)))
        .unwrap_or_else(|| (false, empty_scan_run_setup_dto()));

    ffi::ScanRunResult {
        status: result.status.as_str().to_string(),
        message: result.message.unwrap_or_default(),
        total: result.total as u32,
        succeeded: result.succeeded as u32,
        failed: result.failed as u32,
        cancelled: result.cancelled as u32,
        discovery,
        has_setup,
        setup,
        logs: result
            .logs
            .into_iter()
            .map(scan_run_log_outcome_to_dto)
            .collect(),
    }
}

#[cfg(test)]
#[path = "dto_tests.rs"]
mod tests;
