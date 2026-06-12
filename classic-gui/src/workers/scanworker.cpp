#include "scanworker.h"
#include "core/rust_qt_bridge.h"
#include "scanprogressmodel.h"

#include <QDebug>

#include "classic_cxx_bridge/config.h"
#include "classic_cxx_bridge/files.h"
#include "classic_cxx_bridge/scanner.h"
#include "rust/cxx.h"

#include <cstdint>
#include <filesystem>
#include <string>

namespace {
std::string join_report_lines(const rust::Vec<rust::String>& report_lines)
{
    std::string content;
    std::size_t total_size = 0;
    for (const auto& line : report_lines) {
        total_size += line.size();
    }
    content.reserve(total_size);

    for (const auto& line : report_lines) {
        content += std::string(line.data(), line.size());
    }
    return content;
}

std::string resolve_log_path(const rust::String& result_log_path_rust, const QString& fallback)
{
    const std::string result_log_path(result_log_path_rust.data(), result_log_path_rust.size());
    if (!result_log_path.empty()) {
        return result_log_path;
    }
    return std::string(fallback.toUtf8().constData());
}

std::string build_autoscan_path(const std::string& log_path)
{
    std::filesystem::path crash_log(log_path);
    const auto report_name = crash_log.stem().string() + "-AUTOSCAN.md";
    return (crash_log.parent_path() / report_name).string();
}

void move_file_if_exists(const std::filesystem::path& source, const std::filesystem::path& dest_dir)
{
    std::error_code ec;
    if (!std::filesystem::exists(source, ec)) {
        return;
    }

    std::filesystem::create_directories(dest_dir, ec);
    if (ec) {
        return;
    }

    const auto destination = dest_dir / source.filename();
    std::filesystem::rename(source, destination, ec);
    if (!ec) {
        return;
    }

    ec.clear();
    std::filesystem::copy_file(source, destination, std::filesystem::copy_options::overwrite_existing, ec);
    if (ec) {
        return;
    }
    std::filesystem::remove(source, ec);
}

void move_unsolved_artifacts(const std::string& log_path, const QString& yaml_root)
{
    if (log_path.empty()) {
        return;
    }

    std::error_code ec;
    const auto backup_dir = std::filesystem::path(yaml_root.toStdWString()) / L"CLASSIC Backup" / L"Unsolved Logs";
    if (backup_dir.empty()) {
        return;
    }

    const std::filesystem::path crash_log(log_path);
    const std::filesystem::path autoscan_report(build_autoscan_path(log_path));
    move_file_if_exists(crash_log, backup_dir);
    move_file_if_exists(autoscan_report, backup_dir);
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
{
}

void ScanWorker::requestCancel()
{
    qDebug() << "ScanWorker: cancellation requested";
    m_cancelled.store(true);
}

void ScanWorker::doScan(const QStringList& logPaths, const QString& yamlRoot, const QString& yamlData,
                        const QString& game, const QString& gameVersion, bool showFormIdValues, bool fcxMode,
                        bool simplifyLogs, bool moveUnsolvedLogs, int maxConcurrentScans, bool targetedMode)
{
    m_cancelled.store(false);

    int total = logPaths.size();
    qDebug() << "ScanWorker: starting scan," << total << "logs," << (targetedMode ? "targeted" : "standard") << "mode";
    int successCount = 0;
    int errorCount = 0;
    // Targeted scans operate on user-selected source files and should not relocate them.
    const bool shouldMoveUnsolvedLogs = moveUnsolvedLogs && !targetedMode;

    try {
        // rust::Box<T> is non-nullable and non-default-constructible.
        // Must be initialized at declaration inside the try block.
        auto config = classic::scanner::build_full_scan_config(
            classic::toRustString(yamlRoot), classic::toRustString(yamlData), classic::toRustString(game),
            classic::toRustString(gameVersion), showFormIdValues, fcxMode, simplifyLogs);

        auto orch = classic::scanner::orchestrator_new(*config);

        // Default to batch mode for multi-log scans and stream progress updates
        // from Rust via CXX callback.
        if (total > 1) {
            if (m_cancelled.load()) {
                emit error(QStringLiteral("Scan cancelled by user"));
                return;
            }

            emit progress(0.0f, QStringLiteral("Scanning logs in parallel..."));
            emit progressDetailed(0.0f, QStringLiteral("Scanning logs in parallel..."), 0, total);

            rust::Vec<rust::String> rustPaths;
            for (int i = 0; i < total; ++i) {
                rustPaths.push_back(classic::toRustString(logPaths[i]));
            }

            const uint32_t maxConcurrent = maxConcurrentScans > 0 ? static_cast<uint32_t>(maxConcurrentScans) : 0U;
            BatchProgressCallback progress_callback(*this, total);
            auto results = classic::scanner::orchestrator_process_logs_batch_with_progress(
                *orch, rust::Slice<const rust::String>(rustPaths.data(), rustPaths.size()), maxConcurrent,
                progress_callback);

            for (const auto& result : results) {
                const int index = static_cast<int>(qMin(result.input_index, static_cast<uint32_t>(total - 1)));
                const QString fallbackPath = logPaths[index];
                const std::string reportLogPath = resolve_log_path(result.log_path, fallbackPath);
                const QString resolvedPath = QString::fromStdString(reportLogPath);

                bool scanSuccess = result.success;
                if (scanSuccess && !result.report_lines.empty()) {
                    try {
                        classic::files::write_autoscan_report(reportLogPath, join_report_lines(result.report_lines));
                    } catch (const rust::Error&) {
                        scanSuccess = false;
                    }
                }

                if (!scanSuccess && shouldMoveUnsolvedLogs) {
                    move_unsolved_artifacts(reportLogPath, yamlRoot);
                }

                if (scanSuccess) {
                    ++successCount;
                } else {
                    ++errorCount;
                }

                emit logScanned(index, scanSuccess, resolvedPath);
            }

            qDebug() << "ScanWorker: batch complete -" << successCount << "success," << errorCount << "errors of"
                     << total;
            emit progress(100.0f, QStringLiteral("Complete"));
            emit progressDetailed(100.0f, QStringLiteral("Complete"), total, total);
            emit finished(total, successCount, errorCount);
            return;
        }

        for (int i = 0; i < total; ++i) {
            if (m_cancelled.load()) {
                emit error(QStringLiteral("Scan cancelled by user"));
                return;
            }

            float percent = (static_cast<float>(i) * 100.0f) / static_cast<float>(total);
            emit progress(percent, logPaths[i]);
            emit progressDetailed(percent, logPaths[i], i, total);

            try {
                auto result = classic::scanner::orchestrator_process_log(*orch, classic::toRustString(logPaths[i]));

                bool scan_success = result.success;
                const std::string report_log_path = resolve_log_path(result.log_path, logPaths[i]);

                if (scan_success && !result.report_lines.empty()) {
                    try {
                        classic::files::write_autoscan_report(report_log_path, join_report_lines(result.report_lines));
                    } catch (const rust::Error&) {
                        scan_success = false;
                    }
                }

                if (!scan_success && shouldMoveUnsolvedLogs) {
                    move_unsolved_artifacts(report_log_path, yamlRoot);
                }

                if (scan_success) {
                    ++successCount;
                } else {
                    ++errorCount;
                }
                emit logScanned(i, scan_success, logPaths[i]);

            } catch (const rust::Error&) {
                ++errorCount;
                if (shouldMoveUnsolvedLogs) {
                    move_unsolved_artifacts(std::string(logPaths[i].toUtf8().constData()), yamlRoot);
                }
                emit logScanned(i, false, logPaths[i]);
            }
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
