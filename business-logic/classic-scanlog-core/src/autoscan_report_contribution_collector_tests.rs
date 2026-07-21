use std::collections::HashSet;

use classic_config_core::{ConfigLayout, CrashgenSettingsSnapshot};
use classic_database_core::{
    FormIdValueLookup, FormIdValueLookupEntry, FormIdValueLookupInMemoryReply,
};
use indexmap::IndexMap;

use super::*;
use crate::CrashgenEntry;
use crate::formid_finding_analyzer::FormIDValueLookupStatus;

struct AnalyzerFixture {
    crashgen_settings: CrashgenSettingsAnalyzer,
    crash_suspects: CrashSuspectAnalyzer,
    mod_guidance: ModGuidanceAnalyzer,
    plugin_evidence: PluginEvidenceAnalyzer,
    formid_findings: FormIDFindingAnalyzer,
    named_record_findings: NamedRecordFindingAnalyzer,
}

impl AnalyzerFixture {
    /// Builds a complete immutable analyzer set with the selected FormID lookup behavior.
    fn new(formid_lookup: FormIdValueLookup) -> Self {
        Self {
            crashgen_settings: CrashgenSettingsAnalyzer::new(
                "Buffout 4".to_string(),
                CrashgenEntry::default_entry(),
            )
            .expect("Crashgen Settings Analyzer fixture should build"),
            crash_suspects: CrashSuspectAnalyzer::new(Vec::new(), Vec::new())
                .expect("Crash Suspect Analyzer fixture should build"),
            mod_guidance: ModGuidanceAnalyzer::new(Vec::new(), Vec::new(), Vec::new(), Vec::new())
                .expect("Mod Guidance Analyzer fixture should build"),
            plugin_evidence: PluginEvidenceAnalyzer::new(Vec::new())
                .expect("Plugin Evidence Analyzer fixture should build"),
            formid_findings: FormIDFindingAnalyzer::new(formid_lookup),
            named_record_findings: NamedRecordFindingAnalyzer::new(
                vec!["target".to_string()],
                Vec::new(),
            )
            .expect("Named Record Finding Analyzer fixture should build"),
        }
    }

    fn collector(&self) -> AutoscanReportContributionCollector<'_> {
        AutoscanReportContributionCollector::new(
            &self.crashgen_settings,
            &self.crash_suspects,
            &self.mod_guidance,
            &self.plugin_evidence,
            &self.formid_findings,
            Some(&self.named_record_findings),
        )
    }
}

#[test]
fn collection_distinguishes_not_performed_from_always_performed_empty_analysis() {
    let fixture = AnalyzerFixture::new(FormIdValueLookup::disabled());
    let collector = fixture.collector();
    let settings = CrashgenSettingsSnapshot::new();
    let xse_modules = HashSet::new();
    let plugins = None::<&IndexMap<String, String>>;
    let result = classic_shared_core::get_runtime()
        .block_on(collector.collect(AutoscanReportCollectionInput {
            crashgen_settings: &settings,
            xse_modules: &xse_modules,
            crashgen_version: None,
            config_layout: ConfigLayout::Unknown,
            fake_bot_compatible_mode: false,
            main_error: "ordinary main error",
            combined_crash_lines: &[],
            combined_crash_text: "",
            system_segment_lines: &[],
            plugins,
        }))
        .expect("gated collection should succeed");

    assert!(result.crashgen_settings.is_none());
    assert_eq!(
        result.crash_suspects,
        Some(CrashSuspectAnalysisResult::default())
    );
    assert!(result.mod_guidance.is_none());
    assert!(result.plugin_evidence.is_none());
    assert!(result.formid_findings.is_none());
    assert!(result.named_record_findings.is_none());
    assert_eq!(result.suspect_count(), 0);
    assert_eq!(result.formid_count(), 0);
}

#[test]
fn applicable_analyses_retain_present_empty_results() {
    let fixture = AnalyzerFixture::new(FormIdValueLookup::disabled());
    let collector = fixture.collector();
    let mut settings = CrashgenSettingsSnapshot::new();
    settings.insert("General", "Enabled", "true");
    let xse_modules = HashSet::new();
    let combined_crash_lines = vec!["ordinary crash evidence".to_string()];
    let plugins = IndexMap::from([("unused.esp".to_string(), "01".to_string())]);
    let input = AutoscanReportCollectionInput {
        crashgen_settings: &settings,
        xse_modules: &xse_modules,
        crashgen_version: None,
        config_layout: ConfigLayout::Unknown,
        fake_bot_compatible_mode: false,
        main_error: "ordinary main error",
        combined_crash_lines: &combined_crash_lines,
        combined_crash_text: "ordinary crash evidence",
        system_segment_lines: &[],
        plugins: Some(&plugins),
    };
    let result = classic_shared_core::get_runtime()
        .block_on(collector.collect(input))
        .expect("applicable empty analyses should succeed");

    assert_eq!(
        result.crashgen_settings,
        Some(CrashgenSettingsAnalysisResult::default())
    );
    assert_eq!(
        result.crash_suspects,
        Some(CrashSuspectAnalysisResult::default())
    );
    assert_eq!(
        result.mod_guidance,
        Some(ModGuidanceAnalysisResult::default())
    );
    assert_eq!(
        result.plugin_evidence,
        Some(PluginEvidenceAnalysisResult::default())
    );
    assert_eq!(
        result.formid_findings,
        Some(FormIDFindingAnalysisResult::default())
    );
    assert_eq!(
        result.named_record_findings,
        Some(NamedRecordFindingAnalysisResult::default())
    );

    let fake_mode = classic_shared_core::get_runtime()
        .block_on(collector.collect(AutoscanReportCollectionInput {
            fake_bot_compatible_mode: true,
            ..input
        }))
        .expect("fake bot-compatible mode should skip settings without failing");
    assert!(fake_mode.crashgen_settings.is_none());
}

#[test]
fn formid_operational_failure_preserves_findings_without_value_enrichment() {
    let lookup = FormIdValueLookup::in_memory(vec![FormIdValueLookupEntry::new(
        "123456",
        "Broken.esp",
        FormIdValueLookupInMemoryReply::OperationalFailure("fixture offline".to_string()),
    )]);
    let fixture = AnalyzerFixture::new(lookup);
    let collector = fixture.collector();
    let settings = CrashgenSettingsSnapshot::new();
    let xse_modules = HashSet::new();
    let combined_crash_lines = vec!["Form ID: 0x01123456".to_string()];
    let plugins = IndexMap::from([("Broken.esp".to_string(), "01".to_string())]);
    let result = classic_shared_core::get_runtime()
        .block_on(collector.collect(AutoscanReportCollectionInput {
            crashgen_settings: &settings,
            xse_modules: &xse_modules,
            crashgen_version: None,
            config_layout: ConfigLayout::Unknown,
            fake_bot_compatible_mode: false,
            main_error: "ordinary main error",
            combined_crash_lines: &combined_crash_lines,
            combined_crash_text: "Form ID: 0x01123456",
            system_segment_lines: &[],
            plugins: Some(&plugins),
        }))
        .expect("an optional FormID lookup failure must not abort report collection");

    assert_eq!(result.formid_count(), 1);
    let findings = result
        .formid_findings
        .as_ref()
        .expect("FormID suspects should remain available")
        .findings
        .as_slice();
    assert_eq!(findings.len(), 1);
    assert_eq!(findings[0].identifier, "01123456");
    assert_eq!(findings[0].occurrences, 1);
    assert_eq!(findings[0].plugin.as_deref(), Some("Broken.esp"));
    assert_eq!(
        findings[0].value_lookup_status,
        FormIDValueLookupStatus::Disabled
    );
    assert!(findings[0].value.is_none());
}

#[test]
fn formid_malformed_lookup_result_preserves_findings_without_value_enrichment() {
    let lookup = FormIdValueLookup::in_memory(vec![FormIdValueLookupEntry::new(
        "123456",
        "Broken.esp",
        FormIdValueLookupInMemoryReply::Value(Some("   ".to_string())),
    )]);
    let fixture = AnalyzerFixture::new(lookup);
    let collector = fixture.collector();
    let settings = CrashgenSettingsSnapshot::new();
    let xse_modules = HashSet::new();
    let combined_crash_lines = vec!["Form ID: 0x01123456".to_string()];
    let plugins = IndexMap::from([("Broken.esp".to_string(), "01".to_string())]);
    let result = classic_shared_core::get_runtime()
        .block_on(collector.collect(AutoscanReportCollectionInput {
            crashgen_settings: &settings,
            xse_modules: &xse_modules,
            crashgen_version: None,
            config_layout: ConfigLayout::Unknown,
            fake_bot_compatible_mode: false,
            main_error: "ordinary main error",
            combined_crash_lines: &combined_crash_lines,
            combined_crash_text: "Form ID: 0x01123456",
            system_segment_lines: &[],
            plugins: Some(&plugins),
        }))
        .expect("a malformed optional lookup reply must not abort report collection");

    assert_eq!(result.formid_count(), 1);
    let finding = &result
        .formid_findings
        .as_ref()
        .expect("FormID suspects should remain available")
        .findings[0];
    assert_eq!(finding.identifier, "01123456");
    assert_eq!(finding.plugin.as_deref(), Some("Broken.esp"));
    assert_eq!(
        finding.value_lookup_status,
        FormIDValueLookupStatus::Disabled
    );
    assert!(finding.value.is_none());
}

#[test]
fn immutable_collector_reuse_is_deterministic_sequentially_and_concurrently() {
    let fixture = AnalyzerFixture::new(FormIdValueLookup::disabled());
    let collector = fixture.collector();
    let settings = CrashgenSettingsSnapshot::new();
    let xse_modules = HashSet::new();
    let combined_crash_lines = vec!["Example.esp Form ID: 0x01123456".to_string()];
    let plugins = IndexMap::from([("Example.esp".to_string(), "01".to_string())]);
    let input = AutoscanReportCollectionInput {
        crashgen_settings: &settings,
        xse_modules: &xse_modules,
        crashgen_version: None,
        config_layout: ConfigLayout::Unknown,
        fake_bot_compatible_mode: false,
        main_error: "Unhandled exception in example.dll",
        combined_crash_lines: &combined_crash_lines,
        combined_crash_text: "Example.esp Form ID: 0x01123456",
        system_segment_lines: &[],
        plugins: Some(&plugins),
    };

    let (first, second, concurrent_left, concurrent_right) = classic_shared_core::get_runtime()
        .block_on(async {
            let first = collector
                .collect(input)
                .await
                .expect("first sequential collection should succeed");
            let second = collector
                .collect(input)
                .await
                .expect("second sequential collection should succeed");
            let (left, right) = tokio::join!(collector.collect(input), collector.collect(input));
            (
                first,
                second,
                left.expect("left concurrent collection should succeed"),
                right.expect("right concurrent collection should succeed"),
            )
        });

    assert_eq!(first, second);
    assert_eq!(first, concurrent_left);
    assert_eq!(first, concurrent_right);
    assert_eq!(first.suspect_count(), 1);
    assert_eq!(first.formid_count(), 1);
}
