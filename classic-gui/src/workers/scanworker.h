#pragma once

#include <QObject>
#include <QString>
#include <QStringList>

class ScanWorker : public QObject {
    Q_OBJECT

public:
    explicit ScanWorker(QObject* parent = nullptr);

public slots:
    void doScan(const QStringList& logPaths,
                const QString& yamlRoot,
                const QString& yamlData,
                const QString& game,
                bool vrMode,
                bool showFormIdValues,
                bool fcxMode,
                bool simplifyLogs,
                bool moveUnsolvedLogs,
                int maxConcurrentScans);
    void requestCancel();

signals:
    void progress(float percent, const QString& status);
    void logScanned(int index, bool success, const QString& logPath);
    void finished(int totalLogs, int successCount, int errorCount);
    void error(const QString& message);

private:
    bool m_cancelled = false;
};
