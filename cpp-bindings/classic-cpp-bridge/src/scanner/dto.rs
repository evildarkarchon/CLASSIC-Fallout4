use classic_scanlog_core::{
    AnalysisResult, ConfigIssue as CoreFcxConfigIssue, CrashLogScanOutcome,
    CrashLogScanRunLogOutcome,
};

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
        cancelled,
        moved_to_unsolved_logs: outcome.moved_to_unsolved_logs,
        error_message: outcome.error.unwrap_or_default(),
        processing_time_ms: outcome.processing_time_ms,
        formid_count: outcome.formid_count as u32,
        plugin_count: outcome.plugin_count as u32,
        suspect_count: outcome.suspect_count as u32,
    }
}

#[cfg(test)]
#[path = "dto_tests.rs"]
mod tests;
