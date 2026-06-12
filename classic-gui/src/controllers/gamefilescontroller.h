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

    /// Start a game file scan in a background thread.
    /// @param gameExePath Full path to the game executable (e.g. Fallout4.exe).
    /// @param gameRoot    Root directory of the game installation.
    /// @param docsPath    Documents/INI folder path used for docs checks.
    /// @param gameName    Game identifier string (e.g. "Fallout4").
    void startScan(const QString& gameExePath, const QString& gameRoot, const QString& docsPath,
                   const QString& gameName);

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
