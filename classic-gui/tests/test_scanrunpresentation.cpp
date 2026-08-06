#include <QTemporaryDir>
#include <QtTest/QtTest>

#include "workers/scanrunpresentation.h"

#include <array>
#include <cstddef>
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
    // Exhaustive Display Label coverage, added with #167 when the GUI stopped owning the wording.
    //
    // These pin every variant of every enum the GUI renders a label for, against the canonical
    // strings the Rust core owns. Quoting them as literals here is deliberate and is the one place
    // in this frontend where that is right: it is how a wording a ticket settled gets pinned across
    // the binding boundary, so a core-side reword has to be a decision rather than an accident.
    //
    // They exist because the measurement on #167 found the GUI shipping six stale labels with the
    // entire Qt suite green over all six. The only labels any test named were ones the CLI, the
    // GUI, and the TUI already agreed about, so the assertions were structurally incapable of
    // catching the drift they were nearest to.
    //
    // Per-log failure stage is absent from this block because
    // `terminal_logs_preserve_discovery_order_and_structured_dispositions` already compares all
    // three of its labels in one exact QStringList, and per-log disposition is absent because the
    // GUI renders no label for it — see the decision recorded at `presentLog`.
    void every_local_ignore_state_renders_its_canonical_display_label();
    void every_installed_yaml_data_provenance_renders_its_canonical_display_label();
    void every_installed_yaml_data_diagnostic_kind_renders_its_canonical_display_label();
    void every_infrastructure_error_stage_renders_its_canonical_display_label();
    void every_local_ignore_reset_failure_stage_renders_its_canonical_display_label();
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

    const QString warning = classic::gui::formatInstalledYamlDataWarning(installed);

    QVERIFY(!warning.isEmpty());
    QVERIFY(warning.contains(QStringLiteral("incompatible schema")));
    QVERIFY(warning.contains(QStringLiteral("updated Main schema 9.0 is newer than this client supports")));
    QVERIFY(warning.contains(QStringLiteral("Main")));
    QVERIFY(warning.contains(QStringLiteral("C:/CLASSIC/cache/CLASSIC Main.yaml")));
    // The durable backup location is the one fact a user needs to recover their prior edits.
    QVERIFY(warning.contains(QStringLiteral("C:/CLASSIC/CLASSIC Backup/CLASSIC Ignore.yaml")));
    QVERIFY(warning.contains(QStringLiteral("malformed-hash")));
    QVERIFY2(!warning.contains(QStringLiteral("generated missing Local Ignore YAML Data")),
             "expected-success generation must not be reported as a warning");
    QVERIFY2(!warning.contains(QStringLiteral("could not be parsed")),
             "a Local Ignore problem the user already answered must not be restated");
    QVERIFY2(!warning.contains(QStringLiteral("reset malformed Local Ignore from retained defaults")),
             "the reset diagnostic is superseded by the durable backup paragraph");
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

    QVERIFY(classic::gui::formatInstalledYamlDataWarning(proceeded).isEmpty());

    // A Main or game selection problem is unrelated to the answered question and still warns, which
    // is what the missing role distinguishes.
    classic::gui::ScanRunInstalledYamlDataDiagnosticPresentation selectionFallback{};
    selectionFallback.kind = classic::scanner::ScanRunInstalledYamlDataDiagnosticKind::InvalidRoleData;
    selectionFallback.message = QStringLiteral("updated game YAML Data failed role validation");
    selectionFallback.hasRole = true;
    selectionFallback.role = classic::scanner::ScanRunInstalledYamlDataRole::Game;
    proceeded.diagnostics.append(selectionFallback);

    const QString warning = classic::gui::formatInstalledYamlDataWarning(proceeded);
    QVERIFY(warning.contains(QStringLiteral("updated game YAML Data failed role validation")));
    QVERIFY(!warning.contains(QStringLiteral("could not be parsed")));
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
    for (const auto& [stage, message] : {
             std::pair{classic::scanner::ScanRunContractLogFailureStage::Analysis, "analysis failed"},
             std::pair{classic::scanner::ScanRunContractLogFailureStage::ReportWrite, "report write failed"},
             std::pair{classic::scanner::ScanRunContractLogFailureStage::UnsolvedLogsFinalization, "movement failed"},
         }) {
        classic::scanner::ScanRunContractLogFailure failure{};
        failure.stage = stage;
        failure.message = message;
        failed.failures.push_back(std::move(failure));
    }
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
    QCOMPARE(
        presentation.logs[1].failures,
        QStringList({QStringLiteral("analysis: analysis failed"), QStringLiteral("report write: report write failed"),
                     QStringLiteral("Unsolved Logs finalization: movement failed")}));

    QCOMPARE(presentation.logs[2].discoveryIndex, 2);
    QVERIFY(presentation.logs[2].cancelledBeforeStart);
    QVERIFY(!presentation.logs[2].succeeded);
    QVERIFY(!presentation.logs[2].failed);
}

void ScanRunPresentationTests::expected_lifecycle_statuses_remain_distinct_from_infrastructure_errors()
{
    auto noLogs = executionWithStatus(classic::scanner::ScanRunContractStatus::NoCrashLogsFound);
    noLogs.result.has_discovery = true;
    noLogs.result.discovery.searched_locations.push_back("C:/searched/Crash Logs");
    const auto noLogsPresentation = classic::gui::presentScanRunExecution(noLogs);
    QCOMPARE(noLogsPresentation.kind, classic::gui::ScanRunTerminalKind::NoCrashLogsFound);
    QVERIFY(noLogsPresentation.message.contains(QStringLiteral("No crash logs found")));
    QVERIFY(noLogsPresentation.message.contains(QStringLiteral("C:/searched/Crash Logs")));

    const auto beforeDiscovery = classic::gui::presentScanRunExecution(
        executionWithStatus(classic::scanner::ScanRunContractStatus::CancelledBeforeDiscovery));
    QCOMPARE(beforeDiscovery.kind, classic::gui::ScanRunTerminalKind::CancelledBeforeDiscovery);
    QVERIFY(beforeDiscovery.message.contains(QStringLiteral("before discovery")));

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
    QVERIFY(cancelledPresentation.message.contains(QStringLiteral("3 completed")));
    QVERIFY(cancelledPresentation.message.contains(QStringLiteral("2 not started")));
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
    QCOMPARE(presentation.message, QStringLiteral("Local Ignore recovery is required"));
    QVERIFY(presentation.hasInstalledYamlData);
    QCOMPARE(presentation.installedYamlData.localIgnoreState,
             classic::scanner::ScanRunLocalIgnoreYamlDataState::RecoveryRequired);
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
    for (const QString& expected :
         {QStringLiteral("FCX setup failed"), QStringLiteral("Review the setup details"),
          QStringLiteral("Rendered setup report"), QStringLiteral("game_executable"),
          QStringLiteral("Executable was not found"), QStringLiteral("Expected Fallout4.exe"),
          QStringLiteral("documents"), QStringLiteral("C:/Users/Test/Documents/My Games/Fallout4"),
          QStringLiteral("warning"), QStringLiteral("Fallout4.ini"), QStringLiteral("Display"),
          QStringLiteral("bEnableSomething"), QStringLiteral("The setting should be enabled"),
          QStringLiteral("current: 0"), QStringLiteral("recommended: 1"),
          QStringLiteral("Select the correct game root"), QStringLiteral("Setup could not continue")}) {
        QVERIFY2(presentation.message.contains(expected),
                 qPrintable(QStringLiteral("Setup presentation omitted: %1").arg(expected)));
    }
}

void ScanRunPresentationTests::infrastructure_error_preserves_typed_stage_message_and_path()
{
    classic::scanner::ScanRunContractExecutionResult execution{};
    execution.has_error = true;
    execution.error.stage = classic::scanner::ScanRunContractInfrastructureErrorStage::FormIdDatabaseAccess;
    execution.error.message = "database could not be opened";
    execution.error.has_path = true;
    execution.error.path = "C:/CLASSIC/databases/formids.db";

    const auto presentation = classic::gui::presentScanRunExecution(execution);

    QCOMPARE(presentation.kind, classic::gui::ScanRunTerminalKind::InfrastructureError);
    QCOMPARE(presentation.message,
             QStringLiteral("Crash Log Scan Run failed during FormID database access: database could not be opened "
                            "(path: C:/CLASSIC/databases/formids.db)"));
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

void ScanRunPresentationTests::every_installed_yaml_data_diagnostic_kind_renders_its_canonical_display_label()
{
    // Six of these ten moved: four gained the noun that says the label describes a failure rather
    // than a status, and two gained the glossary capitalization of Local Ignore as a domain term.
    // Asserted through formatInstalledYamlDataDiagnostic rather than the accessor, so the rendered
    // `<label>: <message>` frame the user actually reads is what is pinned.
    using Kind = classic::scanner::ScanRunInstalledYamlDataDiagnosticKind;
    const std::array<std::pair<Kind, QString>, 10> expected{{
        {Kind::CacheUnavailable, QStringLiteral("update cache unavailable")},
        {Kind::Missing, QStringLiteral("missing candidate")},
        {Kind::Read, QStringLiteral("read failure")},
        {Kind::InvalidUtf8, QStringLiteral("invalid UTF-8")},
        {Kind::Parse, QStringLiteral("parse failure")},
        {Kind::InvalidSchema, QStringLiteral("invalid schema")},
        {Kind::IncompatibleSchema, QStringLiteral("incompatible schema")},
        {Kind::InvalidRoleData, QStringLiteral("invalid role data")},
        {Kind::LocalIgnoreGenerated, QStringLiteral("Local Ignore generated")},
        {Kind::LocalIgnoreReset, QStringLiteral("Local Ignore reset")},
    }};

    for (const auto& [kind, label] : expected) {
        classic::gui::ScanRunInstalledYamlDataDiagnosticPresentation diagnostic{};
        diagnostic.kind = kind;
        diagnostic.message = QStringLiteral("diagnostic detail");
        QCOMPARE(classic::gui::formatInstalledYamlDataDiagnostic(diagnostic),
                 QStringLiteral("%1: diagnostic detail").arg(label));
    }
}

void ScanRunPresentationTests::every_infrastructure_error_stage_renders_its_canonical_display_label()
{
    // None of these six moved, but only FormIdDatabaseAccess had an assertion before #167. The
    // other five reach the user through the same fatal banner and were unpinned.
    using Stage = classic::scanner::ScanRunContractInfrastructureErrorStage;
    const std::array<std::pair<Stage, QString>, 6> expected{{
        {Stage::RequestValidation, QStringLiteral("request validation")},
        {Stage::Discovery, QStringLiteral("discovery")},
        {Stage::Intake, QStringLiteral("intake")},
        {Stage::FormIdDatabaseAccess, QStringLiteral("FormID database access")},
        {Stage::Initialization, QStringLiteral("initialization")},
        {Stage::InternalInvariant, QStringLiteral("internal invariant validation")},
    }};

    for (const auto& [stage, label] : expected) {
        classic::scanner::ScanRunContractExecutionResult execution{};
        execution.has_error = true;
        execution.error.stage = stage;
        execution.error.message = "run could not continue";

        const auto presentation = classic::gui::presentScanRunExecution(execution);

        QCOMPARE(presentation.kind, classic::gui::ScanRunTerminalKind::InfrastructureError);
        QCOMPARE(presentation.message,
                 QStringLiteral("Crash Log Scan Run failed during %1: run could not continue").arg(label));
    }
}

void ScanRunPresentationTests::every_local_ignore_reset_failure_stage_renders_its_canonical_display_label()
{
    // None of these five moved either — they delegate to the shared durable publication stage
    // vocabulary, which deliberately keeps each label equal to its token. Pinned because only
    // Publish had an assertion, and because delegation means a reword in the publication crate now
    // reaches this banner.
    using Stage = classic::scanner::ScanRunLocalIgnoreResetFailureStage;
    const std::array<std::pair<Stage, QString>, 5> expected{{
        {Stage::Create, QStringLiteral("create")},
        {Stage::Write, QStringLiteral("write")},
        {Stage::Flush, QStringLiteral("flush")},
        {Stage::Sync, QStringLiteral("sync")},
        {Stage::Publish, QStringLiteral("publish")},
    }};

    for (const auto& [stage, label] : expected) {
        classic::scanner::ScanRunContractExecutionResult execution{};
        execution.has_resume_error = true;
        execution.resume_error.kind =
            classic::scanner::ScanRunContractResumeErrorKind::LocalIgnoreResetReplacementFailure;
        execution.resume_error.code = "local_ignore_reset_replacement_failure";
        execution.resume_error.message = "reset could not complete";
        execution.resume_error.has_stage = true;
        execution.resume_error.stage = stage;

        const auto presentation = classic::gui::presentScanRunExecution(execution);

        QCOMPARE(presentation.message,
                 QStringLiteral("Crash Log Scan recovery failed (local_ignore_reset_replacement_failure): "
                                "reset could not complete\nStage: %1")
                     .arg(label));
    }
}

void ScanRunPresentationTests::consumed_resume_error_preserves_typed_context()
{
    classic::scanner::ScanRunContractExecutionResult execution{};
    execution.has_resume_error = true;
    execution.resume_error.kind = classic::scanner::ScanRunContractResumeErrorKind::ContinuationConsumed;
    execution.resume_error.code = "scan_run_continuation_consumed";
    execution.resume_error.message = "Crash Log Scan Run continuation was already consumed";

    const auto presentation = classic::gui::presentScanRunExecution(execution);

    QCOMPARE(presentation.kind, classic::gui::ScanRunTerminalKind::InfrastructureError);
    QCOMPARE(presentation.message,
             QStringLiteral("Crash Log Scan recovery failed (scan_run_continuation_consumed): "
                            "Crash Log Scan Run continuation was already consumed"));
}

void ScanRunPresentationTests::reset_resume_error_preserves_operational_context()
{
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

    const auto presentation = classic::gui::presentScanRunExecution(execution);

    QCOMPARE(presentation.kind, classic::gui::ScanRunTerminalKind::InfrastructureError);
    QCOMPARE(presentation.message,
             QStringLiteral("Crash Log Scan recovery failed (local_ignore_reset_replacement_failure): "
                            "could not publish retained defaults\n"
                            "Path: C:/CLASSIC/CLASSIC Data/CLASSIC Ignore.yaml\n"
                            "Stage: publish\n"
                            "Expected identity: sha256 expected-hash, 31 bytes\n"
                            "Actual identity: sha256 actual-hash, 32 bytes\n"
                            "Verified backup: C:/CLASSIC/CLASSIC Backup/CLASSIC Ignore.backup.yaml"));
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
