#include "papyrusworker.h"
#include "core/rust_qt_bridge.h"

#include <QDebug>
#include <QTimer>

#include "classic_cxx_bridge/scanner.h"
#include "rust/cxx.h"

PapyrusWorker::PapyrusWorker(QObject* parent)
    : QObject(parent)
{
}

void PapyrusWorker::start(const QString& logPath)
{
    try {
        // Create the Rust PapyrusAnalyzer via CXX bridge.
        // rust::Box<CxxPapyrusAnalyzer> is move-only; we release() it into
        // a raw pointer so we can store it as a member without exposing
        // the CXX-generated type in the header.
        auto analyzer = classic::scanner::papyrus_analyzer_new(classic::toRustString(logPath));
        m_analyzer = analyzer.into_raw();

        // Check log exists before starting
        auto* rawAnalyzer = static_cast<classic::scanner::CxxPapyrusAnalyzer*>(m_analyzer);
        if (!classic::scanner::papyrus_log_exists(*rawAnalyzer)) {
            emit monitoringError(QStringLiteral("Papyrus log file not found: ") + logPath);
            return;
        }

        // Initialize monitoring (positions cursor at end of file)
        classic::scanner::papyrus_start_monitoring(*rawAnalyzer);

        qDebug() << "PapyrusWorker: monitoring started for" << logPath;

        // Start 1-second polling timer
        m_timer = new QTimer(this);
        m_timer->setInterval(1000);
        connect(m_timer, &QTimer::timeout, this, &PapyrusWorker::onPollTimer);
        m_timer->start();

    } catch (const rust::Error& e) {
        emit monitoringError(QString::fromUtf8(e.what()));
    } catch (const std::exception& e) {
        emit monitoringError(QString::fromUtf8(e.what()));
    }
}

void PapyrusWorker::stop()
{
    qDebug() << "PapyrusWorker: monitoring stopped";
    if (m_timer) {
        m_timer->stop();
    }

    // Clean up the Rust analyzer by re-wrapping it in a Box (which drops it)
    if (m_analyzer) {
        auto* rawAnalyzer = static_cast<classic::scanner::CxxPapyrusAnalyzer*>(m_analyzer);
        // Reconstruct Box to trigger Rust Drop
        rust::Box<classic::scanner::CxxPapyrusAnalyzer>::from_raw(rawAnalyzer);
        m_analyzer = nullptr;
    }
}

void PapyrusWorker::onPollTimer()
{
    if (!m_analyzer) {
        return;
    }

    try {
        auto* rawAnalyzer = static_cast<classic::scanner::CxxPapyrusAnalyzer*>(m_analyzer);
        auto stats = classic::scanner::papyrus_check_updates(*rawAnalyzer);

        emit statsUpdated(stats.dumps, stats.stacks, stats.warnings, stats.errors, stats.lines_processed,
                          stats.dumps_stacks_ratio);
    } catch (const rust::Error& e) {
        emit monitoringError(QString::fromUtf8(e.what()));
    } catch (const std::exception& e) {
        emit monitoringError(QString::fromUtf8(e.what()));
    }
}
