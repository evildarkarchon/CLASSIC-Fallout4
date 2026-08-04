#pragma once

#include <QMetaType>
#include <QString>
#include <QStringList>
#include <QVector>

#include "classic_cxx_bridge/scanner.h"

#include <functional>

namespace classic::gui {

/// GUI-facing terminal category for one typed Crash Log Scan Run execution envelope.
enum class ScanRunTerminalKind {
    Completed,
    NoCrashLogsFound,
    SetupFailed,
    LocalIgnoreRecoveryRequired,
    CancelledBeforeDiscovery,
    Cancelled,
    InfrastructureError,
};

/// Explicit GUI response to a malformed Local Ignore file encountered by an active scan run.
enum class ScanRunLocalIgnoreRecoveryChoice {
    ProceedWithoutIgnore,
    ResetToDefault,
    Cancel,
};

/// GUI-thread prompt used by ScanWorker while Rust retains the single-use recovery continuation.
using ScanRunLocalIgnoreRecoveryPrompt =
    std::function<ScanRunLocalIgnoreRecoveryChoice(const QString& message)>;

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

/// Qt-owned durable metadata from a successful Local Ignore reset.
struct ScanRunLocalIgnoreResetPresentation {
    QString localIgnorePath;
    QString backupPath;
    ScanRunYamlDataContentIdentityPresentation malformedIdentity;
    ScanRunYamlDataContentIdentityPresentation backupIdentity;
    ScanRunYamlDataContentIdentityPresentation replacementIdentity;
};

/// Qt-owned projection of the immutable Installed YAML Data selected for one run.
struct ScanRunInstalledYamlDataPresentation {
    ScanRunInstalledYamlDataFilePresentation main;
    ScanRunInstalledYamlDataFilePresentation gameFile;
    classic::scanner::ScanRunLocalIgnoreYamlDataState localIgnoreState =
        classic::scanner::ScanRunLocalIgnoreYamlDataState::Existing;
    ScanRunYamlDataContentIdentityPresentation localIgnoreIdentity;
    QVector<ScanRunInstalledYamlDataDiagnosticPresentation> diagnostics;
    bool hasLocalIgnoreReset = false;
    ScanRunLocalIgnoreResetPresentation localIgnoreReset;
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

/// Returns the stable GUI label for the #146 scan-run Local Ignore state inventory.
QString localIgnoreStateLabel(classic::scanner::ScanRunLocalIgnoreYamlDataState state);

/// Returns the stable GUI label for every selected YAML Data provenance.
QString installedYamlDataProvenanceLabel(classic::scanner::ScanRunInstalledYamlDataProvenance provenance);

/// Returns the stable GUI label for the #146 scan-run Installed YAML Data diagnostic inventory.
QString installedYamlDataDiagnosticKindLabel(classic::scanner::ScanRunInstalledYamlDataDiagnosticKind kind);

/// Formats one structured diagnostic as `<kind>: <message> [<role>, <candidate>, <path>]`.
///
/// Only the context the diagnostic actually carries is appended, so callers do not re-derive which
/// optional fields Rust populated for a given kind.
QString formatInstalledYamlDataDiagnostic(const ScanRunInstalledYamlDataDiagnosticPresentation& diagnostic);

/// Aggregates degraded Installed YAML Data selection and durable Local Ignore recovery into one
/// run-level warning, or returns an empty string when the run has nothing the user must act on.
///
/// `LocalIgnoreGenerated` is deliberately excluded: generating a missing Local Ignore file from the
/// selected Main defaults is an expected successful path, so a clean first run stays silent. The
/// result is run-level only and never contributes to Autoscan Report content.
QString formatInstalledYamlDataWarning(const ScanRunInstalledYamlDataPresentation& installedYamlData);

/// Formats Targeted discovery rejections without reapplying GUI-owned rejection policy.
QString formatScanRunRejections(const classic::scanner::ScanRunContractDiscoveryResult& discovery);

/// Returns unique report directories derived from Rust-accepted Crash Logs.
QStringList scanRunReportDirectories(const classic::scanner::ScanRunContractDiscoveryResult& discovery);

/// Maps every typed terminal status, disposition, failure stage, and infrastructure stage for Qt presentation.
ScanRunTerminalPresentation presentScanRunExecution(const classic::scanner::ScanRunContractExecutionResult& execution);

} // namespace classic::gui

Q_DECLARE_METATYPE(classic::gui::ScanRunInstalledYamlDataPresentation)
