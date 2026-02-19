#include "scanworker.h"
#include "core/rust_qt_bridge.h"

#include "rust/cxx.h"
#include "classic_cxx_bridge/scanner.h"
#include "classic_cxx_bridge/config.h"
#include "classic_cxx_bridge/files.h"

#include <string>

namespace {
std::string join_report_lines(const rust::Vec<rust::String>& report_lines) {
    std::string content;
    for (const auto& line : report_lines) {
        content += std::string(line.data(), line.size());
        content += '\n';
    }
    return content;
}
}

ScanWorker::ScanWorker(QObject* parent)
    : QObject(parent) {}

void ScanWorker::requestCancel() {
    m_cancelled = true;
}

void ScanWorker::doScan(const QStringList& logPaths,
                        const QString& yamlRoot,
                        const QString& yamlData,
                        const QString& game,
                        bool vrMode,
                        bool showFormIdValues,
                        bool fcxMode,
                        bool simplifyLogs) {
    m_cancelled = false;

    int total = logPaths.size();
    int successCount = 0;
    int errorCount = 0;

    try {
        // rust::Box<T> is non-nullable and non-default-constructible.
        // Must be initialized at declaration inside the try block.
        auto config = classic::scanner::build_full_scan_config(
            classic::toRustString(yamlRoot),
            classic::toRustString(yamlData),
            classic::toRustString(game),
            vrMode,
            showFormIdValues,
            fcxMode,
            simplifyLogs
        );

        auto orch = classic::scanner::orchestrator_new(*config);

        for (int i = 0; i < total; ++i) {
            if (m_cancelled) {
                emit error(QStringLiteral("Scan cancelled by user"));
                return;
            }

            float percent = (static_cast<float>(i) * 100.0f) / static_cast<float>(total);
            emit progress(percent, logPaths[i]);

            try {
                auto result = classic::scanner::orchestrator_process_log(
                    *orch,
                    classic::toRustString(logPaths[i])
                );

                bool scan_success = result.success;

                if (scan_success && !result.report_lines.empty()) {
                    try {
                        const auto report_content = join_report_lines(result.report_lines);
                        const std::string result_log_path(result.log_path.data(), result.log_path.size());
                        const auto report_log_path =
                            result_log_path.empty() ? std::string(logPaths[i].toUtf8().constData()) : result_log_path;
                        classic::files::write_autoscan_report(
                            report_log_path,
                            report_content
                        );
                    } catch (const rust::Error&) {
                        scan_success = false;
                    }
                }

                if (scan_success) {
                    ++successCount;
                } else {
                    ++errorCount;
                }
                emit logScanned(i, scan_success, logPaths[i]);

            } catch (const rust::Error&) {
                ++errorCount;
                emit logScanned(i, false, logPaths[i]);
            }
        }

        emit progress(100.0f, QStringLiteral("Complete"));
        emit finished(total, successCount, errorCount);

    } catch (const rust::Error& e) {
        emit error(QString::fromUtf8(e.what()));
    } catch (const std::exception& e) {
        emit error(QString::fromUtf8(e.what()));
    }
}
