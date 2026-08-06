#include <QSet>
#include <QTemporaryDir>
#include <QtTest/QtTest>

#include "core/rust_qt_bridge.h"
#include "workers/scanrunpresentation.h"

#include <array>
#include <cstddef>
#include <initializer_list>
#include <utility>

namespace {

// Compliance anchor: these presentation cases consume Rust-owned terminal facts
// without reconstructing discovery, scheduling, or outcome policy in Qt.

/// Creates a result-bearing execution envelope for one expected lifecycle status.
classic::scanner::ScanRunContractExecutionResult executionWithStatus(classic::scanner::ScanRunContractStatus status)
{
    classic::scanner::ScanRunContractExecutionResult execution{};
    execution.has_result = true;
    execution.result.status = status;
    return execution;
}

/// Creates one discovery-ordered terminal Crash Log outcome.
classic::scanner::ScanRunContractLogResult logResult(std::size_t discoveryIndex, const char* crashLog,
                                                     classic::scanner::ScanRunContractLogDisposition disposition)
{
    classic::scanner::ScanRunContractLogResult result{};
    result.discovery_index = discoveryIndex;
    result.crash_log = crashLog;
    result.disposition = disposition;
    return result;
}

// Renderer-conformance fixtures below deliberately use words no Crash Log Scan Run would ever
// produce. Wording is pinned once, in `classic-scan-presentation`, and per-frontend golden suites
// were rejected on #170 precisely because they would assert the same sentence four times and give
// one rewording four chances to disagree. What this frontend must prove is narrower: that it did
// not reword, reorder, or re-derive what it was handed.

/// Creates one flattened display segment, filling only the field its kind selects.
classic::scanner::ScanRunDisplaySegment segment(classic::scanner::ScanRunDisplaySegmentKind kind, const char* text,
                                                 const char* path = "", quint64 count = 0)
{
    classic::scanner::ScanRunDisplaySegment created{};
    created.kind = kind;
    created.text = text;
    created.path = path;
    created.count = count;
    return created;
}

/// Creates one Qt-owned display line from bridge segments, through the real projection.
///
/// Built through `presentScanRunDisplayLines` rather than by filling the Qt struct directly, so the
/// flattening the bridge applies is exercised by every case below rather than assumed.
classic::gui::ScanRunDisplayLinePresentation presentedLine(
    classic::scanner::ScanRunDisplaySeverity severity,
    std::initializer_list<classic::scanner::ScanRunDisplaySegment> segments)
{
    rust::Vec<classic::scanner::ScanRunDisplayLine> lines;
    classic::scanner::ScanRunDisplayLine line{};
    line.severity = severity;
    for (const auto& created : segments) {
        line.segments.push_back(created);
    }
    lines.push_back(std::move(line));
    return classic::gui::presentScanRunDisplayLines(lines).first();
}

/// Appends one rendered line to an execution envelope's mirrored Display Content.
void appendDisplayLine(classic::scanner::ScanRunContractExecutionResult& execution,
                       classic::scanner::ScanRunDisplaySeverity severity,
                       std::initializer_list<classic::scanner::ScanRunDisplaySegment> segments)
{
    classic::scanner::ScanRunDisplayLine line{};
    line.severity = severity;
    for (const auto& created : segments) {
        line.segments.push_back(created);
    }
    execution.display_lines.push_back(std::move(line));
}

} // namespace

class ScanRunPresentationTests : public QObject {
    Q_OBJECT

private slots:
    void targeted_rejections_preserve_paired_paths_and_reasons();
    void discovery_report_directories_are_deduplicated_case_insensitively();
    void terminal_logs_preserve_discovery_order_and_structured_dispositions();
    void expected_lifecycle_statuses_remain_distinct_from_infrastructure_errors();
    /// Verifies Local Ignore recovery remains expected result data with its own terminal kind.
    void local_ignore_recovery_required_remains_distinct();
    /// Verifies the run's Reset To Default availability survives the projection into Qt-owned data.
    void local_ignore_reset_availability_is_projected_data();
    /// Verifies the offer rule honours an explicit denial and treats an absent report as available.
    void local_ignore_reset_is_offered_unless_the_run_denied_it();
    void setup_failure_presents_checks_updates_configuration_issues_actions_and_fatal_errors();
    void installed_yaml_data_presence_preserves_generated_ignore_metadata_and_diagnostics();
    /// Verifies successful reset metadata remains typed and Qt-owned for later interaction work.
    void reset_to_default_preserves_durable_metadata_and_diagnostic();
    /// Verifies degraded selection and durable recovery aggregate into one run-level warning.
    void fallback_and_recovery_diagnostics_become_one_run_level_warning();
    /// Verifies an expected first-run Ignore generation never escalates to a run-level warning.
    void expected_local_ignore_generation_produces_no_run_level_warning();
    /// Verifies a recovery the user already answered is not re-reported as a warning.
    void answered_recovery_does_not_restate_the_local_ignore_problem();
    /// Verifies continuation replay misuse retains its stable code and message.
    void consumed_resume_error_preserves_typed_context();
    /// Verifies reset failures retain path, publication stage, identities, and any verified backup.
    void reset_resume_error_preserves_operational_context();
    void infrastructure_error_preserves_typed_stage_message_and_path();
    void invalid_execution_envelope_is_presented_as_an_infrastructure_error();
    // Renderer conformance, added with #178 when the GUI stopped composing sentences about a run.
    //
    // These assert the four things an adapter can get wrong about Display Content it did not write:
    // that segments concatenate in Rust's order, that a count prints Rust's noun rather than one
    // re-derived here, that a path is typed as a path and so becomes actionable, and that severity
    // reaches this frontend's own styling. None of them restates a sentence, because
    // `classic-scan-presentation` pins every sentence once and per-frontend golden suites were
    // rejected on #170 for reintroducing the drift they were meant to catch.
    void display_line_segments_concatenate_in_the_order_rust_supplied();
    void a_count_prints_the_noun_rust_resolved_rather_than_re_deciding_it();
    void a_path_segment_renders_as_selectable_actionable_text();
    void every_severity_maps_to_this_frontends_own_styling();
    void rendered_lines_reach_the_terminal_presentation_in_rust_order();

    // Display Label coverage for the two enums this frontend still labels itself.
    //
    // Both are labelled *outside* a display line, by the one-row YAML Data status suffix that has no
    // room for a rendered block. Quoting the canonical strings as literals here is deliberate and is
    // the one place in this frontend where that is right: it is how a wording a ticket settled gets
    // pinned across the binding boundary, so a core-side reword has to be a decision rather than an
    // accident.
    //
    // The three sibling blocks that pinned infrastructure stages, reset failure stages, and
    // diagnostic kinds are gone, not relaxed. Those labels now reach the user inside a `Label`
    // segment on a line Rust wrote, so pinning them here would assert the presentation crate's
    // wording a second time — exactly the four-copies-of-one-sentence problem #170 exists to remove.
    void every_local_ignore_state_renders_its_canonical_display_label();
    void every_installed_yaml_data_provenance_renders_its_canonical_display_label();
};

void ScanRunPresentationTests::targeted_rejections_preserve_paired_paths_and_reasons()
{
    classic::scanner::ScanRunContractDiscoveryResult discovery{};
    discovery.source = classic::scanner::ScanRunContractDiscoverySource::Targeted;

    classic::scanner::ScanRunContractRejectedInput missing{};
    missing.path = "C:/picked/missing.log";
    missing.reason = "path does not exist";
    discovery.rejected_inputs.push_back(std::move(missing));

    classic::scanner::ScanRunContractRejectedInput unsupported{};
    unsupported.path = "C:/picked/readme.txt";
    unsupported.reason = "unsupported Crash Log filename";
    discovery.rejected_inputs.push_back(std::move(unsupported));

    QCOMPARE(classic::gui::formatScanRunRejections(discovery),
             QStringLiteral("Ignored 2 targeted inputs:\n"
                            "- C:/picked/missing.log (path does not exist)\n"
                            "- C:/picked/readme.txt (unsupported Crash Log filename)"));
}

void ScanRunPresentationTests::installed_yaml_data_presence_preserves_generated_ignore_metadata_and_diagnostics()
{
    auto execution = executionWithStatus(classic::scanner::ScanRunContractStatus::Completed);
    execution.result.has_installed_yaml_data = true;
    auto& installed = execution.result.installed_yaml_data;
    installed.main.role = classic::scanner::ScanRunInstalledYamlDataRole::Main;
    installed.main.provenance = classic::scanner::ScanRunInstalledYamlDataProvenance::Bundled;
    installed.main.schema_version = "2.0";
    installed.main.sha256 = "main-hash";
    installed.main.byte_len = 64;
    installed.game_file.role = classic::scanner::ScanRunInstalledYamlDataRole::Game;
    installed.game_file.provenance = classic::scanner::ScanRunInstalledYamlDataProvenance::Updated;
    installed.game_file.schema_version = "1.0";
    installed.game_file.sha256 = "game-hash";
    installed.game_file.byte_len = 48;
    installed.local_ignore_state = classic::scanner::ScanRunLocalIgnoreYamlDataState::Generated;
    installed.local_ignore_identity.sha256 = "ignore-hash";
    installed.local_ignore_identity.byte_len = 32;
    classic::scanner::ScanRunInstalledYamlDataDiagnosticDto diagnostic{};
    diagnostic.kind = classic::scanner::ScanRunInstalledYamlDataDiagnosticKind::LocalIgnoreGenerated;
    diagnostic.has_path = true;
    diagnostic.path = "C:/CLASSIC/CLASSIC Data/CLASSIC Ignore.yaml";
    diagnostic.message = "generated missing Local Ignore YAML Data";
    installed.diagnostics.push_back(std::move(diagnostic));

    const auto presentation = classic::gui::presentScanRunExecution(execution);

    QVERIFY(presentation.hasInstalledYamlData);
    QCOMPARE(presentation.installedYamlData.main.schemaVersion, QStringLiteral("2.0"));
    QCOMPARE(presentation.installedYamlData.main.sha256, QStringLiteral("main-hash"));
    QCOMPARE(presentation.installedYamlData.gameFile.provenance,
             classic::scanner::ScanRunInstalledYamlDataProvenance::Updated);
    QCOMPARE(presentation.installedYamlData.localIgnoreState,
             classic::scanner::ScanRunLocalIgnoreYamlDataState::Generated);
    QCOMPARE(presentation.installedYamlData.localIgnoreIdentity.byteLength, quint64{32});
    QCOMPARE(presentation.installedYamlData.diagnostics.size(), 1);
    QCOMPARE(presentation.installedYamlData.diagnostics[0].kind,
             classic::scanner::ScanRunInstalledYamlDataDiagnosticKind::LocalIgnoreGenerated);
    QVERIFY(presentation.installedYamlData.diagnostics[0].hasPath);
    QVERIFY(presentation.installedYamlData.diagnostics[0].path.endsWith(QStringLiteral("CLASSIC Ignore.yaml")));
}

void ScanRunPresentationTests::reset_to_default_preserves_durable_metadata_and_diagnostic()
{
    auto execution = executionWithStatus(classic::scanner::ScanRunContractStatus::Completed);
    execution.result.has_installed_yaml_data = true;
    auto& installed = execution.result.installed_yaml_data;
    installed.local_ignore_state = classic::scanner::ScanRunLocalIgnoreYamlDataState::ResetToDefault;
    installed.local_ignore_identity.sha256 = "replacement-hash";
    installed.local_ignore_identity.byte_len = 42;
    installed.has_local_ignore_reset = true;
    installed.local_ignore_reset.local_ignore_path = "C:/CLASSIC/CLASSIC Data/CLASSIC Ignore.yaml";
    installed.local_ignore_reset.backup_path = "C:/CLASSIC/CLASSIC Backup/CLASSIC Ignore.backup.yaml";
    installed.local_ignore_reset.malformed_identity.sha256 = "malformed-hash";
    installed.local_ignore_reset.malformed_identity.byte_len = 30;
    installed.local_ignore_reset.backup_identity = installed.local_ignore_reset.malformed_identity;
    installed.local_ignore_reset.replacement_identity = installed.local_ignore_identity;
    classic::scanner::ScanRunInstalledYamlDataDiagnosticDto diagnostic{};
    diagnostic.kind = classic::scanner::ScanRunInstalledYamlDataDiagnosticKind::LocalIgnoreReset;
    diagnostic.has_path = true;
    diagnostic.path = installed.local_ignore_reset.local_ignore_path;
    diagnostic.message = "reset malformed Local Ignore from retained defaults";
    installed.diagnostics.push_back(std::move(diagnostic));

    const auto presentation = classic::gui::presentScanRunExecution(execution);

    QVERIFY(presentation.hasInstalledYamlData);
    QCOMPARE(presentation.installedYamlData.localIgnoreState,
             classic::scanner::ScanRunLocalIgnoreYamlDataState::ResetToDefault);
    QVERIFY(presentation.installedYamlData.hasLocalIgnoreReset);
    QCOMPARE(presentation.installedYamlData.localIgnoreReset.localIgnorePath,
             QStringLiteral("C:/CLASSIC/CLASSIC Data/CLASSIC Ignore.yaml"));
    QCOMPARE(presentation.installedYamlData.localIgnoreReset.backupPath,
             QStringLiteral("C:/CLASSIC/CLASSIC Backup/CLASSIC Ignore.backup.yaml"));
    QCOMPARE(presentation.installedYamlData.localIgnoreReset.malformedIdentity.sha256,
             QStringLiteral("malformed-hash"));
    QCOMPARE(presentation.installedYamlData.localIgnoreReset.backupIdentity.sha256,
             QStringLiteral("malformed-hash"));
    QCOMPARE(presentation.installedYamlData.localIgnoreReset.replacementIdentity.sha256,
             QStringLiteral("replacement-hash"));
    QCOMPARE(presentation.installedYamlData.diagnostics[0].kind,
             classic::scanner::ScanRunInstalledYamlDataDiagnosticKind::LocalIgnoreReset);
}

void ScanRunPresentationTests::fallback_and_recovery_diagnostics_become_one_run_level_warning()
{
    classic::gui::ScanRunInstalledYamlDataPresentation installed{};
    installed.localIgnoreState = classic::scanner::ScanRunLocalIgnoreYamlDataState::ResetToDefault;

    classic::gui::ScanRunInstalledYamlDataDiagnosticPresentation rejected{};
    rejected.kind = classic::scanner::ScanRunInstalledYamlDataDiagnosticKind::IncompatibleSchema;
    rejected.message = QStringLiteral("updated Main schema 9.0 is newer than this client supports");
    rejected.hasRole = true;
    rejected.role = classic::scanner::ScanRunInstalledYamlDataRole::Main;
    rejected.hasCandidate = true;
    rejected.candidate = classic::scanner::ScanRunInstalledYamlDataProvenance::Updated;
    rejected.hasPath = true;
    rejected.path = QStringLiteral("C:/CLASSIC/cache/CLASSIC Main.yaml");
    installed.diagnostics.append(rejected);

    // An expected first-run generation must not add noise to a warning raised for other reasons.
    classic::gui::ScanRunInstalledYamlDataDiagnosticPresentation generated{};
    generated.kind = classic::scanner::ScanRunInstalledYamlDataDiagnosticKind::LocalIgnoreGenerated;
    generated.message = QStringLiteral("generated missing Local Ignore YAML Data");
    installed.diagnostics.append(generated);

    // Local Ignore diagnostics carry no role. Once the user has answered the recovery dialog they
    // must not be restated, so neither of these two reaches the warning.
    classic::gui::ScanRunInstalledYamlDataDiagnosticPresentation answeredParse{};
    answeredParse.kind = classic::scanner::ScanRunInstalledYamlDataDiagnosticKind::Parse;
    answeredParse.message = QStringLiteral("existing Local Ignore YAML Data could not be parsed");
    installed.diagnostics.append(answeredParse);

    classic::gui::ScanRunInstalledYamlDataDiagnosticPresentation reset{};
    reset.kind = classic::scanner::ScanRunInstalledYamlDataDiagnosticKind::LocalIgnoreReset;
    reset.message = QStringLiteral("reset malformed Local Ignore from retained defaults");
    installed.diagnostics.append(reset);

    installed.hasLocalIgnoreReset = true;
    installed.localIgnoreReset.localIgnorePath = QStringLiteral("C:/CLASSIC/CLASSIC Data/CLASSIC Ignore.yaml");
    installed.localIgnoreReset.backupPath = QStringLiteral("C:/CLASSIC/CLASSIC Backup/CLASSIC Ignore.yaml");
    installed.localIgnoreReset.backupIdentity.sha256 = QStringLiteral("malformed-hash");
    installed.localIgnoreReset.backupIdentity.byteLength = 30;

    // The body of the warning is the run's own rendered lines. It carries the whole run rather than
    // the Installed YAML Data block alone because Rust exposes that block only as part of the
    // rendered run, and selecting it back out by position would be a structural assumption about a
    // sequence that deliberately carries no structure.
    using Kind = classic::scanner::ScanRunDisplaySegmentKind;
    // One rendered line per diagnostic above, in the shape Rust renders them: the kind's Display
    // Label, then the message as an Emphasis payload. The messages match the typed diagnostics
    // exactly, which is how the three that must not be restated are recognised.
    for (const auto* message : {"updated Main schema 9.0 is newer than this client supports",
                                "generated missing Local Ignore YAML Data",
                                "existing Local Ignore YAML Data could not be parsed",
                                "reset malformed Local Ignore from retained defaults"}) {
        installed.runDisplayLines.append(presentedLine(classic::scanner::ScanRunDisplaySeverity::Warning,
                                                       {segment(Kind::Label, "unreal diagnostic kind"),
                                                        segment(Kind::Text, "-"), segment(Kind::Emphasis, message)}));
    }
    installed.runDisplayLines.append(
        presentedLine(classic::scanner::ScanRunDisplaySeverity::Info,
                      {segment(Kind::Text, "unreal backup lead"),
                       segment(Kind::Path, "", "C:/CLASSIC/CLASSIC Backup/CLASSIC Ignore.yaml")}));

    const QString warning = classic::gui::formatInstalledYamlDataWarning(installed);

    QVERIFY(!warning.isEmpty());
    // The section header is Display Layout and stays this frontend's.
    QVERIFY(warning.contains(QStringLiteral("CLASSIC could not use some of its installed YAML Data")));
    QVERIFY(warning.contains(QStringLiteral("updated Main schema 9.0 is newer than this client supports")));
    // The durable backup location is the one fact a user needs to recover their prior edits, and it
    // arrives as a path segment, so it is reachable rather than merely readable.
    QVERIFY(warning.contains(QStringLiteral("file:///C:/CLASSIC/CLASSIC%20Backup/CLASSIC%20Ignore.yaml")));
    QVERIFY2(!warning.contains(QStringLiteral("generated missing Local Ignore YAML Data")),
             "expected-success generation must not be reported as a warning");
    QVERIFY2(!warning.contains(QStringLiteral("could not be parsed")),
             "a Local Ignore problem the user already answered must not be restated");
    QVERIFY2(!warning.contains(QStringLiteral("reset malformed Local Ignore from retained defaults")),
             "the reset diagnostic is superseded by the backup and replacement lines beside it");

    // A run whose lines never arrived says nothing rather than showing an empty dialog.
    installed.runDisplayLines.clear();
    QVERIFY(classic::gui::formatInstalledYamlDataWarning(installed).isEmpty());
}

void ScanRunPresentationTests::answered_recovery_does_not_restate_the_local_ignore_problem()
{
    // Proceed Without Ignore leaves the malformed file in place, so its parse diagnostic survives
    // into the resumed snapshot. The user chose that outcome in the dialog, so warning again would
    // report a resolved question.
    classic::gui::ScanRunInstalledYamlDataPresentation proceeded{};
    proceeded.localIgnoreState = classic::scanner::ScanRunLocalIgnoreYamlDataState::ProceedWithoutIgnore;
    classic::gui::ScanRunInstalledYamlDataDiagnosticPresentation answeredParse{};
    answeredParse.kind = classic::scanner::ScanRunInstalledYamlDataDiagnosticKind::Parse;
    answeredParse.message = QStringLiteral("existing Local Ignore YAML Data could not be parsed");
    answeredParse.hasPath = true;
    answeredParse.path = QStringLiteral("C:/CLASSIC/CLASSIC Data/CLASSIC Ignore.yaml");
    proceeded.diagnostics.append(answeredParse);
    using Kind = classic::scanner::ScanRunDisplaySegmentKind;
    proceeded.runDisplayLines.append(presentedLine(classic::scanner::ScanRunDisplaySeverity::Warning,
                                                   {segment(Kind::Text, "unreal rendered run")}));

    QVERIFY(classic::gui::formatInstalledYamlDataWarning(proceeded).isEmpty());

    // A Main or game selection problem is unrelated to the answered question and still warns, which
    // is what the missing role distinguishes. What changed with #178 is only the body: the decision
    // to interrupt is still made from the typed diagnostics here, and the words are the run's.
    classic::gui::ScanRunInstalledYamlDataDiagnosticPresentation selectionFallback{};
    selectionFallback.kind = classic::scanner::ScanRunInstalledYamlDataDiagnosticKind::InvalidRoleData;
    selectionFallback.message = QStringLiteral("updated game YAML Data failed role validation");
    selectionFallback.hasRole = true;
    selectionFallback.role = classic::scanner::ScanRunInstalledYamlDataRole::Game;
    proceeded.diagnostics.append(selectionFallback);

    const QString warning = classic::gui::formatInstalledYamlDataWarning(proceeded);
    QVERIFY(warning.contains(QStringLiteral("unreal rendered run")));
}

void ScanRunPresentationTests::expected_local_ignore_generation_produces_no_run_level_warning()
{
    classic::gui::ScanRunInstalledYamlDataPresentation installed{};
    installed.localIgnoreState = classic::scanner::ScanRunLocalIgnoreYamlDataState::Generated;

    classic::gui::ScanRunInstalledYamlDataDiagnosticPresentation generated{};
    generated.kind = classic::scanner::ScanRunInstalledYamlDataDiagnosticKind::LocalIgnoreGenerated;
    generated.message = QStringLiteral("generated missing Local Ignore YAML Data");
    generated.hasPath = true;
    generated.path = QStringLiteral("C:/CLASSIC/CLASSIC Data/CLASSIC Ignore.yaml");
    installed.diagnostics.append(generated);
    // Rendered lines are supplied throughout so each empty result below is the policy declining to
    // interrupt, not a run that happened to have nothing to say.
    using Kind = classic::scanner::ScanRunDisplaySegmentKind;
    installed.runDisplayLines.append(presentedLine(classic::scanner::ScanRunDisplaySeverity::Info,
                                                   {segment(Kind::Text, "unreal rendered run")}));

    // A clean first run is an expected successful path, so it must never interrupt the user.
    QVERIFY(classic::gui::formatInstalledYamlDataWarning(installed).isEmpty());

    // A run with nothing to report at all is likewise silent.
    QVERIFY(classic::gui::formatInstalledYamlDataWarning({}).isEmpty());

    // The pre-decision snapshot is presented by the recovery choice dialog, so warning on it would
    // both double-report the problem and interrupt the user before they can answer.
    classic::gui::ScanRunInstalledYamlDataPresentation awaitingChoice{};
    awaitingChoice.localIgnoreState = classic::scanner::ScanRunLocalIgnoreYamlDataState::RecoveryRequired;
    classic::gui::ScanRunInstalledYamlDataDiagnosticPresentation malformed{};
    malformed.kind = classic::scanner::ScanRunInstalledYamlDataDiagnosticKind::Parse;
    malformed.message = QStringLiteral("Local Ignore YAML Data is malformed");
    awaitingChoice.diagnostics.append(malformed);
    awaitingChoice.runDisplayLines = installed.runDisplayLines;
    QVERIFY(classic::gui::formatInstalledYamlDataWarning(awaitingChoice).isEmpty());
}

void ScanRunPresentationTests::discovery_report_directories_are_deduplicated_case_insensitively()
{
    QTemporaryDir root;
    QVERIFY(root.isValid());

    const QString firstDirectory = root.filePath(QStringLiteral("Picked"));
    const QString secondDirectory = root.filePath(QStringLiteral("Elsewhere"));
    classic::scanner::ScanRunContractDiscoveryResult discovery{};
    discovery.source = classic::scanner::ScanRunContractDiscoverySource::Targeted;
    discovery.accepted_logs.push_back((firstDirectory + QStringLiteral("/crash-one.log")).toStdString());
    discovery.accepted_logs.push_back((firstDirectory.toUpper() + QStringLiteral("/crash-two.log")).toStdString());
    discovery.accepted_logs.push_back((secondDirectory + QStringLiteral("/crash-three.log")).toStdString());

    QCOMPARE(classic::gui::scanRunReportDirectories(discovery), QStringList({firstDirectory, secondDirectory}));
}

void ScanRunPresentationTests::terminal_logs_preserve_discovery_order_and_structured_dispositions()
{
    auto execution = executionWithStatus(classic::scanner::ScanRunContractStatus::Completed);
    execution.result.total = 3;
    execution.result.succeeded = 1;
    execution.result.failed = 1;
    execution.result.cancelled = 1;

    auto succeeded = logResult(0, "C:/logs/first.log", classic::scanner::ScanRunContractLogDisposition::Succeeded);
    succeeded.has_autoscan_report = true;
    succeeded.autoscan_report = "C:/logs/first-AUTOSCAN.md";
    execution.result.logs.push_back(std::move(succeeded));

    auto failed = logResult(1, "C:/logs/second.log", classic::scanner::ScanRunContractLogDisposition::Failed);
    failed.has_message = true;
    failed.message = "durable finalization had errors";
    failed.moved_to_unsolved_logs = true;
    // Structured failures are carried on the DTO but deliberately not projected into GUI strings any
    // more: Rust renders one display line per failure beneath the log's outcome, so a
    // `<stage>: <message>` list here would be that sentence written a second time.
    classic::scanner::ScanRunContractLogFailure failure{};
    failure.stage = classic::scanner::ScanRunContractLogFailureStage::Analysis;
    failure.message = "analysis failed";
    failed.failures.push_back(std::move(failure));
    execution.result.logs.push_back(std::move(failed));
    execution.result.logs.push_back(
        logResult(2, "C:/logs/third.log", classic::scanner::ScanRunContractLogDisposition::CancelledBeforeStart));

    const auto presentation = classic::gui::presentScanRunExecution(execution);

    QCOMPARE(presentation.kind, classic::gui::ScanRunTerminalKind::Completed);
    QCOMPARE(presentation.total, 3);
    QCOMPARE(presentation.succeeded, 1);
    QCOMPARE(presentation.failed, 1);
    QCOMPARE(presentation.cancelled, 1);
    QCOMPARE(presentation.logs.size(), 3);

    QCOMPARE(presentation.logs[0].discoveryIndex, 0);
    QVERIFY(presentation.logs[0].succeeded);
    QCOMPARE(presentation.logs[0].autoscanReport, QStringLiteral("C:/logs/first-AUTOSCAN.md"));

    QCOMPARE(presentation.logs[1].discoveryIndex, 1);
    QVERIFY(presentation.logs[1].failed);
    QVERIFY(presentation.logs[1].movedToUnsolvedLogs);
    QCOMPARE(presentation.logs[1].message, QStringLiteral("durable finalization had errors"));

    QCOMPARE(presentation.logs[2].discoveryIndex, 2);
    QVERIFY(presentation.logs[2].cancelledBeforeStart);
    QVERIFY(!presentation.logs[2].succeeded);
    QVERIFY(!presentation.logs[2].failed);
}

void ScanRunPresentationTests::expected_lifecycle_statuses_remain_distinct_from_infrastructure_errors()
{
    // Each expected lifecycle status still selects exactly one GUI-facing terminal kind, and that
    // kind is what decides which lifecycle signal the worker emits. The prose these cases used to
    // assert is gone from this frontend: what the run says arrives already written, and is pinned
    // once in `classic-scan-presentation`.
    auto noLogs = executionWithStatus(classic::scanner::ScanRunContractStatus::NoCrashLogsFound);
    noLogs.result.has_discovery = true;
    noLogs.result.discovery.searched_locations.push_back("C:/searched/Crash Logs");
    QCOMPARE(classic::gui::presentScanRunExecution(noLogs).kind, classic::gui::ScanRunTerminalKind::NoCrashLogsFound);

    QCOMPARE(classic::gui::presentScanRunExecution(
                 executionWithStatus(classic::scanner::ScanRunContractStatus::CancelledBeforeDiscovery))
                 .kind,
             classic::gui::ScanRunTerminalKind::CancelledBeforeDiscovery);

    auto cancelled = executionWithStatus(classic::scanner::ScanRunContractStatus::Cancelled);
    cancelled.result.total = 5;
    cancelled.result.succeeded = 2;
    cancelled.result.failed = 1;
    cancelled.result.cancelled = 2;
    const auto cancelledPresentation = classic::gui::presentScanRunExecution(cancelled);
    QCOMPARE(cancelledPresentation.kind, classic::gui::ScanRunTerminalKind::Cancelled);
    QCOMPARE(cancelledPresentation.total, 5);
    QCOMPARE(cancelledPresentation.succeeded + cancelledPresentation.failed, 3);
    QCOMPARE(cancelledPresentation.cancelled, 2);
}

void ScanRunPresentationTests::local_ignore_recovery_required_remains_distinct()
{
    auto execution = executionWithStatus(classic::scanner::ScanRunContractStatus::LocalIgnoreRecoveryRequired);
    execution.result.has_message = true;
    execution.result.message = "Local Ignore recovery is required";
    execution.result.has_installed_yaml_data = true;
    execution.result.installed_yaml_data.local_ignore_state =
        classic::scanner::ScanRunLocalIgnoreYamlDataState::RecoveryRequired;

    const auto presentation = classic::gui::presentScanRunExecution(execution);

    QCOMPARE(presentation.kind, classic::gui::ScanRunTerminalKind::LocalIgnoreRecoveryRequired);
    QVERIFY(presentation.hasInstalledYamlData);
    QCOMPARE(presentation.installedYamlData.localIgnoreState,
             classic::scanner::ScanRunLocalIgnoreYamlDataState::RecoveryRequired);
}

void ScanRunPresentationTests::local_ignore_reset_availability_is_projected_data()
{
    // The projection dropped this one field while mirroring every neighbouring one, which is how
    // both C++ frontends came to offer a decision the run had already said could not succeed. Both
    // directions are pinned so a projection that hard-codes either value fails here.
    for (const bool available : {true, false}) {
        auto execution = executionWithStatus(classic::scanner::ScanRunContractStatus::LocalIgnoreRecoveryRequired);
        execution.result.has_installed_yaml_data = true;
        execution.result.installed_yaml_data.local_ignore_state =
            classic::scanner::ScanRunLocalIgnoreYamlDataState::RecoveryRequired;
        execution.result.installed_yaml_data.local_ignore_reset_available = available;

        const auto presentation = classic::gui::presentScanRunExecution(execution);

        QVERIFY(presentation.hasInstalledYamlData);
        QCOMPARE(presentation.installedYamlData.localIgnoreResetAvailable, available);
    }
}

void ScanRunPresentationTests::local_ignore_reset_is_offered_unless_the_run_denied_it()
{
    classic::gui::ScanRunTerminalPresentation terminal{};
    terminal.kind = classic::gui::ScanRunTerminalKind::LocalIgnoreRecoveryRequired;

    // Silence is not a denial. `localIgnoreResetAvailable` defaults to false to mirror the bridge
    // DTO, so reading it without the presence check would withhold a decision that works.
    terminal.hasInstalledYamlData = false;
    QVERIFY(classic::gui::offersLocalIgnoreResetToDefault(terminal));

    terminal.hasInstalledYamlData = true;
    terminal.installedYamlData.localIgnoreResetAvailable = true;
    QVERIFY(classic::gui::offersLocalIgnoreResetToDefault(terminal));

    terminal.installedYamlData.localIgnoreResetAvailable = false;
    QVERIFY(!classic::gui::offersLocalIgnoreResetToDefault(terminal));
}

void ScanRunPresentationTests::setup_failure_presents_checks_updates_configuration_issues_actions_and_fatal_errors()
{
    auto execution = executionWithStatus(classic::scanner::ScanRunContractStatus::SetupFailed);
    execution.result.has_message = true;
    execution.result.message = "FCX setup failed";
    execution.result.has_setup = true;
    execution.result.setup.status = "failed";
    execution.result.setup.has_message = true;
    execution.result.setup.message = "Review the setup details";
    execution.result.setup.rendered_report = "Rendered setup report";

    classic::scanner::ScanRunSetupCheckDto check{};
    check.kind = "game_executable";
    check.state = "failed";
    check.message = "Executable was not found";
    check.details.push_back("Expected Fallout4.exe under the selected game root");
    execution.result.setup.checks.push_back(std::move(check));

    classic::scanner::ScanRunSetupPathUpdateDto update{};
    update.kind = "documents";
    update.path = "C:/Users/Test/Documents/My Games/Fallout4";
    execution.result.setup.path_updates.push_back(std::move(update));

    classic::scanner::FcxIssueDto issue{};
    issue.severity = "warning";
    issue.file_path = "Fallout4.ini";
    issue.has_section = true;
    issue.section_or_empty = "Display";
    issue.setting = "bEnableSomething";
    issue.current_value = "0";
    issue.recommended_value = "1";
    issue.description = "The setting should be enabled";
    execution.result.setup.configuration_issues.push_back(std::move(issue));
    execution.result.setup.actions.push_back("Select the correct game root");
    execution.result.setup.fatal_errors.push_back("Setup could not continue");

    const auto presentation = classic::gui::presentScanRunExecution(execution);

    QCOMPARE(presentation.kind, classic::gui::ScanRunTerminalKind::SetupFailed);
    // The FCX Mode setup projection is still this frontend's, because its four types have not
    // adopted the shared vocabulary and the presentation crate deliberately does not render it. It
    // is grouped in after the rendered lines rather than spliced into them. `FCX setup failed` — the
    // run's own message — is absent from this list on purpose: that sentence is Rust's now.
    //
    // Asserted through `richText`, which is where the projection is grouped in, and separately
    // through `setupDetails`, which is what the worker logs. `message` deliberately carries neither,
    // so the log cannot print the block twice.
    QCOMPARE(presentation.richText, presentation.setupDetails.toHtmlEscaped().replace(QLatin1Char('\n'),
                                                                                      QStringLiteral("<br>")));
    QVERIFY(presentation.message.isEmpty());
    for (const QString& expected :
         {QStringLiteral("Review the setup details"),
          QStringLiteral("Rendered setup report"), QStringLiteral("game_executable"),
          QStringLiteral("Executable was not found"), QStringLiteral("Expected Fallout4.exe"),
          QStringLiteral("documents"), QStringLiteral("C:/Users/Test/Documents/My Games/Fallout4"),
          QStringLiteral("warning"), QStringLiteral("Fallout4.ini"), QStringLiteral("Display"),
          QStringLiteral("bEnableSomething"), QStringLiteral("The setting should be enabled"),
          QStringLiteral("current: 0"), QStringLiteral("recommended: 1"),
          QStringLiteral("Select the correct game root"), QStringLiteral("Setup could not continue")}) {
        QVERIFY2(presentation.setupDetails.contains(expected),
                 qPrintable(QStringLiteral("Setup presentation omitted: %1").arg(expected)));
    }
}

void ScanRunPresentationTests::infrastructure_error_preserves_typed_stage_message_and_path()
{
    // Two things are asserted and they are deliberately different in kind. The terminal kind and the
    // typed stage are the machine-facing surface a consumer matches on, and they stay exactly where
    // they were. The words are Rust's, so they are checked for arriving intact and in order rather
    // than for saying anything in particular.
    classic::scanner::ScanRunContractExecutionResult execution{};
    execution.has_error = true;
    execution.error.stage = classic::scanner::ScanRunContractInfrastructureErrorStage::FormIdDatabaseAccess;
    execution.error.message = "database could not be opened";
    execution.error.has_path = true;
    execution.error.path = "C:/CLASSIC/databases/formids.db";
    using Kind = classic::scanner::ScanRunDisplaySegmentKind;
    appendDisplayLine(execution, classic::scanner::ScanRunDisplaySeverity::Failure,
                      {segment(Kind::Text, "unreal headline"), segment(Kind::Label, "unreal stage")});
    appendDisplayLine(execution, classic::scanner::ScanRunDisplaySeverity::Info,
                      {segment(Kind::Text, "unreal lead"), segment(Kind::Path, "", "C:/CLASSIC/databases/formids.db")});

    const auto presentation = classic::gui::presentScanRunExecution(execution);

    QCOMPARE(presentation.kind, classic::gui::ScanRunTerminalKind::InfrastructureError);
    QCOMPARE(presentation.displayLines.size(), 2);
    QCOMPARE(presentation.message,
             QStringLiteral("unreal headline unreal stage\nunreal lead C:/CLASSIC/databases/formids.db"));
    QVERIFY(presentation.richText.contains(QStringLiteral("file:///C:/CLASSIC/databases/formids.db")));
}

void ScanRunPresentationTests::every_local_ignore_state_renders_its_canonical_display_label()
{
    // Generated and ProceedWithoutIgnore are the two that moved. Both were terse GUI-local
    // inventions that said less than the TUI's wording for the same state.
    using State = classic::scanner::ScanRunLocalIgnoreYamlDataState;
    const std::array<std::pair<State, QString>, 5> expected{{
        {State::Existing, QStringLiteral("existing")},
        {State::Generated, QStringLiteral("generated from selected Main defaults")},
        {State::RecoveryRequired, QStringLiteral("recovery required")},
        {State::ProceedWithoutIgnore, QStringLiteral("proceeded without ignore entries")},
        {State::ResetToDefault, QStringLiteral("reset to default")},
    }};

    for (const auto& [state, label] : expected) {
        QCOMPARE(classic::gui::localIgnoreStateLabel(state), label);
    }
}

void ScanRunPresentationTests::every_installed_yaml_data_provenance_renders_its_canonical_display_label()
{
    // The one enum in this set whose wording never diverged across the three frontends. Pinned
    // anyway: it had no string assertion at all before #167, only typed-enum comparisons, so a core
    // reword would have reached the results view unobserved.
    using Provenance = classic::scanner::ScanRunInstalledYamlDataProvenance;
    const std::array<std::pair<Provenance, QString>, 3> expected{{
        {Provenance::Updated, QStringLiteral("updated")},
        {Provenance::Previous, QStringLiteral("previous")},
        {Provenance::Bundled, QStringLiteral("bundled")},
    }};

    for (const auto& [provenance, label] : expected) {
        QCOMPARE(classic::gui::installedYamlDataProvenanceLabel(provenance), label);
    }
}

void ScanRunPresentationTests::display_line_segments_concatenate_in_the_order_rust_supplied()
{
    // Ordering is the one thing an adapter is forbidden to touch inside a line. The fixture puts
    // every kind in an order no real line uses, so a renderer that grouped by kind, sorted, or
    // dropped a kind it did not recognise would produce a different string.
    using Kind = classic::scanner::ScanRunDisplaySegmentKind;
    const auto line = presentedLine(classic::scanner::ScanRunDisplaySeverity::Info,
                                    {segment(Kind::Emphasis, "zulu"), segment(Kind::Count, "widgets", "", 4),
                                     segment(Kind::Path, "", "C:/alpha/beta.log"), segment(Kind::Label, "yankee"),
                                     segment(Kind::Name, "xray"), segment(Kind::Text, "whiskey")});

    QCOMPARE(classic::gui::renderScanRunDisplayLineAsPlainText(line),
             QStringLiteral("zulu 4 widgets C:/alpha/beta.log yankee xray whiskey"));

    // The rich-text shape carries the same six payloads in the same six positions; only the markup
    // around them is this frontend's.
    const QString rich = classic::gui::renderScanRunDisplayLineAsRichText(line);
    qsizetype cursor = 0;
    for (const QString& payload : {QStringLiteral("zulu"), QStringLiteral("widgets"), QStringLiteral("beta.log"),
                                   QStringLiteral("yankee"), QStringLiteral("xray"), QStringLiteral("whiskey")}) {
        const qsizetype found = rich.indexOf(payload, cursor);
        QVERIFY2(found >= 0, qPrintable(QStringLiteral("rich text dropped %1").arg(payload)));
        cursor = found + payload.size();
    }
}

void ScanRunPresentationTests::a_count_prints_the_noun_rust_resolved_rather_than_re_deciding_it()
{
    // A count crosses the bridge as a value plus the noun Rust already agreed with it, so this
    // frontend has nothing to decide. Both grammatical numbers are asserted, and the singular case
    // is the one that matters: a renderer that appended its own "s" would read "1 logs" here, which
    // is the exact bug the typed count exists to make unrepresentable.
    using Kind = classic::scanner::ScanRunDisplaySegmentKind;
    const auto singular =
        presentedLine(classic::scanner::ScanRunDisplaySeverity::Info, {segment(Kind::Count, "sprocket", "", 1)});
    const auto plural =
        presentedLine(classic::scanner::ScanRunDisplaySeverity::Info, {segment(Kind::Count, "sprockets", "", 12)});

    QCOMPARE(classic::gui::renderScanRunDisplayLineAsPlainText(singular), QStringLiteral("1 sprocket"));
    QCOMPARE(classic::gui::renderScanRunDisplayLineAsPlainText(plural), QStringLiteral("12 sprockets"));
    // The value is emphasised and the noun is not, which is styling; neither word changes.
    // Escaped rather than a raw string literal: moc's preprocessor cannot parse `R"(...)"` inside a
    // `QStringLiteral`, and it reads this file to find the test class.
    QCOMPARE(classic::gui::renderScanRunDisplayLineAsRichText(plural),
             QStringLiteral("<span style=\"color:#e0e0e0;\"><b>12</b> sprockets</span>"));
}

void ScanRunPresentationTests::a_path_segment_renders_as_selectable_actionable_text()
{
    // The point of typing a path as a path rather than as text: this frontend can make it openable
    // without re-deciding any of the words around it. The label stays the whole path, because a
    // shortened one is not a path a user can copy anywhere else.
    using Kind = classic::scanner::ScanRunDisplaySegmentKind;
    const auto line = presentedLine(classic::scanner::ScanRunDisplaySeverity::Success,
                                    {segment(Kind::Text, "unreal report lead"),
                                     segment(Kind::Path, "", "C:/CLASSIC/Crash Logs/crash-AUTOSCAN.md")});

    const QString rich = classic::gui::renderScanRunDisplayLineAsRichText(line);
    QVERIFY(rich.contains(QStringLiteral("href=\"file:///C:/CLASSIC/Crash%20Logs/crash-AUTOSCAN.md\"")));
    QVERIFY(rich.contains(QStringLiteral(">C:/CLASSIC/Crash Logs/crash-AUTOSCAN.md</a>")));
    // Plain text stays a bare path, because that is what reaches log files and one-row surfaces.
    QCOMPARE(classic::gui::renderScanRunDisplayLineAsPlainText(line),
             QStringLiteral("unreal report lead C:/CLASSIC/Crash Logs/crash-AUTOSCAN.md"));
}

void ScanRunPresentationTests::every_severity_maps_to_this_frontends_own_styling()
{
    // The Rust core names no colour — it says only how gravely a line should read. Five distinct
    // colours are asserted rather than five particular ones, because which hue means "failure" is
    // this frontend's to change; what would be a bug is two severities becoming indistinguishable.
    using Severity = classic::scanner::ScanRunDisplaySeverity;
    QSet<QString> colors;
    for (const auto severity :
         {Severity::Info, Severity::Notice, Severity::Warning, Severity::Failure, Severity::Success}) {
        const QString color = classic::gui::scanRunSeverityColor(severity);
        QVERIFY2(color.startsWith(QLatin1Char('#')), qPrintable(color));
        colors.insert(color);
    }
    QCOMPARE(colors.size(), 5);

    using Kind = classic::scanner::ScanRunDisplaySegmentKind;
    const auto failure =
        presentedLine(Severity::Failure, {segment(Kind::Text, "unreal failure line")});
    QVERIFY(classic::gui::renderScanRunDisplayLineAsRichText(failure).contains(
        classic::gui::scanRunSeverityColor(Severity::Failure)));
}

void ScanRunPresentationTests::rendered_lines_reach_the_terminal_presentation_in_rust_order()
{
    // Line order is the adapter's to change, but only deliberately. This asserts the default is to
    // change nothing: the envelope's lines arrive in the presentation in the order the bridge
    // supplied them, and the plain and rich shapes are the same sequence twice.
    using Kind = classic::scanner::ScanRunDisplaySegmentKind;
    auto execution = executionWithStatus(classic::scanner::ScanRunContractStatus::Completed);
    appendDisplayLine(execution, classic::scanner::ScanRunDisplaySeverity::Success,
                      {segment(Kind::Text, "unreal first")});
    appendDisplayLine(execution, classic::scanner::ScanRunDisplaySeverity::Info,
                      {segment(Kind::Text, "unreal second")});
    appendDisplayLine(execution, classic::scanner::ScanRunDisplaySeverity::Notice,
                      {segment(Kind::Text, "unreal third")});

    const auto presentation = classic::gui::presentScanRunExecution(execution);

    QCOMPARE(presentation.kind, classic::gui::ScanRunTerminalKind::Completed);
    QCOMPARE(presentation.displayLines.size(), 3);
    QCOMPARE(presentation.displayLines[0].severity, classic::scanner::ScanRunDisplaySeverity::Success);
    QCOMPARE(presentation.displayLines[2].severity, classic::scanner::ScanRunDisplaySeverity::Notice);
    QCOMPARE(presentation.message, QStringLiteral("unreal first\nunreal second\nunreal third"));
    QVERIFY(presentation.richText.indexOf(QStringLiteral("unreal first")) <
            presentation.richText.indexOf(QStringLiteral("unreal third")));
}

void ScanRunPresentationTests::consumed_resume_error_preserves_typed_context()
{
    // The stable resume error code is the point of this case. The rendered sentences deliberately
    // omit it — a code is machine-facing identity, not prose — so it has to survive on the DTO, or
    // a consumer that matches on it would have nothing left to match.
    classic::scanner::ScanRunContractExecutionResult execution{};
    execution.has_resume_error = true;
    execution.resume_error.kind = classic::scanner::ScanRunContractResumeErrorKind::ContinuationConsumed;
    execution.resume_error.code = "scan_run_continuation_consumed";
    execution.resume_error.message = "Crash Log Scan Run continuation was already consumed";
    using Kind = classic::scanner::ScanRunDisplaySegmentKind;
    appendDisplayLine(execution, classic::scanner::ScanRunDisplaySeverity::Failure,
                      {segment(Kind::Text, "unreal recovery headline")});

    const auto presentation = classic::gui::presentScanRunExecution(execution);

    QCOMPARE(presentation.kind, classic::gui::ScanRunTerminalKind::InfrastructureError);
    QCOMPARE(presentation.message, QStringLiteral("unreal recovery headline"));
    QVERIFY2(!presentation.message.contains(QStringLiteral("scan_run_continuation_consumed")),
             "a Vocabulary Token must not reach a sentence a person reads");
    QCOMPARE(classic::toQString(execution.resume_error.code), QStringLiteral("scan_run_continuation_consumed"));
}

void ScanRunPresentationTests::reset_resume_error_preserves_operational_context()
{
    // Every optional field a reset failure can carry stays on the envelope for a consumer, and the
    // rendered lines describe them for a person. Both halves matter: the durability receipt in
    // particular is how a user learns their Local Ignore file was already rewritten and which bytes
    // were preserved, and dropping either half would make this frontend less informative than the
    // native CLI on the one outcome where that matters most.
    classic::scanner::ScanRunContractExecutionResult execution{};
    execution.has_resume_error = true;
    execution.resume_error.kind =
        classic::scanner::ScanRunContractResumeErrorKind::LocalIgnoreResetReplacementFailure;
    execution.resume_error.code = "local_ignore_reset_replacement_failure";
    execution.resume_error.message = "could not publish retained defaults";
    execution.resume_error.has_path = true;
    execution.resume_error.path = "C:/CLASSIC/CLASSIC Data/CLASSIC Ignore.yaml";
    execution.resume_error.has_stage = true;
    execution.resume_error.stage = classic::scanner::ScanRunLocalIgnoreResetFailureStage::Publish;
    execution.resume_error.has_expected_identity = true;
    execution.resume_error.expected_identity.sha256 = "expected-hash";
    execution.resume_error.expected_identity.byte_len = 31;
    execution.resume_error.has_actual_identity = true;
    execution.resume_error.actual_identity.sha256 = "actual-hash";
    execution.resume_error.actual_identity.byte_len = 32;
    execution.resume_error.has_backup_path = true;
    execution.resume_error.backup_path = "C:/CLASSIC/CLASSIC Backup/CLASSIC Ignore.backup.yaml";
    using Kind = classic::scanner::ScanRunDisplaySegmentKind;
    appendDisplayLine(execution, classic::scanner::ScanRunDisplaySeverity::Failure,
                      {segment(Kind::Text, "unreal reset headline")});
    appendDisplayLine(execution, classic::scanner::ScanRunDisplaySeverity::Info,
                      {segment(Kind::Text, "unreal backup lead"),
                       segment(Kind::Path, "", "C:/CLASSIC/CLASSIC Backup/CLASSIC Ignore.backup.yaml")});

    const auto presentation = classic::gui::presentScanRunExecution(execution);

    QCOMPARE(presentation.kind, classic::gui::ScanRunTerminalKind::InfrastructureError);
    QCOMPARE(presentation.message, QStringLiteral("unreal reset headline\n"
                                                  "unreal backup lead C:/CLASSIC/CLASSIC Backup/CLASSIC "
                                                  "Ignore.backup.yaml"));
    QVERIFY(execution.resume_error.has_stage);
    QCOMPARE(execution.resume_error.stage, classic::scanner::ScanRunLocalIgnoreResetFailureStage::Publish);
    QVERIFY(execution.resume_error.has_expected_identity);
    QVERIFY(execution.resume_error.has_actual_identity);
    QVERIFY(execution.resume_error.has_backup_path);
}

void ScanRunPresentationTests::invalid_execution_envelope_is_presented_as_an_infrastructure_error()
{
    const classic::scanner::ScanRunContractExecutionResult execution{};

    const auto presentation = classic::gui::presentScanRunExecution(execution);

    QCOMPARE(presentation.kind, classic::gui::ScanRunTerminalKind::InfrastructureError);
    QCOMPARE(presentation.message,
             QStringLiteral("Crash Log Scan Run returned neither a result nor an infrastructure error."));
}

QTEST_MAIN(ScanRunPresentationTests)
#include "test_scanrunpresentation.moc"
