#include "scancontroller.h"
#include "core/signalhub.h"
#include "core/threadmanager.h"
#include "workers/scanworker.h"
#include "core/rust_qt_bridge.h"

#include "rust/cxx.h"
#include "classic_cxx_bridge/files.h"

#include <QThread>
#include <QDir>

ScanController::ScanController(SignalHub* signalHub,
                               ThreadManager* threadManager,
                               QObject* parent)
    : QObject(parent)
    , m_signalHub(signalHub)
    , m_threadManager(threadManager) {}

void ScanController::startScan(const QString& yamlRoot,
                                const QString& yamlData,
                                const QString& game,
                                bool vrMode,
                                bool showFormIdValues,
                                bool fcxMode,
                                bool simplifyLogs,
                                bool moveUnsolvedLogs,
                                int maxConcurrentScans,
                                const QString& customFolder) {
    if (m_scanning) {
        return;
    }

    m_scanning = true;
    emit scanStarted();

    // Collect crash logs via Rust file collector
    QStringList logPathsList;
    try {
        auto baseDir = QDir::currentPath();
        auto collector = classic::files::log_collector_new(
            classic::toRustString(baseDir),
            rust::String(),  // xse_folder (empty)
            classic::toRustString(customFolder)
        );
        auto rustPaths = classic::files::log_collector_collect_crash_logs(*collector);

        logPathsList.reserve(static_cast<int>(rustPaths.size()));
        for (const auto& rpath : rustPaths) {
            logPathsList.append(classic::toQString(rpath));
        }
    } catch (const rust::Error& e) {
        m_scanning = false;
        emit scanError(QString::fromUtf8(e.what()));
        if (m_signalHub) {
            emit m_signalHub->scanError(QString::fromUtf8(e.what()));
        }
        return;
    }

    if (logPathsList.isEmpty()) {
        m_scanning = false;
        emit scanError(QStringLiteral("No crash logs found"));
        if (m_signalHub) {
            emit m_signalHub->scanError(QStringLiteral("No crash logs found"));
        }
        return;
    }

    // Create worker and thread
    auto* worker = new ScanWorker();
    auto* thread = new QThread();
    m_currentWorker = worker;

    // Connect worker signals to controller slots
    connect(worker, &ScanWorker::progress, this, &ScanController::scanProgress);
    connect(worker, &ScanWorker::finished, this, &ScanController::onWorkerFinished);
    connect(worker, &ScanWorker::error, this, &ScanController::onWorkerError);

    // Relay progress to SignalHub
    if (m_signalHub) {
        connect(worker, &ScanWorker::progress, m_signalHub, &SignalHub::scanProgress);
    }

    // Start the worker thread and invoke doScan once the thread is running
    connect(thread, &QThread::started, worker, [worker, logPathsList, yamlRoot, yamlData, game, vrMode, showFormIdValues, fcxMode, simplifyLogs, moveUnsolvedLogs, maxConcurrentScans]() {
        worker->doScan(logPathsList, yamlRoot, yamlData, game, vrMode, showFormIdValues, fcxMode, simplifyLogs, moveUnsolvedLogs, maxConcurrentScans);
    });

    m_threadManager->startWorker(QStringLiteral("crash_scan"), thread, worker);
}

void ScanController::cancelScan() {
    if (m_scanning && m_currentWorker) {
        m_currentWorker->requestCancel();
    }
}

bool ScanController::isScanning() const {
    return m_scanning;
}

void ScanController::onWorkerFinished(int total, int success, int errors) {
    m_scanning = false;
    m_currentWorker = nullptr;
    emit scanFinished(total, success, errors);
    if (m_signalHub) {
        emit m_signalHub->scanCompleted();
    }
}

void ScanController::onWorkerError(const QString& message) {
    m_scanning = false;
    m_currentWorker = nullptr;
    emit scanError(message);
    if (m_signalHub) {
        emit m_signalHub->scanError(message);
    }
}
