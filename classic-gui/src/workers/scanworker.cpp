#include "scanworker.h"
#include "core/rust_qt_bridge.h"
#include "scanprogressmodel.h"

#include <QDebug>

#include "classic_cxx_bridge/config.h"
#include "classic_cxx_bridge/scanner.h"
#include "rust/cxx.h"

#include <cstdint>
#include <string>
#include <utility>

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
                        bool simplifyLogs, bool moveUnsolvedLogs, const QString& unsolvedLogsDestination,
                        int maxConcurrentScans, const QString& baseDirectory, const QString& customFolder,
                        const QString& setupGameRoot, const QString& setupDocsRoot, const QString& setupGameExePath,
                        const QString& setupXseLogPath, bool targetedMode, const QStringList& targetedInputs)
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
        rust::Vec<rust::String> rustTargetedInputs;
        for (const auto& input : targetedInputs) {
            rustTargetedInputs.push_back(classic::toRustString(input));
        }

        const uint32_t maxConcurrent = maxConcurrentScans > 0 ? static_cast<uint32_t>(maxConcurrentScans) : 0U;
        BatchProgressCallback progress_callback(*this, total);
        classic::scanner::ScanRunRequestDto request{};
        request.yaml_dir_root = classic::toRustString(yamlRoot);
        request.yaml_dir_data = classic::toRustString(yamlData);
        request.game = classic::toRustString(game);
        request.game_version = classic::toRustString(gameVersion);
        request.base_directory = classic::toRustString(baseDirectory.isEmpty() ? yamlRoot : baseDirectory);
        request.custom_scan_directory = classic::toRustString(customFolder);
        request.configured_documents_root = classic::toRustString(QString{});
        request.show_formid_values = showFormIdValues;
        request.fcx_mode = fcxMode;
        request.simplify_logs = simplifyLogs;
        request.move_unsolved_logs = moveUnsolvedLogs;
        request.unsolved_logs_destination = classic::toRustString(unsolvedLogsDestination);
        request.targeted_mode = targetedMode;
        request.setup_game_root = classic::toRustString(setupGameRoot);
        request.setup_docs_root = classic::toRustString(setupDocsRoot);
        request.setup_game_exe_path = classic::toRustString(setupGameExePath);
        request.setup_xse_log_path = classic::toRustString(setupXseLogPath);
        request.max_concurrent = maxConcurrent;
        request.targeted_inputs = std::move(rustTargetedInputs);
        request.log_paths = std::move(rustPaths);
        auto scanResult = classic::scanner::scan_run_execute(request, progress_callback, *m_cancellationToken);
        const auto& results = scanResult.logs;

        const QString runStatus = QString::fromUtf8(scanResult.status.data(), static_cast<int>(scanResult.status.size()));
        if (runStatus == QStringLiteral("setup_failed")) {
            const QString message =
                scanResult.message.empty()
                    ? QStringLiteral("Crash Log Scan setup failed")
                    : QString::fromUtf8(scanResult.message.data(), static_cast<int>(scanResult.message.size()));
            emit error(message);
            return;
        }
        if (runStatus == QStringLiteral("no_crash_logs_found")) {
            emit error(QStringLiteral("No crash logs found"));
            return;
        }

        total = static_cast<int>(scanResult.total);

        for (const auto& result : results) {
            const bool hasFallbackPath = result.input_index < static_cast<uint32_t>(logPaths.size());
            const int resultIndex = static_cast<int>(result.input_index);
            const QString fallbackPath =
                hasFallbackPath ? logPaths[resultIndex] : QString{};
            const std::string reportLogPath = resolve_log_path(result.log_path, fallbackPath);
            const QString resolvedPath = QString::fromStdString(reportLogPath);

            if (result.success) {
                ++successCount;
            } else {
                ++errorCount;
            }

            emit logScanned(resultIndex, result.success, resolvedPath);
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
