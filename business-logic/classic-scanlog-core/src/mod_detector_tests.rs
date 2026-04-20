use super::*;
use crate::{LogParser, plugin_analyzer::PluginAnalyzer, segment_key};
use classic_config_core::{ModSolutionCriteria, ModSolutionEntry};
use serial_test::serial;
use std::sync::Arc as StdArc;
use std::sync::Arc;

const IMPORTANT_MODS_FIXTURE_LOG: &str =
    include_str!("../benches/fixtures/crash-2022-06-05-12-58-02.log");

fn reset_matcher_caches_for_tests() {
    SINGLE_MATCHER_CACHE.clear();
    DOUBLE_MATCHER_CACHE.clear();
    BATCH_MATCHER_CACHE.clear();
    IMPORTANT_MATCHER_CACHE.clear();
    SINGLE_MATCHER_COMPILES.store(0, Ordering::Relaxed);
    DOUBLE_MATCHER_COMPILES.store(0, Ordering::Relaxed);
    BATCH_MATCHER_COMPILES.store(0, Ordering::Relaxed);
    IMPORTANT_MATCHER_COMPILES.store(0, Ordering::Relaxed);
}

fn single_matcher_for_tests(yaml_dict: &IndexMap<String, String>) -> Result<Arc<Regex>> {
    let (_, matcher) = get_single_matcher(yaml_dict)?;
    Ok(matcher)
}

fn double_matcher_for_tests(entries: &[ModConflictEntry]) -> Result<Arc<Regex>> {
    get_double_matcher(entries)
}

fn batch_matcher_for_tests(yaml_dict: &IndexMap<String, String>) -> Result<Arc<Regex>> {
    let (_, matcher) = get_batch_matcher(yaml_dict)?;
    Ok(matcher)
}

fn single_cache_size_for_tests() -> usize {
    SINGLE_MATCHER_CACHE.len()
}

fn single_cache_capacity_for_tests() -> usize {
    SINGLE_MATCHER_CACHE.capacity() as usize
}

fn single_compile_count_for_tests() -> u64 {
    SINGLE_MATCHER_COMPILES.load(Ordering::Relaxed)
}

fn double_compile_count_for_tests() -> u64 {
    DOUBLE_MATCHER_COMPILES.load(Ordering::Relaxed)
}

fn double_compile_snapshot_for_tests() -> u64 {
    double_compile_count_for_tests()
}

fn important_matcher_for_tests(entries: &[CoreModEntry]) -> Result<Arc<AhoCorasick>> {
    get_important_matcher(entries)
}

fn important_compile_count_for_tests() -> u64 {
    IMPORTANT_MATCHER_COMPILES.load(Ordering::Relaxed)
}

// ============================================
// Helper function tests
// ============================================

#[test]
fn test_convert_indexmap_to_lowercase_empty() {
    let data: IndexMap<String, String> = IndexMap::new();
    let result = convert_indexmap_to_lowercase(&data);
    assert!(result.is_empty());
}

#[test]
fn test_convert_indexmap_to_lowercase_keys() {
    let mut data = IndexMap::new();
    data.insert("KEY".to_string(), "value".to_string());
    data.insert("AnotherKey".to_string(), "anotherValue".to_string());

    let result = convert_indexmap_to_lowercase(&data);
    assert!(result.contains_key("key"));
    assert!(result.contains_key("anotherkey"));
    assert!(!result.contains_key("KEY"));
}

#[test]
fn test_validate_warning_valid() {
    let result = validate_warning("TestMod", "This is a warning");
    assert!(result.is_ok());
}

#[test]
fn test_validate_warning_empty() {
    let result = validate_warning("TestMod", "");
    assert!(result.is_err());
}

// ============================================
// detect_mods_single tests
// ============================================

#[test]
fn test_detect_mods_single_empty_yaml() {
    let yaml_dict: IndexMap<String, String> = IndexMap::new();
    let plugins: IndexMap<String, String> = IndexMap::new();

    let result = detect_mods_single(yaml_dict, plugins).unwrap();
    assert!(result.is_empty());
}

#[test]
fn test_detect_mods_single_empty_plugins() {
    let mut yaml_dict = IndexMap::new();
    yaml_dict.insert(
        "testmod".to_string(),
        "Test Mod\nThis is a test.".to_string(),
    );

    let plugins: IndexMap<String, String> = IndexMap::new();

    let result = detect_mods_single(yaml_dict, plugins).unwrap();
    assert!(result.is_empty());
}

#[test]
fn test_detect_mods_single_match() {
    let mut yaml_dict = IndexMap::new();
    yaml_dict.insert(
        "problematicmod".to_string(),
        "Problematic Mod\nThis mod causes crashes.".to_string(),
    );

    let mut plugins = IndexMap::new();
    plugins.insert("ProblematicMod.esp".to_string(), "12".to_string());

    let result = detect_mods_single(yaml_dict, plugins).unwrap();
    assert!(!result.is_empty());
    // Should contain FOUND marker
    let output = result.join("");
    assert!(output.contains("FOUND"));
    assert!(output.contains("[12]"));
}

#[test]
fn test_detect_mods_single_no_match() {
    let mut yaml_dict = IndexMap::new();
    yaml_dict.insert(
        "problematicmod".to_string(),
        "Problematic Mod\nThis mod causes crashes.".to_string(),
    );

    let mut plugins = IndexMap::new();
    plugins.insert("DifferentMod.esp".to_string(), "12".to_string());

    let result = detect_mods_single(yaml_dict, plugins).unwrap();
    assert!(result.is_empty());
}

#[test]
fn test_detect_mods_single_case_insensitive() {
    let mut yaml_dict = IndexMap::new();
    yaml_dict.insert("testmod".to_string(), "Test Mod\nWarning text.".to_string());

    let mut plugins = IndexMap::new();
    plugins.insert("TESTMOD.esp".to_string(), "05".to_string());

    let result = detect_mods_single(yaml_dict, plugins).unwrap();
    assert!(!result.is_empty());
}

#[test]
fn test_detect_mods_single_substring_match() {
    let mut yaml_dict = IndexMap::new();
    yaml_dict.insert(
        "partial".to_string(),
        "Partial Match\nMatch found.".to_string(),
    );

    let mut plugins = IndexMap::new();
    plugins.insert("MyPartialMod.esp".to_string(), "10".to_string());

    let result = detect_mods_single(yaml_dict, plugins).unwrap();
    assert!(!result.is_empty());
}

#[test]
fn test_detect_mods_single_longest_match_priority() {
    let mut yaml_dict = IndexMap::new();
    yaml_dict.insert("mod".to_string(), "Mod\nShort match.".to_string());
    yaml_dict.insert(
        "modextended".to_string(),
        "Mod Extended\nLong match.".to_string(),
    );

    let mut plugins = IndexMap::new();
    plugins.insert("ModExtended.esp".to_string(), "15".to_string());

    let result = detect_mods_single(yaml_dict, plugins).unwrap();
    let output = result.join("");
    // The longer pattern should match
    assert!(output.contains("Mod Extended") || output.contains("modextended"));
}

#[test]
#[serial]
fn test_detect_mods_single_reuses_cached_matcher_for_same_normalized_input() {
    let mut yaml_dict = IndexMap::new();
    yaml_dict.insert(
        "RepeatableMod".to_string(),
        "Repeatable Mod\nCache me once.".to_string(),
    );
    yaml_dict.insert(
        "RepeatableModExtended".to_string(),
        "Repeatable Mod Extended\nStill cache me once.".to_string(),
    );

    reset_matcher_caches_for_tests();

    let first = single_matcher_for_tests(&yaml_dict).unwrap();
    let second = single_matcher_for_tests(&yaml_dict).unwrap();

    assert!(Arc::ptr_eq(&first, &second));
    assert_eq!(single_compile_count_for_tests(), 1);
}

#[test]
#[serial]
fn test_detect_mods_single_cache_stays_bounded_without_victim_assertions() {
    reset_matcher_caches_for_tests();

    for index in 0..70 {
        let mut yaml_dict = IndexMap::new();
        yaml_dict.insert(
            format!("bounded-single-{index}"),
            format!("Bounded Single {index}\nKeep cache bounded."),
        );
        let _ = single_matcher_for_tests(&yaml_dict).unwrap();
    }

    assert_eq!(single_cache_capacity_for_tests(), 64);
    assert!(single_cache_size_for_tests() <= single_cache_capacity_for_tests());
    assert!(single_compile_count_for_tests() >= 64);
}

#[test]
fn test_detect_mods_freq_any_match() {
    let entries = vec![make_solution_entry(
        "freq-test",
        ModSolutionCriteria::Any(vec!["FreqMod".to_string(), "FallbackToken".to_string()]),
        vec![],
        "Frequent Mod",
        "This mod can frequently crash the game.",
    )];
    let mut plugins = IndexMap::new();
    plugins.insert("FreqMod.esp".to_string(), "06".to_string());

    let result = detect_mods_freq(&entries, &plugins).unwrap();
    let output = result.join("");

    assert!(output.contains("FOUND : [06] Frequent Mod"));
    assert!(output.contains("frequently crash the game"));
}

#[test]
fn test_detect_mods_freq_all_requires_every_criterion() {
    let entries = vec![make_solution_entry(
        "freq-all",
        ModSolutionCriteria::All(vec!["LooksMenu".to_string(), "CBBE".to_string()]),
        vec![],
        "Combined Setup",
        "Only report when both mods are installed.",
    )];
    let mut plugins = IndexMap::new();
    plugins.insert("LooksMenu.esp".to_string(), "07".to_string());

    let result = detect_mods_freq(&entries, &plugins).unwrap();
    assert!(result.is_empty());
}

#[test]
fn test_detect_mods_freq_exception_suppresses_match() {
    let entries = vec![make_solution_entry(
        "freq-exception",
        ModSolutionCriteria::Any(vec!["ProblematicMod".to_string()]),
        vec!["PatchForProblematicMod"],
        "Problematic Mod",
        "Skip this warning when the patch is installed.",
    )];
    let mut plugins = IndexMap::new();
    plugins.insert("ProblematicMod.esp".to_string(), "08".to_string());
    plugins.insert("PatchForProblematicMod.esp".to_string(), "09".to_string());

    let result = detect_mods_freq(&entries, &plugins).unwrap();
    assert!(result.is_empty());
}

// ============================================
// detect_mods_solutions tests
// ============================================

fn make_solution_entry(
    id: &str,
    criteria: ModSolutionCriteria,
    exceptions: Vec<&str>,
    name: &str,
    description: &str,
) -> ModSolutionEntry {
    ModSolutionEntry {
        id: id.to_string(),
        criteria,
        exceptions: exceptions.into_iter().map(str::to_string).collect(),
        name: name.to_string(),
        description: description.to_string(),
    }
}

#[test]
fn test_detect_mods_solutions_any_match() {
    let entries = vec![make_solution_entry(
        "high-resolution-dlc",
        ModSolutionCriteria::Any(vec![
            "DLCUltraHighResolution".to_string(),
            "HighResPack".to_string(),
        ]),
        vec![],
        "High Resolution DLC",
        "Disable the official texture pack.\nIt causes crashes and stutter.",
    )];
    let mut plugins = IndexMap::new();
    plugins.insert("DLCUltraHighResolution.esp".to_string(), "01".to_string());

    let result = detect_mods_solutions(&entries, &plugins).unwrap();
    let output = result.join("");

    assert!(output.contains("FOUND : [01] High Resolution DLC"));
    assert!(output.contains("Disable the official texture pack."));
    assert!(output.contains("It causes crashes and stutter."));
}

#[test]
fn test_detect_mods_solutions_all_requires_every_criterion() {
    let entries = vec![make_solution_entry(
        "bodyslide-patch",
        ModSolutionCriteria::All(vec!["LooksMenu".to_string(), "CBBE".to_string()]),
        vec![],
        "BodySlide Patch",
        "Install the compatibility patch.",
    )];
    let mut plugins = IndexMap::new();
    plugins.insert("LooksMenu.esp".to_string(), "02".to_string());

    let result = detect_mods_solutions(&entries, &plugins).unwrap();
    assert!(result.is_empty());
}

#[test]
fn test_detect_mods_solutions_exception_suppresses_match() {
    let entries = vec![make_solution_entry(
        "ebf-redux",
        ModSolutionCriteria::Any(vec!["EveryonesBestFriend".to_string()]),
        vec!["UFO4P"],
        "Everyone's Best Friend",
        "Install the compatibility patch.",
    )];
    let mut plugins = IndexMap::new();
    plugins.insert("EveryonesBestFriend.esp".to_string(), "03".to_string());
    plugins.insert("UFO4P.esp".to_string(), "04".to_string());

    let result = detect_mods_solutions(&entries, &plugins).unwrap();
    assert!(result.is_empty());
}

#[test]
fn test_detect_mods_solutions_ignores_exception_identical_to_criterion() {
    let entries = vec![make_solution_entry(
        "overlap-safe",
        ModSolutionCriteria::Any(vec!["OverlapMod".to_string()]),
        vec!["OverlapMod"],
        "Overlap Mod",
        "Still report the mod when exception equals the criterion.",
    )];
    let mut plugins = IndexMap::new();
    plugins.insert("OverlapMod.esp".to_string(), "05".to_string());

    let result = detect_mods_solutions(&entries, &plugins).unwrap();
    let output = result.join("");

    assert!(output.contains("FOUND : [05] Overlap Mod"));
    assert!(output.contains("Still report the mod"));
}

// ============================================
// detect_mods_double tests
// ============================================

fn make_conflict(mod_a: &str, mod_b: &str) -> ModConflictEntry {
    ModConflictEntry {
        mod_a: mod_a.to_string(),
        mod_b: mod_b.to_string(),
        name_a: format!("Mod {}", mod_a),
        name_b: format!("Mod {}", mod_b),
        description: "These mods conflict!".to_string(),
        fix: "Remove one of them.".to_string(),
        link: None,
    }
}

// Keep detect_mods_double coverage serial so shared matcher compile counters stay scoped
// to each regression proof during grouped test runs.
#[test]
#[serial]
fn test_detect_mods_double_empty() {
    let entries: Vec<ModConflictEntry> = Vec::new();
    let plugins: IndexMap<String, String> = IndexMap::new();

    let result = detect_mods_double(&entries, plugins).unwrap();
    assert!(result.is_empty());
}

#[test]
#[serial]
fn test_detect_mods_double_no_conflict() {
    let entries = vec![make_conflict("moda", "modb")];

    let mut plugins = IndexMap::new();
    plugins.insert("ModA.esp".to_string(), "10".to_string());

    let result = detect_mods_double(&entries, plugins).unwrap();
    assert!(result.is_empty());
}

#[test]
#[serial]
fn test_detect_mods_double_conflict_detected() {
    let entries = vec![make_conflict("moda", "modb")];

    let mut plugins = IndexMap::new();
    plugins.insert("ModA.esp".to_string(), "10".to_string());
    plugins.insert("ModB.esp".to_string(), "11".to_string());

    let result = detect_mods_double(&entries, plugins).unwrap();
    assert!(!result.is_empty());
    let output = result.join("");
    assert!(output.contains("CAUTION"));
    assert!(output.contains("CONFLICTS WITH"));
}

#[test]
#[serial]
fn test_detect_mods_double_case_insensitive() {
    let entries = vec![make_conflict("moda", "modb")];

    let mut plugins = IndexMap::new();
    plugins.insert("MODA.esp".to_string(), "10".to_string());
    plugins.insert("MODB.esp".to_string(), "11".to_string());

    let result = detect_mods_double(&entries, plugins).unwrap();
    assert!(!result.is_empty());
}

#[test]
#[serial]
fn test_detect_mods_double_with_link() {
    let entries = vec![ModConflictEntry {
        mod_a: "modx".to_string(),
        mod_b: "mody".to_string(),
        name_a: "Mod X".to_string(),
        name_b: "Mod Y".to_string(),
        description: "They clash.".to_string(),
        fix: "Get a patch.".to_string(),
        link: Some("https://example.com/patch".to_string()),
    }];

    let mut plugins = IndexMap::new();
    plugins.insert("ModX.esp".to_string(), "10".to_string());
    plugins.insert("ModY.esp".to_string(), "11".to_string());

    let result = detect_mods_double(&entries, plugins).unwrap();
    let output = result.join("");
    assert!(output.contains("https://example.com/patch"));
}

#[test]
#[serial]
fn test_detect_mods_double_multiple_conflicts_single_header() {
    let entries = vec![make_conflict("moda", "modb"), make_conflict("modc", "modd")];

    let mut plugins = IndexMap::new();
    plugins.insert("ModA.esp".to_string(), "10".to_string());
    plugins.insert("ModB.esp".to_string(), "11".to_string());
    plugins.insert("ModC.esp".to_string(), "12".to_string());
    plugins.insert("ModD.esp".to_string(), "13".to_string());

    let result = detect_mods_double(&entries, plugins).unwrap();
    let output = result.join("");

    // Header must appear exactly once, not per-conflict
    assert_eq!(
        output
            .matches("[!] CAUTION : Conflicting mods detected")
            .count(),
        1,
        "CAUTION header should appear exactly once, not per conflict"
    );

    // Both conflict pairs must still be reported
    assert!(output.contains("Mod moda"));
    assert!(output.contains("Mod modb"));
    assert!(output.contains("Mod modc"));
    assert!(output.contains("Mod modd"));
    assert_eq!(
        output.matches("CONFLICTS WITH").count(),
        2,
        "Both conflict pairs should be reported"
    );
}

#[test]
#[serial]
fn test_detect_mods_double_reuses_cached_matcher_for_same_conflict_set() {
    let entries = vec![
        make_conflict("repeat-double-a", "repeat-double-b"),
        make_conflict("repeat-double-c", "repeat-double-d"),
    ];

    reset_matcher_caches_for_tests();
    let starting_compiles = double_compile_snapshot_for_tests();

    let first = double_matcher_for_tests(&entries).unwrap();
    let second = double_matcher_for_tests(&entries).unwrap();

    assert!(Arc::ptr_eq(&first, &second));
    assert_eq!(double_compile_count_for_tests() - starting_compiles, 1);
}

// ============================================
// detect_mods_important tests
// ============================================

fn make_core_entry(detect: &str, name: &str, desc: &str) -> CoreModEntry {
    CoreModEntry {
        detect: detect.to_string(),
        name: name.to_string(),
        description: desc.to_string(),
        gpu: None,
        gpu_mismatch_warning: None,
        exclude_when: None,
    }
}

fn important_fixture_plugins() -> IndexMap<String, String> {
    let parser = LogParser::new(None).expect("fixture parser should build");
    let fixture_lines: Vec<StdArc<str>> = IMPORTANT_MODS_FIXTURE_LOG
        .lines()
        .map(StdArc::<str>::from)
        .collect();
    let sections = parser.parse_all_sections_arc(&fixture_lines);
    let plugin_lines: Vec<String> = sections
        .get(segment_key::PLUGINS)
        .expect("fixture should include a plugins section")
        .iter()
        .map(|line| line.to_string())
        .collect();
    let analyzer = PluginAnalyzer::new(
        vec![],
        vec![],
        "Buffout 4".to_string(),
        "1.10.163".to_string(),
        "1.2.72".to_string(),
    )
    .expect("fixture plugin analyzer should build");
    let (plugins, _limit_triggered, _limit_disabled) = analyzer
        .loadorder_scan_log(&plugin_lines, None, None)
        .expect("fixture plugins should parse");
    assert!(
        plugins.contains_key("DLCUltraHighResolution.esm"),
        "fixture should contain a known plugin exercised by parity coverage"
    );
    plugins
}

fn parity_fixture_entries() -> Vec<CoreModEntry> {
    vec![
        make_core_entry(
            "DLCUltraHighResolution.esm",
            "High Resolution DLC",
            "Disable the official texture pack.\nIt causes crashes and stutter.",
        ),
        CoreModEntry {
            detect: "skip-me.esp".to_string(),
            name: "Skipped Entry".to_string(),
            description: "This line should stay excluded.".to_string(),
            gpu: None,
            gpu_mismatch_warning: None,
            exclude_when: Some(CoreModExclude::PluginAny(vec![
                "DLCUltraHighResolution.esm".to_string(),
            ])),
        },
        make_core_entry(
            "EngineFixes.esp",
            "Engine Fixes",
            "Highly recommended for stability.\nLink: https://example.com/mod",
        ),
    ]
}

#[test]
fn test_detect_mods_important_fixture_parity_matches_legacy_and_aho_paths() {
    let entries = parity_fixture_entries();
    let plugins = important_fixture_plugins();
    let xse_modules: HashSet<String> = HashSet::new();

    let legacy =
        detect_mods_important_legacy(&entries, &plugins, Some("amd"), &xse_modules).unwrap();
    let aho = detect_mods_important_aho(&entries, &plugins, Some("amd"), &xse_modules).unwrap();

    assert_eq!(aho, legacy);
}

#[test]
fn test_detect_mods_important_aho_prefers_leftmost_longest_overlap_match() {
    let entries = vec![
        make_core_entry("f4se", "Short Match", "Short overlap should lose."),
        make_core_entry(
            "f4se_plugin_preloader",
            "Long Match",
            "Long overlap should win.",
        ),
    ];
    let plugins: IndexMap<String, String> = IndexMap::new();
    let xse_modules = HashSet::from(["f4se_plugin_preloader.dll".to_string()]);

    let output = detect_mods_important_aho(&entries, &plugins, None, &xse_modules)
        .unwrap()
        .join("");

    assert!(output.contains("Long Match is installed"));
    assert!(!output.contains("Short Match is installed"));
}

#[test]
fn test_detect_mods_important_reuses_cached_matcher_for_same_detect_literals() {
    let entries = vec![
        make_core_entry(
            "bakascrapheap",
            "Baka ScrapHeap",
            "Synthetic important-mod literal benchmark token.",
        ),
        make_core_entry(
            "x-cell-fo4.dll",
            "X-Cell",
            "Synthetic XSE-module benchmark token.",
        ),
    ];

    reset_matcher_caches_for_tests();
    let starting_compiles = important_compile_count_for_tests();

    let first = important_matcher_for_tests(&entries).unwrap();
    let second = important_matcher_for_tests(&entries).unwrap();

    assert!(Arc::ptr_eq(&first, &second));
    assert!(important_compile_count_for_tests() > starting_compiles);
}

#[test]
fn test_detect_mods_important_fixture_entries_keep_gpu_exclude_and_not_installed_quirks() {
    let plugins = important_fixture_plugins();
    let xse_modules: HashSet<String> = HashSet::new();
    let entries = vec![
        CoreModEntry {
            detect: "DLCUltraHighResolution.esm".to_string(),
            name: "NVIDIA High Resolution DLC".to_string(),
            description: "For NVIDIA GPUs only!".to_string(),
            gpu: Some("nvidia".to_string()),
            gpu_mismatch_warning: None,
            exclude_when: None,
        },
        CoreModEntry {
            detect: "skip-me.esp".to_string(),
            name: "Skipped Entry".to_string(),
            description: "This line should stay excluded.".to_string(),
            gpu: None,
            gpu_mismatch_warning: None,
            exclude_when: Some(CoreModExclude::PluginAny(vec![
                "DLCUltraHighResolution.esm".to_string(),
            ])),
        },
        make_core_entry(
            "EngineFixes.esp",
            "Engine Fixes",
            "Highly recommended for stability.\nLink: https://example.com/mod",
        ),
    ];

    let output = detect_mods_important_aho(&entries, &plugins, Some("amd"), &xse_modules)
        .unwrap()
        .join("");

    assert!(output.contains("❓ NVIDIA High Resolution DLC is installed"));
    assert!(!output.contains("Skipped Entry"));
    assert!(
        output.contains("❌ Engine Fixes is not installed! Highly recommended for stability.")
    );
    assert!(output.contains("Link: https://example.com/mod"));
}

#[test]
fn test_detect_mods_important_fixture_detect_values_match_as_literals_not_regex() {
    let entries = vec![make_core_entry(
        "DLCUltraHighResolution.esm",
        "High Resolution DLC",
        "Literal dots should stay literal.",
    )];
    let mut plugins = IndexMap::new();
    plugins.insert("DLCUltraHighResolutionXesm".to_string(), "01".to_string());
    let xse_modules: HashSet<String> = HashSet::new();

    let legacy = detect_mods_important_legacy(&entries, &plugins, None, &xse_modules).unwrap();
    let aho = detect_mods_important_aho(&entries, &plugins, None, &xse_modules).unwrap();

    assert!(legacy.is_empty());
    assert!(aho.is_empty());
}

#[test]
fn test_detect_mods_important_empty() {
    let entries: Vec<CoreModEntry> = vec![];
    let plugins: IndexMap<String, String> = IndexMap::new();
    let xse_modules: HashSet<String> = HashSet::new();

    let result = detect_mods_important(&entries, &plugins, None, &xse_modules).unwrap();
    assert!(result.is_empty());
}

#[test]
fn test_detect_mods_important_installed() {
    let entries = vec![make_core_entry(
        "enginefixes.esp",
        "Engine Fixes",
        "Highly recommended for stability.",
    )];

    let mut plugins = IndexMap::new();
    plugins.insert("EngineFixes.esp".to_string(), "05".to_string());
    let xse_modules: HashSet<String> = HashSet::new();

    let result = detect_mods_important(&entries, &plugins, None, &xse_modules).unwrap();
    let output = result.join("");
    assert!(output.contains("✔️"));
    assert!(output.contains("Engine Fixes"));
    assert!(output.contains("installed"));
}

#[test]
fn test_detect_mods_important_not_installed() {
    let entries = vec![make_core_entry(
        "enginefixes.esp",
        "Engine Fixes",
        "Highly recommended for stability.\nLink: https://example.com/mod",
    )];

    let plugins: IndexMap<String, String> = IndexMap::new();
    let xse_modules: HashSet<String> = HashSet::new();

    // user_gpu is known → "not installed" warnings are shown for universal mods
    let result = detect_mods_important(&entries, &plugins, Some("amd"), &xse_modules).unwrap();
    let output = result.join("");
    assert!(output.contains("❌"));
    assert!(output.contains("Engine Fixes"));
    assert!(output.contains("not installed"));

    // Description text should be on the same line as the "not installed" message
    assert!(
        output.contains("not installed! Highly recommended"),
        "Description should follow the not-installed message on the same line"
    );

    // Link must appear on its own line (after a hard line break)
    assert!(
        output.contains("  \nLink: https://example.com/mod"),
        "Link should be on a new line via hard line break, got: {:?}",
        output
    );

    let result_no_gpu = detect_mods_important(&entries, &plugins, None, &xse_modules).unwrap();
    assert!(result_no_gpu.is_empty());
}

#[test]
fn test_detect_mods_important_gpu_mismatch() {
    let entries = vec![CoreModEntry {
        detect: "nvidiapatch.esp".to_string(),
        name: "NVIDIA Patch".to_string(),
        description: "For NVIDIA GPUs only!".to_string(),
        gpu: Some("nvidia".to_string()),
        gpu_mismatch_warning: None,
        exclude_when: None,
    }];

    let mut plugins = IndexMap::new();
    plugins.insert("NvidiaPatch.esp".to_string(), "10".to_string());
    let xse_modules: HashSet<String> = HashSet::new();

    // User has AMD, nvidia mod is installed → mismatch warning
    let result = detect_mods_important(&entries, &plugins, Some("amd"), &xse_modules).unwrap();
    let output = result.join("");
    assert!(output.contains("❓"));
    assert!(output.contains("UNINSTALL"));
}

#[test]
fn test_detect_mods_important_xse_module() {
    let entries = vec![
        make_core_entry("someplugin.esp", "Some Plugin", "A plugin."),
        make_core_entry(
            "addresslib.dll",
            "Address Library",
            "Required for many F4SE plugins.",
        ),
    ];

    let mut plugins = IndexMap::new();
    plugins.insert("SomePlugin.esp".to_string(), "05".to_string());

    let mut xse_modules = HashSet::new();
    xse_modules.insert("AddressLibrary.dll".to_string());

    let result = detect_mods_important(&entries, &plugins, None, &xse_modules).unwrap();
    let output = result.join("");
    assert!(output.contains("✔️"));
    assert!(output.contains("installed"));
}

#[test]
fn test_detect_mods_important_no_leading_newline_before_first_entry() {
    let entries = vec![make_core_entry(
        "enginefixes.esp",
        "Engine Fixes",
        "Highly recommended for stability.",
    )];

    let mut plugins = IndexMap::new();
    plugins.insert("EngineFixes.esp".to_string(), "05".to_string());
    let xse_modules: HashSet<String> = HashSet::new();

    let result = detect_mods_important(&entries, &plugins, None, &xse_modules).unwrap();
    let output = result.join("");
    assert!(!output.starts_with('\n'));
    assert!(output.starts_with("✔️ "));
}

#[test]
fn test_detect_mods_important_exclude_when_plugin_any() {
    let entries = vec![CoreModEntry {
        detect: "UFO4P.esp".to_string(),
        name: "Unofficial Patch".to_string(),
        description: "Install this patch.".to_string(),
        gpu: None,
        gpu_mismatch_warning: None,
        exclude_when: Some(CoreModExclude::PluginAny(vec![
            "LondonWorldspace.esm".to_string(),
        ])),
    }];

    let mut plugins_without_folon = IndexMap::new();
    plugins_without_folon.insert("SomeMod.esp".to_string(), "01".to_string());
    let xse_modules: HashSet<String> = HashSet::new();

    let result =
        detect_mods_important(&entries, &plugins_without_folon, Some("amd"), &xse_modules)
            .unwrap();
    assert!(
        !result.is_empty(),
        "Entry should be shown when exclusion plugin is absent"
    );

    let mut plugins_with_folon = IndexMap::new();
    plugins_with_folon.insert("LondonWorldspace.esm".to_string(), "01".to_string());

    let result =
        detect_mods_important(&entries, &plugins_with_folon, Some("amd"), &xse_modules)
            .unwrap();
    assert!(
        result.is_empty(),
        "Entry should be skipped when exclusion plugin is present"
    );
}

#[test]
fn test_detect_mods_important_exclude_when_plugin_any_is_case_insensitive() {
    let entries = vec![CoreModEntry {
        detect: "UFO4P.esp".to_string(),
        name: "Unofficial Patch".to_string(),
        description: "Install this patch.".to_string(),
        gpu: None,
        gpu_mismatch_warning: None,
        exclude_when: Some(CoreModExclude::PluginAny(vec![
            "londonworldspace.esm".to_string(),
        ])),
    }];

    let mut plugins = IndexMap::new();
    plugins.insert("LondonWorldspace.esm".to_string(), "01".to_string());
    let xse_modules: HashSet<String> = HashSet::new();

    let result = detect_mods_important(&entries, &plugins, Some("amd"), &xse_modules).unwrap();
    assert!(
        result.is_empty(),
        "Entry should be skipped even when exclusion plugin casing differs"
    );
}

#[test]
fn test_detect_mods_important_gpu_not_rival_shows_installed() {
    let entries = vec![CoreModEntry {
        detect: "nvidiapatch.esp".to_string(),
        name: "NVIDIA Patch".to_string(),
        description: "For NVIDIA GPUs only!".to_string(),
        gpu: Some("nvidia".to_string()),
        gpu_mismatch_warning: None,
        exclude_when: None,
    }];

    let mut plugins = IndexMap::new();
    plugins.insert("NvidiaPatch.esp".to_string(), "10".to_string());
    let xse_modules: HashSet<String> = HashSet::new();

    // User has NVIDIA, mod is for nvidia -> shows installed
    let result =
        detect_mods_important(&entries, &plugins, Some("nvidia"), &xse_modules).unwrap();
    let output = result.join("");
    assert!(output.contains("✔️"));
    assert!(output.contains("installed"));
}

#[test]
fn test_detect_mods_important_custom_gpu_mismatch_warning() {
    let entries = vec![CoreModEntry {
        detect: "nvidiapatch.esp".to_string(),
        name: "NVIDIA Patch".to_string(),
        description: "For NVIDIA GPUs only!".to_string(),
        gpu: Some("nvidia".to_string()),
        gpu_mismatch_warning: Some(
            "Custom warning: you don't have NVIDIA, remove this mod!".to_string(),
        ),
        exclude_when: None,
    }];

    let mut plugins = IndexMap::new();
    plugins.insert("NvidiaPatch.esp".to_string(), "10".to_string());
    let xse_modules: HashSet<String> = HashSet::new();

    // User has AMD, nvidia mod is installed → custom mismatch warning
    let result = detect_mods_important(&entries, &plugins, Some("amd"), &xse_modules).unwrap();
    let output = result.join("");
    assert!(output.contains("❓"));
    assert!(output.contains("Custom warning: you don't have NVIDIA"));
    assert!(!output.contains("BUT IT SEEMS"));
}

// ============================================
// detect_mods_batch tests
// ============================================

#[test]
fn test_detect_mods_batch_empty() {
    let yaml_dict: IndexMap<String, String> = IndexMap::new();
    let logs: Vec<IndexMap<String, String>> = vec![];

    let result = detect_mods_batch(yaml_dict, logs).unwrap();
    assert!(result.is_empty());
}

#[test]
fn test_detect_mods_batch_empty_yaml() {
    let yaml_dict: IndexMap<String, String> = IndexMap::new();
    let mut log1 = IndexMap::new();
    log1.insert("Mod.esp".to_string(), "01".to_string());

    let result = detect_mods_batch(yaml_dict, vec![log1]).unwrap();
    assert_eq!(result.len(), 1);
    assert!(result[0].is_empty());
}

#[test]
fn test_detect_mods_batch_single_log() {
    let mut yaml_dict = IndexMap::new();
    yaml_dict.insert(
        "testmod".to_string(),
        "Test Mod\nWarning message.".to_string(),
    );

    let mut log1 = IndexMap::new();
    log1.insert("TestMod.esp".to_string(), "10".to_string());

    let result = detect_mods_batch(yaml_dict, vec![log1]).unwrap();
    assert_eq!(result.len(), 1);
    assert!(!result[0].is_empty());
}

#[test]
fn test_detect_mods_batch_multiple_logs() {
    let mut yaml_dict = IndexMap::new();
    yaml_dict.insert(
        "badmod".to_string(),
        "Bad Mod\nThis is problematic.".to_string(),
    );

    let mut log1 = IndexMap::new();
    log1.insert("BadMod.esp".to_string(), "10".to_string());

    let mut log2 = IndexMap::new();
    log2.insert("GoodMod.esp".to_string(), "05".to_string());

    let mut log3 = IndexMap::new();
    log3.insert("BadMod.esp".to_string(), "12".to_string());

    let result = detect_mods_batch(yaml_dict, vec![log1, log2, log3]).unwrap();
    assert_eq!(result.len(), 3);
    assert!(!result[0].is_empty()); // Has BadMod
    assert!(result[1].is_empty()); // No BadMod
    assert!(!result[2].is_empty()); // Has BadMod
}

#[test]
fn test_detect_mods_batch_preserves_order() {
    let mut yaml_dict = IndexMap::new();
    yaml_dict.insert("mod1".to_string(), "Mod 1\nWarning 1.".to_string());
    yaml_dict.insert("mod2".to_string(), "Mod 2\nWarning 2.".to_string());

    let mut log1 = IndexMap::new();
    log1.insert("Mod1.esp".to_string(), "01".to_string());

    let mut log2 = IndexMap::new();
    log2.insert("Mod2.esp".to_string(), "02".to_string());

    let result = detect_mods_batch(yaml_dict, vec![log1, log2]).unwrap();
    assert_eq!(result.len(), 2);

    // First result should be about Mod1
    let output1 = result[0].join("");
    assert!(output1.contains("[01]") || output1.contains("Mod 1"));

    // Second result should be about Mod2
    let output2 = result[1].join("");
    assert!(output2.contains("[02]") || output2.contains("Mod 2"));
}

#[test]
#[serial]
fn test_detect_mods_batch_reuses_cached_matcher_across_repeated_invocations() {
    let mut yaml_dict = IndexMap::new();
    yaml_dict.insert(
        "repeatable-batch".to_string(),
        "Repeatable Batch\nFirst warning.".to_string(),
    );
    yaml_dict.insert(
        "repeatable-batch-extended".to_string(),
        "Repeatable Batch Extended\nSecond warning.".to_string(),
    );

    let mut log1 = IndexMap::new();
    log1.insert("Repeatable-Batch.esp".to_string(), "0A".to_string());

    let mut log2 = IndexMap::new();
    log2.insert(
        "Repeatable-Batch-Extended.esp".to_string(),
        "0B".to_string(),
    );

    let logs = vec![log1, log2];

    reset_matcher_caches_for_tests();

    let first = detect_mods_batch(yaml_dict.clone(), logs.clone()).unwrap();
    let cached_after_first = batch_matcher_for_tests(&yaml_dict).unwrap();
    let second = detect_mods_batch(yaml_dict.clone(), logs.clone()).unwrap();
    let cached_after_second = batch_matcher_for_tests(&yaml_dict).unwrap();

    assert_eq!(first, second);
    assert!(Arc::ptr_eq(&cached_after_first, &cached_after_second));
}
