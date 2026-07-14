#include "gamefilescontroller.h"
#include "core/signalhub.h"
#include "core/threadmanager.h"
#include "workers/gamefilesworker.h"

#include <QThread>

GameFilesController::GameFilesController(SignalHub* signalHub, ThreadManager* threadManager, QObject* parent)
    : QObject(parent)
    , m_signalHub(signalHub)
    , m_threadManager(threadManager)
{
}

void GameFilesController::startScan(const QString& classicRoot, const QString& xseLogPath)
{
    if (m_scanning) {
        return;
    }

    m_scanning = true;
    emit scanStarted();
    if (m_signalHub) {
        emit m_signalHub->scanStarted();
    }

    // Create worker and thread (same pattern as ScanController)
    auto* worker = new GameFilesWorker();
    auto* thread = new QThread();

    // Connect worker signals to controller slots
    connect(worker, &GameFilesWorker::progress, this, &GameFilesController::scanProgress);
    connect(worker, &GameFilesWorker::finished, this, &GameFilesController::onWorkerFinished);
    connect(worker, &GameFilesWorker::error, this, &GameFilesController::onWorkerError);

    // Relay progress to SignalHub for global UI updates
    if (m_signalHub) {
        connect(worker, &GameFilesWorker::progress, m_signalHub, &SignalHub::scanProgress);
    }

    // Start the worker thread; invoke doScan once the thread is running
    connect(thread, &QThread::started, worker,
            [worker, classicRoot, xseLogPath]() { worker->doScan(classicRoot, xseLogPath); });

    m_threadManager->startWorker(QStringLiteral("game_files_scan"), thread, worker);
}

bool GameFilesController::isScanning() const
{
    return m_scanning;
}

void GameFilesController::onWorkerFinished(const QString& output, bool hasErrors, uint32_t totalChecks)
{
    m_scanning = false;
    emit scanFinished(output, hasErrors, totalChecks);
    if (m_signalHub) {
        emit m_signalHub->scanCompleted();
    }
}

void GameFilesController::onWorkerError(const QString& message)
{
    m_scanning = false;
    emit scanError(message);
    if (m_signalHub) {
        emit m_signalHub->scanError(message);
    }
}
