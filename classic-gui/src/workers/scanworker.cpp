#include "scanworker.h"

#include "core/rust_qt_bridge.h"
#include "scanlaunch.h"
#include "scanprogressmodel.h"
#include "scanrunpresentation.h"

#include "classic_cxx_bridge/scanner.h"

#include <QDebug>
#include <QDir>
#include <QFileInfo>
#include <QSet>

#include <exception>
#include <optional>
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
    /// Borrows the worker for the synchronous execution and settlement lifetime.
    explicit GuiScanRunObserver(ScanWorker& worker) noexcept
        : m_worker(worker)
    {
    }

    /// Presents one serialized event without allowing adapter failures to cross the CXX boundary.
    ///
    /// A presentation failure is returned as a failed delivery, which Rust applies under the
    /// cancel-run policy `doScan` passes: Rust cancels the run, stops delivering, abandons a
    /// recovery the run had not yet paused for, and reports the failure in the envelope. Nothing
    /// is recorded here, so the envelope is the one place the worker learns a delivery failed.
    scanner::ScanRunObserverDelivery on_scan_run_event(const scanner::ScanRunContractEvent& event) const noexcept override
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
            return {};
        } catch (...) {
            // Qt presentation failure is adapter-local; Rust's cancel-run policy stops the run at
            // its next safe seam.
            return {true, "Qt scan progress presentation failed"};
        }
    }

private:
    ScanWorker& m_worker;
    mutable BatchProgressModel m_progress;
};

/// Maps the GUI prompt's answer onto the decision passed to settling; dismissal is no decision.
///
/// The switch stays exhaustive so a choice added later trips `-Wswitch` here rather than silently
/// resolving to Proceed Without Ignore. `LocalIgnoreRecoveryDecision` deliberately has no
/// abandonment variant, so absence is how abandonment is spelled everywhere — the native CLI and
/// the Node and Python bindings use the same `optional`-shaped mapping for the same reason.
std::optional<scanner::ScanRunLocalIgnoreRecoveryDecision>
settlementDecision(classic::gui::ScanRunLocalIgnoreRecoveryChoice choice) noexcept
{
    switch (choice) {
    case classic::gui::ScanRunLocalIgnoreRecoveryChoice::ProceedWithoutIgnore:
        return scanner::ScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore;
    case classic::gui::ScanRunLocalIgnoreRecoveryChoice::ResetToDefault:
        return scanner::ScanRunLocalIgnoreRecoveryDecision::ResetToDefault;
    case classic::gui::ScanRunLocalIgnoreRecoveryChoice::Cancel:
        return std::nullopt;
    }
    // Unreachable for a valid enumerator. No decision is the safe resolution for a value this
    // build does not recognize: it cannot touch the user's files.
    return std::nullopt;
}

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

void ScanWorker::doScan(const QString& installationRoot, const QStringList& targetedInputs)
{
    qDebug() << "ScanWorker: starting" << (targetedInputs.isEmpty() ? "standard" : "targeted") << "scan run";

    try {
        // Launching reads User Settings on this worker thread, at the moment the scan starts, so a
        // save made since the window last refreshed its snapshot is what the scan uses.
        const auto launch = classic::gui::launchScanRun(installationRoot, targetedInputs);
        const auto launchError = scanner::scan_run_launch_error(*launch);
        if (launchError.has_error) {
            // Typed refusals are reserved for input Rust cannot launch from, such as an XSE log
            // location that cannot be inspected. A missing FCX folder is not one: it launches and
            // the run's Crash Log Scan Setup Result reports it.
            emit error(classic::toQString(launchError.message));
            return;
        }
        const auto launchView = scanner::scan_run_launch_view(*launch);
        const QString launchWarningText = classic::gui::formatScanRunLaunchWarning(launchView);
        if (!launchWarningText.isEmpty()) {
            qWarning().noquote() << classic::gui::renderScanRunDisplayLinesAsPlainText(
                classic::gui::presentScanRunDisplayLines(launchView.display_lines));
            emit launchWarning(launchWarningText);
        }
        auto request = scanner::scan_run_launch_request(*launch);
        GuiScanRunObserver observer(*this);
        // The GUI has always stopped a run whose progress view failed, so it asks Rust to.
        auto operation = scanner::scan_run_contract_execute(*request, *m_cancellation, &observer,
                                                            scanner::ScanRunObserverFailurePolicy::CancelRun);
        auto execution = scanner::scan_run_contract_execution_take_result(*operation);
        auto terminal = classic::gui::presentScanRunExecution(execution);
        if (scanner::scan_run_contract_execution_has_pending_recovery(*operation)) {
            if (terminal.hasInstalledYamlData) {
                // Publish the retained malformed-file identity before the modal GUI decision.
                emit installedYamlDataResolved(terminal.installedYamlData);
            }
            auto pending = scanner::scan_run_contract_execution_take_pending_recovery(*operation);

            // A run cancelled while it sat at the pause is settled with no decision and never
            // prompts: asking about a scan the user already walked away from would be a question
            // whose every answer is ignored. The fact is read live from the run's own control, so a
            // cancel that landed after the pause but before this line is seen here.
            std::optional<scanner::ScanRunLocalIgnoreRecoveryDecision> decision;
            std::exception_ptr promptFailure;
            if (!scanner::scan_run_pending_recovery_cancellation_requested(*pending) && m_localIgnoreRecoveryPrompt) {
                // The prompt is handed the whole rendered run *and* Rust's own question, already
                // rendered on this thread. Rust exposes the Installed YAML Data block — the facts this
                // decision is about — only as part of the rendered run, and picking that block back
                // out by position would be a structural assumption about a sequence that carries no
                // structure. The native CLI and the TUI made the same call for the same reason.
                //
                // Rendering happens here rather than in the dialog because the bridged envelope
                // cannot cross the hop to the GUI thread: `presentScanRunExecution` above has already
                // turned it into copyable Qt values carrying no `rust::Box`, which is what makes the
                // `Qt::BlockingQueuedConnection` in `makeLocalIgnoreRecoveryPrompt` legal.
                //
                // A worker with no prompt is a non-interactive caller; it falls through with no
                // decision, which refuses to choose for the user exactly as a dismissed dialog does.
                try {
                    decision = settlementDecision(m_localIgnoreRecoveryPrompt(terminal.recoveryPrompt));
                } catch (...) {
                    // A failed prompt is no answer. Settle with no decision first so the paused run
                    // is abandoned rather than dropped, then report the failure below.
                    promptFailure = std::current_exception();
                }
            }

            // Settling with no decision cancels the run's own control and finishes it cancelled
            // with no filesystem work, so nothing here cancels first, and a later `requestCancel()`
            // stays inert. The settled envelope cannot carry another recovery: Rust's settled
            // result has no continuation, so this run can pause at most once.
            scanner::ScanRunLocalIgnoreRecoverySettlement settlement{};
            settlement.has_decision = decision.has_value();
            // Read by Rust only when `has_decision` is true; the fallback is never acted on.
            settlement.decision = decision.value_or(scanner::ScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore);
            execution = scanner::scan_run_pending_recovery_settle(*pending, settlement, &observer,
                                                                  scanner::ScanRunObserverFailurePolicy::CancelRun);
            if (promptFailure) {
                std::rethrow_exception(promptFailure);
            }
            terminal = classic::gui::presentScanRunExecution(execution);
        }

        // Rust reports a failed delivery in the envelope it applied the cancel-run policy to. A
        // failure before the pause already abandoned the recovery inside Rust, so a run that
        // reaches here with a failure never paused; one during settlement is reported by the
        // settled envelope.
        if (execution.has_observer_delivery_failure) {
            emit error(QStringLiteral("Crash Log Scan progress delivery failed; the run was cancelled safely."));
            return;
        }

        using TerminalKind = classic::gui::ScanRunTerminalKind;

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

        // Every terminal signal carries the rendered run as rich text, because each ends in a
        // `QMessageBox` — a widget that can style a severity and open a path the run just wrote.
        // The window reduces it to one plain line for the progress row, which is the only surface
        // here that cannot hold more.
        //
        // `finished` was the exception until it carried a message: it published three counts and no
        // words, so the window had nothing to state the outcome with and wrote its own sentence,
        // re-deciding both the wording and the plural of "logs". Handing it the same rendered run
        // the other three get is what removed that.
        switch (terminal.kind) {
        case TerminalKind::Completed:
            emit progress(100.0F, QStringLiteral("Complete"));
            emit progressDetailed(100.0F, QStringLiteral("Complete"), terminal.succeeded + terminal.failed,
                                  terminal.total);
            emit finished(terminal.total, terminal.succeeded, terminal.failed, terminal.richText);
            break;
        case TerminalKind::CancelledBeforeDiscovery:
        case TerminalKind::Cancelled:
            emit cancelled(terminal.richText);
            break;
        case TerminalKind::NoCrashLogsFound:
            emit noLogsFound(terminal.richText);
            break;
        // Every recovery the run paused for was settled above, and a settled run cannot pause again,
        // so `LocalIgnoreRecoveryRequired` is listed only to keep this switch exhaustive. It ends the
        // run in Rust's own words like the other outcomes that are not a success.
        case TerminalKind::SetupFailed:
        case TerminalKind::InfrastructureError:
        case TerminalKind::LocalIgnoreRecoveryRequired:
            emit error(terminal.richText);
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
