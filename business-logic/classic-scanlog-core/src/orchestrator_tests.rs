use super::*;
use classic_shared_core::get_runtime;
use tempfile::tempdir;

const FIXTURE_LOG_SMALL: &str = include_str!("../benches/fixtures/crash-0DB9300.log");
const FIXTURE_LOG_LARGE: &str = include_str!("../benches/fixtures/crash-2022-06-05-12-58-02.log");

fn make_fixture_orchestrator() -> OrchestratorCore {
    let mut config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
    config.crashgen_name = "Buffout 4".to_string();
    config.crashgen_latest = "1.26.2".to_string();
    config.game_version = "1.10.163".to_string();
    config.game_version_vr = "1.2.72".to_string();
    config.xse_acronym = "F4SE".to_string();
    OrchestratorCore::new(config).expect("fixture orchestrator should build")
}

struct FixtureLog {
    _temp: tempfile::TempDir,
    path: String,
}

fn write_fixture_log(filename: &str, contents: &str) -> FixtureLog {
    let temp = tempdir().expect("tempdir should succeed");
    let log_path = temp.path().join(filename);
    std::fs::write(&log_path, contents).expect("fixture log write should succeed");
    FixtureLog {
        _temp: temp,
        path: log_path.to_string_lossy().to_string(),
    }
}

fn make_yaml_data(classic_version: &str) -> classic_config_core::YamlDataCore {
    classic_config_core::YamlDataCore {
        classic_game_hints: Vec::new(),
        classic_records_list: Vec::new(),
        classic_version: classic_version.to_string(),
        classic_version_date: String::new(),
        crashgen_name: "Buffout 4".to_string(),
        crashgen_latest_og: String::new(),
        crashgen_ignore: Vec::new(),
        warn_noplugins: String::new(),
        warn_outdated: String::new(),
        xse_acronym: "F4SE".to_string(),
        game_ignore_plugins: Vec::new(),
        game_ignore_records: Vec::new(),
        ignore_list: Vec::new(),
        suspect_error_rules: Vec::new(),
        suspect_stack_rules: Vec::new(),
        game_mods_conf: Vec::new(),
        game_mods_core: Vec::new(),
        game_mods_freq: Vec::new(),
        game_mods_solu: Vec::new(),
        autoscan_text: String::new(),
        game_version: String::new(),
        game_root_name: "Fallout4".to_string(),
        crashgen_registry: std::collections::HashMap::new(),
    }
}

fn build_orchestrator_with_structured_mods_solu(mods_solu_yaml: &str) -> OrchestratorCore {
    let main_yaml = concat!(
        "CLASSIC_Info:\n",
        "  version: \"7.31.0\"\n",
        "  version_date: \"2024-01-15\"\n",
        "CLASSIC_Interface:\n",
        "  autoscan_text_Fallout4: \"Autoscan Fallout 4\"\n",
    );
    let game_yaml = format!(
        concat!(
            "Game_Info:\n",
            "  XSE_Acronym: \"F4SE\"\n",
            "  GameVersion: \"1.10.163\"\n",
            "  CRASHGEN_LatestVer: \"1.28.6\"\n",
            "  CRASHGEN_LogName: \"Buffout 4\"\n",
            "  Main_Root_Name: \"Fallout4\"\n",
            "{}"
        ),
        mods_solu_yaml
    );
    let ignore_yaml = "CLASSIC_Ignore_Fallout4: []\n";
    let yaml = classic_config_core::YamlDataCore::from_yaml_content(
        main_yaml,
        &game_yaml,
        ignore_yaml,
        "Fallout4".to_string(),
        "auto".to_string(),
    )
    .expect("structured Mods_SOLU yaml should load");
    let config =
        build_analysis_config_from_yaml(&yaml, "Fallout4", "auto", false, false, false, Vec::new());

    OrchestratorCore::new(config).expect("orchestrator should build")
}

fn structured_mods_solu_log(plugins: &[(&str, &str)]) -> String {
    let mut lines = vec![
        "Fallout 4 v1.11.191".to_string(),
        "Buffout 4 v1.28.6".to_string(),
        "Unhandled exception \"EXCEPTION_ACCESS_VIOLATION\" at 0x0 Fallout4.exe+0000000"
            .to_string(),
        String::new(),
        "PROBABLE CALL STACK:".to_string(),
        "stack frame".to_string(),
        "MODULES:".to_string(),
        "kernel32.dll v10.0.0".to_string(),
        "F4SE PLUGINS:".to_string(),
        "buffout4.dll v1.28.6".to_string(),
        "PLUGINS:".to_string(),
    ];

    lines.extend(
        plugins
            .iter()
            .map(|(plugin_id, plugin_name)| format!("[{plugin_id}] {plugin_name}")),
    );

    lines.extend([
        "REGISTERS:".to_string(),
        "RAX 0x0".to_string(),
        "STACK:".to_string(),
        "stack dump line".to_string(),
    ]);

    lines.join("\n")
}

#[test]
fn build_analysis_config_does_not_double_prefix_classic_version() {
    let yaml = make_yaml_data("v9.0.0");

    let config =
        build_analysis_config_from_yaml(&yaml, "Fallout4", "auto", false, false, false, Vec::new());

    assert_eq!(config.classic_version, "v9.0.0");
}

#[test]
fn create_report_generator_from_default_config_avoids_double_classic_prefix() {
    let config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
    let orchestrator = OrchestratorCore::new(config).unwrap();

    let report_text = orchestrator
        .create_report_generator()
        .generate_header("crash.log")
        .to_list()
        .join("");

    assert!(
        !report_text.contains("CLASSIC CLASSIC"),
        "default-config report header should not double-prefix CLASSIC"
    );
}

#[test]
fn build_analysis_config_uses_registry_metadata_when_yaml_game_info_is_missing() {
    let mut yaml = make_yaml_data("v9.0.0");
    yaml.crashgen_name.clear();
    yaml.crashgen_latest_og.clear();
    yaml.xse_acronym.clear();
    yaml.game_version.clear();
    yaml.crashgen_registry.insert(
        "Buffout 4".to_string(),
        classic_config_core::CrashgenEntryRaw {
            display_section: "[Compatibility]".to_string(),
            ignore_keys: vec![],
            checks: vec!["achievements".to_string()],
            settings_rules_version: None,
            settings_rules: None,
        },
    );
    yaml.crashgen_registry.insert(
        "default".to_string(),
        classic_config_core::CrashgenEntryRaw {
            display_section: String::new(),
            ignore_keys: vec![],
            checks: vec![],
            settings_rules_version: None,
            settings_rules: None,
        },
    );

    let config =
        build_analysis_config_from_yaml(&yaml, "Fallout4", "auto", false, false, false, Vec::new());

    assert_eq!(config.crashgen_name, "Buffout 4");
    assert!(!config.crashgen_latest.is_empty());
    assert_eq!(config.xse_acronym, "F4SE");
    // Auto mode resolves to the configured registry default for Fallout4.
    assert_eq!(config.game_version, "1.11.221");
    assert_eq!(config.game_version_vr, "1.2.72");
    assert!(
        !config
            .crashgen_registry
            .lookup(&config.crashgen_name)
            .checks
            .is_empty()
    );
}

#[test]
fn build_analysis_config_resolves_registry_metadata_for_spaced_game_and_root_name() {
    let mut yaml = make_yaml_data("v9.0.0");
    yaml.game_root_name = "Fallout 4".to_string();
    yaml.crashgen_name.clear();
    yaml.crashgen_latest_og.clear();
    yaml.xse_acronym.clear();
    yaml.game_version.clear();

    let config = build_analysis_config_from_yaml(
        &yaml,
        "Fallout 4",
        "auto",
        false,
        false,
        false,
        Vec::new(),
    );

    assert_eq!(config.crashgen_name, "Buffout 4");
    assert_eq!(config.game_version, "1.11.221");
    assert_eq!(config.game_version_vr, "1.2.72");
}

#[test]
fn build_analysis_config_resolves_identical_metadata_for_spaced_and_compact_names() {
    let mut compact_yaml = make_yaml_data("v9.0.0");
    compact_yaml.crashgen_name.clear();
    compact_yaml.crashgen_latest_og.clear();
    compact_yaml.xse_acronym.clear();
    compact_yaml.game_version.clear();

    let mut spaced_yaml = compact_yaml.clone();
    spaced_yaml.game_root_name = "Fallout 4".to_string();

    let compact_config = build_analysis_config_from_yaml(
        &compact_yaml,
        "Fallout4",
        "auto",
        false,
        false,
        false,
        Vec::new(),
    );
    let spaced_config = build_analysis_config_from_yaml(
        &spaced_yaml,
        "Fallout 4",
        "auto",
        false,
        false,
        false,
        Vec::new(),
    );

    assert_eq!(spaced_config.crashgen_name, compact_config.crashgen_name);
    assert_eq!(
        spaced_config.crashgen_latest,
        compact_config.crashgen_latest
    );
    assert_eq!(spaced_config.xse_acronym, compact_config.xse_acronym);
    assert_eq!(spaced_config.game_version, compact_config.game_version);
    assert_eq!(
        spaced_config.game_version_vr,
        compact_config.game_version_vr
    );
}

#[test]
fn orchestrator_plugin_limit_matches_vr_version_from_built_config() {
    let mut yaml = make_yaml_data("v9.0.0");
    yaml.game_ignore_plugins.push("Fallout4.esm".to_string());

    let config =
        build_analysis_config_from_yaml(&yaml, "Fallout4", "auto", false, false, false, Vec::new());
    let orchestrator = OrchestratorCore::new(config).unwrap();
    let analyzer = orchestrator.plugin_analyzer.as_ref().unwrap();

    let segment = vec!["[FF] PluginLimit.esp".to_string()];
    let (triggered, disabled) = analyzer
        .check_plugin_limit(&segment, "1.2.72", "1.36.0")
        .unwrap();

    assert!(triggered);
    assert!(!disabled);
}

#[test]
fn check_crashgen_version_for_detected_game_rejects_addictol_below_ae_floor() {
    let config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
    let orchestrator = OrchestratorCore::new(config).unwrap();

    let (_parsed, status) = orchestrator.check_crashgen_version_for_detected_game(
        "Addictol v1.0.0 Feb 16 2026 08:02:06",
        "Fallout 4 v1.11.191",
    );

    assert_eq!(status, crate::version::CrashgenVersionStatus::Outdated);
}

#[test]
fn check_crashgen_version_for_detected_game_rejects_buffout_below_og_floor() {
    let config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
    let orchestrator = OrchestratorCore::new(config).unwrap();

    let (_parsed, status) = orchestrator
        .check_crashgen_version_for_detected_game("Buffout 4 v1.3.1", "Fallout 4 v1.10.163");

    assert_eq!(status, crate::version::CrashgenVersionStatus::Outdated);
}

#[test]
fn process_log_accepts_addictol_versions_newer_than_registry_floor() {
    let mut config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
    config.crashgen_name = "Buffout 4".to_string();
    let orchestrator = OrchestratorCore::new(config).unwrap();

    let log_contents = [
        "Fallout 4 v1.11.191",
        "Addictol v1.3.1 Feb 16 2026 08:02:06",
        "Unhandled exception \"EXCEPTION_ACCESS_VIOLATION\" at 0x0 Fallout4.exe+0000000",
        "",
        "SYSTEM SPECS:",
        "GPU #1: NVIDIA GeForce RTX 4090",
        "PROBABLE CALL STACK:",
        "stack frame",
        "MODULES:",
        "kernel32.dll v10.0.0",
        "F4SE PLUGINS:",
        "addictol.dll v1.3.1",
        "PLUGINS:",
        "[00] Fallout4.esm",
        "REGISTERS:",
        "RAX 0x0",
        "STACK:",
        "stack dump line",
    ]
    .join("\n");
    let fixture = write_fixture_log("addictol-newer-than-floor.log", &log_contents);

    let result = get_runtime()
        .block_on(orchestrator.process_log(fixture.path.clone()))
        .expect("addictol fixture should process");
    let report_text = result.report_lines.join("");

    assert!(result.success);
    assert!(report_text.contains("✅ *You have a valid version of Addictol!*"));
    assert!(!report_text.contains("OUTDATED"));
}

#[test]
fn crashgen_version_strings_for_name_filters_mixed_generator_entries() {
    let version_info = classic_version_registry_core::VersionInfo {
        id: "FO4_TEST".to_string(),
        game: "Fallout4".to_string(),
        is_vr: false,
        version: classic_version_registry_core::GameVersion::new(1, 10, 984, 0),
        display_name: "Test".to_string(),
        short_name: "TEST".to_string(),
        description: String::new(),
        docs_name: "Fallout4".to_string(),
        steam_id: 377160,
        address_library: None,
        xse: None,
        compatible_range: None,
        priority: 100,
        deprecated: false,
        exe_hash: None,
        crashgen_versions: vec![
            classic_version_registry_core::CrashgenConfig::new(
                "1.38.1",
                "Buffout 4",
                "BO4",
                "buffout4.dll",
                "Buffout floor",
                "https://example.invalid/buffout",
            ),
            classic_version_registry_core::CrashgenConfig::new(
                "1.3.0",
                "Addictol",
                "Addictol",
                "addictol.dll",
                "Addictol floor",
                "https://example.invalid/addictol",
            ),
        ],
    };

    let buffout_versions =
        OrchestratorCore::crashgen_version_strings_for_name(&version_info, "Buffout 4");
    let addictol_versions =
        OrchestratorCore::crashgen_version_strings_for_name(&version_info, "Addictol");

    assert_eq!(buffout_versions, vec!["1.38.1"]);
    assert_eq!(addictol_versions, vec!["1.3.0"]);
}

#[test]
fn process_log_does_not_validate_old_buffout_against_addictol_floor() {
    let mut config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
    config.crashgen_name = "Buffout 4".to_string();
    let orchestrator = OrchestratorCore::new(config).unwrap();

    let log_contents = [
        "Fallout 4 v1.10.984",
        "Buffout 4 v1.30.0",
        "Unhandled exception \"EXCEPTION_ACCESS_VIOLATION\" at 0x0 Fallout4.exe+0000000",
        "",
        "[Compatibility]",
        "Achievements: true",
        "SYSTEM SPECS:",
        "GPU #1: NVIDIA GeForce RTX 4090",
        "PROBABLE CALL STACK:",
        "stack frame",
        "MODULES:",
        "kernel32.dll v10.0.0",
        "F4SE PLUGINS:",
        "buffout4.dll v1.30.0",
        "PLUGINS:",
        "[00] Fallout4.esm",
        "REGISTERS:",
        "RAX 0x0",
        "STACK:",
        "stack dump line",
    ]
    .join("\n");
    let fixture = write_fixture_log("buffout-older-than-own-floor.log", &log_contents);

    let result = get_runtime()
        .block_on(orchestrator.process_log(fixture.path.clone()))
        .expect("buffout fixture should process");
    let report_text = result.report_lines.join("");

    assert!(result.success);
    assert!(report_text.contains("***❌ WARNING: YOUR Buffout 4 IS OUTDATED!"));
}

#[test]
fn resolve_effective_crashgen_name_prefers_addictol_header() {
    let mut config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
    config.crashgen_name = "Buffout 4".to_string();
    let orchestrator = OrchestratorCore::new(config).unwrap();

    let xse_modules = HashSet::new();
    let resolved = orchestrator
        .resolve_effective_crashgen_name("Addictol v1.0.0 Feb 16 2026 08:02:06", &xse_modules);

    assert_eq!(resolved, "Addictol");
}

#[test]
fn resolve_effective_crashgen_name_uses_module_fallback_when_header_missing() {
    let mut config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
    config.crashgen_name = "Buffout 4".to_string();
    let orchestrator = OrchestratorCore::new(config).unwrap();

    let mut xse_modules = HashSet::new();
    xse_modules.insert("addictol.dll".to_string());
    let resolved = orchestrator.resolve_effective_crashgen_name("", &xse_modules);

    assert_eq!(resolved, "Addictol");
}

#[test]
fn extract_module_names_accepts_chained_borrowed_iterators() {
    let mods = ["kernel32.dll v10.0.0", "user32.dll v10.0.0"];
    let xse = ["addictol.dll v1.0.0"];

    let extracted = extract_module_names(mods.iter().chain(xse.iter()));

    assert_eq!(extracted.len(), 3);
    assert!(extracted.contains("kernel32.dll"));
    assert!(extracted.contains("user32.dll"));
    assert!(extracted.contains("addictol.dll"));
}

#[test]
fn scan_analysis_context_builds_from_arc_sections() {
    let parser = LogParser::new(None).unwrap();
    let processed_lines = vec![
        "[Compatibility]".to_string(),
        "Achievements: true".to_string(),
        "SYSTEM SPECS:".to_string(),
        "GPU #1: NVIDIA GeForce RTX 4090".to_string(),
        "PROBABLE CALL STACK:".to_string(),
        "stack frame".to_string(),
        "MODULES:".to_string(),
        "kernel32.dll v10.0.0".to_string(),
        "F4SE PLUGINS:".to_string(),
        "addictol.dll v1.0.0".to_string(),
        "PLUGINS:".to_string(),
        "[00] Fallout4.esm".to_string(),
        "REGISTERS:".to_string(),
        "RAX 0x0".to_string(),
        "STACK:".to_string(),
        "stack dump line".to_string(),
    ];
    let arc_lines: Vec<Arc<str>> = processed_lines
        .iter()
        .map(|line| Arc::from(line.as_str()))
        .collect();
    let segments = parser.parse_all_sections_arc(&arc_lines);

    let context = ScanAnalysisContext::from_arc_sections(processed_lines.clone(), &segments);

    assert_eq!(context.processed_lines, processed_lines);
    assert_eq!(
        context.combined_crash_lines,
        vec![
            "stack frame".to_string(),
            "RAX 0x0".to_string(),
            "stack dump line".to_string(),
        ]
    );
    assert_eq!(context.plugin_lines, vec!["[00] Fallout4.esm".to_string()]);
    assert_eq!(
        context.system_segment_lines,
        vec!["GPU #1: NVIDIA GeForce RTX 4090".to_string()]
    );
    assert_eq!(
        context.crashgen_settings.get("Achievements"),
        Some(&"true".to_string())
    );
    assert!(context.xse_modules_for_settings.contains("kernel32.dll"));
    assert!(context.xse_modules_for_settings.contains("addictol.dll"));
}

#[test]
fn resolve_effective_crashgen_name_falls_back_for_ambiguous_modules() {
    let mut config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
    config.crashgen_name = "Buffout 4".to_string();
    let orchestrator = OrchestratorCore::new(config).unwrap();

    let mut xse_modules = HashSet::new();
    xse_modules.insert("addictol.dll".to_string());
    xse_modules.insert("buffout4.dll".to_string());
    let resolved = orchestrator.resolve_effective_crashgen_name("", &xse_modules);

    assert_eq!(resolved, "Buffout 4");
}

#[test]
fn fake_bot_mode_treats_buffout4ae_dll_as_real_buffout() {
    let mut xse_modules = HashSet::new();
    xse_modules.insert("buffout4ae.dll".to_string());

    assert!(
        !OrchestratorCore::is_fake_bot_compatible_mode("Buffout 4 v1.28.6", &xse_modules),
        "buffout4ae.dll should count as a real Buffout module"
    );
}

#[test]
fn create_report_generator_with_crashgen_name_updates_error_section_label() {
    let config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
    let orchestrator = OrchestratorCore::new(config).unwrap();

    let report_gen = orchestrator.create_report_generator_with_crashgen_name("Addictol");
    let fragment = report_gen.generate_error_section_with_status(
        "Unhandled exception",
        "Addictol v1.0.0",
        Some(crate::version::CrashgenVersionStatus::Valid),
    );
    let text = fragment.to_list().join("");

    assert!(text.contains("Detected Addictol Version"));
    assert!(text.contains("valid version of Addictol"));
    assert!(!text.contains("Detected Buffout 4 Version"));
}

#[test]
fn settings_validator_routes_to_addictol_rules_and_avoids_scaffold() {
    use classic_config_core::{
        CrashgenSettingsRules, Predicate, PreflightAction, PreflightActionKind, PreflightRule,
        RuleReportBucket, RuleSeverity,
    };

    let mut raw_registry: HashMap<String, classic_config_core::CrashgenEntryRaw> = HashMap::new();
    raw_registry.insert(
        "Buffout 4".to_string(),
        classic_config_core::CrashgenEntryRaw {
            display_section: "[Compatibility]".to_string(),
            ignore_keys: vec![],
            checks: vec![],
            settings_rules_version: None,
            settings_rules: None,
        },
    );
    raw_registry.insert(
        "Addictol".to_string(),
        classic_config_core::CrashgenEntryRaw {
            display_section: "[Patches]".to_string(),
            ignore_keys: vec![],
            checks: vec![],
            settings_rules_version: Some(1),
            settings_rules: Some(CrashgenSettingsRules {
                version: 1,
                preflight: vec![PreflightRule {
                    id: "addictol_active".to_string(),
                    when: Predicate::Always,
                    action: PreflightAction {
                        kind: PreflightActionKind::Notice,
                        bucket: RuleReportBucket::Settings,
                        severity: RuleSeverity::Info,
                        message: "Addictol rules active".to_string(),
                        fix: None,
                    },
                }],
                checks: vec![],
            }),
        },
    );
    raw_registry.insert(
        "default".to_string(),
        classic_config_core::CrashgenEntryRaw {
            display_section: String::new(),
            ignore_keys: vec![],
            checks: vec![],
            settings_rules_version: None,
            settings_rules: None,
        },
    );

    let mut config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
    config.crashgen_name = "Buffout 4".to_string();
    config.crashgen_registry = build_crashgen_registry(&raw_registry);
    let orchestrator = OrchestratorCore::new(config).unwrap();

    let mut xse_modules = HashSet::new();
    xse_modules.insert("addictol.dll".to_string());
    let effective_name = orchestrator
        .resolve_effective_crashgen_name("Addictol v1.0.0 Feb 16 2026 08:02:06", &xse_modules);
    assert_eq!(effective_name, "Addictol");

    let validator =
        OrchestratorCore::settings_validator_for_crashgen(&orchestrator.config, &effective_name);
    let fragments = validator
        .scan_all_settings(
            &HashMap::new(),
            &xse_modules,
            None,
            classic_config_core::ConfigLayout::Unknown,
        )
        .unwrap();
    let all_lines: Vec<String> = fragments
        .iter()
        .flat_map(crate::report::ReportFragment::to_list)
        .collect();

    assert!(
        all_lines
            .iter()
            .any(|line| line.contains("Addictol rules active"))
    );
    assert!(
        !all_lines
            .iter()
            .any(|line| line.contains("scaffold (rules pending)"))
    );
}

#[test]
fn process_log_promotes_bucketed_compatibility_notice_into_error_information() {
    use classic_config_core::{
        CrashgenSettingsRules, Predicate, PreflightAction, PreflightActionKind, PreflightRule,
        RuleReportBucket, RuleSeverity,
    };

    let mut raw_registry: HashMap<String, classic_config_core::CrashgenEntryRaw> = HashMap::new();
    raw_registry.insert(
        "Buffout 4".to_string(),
        classic_config_core::CrashgenEntryRaw {
            display_section: "[Compatibility]".to_string(),
            ignore_keys: vec![],
            checks: vec![],
            settings_rules_version: None,
            settings_rules: None,
        },
    );
    raw_registry.insert(
        "Addictol".to_string(),
        classic_config_core::CrashgenEntryRaw {
            display_section: "[Patches]".to_string(),
            ignore_keys: vec![],
            checks: vec![],
            settings_rules_version: Some(1),
            settings_rules: Some(CrashgenSettingsRules {
                version: 1,
                preflight: vec![PreflightRule {
                    id: "buffout_addictol_incompatible".to_string(),
                    when: Predicate::All(vec![
                        Predicate::PluginAny(vec!["addictol.dll".to_string()]),
                        Predicate::PluginAny(vec!["buffout4.dll".to_string()]),
                    ]),
                    action: PreflightAction {
                        kind: PreflightActionKind::NoticeAndSkipRemaining,
                        bucket: RuleReportBucket::ErrorInformation,
                        severity: RuleSeverity::Warning,
                        message: "{crashgen_name} and Buffout 4 are incompatible, remove one to avoid crashes.".to_string(),
                        fix: None,
                    },
                }],
                checks: vec![],
            }),
        },
    );
    raw_registry.insert(
        "default".to_string(),
        classic_config_core::CrashgenEntryRaw {
            display_section: String::new(),
            ignore_keys: vec![],
            checks: vec![],
            settings_rules_version: None,
            settings_rules: None,
        },
    );

    let mut config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
    config.crashgen_name = "Buffout 4".to_string();
    config.crashgen_registry = build_crashgen_registry(&raw_registry);
    let orchestrator = OrchestratorCore::new(config).unwrap();

    let log_contents = [
        "Fallout 4 v1.11.191",
        "Addictol v1.3.1 Feb 16 2026 08:02:06",
        "Unhandled exception \"EXCEPTION_ACCESS_VIOLATION\" at 0x0 Fallout4.exe+0000000",
        "",
        "[Patches]",
        "bThreads: true",
        "SYSTEM SPECS:",
        "GPU #1: NVIDIA GeForce RTX 4090",
        "PROBABLE CALL STACK:",
        "stack frame",
        "MODULES:",
        "kernel32.dll v10.0.0",
        "F4SE PLUGINS:",
        "addictol.dll v1.3.1",
        "buffout4.dll v1.28.6",
        "PLUGINS:",
        "[00] Fallout4.esm",
        "REGISTERS:",
        "RAX 0x0",
        "STACK:",
        "stack dump line",
    ]
    .join("\n");
    let fixture = write_fixture_log("bucketed-addictol.log", &log_contents);

    let result = get_runtime()
        .block_on(orchestrator.process_log(fixture.path.clone()))
        .expect("bucketed fixture should process");
    let report_text = result.report_lines.join("");

    let status_line = "✅ *You have a valid version of Addictol!*";
    let compatibility_notice =
        "**# ⚠️ NOTICE : Addictol and Buffout 4 are incompatible, remove one to avoid crashes. #**";
    let suspect_header = "### Checking for Known Crash Messages, Errors and Suspects";

    assert!(result.success);
    assert!(report_text.contains("### Error Information"));
    assert!(report_text.contains(status_line));
    assert!(report_text.contains(compatibility_notice));
    assert!(!report_text.contains("### Checking for Settings-related Issues"));

    let status_index = report_text.find(status_line).unwrap();
    let notice_index = report_text.find(compatibility_notice).unwrap();
    let suspect_index = report_text.find(suspect_header).unwrap();
    assert!(status_index < notice_index);
    assert!(notice_index < suspect_index);
}

#[test]
fn process_log_skips_fake_bot_compatible_buffout_version_and_settings_checks() {
    let mut config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
    config.crashgen_name = "Buffout 4".to_string();
    let orchestrator = OrchestratorCore::new(config).unwrap();

    let log_contents = [
        "Fallout 4 v1.11.191",
        "Buffout 4 v1.1.0",
        "Unhandled exception \"EXCEPTION_ACCESS_VIOLATION\" at 0x0 Fallout4.exe+0000000",
        "",
        "[Compatibility]",
        "Achievements: true",
        "MemoryManager: true",
        "ArchiveLimit: false",
        "SYSTEM SPECS:",
        "GPU #1: NVIDIA GeForce RTX 4090",
        "PROBABLE CALL STACK:",
        "stack frame",
        "MODULES:",
        "kernel32.dll v10.0.0",
        "F4SE PLUGINS:",
        "fake-buffout.dll v1.0.0",
        "PLUGINS:",
        "[00] Fallout4.esm",
        "REGISTERS:",
        "RAX 0x0",
        "STACK:",
        "stack dump line",
    ]
    .join("\n");
    let fixture = write_fixture_log("fake-bot-compatible.log", &log_contents);

    let result = get_runtime()
        .block_on(orchestrator.process_log(fixture.path.clone()))
        .expect("fake bot-compatible fixture should process");
    let report_text = result.report_lines.join("");

    assert!(result.success);
    assert!(report_text.contains("Bot Compatible Mode"));
    assert!(
        report_text.contains("Version and Settings checks are disabled"),
        "report should explain why checks were skipped"
    );
    assert!(
        !report_text.contains("OUTDATED"),
        "fake bot-compatible logs should not emit outdated-version warnings"
    );
    assert!(
        !report_text.contains("### Checking for Settings-related Issues"),
        "fake bot-compatible logs should skip settings validation"
    );
}

#[test]
fn process_log_skips_checks_when_buffout_header_lacks_buffout_module() {
    let mut config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
    config.crashgen_name = "Buffout 4".to_string();
    let orchestrator = OrchestratorCore::new(config).unwrap();

    let log_contents = [
        "Fallout 4 v1.11.191",
        "Buffout 4 v1.28.6",
        "Unhandled exception \"EXCEPTION_ACCESS_VIOLATION\" at 0x0 Fallout4.exe+0000000",
        "",
        "[Compatibility]",
        "Achievements: true",
        "MemoryManager: true",
        "SYSTEM SPECS:",
        "GPU #1: NVIDIA GeForce RTX 4090",
        "PROBABLE CALL STACK:",
        "stack frame",
        "MODULES:",
        "kernel32.dll v10.0.0",
        "F4SE PLUGINS:",
        "addictol.dll v1.1.0",
        "PLUGINS:",
        "[00] Fallout4.esm",
        "REGISTERS:",
        "RAX 0x0",
        "STACK:",
        "stack dump line",
    ]
    .join("\n");
    let fixture = write_fixture_log(
        "fake-bot-compatible-missing-buffout-module.log",
        &log_contents,
    );

    let result = get_runtime()
        .block_on(orchestrator.process_log(fixture.path.clone()))
        .expect("missing buffout module fixture should process");
    let report_text = result.report_lines.join("");

    assert!(result.success);
    assert!(
        report_text.contains("Bot Compatible Mode"),
        "logs claiming Buffout 4 without buffout4.dll should be treated as bot-compatible"
    );
    assert!(
        !report_text.contains("### Checking for Settings-related Issues"),
        "missing buffout4.dll should suppress settings validation for fake Buffout logs"
    );
}

#[test]
fn derive_config_layout_returns_og_for_valid_non_vr_version() {
    let config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
    let orchestrator = OrchestratorCore::new(config).unwrap();

    let layout = orchestrator.derive_scanlog_config_layout("Fallout 4 v1.10.163");
    assert_eq!(layout, classic_config_core::ConfigLayout::Og);
}

#[test]
fn derive_config_layout_returns_og_for_valid_vr_version() {
    let config = AnalysisConfig::new("Fallout4".to_string(), "VR".to_string());
    let orchestrator = OrchestratorCore::new(config).unwrap();

    let layout = orchestrator.derive_scanlog_config_layout("Fallout 4 VR v1.2.72");
    assert_eq!(layout, classic_config_core::ConfigLayout::Og);
}

#[test]
fn derive_config_layout_returns_unknown_for_invalid_header_version() {
    let config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
    let orchestrator = OrchestratorCore::new(config).unwrap();

    let layout = orchestrator.derive_scanlog_config_layout("not a valid version line");
    assert_eq!(layout, classic_config_core::ConfigLayout::Unknown);
}

#[test]
fn detect_incomplete_log_slice_matches_named_segment_semantics() {
    let config = AnalysisConfig::new("Fallout4".to_string(), "auto".to_string());
    let orchestrator = OrchestratorCore::new(config).unwrap();

    // One plugin line should be considered complete by both APIs.
    let one_plugin = vec!["[00] Fallout4.esm".to_string()];
    assert!(!orchestrator.detect_incomplete_log_slice(&one_plugin));
}

#[test]
fn process_log_with_progress_reports_monotonic_phases_for_fixture() {
    let orchestrator = make_fixture_orchestrator();
    let fixture = write_fixture_log("progress-fixture.log", FIXTURE_LOG_SMALL);
    let mut phases = Vec::new();

    let result = get_runtime().block_on(orchestrator.process_log_with_progress(
        fixture.path.clone(),
        |phase| {
            phases.push(phase);
        },
    ));

    let result = result.expect("fixture processing should succeed");
    assert!(result.success);
    assert_eq!(
        phases,
        vec![
            ScanProgressPhase::Setup,
            ScanProgressPhase::Parse,
            ScanProgressPhase::Analyze,
            ScanProgressPhase::Finalize,
        ]
    );
}

#[test]
fn process_log_missing_fixture_returns_error_after_setup_phase() {
    let orchestrator = make_fixture_orchestrator();
    let mut phases = Vec::new();

    let result = get_runtime().block_on(
        orchestrator.process_log_with_progress("missing-fixture.log".to_string(), |phase| {
            phases.push(phase)
        }),
    );

    assert!(result.is_err());
    assert_eq!(phases, vec![ScanProgressPhase::Setup]);
}

#[test]
fn process_log_large_fixture_preserves_basic_report_shape() {
    let orchestrator = make_fixture_orchestrator();
    let fixture = write_fixture_log("heavy-fixture.log", FIXTURE_LOG_LARGE);

    let result = get_runtime()
        .block_on(orchestrator.process_log(fixture.path.clone()))
        .expect("large fixture should process");
    let report_text = result.report_lines.join("");

    assert!(result.success);
    assert!(report_text.contains("Generated by CLASSIC"));
    assert!(report_text.contains("Checking for Known Crash Messages, Errors and Suspects"));
    assert!(report_text.contains("### End of Report"));
}

#[test]
fn process_log_ignores_legacy_mods_opc2_yaml_entries() {
    let main_yaml = concat!(
        "CLASSIC_Info:\n",
        "  version: \"7.31.0\"\n",
        "  version_date: \"2024-01-15\"\n",
        "CLASSIC_Interface:\n",
        "  autoscan_text_Fallout4: \"Autoscan Fallout 4\"\n",
    );
    let game_yaml = concat!(
        "Game_Info:\n",
        "  XSE_Acronym: \"F4SE\"\n",
        "  GameVersion: \"1.10.163\"\n",
        "  CRASHGEN_LatestVer: \"1.28.6\"\n",
        "  CRASHGEN_LogName: \"Buffout 4\"\n",
        "  Main_Root_Name: \"Fallout4\"\n",
        "Mods_OPC2:\n",
        "  OpcMod: \"OPC2 mod\"\n",
    );
    let ignore_yaml = "CLASSIC_Ignore_Fallout4: []\n";
    let yaml = classic_config_core::YamlDataCore::from_yaml_content(
        main_yaml,
        game_yaml,
        ignore_yaml,
        "Fallout4".to_string(),
        "auto".to_string(),
    )
    .expect("yaml fixture should load");
    let config =
        build_analysis_config_from_yaml(&yaml, "Fallout4", "auto", false, false, false, Vec::new());
    let orchestrator = OrchestratorCore::new(config).expect("orchestrator should build");

    let log_contents = [
        "Fallout 4 v1.11.191",
        "Buffout 4 v1.28.6",
        "Unhandled exception \"EXCEPTION_ACCESS_VIOLATION\" at 0x0 Fallout4.exe+0000000",
        "",
        "PROBABLE CALL STACK:",
        "stack frame",
        "MODULES:",
        "kernel32.dll v10.0.0",
        "F4SE PLUGINS:",
        "buffout4.dll v1.28.6",
        "PLUGINS:",
        "[00] Fallout4.esm",
        "[01] OpcMod.esp",
        "REGISTERS:",
        "RAX 0x0",
        "STACK:",
        "stack dump line",
    ]
    .join("\n");
    let fixture = write_fixture_log("legacy-opc2.log", &log_contents);

    let result = get_runtime()
        .block_on(orchestrator.process_log(fixture.path.clone()))
        .expect("fixture should process");
    let report_text = result.report_lines.join("");

    assert!(result.success);
    assert!(
        !report_text.contains(
            "### Checking For Mods That Are Outdated, Redundant, or Have Community Patches"
        )
    );
}

#[test]
fn process_log_renders_structured_mods_solu_any_matches() {
    let orchestrator = build_orchestrator_with_structured_mods_solu(concat!(
        "Mods_SOLU:\n",
        "  - id: high-resolution-dlc\n",
        "    criteria:\n",
        "      any:\n",
        "        - DLCUltraHighResolution\n",
        "        - HighResPack\n",
        "    name: High Resolution DLC\n",
        "    description: |\n",
        "      Disable the official texture pack.\n",
        "      It causes crashes and stutter.\n"
    ));
    let log_contents = structured_mods_solu_log(&[("01", "DLCUltraHighResolution.esp")]);
    let processed_lines = orchestrator
        .reformat_crash_data_inline(&log_contents.lines().map(str::to_string).collect::<Vec<_>>());
    let context = ScanAnalysisContext::from_processed_lines(&orchestrator.parser, processed_lines);
    assert!(
        !context.plugin_lines.is_empty(),
        "plugin segment should not be empty"
    );

    let analyzer = orchestrator
        .plugin_analyzer
        .as_ref()
        .expect("orchestrator should have a plugin analyzer");
    let (plugins, _limit_triggered, _limit_disabled) = analyzer
        .loadorder_scan_log(
            &context.plugin_lines,
            Some(orchestrator.config.game_version.as_str()),
            Some(orchestrator.config.crashgen_latest.as_str()),
        )
        .expect("plugin analyzer should parse the fixture plugins");
    assert_eq!(
        plugins.get("DLCUltraHighResolution.esp"),
        Some(&"01".to_string())
    );
    assert!(
        !detect_mods_solutions(&orchestrator.config.mods_solu, &plugins)
            .expect("structured matcher should succeed")
            .is_empty(),
        "structured matcher should detect the configured entry"
    );

    let fixture = write_fixture_log("mods-solu-any.log", &log_contents);

    let result = get_runtime()
        .block_on(orchestrator.process_log(fixture.path.clone()))
        .expect("fixture should process");
    let report_text = result.report_lines.join("");

    assert!(result.success);
    assert!(report_text.contains("### Checking For Mods That HAVE SOLUTIONS"));
    assert!(report_text.contains("FOUND : [01] High Resolution DLC"));
    assert!(report_text.contains("Disable the official texture pack."));
    assert!(report_text.contains("It causes crashes and stutter."));
}

#[test]
fn process_log_requires_all_structured_mods_solu_criteria() {
    let orchestrator = build_orchestrator_with_structured_mods_solu(concat!(
        "Mods_SOLU:\n",
        "  - id: bodyslide-patch\n",
        "    criteria:\n",
        "      all:\n",
        "        - LooksMenu\n",
        "        - CBBE\n",
        "    name: BodySlide Patch\n",
        "    description: |\n",
        "      Install the compatibility patch.\n"
    ));
    let fixture = write_fixture_log(
        "mods-solu-all.log",
        &structured_mods_solu_log(&[("02", "LooksMenu.esp")]),
    );

    let result = get_runtime()
        .block_on(orchestrator.process_log(fixture.path.clone()))
        .expect("fixture should process");
    let report_text = result.report_lines.join("");

    assert!(result.success);
    assert!(!report_text.contains("BodySlide Patch"));
    assert!(!report_text.contains("### Checking For Mods That HAVE SOLUTIONS"));
}

#[test]
fn process_log_suppresses_structured_mods_solu_exceptions() {
    let orchestrator = build_orchestrator_with_structured_mods_solu(concat!(
        "Mods_SOLU:\n",
        "  - id: ebf-redux\n",
        "    criteria:\n",
        "      any:\n",
        "        - EveryonesBestFriend\n",
        "    exceptions:\n",
        "      - UFO4P\n",
        "    name: Everyone's Best Friend\n",
        "    description: |\n",
        "      Install the compatibility patch.\n"
    ));
    let fixture = write_fixture_log(
        "mods-solu-exception.log",
        &structured_mods_solu_log(&[("03", "EveryonesBestFriend.esp"), ("04", "UFO4P.esp")]),
    );

    let result = get_runtime()
        .block_on(orchestrator.process_log(fixture.path.clone()))
        .expect("fixture should process");
    let report_text = result.report_lines.join("");

    assert!(result.success);
    assert!(!report_text.contains("Everyone's Best Friend"));
    assert!(!report_text.contains("### Checking For Mods That HAVE SOLUTIONS"));
}

#[test]
fn resolve_batch_concurrency_honors_manual_override() {
    assert_eq!(resolve_batch_concurrency(8, Some(3)), 3);
    assert_eq!(resolve_batch_concurrency(8, Some(0)), 1);
}

#[test]
fn resolve_batch_concurrency_handles_empty_batches() {
    assert_eq!(resolve_batch_concurrency(0, None), 1);
}
