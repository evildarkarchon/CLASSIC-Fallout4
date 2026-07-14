#pragma once

#include <QObject>
#include <QString>
#include <QStringList>

#include "classic_cxx_bridge/scanner.h"
#include "core/guiusersettings.h"
#include "rust/cxx.h"

#include <atomic>

class ScanWorker : public QObject {
    Q_OBJECT

public:
    explicit ScanWorker(QObject* parent = nullptr);

    /// Executes one Crash Log Scan from an immutable, revision-approved typed settings value object.
    ///
    /// This method runs synchronously on the worker thread, consumes runtime paths separately from
    /// User Settings, and reports completion or failure through Qt signals without reopening settings.
    void doScan(const QStringList& logPaths, const QString& yamlRoot, const QString& yamlData,
                const classic::gui::CrashLogScanLaunchSettings& settings, const QString& baseDirectory,
                const QString& setupXseLogPath, bool targetedMode, const QStringList& targetedInputs);

public slots:
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
