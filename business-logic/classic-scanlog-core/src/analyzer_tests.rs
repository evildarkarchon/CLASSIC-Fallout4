use super::*;

#[test]
fn analyzer_kinds_and_error_codes_have_stable_names() {
    assert_eq!(AnalyzerKind::CrashgenSettings.as_str(), "crashgen_settings");
    assert_eq!(AnalyzerKind::CrashSuspect.as_str(), "crash_suspect");
    assert_eq!(AnalyzerKind::ModGuidance.as_str(), "mod_guidance");
    assert_eq!(AnalyzerKind::PluginEvidence.as_str(), "plugin_evidence");
    assert_eq!(AnalyzerKind::FormIdFinding.as_str(), "formid_finding");
    assert_eq!(
        AnalyzerKind::NamedRecordFinding.as_str(),
        "named_record_finding"
    );
    assert_eq!(
        AnalyzerErrorCode::InvalidConfiguration.as_str(),
        "invalid_configuration"
    );
    assert_eq!(
        AnalyzerErrorCode::UnsupportedConfigurationVersion.as_str(),
        "unsupported_configuration_version"
    );
}
