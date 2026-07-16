use super::*;

// ============================================
// PluginAnalyzer creation tests
// ============================================

#[test]
fn test_plugin_analyzer_new() {
    let analyzer = PluginAnalyzer::new(
        vec!["Fallout4.esm".to_string()],
        vec!["IgnoredMod.esp".to_string()],
        "Buffout 4".to_string(),
        "1.10.163".to_string(),
        "1.10.163vr".to_string(),
    );
    assert!(analyzer.is_ok());
}

#[test]
fn test_plugin_analyzer_empty_lists() {
    let analyzer = PluginAnalyzer::new(
        vec![],
        vec![],
        "Buffout 4".to_string(),
        "1.10.163".to_string(),
        "1.10.163vr".to_string(),
    );
    assert!(analyzer.is_ok());
}

// ============================================
// contains_plugin tests
// ============================================

#[test]
fn test_contains_plugin_standard_format() {
    assert!(contains_plugin("[00] Fallout4.esm"));
    assert!(contains_plugin("[01] MyMod.esp"));
    assert!(contains_plugin("[FE] LightPlugin.esl"));
}

#[test]
fn test_contains_plugin_light_plugin_format() {
    assert!(contains_plugin("[FE:001] LightMod.esl"));
    assert!(contains_plugin("[FE:ABC] AnotherLight.esl"));
}

#[test]
fn test_contains_plugin_with_spaces() {
    assert!(contains_plugin("  [00] Fallout4.esm"));
    assert!(contains_plugin("\t[01] MyMod.esp"));
}

#[test]
fn test_contains_plugin_negative() {
    assert!(!contains_plugin("Just a regular log line"));
    assert!(!contains_plugin("Fallout4.esm without brackets"));
    assert!(!contains_plugin("[ZZ] InvalidHex.esp"));
}

#[test]
fn test_contains_plugin_case_insensitive() {
    assert!(contains_plugin("[fe:001] lowercaselight.ESL"));
    assert!(contains_plugin("[AB] UPPERCASE.ESM"));
}

// ============================================
// loadorder_scan_log tests
// ============================================

#[test]
fn test_loadorder_scan_log_empty() {
    let analyzer = PluginAnalyzer::new(
        vec![],
        vec![],
        "Buffout 4".to_string(),
        "1.10.163".to_string(),
        "1.10.163vr".to_string(),
    )
    .unwrap();

    let empty: Vec<String> = vec![];
    let (plugins, limit, disabled) = analyzer.loadorder_scan_log(&empty, None, None).unwrap();

    assert!(plugins.is_empty());
    assert!(!limit);
    assert!(!disabled);
}

#[test]
fn test_loadorder_scan_log_standard_plugins() {
    let analyzer = PluginAnalyzer::new(
        vec![],
        vec![],
        "Buffout 4".to_string(),
        "1.10.163".to_string(),
        "1.10.163vr".to_string(),
    )
    .unwrap();

    let segment = vec![
        "[00] Fallout4.esm".to_string(),
        "[01] DLCRobot.esm".to_string(),
        "[02] MyMod.esp".to_string(),
    ];

    let (plugins, _, _) = analyzer.loadorder_scan_log(&segment, None, None).unwrap();

    assert_eq!(plugins.len(), 3);
    assert_eq!(plugins.get("Fallout4.esm"), Some(&"00".to_string()));
    assert_eq!(plugins.get("DLCRobot.esm"), Some(&"01".to_string()));
    assert_eq!(plugins.get("MyMod.esp"), Some(&"02".to_string()));
}

#[test]
fn test_loadorder_scan_log_light_plugins() {
    let analyzer = PluginAnalyzer::new(
        vec![],
        vec![],
        "Buffout 4".to_string(),
        "1.10.163".to_string(),
        "1.10.163vr".to_string(),
    )
    .unwrap();

    let segment = vec![
        "[FE:001] LightMod1.esl".to_string(),
        "[FE:002] LightMod2.esl".to_string(),
    ];

    let (plugins, _, _) = analyzer.loadorder_scan_log(&segment, None, None).unwrap();

    assert_eq!(plugins.len(), 2);
    assert_eq!(plugins.get("LightMod1.esl"), Some(&"FE001".to_string()));
    assert_eq!(plugins.get("LightMod2.esl"), Some(&"FE002".to_string()));
}

#[test]
fn test_loadorder_scan_log_skips_duplicates() {
    let analyzer = PluginAnalyzer::new(
        vec![],
        vec![],
        "Buffout 4".to_string(),
        "1.10.163".to_string(),
        "1.10.163vr".to_string(),
    )
    .unwrap();

    let segment = vec![
        "[00] Fallout4.esm".to_string(),
        "[00] Fallout4.esm".to_string(), // Duplicate
    ];

    let (plugins, _, _) = analyzer.loadorder_scan_log(&segment, None, None).unwrap();

    assert_eq!(plugins.len(), 1);
}

#[test]
fn test_loadorder_scan_log_skips_mixed_case_duplicates() {
    let analyzer = PluginAnalyzer::new(
        vec![],
        vec![],
        "Buffout 4".to_string(),
        "1.10.163".to_string(),
        "1.10.163vr".to_string(),
    )
    .unwrap();

    let segment = vec!["[01] MyMod.esp".to_string(), "[02] mymod.esp".to_string()];

    let (plugins, _, _) = analyzer.loadorder_scan_log(&segment, None, None).unwrap();

    assert_eq!(plugins.len(), 1);
    assert_eq!(plugins.get("MyMod.esp"), Some(&"01".to_string()));
    assert!(!plugins.contains_key("mymod.esp"));
}

// ============================================
// check_plugin_limit tests
// ============================================

#[test]
fn test_check_plugin_limit_no_ff() {
    let analyzer = PluginAnalyzer::new(
        vec![],
        vec![],
        "Buffout 4".to_string(),
        "1.10.163".to_string(),
        "1.10.163vr".to_string(),
    )
    .unwrap();

    let segment = vec!["[00] Fallout4.esm".to_string()];
    let (triggered, disabled) = analyzer
        .check_plugin_limit(&segment, "1.10.163", "1.36.0")
        .unwrap();

    assert!(!triggered);
    assert!(!disabled);
}

#[test]
fn test_check_plugin_limit_original_game() {
    let analyzer = PluginAnalyzer::new(
        vec![],
        vec![],
        "Buffout 4".to_string(),
        "1.10.163".to_string(),
        "1.10.163vr".to_string(),
    )
    .unwrap();

    let segment = vec!["[FF] PluginLimit.esp".to_string()];
    let (triggered, disabled) = analyzer
        .check_plugin_limit(&segment, "1.10.163", "1.36.0")
        .unwrap();

    assert!(triggered);
    assert!(!disabled);
}

#[test]
fn test_check_plugin_limit_vr_game() {
    let analyzer = PluginAnalyzer::new(
        vec![],
        vec![],
        "Buffout 4".to_string(),
        "1.10.163".to_string(),
        "1.10.163vr".to_string(),
    )
    .unwrap();

    let segment = vec!["[FF] PluginLimit.esp".to_string()];
    let (triggered, _) = analyzer
        .check_plugin_limit(&segment, "1.10.163vr", "1.36.0")
        .unwrap();

    assert!(triggered);
}

#[test]
fn test_check_plugin_limit_ng_pre_137_disables_limit_check() {
    let analyzer = PluginAnalyzer::new(
        vec![],
        vec![],
        "Buffout 4".to_string(),
        "1.10.163".to_string(),
        "1.10.163vr".to_string(),
    )
    .unwrap();

    let segment = vec!["[FF] PluginLimit.esp".to_string()];
    let (triggered, disabled) = analyzer
        .check_plugin_limit(&segment, "1.10.984", "1.36.0")
        .unwrap();

    assert!(!triggered);
    assert!(disabled);
}

#[test]
fn test_check_plugin_limit_ae_pre_137_still_triggers_warning() {
    let analyzer = PluginAnalyzer::new(
        vec![],
        vec![],
        "Buffout 4".to_string(),
        "1.10.163".to_string(),
        "1.10.163vr".to_string(),
    )
    .unwrap();

    let segment = vec!["[FF] PluginLimit.esp".to_string()];
    let (triggered, disabled) = analyzer
        .check_plugin_limit(&segment, "1.11.191", "1.36.0")
        .unwrap();

    assert!(triggered);
    assert!(!disabled);
}

// ============================================
// filter_ignored_plugins tests
// ============================================

#[test]
fn test_filter_ignored_plugins_empty() {
    let analyzer = PluginAnalyzer::new(
        vec![],
        vec![],
        "Buffout 4".to_string(),
        "1.10.163".to_string(),
        "1.10.163vr".to_string(),
    )
    .unwrap();

    let plugins: IndexMap<String, String> = IndexMap::new();
    let result = analyzer.filter_ignored_plugins(plugins).unwrap();
    assert!(result.is_empty());
}

#[test]
fn test_filter_ignored_plugins_no_ignore_list() {
    let analyzer = PluginAnalyzer::new(
        vec![],
        vec![], // No ignore list
        "Buffout 4".to_string(),
        "1.10.163".to_string(),
        "1.10.163vr".to_string(),
    )
    .unwrap();

    let mut plugins = IndexMap::new();
    plugins.insert("Fallout4.esm".to_string(), "00".to_string());
    plugins.insert("MyMod.esp".to_string(), "01".to_string());

    let result = analyzer.filter_ignored_plugins(plugins).unwrap();
    assert_eq!(result.len(), 2);
}

#[test]
fn test_filter_ignored_plugins_filters() {
    let analyzer = PluginAnalyzer::new(
        vec![],
        vec!["fallout4.esm".to_string()], // Ignore base game
        "Buffout 4".to_string(),
        "1.10.163".to_string(),
        "1.10.163vr".to_string(),
    )
    .unwrap();

    let mut plugins = IndexMap::new();
    plugins.insert("Fallout4.esm".to_string(), "00".to_string());
    plugins.insert("MyMod.esp".to_string(), "01".to_string());

    let result = analyzer.filter_ignored_plugins(plugins).unwrap();
    assert_eq!(result.len(), 1);
    assert!(result.contains_key("MyMod.esp"));
    assert!(!result.contains_key("Fallout4.esm"));
}

#[test]
fn test_filter_ignored_plugins_case_insensitive() {
    let analyzer = PluginAnalyzer::new(
        vec![],
        vec!["FALLOUT4.ESM".to_string()], // Uppercase in ignore
        "Buffout 4".to_string(),
        "1.10.163".to_string(),
        "1.10.163vr".to_string(),
    )
    .unwrap();

    let mut plugins = IndexMap::new();
    plugins.insert("Fallout4.esm".to_string(), "00".to_string()); // Mixed case

    let result = analyzer.filter_ignored_plugins(plugins).unwrap();
    // The ignore list is lowercased during construction, so it should match
    assert!(!result.contains_key("Fallout4.esm"));
}

// ============================================
// detect_plugins_batch tests
// ============================================

#[test]
fn test_detect_plugins_batch_empty() {
    let logs: Vec<String> = vec![];
    let result = detect_plugins_batch(logs);
    assert!(result.is_empty());
}

#[test]
fn test_detect_plugins_batch_single_log() {
    let logs = vec!["[00] Fallout4.esm\n[01] MyMod.esp".to_string()];
    let result = detect_plugins_batch(logs);

    assert_eq!(result.len(), 1);
    assert_eq!(result[0].len(), 2);
    assert_eq!(result[0].get("Fallout4.esm"), Some(&"00".to_string()));
    assert_eq!(result[0].get("MyMod.esp"), Some(&"01".to_string()));
}

#[test]
fn test_detect_plugins_batch_multiple_logs() {
    let logs = vec![
        "[00] GameA.esm\n[01] ModA.esp".to_string(),
        "[00] GameB.esm\n[01] ModB.esp".to_string(),
    ];
    let result = detect_plugins_batch(logs);

    assert_eq!(result.len(), 2);
    assert!(result[0].contains_key("GameA.esm"));
    assert!(result[1].contains_key("GameB.esm"));
}

#[test]
fn test_detect_plugins_batch_preserves_order() {
    let logs = vec![
        "[00] First.esm".to_string(),
        "[00] Second.esm".to_string(),
        "[00] Third.esm".to_string(),
    ];
    let result = detect_plugins_batch(logs);

    assert_eq!(result.len(), 3);
    assert!(result[0].contains_key("First.esm"));
    assert!(result[1].contains_key("Second.esm"));
    assert!(result[2].contains_key("Third.esm"));
}

#[test]
fn test_detect_plugins_batch_light_plugins() {
    let logs = vec!["[FE:001] Light1.esl\n[FE:002] Light2.esl".to_string()];
    let result = detect_plugins_batch(logs);

    assert_eq!(result.len(), 1);
    assert_eq!(result[0].get("Light1.esl"), Some(&"FE001".to_string()));
    assert_eq!(result[0].get("Light2.esl"), Some(&"FE002".to_string()));
}

#[test]
fn test_detect_plugins_batch_no_plugins() {
    let logs = vec!["No plugins in this log\nJust regular text".to_string()];
    let result = detect_plugins_batch(logs);

    assert_eq!(result.len(), 1);
    assert!(result[0].is_empty());
}

#[test]
fn test_detect_plugins_batch_skips_mixed_case_duplicates() {
    let logs = vec!["[01] MyMod.esp\n[02] mymod.esp".to_string()];
    let result = detect_plugins_batch(logs);

    assert_eq!(result.len(), 1);
    assert_eq!(result[0].len(), 1);
    assert_eq!(result[0].get("MyMod.esp"), Some(&"01".to_string()));
    assert!(!result[0].contains_key("mymod.esp"));
}
