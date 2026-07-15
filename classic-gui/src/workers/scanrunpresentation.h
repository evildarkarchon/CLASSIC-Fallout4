#pragma once

#include <QString>
#include <QStringList>
#include <QVector>

#include "classic_cxx_bridge/scanner.h"

namespace classic::gui {

/// GUI-facing terminal category for one typed Crash Log Scan Run execution envelope.
enum class ScanRunTerminalKind {
    Completed,
    NoCrashLogsFound,
    SetupFailed,
    CancelledBeforeDiscovery,
    Cancelled,
    InfrastructureError,
};

/// Presentation-ready projection of one discovery-ordered per-log outcome.
struct ScanRunLogPresentation {
    int discoveryIndex = 0;
    bool succeeded = false;
    bool failed = false;
    bool cancelledBeforeStart = false;
    QString crashLog;
    QString autoscanReport;
    QStringList failures;
    QString message;
    bool movedToUnsolvedLogs = false;
};

/// Presentation-ready terminal state without flattening typed counts or per-log dispositions.
struct ScanRunTerminalPresentation {
    ScanRunTerminalKind kind = ScanRunTerminalKind::InfrastructureError;
    QString message;
    QString setupDetails;
    int total = 0;
    int succeeded = 0;
    int failed = 0;
    int cancelled = 0;
    QVector<ScanRunLogPresentation> logs;
};

/// Formats Targeted discovery rejections without reapplying GUI-owned rejection policy.
QString formatScanRunRejections(const classic::scanner::ScanRunContractDiscoveryResult& discovery);

/// Returns unique report directories derived from Rust-accepted Crash Logs.
QStringList scanRunReportDirectories(const classic::scanner::ScanRunContractDiscoveryResult& discovery);

/// Maps every typed terminal status, disposition, failure stage, and infrastructure stage for Qt presentation.
ScanRunTerminalPresentation presentScanRunExecution(const classic::scanner::ScanRunContractExecutionResult& execution);

} // namespace classic::gui
