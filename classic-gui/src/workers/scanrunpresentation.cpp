#include "scanrunpresentation.h"

#include "core/rust_qt_bridge.h"

#include <QDir>
#include <QFileInfo>
#include <QSet>

namespace classic::gui {
namespace {

QString failureStageName(classic::scanner::ScanRunContractLogFailureStage stage)
{
    using Stage = classic::scanner::ScanRunContractLogFailureStage;
    switch (stage) {
    case Stage::Analysis:
        return QStringLiteral("analysis");
    case Stage::ReportWrite:
        return QStringLiteral("report write");
    case Stage::UnsolvedLogsFinalization:
        return QStringLiteral("Unsolved Logs finalization");
    }
    return QStringLiteral("unknown stage");
}

QString infrastructureStageName(classic::scanner::ScanRunContractInfrastructureErrorStage stage)
{
    using Stage = classic::scanner::ScanRunContractInfrastructureErrorStage;
    switch (stage) {
    case Stage::RequestValidation:
        return QStringLiteral("request validation");
    case Stage::Discovery:
        return QStringLiteral("discovery");
    case Stage::Intake:
        return QStringLiteral("intake");
    case Stage::FormIdDatabaseAccess:
        return QStringLiteral("FormID database access");
    case Stage::Initialization:
        return QStringLiteral("initialization");
    case Stage::InternalInvariant:
        return QStringLiteral("internal invariant validation");
    }
    return QStringLiteral("unknown stage");
}

QString setupDetails(const classic::scanner::ScanRunContractRunResult& result)
{
    QStringList lines;
    if (!result.has_setup) {
        return {};
    }

    lines.append(QStringLiteral("FCX setup: %1").arg(classic::toQString(result.setup.status)));
    if (result.setup.has_message) {
        lines.append(classic::toQString(result.setup.message));
    }
    if (!result.setup.rendered_report.empty()) {
        lines.append(classic::toQString(result.setup.rendered_report));
    }
    for (const auto& check : result.setup.checks) {
        lines.append(QStringLiteral("[%1] %2: %3")
                         .arg(classic::toQString(check.state), classic::toQString(check.kind),
                              classic::toQString(check.message)));
        for (const auto& detail : check.details) {
            lines.append(QStringLiteral("  %1").arg(classic::toQString(detail)));
        }
    }
    for (const auto& update : result.setup.path_updates) {
        lines.append(QStringLiteral("Proposed %1 path: %2")
                         .arg(classic::toQString(update.kind), classic::toQString(update.path)));
    }
    for (const auto& issue : result.setup.configuration_issues) {
        const QString section =
            issue.has_section ? QStringLiteral("/[%1]").arg(classic::toQString(issue.section_or_empty)) : QString{};
        lines.append(QStringLiteral("[%1] %2%3 %4: %5 (current: %6, recommended: %7)")
                         .arg(classic::toQString(issue.severity), classic::toQString(issue.file_path), section,
                              classic::toQString(issue.setting), classic::toQString(issue.description),
                              classic::toQString(issue.current_value), classic::toQString(issue.recommended_value)));
    }
    for (const auto& action : result.setup.actions) {
        lines.append(QStringLiteral("Action: %1").arg(classic::toQString(action)));
    }
    for (const auto& error : result.setup.fatal_errors) {
        lines.append(QStringLiteral("Setup error: %1").arg(classic::toQString(error)));
    }
    return lines.join('\n');
}

ScanRunLogPresentation presentLog(const classic::scanner::ScanRunContractLogResult& log)
{
    ScanRunLogPresentation presentation;
    presentation.discoveryIndex = static_cast<int>(log.discovery_index);
    presentation.crashLog = classic::toQString(log.crash_log);
    if (log.has_autoscan_report) {
        presentation.autoscanReport = classic::toQString(log.autoscan_report);
    }
    presentation.message = log.has_message ? classic::toQString(log.message) : QString{};
    presentation.movedToUnsolvedLogs = log.moved_to_unsolved_logs;

    using Disposition = classic::scanner::ScanRunContractLogDisposition;
    switch (log.disposition) {
    case Disposition::Succeeded:
        presentation.succeeded = true;
        break;
    case Disposition::Failed:
        presentation.failed = true;
        break;
    case Disposition::CancelledBeforeStart:
        presentation.cancelledBeforeStart = true;
        break;
    }

    for (const auto& failure : log.failures) {
        presentation.failures.append(
            QStringLiteral("%1: %2").arg(failureStageName(failure.stage), classic::toQString(failure.message)));
    }
    return presentation;
}

} // namespace

QString formatScanRunRejections(const classic::scanner::ScanRunContractDiscoveryResult& discovery)
{
    if (discovery.rejected_inputs.empty()) {
        return {};
    }

    QStringList lines;
    const auto count = discovery.rejected_inputs.size();
    lines.append(QStringLiteral("Ignored %1 targeted input%2:").arg(count).arg(count == 1 ? "" : "s"));
    for (const auto& rejection : discovery.rejected_inputs) {
        lines.append(
            QStringLiteral("- %1 (%2)").arg(classic::toQString(rejection.path), classic::toQString(rejection.reason)));
    }
    return lines.join('\n');
}

QStringList scanRunReportDirectories(const classic::scanner::ScanRunContractDiscoveryResult& discovery)
{
    QStringList directories;
    QSet<QString> seen;
    for (const auto& accepted : discovery.accepted_logs) {
        const QString directory = QDir::cleanPath(QFileInfo(classic::toQString(accepted)).absolutePath());
        const QString key = directory.toLower();
        if (!directory.isEmpty() && !seen.contains(key)) {
            seen.insert(key);
            directories.append(directory);
        }
    }
    return directories;
}

ScanRunTerminalPresentation presentScanRunExecution(const classic::scanner::ScanRunContractExecutionResult& execution)
{
    ScanRunTerminalPresentation presentation;
    if (execution.has_error) {
        presentation.kind = ScanRunTerminalKind::InfrastructureError;
        presentation.message =
            QStringLiteral("Crash Log Scan Run failed during %1: %2")
                .arg(infrastructureStageName(execution.error.stage), classic::toQString(execution.error.message));
        if (execution.error.has_path) {
            presentation.message.append(QStringLiteral(" (path: %1)").arg(classic::toQString(execution.error.path)));
        }
        return presentation;
    }

    if (!execution.has_result) {
        presentation.kind = ScanRunTerminalKind::InfrastructureError;
        presentation.message =
            QStringLiteral("Crash Log Scan Run returned neither a result nor an infrastructure error.");
        return presentation;
    }

    const auto& result = execution.result;
    presentation.total = static_cast<int>(result.total);
    presentation.succeeded = static_cast<int>(result.succeeded);
    presentation.failed = static_cast<int>(result.failed);
    presentation.cancelled = static_cast<int>(result.cancelled);
    presentation.setupDetails = setupDetails(result);
    presentation.logs.reserve(static_cast<qsizetype>(result.logs.size()));
    for (const auto& log : result.logs) {
        presentation.logs.append(presentLog(log));
    }

    using Status = classic::scanner::ScanRunContractStatus;
    switch (result.status) {
    case Status::Completed:
        presentation.kind = ScanRunTerminalKind::Completed;
        presentation.message =
            result.has_message ? classic::toQString(result.message) : QStringLiteral("Scan complete.");
        break;
    case Status::NoCrashLogsFound:
        presentation.kind = ScanRunTerminalKind::NoCrashLogsFound;
        presentation.message =
            result.has_message ? classic::toQString(result.message) : QStringLiteral("No crash logs found.");
        if (result.has_discovery) {
            for (const auto& location : result.discovery.searched_locations) {
                presentation.message.append(QStringLiteral("\nSearched: %1").arg(classic::toQString(location)));
            }
        }
        break;
    case Status::SetupFailed:
        presentation.kind = ScanRunTerminalKind::SetupFailed;
        presentation.message =
            result.has_message ? classic::toQString(result.message) : QStringLiteral("Crash Log Scan setup failed.");
        if (!presentation.setupDetails.isEmpty()) {
            presentation.message.append(QStringLiteral("\n") + presentation.setupDetails);
        }
        break;
    case Status::CancelledBeforeDiscovery:
        presentation.kind = ScanRunTerminalKind::CancelledBeforeDiscovery;
        presentation.message = QStringLiteral("Scan cancelled safely before discovery completed.");
        break;
    case Status::Cancelled:
        presentation.kind = ScanRunTerminalKind::Cancelled;
        presentation.message = QStringLiteral("Scan cancelled safely: %1 completed, %2 not started.")
                                   .arg(result.succeeded + result.failed)
                                   .arg(result.cancelled);
        break;
    }
    return presentation;
}

} // namespace classic::gui
