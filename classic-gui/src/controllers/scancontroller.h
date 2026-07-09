#pragma once

#include <QObject>
#include <QString>
#include <QStringList>

class SignalHub;
class ThreadManager;
class ScanWorker;

class ScanController : public QObject {
    Q_OBJECT

public:
    explicit ScanController(SignalHub* signalHub, ThreadManager* threadManager, QObject* parent = nullptr);

    void startScan(const QString& yamlRoot, const QString& yamlData, const QString& game, const QString& gameVersion,
                   bool showFormIdValues, bool fcxMode, bool simplifyLogs, bool moveUnsolvedLogs,
                   const QString& unsolvedLogsDestination, int maxConcurrentScans, const QString& customFolder,
                   const QStringList& targetedInputs = {});
    void cancelScan();
    bool isScanning() const;

signals:
    void scanStarted();
    void scanDiscovered(int totalLogs);
    void scanLogScanned(int index, bool success, const QString& logPath);
    void scanFinished(int total, int success, int errors);
    void scanError(const QString& message);
    void scanWarning(const QString& message);
    void scanProgress(float percent, const QString& status, int completed, int total);
    void scanReportDirectoriesResolved(const QStringList& reportDirs);

private slots:
    void onWorkerFinished(int total, int success, int errors);
    void onWorkerError(const QString& message);

private:
    bool m_scanning = false;
    SignalHub* m_signalHub = nullptr;
    ThreadManager* m_threadManager = nullptr;
    ScanWorker* m_currentWorker = nullptr;
};
