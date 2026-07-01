#include "scanworker.h"
#include "core/rust_qt_bridge.h"
#include "scanprogressmodel.h"

#include <QDebug>

#include "classic_cxx_bridge/config.h"
#include "classic_cxx_bridge/scanner.h"
#include "rust/cxx.h"

#include <cstdint>
#include <string>

namespace {
std::string resolve_log_path(const rust::String& result_log_path_rust, const QString& fallback)
{
    const std::string result_log_path(result_log_path_rust.data(), result_log_path_rust.size());
    if (!result_log_path.empty()) {
        return result_log_path;
    }
    return std::string(fallback.toUtf8().constData());
}

class BatchProgressCallback final : public classic::scanner::ScanBatchProgressCallback {
public:
    BatchProgressCallback(ScanWorker& worker, int total_logs)
        : m_worker(worker)
        , m_progressModel(total_logs)
    {
    }

    void on_batch_progress(const classic::scanner::BatchProgressEvent& event) const override
    {
        const float percent = m_progressModel.update(event);
        const QString status = QString::fromUtf8(event.log_path.data(), static_cast<int>(event.log_path.size()));
        const int completed = static_cast<int>(event.completed);
        const int total = static_cast<int>(event.total);
        Q_EMIT m_worker.progress(percent, status);
        Q_EMIT m_worker.progressDetailed(percent, status, completed, total);
    }

private:
    ScanWorker& m_worker;
    mutable BatchProgressModel m_progressModel;
};
} // namespace

ScanWorker::ScanWorker(QObject* parent)
    : QObject(parent)
    , m_cancellationToken(classic::scanner::scan_cancellation_token_new())
{
}

void ScanWorker::requestCancel()
{
    qDebug() << "ScanWorker: cancellation requested";
    m_cancelled.store(true);
    classic::scanner::scan_cancellation_token_cancel(*m_cancellationToken);
}

void ScanWorker::doScan(const QStringList& logPaths, const QString& yamlRoot, const QString& yamlData,
                        const QString& game, const QString& gameVersion, bool showFormIdValues, bool fcxMode,
                        bool simplifyLogs, bool moveUnsolvedLogs, int maxConcurrentScans, bool targetedMode)
{
    m_cancelled.store(false);
    classic::scanner::scan_cancellation_token_reset(*m_cancellationToken);

    int total = logPaths.size();
    qDebug() << "ScanWorker: starting scan," << total << "logs," << (targetedMode ? "targeted" : "standard") << "mode";
    int successCount = 0;
    int errorCount = 0;

    try {
        if (m_cancelled.load()) {
            emit error(QStringLiteral("Scan cancelled by user"));
            return;
        }

        emit progress(0.0f, QStringLiteral("Scanning logs..."));
        emit progressDetailed(0.0f, QStringLiteral("Scanning logs..."), 0, total);

        rust::Vec<rust::String> rustPaths;
        for (int i = 0; i < total; ++i) {
            rustPaths.push_back(classic::toRustString(logPaths[i]));
        }

        const uint32_t maxConcurrent = maxConcurrentScans > 0 ? static_cast<uint32_t>(maxConcurrentScans) : 0U;
        BatchProgressCallback progress_callback(*this, total);
        auto results = classic::scanner::scan_run_execute(
            classic::toRustString(yamlRoot), classic::toRustString(yamlData), classic::toRustString(game),
            classic::toRustString(gameVersion), showFormIdValues, fcxMode, simplifyLogs, moveUnsolvedLogs,
            targetedMode, maxConcurrent, rust::Slice<const rust::String>(rustPaths.data(), rustPaths.size()),
            progress_callback, *m_cancellationToken);

        for (const auto& result : results) {
            const int index = static_cast<int>(qMin(result.input_index, static_cast<uint32_t>(total - 1)));
            const QString fallbackPath = logPaths[index];
            const std::string reportLogPath = resolve_log_path(result.log_path, fallbackPath);
            const QString resolvedPath = QString::fromStdString(reportLogPath);

            if (result.success) {
                ++successCount;
            } else {
                ++errorCount;
            }

            emit logScanned(index, result.success, resolvedPath);
        }

        qDebug() << "ScanWorker: scan complete -" << successCount << "success," << errorCount << "errors of" << total;
        emit progress(100.0f, QStringLiteral("Complete"));
        emit progressDetailed(100.0f, QStringLiteral("Complete"), total, total);
        emit finished(total, successCount, errorCount);

    } catch (const rust::Error& e) {
        emit error(QString::fromUtf8(e.what()));
    } catch (const std::exception& e) {
        emit error(QString::fromUtf8(e.what()));
    }
}
