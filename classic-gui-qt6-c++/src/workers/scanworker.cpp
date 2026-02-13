#include "scanworker.h"
#include "core/rust_qt_bridge.h"

#include "rust/cxx.h"
#include "classic_cxx_bridge/scanner.h"
#include "classic_cxx_bridge/config.h"

ScanWorker::ScanWorker(QObject* parent)
    : QObject(parent) {}

void ScanWorker::requestCancel() {
    m_cancelled = true;
}

void ScanWorker::doScan(const QStringList& logPaths,
                        const QString& yamlRoot,
                        const QString& yamlData,
                        const QString& game,
                        bool vrMode) {
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
            false,  // show_formid_values
            false,  // fcx_mode
            false   // simplify_logs
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

                if (result.success) {
                    ++successCount;
                } else {
                    ++errorCount;
                }
                emit logScanned(i, result.success, logPaths[i]);

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
