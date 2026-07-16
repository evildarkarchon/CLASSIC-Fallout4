//! Thin CXX adapter for focused semantic analyzer contracts.

use std::collections::HashSet;

use classic_config_core::{
    AutoscanReportPlacement as CoreAutoscanReportPlacement, ConfigLayout, CrashgenSettingsSnapshot,
    OutcomeKind, RuleSeverity, parse_crashgen_expectations,
};
use classic_scanlog_core::{
    AnalyzerError as CoreAnalyzerError, AnalyzerErrorCode as CoreAnalyzerErrorCode,
    AnalyzerKind as CoreAnalyzerKind, CrashgenEntry, CrashgenExpectationOutcome,
    CrashgenSettingsAnalysisInput, CrashgenSettingsAnalysisResult, CrashgenSettingsAnalyzer,
};

use super::ffi;

/// Bridge-owned error payload used for carrier decoding and core error projection.
#[derive(Clone, Debug)]
struct BridgeAnalyzerError {
    analyzer_kind: CoreAnalyzerKind,
    code: CoreAnalyzerErrorCode,
    message: String,
}

impl From<CoreAnalyzerError> for BridgeAnalyzerError {
    fn from(error: CoreAnalyzerError) -> Self {
        Self {
            analyzer_kind: error.analyzer(),
            code: error.code(),
            message: error.message().to_string(),
        }
    }
}

/// Immutable CXX-owned handle for one validated Crashgen Settings Analyzer.
///
/// Construction errors remain attached to the handle so C++ can inspect a
/// stable typed envelope without parsing a thrown exception. Successful
/// handles contain only immutable shared core state and are safe for concurrent calls.
pub(crate) struct CxxCrashgenSettingsAnalyzer {
    inner: Result<CrashgenSettingsAnalyzer, BridgeAnalyzerError>,
}

/// Constructs and validates a Crashgen Settings Analyzer from owned bridge configuration.
///
/// JSON is used only as the carrier for YAML-authored Crashgen Expectations;
/// `classic-config-core` remains the parser and the analyzer remains the owner
/// of validation and matcher compilation.
pub(crate) fn crashgen_settings_analyzer_new(
    configuration: ffi::CrashgenSettingsAnalyzerConfigurationDto,
) -> Box<CxxCrashgenSettingsAnalyzer> {
    Box::new(CxxCrashgenSettingsAnalyzer {
        inner: build_analyzer(configuration),
    })
}

/// Returns the explicit typed status captured while constructing an analyzer handle.
pub(crate) fn crashgen_settings_analyzer_construction_result(
    analyzer: &CxxCrashgenSettingsAnalyzer,
) -> ffi::CrashgenSettingsAnalyzerConstructionResultDto {
    match &analyzer.inner {
        Ok(_) => ffi::CrashgenSettingsAnalyzerConstructionResultDto {
            has_analyzer: true,
            has_error: false,
            error: empty_error_dto(),
        },
        Err(error) => ffi::CrashgenSettingsAnalyzerConstructionResultDto {
            has_analyzer: false,
            has_error: true,
            error: bridge_error_to_dto(error),
        },
    }
}

/// Runs one aggregate Crashgen Settings Analysis over a fully owned input DTO.
///
/// A valid analyzer always returns an explicit result, including when both
/// result collections are empty. Invalid construction and future analysis
/// failures retain their analyzer kind, stable code, and readable message.
pub(crate) fn crashgen_settings_analyze(
    analyzer: &CxxCrashgenSettingsAnalyzer,
    input: ffi::CrashgenSettingsAnalysisInputDto,
) -> ffi::CrashgenSettingsAnalysisExecutionResultDto {
    let core_analyzer = match &analyzer.inner {
        Ok(analyzer) => analyzer,
        Err(error) => return analysis_error_result(bridge_error_to_dto(error)),
    };

    match core_analyzer.analyze(input_to_core(input)) {
        Ok(result) => ffi::CrashgenSettingsAnalysisExecutionResultDto {
            has_result: true,
            result: result_to_dto(result),
            has_error: false,
            error: empty_error_dto(),
        },
        Err(error) => analysis_error_result(bridge_error_to_dto(&error.into())),
    }
}

/// Decodes carrier configuration, rejects parser diagnostics, and delegates
/// semantic validation and matcher compilation to the Rust core analyzer.
fn build_analyzer(
    configuration: ffi::CrashgenSettingsAnalyzerConfigurationDto,
) -> Result<CrashgenSettingsAnalyzer, BridgeAnalyzerError> {
    let (rules, diagnostics) = if configuration.has_settings_rules {
        let document =
            serde_json::from_str(&configuration.settings_rules_json).map_err(|error| {
                invalid_configuration_error(format!(
                    "settings_rules_json is not valid JSON: {error}"
                ))
            })?;
        let parsed = parse_crashgen_expectations(
            &document,
            configuration
                .has_settings_rules_version
                .then_some(configuration.settings_rules_version),
        );
        (parsed.rules, parsed.diagnostics)
    } else {
        (None, Vec::new())
    };

    CrashgenSettingsAnalyzer::from_parsed_configuration(
        configuration.crashgen_name,
        CrashgenEntry {
            display_section: configuration.display_section,
            ignore_keys: configuration.ignore_keys.into_iter().collect(),
            settings_rules: rules,
        },
        diagnostics,
    )
    .map_err(Into::into)
}

/// Converts authoritative presence flags and owned CXX fields into core input.
fn input_to_core(input: ffi::CrashgenSettingsAnalysisInputDto) -> CrashgenSettingsAnalysisInput {
    let mut settings = CrashgenSettingsSnapshot::new();
    for setting in input.settings {
        if setting.has_section {
            settings.insert(&setting.section, &setting.key, setting.value);
        } else {
            settings.insert_unscoped(&setting.key, setting.value);
        }
    }

    CrashgenSettingsAnalysisInput {
        settings,
        installed_plugins: input.installed_plugins.into_iter().collect::<HashSet<_>>(),
        crashgen_version: input.has_crashgen_version.then_some((
            input.crashgen_version_major,
            input.crashgen_version_minor,
            input.crashgen_version_patch,
        )),
        config_layout: match input.config_layout {
            ffi::CrashgenConfigLayout::Og => ConfigLayout::Og,
            ffi::CrashgenConfigLayout::Vr => ConfigLayout::Vr,
            ffi::CrashgenConfigLayout::Unknown => ConfigLayout::Unknown,
            _ => ConfigLayout::Unknown,
        },
    }
}

/// Projects one owned core aggregate result without adding presentation data.
fn result_to_dto(result: CrashgenSettingsAnalysisResult) -> ffi::CrashgenSettingsAnalysisResultDto {
    ffi::CrashgenSettingsAnalysisResultDto {
        expectation_outcomes: result
            .expectation_outcomes
            .into_iter()
            .map(outcome_to_dto)
            .collect(),
        disabled_setting_notices: result
            .disabled_setting_notices
            .into_iter()
            .map(|notice| ffi::DisabledSettingNoticeDto {
                setting_name: notice.setting_name,
            })
            .collect(),
    }
}

/// Projects one semantic outcome and flattens optional strings for CXX.
fn outcome_to_dto(outcome: CrashgenExpectationOutcome) -> ffi::CrashgenExpectationOutcomeDto {
    let (has_fix, fix) = flatten_optional(outcome.fix);
    let (has_section, section) = flatten_optional(outcome.section);
    let (has_setting, setting) = flatten_optional(outcome.setting);
    let (has_expected, expected) = flatten_optional(outcome.expected);
    let (has_actual, actual) = flatten_optional(outcome.actual);

    ffi::CrashgenExpectationOutcomeDto {
        rule_id: outcome.rule_id,
        kind: match outcome.kind {
            OutcomeKind::Notice => ffi::CrashgenExpectationOutcomeKind::Notice,
            OutcomeKind::Issue => ffi::CrashgenExpectationOutcomeKind::Issue,
            OutcomeKind::Success => ffi::CrashgenExpectationOutcomeKind::Success,
        },
        severity: match outcome.severity {
            RuleSeverity::Info => ffi::CrashgenExpectationSeverity::Info,
            RuleSeverity::Warning => ffi::CrashgenExpectationSeverity::Warning,
            RuleSeverity::Error => ffi::CrashgenExpectationSeverity::Error,
        },
        message: outcome.message,
        has_fix,
        fix,
        placement: match outcome.placement {
            CoreAutoscanReportPlacement::Settings => ffi::AutoscanReportPlacement::Settings,
            CoreAutoscanReportPlacement::ErrorInformation => {
                ffi::AutoscanReportPlacement::ErrorInformation
            }
        },
        has_section,
        section,
        has_setting,
        setting,
        has_expected,
        expected,
        has_actual,
        actual,
    }
}

/// Builds the error branch of the explicit analysis execution envelope.
fn analysis_error_result(
    error: ffi::AnalyzerErrorDto,
) -> ffi::CrashgenSettingsAnalysisExecutionResultDto {
    ffi::CrashgenSettingsAnalysisExecutionResultDto {
        has_result: false,
        result: ffi::CrashgenSettingsAnalysisResultDto {
            expectation_outcomes: Vec::new(),
            disabled_setting_notices: Vec::new(),
        },
        has_error: true,
        error,
    }
}

/// Creates the stable error used when the JSON carrier cannot represent valid rules.
fn invalid_configuration_error(message: String) -> BridgeAnalyzerError {
    BridgeAnalyzerError {
        analyzer_kind: CoreAnalyzerKind::CrashgenSettings,
        code: CoreAnalyzerErrorCode::InvalidConfiguration,
        message,
    }
}

/// Projects an internal error into the shared typed CXX payload.
fn bridge_error_to_dto(error: &BridgeAnalyzerError) -> ffi::AnalyzerErrorDto {
    ffi::AnalyzerErrorDto {
        analyzer_kind: analyzer_kind_to_dto(error.analyzer_kind),
        code: match error.code {
            CoreAnalyzerErrorCode::InvalidConfiguration => {
                ffi::AnalyzerErrorCode::InvalidConfiguration
            }
            CoreAnalyzerErrorCode::UnsupportedConfigurationVersion => {
                ffi::AnalyzerErrorCode::UnsupportedConfigurationVersion
            }
        },
        message: error.message.clone(),
    }
}

/// Maps every shared core analyzer identity to its stable CXX enum value.
fn analyzer_kind_to_dto(kind: CoreAnalyzerKind) -> ffi::AnalyzerKind {
    match kind {
        CoreAnalyzerKind::CrashgenSettings => ffi::AnalyzerKind::CrashgenSettings,
        CoreAnalyzerKind::CrashSuspect => ffi::AnalyzerKind::CrashSuspect,
        CoreAnalyzerKind::ModGuidance => ffi::AnalyzerKind::ModGuidance,
        CoreAnalyzerKind::PluginEvidence => ffi::AnalyzerKind::PluginEvidence,
        CoreAnalyzerKind::FormIdFinding => ffi::AnalyzerKind::FormIdFinding,
        CoreAnalyzerKind::NamedRecordFinding => ffi::AnalyzerKind::NamedRecordFinding,
    }
}

/// Builds the ignored placeholder required in a successful CXX envelope.
fn empty_error_dto() -> ffi::AnalyzerErrorDto {
    // CXX shared structs cannot omit a nested record; `has_error` remains authoritative.
    ffi::AnalyzerErrorDto {
        analyzer_kind: ffi::AnalyzerKind::CrashgenSettings,
        code: ffi::AnalyzerErrorCode::InvalidConfiguration,
        message: String::new(),
    }
}

/// Flattens an owned optional string into the bridge presence/value convention.
fn flatten_optional(value: Option<String>) -> (bool, String) {
    match value {
        Some(value) => (true, value),
        None => (false, String::new()),
    }
}

#[cfg(test)]
#[path = "analyzer_tests.rs"]
mod tests;
