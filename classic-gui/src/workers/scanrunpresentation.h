#pragma once

#include <QMetaType>
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

/// Exact identity of one YAML Data byte sequence retained by the scan run.
struct ScanRunYamlDataContentIdentityPresentation {
    QString sha256;
    quint64 byteLength = 0;
};

/// Selected Main or game YAML Data metadata projected into Qt-owned values.
struct ScanRunInstalledYamlDataFilePresentation {
    classic::scanner::ScanRunInstalledYamlDataRole role = classic::scanner::ScanRunInstalledYamlDataRole::Main;
    classic::scanner::ScanRunInstalledYamlDataProvenance provenance =
        classic::scanner::ScanRunInstalledYamlDataProvenance::Bundled;
    QString schemaVersion;
    QString sha256;
    quint64 byteLength = 0;
};

/// One structured Installed YAML Data diagnostic with explicit optional context.
struct ScanRunInstalledYamlDataDiagnosticPresentation {
    bool hasRole = false;
    classic::scanner::ScanRunInstalledYamlDataRole role = classic::scanner::ScanRunInstalledYamlDataRole::Main;
    bool hasCandidate = false;
    classic::scanner::ScanRunInstalledYamlDataProvenance candidate =
        classic::scanner::ScanRunInstalledYamlDataProvenance::Bundled;
    bool hasPath = false;
    QString path;
    classic::scanner::ScanRunInstalledYamlDataDiagnosticKind kind =
        classic::scanner::ScanRunInstalledYamlDataDiagnosticKind::CacheUnavailable;
    QString message;
};

/// Qt-owned projection of the immutable Installed YAML Data selected for one run.
struct ScanRunInstalledYamlDataPresentation {
    ScanRunInstalledYamlDataFilePresentation main;
    ScanRunInstalledYamlDataFilePresentation gameFile;
    classic::scanner::ScanRunLocalIgnoreYamlDataState localIgnoreState =
        classic::scanner::ScanRunLocalIgnoreYamlDataState::Existing;
    ScanRunYamlDataContentIdentityPresentation localIgnoreIdentity;
    QVector<ScanRunInstalledYamlDataDiagnosticPresentation> diagnostics;
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
    bool hasInstalledYamlData = false;
    ScanRunInstalledYamlDataPresentation installedYamlData;
};

/// Formats Targeted discovery rejections without reapplying GUI-owned rejection policy.
QString formatScanRunRejections(const classic::scanner::ScanRunContractDiscoveryResult& discovery);

/// Returns unique report directories derived from Rust-accepted Crash Logs.
QStringList scanRunReportDirectories(const classic::scanner::ScanRunContractDiscoveryResult& discovery);

/// Maps every typed terminal status, disposition, failure stage, and infrastructure stage for Qt presentation.
ScanRunTerminalPresentation presentScanRunExecution(const classic::scanner::ScanRunContractExecutionResult& execution);

} // namespace classic::gui

Q_DECLARE_METATYPE(classic::gui::ScanRunInstalledYamlDataPresentation)
