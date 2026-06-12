use super::*;
use classic_scanlog_core::{AnalysisResult, ConfigIssue};

#[test]
fn test_scan_result_dto() {
    let ar = AnalysisResult::success("test.log".to_string(), vec!["line1".to_string()], 1000);
    let dto = analysis_result_to_dto(ar);
    assert_eq!(dto.log_path, "test.log");
    assert!(dto.success);
    assert_eq!(dto.report_lines, vec!["line1"]);
    assert!(dto.error_message.is_empty());
}

#[test]
fn test_batch_scan_result_dto_preserves_progress_metadata() {
    let ar = AnalysisResult::success("batch.log".to_string(), vec!["line1".to_string()], 1000);
    let dto = analysis_result_to_batch_dto(3, 4, 10, ar);

    assert_eq!(dto.input_index, 3);
    assert_eq!(dto.completed, 4);
    assert_eq!(dto.total, 10);
    assert_eq!(dto.log_path, "batch.log");
    assert!(dto.success);
    assert_eq!(dto.report_lines, vec!["line1"]);
    assert!(dto.error_message.is_empty());
}

#[test]
fn test_fcx_issue_to_dto_round_trips_section_none() {
    let issue = ConfigIssue::new(
        "Fallout4.ini".to_string(),
        None,
        "iNumThreads".to_string(),
        "4".to_string(),
        "8".to_string(),
        "thread count too low".to_string(),
        "warning".to_string(),
    );

    let dto = fcx_issue_to_dto(&issue);

    assert_eq!(dto.file_path, "Fallout4.ini");
    assert_eq!(dto.section_or_empty, "");
    assert!(!dto.has_section);
    assert_eq!(dto.setting, "iNumThreads");
    assert_eq!(dto.current_value, "4");
    assert_eq!(dto.recommended_value, "8");
    assert_eq!(dto.description, "thread count too low");
    assert_eq!(dto.severity, "warning");
}

#[test]
fn test_fcx_issue_to_dto_round_trips_section_some() {
    let issue = ConfigIssue::new(
        "Fallout4Prefs.ini".to_string(),
        Some("Display".to_string()),
        "iSize W".to_string(),
        "640".to_string(),
        "1920".to_string(),
        "resolution too low".to_string(),
        "info".to_string(),
    );

    let dto = fcx_issue_to_dto(&issue);

    assert_eq!(dto.file_path, "Fallout4Prefs.ini");
    assert_eq!(dto.section_or_empty, "Display");
    assert!(dto.has_section);
    assert_eq!(dto.setting, "iSize W");
    assert_eq!(dto.current_value, "640");
    assert_eq!(dto.recommended_value, "1920");
    assert_eq!(dto.description, "resolution too low");
    assert_eq!(dto.severity, "info");
}
