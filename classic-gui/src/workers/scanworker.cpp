#include "scanworker.h"

#include "core/rust_qt_bridge.h"
#include "scanprogressmodel.h"
#include "scanrequestbuilder.h"
#include "scanrunpresentation.h"

#include "classic_cxx_bridge/scanner.h"

#include <QDebug>
#include <QDir>
#include <QFileInfo>
#include <QSet>

#include <exception>
#include <utility>

namespace {

namespace scanner = classic::scanner;

/// Produces the one-row progress text for one observed lifecycle event.
///
/// The words come from Rust, already rendered on the observer callback before the event crossed the
/// bridge — there is no later opportunity, because this process receives a projected copy and never
/// holds the Rust event. What stays this frontend's is the shape: the progress row is a single
/// `QProgressBar` format string, so a discovery that also states a rejection is joined onto one line
/// rather than shown as two.
QString eventStatus(const scanner::ScanRunContractEvent& event)
{
    QStringList rendered;
    rendered.reserve(static_cast<qsizetype>(event.display_lines.size()));
    for (const auto& line : classic::gui::presentScanRunDisplayLines(event.display_lines)) {
        rendered.append(classic::gui::renderScanRunDisplayLineAsPlainText(line));
    }
    return rendered.join(QStringLiteral(" - "));
}

QStringList terminalReportDirectories(const classic::gui::ScanRunTerminalPresentation& terminal)
{
    QStringList directories;
    QSet<QString> seen;
    for (const auto& log : terminal.logs) {
        if (log.autoscanReport.isEmpty()) {
            continue;
        }
        const QString directory = QDir::cleanPath(QFileInfo(log.autoscanReport).absolutePath());
        const QString key = directory.toLower();
        if (!directory.isEmpty() && !seen.contains(key)) {
            seen.insert(key);
            directories.append(directory);
        }
    }
    return directories;
}

/// Serially projects Rust lifecycle events to the worker's Qt signals.
class GuiScanRunObserver final : public scanner::ScanRunObserver {
public:
    /// Borrows the worker and cancellation control for the synchronous execution lifetime.
    GuiScanRunObserver(ScanWorker& worker, const scanner::ScanRunCancellation& cancellation) noexcept
        : m_worker(worker)
        , m_cancellation(cancellation)
    {
    }

    /// Presents one serialized event without allowing adapter failures to cross the CXX boundary.
    void on_scan_run_event(const scanner::ScanRunContractEvent& event) const noexcept override
    {
        try {
            const float percent = m_progress.update(event);
            using EventKind = scanner::ScanRunContractEventKind;
            switch (event.kind) {
            case EventKind::DiscoveryCompleted: {
                const int total = m_progress.totalLogs();
                Q_EMIT m_worker.discoveryCompleted(total, classic::gui::formatScanRunRejections(event.discovery),
                                                   classic::gui::scanRunReportDirectories(event.discovery));
                Q_EMIT m_worker.progress(0.0F, eventStatus(event));
                Q_EMIT m_worker.progressDetailed(0.0F, eventStatus(event), 0, total);
                break;
            }
            case EventKind::EffectiveConcurrencySelected:
                Q_EMIT m_worker.effectiveConcurrencySelected(m_progress.effectiveConcurrency());
                Q_EMIT m_worker.progress(percent, eventStatus(event));
                Q_EMIT m_worker.progressDetailed(percent, eventStatus(event), static_cast<int>(event.completed),
                                                 static_cast<int>(event.total));
                break;
            case EventKind::LogQueued:
            case EventKind::LogStarted:
            case EventKind::LogPhase:
            case EventKind::LogFinished:
                Q_EMIT m_worker.progress(percent, eventStatus(event));
                Q_EMIT m_worker.progressDetailed(percent, eventStatus(event), static_cast<int>(event.completed),
                                                 static_cast<int>(event.total));
                break;
            }
        } catch (...) {
            // Qt presentation failure is adapter-local; stop future admissions at Rust's next safe seam.
            m_deliveryFailed = true;
            scanner::scan_run_cancellation_cancel(m_cancellation);
        }
    }

    /// Returns whether Qt event presentation failed during observer delivery.
    [[nodiscard]] bool deliveryFailed() const noexcept { return m_deliveryFailed; }

private:
    ScanWorker& m_worker;
    const scanner::ScanRunCancellation& m_cancellation;
    mutable BatchProgressModel m_progress;
    mutable bool m_deliveryFailed = false;
};

} // namespace

ScanWorker::ScanWorker(QObject* parent)
    : ScanWorker({}, parent)
{
}

ScanWorker::ScanWorker(classic::gui::ScanRunLocalIgnoreRecoveryPrompt localIgnoreRecoveryPrompt, QObject* parent)
    : QObject(parent)
    , m_cancellation(scanner::scan_run_cancellation_new())
    , m_localIgnoreRecoveryPrompt(std::move(localIgnoreRecoveryPrompt))
{
}

void ScanWorker::requestCancel()
{
    qDebug() << "ScanWorker: cancellation requested";
    scanner::scan_run_cancellation_cancel(*m_cancellation);
}

void ScanWorker::doScan(const QString& installationRoot, const classic::gui::CrashLogScanLaunchSettings& settings,
                        const QString& baseDirectory, const QString& setupXseLogPath, const QStringList& targetedInputs)
{
    qDebug() << "ScanWorker: starting" << (targetedInputs.isEmpty() ? "standard" : "targeted") << "scan run";

    try {
        auto request = classic::gui::buildScanRunRequest(installationRoot, baseDirectory, settings, setupXseLogPath,
                                                         targetedInputs);
        GuiScanRunObserver observer(*this, *m_cancellation);
        auto operation = scanner::scan_run_contract_execute(*request, *m_cancellation, &observer);
        const auto execution = scanner::scan_run_contract_execution_take_result(*operation);
        if (observer.deliveryFailed()) {
            emit error(QStringLiteral("Crash Log Scan progress delivery failed; the run was cancelled safely."));
            return;
        }

        auto terminal = classic::gui::presentScanRunExecution(execution);
        using TerminalKind = classic::gui::ScanRunTerminalKind;
        if (terminal.kind == TerminalKind::LocalIgnoreRecoveryRequired) {
            if (terminal.hasInstalledYamlData) {
                // Publish the retained malformed-file identity before the modal GUI decision.
                emit installedYamlDataResolved(terminal.installedYamlData);
            }
            if (!scanner::scan_run_contract_execution_has_continuation(*operation)) {
                emit error(QStringLiteral(
                    "Crash Log Scan Run requested Local Ignore recovery without retaining its continuation."));
                return;
            }
            if (!m_localIgnoreRecoveryPrompt) {
                emit error(terminal.message +
                           QStringLiteral("\nNo Local Ignore recovery prompt is configured for this scan."));
                return;
            }

            // The prompt is handed the whole rendered run rather than the run message alone. Rust
            // exposes the Installed YAML Data block — the facts this decision is about — only as
            // part of the rendered run, and picking that block back out by position would be a
            // structural assumption about a sequence that carries no structure. The native CLI and
            // the TUI made the same call for the same reason. The prompt's own wording, its buttons,
            // and the descriptions beside them are untouched and land with the gated recovery phase.
            auto continuation = scanner::scan_run_contract_execution_take_continuation(*operation);
            const auto choice = m_localIgnoreRecoveryPrompt(
                terminal.richText, classic::gui::offersLocalIgnoreResetToDefault(terminal));
            auto decision = scanner::ScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore;
            switch (choice) {
            case classic::gui::ScanRunLocalIgnoreRecoveryChoice::ProceedWithoutIgnore:
                break;
            case classic::gui::ScanRunLocalIgnoreRecoveryChoice::ResetToDefault:
                decision = scanner::ScanRunLocalIgnoreRecoveryDecision::ResetToDefault;
                break;
            case classic::gui::ScanRunLocalIgnoreRecoveryChoice::Cancel:
                // Rust observes cancellation before the placeholder decision, so dismissal cannot mutate Local Ignore.
                scanner::scan_run_cancellation_cancel(*m_cancellation);
                break;
            }

            auto resumedOperation =
                scanner::scan_run_continuation_resume(*continuation, decision, *m_cancellation, &observer);
            const auto resumedExecution =
                scanner::scan_run_contract_execution_take_result(*resumedOperation);
            if (observer.deliveryFailed()) {
                emit error(QStringLiteral("Crash Log Scan progress delivery failed; the run was cancelled safely."));
                return;
            }
            terminal = classic::gui::presentScanRunExecution(resumedExecution);
        }

        // One log entry for the whole run, in the words the run itself used. This replaces the
        // per-log warnings this worker used to compose: every fact they carried — the Crash Log
        // path, its outcome, the Autoscan Report, movement to Unsolved Logs, and each structured
        // failure's stage and message — is a line in the rendered run, stated once by Rust rather
        // than twice in two frontends able to disagree. The FCX setup projection still follows,
        // because the presentation crate deliberately does not render it.
        qInfo().noquote() << terminal.message;
        if (!terminal.setupDetails.isEmpty()) {
            qInfo().noquote() << terminal.setupDetails;
        }
        if (terminal.hasInstalledYamlData) {
            // Publish the Qt-owned copy before terminal signals allow the worker thread to be torn down.
            emit installedYamlDataResolved(terminal.installedYamlData);
        }
        const QStringList reportDirectories = terminalReportDirectories(terminal);
        if (!reportDirectories.isEmpty()) {
            emit reportDirectoriesResolved(reportDirectories);
        }

        // The contract supplies terminal outcomes in discovery order even when execution events
        // interleave. Nothing is described here any more — the rendered run above already said what
        // happened to each Crash Log. What survives is the signal, which carries data rather than
        // words: a discovery index, a success flag, and the path the results view keys on.
        for (const auto& log : terminal.logs) {
            if (log.cancelledBeforeStart) {
                continue;
            }
            emit logScanned(log.discoveryIndex, log.succeeded, log.crashLog);
        }

        // The three terminal signals that carry prose carry the rendered run as rich text, because
        // every one of them ends in a `QMessageBox` — a widget that can style a severity and open a
        // path the run just wrote. The window reduces it to one plain line for the progress row,
        // which is the only surface here that cannot hold more.
        switch (terminal.kind) {
        case TerminalKind::Completed:
            emit progress(100.0F, QStringLiteral("Complete"));
            emit progressDetailed(100.0F, QStringLiteral("Complete"), terminal.succeeded + terminal.failed,
                                  terminal.total);
            emit finished(terminal.total, terminal.succeeded, terminal.failed);
            break;
        case TerminalKind::CancelledBeforeDiscovery:
        case TerminalKind::Cancelled:
            emit cancelled(terminal.richText);
            break;
        case TerminalKind::NoCrashLogsFound:
            emit noLogsFound(terminal.richText);
            break;
        case TerminalKind::SetupFailed:
        case TerminalKind::InfrastructureError:
            emit error(terminal.richText);
            break;
        case TerminalKind::LocalIgnoreRecoveryRequired:
            emit error(QStringLiteral("Crash Log Scan recovery returned an unexpected second recovery request."));
            break;
        }
    } catch (const rust::Error& error) {
        emit this->error(QString::fromUtf8(error.what()));
    } catch (const std::exception& error) {
        emit this->error(QString::fromUtf8(error.what()));
    } catch (...) {
        emit error(QStringLiteral("Crash Log Scan Run failed with an unknown adapter error."));
    }
}
