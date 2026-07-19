#include "scancontroller.h"
#include "core/signalhub.h"
#include "core/threadmanager.h"
#include "workers/scanworker.h"

#include <QCoreApplication>
#include <QDir>
#include <QMetaType>
#include <QThread>

ScanController::ScanController(SignalHub* signalHub, ThreadManager* threadManager, QObject* parent)
    : QObject(parent)
    , m_signalHub(signalHub)
    , m_threadManager(threadManager)
{
    qRegisterMetaType<classic::gui::ScanRunInstalledYamlDataPresentation>(
        "classic::gui::ScanRunInstalledYamlDataPresentation");
}

void ScanController::startScan(const QString& installationRoot,
                               const classic::gui::CrashLogScanLaunchSettings& settings, const QString& setupXseLogPath,
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

    const QString baseDir = QDir::cleanPath(QCoreApplication::applicationDirPath());

    // Create worker and thread
    auto* worker = new ScanWorker();
    auto* thread = new QThread();
    m_currentWorker = worker;

    // Connect worker signals to controller slots
    connect(worker, &ScanWorker::progressDetailed, this, &ScanController::scanProgress);
    connect(
        worker, &ScanWorker::discoveryCompleted, this,
        [this](int total, const QString& warning, const QStringList& reportDirectories) {
            emit scanDiscovered(total);
            if (!warning.isEmpty()) {
                emit scanWarning(warning);
            }
            emit scanReportDirectoriesResolved(reportDirectories);
        },
        Qt::BlockingQueuedConnection);
    connect(worker, &ScanWorker::effectiveConcurrencySelected, this, &ScanController::scanConcurrencySelected);
    connect(worker, &ScanWorker::reportDirectoriesResolved, this, &ScanController::scanReportDirectoriesResolved);
    connect(worker, &ScanWorker::installedYamlDataResolved, this, &ScanController::scanInstalledYamlDataResolved);
    connect(worker, &ScanWorker::logScanned, this, &ScanController::scanLogScanned);
    connect(worker, &ScanWorker::finished, this, &ScanController::onWorkerFinished);
    connect(worker, &ScanWorker::noLogsFound, this, &ScanController::onWorkerNoLogsFound);
    connect(worker, &ScanWorker::cancelled, this, &ScanController::onWorkerCancelled);
    connect(worker, &ScanWorker::error, this, &ScanController::onWorkerError);

    // Relay progress to SignalHub
    if (m_signalHub) {
        connect(worker, &ScanWorker::progress, m_signalHub, &SignalHub::scanProgress);
    }

    // Start the worker thread and invoke doScan once the thread is running
    connect(thread, &QThread::started, worker,
            [worker, installationRoot, settings, baseDir, setupXseLogPath, targetedInputs]() {
                worker->doScan(installationRoot, settings, baseDir, setupXseLogPath, targetedInputs);
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

void ScanController::onWorkerNoLogsFound(const QString& message)
{
    m_scanning = false;
    m_currentWorker = nullptr;
    emit scanNoLogsFound(message);
    if (m_signalHub) {
        emit m_signalHub->scanNoLogsFound(message);
    }
}

void ScanController::onWorkerCancelled(const QString& message)
{
    m_scanning = false;
    m_currentWorker = nullptr;
    emit scanCancelled(message);
    if (m_signalHub) {
        emit m_signalHub->scanCancelled(message);
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
