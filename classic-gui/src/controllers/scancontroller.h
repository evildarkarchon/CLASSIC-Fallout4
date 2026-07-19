#pragma once

#include <QObject>
#include <QString>
#include <QStringList>

#include "core/guiusersettings.h"
#include "workers/scanrunpresentation.h"

class SignalHub;
class ThreadManager;
class ScanWorker;

class ScanController : public QObject {
    Q_OBJECT

public:
    explicit ScanController(SignalHub* signalHub, ThreadManager* threadManager, QObject* parent = nullptr);

    /// Starts one scan from an immutable, revision-approved typed settings value object.
    ///
    /// `setupXseLogPath` and `targetedInputs` are runtime-only hints. The value object is copied
    /// into the worker-thread callback, where Rust owns discovery and the remaining lifecycle, so
    /// no User Settings read or GUI-side source resolution occurs after launch begins.
    void startScan(const QString& installationRoot, const classic::gui::CrashLogScanLaunchSettings& settings,
                   const QString& setupXseLogPath = {}, const QStringList& targetedInputs = {});
    void cancelScan();
    bool isScanning() const;

signals:
    void scanStarted();
    void scanDiscovered(int totalLogs);
    void scanConcurrencySelected(int concurrency);
    void scanLogScanned(int index, bool success, const QString& logPath);
    void scanFinished(int total, int success, int errors);
    void scanNoLogsFound(const QString& message);
    void scanCancelled(const QString& message);
    void scanError(const QString& message);
    void scanWarning(const QString& message);
    void scanProgress(float percent, const QString& status, int completed, int total);
    void scanReportDirectoriesResolved(const QStringList& reportDirs);
    /// Relays the immutable Installed YAML Data selected for the active run to GUI consumers.
    void scanInstalledYamlDataResolved(const classic::gui::ScanRunInstalledYamlDataPresentation& installedYamlData);

private slots:
    void onWorkerFinished(int total, int success, int errors);
    /// Completes GUI cleanup for the expected no-logs terminal lifecycle state.
    void onWorkerNoLogsFound(const QString& message);
    /// Completes GUI cleanup for an expected safe-seam cancellation without presenting an error.
    void onWorkerCancelled(const QString& message);
    void onWorkerError(const QString& message);

private:
    bool m_scanning = false;
    SignalHub* m_signalHub = nullptr;
    ThreadManager* m_threadManager = nullptr;
    ScanWorker* m_currentWorker = nullptr;
};
