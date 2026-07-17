//! Private canonical Autoscan Report assembly and persistence helpers.
//!
//! Semantic analyzers do not depend on this presentation layer. The complete
//! Crash Log Scan Run is the only public operation that reaches this module.

// Error types not needed in pure Rust - using standard Result
use crate::autoscan_report_contribution_collector::AutoscanReportContributions;
use crate::crash_suspect_analyzer::{CrashSuspectAnalysisResult, CrashSuspectFinding};
use crate::crashgen_settings_analyzer::{
    CrashgenExpectationOutcome, CrashgenSettingsAnalysisResult, DisabledSettingNotice,
};
use crate::error::{Result, ScanLogError};
use crate::formid_finding_analyzer::FormIDFindingAnalysisResult;
use crate::mod_guidance_analyzer::{
    ImportantModGuidance, ModGuidanceAnalysisResult, ModGuidanceMatchState, ModSolutionGuidance,
};
use crate::named_record_finding_analyzer::NamedRecordFindingAnalysisResult;
use crate::plugin_evidence_analyzer::PluginEvidenceAnalysisResult;
use crate::scan_run::CrashLogScanSetupResult;
use crate::version::CrashgenVersionStatus;
use classic_config_core::{AutoscanReportPlacement, OutcomeKind, RuleSeverity};
use classic_file_io_core::FileIOCore;
use std::path::{Path, PathBuf};
use std::sync::Arc;

/// Build the Autoscan Report path for a Crash Log path.
pub(crate) fn autoscan_report_path(log_path: &Path) -> PathBuf {
    let stem = log_path
        .file_stem()
        .and_then(|stem| stem.to_str())
        .unwrap_or("unknown");
    log_path.with_file_name(format!("{stem}-AUTOSCAN.md"))
}

/// Write an Autoscan Report using the shared file I/O contract.
pub(crate) async fn write_autoscan_report(
    file_io: &FileIOCore,
    log_path: &Path,
    report_lines: &[String],
) -> Result<PathBuf> {
    let autoscan_path = autoscan_report_path(log_path);
    let content = report_lines.join("");
    file_io
        .write_file(&autoscan_path, &content)
        .await
        .map_err(|error| {
            ScanLogError::ReportError(format!(
                "Failed to write report {}: {}",
                autoscan_path.display(),
                error
            ))
        })?;
    Ok(autoscan_path)
}

/// Returns the legacy Crash Suspect source-group order owned by report assembly.
fn crash_suspect_kind_rank(finding: &CrashSuspectFinding) -> u8 {
    match finding {
        CrashSuspectFinding::MainErrorRule { .. } => 0,
        CrashSuspectFinding::StackRule { .. } => 1,
        CrashSuspectFinding::DllInvolvement => 2,
    }
}

/// Returns authored rule ordering facts when the finding came from a rule.
fn crash_suspect_rule_order(finding: &CrashSuspectFinding) -> Option<(i32, &str)> {
    match finding {
        CrashSuspectFinding::MainErrorRule { name, severity, .. }
        | CrashSuspectFinding::StackRule { name, severity, .. } => Some((*severity, name)),
        CrashSuspectFinding::DllInvolvement => None,
    }
}

/// Parses regular and light-plugin identifiers into the canonical report sort key.
fn parse_plugin_id_for_sort(plugin_id: &str) -> (bool, u32) {
    let id = plugin_id.to_uppercase();
    if id.starts_with("FE") && id.len() > 2 {
        (true, u32::from_str_radix(&id[2..], 16).unwrap_or(0))
    } else {
        (false, u32::from_str_radix(&id, 16).unwrap_or(0))
    }
}

/// Appends the legacy found-entry presentation for one semantic guidance item.
fn append_mod_found_entry(lines: &mut Vec<String>, plugin_ids: &[String], title: &str, body: &str) {
    let plugin_list = plugin_ids
        .iter()
        .map(|plugin_id| format!("[{plugin_id}]"))
        .collect::<Vec<_>>()
        .join(", ");
    lines.push(format!(
        "**[!] FOUND : {plugin_list} {}**\n\n",
        title.trim()
    ));
    for line in body.lines() {
        if line.trim().is_empty() {
            lines.push("  \n".to_string());
        } else {
            lines.push(format!("{line}  \n"));
        }
    }
}

/// Per-log facts that affect Autoscan Report rendering.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct AutoscanReportFacts {
    pub classic_version: String,
    pub crashlog_filename: String,
    pub main_error: String,
    pub crashgen_name: String,
    pub crashgen_version: String,
    pub crashgen_status: Option<CrashgenVersionStatus>,
    pub fake_bot_compatible_mode: bool,
    pub fcx_setup: Option<Arc<CrashLogScanSetupResult>>,
}

/// Semantic Mod Guidance groups rendered in the canonical Autoscan Report order.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum ModGuidanceGroup {
    MayConflict,
    FrequentCrashes,
    HasSolutions,
    ImportantMods,
}

/// Deep module for canonical Autoscan Report assembly.
pub(crate) struct AutoscanReportAssembler;

impl Default for AutoscanReportAssembler {
    fn default() -> Self {
        Self::new()
    }
}

impl AutoscanReportAssembler {
    pub(crate) fn new() -> Self {
        Self
    }

    /// Renders one typed aggregate in the canonical Autoscan Report section order.
    ///
    /// Optional results preserve the collector's performed-versus-not-run distinction;
    /// the assembler alone decides whether completed-empty results produce report text.
    pub(crate) fn assemble(
        &self,
        facts: &AutoscanReportFacts,
        contributions: AutoscanReportContributions,
    ) -> Vec<String> {
        let report_gen = ReportGenerator::with_config(
            facts.classic_version.clone(),
            facts.crashgen_name.clone(),
        );
        let mut composer = ReportComposer::new();

        composer.add(report_gen.generate_header(&facts.crashlog_filename));
        composer.add(Self::append_error_information_fragments(
            report_gen.generate_error_section_with_status_and_fake_mode(
                &facts.main_error,
                &facts.crashgen_version,
                facts.crashgen_status,
                facts.fake_bot_compatible_mode,
            ),
            Self::error_information_fragments(contributions.crashgen_settings.as_ref()),
        ));

        let suspect_fragments =
            Self::crash_suspect_fragments(contributions.crash_suspects.as_ref());
        let found_suspect = !suspect_fragments.is_empty();
        composer.add(report_gen.generate_suspect_section_header());
        composer.add_many(suspect_fragments);
        composer.add(report_gen.generate_suspect_found_footer(found_suspect));

        if let Some(setup) = facts.fcx_setup.as_deref() {
            composer.add(Self::fcx_setup_fragment(setup));
        }

        let settings_fragments = Self::settings_fragments(
            contributions.crashgen_settings.as_ref(),
            &facts.crashgen_name,
        );
        if !settings_fragments.is_empty() {
            composer.add(report_gen.generate_settings_section_header());
            composer.add_many(settings_fragments);
        }

        for group in [
            ModGuidanceGroup::MayConflict,
            ModGuidanceGroup::FrequentCrashes,
            ModGuidanceGroup::HasSolutions,
            ModGuidanceGroup::ImportantMods,
        ] {
            let fragments =
                Self::mod_guidance_fragments(contributions.mod_guidance.as_ref(), group);
            if !fragments.is_empty() {
                composer.add(Self::mod_guidance_header(&report_gen, group));
                composer.add_many(fragments);
            }
        }

        Self::add_section_with_header(
            &mut composer,
            report_gen.generate_plugin_suspect_header(),
            Self::plugin_evidence_fragments(
                contributions.plugin_evidence.as_ref(),
                &facts.crashgen_name,
            ),
        );
        Self::add_section_with_header(
            &mut composer,
            report_gen.generate_formid_section_header(),
            Self::formid_finding_fragments(
                contributions.formid_findings.as_ref(),
                &facts.crashgen_name,
            ),
        );
        Self::add_section_with_header(
            &mut composer,
            report_gen.generate_record_section_header(),
            Self::named_record_finding_fragments(
                contributions.named_record_findings.as_ref(),
                &facts.crashgen_name,
            ),
        );

        composer.add(report_gen.generate_footer());
        composer.compose().to_list()
    }

    /// Renders present FormID Finding results while preserving absent analysis as no section.
    fn formid_finding_fragments(
        result: Option<&FormIDFindingAnalysisResult>,
        crashgen_name: &str,
    ) -> Vec<ReportFragment> {
        let Some(result) = result else {
            return Vec::new();
        };
        let lines = Self::render_formid_findings(result, crashgen_name);
        if lines.is_empty() {
            Vec::new()
        } else {
            vec![ReportFragment::from_lines(lines)]
        }
    }

    /// Owns canonical FormID sorting, resolved-value formatting, and report prose.
    fn render_formid_findings(
        result: &FormIDFindingAnalysisResult,
        crashgen_name: &str,
    ) -> Vec<String> {
        let mut findings = result
            .findings
            .iter()
            .filter(|finding| finding.plugin.is_some())
            .collect::<Vec<_>>();
        findings.sort_by(|left, right| left.identifier.cmp(&right.identifier));
        if findings.is_empty() {
            // Unresolved identifiers remain semantic evidence but are intentionally not reportable yet.
            return Vec::new();
        }
        let mut lines = findings
            .into_iter()
            .map(|finding| {
                let plugin = finding
                    .plugin
                    .as_deref()
                    .expect("resolved FormID findings always have a plugin");
                match finding.value.as_deref() {
                    Some(value) => format!(
                        "- {plugin} | {} | {value} | {}\n",
                        finding.identifier, finding.occurrences
                    ),
                    None => format!(
                        "- {plugin} | {} | {}\n",
                        finding.identifier, finding.occurrences
                    ),
                }
            })
            .collect::<Vec<_>>();
        lines.push(
            "\n[Last number counts how many times each Form ID shows up in the crash log.]\n"
                .to_string(),
        );
        lines.push(format!(
            "These Form IDs were caught by {crashgen_name} and some of them might be related to this crash.\n"
        ));
        lines.push(
            "You can try searching any listed Form IDs in xEdit and see if they lead to relevant records.\n\n"
                .to_string(),
        );
        lines
    }

    /// Renders a present Plugin Evidence result while preserving absent analysis as no section.
    fn plugin_evidence_fragments(
        result: Option<&PluginEvidenceAnalysisResult>,
        crashgen_name: &str,
    ) -> Vec<ReportFragment> {
        result
            .map(|result| {
                vec![ReportFragment::from_lines(Self::render_plugin_evidence(
                    result,
                    crashgen_name,
                ))]
            })
            .unwrap_or_default()
    }

    /// Owns canonical sorting and prose for typed Plugin Evidence.
    fn render_plugin_evidence(
        result: &PluginEvidenceAnalysisResult,
        crashgen_name: &str,
    ) -> Vec<String> {
        if result.evidence.is_empty() {
            return vec!["* COULDN'T FIND ANY PLUGIN SUSPECTS *\n\n".to_string()];
        }

        let mut evidence = result.evidence.iter().collect::<Vec<_>>();
        evidence.sort_by(|left, right| {
            right
                .occurrences
                .cmp(&left.occurrences)
                .then_with(|| left.plugin.cmp(&right.plugin))
        });
        let mut lines = vec!["The following PLUGINS were found in the CRASH STACK:\n".to_string()];
        lines.extend(
            evidence
                .into_iter()
                .map(|entry| format!("- {} | {}\n", entry.plugin, entry.occurrences)),
        );
        lines.push(
            "\n[Last number counts how many times each Plugin Suspect shows up in the crash log.]\n"
                .to_string(),
        );
        lines.push(format!(
            "These Plugins were caught by {crashgen_name} and some of them might be responsible for this crash.\n"
        ));
        lines.push(
            "You can try disabling these plugins and check if the game still crashes, though this method can be unreliable.\n\n"
                .to_string(),
        );
        lines
    }

    /// Renders a present Named Record Finding result while preserving absent analysis as no section.
    fn named_record_finding_fragments(
        result: Option<&NamedRecordFindingAnalysisResult>,
        crashgen_name: &str,
    ) -> Vec<ReportFragment> {
        result
            .map(|result| {
                vec![ReportFragment::from_lines(
                    Self::render_named_record_findings(result, crashgen_name),
                )]
            })
            .unwrap_or_default()
    }

    /// Owns canonical sorting, occurrence formatting, and prose for Named Record Findings.
    fn render_named_record_findings(
        result: &NamedRecordFindingAnalysisResult,
        crashgen_name: &str,
    ) -> Vec<String> {
        if result.findings.is_empty() {
            return vec!["* COULDN'T FIND ANY NAMED RECORDS *\n\n".to_string()];
        }

        let mut findings = result.findings.iter().collect::<Vec<_>>();
        findings.sort_by(|left, right| left.record.cmp(&right.record));
        let mut lines = findings
            .into_iter()
            .map(|finding| format!("- {} | {}\n", finding.record, finding.occurrences))
            .collect::<Vec<_>>();
        lines.push(
            "\n[Last number counts how many times each Named Record shows up in the crash log.]\n"
                .to_string(),
        );
        lines.push(format!(
            "These records were caught by {crashgen_name} and some of them might be related to this crash.\n"
        ));
        lines.push(
            "Named records should give extra info on involved game objects, record types or mod files.\n\n"
                .to_string(),
        );
        lines
    }

    fn add_section_with_header(
        composer: &mut ReportComposer,
        header: ReportFragment,
        fragments: Vec<ReportFragment>,
    ) {
        if fragments.is_empty() {
            return;
        }
        composer.add(header);
        composer.add_many(fragments);
    }

    /// Renders semantic Crash Suspect Findings at the sole presentation boundary.
    fn crash_suspect_fragments(result: Option<&CrashSuspectAnalysisResult>) -> Vec<ReportFragment> {
        let mut findings = result
            .into_iter()
            .flat_map(|result| result.findings.iter())
            .collect::<Vec<_>>();

        // The analyzer preserves semantic rule order; canonical report grouping and sorting live here.
        findings.sort_by(|left, right| {
            crash_suspect_kind_rank(left)
                .cmp(&crash_suspect_kind_rank(right))
                .then_with(|| {
                    match (
                        crash_suspect_rule_order(left),
                        crash_suspect_rule_order(right),
                    ) {
                        (Some((left_severity, left_name)), Some((right_severity, right_name))) => {
                            right_severity
                                .cmp(&left_severity)
                                .then_with(|| left_name.cmp(right_name))
                        }
                        _ => std::cmp::Ordering::Equal,
                    }
                })
        });

        findings
            .into_iter()
            .map(|finding| {
                ReportFragment::from_lines(match finding {
                    CrashSuspectFinding::MainErrorRule { name, severity, .. }
                    | CrashSuspectFinding::StackRule { name, severity, .. } => vec![
                        format!(
                            "- **Checking for {:.<width$} SUSPECT FOUND! > Severity : {}** \n\n",
                            name,
                            severity,
                            width = 50
                        ),
                        "-----\n".to_string(),
                    ],
                    CrashSuspectFinding::DllInvolvement => vec![
                        "* NOTICE : MAIN ERROR REPORTS THAT A DLL FILE WAS INVOLVED IN THIS CRASH! * \n".to_string(),
                        "If that dll file belongs to a mod, that mod is a prime suspect for the crash. \n\n".to_string(),
                        "-----\n".to_string(),
                    ],
                })
            })
            .collect()
    }

    /// Renders only YAML outcomes placed into the Error Information section.
    fn error_information_fragments(
        result: Option<&CrashgenSettingsAnalysisResult>,
    ) -> Vec<ReportFragment> {
        result
            .into_iter()
            .flat_map(|result| result.expectation_outcomes.iter())
            .filter(|outcome| outcome.placement == AutoscanReportPlacement::ErrorInformation)
            .map(|outcome| ReportFragment::from_lines(render_error_information_lines(outcome)))
            .collect()
    }

    /// Renders settings-placement expectations before universal disabled-setting notices.
    fn settings_fragments(
        result: Option<&CrashgenSettingsAnalysisResult>,
        crashgen_name: &str,
    ) -> Vec<ReportFragment> {
        let Some(result) = result else {
            return Vec::new();
        };
        let mut fragments = result
            .expectation_outcomes
            .iter()
            .filter(|outcome| outcome.placement == AutoscanReportPlacement::Settings)
            .map(|outcome| ReportFragment::from_lines(render_settings_lines(outcome)))
            .collect::<Vec<_>>();
        fragments.extend(
            result
                .disabled_setting_notices
                .iter()
                .map(|notice| render_disabled_setting_notice_fragment(notice, crashgen_name)),
        );
        fragments
    }

    /// Renders one canonical Mod Guidance group from the aggregate semantic result.
    fn mod_guidance_fragments(
        result: Option<&ModGuidanceAnalysisResult>,
        group: ModGuidanceGroup,
    ) -> Vec<ReportFragment> {
        let lines = result
            .map(|result| match group {
                ModGuidanceGroup::MayConflict => Self::render_mod_conflicts(result),
                ModGuidanceGroup::FrequentCrashes => {
                    Self::render_mod_solutions(&result.frequent_crashes)
                }
                ModGuidanceGroup::HasSolutions => Self::render_mod_solutions(&result.solutions),
                ModGuidanceGroup::ImportantMods => {
                    Self::render_important_mods(&result.important_mods)
                }
            })
            .unwrap_or_default();

        if lines.is_empty() {
            Vec::new()
        } else {
            vec![ReportFragment::from_lines(lines)]
        }
    }

    /// Renders matched conflict guidance without leaking formatting into the analyzer.
    fn render_mod_conflicts(result: &ModGuidanceAnalysisResult) -> Vec<String> {
        if result.conflicts.is_empty() {
            return Vec::new();
        }

        let mut lines = vec!["[!] CAUTION : Conflicting mods detected\n".to_string()];
        for conflict in &result.conflicts {
            lines.push(format!(
                "{} ❌ CONFLICTS WITH : {}\n",
                conflict.name_a, conflict.name_b
            ));
            lines.push(format!("    {}\n", conflict.description));
            lines.push(format!("    {}\n", conflict.fix));
            if let Some(link) = &conflict.link {
                lines.push(format!("    Link: {link}\n"));
            }
            lines.push("    -----\n\n".to_string());
        }
        lines
    }

    /// Sorts matched semantic entries by load order and renders their report bodies.
    fn render_mod_solutions(entries: &[ModSolutionGuidance]) -> Vec<String> {
        let mut ordered = entries
            .iter()
            .enumerate()
            .map(|(index, entry)| {
                let mut plugin_ids = entry.matched_plugin_ids.clone();
                plugin_ids.sort_by_key(|plugin_id| parse_plugin_id_for_sort(plugin_id));
                (index, entry, plugin_ids)
            })
            .collect::<Vec<_>>();
        ordered.sort_by(|(left_index, _, left_ids), (right_index, _, right_ids)| {
            let left_key = left_ids
                .first()
                .map(|id| parse_plugin_id_for_sort(id))
                .unwrap_or((false, 0));
            let right_key = right_ids
                .first()
                .map(|id| parse_plugin_id_for_sort(id))
                .unwrap_or((false, 0));
            left_key
                .cmp(&right_key)
                .then_with(|| left_index.cmp(right_index))
        });

        let mut lines = Vec::new();
        for (_, entry, plugin_ids) in ordered {
            append_mod_found_entry(&mut lines, &plugin_ids, &entry.name, &entry.description);
        }
        lines
    }

    /// Renders important-mod states while keeping icons and fallback prose private.
    fn render_important_mods(entries: &[ImportantModGuidance]) -> Vec<String> {
        let mut lines = Vec::new();
        for entry in entries {
            match entry.state {
                ModGuidanceMatchState::Matched => {
                    lines.push(format!("✔️ {} is installed!\n\n", entry.name));
                }
                ModGuidanceMatchState::GpuMismatch => {
                    if let Some(warning) = &entry.gpu_mismatch_warning {
                        let warning = warning.trim_end().replace('\n', "\n\n");
                        lines.push(format!("❓ {warning}\n\n"));
                    } else {
                        let gpu = entry.gpu.as_deref().unwrap_or("UNKNOWN").to_uppercase();
                        lines.push(format!(
                            "❓ {} is installed, BUT IT SEEMS YOU DON'T HAVE AN {} GPU?\n\n",
                            entry.name, gpu
                        ));
                        lines.push("IF THIS IS CORRECT, COMPLETELY UNINSTALL THIS MOD TO AVOID ANY PROBLEMS!\n\n".to_string());
                    }
                }
                ModGuidanceMatchState::Missing => {
                    let description_lines =
                        entry.description.trim_end().lines().collect::<Vec<_>>();
                    let first_line = description_lines
                        .first()
                        .map(|line| line.trim())
                        .unwrap_or("");
                    lines.push(format!(
                        "❌ {} is not installed! {}  \n",
                        entry.name, first_line
                    ));
                    for line in description_lines.iter().skip(1) {
                        let line = line.trim();
                        if !line.is_empty() {
                            lines.push(format!("{line}  \n"));
                        }
                    }
                    lines.push("\n".to_string());
                }
            }
        }
        lines
    }

    fn mod_guidance_header(
        report_gen: &ReportGenerator,
        group: ModGuidanceGroup,
    ) -> ReportFragment {
        match group {
            ModGuidanceGroup::MayConflict => {
                report_gen.generate_mod_check_header("May Conflict With Each Other")
            }
            ModGuidanceGroup::FrequentCrashes => {
                report_gen.generate_mod_check_header("Can Cause Frequent Crashes")
            }
            ModGuidanceGroup::HasSolutions => {
                report_gen.generate_mod_check_header("HAVE SOLUTIONS")
            }
            ModGuidanceGroup::ImportantMods => {
                ReportFragment::from_lines(vec!["### Checking for Important Mods\n\n".to_string()])
            }
        }
    }

    fn append_error_information_fragments(
        error_section: ReportFragment,
        extra_fragments: Vec<ReportFragment>,
    ) -> ReportFragment {
        if extra_fragments.is_empty() {
            return error_section;
        }

        let mut lines = error_section.to_list();
        let separator = if matches!(lines.last(), Some(line) if line == "---\n\n") {
            lines.pop().unwrap_or_default()
        } else {
            "---\n\n".to_string()
        };

        for fragment in extra_fragments {
            lines.extend(fragment.to_list());
        }
        lines.push(separator);

        ReportFragment::from_lines(lines)
    }

    /// Renders the immutable setup snapshot owned by the current scan run.
    fn fcx_setup_fragment(setup: &CrashLogScanSetupResult) -> ReportFragment {
        let mut lines = vec![
            "* NOTICE: FCX LOCAL FILE CHECKS ARE ENABLED FOR THIS SCAN * \n\n".to_string(),
            "[ Use FCX only with crash logs from your own installation. ] \n\n".to_string(),
        ];

        if !setup.rendered_report.trim().is_empty() {
            lines.push("\n--- FCX SETUP VALIDATION ---\n\n".to_string());
            lines.push(setup.rendered_report.clone());
            if !setup.rendered_report.ends_with('\n') {
                lines.push("\n".to_string());
            }
        }

        if !setup.configuration_issues.is_empty() {
            lines.push("\n--- DETECTED CONFIGURATION ISSUES ---\n\n".to_string());
            lines.extend(
                setup
                    .configuration_issues
                    .iter()
                    .map(Self::render_configuration_issue),
            );
        }

        ReportFragment::from_lines(lines)
    }

    /// Renders one semantic FCX configuration issue inside private report assembly.
    fn render_configuration_issue(issue: &crate::ConfigIssue) -> String {
        let icon = match issue.severity.as_str() {
            "error" => "❌",
            "warning" => "⚠️",
            "info" => "ℹ️",
            _ => "⚠️",
        };
        let section = issue
            .section
            .as_ref()
            .map(|section| format!("[{section}]"))
            .unwrap_or_else(|| "N/A".to_string());

        format!(
            "{} DETECTED ISSUE: {}\n   File: {}\n   Section: {}\n   Setting: {}\n   Current Value: {}\n   Recommended Value: {}\n\n",
            icon,
            issue.description,
            issue.file_path,
            section,
            issue.setting,
            issue.current_value,
            issue.recommended_value
        )
    }
}

/// Renders one universal disabled-setting notice with presentation supplied by report assembly.
fn render_disabled_setting_notice_fragment(
    notice: &DisabledSettingNotice,
    crashgen_name: &str,
) -> ReportFragment {
    ReportFragment::from_lines(disabled_setting_notice_lines(
        &notice.setting_name,
        crashgen_name,
    ))
}

/// Renders one semantic expectation under settings-related guidance.
fn render_settings_lines(outcome: &CrashgenExpectationOutcome) -> Vec<String> {
    let mut lines = Vec::new();
    match outcome.kind {
        OutcomeKind::Issue => {
            lines.push(format!("# ❌ CAUTION : {} # \n", outcome.message));
            if let Some(fix) = outcome.fix.as_deref() {
                lines.push(format!(" FIX: {}\n\n-----\n", fix));
            } else {
                lines.push("\n-----\n".to_string());
            }
        }
        OutcomeKind::Notice => {
            lines.push(format!(
                "# {} NOTICE : {} # \n",
                notice_icon(outcome.severity),
                outcome.message
            ));
            if let Some(fix) = outcome.fix.as_deref() {
                lines.push(format!(" {}\n\n-----\n", fix));
            } else {
                lines.push("\n-----\n".to_string());
            }
        }
        OutcomeKind::Success => {
            lines.push(format!("✔️ {}\n\n-----\n", outcome.message));
        }
    }
    lines
}

/// Renders one semantic expectation promoted into Error Information.
fn render_error_information_lines(outcome: &CrashgenExpectationOutcome) -> Vec<String> {
    let mut lines = Vec::new();
    match outcome.kind {
        OutcomeKind::Issue => {
            lines.push(format!("**# ❌ CAUTION : {} #**\n\n", outcome.message));
            if let Some(fix) = outcome.fix.as_deref() {
                lines.push(format!("FIX: {}\n\n", fix));
            }
        }
        OutcomeKind::Notice => {
            lines.push(format!(
                "**# {} NOTICE : {} #**\n\n",
                notice_icon(outcome.severity),
                outcome.message
            ));
            if let Some(fix) = outcome.fix.as_deref() {
                lines.push(format!("{}\n\n", fix));
            }
        }
        OutcomeKind::Success => {
            lines.push(format!("**✔️ {}**\n\n", outcome.message));
        }
    }
    lines
}

fn disabled_setting_notice_lines(setting_name: &str, crashgen_name: &str) -> Vec<String> {
    vec![format!(
        "* NOTICE : {} is disabled in your {} settings, is this intentional? * \n\n-----\n",
        setting_name, crashgen_name
    )]
}

fn notice_icon(severity: RuleSeverity) -> &'static str {
    match severity {
        RuleSeverity::Error => "❌",
        RuleSeverity::Warning => "⚠️",
        RuleSeverity::Info => "[!]",
    }
}

/// Private immutable report fragment used during Autoscan Report Assembly.
#[derive(Clone, Debug)]
struct ReportFragment {
    /// Immutable content lines
    content: Arc<Vec<String>>,
    /// Whether this fragment contains meaningful content
    has_content: bool,
}

impl ReportFragment {
    /// Create an empty fragment
    pub fn empty() -> Self {
        Self {
            content: Arc::new(Vec::new()),
            has_content: false,
        }
    }

    /// Create a fragment from lines
    pub fn from_lines(lines: Vec<String>) -> Self {
        let has_content = !lines.is_empty();
        Self {
            content: Arc::new(lines),
            has_content,
        }
    }

    /// Combine two fragments
    pub fn combine(&self, other: &ReportFragment) -> Self {
        if !self.has_content && !other.has_content {
            return Self::empty();
        }

        let mut combined = Vec::with_capacity(self.content.len() + other.content.len());
        combined.extend(self.content.iter().cloned());
        combined.extend(other.content.iter().cloned());

        Self {
            content: Arc::new(combined),
            has_content: self.has_content || other.has_content,
        }
    }

    /// Convert to a list of strings
    pub fn to_list(&self) -> Vec<String> {
        self.content.to_vec()
    }
}

/// Private report composer with deterministic final fragment ordering.
struct ReportComposer {
    fragments: Vec<ReportFragment>,
}

impl ReportComposer {
    /// Create a new composer
    pub fn new() -> Self {
        Self {
            fragments: Vec::new(),
        }
    }

    /// Add a fragment to the composer
    pub fn add(&mut self, fragment: ReportFragment) {
        self.fragments.push(fragment);
    }

    /// Add multiple fragments
    pub fn add_many(&mut self, fragments: Vec<ReportFragment>) {
        self.fragments.extend(fragments);
    }

    /// Compose all fragments into a single fragment
    pub fn compose(&self) -> ReportFragment {
        if self.fragments.is_empty() {
            return ReportFragment::empty();
        }

        if self.fragments.len() == 1 {
            return self.fragments[0].clone();
        }

        self.compose_sequential()
    }

    /// Sequential composition for small numbers of fragments
    fn compose_sequential(&self) -> ReportFragment {
        let mut result = self.fragments[0].clone();
        for fragment in &self.fragments[1..] {
            result = result.combine(fragment);
        }
        result
    }
}

/// Private generator for report fragments with efficient string building.
///
/// Its output preserves the established Autoscan Report byte contract while
/// keeping presentation mechanics behind the final scan-run operation.
struct ReportGenerator {
    /// Bare SemVer version string for the CLASSIC application (e.g., "v8.0.0").
    /// The `CLASSIC ` product-name prefix is applied by the report generator's
    /// format strings, not stored here.
    classic_version: String,
    /// Name of the crash generator (e.g., "Buffout 4")
    crashgen_name: String,
}

impl ReportGenerator {
    /// Creates a report generator with specified configuration.
    ///
    /// # Arguments
    ///
    /// * `classic_version` - The bare SemVer version string (e.g., "v8.0.0"). The generator
    ///   prepends the `CLASSIC ` product-name prefix at format time, so the caller passes the
    ///   raw YAML value without decoration.
    /// * `crashgen_name` - The crash generator name (e.g., "Buffout 4")
    ///
    /// # Returns
    ///
    /// A configured `ReportGenerator` instance.
    pub fn with_config(classic_version: String, crashgen_name: String) -> Self {
        Self {
            classic_version,
            crashgen_name,
        }
    }

    fn formatted_classic_name(&self) -> String {
        let version = self
            .classic_version
            .trim()
            .strip_prefix("CLASSIC")
            .map_or_else(|| self.classic_version.trim(), str::trim_start);

        if version.is_empty() {
            "CLASSIC".to_string()
        } else {
            format!("CLASSIC {version}")
        }
    }

    /// Generate a header fragment for the report.
    ///
    /// Preserves the established Autoscan Report header byte contract.
    ///
    /// # Arguments
    ///
    /// * `crashlog_filename` - Name of the crash log file being analyzed
    ///
    /// # Returns
    ///
    /// A `ReportFragment` containing the formatted header.
    pub fn generate_header(&self, crashlog_filename: &str) -> ReportFragment {
        let classic_name = self.formatted_classic_name();
        let lines = vec![
            format!("# {}\n", crashlog_filename),
            format!("**AUTOSCAN REPORT GENERATED BY {classic_name}**\n\n"),
            "> **FOR BEST VIEWING EXPERIENCE OPEN THIS FILE IN NOTEPAD++ OR SIMILAR**\n\n"
                .to_string(),
            "> **PLEASE READ EVERYTHING CAREFULLY AND BEWARE OF FALSE POSITIVES**\n\n".to_string(),
            "---\n\n".to_string(),
        ];

        ReportFragment::from_lines(lines)
    }

    /// Generate an error section with optional fake bot-compatible mode notice.
    pub fn generate_error_section_with_status_and_fake_mode(
        &self,
        main_error: &str,
        crashgen_version: &str,
        status: Option<CrashgenVersionStatus>,
        fake_bot_compatible_mode: bool,
    ) -> ReportFragment {
        let mut lines = vec![
            "### Error Information\n\n".to_string(),
            format!("**Main Error:** {}\n\n", main_error),
            format!(
                "**Detected {} Version:** {}\n\n",
                self.crashgen_name, crashgen_version
            ),
        ];

        if fake_bot_compatible_mode {
            lines.push("**# ⚠️ NOTICE : This report was generated in Bot Compatible Mode. Version and Settings checks are disabled. #**\n\n".to_string());
        } else {
            match status {
                Some(CrashgenVersionStatus::Valid) => {
                    lines.push(format!(
                        "✅ *You have a valid version of {}!*\n\n",
                        self.crashgen_name
                    ));
                }
                Some(CrashgenVersionStatus::NewerThanKnown) => {
                    lines.push(format!(
                        "✅ *Your {} version is newer than known versions.*\n\n",
                        self.crashgen_name
                    ));
                }
                Some(CrashgenVersionStatus::Outdated) => {
                    lines.push(format!(
                        "***❌ WARNING: YOUR {} IS OUTDATED! PLEASE UPDATE TO A VALID VERSION!***\n\n",
                        self.crashgen_name
                    ));
                }
                Some(CrashgenVersionStatus::NoSupportedVersion) => {
                    lines.push(
                        "⚠️ *No supported crash log generator for this game version yet.*\n\n"
                            .to_string(),
                    );
                }
                None => {
                    lines.push(format!(
                        "⚠️ *Unable to verify {} version.*\n\n",
                        self.crashgen_name
                    ));
                }
            }
        }

        lines.push("---\n\n".to_string());

        ReportFragment::from_lines(lines)
    }

    /// Generate the suspect section header.
    ///
    /// Preserves the established Crash Suspect header byte contract.
    ///
    /// # Returns
    ///
    /// A `ReportFragment` containing the suspect section header.
    pub fn generate_suspect_section_header(&self) -> ReportFragment {
        ReportFragment::from_lines(vec![
            "### Checking for Known Crash Messages, Errors and Suspects\n\n".to_string(),
        ])
    }

    /// Generate the suspect found footer based on whether suspects were detected.
    ///
    /// Preserves the established Crash Suspect footer byte contract.
    ///
    /// # Arguments
    ///
    /// * `found_suspect` - Whether any suspects were detected
    ///
    /// # Returns
    ///
    /// A `ReportFragment` containing the footer message.
    pub fn generate_suspect_found_footer(&self, found_suspect: bool) -> ReportFragment {
        if found_suspect {
            ReportFragment::from_lines(vec![
                "* **ONE OR MORE SUSPECTS DETECTED! CHECK LOG ABOVE FOR MORE INFORMATION!** *\n\n"
                    .to_string(),
                "---\n\n".to_string(),
            ])
        } else {
            ReportFragment::from_lines(vec![
                "* **NO SUSPECTS DETECTED** *\n\n".to_string(),
                "---\n\n".to_string(),
            ])
        }
    }

    /// Generate the settings section header.
    ///
    /// Preserves the established settings-section header byte contract.
    ///
    /// # Returns
    ///
    /// A `ReportFragment` containing the settings section header.
    pub fn generate_settings_section_header(&self) -> ReportFragment {
        ReportFragment::from_lines(vec![
            "### Checking for Settings-related Issues\n\n".to_string(),
        ])
    }

    /// Generate a mod check header with the specified check type.
    ///
    /// Preserves the established mod-check header byte contract.
    ///
    /// # Arguments
    ///
    /// * `check_type` - Description of what type of mods are being checked
    ///
    /// # Returns
    ///
    /// A `ReportFragment` containing the mod check header.
    pub fn generate_mod_check_header(&self, check_type: &str) -> ReportFragment {
        ReportFragment::from_lines(vec![format!(
            "### Checking For Mods That {}\n\n",
            check_type
        )])
    }

    /// Generate the plugin suspect header.
    ///
    /// Preserves the established plugin-suspect header byte contract.
    ///
    /// # Returns
    ///
    /// A `ReportFragment` containing the plugin suspect header.
    pub fn generate_plugin_suspect_header(&self) -> ReportFragment {
        ReportFragment::from_lines(vec![
            "### Checking for Plugin-related Errors\n\n".to_string(),
        ])
    }

    /// Generate the FormID section header.
    ///
    /// Preserves the established FormID header byte contract.
    ///
    /// # Returns
    ///
    /// A `ReportFragment` containing the FormID section header.
    pub fn generate_formid_section_header(&self) -> ReportFragment {
        ReportFragment::from_lines(vec!["### Checking FormIDs\n\n".to_string()])
    }

    /// Generate the record section header.
    ///
    /// Preserves the established named-record header byte contract.
    ///
    /// # Returns
    ///
    /// A `ReportFragment` containing the record section header.
    pub fn generate_record_section_header(&self) -> ReportFragment {
        ReportFragment::from_lines(vec!["### Checking for Named Records\n\n".to_string()])
    }

    /// Generate the report footer.
    ///
    /// Preserves the established Autoscan Report footer byte contract.
    /// The footer includes end of report marker, version info, and credits
    /// for the author and contributors.
    ///
    /// # Returns
    ///
    /// A `ReportFragment` containing the report footer with credits.
    pub fn generate_footer(&self) -> ReportFragment {
        let classic_name = self.formatted_classic_name();
        ReportFragment::from_lines(vec![
            "---\n\n".to_string(),
            "### End of Report\n\n".to_string(),
            format!("Generated by {classic_name}\n\n"),
            "---\n\n".to_string(),
            "Author/Made By: Poet (guidance.of.grace) | https://discord.gg/DfFYJtt8p4\n\n"
                .to_string(),
            "CONTRIBUTORS | evildarkarchon | kittivelae | AtomicFallout757 | wxMichael\n\n"
                .to_string(),
            "FO4 CLASSIC | https://www.nexusmods.com/fallout4/mods/56255\n".to_string(),
        ])
    }
}

#[cfg(test)]
#[path = "report_tests.rs"]
mod tests;
