#pragma once

#include <QObject>
#include <QString>
#include <QStringList>

#include "classic_cxx_bridge/scanner.h"
#include "core/guiusersettings.h"
#include "rust/cxx.h"
#include "workers/scanrunpresentation.h"

class ScanWorker : public QObject {
    Q_OBJECT

public:
    explicit ScanWorker(QObject* parent = nullptr);
    /// Creates a worker that can synchronously obtain an explicit GUI recovery choice.
    ScanWorker(classic::gui::ScanRunLocalIgnoreRecoveryPrompt localIgnoreRecoveryPrompt, QObject* parent = nullptr);

    /// Executes one Rust-owned Crash Log Scan Run from immutable, revision-approved GUI settings.
    ///
    /// Discovery, scheduling, durable finalization, and terminal ordering remain inside Rust. This
    /// synchronous worker-thread call only projects the tagged request and presents events/results.
    void doScan(const QString& installationRoot, const classic::gui::CrashLogScanLaunchSettings& settings,
                const QString& baseDirectory, const QString& setupXseLogPath, const QStringList& targetedInputs);

public slots:
    void requestCancel();

signals:
    void progress(float percent, const QString& status);
    void progressDetailed(float percent, const QString& status, int completed, int total);
    void discoveryCompleted(int totalLogs, const QString& rejectionWarning, const QStringList& reportDirectories);
    void effectiveConcurrencySelected(int concurrency);
    void reportDirectoriesResolved(const QStringList& reportDirectories);
    /// Publishes the exact Qt-owned YAML Data selection before terminal lifecycle signals destroy the worker.
    void installedYamlDataResolved(const classic::gui::ScanRunInstalledYamlDataPresentation& installedYamlData);
    void logScanned(int index, bool success, const QString& logPath);
    /// Reports a completed run, carrying the rendered run as rich text alongside its counts.
    ///
    /// `message` is what the other three terminal signals carry, and it is here for the same
    /// reason: without it the window had nothing to say about a completed run and composed a
    /// sentence of its own, which is the one thing an adapter may not do. The counts stay because
    /// consumers key on them as data; they are no longer the raw material for prose.
    void finished(int totalLogs, int successCount, int errorCount, const QString& message);
    void noLogsFound(const QString& message);
    void cancelled(const QString& message);
    void error(const QString& message);

private:
    rust::Box<classic::scanner::ScanRunCancellation> m_cancellation;
    classic::gui::ScanRunLocalIgnoreRecoveryPrompt m_localIgnoreRecoveryPrompt;
};
