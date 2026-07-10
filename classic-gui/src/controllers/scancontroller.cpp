#include "scancontroller.h"
#include "core/rust_qt_bridge.h"
#include "core/signalhub.h"
#include "core/threadmanager.h"
#include "workers/scanworker.h"

#include "classic_cxx_bridge/files.h"
#include "rust/cxx.h"

#include <QCoreApplication>
#include <QDir>
#include <QFileInfo>
#include <QSet>
#include <QThread>

namespace {

bool isCrashLogPath(const QString& path)
{
    const QFileInfo info(path);
    const QString name = info.fileName();
    return name.startsWith(QStringLiteral("crash-"), Qt::CaseInsensitive) &&
           name.endsWith(QStringLiteral(".log"), Qt::CaseInsensitive);
}

QString formatTargetedRejectionMessage(const rust::Vec<rust::String>& rejectedPaths,
                                       const rust::Vec<rust::String>& rejectedReasons)
{
    if (rejectedPaths.empty()) {
        return {};
    }

    QStringList lines;
    lines.append(QStringLiteral("Ignored %1 targeted input%2:")
                     .arg(rejectedPaths.size())
                     .arg(rejectedPaths.size() == 1 ? "" : "s"));

    for (size_t i = 0; i < rejectedPaths.size(); ++i) {
        const QString path = classic::toQString(rejectedPaths[i]);
        const QString reason =
            i < rejectedReasons.size() ? classic::toQString(rejectedReasons[i]) : QStringLiteral("unknown reason");
        lines.append(QStringLiteral("- %1 (%2)").arg(path, reason));
    }

    return lines.join('\n');
}

QStringList collectReportDirectories(const QStringList& logPaths)
{
    QStringList reportDirs;
    QSet<QString> seen;

    for (const auto& logPath : logPaths) {
        const QString reportDir = QDir::cleanPath(QFileInfo(logPath).absolutePath());
        if (reportDir.isEmpty()) {
            continue;
        }

        const QString key = reportDir.toLower();
        if (seen.contains(key)) {
            continue;
        }

        seen.insert(key);
        reportDirs.append(reportDir);
    }

    return reportDirs;
}

} // namespace

ScanController::ScanController(SignalHub* signalHub, ThreadManager* threadManager, QObject* parent)
    : QObject(parent)
    , m_signalHub(signalHub)
    , m_threadManager(threadManager)
{
}

void ScanController::startScan(const QString& yamlRoot, const QString& yamlData, const QString& game,
                               const QString& gameVersion, bool showFormIdValues, bool fcxMode, bool simplifyLogs,
                               bool moveUnsolvedLogs, const QString& unsolvedLogsDestination, int maxConcurrentScans,
                               const QString& customFolder, const QString& setupGameRoot, const QString& setupDocsRoot,
                               const QString& setupGameExePath, const QString& setupXseLogPath,
                               const QStringList& targetedInputs)
{
    if (m_scanning) {
        return;
    }

    m_scanning = true;
    emit scanStarted();
    if (m_signalHub) {
        emit m_signalHub->scanStarted();
    }

    const bool targetedMode = !targetedInputs.isEmpty();

    // Collect crash logs -- targeted mode or standard discovery
    QStringList logPathsList;
    QString targetedRejectionMessage;
    const QString baseDir = QDir::cleanPath(QCoreApplication::applicationDirPath());
    try {
        if (targetedMode) {
            rust::Vec<rust::String> rustInputs;
            rustInputs.reserve(static_cast<size_t>(targetedInputs.size()));
            for (const auto& p : targetedInputs) {
                rustInputs.push_back(classic::toRustString(p));
            }
            auto resolution = classic::files::resolve_targeted_inputs({rustInputs.data(), rustInputs.size()});

            logPathsList.reserve(static_cast<int>(resolution.logs.size()));
            for (const auto& rpath : resolution.logs) {
                const QString qpath = classic::toQString(rpath);
                logPathsList.append(qpath);
            }

            targetedRejectionMessage =
                formatTargetedRejectionMessage(resolution.rejected_paths, resolution.rejected_reasons);
            if (!targetedRejectionMessage.isEmpty()) {
                for (size_t i = 0; i < resolution.rejected_paths.size(); ++i) {
                    const QString reason = i < resolution.rejected_reasons.size()
                                               ? classic::toQString(resolution.rejected_reasons[i])
                                               : QStringLiteral("unknown reason");
                    qWarning("Targeted input rejected: %s (%s)",
                             qPrintable(classic::toQString(resolution.rejected_paths[i])), qPrintable(reason));
                }
            }
        } else {
            // Intentionally collect under the portable app root. CLASSIC is distributed as a
            // portable app, so the application directory is expected to be writable and we do
            // not use a separate per-user/AppData fallback here.
            auto collector = classic::files::log_collector_new_for_scan(
                classic::toRustString(baseDir), classic::toRustString(yamlData), classic::toRustString(game),
                classic::toRustString(gameVersion), "", classic::toRustString(customFolder));
            auto rustPaths = classic::files::log_collector_collect_all(*collector);

            logPathsList.reserve(static_cast<int>(rustPaths.size()));
            for (const auto& rpath : rustPaths) {
                const QString qpath = classic::toQString(rpath);
                if (isCrashLogPath(qpath)) {
                    logPathsList.append(qpath);
                }
            }
        }
    } catch (const rust::Error& e) {
        m_scanning = false;
        emit scanError(QString::fromUtf8(e.what()));
        if (m_signalHub) {
            emit m_signalHub->scanError(QString::fromUtf8(e.what()));
        }
        return;
    }

    if (!targetedRejectionMessage.isEmpty()) {
        emit scanWarning(targetedRejectionMessage);
    }
    if (targetedMode) {
        emit scanReportDirectoriesResolved(collectReportDirectories(logPathsList));
    }

    emit scanDiscovered(logPathsList.size());

    // Create worker and thread
    auto* worker = new ScanWorker();
    auto* thread = new QThread();
    m_currentWorker = worker;

    // Connect worker signals to controller slots
    connect(worker, &ScanWorker::progressDetailed, this, &ScanController::scanProgress);
    connect(worker, &ScanWorker::logScanned, this, &ScanController::scanLogScanned);
    connect(worker, &ScanWorker::finished, this, &ScanController::onWorkerFinished);
    connect(worker, &ScanWorker::error, this, &ScanController::onWorkerError);

    // Relay progress to SignalHub
    if (m_signalHub) {
        connect(worker, &ScanWorker::progress, m_signalHub, &SignalHub::scanProgress);
    }

    // Start the worker thread and invoke doScan once the thread is running
    connect(thread, &QThread::started, worker,
            [worker, logPathsList, yamlRoot, yamlData, game, gameVersion, showFormIdValues, fcxMode, simplifyLogs,
             moveUnsolvedLogs, unsolvedLogsDestination, maxConcurrentScans, baseDir, customFolder, targetedMode,
             setupGameRoot, setupDocsRoot, setupGameExePath, setupXseLogPath, targetedInputs]() {
                worker->doScan(logPathsList, yamlRoot, yamlData, game, gameVersion, showFormIdValues, fcxMode,
                               simplifyLogs, moveUnsolvedLogs, unsolvedLogsDestination, maxConcurrentScans, baseDir,
                               customFolder, setupGameRoot, setupDocsRoot, setupGameExePath, setupXseLogPath,
                               targetedMode, targetedInputs);
            });

    m_threadManager->startWorker(QStringLiteral("crash_scan"), thread, worker);
}

void ScanController::cancelScan()
{
    if (m_scanning && m_currentWorker) {
        m_currentWorker->requestCancel();
    }
}

bool ScanController::isScanning() const
{
    return m_scanning;
}

void ScanController::onWorkerFinished(int total, int success, int errors)
{
    m_scanning = false;
    m_currentWorker = nullptr;
    emit scanFinished(total, success, errors);
    if (m_signalHub) {
        emit m_signalHub->scanCompleted();
    }
}

void ScanController::onWorkerError(const QString& message)
{
    m_scanning = false;
    m_currentWorker = nullptr;
    emit scanError(message);
    if (m_signalHub) {
        emit m_signalHub->scanError(message);
    }
}
