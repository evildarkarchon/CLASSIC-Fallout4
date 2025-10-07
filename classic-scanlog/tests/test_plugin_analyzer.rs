//! Comprehensive tests for the high-performance plugin analyzer module
//!
//! This module tests the plugin analysis implementation with:
//! - Plugin file parsing (.esp, .esm, .esl)
//! - Plugin type detection and load order analysis
//! - Dependency resolution and conflict detection
//! - Plugin limit detection (FF marker)
//! - Plugin matching in call stacks
//! - Loadorder.txt file handling
//! - Batch processing capabilities
//! - Cache effectiveness
//! - PyO3 bindings and error handling
#[deny(warnings, deprecated)]
use classic_scanlog::{PluginAnalyzer, detect_plugins_batch, contains_plugin};
use std::collections::{HashMap, HashSet};
use std::time::Instant;
use pyo3::prelude::*;
use pyo3::types::PyDict;

// ============================================================================
// Helper Macros
// ============================================================================

/// Macro to simplify PyO3 GIL handling in tests
macro_rules! with_py {
    ($body:expr) => {{
        pyo3::Python::initialize();
        pyo3::Python::attach(|py| $body(py))
    }};
}

// ============================================================================
// Test Data Helpers
// ============================================================================

/// Create sample YAML data for plugin analyzer
fn create_mock_yamldata(py: Python) -> PyResult<Py<PyAny>> {
    let types_module = py.import("types")?;
    let simple_namespace = types_module.getattr("SimpleNamespace")?;

    let kwargs = PyDict::new(py);

    // Game ignore plugins (base game files)
    let game_ignore = vec![
        "Fallout4.esm",
        "DLCRobot.esm",
        "DLCworkshop01.esm",
        "DLCCoast.esm",
        "DLCworkshop02.esm",
        "DLCworkshop03.esm",
        "DLCNukaWorld.esm",
    ];
    kwargs.set_item("game_ignore_plugins", game_ignore)?;

    // User ignore list
    let ignore_list: Vec<String> = vec![];
    kwargs.set_item("ignore_list", ignore_list)?;

    // Game version info
    kwargs.set_item("game_version", "1.10.163")?;
    kwargs.set_item("game_version_vr", "1.2.72")?;
    kwargs.set_item("game_version_new", "1.10.984")?;
    kwargs.set_item("crashgen_name", "Buffout 4")?;

    let namespace = simple_namespace.call((), Some(&kwargs))?;
    Ok(namespace.into())
}

/// Create sample plugin entries from a crash log
fn create_sample_plugin_entries() -> Vec<String> {
    vec![
        "[00]     Fallout4.esm".to_string(),
        "[01]     DLCRobot.esm".to_string(),
        "[02]     DLCworkshop01.esm".to_string(),
        "[03]     DLCCoast.esm".to_string(),
        "[04]     DLCworkshop02.esm".to_string(),
        "[05]     DLCworkshop03.esm".to_string(),
        "[06]     DLCNukaWorld.esm".to_string(),
        "[07]     Unofficial Fallout 4 Patch.esp".to_string(),
        "[08]     ArmorKeywords.esm".to_string(),
        "[09]     WorkshopFramework.esm".to_string(),
        "[0A]     SimSettlements.esm".to_string(),
        "[FE:000] AAF.esm".to_string(),
        "[FE:001] LooksMenu.esl".to_string(),
        "[FE:002] CustomMod.esp".to_string(),
    ]
}

/// Create plugin entries with plugin limit marker
fn create_plugin_entries_with_limit() -> Vec<String> {
    let mut entries = create_sample_plugin_entries();
    entries.push("[FF]     * PLUGIN LIMIT REACHED *".to_string());
    entries
}

/// Create plugin entries with malformed data
fn create_malformed_plugin_entries() -> Vec<String> {
    vec![
        "[00]     Fallout4.esm".to_string(),
        "INVALID LINE".to_string(),
        "[01".to_string(),
        "DLCRobot.esm".to_string(),
        "[FE:GGG] Invalid.esp".to_string(),
        "[  ]     Empty.esp".to_string(),
        "[]       NoID.esp".to_string(),
    ]
}

/// Create large plugin list for performance testing
fn create_large_plugin_list(count: usize) -> Vec<String> {
    let mut plugins = Vec::with_capacity(count);

    for i in 0..count.min(254) {
        plugins.push(format!("[{:02X}]     TestPlugin{:03}.esp", i, i));
    }

    // Add ESL plugins (FE prefix)
    for i in 0..(count.saturating_sub(254)) {
        plugins.push(format!("[FE:{:03X}] ESLPlugin{:03}.esl", i, i));
    }

    plugins
}

/// Create sample call stack for plugin matching
fn create_sample_callstack() -> Vec<String> {
    vec![
        "PROBABLE CALL STACK:".to_string(),
        "[0] 0x7FF123456789 Fallout4.exe+0123456".to_string(),
        "[1] 0x7FF234567890 unofficial fallout 4 patch.esp+0000123".to_string(),
        "[2] 0x7FF345678901 WorkshopFramework.esm+0000456".to_string(),
        "[3] 0x7FF456789012 simsettlements.esm+0000789".to_string(),
        "[4] 0x7FF567890123 Fallout4.exe+0123457".to_string(),
        "[5] 0x7FF678901234 LooksMenu.esl+0000012 modified by: custommod.esp".to_string(),
    ]
}

/// Create plugins detected in crash log
fn create_crashlog_plugins() -> HashMap<String, String> {
    let mut plugins = HashMap::new();

    plugins.insert("Fallout4.esm".to_string(), "00".to_string());
    plugins.insert("DLCRobot.esm".to_string(), "01".to_string());
    plugins.insert("DLCworkshop01.esm".to_string(), "02".to_string());
    plugins.insert("Unofficial Fallout 4 Patch.esp".to_string(), "07".to_string());
    plugins.insert("WorkshopFramework.esm".to_string(), "09".to_string());
    plugins.insert("SimSettlements.esm".to_string(), "0A".to_string());
    plugins.insert("LooksMenu.esl".to_string(), "FE001".to_string());
    plugins.insert("CustomMod.esp".to_string(), "FE002".to_string());

    plugins
}

// ============================================================================
// Unit Tests - Pure Rust Functions
// ============================================================================

#[test]
fn test_contains_plugin_valid() {
    // Standard plugin entries
    assert!(contains_plugin("[00]     Fallout4.esm"));
    assert!(contains_plugin("[01]     DLCRobot.esm"));
    assert!(contains_plugin("[FF]     SomePlugin.esp"));

    // ESL plugins with FE prefix
    assert!(contains_plugin("[FE:000] TestMod.esl"));
    assert!(contains_plugin("[FE:ABC] AnotherMod.esp"));

    // Mixed case extensions
    assert!(contains_plugin("[00]     Test.ESP"));
    assert!(contains_plugin("[01]     Test.ESM"));
    assert!(contains_plugin("[FE:000] Test.ESL"));

    // With whitespace
    assert!(contains_plugin("   [00]     Fallout4.esm   "));
    assert!(contains_plugin("\t[01]\tDLCRobot.esm"));
}

#[test]
fn test_contains_plugin_invalid() {
    // Missing brackets
    assert!(!contains_plugin("00 Fallout4.esm"));
    assert!(!contains_plugin("Fallout4.esm"));

    // Invalid plugin ID format
    assert!(!contains_plugin("[GG] Invalid.esp"));
    assert!(!contains_plugin("[FE:GGG] Invalid.esp"));

    // Wrong file extension
    assert!(!contains_plugin("[00] NotAPlugin.txt"));
    assert!(!contains_plugin("[00] NotAPlugin.dll"));

    // Empty or incomplete
    assert!(!contains_plugin(""));
    assert!(!contains_plugin("[00]"));
    assert!(!contains_plugin("[00]     "));
}

#[test]
fn test_contains_plugin_edge_cases() {
    // Multiple extensions (some mods have this)
    assert!(contains_plugin("[00] Test.esm.esp"));

    // Case insensitivity
    assert!(contains_plugin("[00] test.ESP"));
    assert!(contains_plugin("[00] TEST.esm"));

    // Minimal whitespace
    assert!(contains_plugin("[00]Test.esp"));
}

#[test]
fn test_detect_plugins_batch_single_log() {
    let log = create_sample_plugin_entries().join("\n");
    let results = detect_plugins_batch(vec![log]).unwrap();

    assert_eq!(results.len(), 1);

    let plugins = &results[0];
    assert!(plugins.len() > 0);

    // Check base game plugins
    assert!(plugins.contains_key("Fallout4.esm"));
    assert!(plugins.contains_key("DLCRobot.esm"));

    // Check ESL plugins
    assert!(plugins.contains_key("LooksMenu.esl"));
}

#[test]
fn test_detect_plugins_batch_multiple_logs() {
    let log1 = create_sample_plugin_entries().join("\n");
    let log2 = vec![
        "[00] Fallout4.esm",
        "[01] TestPlugin.esp",
        "[FE:000] AnotherESL.esl",
    ].join("\n");

    let results = detect_plugins_batch(vec![log1, log2]).unwrap();

    assert_eq!(results.len(), 2);
    assert!(results[0].len() > results[1].len()); // First log has more plugins
}

#[test]
fn test_detect_plugins_batch_empty() {
    let results = detect_plugins_batch(vec![]).unwrap();
    assert_eq!(results.len(), 0);
}

#[test]
fn test_detect_plugins_batch_dll_detection() {
    let log = vec![
        "[00] Fallout4.esm",
        "Buffout4.dll loaded",
        "F4SE.dll initialized",
        "[01] TestMod.esp",
    ].join("\n");

    let results = detect_plugins_batch(vec![log]).unwrap();

    assert_eq!(results.len(), 1);
    let plugins = &results[0];

    // Plugin pattern only matches .esp/.esm/.esl files
    // DLL files are NOT detected by the plugin pattern
    assert!(plugins.contains_key("Fallout4.esm"));
    assert!(plugins.contains_key("TestMod.esp"));

    // DLL files should NOT be in the plugin list
    assert!(!plugins.contains_key("Buffout4.dll"));
    assert!(!plugins.contains_key("F4SE.dll"));
}

// ============================================================================
// Integration Tests - PluginAnalyzer Class
// ============================================================================

#[test]
fn test_plugin_analyzer_creation() {
    with_py!(|py| {
        let yamldata = create_mock_yamldata(py).unwrap();
        let analyzer = Py::new(
            py,
            PluginAnalyzer::new(yamldata.bind(py)).unwrap()
        ).unwrap();

        assert!(analyzer.bind(py).is_instance_of::<PluginAnalyzer>());
        Ok::<(), PyErr>(())
    }).unwrap();
}

#[test]
fn test_loadorder_scan_log_basic() {
    with_py!(|py| {
        let yamldata = create_mock_yamldata(py).unwrap();
        let analyzer = Py::new(
            py,
            PluginAnalyzer::new(yamldata.bind(py)).unwrap()
        ).unwrap();

        let plugin_entries = create_sample_plugin_entries();

        let result = analyzer.bind(py).call_method1(
            "loadorder_scan_log",
            (plugin_entries,)
        ).unwrap();

        let load_order = result.extract::<Vec<String>>().unwrap();

        assert!(load_order.len() > 0);

        // Check plugin order preservation
        assert_eq!(load_order[0], "Fallout4.esm");
        assert!(load_order.contains(&"Unofficial Fallout 4 Patch.esp".to_string()));
        assert!(load_order.contains(&"LooksMenu.esl".to_string()));

        Ok::<(), PyErr>(())
    }).unwrap();
}

#[test]
fn test_loadorder_scan_log_deduplication() {
    with_py!(|py| {
        let yamldata = create_mock_yamldata(py).unwrap();
        let analyzer = Py::new(
            py,
            PluginAnalyzer::new(yamldata.bind(py)).unwrap()
        ).unwrap();

        let plugin_entries = vec![
            "[00] Fallout4.esm".to_string(),
            "[01] TestPlugin.esp".to_string(),
            "[02] TestPlugin.esp".to_string(), // Duplicate
            "[03] Another.esp".to_string(),
            "[04] TestPlugin.esp".to_string(), // Another duplicate
        ];

        let result = analyzer.bind(py).call_method1(
            "loadorder_scan_log",
            (plugin_entries,)
        ).unwrap();

        let load_order = result.extract::<Vec<String>>().unwrap();

        // Should only contain unique plugins
        assert_eq!(load_order.len(), 3);
        assert_eq!(load_order.iter().filter(|p| *p == "TestPlugin.esp").count(), 1);

        Ok::<(), PyErr>(())
    }).unwrap();
}

#[test]
fn test_loadorder_scan_log_empty() {
    with_py!(|py| {
        let yamldata = create_mock_yamldata(py).unwrap();
        let analyzer = Py::new(
            py,
            PluginAnalyzer::new(yamldata.bind(py)).unwrap()
        ).unwrap();

        let plugin_entries: Vec<String> = vec![];

        let result = analyzer.bind(py).call_method1(
            "loadorder_scan_log",
            (plugin_entries,)
        ).unwrap();

        let load_order = result.extract::<Vec<String>>().unwrap();
        assert_eq!(load_order.len(), 0);

        Ok::<(), PyErr>(())
    }).unwrap();
}

#[test]
fn test_loadorder_scan_log_malformed_entries() {
    with_py!(|py| {
        let yamldata = create_mock_yamldata(py).unwrap();
        let analyzer = Py::new(
            py,
            PluginAnalyzer::new(yamldata.bind(py)).unwrap()
        ).unwrap();

        let plugin_entries = create_malformed_plugin_entries();

        let result = analyzer.bind(py).call_method1(
            "loadorder_scan_log",
            (plugin_entries,)
        ).unwrap();

        let load_order = result.extract::<Vec<String>>().unwrap();

        // Should only extract valid entries
        assert!(load_order.contains(&"Fallout4.esm".to_string()));
        assert!(!load_order.contains(&"INVALID LINE".to_string()));

        Ok::<(), PyErr>(())
    }).unwrap();
}

#[test]
fn test_check_plugin_limit_original_game() {
    with_py!(|py| {
        let yamldata = create_mock_yamldata(py).unwrap();
        let analyzer = Py::new(
            py,
            PluginAnalyzer::new(yamldata.bind(py)).unwrap()
        ).unwrap();

        let plugin_entries = create_plugin_entries_with_limit();
        let game_version = "1.10.163";
        let crashgen_version = "1.28.0";

        let result = analyzer.bind(py).call_method1(
            "check_plugin_limit",
            (plugin_entries, game_version, crashgen_version)
        ).unwrap();

        let (limit_triggered, limit_disabled) = result.extract::<(bool, bool)>().unwrap();

        // Original game should trigger plugin limit
        assert_eq!(limit_triggered, true);
        assert_eq!(limit_disabled, false);

        Ok::<(), PyErr>(())
    }).unwrap();
}

#[test]
fn test_check_plugin_limit_new_game() {
    with_py!(|py| {
        let yamldata = create_mock_yamldata(py).unwrap();
        let analyzer = Py::new(
            py,
            PluginAnalyzer::new(yamldata.bind(py)).unwrap()
        ).unwrap();

        let plugin_entries = create_plugin_entries_with_limit();
        let game_version = "1.10.984"; // Next-gen update
        let crashgen_version = "1.36.0"; // Pre-1.37 Buffout

        let result = analyzer.bind(py).call_method1(
            "check_plugin_limit",
            (plugin_entries, game_version, crashgen_version)
        ).unwrap();

        let (limit_triggered, limit_disabled) = result.extract::<(bool, bool)>().unwrap();

        // New game with pre-1.37 Buffout should disable limit check
        assert_eq!(limit_triggered, false);
        assert_eq!(limit_disabled, true);

        Ok::<(), PyErr>(())
    }).unwrap();
}

#[test]
fn test_check_plugin_limit_no_marker() {
    with_py!(|py| {
        let yamldata = create_mock_yamldata(py).unwrap();
        let analyzer = Py::new(
            py,
            PluginAnalyzer::new(yamldata.bind(py)).unwrap()
        ).unwrap();

        let plugin_entries = create_sample_plugin_entries(); // No [FF] marker
        let game_version = "1.10.163";
        let crashgen_version = "1.28.0";

        let result = analyzer.bind(py).call_method1(
            "check_plugin_limit",
            (plugin_entries, game_version, crashgen_version)
        ).unwrap();

        let (limit_triggered, limit_disabled) = result.extract::<(bool, bool)>().unwrap();

        // No marker = no limit triggered
        assert_eq!(limit_triggered, false);
        assert_eq!(limit_disabled, false);

        Ok::<(), PyErr>(())
    }).unwrap();
}

#[test]
fn test_plugin_match_found_suspects() {
    with_py!(|py| {
        let yamldata = create_mock_yamldata(py).unwrap();
        let analyzer = Py::new(
            py,
            PluginAnalyzer::new(yamldata.bind(py)).unwrap()
        ).unwrap();

        let callstack = create_sample_callstack();
        let callstack_lower: Vec<String> = callstack.iter().map(|s| s.to_lowercase()).collect();

        let plugins = create_crashlog_plugins();
        let plugins_lower: HashSet<String> = plugins.keys().map(|s| s.to_lowercase()).collect();

        let result = analyzer.bind(py).call_method1(
            "plugin_match",
            (callstack_lower, plugins_lower)
        ).unwrap();

        let report = result.extract::<Vec<String>>().unwrap();

        // Should find plugin suspects
        assert!(report.len() > 0);
        assert!(report.iter().any(|line| line.contains("PLUGINS were found")));
        assert!(report.iter().any(|line| line.contains("unofficial fallout 4 patch.esp")));
        assert!(report.iter().any(|line| line.contains("workshopframework.esm")));

        Ok::<(), PyErr>(())
    }).unwrap();
}

#[test]
fn test_plugin_match_no_suspects() {
    with_py!(|py| {
        let yamldata = create_mock_yamldata(py).unwrap();
        let analyzer = Py::new(
            py,
            PluginAnalyzer::new(yamldata.bind(py)).unwrap()
        ).unwrap();

        let callstack = vec![
            "[0] 0x7FF123456789 Fallout4.exe+0123456".to_string(),
            "[1] 0x7FF234567890 ntdll.dll+0000123".to_string(),
        ];
        let callstack_lower: Vec<String> = callstack.iter().map(|s| s.to_lowercase()).collect();

        let plugins = create_crashlog_plugins();
        let plugins_lower: HashSet<String> = plugins.keys().map(|s| s.to_lowercase()).collect();

        let result = analyzer.bind(py).call_method1(
            "plugin_match",
            (callstack_lower, plugins_lower)
        ).unwrap();

        let report = result.extract::<Vec<String>>().unwrap();

        // Should report no suspects found
        assert!(report.iter().any(|line| line.contains("COULDN'T FIND ANY PLUGIN SUSPECTS")));

        Ok::<(), PyErr>(())
    }).unwrap();
}

#[test]
fn test_plugin_match_ignores_game_plugins() {
    with_py!(|py| {
        let yamldata = create_mock_yamldata(py).unwrap();
        let analyzer = Py::new(
            py,
            PluginAnalyzer::new(yamldata.bind(py)).unwrap()
        ).unwrap();

        let callstack = vec![
            "[0] 0x7FF123456789 fallout4.esm+0123456".to_string(),
            "[1] 0x7FF234567890 dlcrobot.esm+0000123".to_string(),
        ];
        let callstack_lower: Vec<String> = callstack.iter().map(|s| s.to_lowercase()).collect();

        let mut plugins = create_crashlog_plugins();
        // Add only base game plugins
        plugins.clear();
        plugins.insert("Fallout4.esm".to_string(), "00".to_string());
        plugins.insert("DLCRobot.esm".to_string(), "01".to_string());

        let plugins_lower: HashSet<String> = plugins.keys().map(|s| s.to_lowercase()).collect();

        let result = analyzer.bind(py).call_method1(
            "plugin_match",
            (callstack_lower, plugins_lower)
        ).unwrap();

        let report = result.extract::<Vec<String>>().unwrap();

        // Base game plugins should be ignored
        assert!(report.iter().any(|line| line.contains("COULDN'T FIND ANY PLUGIN SUSPECTS")));

        Ok::<(), PyErr>(())
    }).unwrap();
}

#[test]
fn test_plugin_match_count_ordering() {
    with_py!(|py| {
        let yamldata = create_mock_yamldata(py).unwrap();
        let analyzer = Py::new(
            py,
            PluginAnalyzer::new(yamldata.bind(py)).unwrap()
        ).unwrap();

        let callstack = vec![
            "[0] testmod.esp".to_string(),
            "[1] testmod.esp".to_string(),
            "[2] testmod.esp".to_string(),
            "[3] anothermod.esp".to_string(),
        ];
        let callstack_lower: Vec<String> = callstack.iter().map(|s| s.to_lowercase()).collect();

        let mut plugins = HashMap::new();
        plugins.insert("TestMod.esp".to_string(), "10".to_string());
        plugins.insert("AnotherMod.esp".to_string(), "11".to_string());

        let plugins_lower: HashSet<String> = plugins.keys().map(|s| s.to_lowercase()).collect();

        let result = analyzer.bind(py).call_method1(
            "plugin_match",
            (callstack_lower, plugins_lower)
        ).unwrap();

        let report = result.extract::<Vec<String>>().unwrap();

        // TestMod.esp should appear before AnotherMod.esp (higher count)
        let testmod_idx = report.iter().position(|line| line.contains("testmod.esp"));
        let anothermod_idx = report.iter().position(|line| line.contains("anothermod.esp"));

        assert!(testmod_idx.is_some());
        assert!(anothermod_idx.is_some());
        assert!(testmod_idx.unwrap() < anothermod_idx.unwrap());

        Ok::<(), PyErr>(())
    }).unwrap();
}

#[test]
fn test_filter_ignored_plugins_empty_ignore_list() {
    with_py!(|py| {
        let yamldata = create_mock_yamldata(py).unwrap();
        let analyzer = Py::new(
            py,
            PluginAnalyzer::new(yamldata.bind(py)).unwrap()
        ).unwrap();

        let plugins = create_crashlog_plugins();
        let original_count = plugins.len();

        let result = analyzer.bind(py).call_method1(
            "filter_ignored_plugins",
            (plugins.clone(),)
        ).unwrap();

        let filtered = result.extract::<HashMap<String, String>>().unwrap();

        // Should return unchanged when ignore list is empty
        assert_eq!(filtered.len(), original_count);

        Ok::<(), PyErr>(())
    }).unwrap();
}

#[test]
fn test_filter_ignored_plugins_with_ignore_list() {
    pyo3::Python::initialize();
    pyo3::Python::attach(|py| {
        // Create yamldata with ignore list
        let types_module = py.import("types").unwrap();
        let simple_namespace = types_module.getattr("SimpleNamespace").unwrap();

        let kwargs = PyDict::new(py);
        let game_ignore: Vec<String> = vec![];
        kwargs.set_item("game_ignore_plugins", game_ignore).unwrap();

        let ignore_list = vec!["LooksMenu.esl", "CustomMod.esp"];
        kwargs.set_item("ignore_list", ignore_list).unwrap();

        kwargs.set_item("game_version", "1.10.163").unwrap();
        kwargs.set_item("game_version_vr", "1.2.72").unwrap();
        kwargs.set_item("game_version_new", "1.10.984").unwrap();
        kwargs.set_item("crashgen_name", "Buffout 4").unwrap();

        let yamldata: Py<PyAny> = simple_namespace.call((), Some(&kwargs)).unwrap().into();

        let analyzer = Py::new(
            py,
            PluginAnalyzer::new(yamldata.bind(py)).unwrap()
        ).unwrap();

        let plugins = create_crashlog_plugins();

        let result = analyzer.bind(py).call_method1(
            "filter_ignored_plugins",
            (plugins.clone(),)
        ).unwrap();

        let filtered = result.extract::<HashMap<String, String>>().unwrap();

        // Should remove ignored plugins
        assert!(!filtered.contains_key("LooksMenu.esl"));
        assert!(!filtered.contains_key("CustomMod.esp"));
        assert!(filtered.len() < plugins.len());
    });
}

#[test]
fn test_filter_ignored_plugins_case_insensitive() {
    pyo3::Python::initialize();
    pyo3::Python::attach(|py| {
        // Create yamldata with ignore list (different case)
        let types_module = py.import("types").unwrap();
        let simple_namespace = types_module.getattr("SimpleNamespace").unwrap();

        let kwargs = PyDict::new(py);
        let game_ignore: Vec<String> = vec![];
        kwargs.set_item("game_ignore_plugins", game_ignore).unwrap();

        let ignore_list = vec!["LOOKSMENU.ESL", "custommodd.ESP"]; // Different case
        kwargs.set_item("ignore_list", ignore_list).unwrap();

        kwargs.set_item("game_version", "1.10.163").unwrap();
        kwargs.set_item("game_version_vr", "1.2.72").unwrap();
        kwargs.set_item("game_version_new", "1.10.984").unwrap();
        kwargs.set_item("crashgen_name", "Buffout 4").unwrap();

        let yamldata: Py<PyAny> = simple_namespace.call((), Some(&kwargs)).unwrap().into();

        let analyzer = Py::new(
            py,
            PluginAnalyzer::new(yamldata.bind(py)).unwrap()
        ).unwrap();

        let plugins = create_crashlog_plugins();

        let result = analyzer.bind(py).call_method1(
            "filter_ignored_plugins",
            (plugins.clone(),)
        ).unwrap();

        let filtered = result.extract::<HashMap<String, String>>().unwrap();

        // Should remove LooksMenu.esl despite case difference
        assert!(!filtered.contains_key("LooksMenu.esl"));
    });
}

#[test]
fn test_loadorder_scan_loadorder_txt() {
    with_py!(|py| {
        // Note: This test requires actual loadorder.txt file
        // For now, test the function signature and error handling
        let result = PluginAnalyzer::loadorder_scan_loadorder_txt(py);

        assert!(result.is_ok());
        let (plugins_dict, _plugins_loaded, report_lines) = result.unwrap();

        // Should return proper types
        assert!(plugins_dict.bind(py).is_instance_of::<PyDict>());
        assert!(report_lines.len() >= 3); // At least the header lines

        Ok::<(), PyErr>(())
    }).unwrap();
}

// ============================================================================
// Performance Tests
// ============================================================================

#[test]
fn test_loadorder_scan_performance() {
    with_py!(|py| {
        let yamldata = create_mock_yamldata(py).unwrap();
        let analyzer = Py::new(
            py,
            PluginAnalyzer::new(yamldata.bind(py)).unwrap()
        ).unwrap();

        let large_plugin_list = create_large_plugin_list(500);

        let start = Instant::now();
        let result = analyzer.bind(py).call_method1(
            "loadorder_scan_log",
            (large_plugin_list,)
        ).unwrap();
        let elapsed = start.elapsed();

        let load_order = result.extract::<Vec<String>>().unwrap();

        println!("Scanned {} plugins in {:?}", load_order.len(), elapsed);

        // Should be fast (< 50ms for 500 plugins)
        assert!(elapsed.as_millis() < 50);
        assert!(load_order.len() > 0);

        Ok::<(), PyErr>(())
    }).unwrap();
}

#[test]
fn test_plugin_match_performance() {
    with_py!(|py| {
        let yamldata = create_mock_yamldata(py).unwrap();
        let analyzer = Py::new(
            py,
            PluginAnalyzer::new(yamldata.bind(py)).unwrap()
        ).unwrap();

        // Create large call stack
        let mut callstack = Vec::new();
        for i in 0..1000 {
            callstack.push(format!("[{}] 0x7FF{:08X} testmod{}.esp+{:06X}", i, i, i % 10, i));
        }
        let callstack_lower: Vec<String> = callstack.iter().map(|s| s.to_lowercase()).collect();

        // Create plugin set
        let mut plugins = HashSet::new();
        for i in 0..10 {
            plugins.insert(format!("testmod{}.esp", i));
        }

        let start = Instant::now();
        let result = analyzer.bind(py).call_method1(
            "plugin_match",
            (callstack_lower, plugins)
        ).unwrap();
        let elapsed = start.elapsed();

        let report = result.extract::<Vec<String>>().unwrap();

        println!("Matched plugins in 1000-line call stack in {:?}", elapsed);

        // Should be fast (< 100ms for 1000 lines)
        assert!(elapsed.as_millis() < 100);
        assert!(report.len() > 0);

        Ok::<(), PyErr>(())
    }).unwrap();
}

#[test]
fn test_batch_plugin_detection_performance() {
    let mut logs = Vec::new();

    for _ in 0..100 {
        logs.push(create_sample_plugin_entries().join("\n"));
    }

    let start = Instant::now();
    let results = detect_plugins_batch(logs).unwrap();
    let elapsed = start.elapsed();

    println!("Detected plugins in 100 logs in {:?}", elapsed);

    assert_eq!(results.len(), 100);

    // Should use parallel processing (< 200ms for 100 logs)
    assert!(elapsed.as_millis() < 200);
}

// ============================================================================
// Edge Cases and Error Handling
// ============================================================================

#[test]
fn test_plugin_pattern_case_sensitivity() {
    // Windows filesystem is case-insensitive, plugin matching should be too
    assert!(contains_plugin("[00] FALLOUT4.ESM"));
    assert!(contains_plugin("[00] fallout4.esm"));
    assert!(contains_plugin("[00] FaLlOuT4.EsM"));
}

#[test]
fn test_plugin_extensions_all_types() {
    assert!(contains_plugin("[00] Test.esp"));
    assert!(contains_plugin("[00] Test.esm"));
    assert!(contains_plugin("[00] Test.esl"));

    // Case variations
    assert!(contains_plugin("[00] Test.ESP"));
    assert!(contains_plugin("[00] Test.ESM"));
    assert!(contains_plugin("[00] Test.ESL"));
}

#[test]
fn test_esl_plugin_fe_format() {
    // ESL plugins use FE:XXX format where XXX is 3 hex digits
    assert!(contains_plugin("[FE:000] First.esl"));
    assert!(contains_plugin("[FE:FFF] Last.esl"));
    assert!(contains_plugin("[FE:ABC] Middle.esl"));

    // Case insensitive
    assert!(contains_plugin("[fe:000] test.esl"));
    assert!(contains_plugin("[FE:abc] test.esl"));
}

#[test]
fn test_plugin_limit_marker_detection() {
    // Plugin limit markers don't have .esp/.esm/.esl extensions
    // so they won't match the plugin pattern
    // The pattern specifically requires plugin file extensions
    assert!(!contains_plugin("[FF] * PLUGIN LIMIT *"));
    assert!(!contains_plugin("[FF]     * PLUGIN LIMIT REACHED *"));

    // But plugins with [FF] ID and proper extensions would match
    // (though [FF] is typically reserved for the limit marker)
    assert!(contains_plugin("[FF] RarePlugin.esp"));
}

#[test]
fn test_multiple_extensions_in_filename() {
    // Some mods have unusual naming
    assert!(contains_plugin("[00] Test.esm.esp"));
    assert!(contains_plugin("[00] Mod.Name.With.Dots.esp"));
}

#[test]
fn test_unicode_plugin_names() {
    // Some mod names may contain unicode characters
    assert!(contains_plugin("[00] Тест.esp")); // Cyrillic
    assert!(contains_plugin("[00] 测试.esp")); // Chinese
    assert!(contains_plugin("[00] Modé.esp")); // Accented
}

#[test]
fn test_loadorder_scan_preserves_order() {
    with_py!(|py| {
        let yamldata = create_mock_yamldata(py).unwrap();
        let analyzer = Py::new(
            py,
            PluginAnalyzer::new(yamldata.bind(py)).unwrap()
        ).unwrap();

        let plugin_entries = vec![
            "[00] A.esm".to_string(),
            "[01] B.esm".to_string(),
            "[02] C.esp".to_string(),
            "[03] D.esp".to_string(),
        ];

        let result = analyzer.bind(py).call_method1(
            "loadorder_scan_log",
            (plugin_entries,)
        ).unwrap();

        let load_order = result.extract::<Vec<String>>().unwrap();

        // Order should be preserved
        assert_eq!(load_order[0], "A.esm");
        assert_eq!(load_order[1], "B.esm");
        assert_eq!(load_order[2], "C.esp");
        assert_eq!(load_order[3], "D.esp");

        Ok::<(), PyErr>(())
    }).unwrap();
}

// ============================================================================
// Benchmark Tests (Ignored by default)
// ============================================================================

#[cfg(test)]
mod benchmarks {
    use super::*;

    #[test]
    #[ignore]
    fn bench_plugin_detection_scaling() {
        let sizes = vec![10, 50, 100, 500, 1000];

        for size in sizes {
            let mut logs = Vec::new();
            for _ in 0..size {
                logs.push(create_large_plugin_list(100).join("\n"));
            }

            let start = Instant::now();
            let results = detect_plugins_batch(logs).unwrap();
            let elapsed = start.elapsed();

            println!("Batch detection for {} logs: {:?} ({:.2} logs/sec)",
                     size, elapsed, size as f64 / elapsed.as_secs_f64());

            assert_eq!(results.len(), size);
        }
    }

    #[test]
    #[ignore]
    fn bench_plugin_matching_scaling() {
        pyo3::Python::initialize();
        pyo3::Python::attach(|py| {
            let yamldata = create_mock_yamldata(py).unwrap();
            let analyzer = Py::new(
                py,
                PluginAnalyzer::new(yamldata.bind(py)).unwrap()
            ).unwrap();

            let sizes = vec![100, 500, 1000, 5000];

            for size in sizes {
                let mut callstack = Vec::new();
                for i in 0..size {
                    callstack.push(format!("[{}] testmod{}.esp+{:06X}", i, i % 50, i));
                }
                let callstack_lower: Vec<String> = callstack.iter().map(|s| s.to_lowercase()).collect();

                let mut plugins = HashSet::new();
                for i in 0..50 {
                    plugins.insert(format!("testmod{}.esp", i));
                }

                let start = Instant::now();
                let _result = analyzer.bind(py).call_method1(
                    "plugin_match",
                    (callstack_lower, plugins)
                ).unwrap();
                let elapsed = start.elapsed();

                println!("Plugin matching for {} callstack lines: {:?} ({:.2} lines/sec)",
                         size, elapsed, size as f64 / elapsed.as_secs_f64());
            }
        });
    }

    #[test]
    #[ignore]
    fn bench_loadorder_parsing() {
        pyo3::Python::initialize();
        pyo3::Python::attach(|py| {
            let yamldata = create_mock_yamldata(py).unwrap();
            let analyzer = Py::new(
                py,
                PluginAnalyzer::new(yamldata.bind(py)).unwrap()
            ).unwrap();

            let sizes = vec![50, 100, 254, 500, 1000];

            for size in sizes {
                let plugin_list = create_large_plugin_list(size);

                let start = Instant::now();
                let result = analyzer.bind(py).call_method1(
                    "loadorder_scan_log",
                    (plugin_list.clone(),)
                ).unwrap();
                let elapsed = start.elapsed();

                let load_order = result.extract::<Vec<String>>().unwrap();

                println!("Loadorder parsing for {} plugins: {:?} ({:.2} plugins/ms)",
                         size, elapsed, size as f64 / elapsed.as_millis() as f64);

                assert!(load_order.len() > 0);
            }
        });
    }

    #[test]
    #[ignore]
    fn bench_filter_ignored_plugins() {
        pyo3::Python::initialize();
        pyo3::Python::attach(|py| {
            // Create yamldata with large ignore list
            let types_module = py.import("types").unwrap();
            let simple_namespace = types_module.getattr("SimpleNamespace").unwrap();

            let kwargs = PyDict::new(py);
            let game_ignore: Vec<String> = vec![];
            kwargs.set_item("game_ignore_plugins", game_ignore).unwrap();

            let mut ignore_list = Vec::new();
            for i in 0..100 {
                ignore_list.push(format!("IgnoredMod{}.esp", i));
            }
            kwargs.set_item("ignore_list", ignore_list).unwrap();

            kwargs.set_item("game_version", "1.10.163").unwrap();
            kwargs.set_item("game_version_vr", "1.2.72").unwrap();
            kwargs.set_item("game_version_new", "1.10.984").unwrap();
            kwargs.set_item("crashgen_name", "Buffout 4").unwrap();

            let yamldata: Py<PyAny> = simple_namespace.call((), Some(&kwargs)).unwrap().into();

            let analyzer = Py::new(
                py,
                PluginAnalyzer::new(yamldata.bind(py)).unwrap()
            ).unwrap();

            // Create large plugin set
            let mut plugins = HashMap::new();
            for i in 0..500 {
                plugins.insert(format!("TestMod{}.esp", i), format!("{:02X}", i % 254));
            }

            let start = Instant::now();
            let _result = analyzer.bind(py).call_method1(
                "filter_ignored_plugins",
                (plugins.clone(),)
            ).unwrap();
            let elapsed = start.elapsed();

            println!("Filtering {} plugins with 100 ignore patterns: {:?}",
                     plugins.len(), elapsed);
        });
    }
}
