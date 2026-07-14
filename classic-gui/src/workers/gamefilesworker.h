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
    /// Run Game Setup Intake from a read-only typed User Settings snapshot via CXX.
    ///
    /// Called from the QThread once it starts. Emits progress/finished/error
    /// signals back to the controller on the main thread.
    /// @param classicRoot CLASSIC root used by Rust to open User Settings.
    /// @param xseLogPath Optional script-extender log used as a detection hint.
    void doScan(const QString& classicRoot, const QString& xseLogPath);

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
