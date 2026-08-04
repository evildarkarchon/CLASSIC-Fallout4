#include "scanrunpresentation.h"

#include "core/rust_qt_bridge.h"

#include <QDir>
#include <QFileInfo>
#include <QSet>
#include <QStringList>

#include <utility>

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

/// Returns the stable user-facing name for a Local Ignore reset publication stage.
QString resetFailureStageName(classic::scanner::ScanRunLocalIgnoreResetFailureStage stage)
{
    using Stage = classic::scanner::ScanRunLocalIgnoreResetFailureStage;
    switch (stage) {
    case Stage::Create:
        return QStringLiteral("create");
    case Stage::Write:
        return QStringLiteral("write");
    case Stage::Flush:
        return QStringLiteral("flush");
    case Stage::Sync:
        return QStringLiteral("sync");
    case Stage::Publish:
        return QStringLiteral("publish");
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

/// Projects one exact selected YAML Data file into Qt-owned strings and scalar metadata.
ScanRunInstalledYamlDataFilePresentation presentInstalledYamlDataFile(
    const classic::scanner::ScanRunInspectedYamlDataFileDto& file)
{
    ScanRunInstalledYamlDataFilePresentation presentation;
    presentation.role = file.role;
    presentation.provenance = file.provenance;
    presentation.schemaVersion = classic::toQString(file.schema_version);
    presentation.sha256 = classic::toQString(file.sha256);
    presentation.byteLength = file.byte_len;
    return presentation;
}

/// Projects Installed YAML Data run metadata without flattening diagnostic presence flags.
ScanRunInstalledYamlDataPresentation presentInstalledYamlData(
    const classic::scanner::ScanRunInstalledYamlDataRunDataDto& installed)
{
    ScanRunInstalledYamlDataPresentation presentation;
    presentation.main = presentInstalledYamlDataFile(installed.main);
    presentation.gameFile = presentInstalledYamlDataFile(installed.game_file);
    presentation.localIgnoreState = installed.local_ignore_state;
    presentation.localIgnoreIdentity.sha256 = classic::toQString(installed.local_ignore_identity.sha256);
    presentation.localIgnoreIdentity.byteLength = installed.local_ignore_identity.byte_len;
    presentation.hasLocalIgnoreReset = installed.has_local_ignore_reset;
    if (installed.has_local_ignore_reset) {
        const auto& reset = installed.local_ignore_reset;
        presentation.localIgnoreReset.localIgnorePath = classic::toQString(reset.local_ignore_path);
        presentation.localIgnoreReset.backupPath = classic::toQString(reset.backup_path);
        presentation.localIgnoreReset.malformedIdentity.sha256 = classic::toQString(reset.malformed_identity.sha256);
        presentation.localIgnoreReset.malformedIdentity.byteLength = reset.malformed_identity.byte_len;
        presentation.localIgnoreReset.backupIdentity.sha256 = classic::toQString(reset.backup_identity.sha256);
        presentation.localIgnoreReset.backupIdentity.byteLength = reset.backup_identity.byte_len;
        presentation.localIgnoreReset.replacementIdentity.sha256 = classic::toQString(reset.replacement_identity.sha256);
        presentation.localIgnoreReset.replacementIdentity.byteLength = reset.replacement_identity.byte_len;
    }
    presentation.diagnostics.reserve(static_cast<qsizetype>(installed.diagnostics.size()));
    for (const auto& diagnostic : installed.diagnostics) {
        ScanRunInstalledYamlDataDiagnosticPresentation mapped;
        mapped.hasRole = diagnostic.has_role;
        mapped.role = diagnostic.role;
        mapped.hasCandidate = diagnostic.has_candidate;
        mapped.candidate = diagnostic.candidate;
        mapped.hasPath = diagnostic.has_path;
        mapped.path = diagnostic.has_path ? classic::toQString(diagnostic.path) : QString{};
        mapped.kind = diagnostic.kind;
        mapped.message = classic::toQString(diagnostic.message);
        presentation.diagnostics.append(std::move(mapped));
    }
    return presentation;
}

} // namespace

QString localIgnoreStateLabel(classic::scanner::ScanRunLocalIgnoreYamlDataState state)
{
    using State = classic::scanner::ScanRunLocalIgnoreYamlDataState;
    switch (state) {
    case State::Existing:
        return QStringLiteral("existing");
    case State::Generated:
        return QStringLiteral("generated");
    case State::RecoveryRequired:
        return QStringLiteral("recovery required");
    case State::ProceedWithoutIgnore:
        return QStringLiteral("proceed without Ignore");
    case State::ResetToDefault:
        return QStringLiteral("reset to default");
    }
    return QStringLiteral("unknown");
}

QString installedYamlDataProvenanceLabel(classic::scanner::ScanRunInstalledYamlDataProvenance provenance)
{
    using Provenance = classic::scanner::ScanRunInstalledYamlDataProvenance;
    switch (provenance) {
    case Provenance::Updated:
        return QStringLiteral("updated");
    case Provenance::Previous:
        return QStringLiteral("previous");
    case Provenance::Bundled:
        return QStringLiteral("bundled");
    }
    return QStringLiteral("unknown");
}

QString installedYamlDataDiagnosticKindLabel(classic::scanner::ScanRunInstalledYamlDataDiagnosticKind kind)
{
    using Kind = classic::scanner::ScanRunInstalledYamlDataDiagnosticKind;
    switch (kind) {
    case Kind::CacheUnavailable:
        return QStringLiteral("cache unavailable");
    case Kind::Missing:
        return QStringLiteral("missing");
    case Kind::Read:
        return QStringLiteral("read");
    case Kind::InvalidUtf8:
        return QStringLiteral("invalid UTF-8");
    case Kind::Parse:
        return QStringLiteral("parse");
    case Kind::InvalidSchema:
        return QStringLiteral("invalid schema");
    case Kind::IncompatibleSchema:
        return QStringLiteral("incompatible schema");
    case Kind::InvalidRoleData:
        return QStringLiteral("invalid role data");
    case Kind::LocalIgnoreGenerated:
        return QStringLiteral("local ignore generated");
    case Kind::LocalIgnoreReset:
        return QStringLiteral("local ignore reset");
    }
    return QStringLiteral("unknown");
}

QString formatInstalledYamlDataDiagnostic(const ScanRunInstalledYamlDataDiagnosticPresentation& diagnostic)
{
    QStringList context;
    if (diagnostic.hasRole) {
        context.append(diagnostic.role == classic::scanner::ScanRunInstalledYamlDataRole::Main
                           ? QStringLiteral("Main")
                           : QStringLiteral("Game"));
    }
    if (diagnostic.hasCandidate) {
        context.append(installedYamlDataProvenanceLabel(diagnostic.candidate));
    }
    if (diagnostic.hasPath) {
        context.append(diagnostic.path);
    }
    const QString suffix = context.isEmpty() ? QString{} : QStringLiteral(" [%1]").arg(context.join(", "));
    return QStringLiteral("%1: %2%3")
        .arg(installedYamlDataDiagnosticKindLabel(diagnostic.kind), diagnostic.message, suffix);
}

QString formatInstalledYamlDataWarning(const ScanRunInstalledYamlDataPresentation& installedYamlData)
{
    if (installedYamlData.localIgnoreState == classic::scanner::ScanRunLocalIgnoreYamlDataState::RecoveryRequired) {
        // This is the pre-decision snapshot published while the run still awaits a recovery choice.
        // The choice dialog is that snapshot's presentation, so a warning here would double-report it
        // and would interrupt the user before they can answer.
        return {};
    }

    using State = classic::scanner::ScanRunLocalIgnoreYamlDataState;
    const bool localIgnoreWasDecided = installedYamlData.localIgnoreState == State::ProceedWithoutIgnore ||
                                       installedYamlData.localIgnoreState == State::ResetToDefault;

    QStringList lines;
    for (const auto& diagnostic : installedYamlData.diagnostics) {
        if (diagnostic.kind == classic::scanner::ScanRunInstalledYamlDataDiagnosticKind::LocalIgnoreGenerated) {
            // Generating an absent Local Ignore file is an expected successful path, not a warning.
            continue;
        }
        if (localIgnoreWasDecided && !diagnostic.hasRole) {
            // Local Ignore diagnostics carry no Main/Game role, which is what distinguishes them
            // from selection fallback. The recovery dialog already showed this exact problem and the
            // user answered it, so restating it would warn about a resolved question. Anything the
            // answer did not cover is reported by the durable reset paragraph below.
            continue;
        }
        lines.append(QStringLiteral("- ") + formatInstalledYamlDataDiagnostic(diagnostic));
    }

    if (lines.isEmpty() && !installedYamlData.hasLocalIgnoreReset) {
        return {};
    }

    QStringList sections;
    if (!lines.isEmpty()) {
        sections.append(QStringLiteral("CLASSIC could not use some of its installed YAML Data for this scan:\n\n") +
                        lines.join(QStringLiteral("\n")));
    }
    if (installedYamlData.hasLocalIgnoreReset) {
        // The backup location is the only way a user recovers the edits the reset replaced.
        sections.append(QStringLiteral("Your malformed %1 was backed up byte-exactly to %2 (%3 bytes, sha256 %4) "
                                       "before it was replaced with the retained defaults.")
                            .arg(installedYamlData.localIgnoreReset.localIgnorePath.isEmpty()
                                     ? QStringLiteral("CLASSIC Ignore.yaml")
                                     : installedYamlData.localIgnoreReset.localIgnorePath,
                                 installedYamlData.localIgnoreReset.backupPath)
                            .arg(installedYamlData.localIgnoreReset.backupIdentity.byteLength)
                            .arg(installedYamlData.localIgnoreReset.backupIdentity.sha256));
    }
    return sections.join(QStringLiteral("\n\n"));
}

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

    if (execution.has_resume_error) {
        presentation.kind = ScanRunTerminalKind::InfrastructureError;
        presentation.message =
            QStringLiteral("Crash Log Scan recovery failed (%1): %2")
                .arg(classic::toQString(execution.resume_error.code),
                     classic::toQString(execution.resume_error.message));
        QStringList context;
        if (execution.resume_error.has_path) {
            context.append(QStringLiteral("Path: %1").arg(classic::toQString(execution.resume_error.path)));
        }
        if (execution.resume_error.has_stage) {
            context.append(QStringLiteral("Stage: %1").arg(resetFailureStageName(execution.resume_error.stage)));
        }
        if (execution.resume_error.has_expected_identity) {
            context.append(
                QStringLiteral("Expected identity: sha256 %1, %2 bytes")
                    .arg(classic::toQString(execution.resume_error.expected_identity.sha256))
                    .arg(execution.resume_error.expected_identity.byte_len));
        }
        if (execution.resume_error.has_actual_identity) {
            context.append(QStringLiteral("Actual identity: sha256 %1, %2 bytes")
                               .arg(classic::toQString(execution.resume_error.actual_identity.sha256))
                               .arg(execution.resume_error.actual_identity.byte_len));
        }
        if (execution.resume_error.has_backup_path) {
            context.append(
                QStringLiteral("Verified backup: %1").arg(classic::toQString(execution.resume_error.backup_path)));
        }
        if (!context.isEmpty()) {
            presentation.message.append(QStringLiteral("\n") + context.join('\n'));
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
    presentation.hasInstalledYamlData = result.has_installed_yaml_data;
    if (result.has_installed_yaml_data) {
        presentation.installedYamlData = presentInstalledYamlData(result.installed_yaml_data);
    }
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
    case Status::LocalIgnoreRecoveryRequired:
        presentation.kind = ScanRunTerminalKind::LocalIgnoreRecoveryRequired;
        presentation.message = result.has_message
                                   ? classic::toQString(result.message)
                                   : QStringLiteral("Local Ignore recovery is required before scanning can continue.");
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
