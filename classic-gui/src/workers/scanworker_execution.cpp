#include "scanworker_execution.h"

#include "core/rust_qt_bridge.h"
#include "scanprogressmodel.h"

#include "classic_cxx_bridge/config.h"
#include "classic_cxx_bridge/files.h"
#include "classic_cxx_bridge/scanner.h"
#include "rust/cxx.h"

#include <cstdint>
#include <stdexcept>

namespace {
std::string join_report_lines(const rust::Vec<rust::String>& reportLines) {
    std::string content;
    std::size_t totalSize = 0;
    for (const auto& line : reportLines) {
        totalSize += line.size();
    }
    content.reserve(totalSize);

    for (const auto& line : reportLines) {
        content += std::string(line.data(), line.size());
    }
    return content;
}

QString to_qstring(const rust::String& value) {
    return QString::fromUtf8(value.data(), static_cast<int>(value.size()));
}

class QtBatchProgressCallback final : public classic::scanner::ScanBatchProgressCallback {
public:
    QtBatchProgressCallback(int totalLogs,
                            const classic::gui::scanworker_execution::BatchProgressCallback& callback)
        : m_progressModel(totalLogs), m_callback(callback) {}

    void on_batch_progress(const classic::scanner::BatchProgressEvent& event) const override {
        const float percent = m_progressModel.update(event);
        m_callback(
            percent,
            to_qstring(event.log_path),
            static_cast<int>(event.completed),
            static_cast<int>(event.total)
        );
    }

private:
    mutable BatchProgressModel m_progressModel;
    classic::gui::scanworker_execution::BatchProgressCallback m_callback;
};
}

namespace classic::gui::scanworker_execution {
SingleScanResult executeSingleScan(const ScanExecutionConfig& config, const QString& logPath) {
    try {
        auto rustConfig = classic::scanner::build_full_scan_config(
            classic::toRustString(config.yamlRoot),
            classic::toRustString(config.yamlData),
            classic::toRustString(config.game),
            classic::toRustString(config.gameVersion),
            config.showFormIdValues,
            config.fcxMode,
            config.simplifyLogs
        );

        auto orchestrator = classic::scanner::orchestrator_new(*rustConfig);
        auto result = classic::scanner::orchestrator_process_log(
            *orchestrator,
            classic::toRustString(logPath)
        );

        SingleScanResult scanResult;
        scanResult.logPath = to_qstring(result.log_path);
        scanResult.success = result.success;
        if (!result.report_lines.empty()) {
            scanResult.reportContent = join_report_lines(result.report_lines);
        }
        return scanResult;
    } catch (const rust::Error& error) {
        throw std::runtime_error(error.what());
    }
}

QVector<BatchScanResult> executeBatchScan(const ScanExecutionConfig& config,
                                          const QStringList& logPaths,
                                          int maxConcurrentScans,
                                          const BatchProgressCallback& progressCallback) {
    try {
        auto rustConfig = classic::scanner::build_full_scan_config(
            classic::toRustString(config.yamlRoot),
            classic::toRustString(config.yamlData),
            classic::toRustString(config.game),
            classic::toRustString(config.gameVersion),
            config.showFormIdValues,
            config.fcxMode,
            config.simplifyLogs
        );

        auto orchestrator = classic::scanner::orchestrator_new(*rustConfig);

        rust::Vec<rust::String> rustPaths;
        for (const QString& path : logPaths) {
            rustPaths.push_back(classic::toRustString(path));
        }

        const uint32_t maxConcurrent =
            maxConcurrentScans > 0 ? static_cast<uint32_t>(maxConcurrentScans) : 0U;
        QtBatchProgressCallback callback(logPaths.size(), progressCallback);
        auto results = classic::scanner::orchestrator_process_logs_batch_with_progress(
            *orchestrator,
            rust::Slice<const rust::String>(rustPaths.data(), rustPaths.size()),
            maxConcurrent,
            callback
        );

        QVector<BatchScanResult> batchResults;
        batchResults.reserve(static_cast<qsizetype>(results.size()));
        for (const auto& result : results) {
            BatchScanResult batchResult;
            batchResult.inputIndex = result.input_index;
            batchResult.logPath = to_qstring(result.log_path);
            batchResult.success = result.success;
            if (!result.report_lines.empty()) {
                batchResult.reportContent = join_report_lines(result.report_lines);
            }
            batchResults.push_back(std::move(batchResult));
        }
        return batchResults;
    } catch (const rust::Error& error) {
        throw std::runtime_error(error.what());
    }
}

void writeAutoscanReport(const QString& logPath, const std::string& reportContent) {
    try {
        const QByteArray utf8Path = logPath.toUtf8();
        classic::files::write_autoscan_report(
            std::string(utf8Path.constData(), static_cast<std::size_t>(utf8Path.size())),
            reportContent
        );
    } catch (const rust::Error& error) {
        throw std::runtime_error(error.what());
    }
}
}
