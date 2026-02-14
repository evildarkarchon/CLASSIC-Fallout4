#pragma once

#include <QObject>
#include <QString>

class SignalHub;
class ThreadManager;
class ScanWorker;

class ScanController : public QObject {
    Q_OBJECT

public:
    explicit ScanController(SignalHub* signalHub,
                            ThreadManager* threadManager,
                            QObject* parent = nullptr);

    void startScan(const QString& yamlRoot,
                   const QString& yamlData,
                   const QString& game,
                   bool vrMode,
                   const QString& customFolder);
    void cancelScan();
    bool isScanning() const;

signals:
    void scanStarted();
    void scanFinished(int total, int success, int errors);
    void scanError(const QString& message);
    void scanProgress(float percent, const QString& status);

private slots:
    void onWorkerFinished(int total, int success, int errors);
    void onWorkerError(const QString& message);

private:
    bool m_scanning = false;
    SignalHub* m_signalHub = nullptr;
    ThreadManager* m_threadManager = nullptr;
    ScanWorker* m_currentWorker = nullptr;
};
