#pragma once

#include <QObject>
#include <QString>

class SignalHub;
class ThreadManager;
class GameFilesWorker;

/// Controller that orchestrates game file scanning.
///
/// Follows the same pattern as ScanController: creates a GameFilesWorker,
/// moves it to a QThread via ThreadManager, and relays signals to the UI.
class GameFilesController : public QObject {
    Q_OBJECT

public:
    explicit GameFilesController(SignalHub* signalHub, ThreadManager* threadManager, QObject* parent = nullptr);

    /// Start a read-only Game Setup Intake run in a background thread.
    /// @param classicRoot CLASSIC root used by Rust to open the typed User Settings snapshot.
    /// @param xseLogPath Optional script-extender log used only as a detection hint.
    void startScan(const QString& classicRoot, const QString& xseLogPath);

    /// @return true if a scan is currently in progress.
    bool isScanning() const;

signals:
    void scanStarted();
    void scanProgress(float percent, const QString& status);
    void scanFinished(const QString& output, bool hasErrors, uint32_t totalChecks);
    void scanError(const QString& message);

private slots:
    void onWorkerFinished(const QString& output, bool hasErrors, uint32_t totalChecks);
    void onWorkerError(const QString& message);

private:
    bool m_scanning = false;
    SignalHub* m_signalHub = nullptr;
    ThreadManager* m_threadManager = nullptr;
};
