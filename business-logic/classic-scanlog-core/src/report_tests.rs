use super::*;
use crate::autoscan_report_contribution_collector::AutoscanReportContributions;
use crate::version::CrashgenVersionStatus;
use crate::{
    CrashSuspectAnalysisResult, CrashSuspectFinding, CrashgenExpectationOutcome,
    CrashgenSettingsAnalysisResult, DisabledSettingNotice, FormIDFinding,
    FormIDFindingAnalysisResult, FormIDValueLookupStatus, NamedRecordFinding,
    NamedRecordFindingAnalysisResult, PluginEvidence, PluginEvidenceAnalysisResult,
};
use classic_config_core::{AutoscanReportPlacement, OutcomeKind, RuleSeverity};

fn base_facts() -> AutoscanReportFacts {
    AutoscanReportFacts {
        classic_version: "v9.0.0".to_string(),
        crashlog_filename: "crash.log".to_string(),
        main_error: "Unhandled exception \"EXCEPTION_ACCESS_VIOLATION\"".to_string(),
        crashgen_name: "Buffout 4".to_string(),
        crashgen_version: "Buffout 4 v1.28.6".to_string(),
        crashgen_status: Some(CrashgenVersionStatus::Valid),
        fake_bot_compatible_mode: false,
        fcx_setup: None,
    }
}

fn settings_result(
    message: &str,
    placement: AutoscanReportPlacement,
) -> CrashgenSettingsAnalysisResult {
    CrashgenSettingsAnalysisResult {
        expectation_outcomes: vec![CrashgenExpectationOutcome {
            rule_id: "test-rule".to_string(),
            kind: OutcomeKind::Notice,
            severity: RuleSeverity::Warning,
            message: message.to_string(),
            fix: None,
            placement,
            section: None,
            setting: None,
            expected: None,
            actual: None,
        }],
        disabled_setting_notices: Vec::new(),
    }
}

#[test]
fn autoscan_report_assembler_applies_canonical_order_to_typed_contributions() {
    let report_lines = AutoscanReportAssembler::new().assemble(
        &base_facts(),
        AutoscanReportContributions {
            crashgen_settings: Some(settings_result(
                "Settings placement",
                AutoscanReportPlacement::Settings,
            )),
            crash_suspects: Some(CrashSuspectAnalysisResult {
                findings: vec![CrashSuspectFinding::MainErrorRule {
                    rule_id: "suspect-rule".to_string(),
                    name: "Suspect finding".to_string(),
                    severity: 3,
                }],
            }),
            plugin_evidence: Some(PluginEvidenceAnalysisResult {
                evidence: vec![PluginEvidence {
                    plugin: "plugin.esp".to_string(),
                    occurrences: 1,
                }],
            }),
            formid_findings: Some(FormIDFindingAnalysisResult {
                findings: vec![FormIDFinding {
                    identifier: "01123456".to_string(),
                    occurrences: 1,
                    plugin: Some("plugin.esp".to_string()),
                    value_lookup_status: FormIDValueLookupStatus::Disabled,
                    value: None,
                }],
            }),
            ..AutoscanReportContributions::default()
        },
    );
    let text = report_lines.join("");

    let header = text.find("# crash.log").unwrap();
    let error = text.find("### Error Information").unwrap();
    let suspect = text
        .find("### Checking for Known Crash Messages, Errors and Suspects")
        .unwrap();
    let settings = text
        .find("### Checking for Settings-related Issues")
        .unwrap();
    let plugin = text.find("### Checking for Plugin-related Errors").unwrap();
    let formid = text.find("### Checking FormIDs").unwrap();
    let footer = text.find("### End of Report").unwrap();

    assert!(header < error);
    assert!(error < suspect);
    assert!(suspect < settings);
    assert!(settings < plugin);
    assert!(plugin < formid);
    assert!(formid < footer);
}

#[test]
fn autoscan_report_assembler_renders_resolved_formids_and_omits_unresolved_identifiers() {
    let report_lines = AutoscanReportAssembler::new().assemble(
        &base_facts(),
        AutoscanReportContributions {
            formid_findings: Some(FormIDFindingAnalysisResult {
                findings: vec![
                    FormIDFinding {
                        identifier: "03999999".to_string(),
                        occurrences: 4,
                        plugin: None,
                        value_lookup_status: FormIDValueLookupStatus::NotApplicable,
                        value: None,
                    },
                    FormIDFinding {
                        identifier: "02123456".to_string(),
                        occurrences: 2,
                        plugin: Some("Missing.esp".to_string()),
                        value_lookup_status: FormIDValueLookupStatus::Missing,
                        value: None,
                    },
                    FormIDFinding {
                        identifier: "01ABCDEF".to_string(),
                        occurrences: 1,
                        plugin: Some("Found.esp".to_string()),
                        value_lookup_status: FormIDValueLookupStatus::Found,
                        value: Some("Resolved value".to_string()),
                    },
                ],
            }),
            ..AutoscanReportContributions::default()
        },
    );
    let text = report_lines.join("");

    assert!(text.contains("- Found.esp | 01ABCDEF | Resolved value | 1\n"));
    assert!(text.contains("- Missing.esp | 02123456 | 2\n"));
    assert!(!text.contains("03999999"));
    assert!(text.contains("These Form IDs were caught by Buffout 4"));
}

#[test]
fn autoscan_report_assembler_preserves_legacy_output_for_completed_empty_formid_analysis() {
    let absent = AutoscanReportAssembler::new()
        .assemble(&base_facts(), AutoscanReportContributions::default())
        .join("");
    let completed_empty = AutoscanReportAssembler::new()
        .assemble(
            &base_facts(),
            AutoscanReportContributions {
                formid_findings: Some(FormIDFindingAnalysisResult::default()),
                ..AutoscanReportContributions::default()
            },
        )
        .join("");

    assert!(!absent.contains("### Checking FormIDs"));
    assert_eq!(completed_empty, absent);
}

#[test]
fn autoscan_report_assembler_omits_formid_section_for_unresolved_only_findings() {
    let report = AutoscanReportAssembler::new()
        .assemble(
            &base_facts(),
            AutoscanReportContributions {
                formid_findings: Some(FormIDFindingAnalysisResult {
                    findings: vec![FormIDFinding {
                        identifier: "03999999".to_string(),
                        occurrences: 4,
                        plugin: None,
                        value_lookup_status: FormIDValueLookupStatus::NotApplicable,
                        value: None,
                    }],
                }),
                ..AutoscanReportContributions::default()
            },
        )
        .join("");

    assert!(!report.contains("### Checking FormIDs"));
    assert!(!report.contains("These Form IDs were caught by"));
    assert!(!report.contains("03999999"));
}

#[test]
fn autoscan_report_assembler_owns_plugin_evidence_sorting_and_legacy_prose() {
    let report_lines = AutoscanReportAssembler::new().assemble(
        &base_facts(),
        AutoscanReportContributions {
            plugin_evidence: Some(PluginEvidenceAnalysisResult {
                evidence: vec![
                    PluginEvidence {
                        plugin: "zeta.esp".to_string(),
                        occurrences: 1,
                    },
                    PluginEvidence {
                        plugin: "alpha.esp".to_string(),
                        occurrences: 3,
                    },
                ],
            }),
            ..AutoscanReportContributions::default()
        },
    );
    let text = report_lines.join("");

    assert!(text.contains(
        "The following PLUGINS were found in the CRASH STACK:\n\
- alpha.esp | 3\n\
- zeta.esp | 1\n\n\
[Last number counts how many times each Plugin Suspect shows up in the crash log.]\n\
These Plugins were caught by Buffout 4 and some of them might be responsible for this crash.\n\
You can try disabling these plugins and check if the game still crashes, though this method can be unreliable.\n\n"
    ));
}

#[test]
fn autoscan_report_assembler_distinguishes_absent_from_completed_empty_plugin_evidence() {
    let absent = AutoscanReportAssembler::new()
        .assemble(&base_facts(), AutoscanReportContributions::default())
        .join("");
    let completed_empty = AutoscanReportAssembler::new()
        .assemble(
            &base_facts(),
            AutoscanReportContributions {
                plugin_evidence: Some(PluginEvidenceAnalysisResult::default()),
                ..AutoscanReportContributions::default()
            },
        )
        .join("");

    assert!(!absent.contains("COULDN'T FIND ANY PLUGIN SUSPECTS"));
    assert!(completed_empty.contains("* COULDN'T FIND ANY PLUGIN SUSPECTS *\n\n"));
}

#[test]
fn autoscan_report_assembler_owns_named_record_sorting_counts_and_legacy_prose() {
    let report_lines = AutoscanReportAssembler::new().assemble(
        &base_facts(),
        AutoscanReportContributions {
            named_record_findings: Some(NamedRecordFindingAnalysisResult {
                findings: vec![
                    NamedRecordFinding {
                        record: "Weapon_Pistol".to_string(),
                        occurrences: 1,
                    },
                    NamedRecordFinding {
                        record: "ActorBase_Player".to_string(),
                        occurrences: 2,
                    },
                ],
            }),
            ..AutoscanReportContributions::default()
        },
    );
    let text = report_lines.join("");

    let actor = text.find("- ActorBase_Player | 2\n").unwrap();
    let weapon = text.find("- Weapon_Pistol | 1\n").unwrap();
    assert!(actor < weapon);
    assert!(text.contains(
        "[Last number counts how many times each Named Record shows up in the crash log.]\n"
    ));
    assert!(text.contains("These records were caught by Buffout 4"));
}

#[test]
fn autoscan_report_assembler_renders_error_information_placement_before_separator() {
    let report_lines = AutoscanReportAssembler::new().assemble(
        &base_facts(),
        AutoscanReportContributions {
            crashgen_settings: Some(settings_result(
                "Compatibility notice",
                AutoscanReportPlacement::ErrorInformation,
            )),
            ..AutoscanReportContributions::default()
        },
    );
    let text = report_lines.join("");

    let valid_status = text.find("valid version of Buffout 4").unwrap();
    let notice = text
        .find("**# ⚠️ NOTICE : Compatibility notice #**")
        .unwrap();
    let suspect_header = text
        .find("### Checking for Known Crash Messages, Errors and Suspects")
        .unwrap();

    assert!(valid_status < notice);
    assert!(notice < suspect_header);
    assert!(text.contains("**# ⚠️ NOTICE : Compatibility notice #**\n\n---\n\n### Checking"));
}

#[test]
fn autoscan_report_assembler_renders_settings_placement_under_settings_guidance() {
    let report_lines = AutoscanReportAssembler::new().assemble(
        &base_facts(),
        AutoscanReportContributions {
            crashgen_settings: Some(settings_result(
                "Settings placement",
                AutoscanReportPlacement::Settings,
            )),
            ..AutoscanReportContributions::default()
        },
    );
    let text = report_lines.join("");

    let settings_header = text
        .find("### Checking for Settings-related Issues")
        .unwrap();
    let settings_notice = text.find("# ⚠️ NOTICE : Settings placement #").unwrap();

    assert!(settings_header < settings_notice);
}

#[test]
fn autoscan_report_assembler_renders_disabled_setting_notices() {
    let report_lines = AutoscanReportAssembler::new().assemble(
        &base_facts(),
        AutoscanReportContributions {
            crashgen_settings: Some(CrashgenSettingsAnalysisResult {
                expectation_outcomes: Vec::new(),
                disabled_setting_notices: vec![DisabledSettingNotice {
                    setting_name: "ArchiveLimit".to_string(),
                }],
            }),
            ..AutoscanReportContributions::default()
        },
    );
    let text = report_lines.join("");

    assert!(text.contains("### Checking for Settings-related Issues"));
    assert!(text.contains("ArchiveLimit is disabled in your Buffout 4 settings"));
}

#[test]
fn autoscan_report_assembler_renders_no_suspects_footer_when_no_findings_exist() {
    let report_lines = AutoscanReportAssembler::new()
        .assemble(&base_facts(), AutoscanReportContributions::default());
    let text = report_lines.join("");

    assert!(text.contains("* **NO SUSPECTS DETECTED** *"));
}

#[test]
fn autoscan_report_assembler_renders_fcx_content_from_run_setup() {
    let mut facts = base_facts();
    facts.fcx_setup = Some(Arc::new(crate::scan_run::CrashLogScanSetupResult {
        status: "completed".to_string(),
        checks: Vec::new(),
        path_updates: Vec::new(),
        configuration_issues: Vec::new(),
        actions: Vec::new(),
        fatal_errors: Vec::new(),
        message: None,
        rendered_report: "Run-owned setup facts\n".to_string(),
    }));

    let report_lines =
        AutoscanReportAssembler::new().assemble(&facts, AutoscanReportContributions::default());
    let text = report_lines.join("");

    assert!(text.contains("FCX LOCAL FILE CHECKS ARE ENABLED"));
    assert!(text.contains("Use FCX only with crash logs from your own installation"));
    assert!(text.contains("Run-owned setup facts"));
}

#[test]
fn autoscan_report_assembler_owns_crash_suspect_presentation() {
    let report_lines = AutoscanReportAssembler::new().assemble(
        &base_facts(),
        AutoscanReportContributions {
            crash_suspects: Some(CrashSuspectAnalysisResult {
                findings: vec![
                    CrashSuspectFinding::MainErrorRule {
                        rule_id: "main-error".to_string(),
                        name: "Authored Suspect".to_string(),
                        severity: 5,
                    },
                    CrashSuspectFinding::DllInvolvement,
                ],
            }),
            ..AutoscanReportContributions::default()
        },
    );
    let text = report_lines.join("");

    assert!(text.contains(
        "- **Checking for Authored Suspect.................................. SUSPECT FOUND! > Severity : 5** \n\n-----\n"
    ));
    assert!(text.contains(
        "* NOTICE : MAIN ERROR REPORTS THAT A DLL FILE WAS INVOLVED IN THIS CRASH! * \nIf that dll file belongs to a mod, that mod is a prime suspect for the crash. \n\n-----\n"
    ));
}

#[test]
fn autoscan_report_assembler_sorts_solution_matches_by_plugin_load_order() {
    let guidance = ModGuidanceAnalysisResult {
        solutions: vec![
            ModSolutionGuidance {
                state: ModGuidanceMatchState::Matched,
                id: "later-authored-entry".to_string(),
                name: "Later Authored Entry".to_string(),
                description: "Later body".to_string(),
                matched_plugin_ids: vec!["10".to_string(), "02".to_string()],
            },
            ModSolutionGuidance {
                state: ModGuidanceMatchState::Matched,
                id: "middle-entry".to_string(),
                name: "Middle Entry".to_string(),
                description: "Middle body".to_string(),
                matched_plugin_ids: vec!["05".to_string()],
            },
        ],
        ..ModGuidanceAnalysisResult::default()
    };

    let report_lines = AutoscanReportAssembler::new().assemble(
        &base_facts(),
        AutoscanReportContributions {
            mod_guidance: Some(guidance),
            ..AutoscanReportContributions::default()
        },
    );
    let text = report_lines.join("");

    let earlier = text.find("[02], [10] Later Authored Entry").unwrap();
    let middle = text.find("[05] Middle Entry").unwrap();
    assert!(earlier < middle);
}
