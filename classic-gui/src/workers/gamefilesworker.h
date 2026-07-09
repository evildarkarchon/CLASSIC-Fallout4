#pragma once

#include <QObject>
#include <QString>

/// Worker object for game file scanning on a background QThread.
///
/// Follows the same moveToThread() pattern as ScanWorker: the controller
/// creates the worker, moves it to a QThread, and connects signals/slots.
/// The worker calls CXX bridge functions (classic::scangame) that invoke
/// Rust business logic via block_on().
class GameFilesWorker : public QObject {
    Q_OBJECT

public:
    explicit GameFilesWorker(QObject* parent = nullptr);

public slots:
    /// Run Game Setup Intake via the CXX bridge.
    ///
    /// Called from the QThread once it starts. Emits progress/finished/error
    /// signals back to the controller on the main thread.
    /// @param gameExePath Saved or caller-validated game executable path.
    /// @param gameVersion Saved game-version selection forwarded to setup intake.
    void doScan(const QString& gameExePath, const QString& gameRoot, const QString& docsPath, const QString& gameName,
                const QString& gameVersion);

signals:
    /// Emitted periodically to indicate scan progress.
    void progress(float percent, const QString& status);

    /// Emitted when the scan completes successfully.
    /// @param output The Rust-rendered intake report.
    /// @param hasErrors Whether the report requires user attention.
    /// @param totalChecks Number of intake checks that were executed.
    void finished(const QString& output, bool hasErrors, uint32_t totalChecks);

    /// Emitted when the scan fails with an unrecoverable error.
    void error(const QString& message);
};
