#include <QTemporaryDir>
#include <QtTest/QtTest>

#include "workers/scanrunpresentation.h"

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
    void setup_failure_presents_checks_updates_configuration_issues_actions_and_fatal_errors();
    void installed_yaml_data_presence_preserves_generated_ignore_metadata_and_diagnostics();
    void infrastructure_error_preserves_typed_stage_message_and_path();
    void invalid_execution_envelope_is_presented_as_an_infrastructure_error();
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
