#pragma once

#include <QObject>
#include <QString>

class QTimer;

/// Background worker for Papyrus log monitoring via 1-second polling.
///
/// Runs on a QThread managed by ThreadManager. Creates a CXX Papyrus
/// analyzer, calls start_monitoring() once, then polls check_updates()
/// every second. Stats are forwarded to the UI via the statsUpdated signal.
class PapyrusWorker : public QObject {
    Q_OBJECT

public:
    explicit PapyrusWorker(QObject* parent = nullptr);

public slots:
    /// Begin monitoring the Papyrus log at the given path.
    /// Called once after the worker is moved to its thread.
    void start(const QString& logPath);

    /// Stop the polling timer. Called from the main thread via signal.
    void stop();

signals:
    /// Emitted every polling cycle with updated Papyrus stats.
    void statsUpdated(uint32_t dumps,
                      uint32_t stacks,
                      uint32_t warnings,
                      uint32_t errors,
                      uint32_t linesProcessed,
                      QString severity,
                      double dumpsStacksRatio,
                      uint32_t totalIssues);

    /// Emitted if monitoring setup fails (e.g. log file not found).
    void monitoringError(QString message);

private slots:
    void onPollTimer();

private:
    QTimer* m_timer = nullptr;

    // Opaque pointer to Rust CxxPapyrusAnalyzer (Box<T> stored as void*).
    // We use void* because the CXX-generated type is only available in the .cpp.
    void* m_analyzer = nullptr;
};
