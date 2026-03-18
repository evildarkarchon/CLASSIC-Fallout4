#include "scancontroller.h"
#include "core/rust_qt_bridge.h"
#include "core/signalhub.h"
#include "core/threadmanager.h"
#include "workers/scanworker.h"

#include "classic_cxx_bridge/files.h"
#include "classic_cxx_bridge/yaml.h"
#include "rust/cxx.h"

#include <QCoreApplication>
#include <QDir>
#include <QFileInfo>
#include <QThread>

namespace {

QString cleanDirectoryPath(const rust::String& value)
{
    const QString trimmed = classic::toQString(value).trimmed();
    return trimmed.isEmpty() ? QString() : QDir::cleanPath(trimmed);
}

QString resolveXseFolderFromLocalYaml(const QString& yamlData, const QString& game)
{
    const QString localYamlPath = QDir(yamlData).filePath(QStringLiteral("CLASSIC %1 Local.yaml").arg(game));

    try {
        auto ops = classic::yaml::yaml_ops_new();
        classic::yaml::yaml_ops_load_file(*ops, classic::toRustString(localYamlPath));

        const QString xsePath = cleanDirectoryPath(classic::yaml::yaml_ops_get_string(*ops, "Game_Info.Docs_Folder_XSE", ""));
        if (!xsePath.isEmpty()) {
            return xsePath;
        }

        const QString docsRoot =
            cleanDirectoryPath(classic::yaml::yaml_ops_get_string(*ops, "Game_Info.Root_Folder_Docs", ""));
        if (!docsRoot.isEmpty()) {
            return QDir(docsRoot).filePath(QStringLiteral("F4SE"));
        }

        return {};
    } catch (const rust::Error&) {
        return {};
    }
}

bool isCrashLogPath(const QString& path)
{
    const QFileInfo info(path);
    const QString name = info.fileName();
    return name.startsWith(QStringLiteral("crash-"), Qt::CaseInsensitive) &&
           name.endsWith(QStringLiteral(".log"), Qt::CaseInsensitive);
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
                               bool moveUnsolvedLogs, int maxConcurrentScans, const QString& customFolder,
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

    // Collect crash logs -- targeted mode or standard discovery
    QStringList logPathsList;
    try {
        if (!targetedInputs.isEmpty()) {
            rust::Vec<rust::String> rustInputs;
            rustInputs.reserve(static_cast<size_t>(targetedInputs.size()));
            for (const auto& p : targetedInputs) {
                rustInputs.push_back(classic::toRustString(p));
            }
            auto resolution = classic::files::resolve_targeted_inputs({rustInputs.data(), rustInputs.size()});

            logPathsList.reserve(static_cast<int>(resolution.logs.size()));
            for (const auto& rpath : resolution.logs) {
                const QString qpath = classic::toQString(rpath);
                if (isCrashLogPath(qpath)) {
                    logPathsList.append(qpath);
                }
            }

            if (!resolution.rejected_paths.empty()) {
                for (size_t i = 0; i < resolution.rejected_paths.size(); ++i) {
                    qWarning("Targeted input rejected: %s (%s)",
                             qPrintable(classic::toQString(resolution.rejected_paths[i])),
                             qPrintable(classic::toQString(resolution.rejected_reasons[i])));
                }
            }
        } else {
            // Intentionally collect under the portable app root. CLASSIC is distributed as a
            // portable app, so the application directory is expected to be writable and we do
            // not use a separate per-user/AppData fallback here.
            const QString baseDir = QDir::cleanPath(QCoreApplication::applicationDirPath());
            auto xseFolder = resolveXseFolderFromLocalYaml(yamlData, game);
            auto collector = classic::files::log_collector_new(
                classic::toRustString(baseDir), classic::toRustString(xseFolder), classic::toRustString(customFolder));
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

    if (logPathsList.isEmpty()) {
        m_scanning = false;
        emit scanError(QStringLiteral("No crash logs found"));
        if (m_signalHub) {
            emit m_signalHub->scanError(QStringLiteral("No crash logs found"));
        }
        return;
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
             moveUnsolvedLogs, maxConcurrentScans]() {
                worker->doScan(logPathsList, yamlRoot, yamlData, game, gameVersion, showFormIdValues, fcxMode,
                               simplifyLogs, moveUnsolvedLogs, maxConcurrentScans);
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
