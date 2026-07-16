//! Thin CXX adapter for focused semantic analyzer contracts.

use std::collections::HashSet;

use classic_config_core::{
    AutoscanReportPlacement as CoreAutoscanReportPlacement, ConfigLayout, CoreModEntry,
    CoreModExclude, CrashgenSettingsSnapshot, ModConflictEntry, ModSolutionCriteria,
    ModSolutionEntry, OutcomeKind, RuleSeverity, SuspectErrorRule, SuspectStackCountRule,
    SuspectStackRule, parse_crashgen_expectations,
};
use classic_scanlog_core::mod_guidance_analyzer::{
    ImportantModGuidance, ModConflictGuidance, ModGuidanceAnalysisInput, ModGuidanceAnalysisResult,
    ModGuidanceAnalyzer, ModGuidanceMatchState, ModSolutionGuidance,
};
use classic_scanlog_core::{
    AnalyzerError as CoreAnalyzerError, AnalyzerErrorCode as CoreAnalyzerErrorCode,
    AnalyzerKind as CoreAnalyzerKind, CrashSuspectAnalysisInput, CrashSuspectAnalysisResult,
    CrashSuspectAnalyzer, CrashSuspectFinding, CrashSuspectFindingKind, CrashgenEntry,
    CrashgenExpectationOutcome, CrashgenSettingsAnalysisInput, CrashgenSettingsAnalysisResult,
    CrashgenSettingsAnalyzer,
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

/// Immutable CXX-owned handle for one validated Crash Suspect Analyzer.
pub(crate) struct CxxCrashSuspectAnalyzer {
    inner: Result<CrashSuspectAnalyzer, BridgeAnalyzerError>,
}

/// Immutable CXX-owned handle for one validated aggregate Mod Guidance Analyzer.
pub(crate) struct CxxModGuidanceAnalyzer {
    inner: Result<ModGuidanceAnalyzer, BridgeAnalyzerError>,
}

/// Constructs and validates a Mod Guidance Analyzer from owned bridge configuration.
pub(crate) fn mod_guidance_analyzer_new(
    configuration: ffi::ModGuidanceAnalyzerConfigurationDto,
) -> Box<CxxModGuidanceAnalyzer> {
    Box::new(CxxModGuidanceAnalyzer {
        inner: build_mod_guidance_analyzer(configuration),
    })
}

/// Returns the explicit typed status captured during Mod Guidance construction.
pub(crate) fn mod_guidance_analyzer_construction_result(
    analyzer: &CxxModGuidanceAnalyzer,
) -> ffi::ModGuidanceAnalyzerConstructionResultDto {
    match &analyzer.inner {
        Ok(_) => ffi::ModGuidanceAnalyzerConstructionResultDto {
            has_analyzer: true,
            has_error: false,
            error: empty_error_dto(),
        },
        Err(error) => ffi::ModGuidanceAnalyzerConstructionResultDto {
            has_analyzer: false,
            has_error: true,
            error: bridge_error_to_dto(error),
        },
    }
}

/// Runs aggregate Mod Guidance analysis and preserves the shared typed error envelope.
pub(crate) fn mod_guidance_analyze(
    analyzer: &CxxModGuidanceAnalyzer,
    input: ffi::ModGuidanceAnalysisInputDto,
) -> ffi::ModGuidanceAnalysisExecutionResultDto {
    let core_analyzer = match &analyzer.inner {
        Ok(analyzer) => analyzer,
        Err(error) => return mod_guidance_error_result(bridge_error_to_dto(error)),
    };

    let plugins = input
        .plugins
        .into_iter()
        .map(|plugin| (plugin.name, plugin.id))
        .collect();
    let core_input = ModGuidanceAnalysisInput {
        plugins,
        user_gpu: input.has_user_gpu.then_some(input.user_gpu),
        xse_modules: input.xse_modules.into_iter().collect(),
    };

    match core_analyzer.analyze(core_input) {
        Ok(result) => ffi::ModGuidanceAnalysisExecutionResultDto {
            has_result: true,
            result: mod_guidance_result_to_dto(result),
            has_error: false,
            error: empty_error_dto(),
        },
        Err(error) => mod_guidance_error_result(bridge_error_to_dto(&error.into())),
    }
}

/// Converts owned CXX configuration into the authoritative core configuration model.
fn build_mod_guidance_analyzer(
    configuration: ffi::ModGuidanceAnalyzerConfigurationDto,
) -> Result<ModGuidanceAnalyzer, BridgeAnalyzerError> {
    let conflicts = configuration
        .conflicts
        .into_iter()
        .map(|entry| ModConflictEntry {
            mod_a: entry.mod_a,
            mod_b: entry.mod_b,
            name_a: entry.name_a,
            name_b: entry.name_b,
            description: entry.description,
            fix: entry.fix,
            link: entry.has_link.then_some(entry.link),
        })
        .collect();
    let frequent_crashes = configuration
        .frequent_crashes
        .into_iter()
        .map(mod_guidance_solution_configuration_to_core)
        .collect::<Result<Vec<_>, _>>()?;
    let solutions = configuration
        .solutions
        .into_iter()
        .map(mod_guidance_solution_configuration_to_core)
        .collect::<Result<Vec<_>, _>>()?;
    let important_mods = configuration
        .important_mods
        .into_iter()
        .map(|entry| CoreModEntry {
            detect: entry.detect,
            name: entry.name,
            description: entry.description,
            gpu: entry.has_gpu.then_some(entry.gpu),
            gpu_mismatch_warning: entry
                .has_gpu_mismatch_warning
                .then_some(entry.gpu_mismatch_warning),
            exclude_when: entry
                .has_exclude_when_plugin_any
                .then_some(CoreModExclude::PluginAny(entry.exclude_when_plugin_any)),
        })
        .collect();

    ModGuidanceAnalyzer::new(conflicts, frequent_crashes, solutions, important_mods)
        .map_err(Into::into)
}

/// Converts one bridge criteria discriminant into the core grouped criteria model.
fn mod_guidance_solution_configuration_to_core(
    entry: ffi::ModGuidanceSolutionConfigurationDto,
) -> Result<ModSolutionEntry, BridgeAnalyzerError> {
    let criteria = match entry.criteria_kind {
        ffi::ModGuidanceCriteriaKind::Any => ModSolutionCriteria::Any(entry.criteria),
        ffi::ModGuidanceCriteriaKind::All => ModSolutionCriteria::All(entry.criteria),
        _ => {
            return Err(BridgeAnalyzerError {
                analyzer_kind: CoreAnalyzerKind::ModGuidance,
                code: CoreAnalyzerErrorCode::InvalidConfiguration,
                message: "Mod Guidance criteria kind is not supported".to_string(),
            });
        }
    };
    Ok(ModSolutionEntry {
        id: entry.id,
        criteria,
        exceptions: entry.exceptions,
        name: entry.name,
        description: entry.description,
    })
}

/// Projects one owned aggregate Mod Guidance result without report presentation data.
fn mod_guidance_result_to_dto(
    result: ModGuidanceAnalysisResult,
) -> ffi::ModGuidanceAnalysisResultDto {
    ffi::ModGuidanceAnalysisResultDto {
        conflicts: result
            .conflicts
            .into_iter()
            .map(mod_conflict_guidance_to_dto)
            .collect(),
        frequent_crashes: result
            .frequent_crashes
            .into_iter()
            .map(mod_solution_guidance_to_dto)
            .collect(),
        solutions: result
            .solutions
            .into_iter()
            .map(mod_solution_guidance_to_dto)
            .collect(),
        important_mods: result
            .important_mods
            .into_iter()
            .map(important_mod_guidance_to_dto)
            .collect(),
    }
}

/// Projects one conflict while preserving optional link presence explicitly.
fn mod_conflict_guidance_to_dto(guidance: ModConflictGuidance) -> ffi::ModConflictGuidanceDto {
    let (has_link, link) = flatten_optional(guidance.link);
    ffi::ModConflictGuidanceDto {
        state: mod_guidance_match_state_to_dto(guidance.state),
        mod_a: guidance.mod_a,
        mod_b: guidance.mod_b,
        name_a: guidance.name_a,
        name_b: guidance.name_b,
        description: guidance.description,
        fix: guidance.fix,
        has_link,
        link,
    }
}

/// Projects one frequent-crash or solution result with its matched load-order identifiers.
fn mod_solution_guidance_to_dto(guidance: ModSolutionGuidance) -> ffi::ModSolutionGuidanceDto {
    ffi::ModSolutionGuidanceDto {
        state: mod_guidance_match_state_to_dto(guidance.state),
        id: guidance.id,
        name: guidance.name,
        description: guidance.description,
        matched_plugin_ids: guidance.matched_plugin_ids,
    }
}

/// Projects one important-mod result with explicit GPU and warning presence.
fn important_mod_guidance_to_dto(guidance: ImportantModGuidance) -> ffi::ImportantModGuidanceDto {
    let (has_gpu, gpu) = flatten_optional(guidance.gpu);
    let (has_gpu_mismatch_warning, gpu_mismatch_warning) =
        flatten_optional(guidance.gpu_mismatch_warning);
    ffi::ImportantModGuidanceDto {
        state: mod_guidance_match_state_to_dto(guidance.state),
        detect: guidance.detect,
        name: guidance.name,
        description: guidance.description,
        has_gpu,
        gpu,
        has_gpu_mismatch_warning,
        gpu_mismatch_warning,
    }
}

/// Maps the shared core Mod Guidance match state to its stable CXX discriminant.
fn mod_guidance_match_state_to_dto(state: ModGuidanceMatchState) -> ffi::ModGuidanceMatchState {
    match state {
        ModGuidanceMatchState::Matched => ffi::ModGuidanceMatchState::Matched,
        ModGuidanceMatchState::Missing => ffi::ModGuidanceMatchState::Missing,
        ModGuidanceMatchState::GpuMismatch => ffi::ModGuidanceMatchState::GpuMismatch,
    }
}

/// Builds the error branch of the explicit Mod Guidance execution envelope.
fn mod_guidance_error_result(
    error: ffi::AnalyzerErrorDto,
) -> ffi::ModGuidanceAnalysisExecutionResultDto {
    ffi::ModGuidanceAnalysisExecutionResultDto {
        has_result: false,
        result: ffi::ModGuidanceAnalysisResultDto {
            conflicts: Vec::new(),
            frequent_crashes: Vec::new(),
            solutions: Vec::new(),
            important_mods: Vec::new(),
        },
        has_error: true,
        error,
    }
}

/// Constructs and validates a Crash Suspect Analyzer from owned bridge rules.
pub(crate) fn crash_suspect_analyzer_new(
    configuration: ffi::CrashSuspectAnalyzerConfigurationDto,
) -> Box<CxxCrashSuspectAnalyzer> {
    let main_error_rules = configuration
        .main_error_rules
        .into_iter()
        .map(|rule| SuspectErrorRule {
            id: rule.id,
            name: rule.name,
            severity: rule.severity,
            main_error_contains_any: rule.main_error_contains_any,
        })
        .collect();
    let stack_rules = configuration
        .stack_rules
        .into_iter()
        .map(|rule| SuspectStackRule {
            id: rule.id,
            name: rule.name,
            severity: rule.severity,
            main_error_required_any: rule.main_error_required_any,
            main_error_optional_any: rule.main_error_optional_any,
            stack_contains_any: rule.stack_contains_any,
            exclude_if_stack_contains_any: rule.exclude_if_stack_contains_any,
            stack_contains_at_least: rule
                .stack_contains_at_least
                .into_iter()
                .map(|count_rule| SuspectStackCountRule {
                    substring: count_rule.substring,
                    count: count_rule.count,
                })
                .collect(),
        })
        .collect();

    Box::new(CxxCrashSuspectAnalyzer {
        inner: CrashSuspectAnalyzer::new(main_error_rules, stack_rules).map_err(Into::into),
    })
}

/// Returns the explicit typed status captured during Crash Suspect construction.
pub(crate) fn crash_suspect_analyzer_construction_result(
    analyzer: &CxxCrashSuspectAnalyzer,
) -> ffi::CrashSuspectAnalyzerConstructionResultDto {
    match &analyzer.inner {
        Ok(_) => ffi::CrashSuspectAnalyzerConstructionResultDto {
            has_analyzer: true,
            has_error: false,
            error: empty_error_dto(),
        },
        Err(error) => ffi::CrashSuspectAnalyzerConstructionResultDto {
            has_analyzer: false,
            has_error: true,
            error: bridge_error_to_dto(error),
        },
    }
}

/// Runs aggregate Crash Suspect analysis and preserves the shared typed error envelope.
pub(crate) fn crash_suspect_analyze(
    analyzer: &CxxCrashSuspectAnalyzer,
    input: ffi::CrashSuspectAnalysisInputDto,
) -> ffi::CrashSuspectAnalysisExecutionResultDto {
    let core_analyzer = match &analyzer.inner {
        Ok(analyzer) => analyzer,
        Err(error) => return crash_suspect_error_result(bridge_error_to_dto(error)),
    };

    match core_analyzer.analyze(CrashSuspectAnalysisInput {
        main_error: input.main_error,
        call_stack: input.call_stack,
    }) {
        Ok(result) => ffi::CrashSuspectAnalysisExecutionResultDto {
            has_result: true,
            result: crash_suspect_result_to_dto(result),
            has_error: false,
            error: empty_error_dto(),
        },
        Err(error) => crash_suspect_error_result(bridge_error_to_dto(&error.into())),
    }
}

/// Projects one owned semantic Crash Suspect result without adding presentation data.
fn crash_suspect_result_to_dto(
    result: CrashSuspectAnalysisResult,
) -> ffi::CrashSuspectAnalysisResultDto {
    ffi::CrashSuspectAnalysisResultDto {
        findings: result
            .findings
            .into_iter()
            .map(crash_suspect_finding_to_dto)
            .collect(),
    }
}

/// Flattens optional rule facts for CXX while retaining the semantic finding kind.
fn crash_suspect_finding_to_dto(finding: CrashSuspectFinding) -> ffi::CrashSuspectFindingDto {
    let kind = match finding.kind() {
        CrashSuspectFindingKind::MainErrorRule => ffi::CrashSuspectFindingKind::MainErrorRule,
        CrashSuspectFindingKind::StackRule => ffi::CrashSuspectFindingKind::StackRule,
        CrashSuspectFindingKind::DllInvolvement => ffi::CrashSuspectFindingKind::DllInvolvement,
    };
    match finding {
        CrashSuspectFinding::MainErrorRule {
            rule_id,
            name,
            severity,
        } => ffi::CrashSuspectFindingDto {
            kind,
            has_rule_id: true,
            rule_id,
            has_name: true,
            name,
            has_severity: true,
            severity,
        },
        CrashSuspectFinding::StackRule {
            rule_id,
            name,
            severity,
        } => ffi::CrashSuspectFindingDto {
            kind,
            has_rule_id: true,
            rule_id,
            has_name: true,
            name,
            has_severity: true,
            severity,
        },
        CrashSuspectFinding::DllInvolvement => ffi::CrashSuspectFindingDto {
            kind,
            has_rule_id: false,
            rule_id: String::new(),
            has_name: false,
            name: String::new(),
            has_severity: false,
            severity: 0,
        },
    }
}

/// Builds the error branch of the explicit Crash Suspect execution envelope.
fn crash_suspect_error_result(
    error: ffi::AnalyzerErrorDto,
) -> ffi::CrashSuspectAnalysisExecutionResultDto {
    ffi::CrashSuspectAnalysisExecutionResultDto {
        has_result: false,
        result: ffi::CrashSuspectAnalysisResultDto {
            findings: Vec::new(),
        },
        has_error: true,
        error,
    }
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
