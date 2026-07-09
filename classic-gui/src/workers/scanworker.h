#pragma once

#include <QObject>
#include <QString>
#include <QStringList>

#include "classic_cxx_bridge/scanner.h"
#include "rust/cxx.h"

#include <atomic>

class ScanWorker : public QObject {
    Q_OBJECT

public:
    explicit ScanWorker(QObject* parent = nullptr);

public slots:
    void doScan(const QStringList& logPaths, const QString& yamlRoot, const QString& yamlData, const QString& game,
                const QString& gameVersion, bool showFormIdValues, bool fcxMode, bool simplifyLogs,
                bool moveUnsolvedLogs, const QString& unsolvedLogsDestination, int maxConcurrentScans,
                const QString& baseDirectory, const QString& customFolder, const QString& setupGameRoot,
                const QString& setupDocsRoot, const QString& setupGameExePath, bool targetedMode,
                const QStringList& targetedInputs);
    void requestCancel();

signals:
    void progress(float percent, const QString& status);
    void progressDetailed(float percent, const QString& status, int completed, int total);
    void logScanned(int index, bool success, const QString& logPath);
    void finished(int totalLogs, int successCount, int errorCount);
    void error(const QString& message);

private:
    std::atomic<bool> m_cancelled{false};
    rust::Box<classic::scanner::ScanCancellationToken> m_cancellationToken;
};
