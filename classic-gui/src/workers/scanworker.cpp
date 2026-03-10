#include "scanworker.h"

#include "scanworker_execution.h"

#include <filesystem>

namespace {
using classic::gui::scanworker_execution::BatchScanResult;
using classic::gui::scanworker_execution::ScanExecutionConfig;
using classic::gui::scanworker_execution::SingleScanResult;

QString resolve_log_path(const QString& resultLogPath, const QString& fallback) {
    if (!resultLogPath.isEmpty()) {
        return resultLogPath;
    }
    return fallback;
}

std::string to_utf8_std_string(const QString& value) {
    const QByteArray utf8 = value.toUtf8();
    return std::string(utf8.constData(), static_cast<std::size_t>(utf8.size()));
}

std::string build_autoscan_path(const std::string& logPath) {
    std::filesystem::path crashLog(logPath);
    const auto reportName = crashLog.stem().string() + "-AUTOSCAN.md";
    return (crashLog.parent_path() / reportName).string();
}

void move_file_if_exists(const std::filesystem::path& source, const std::filesystem::path& destDir) {
    std::error_code ec;
    if (!std::filesystem::exists(source, ec)) {
        return;
    }

    std::filesystem::create_directories(destDir, ec);
    if (ec) {
        return;
    }

    const auto destination = destDir / source.filename();
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

void move_unsolved_artifacts(const std::string& logPath, const QString& yamlRoot) {
    if (logPath.empty()) {
        return;
    }

    std::error_code ec;
    const auto backupDir =
        std::filesystem::path(yamlRoot.toStdWString()) / L"CLASSIC Backup" / L"Unsolved Logs";
    if (backupDir.empty()) {
        return;
    }

    const std::filesystem::path crashLog(logPath);
    const std::filesystem::path autoscanReport(build_autoscan_path(logPath));
    move_file_if_exists(crashLog, backupDir);
    move_file_if_exists(autoscanReport, backupDir);
}

ScanExecutionConfig build_execution_config(const QString& yamlRoot,
                                           const QString& yamlData,
                                           const QString& game,
                                           const QString& gameVersion,
                                           bool showFormIdValues,
                                           bool fcxMode,
                                           bool simplifyLogs) {
    ScanExecutionConfig config;
    config.yamlRoot = yamlRoot;
    config.yamlData = yamlData;
    config.game = game;
    config.gameVersion = gameVersion;
    config.showFormIdValues = showFormIdValues;
    config.fcxMode = fcxMode;
    config.simplifyLogs = simplifyLogs;
    return config;
}

bool try_get_fallback_path(const QStringList& logPaths, std::uint32_t inputIndex, QString* fallbackPath) {
    if (inputIndex >= static_cast<std::uint32_t>(logPaths.size())) {
        return false;
    }

    *fallbackPath = logPaths.at(static_cast<qsizetype>(inputIndex));
    return true;
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
                        const QString& gameVersion,
                        bool showFormIdValues,
                        bool fcxMode,
                        bool simplifyLogs,
                        bool moveUnsolvedLogs,
                        int maxConcurrentScans) {
    m_cancelled = false;

    const int total = logPaths.size();
    int successCount = 0;
    int errorCount = 0;
    const ScanExecutionConfig config = build_execution_config(
        yamlRoot,
        yamlData,
        game,
        gameVersion,
        showFormIdValues,
        fcxMode,
        simplifyLogs
    );

    try {
        if (total > 1) {
            if (m_cancelled) {
                emit error(QStringLiteral("Scan cancelled by user"));
                return;
            }

            emit progress(0.0f, QStringLiteral("Scanning logs in parallel..."));
            emit progressDetailed(0.0f, QStringLiteral("Scanning logs in parallel..."), 0, total);

            const QVector<BatchScanResult> results = classic::gui::scanworker_execution::executeBatchScan(
                config,
                logPaths,
                maxConcurrentScans,
                [this](float percent, const QString& status, int completed, int totalCount) {
                    emit progress(percent, status);
                    emit progressDetailed(percent, status, completed, totalCount);
                }
            );

            for (const auto& result : results) {
                QString fallbackPath;
                if (!try_get_fallback_path(logPaths, result.inputIndex, &fallbackPath)) {
                    ++errorCount;
                    emit error(QStringLiteral("Batch scan returned invalid input_index %1 for %2 logs")
                                   .arg(result.inputIndex)
                                   .arg(total));
                    continue;
                }

                const int index = static_cast<int>(result.inputIndex);
                const QString resolvedPath = resolve_log_path(result.logPath, fallbackPath);
                const std::string reportLogPath = to_utf8_std_string(resolvedPath);

                bool scanSuccess = result.success;
                if (scanSuccess && !result.reportContent.empty()) {
                    try {
                        classic::gui::scanworker_execution::writeAutoscanReport(
                            resolvedPath,
                            result.reportContent
                        );
                    } catch (const std::exception&) {
                        scanSuccess = false;
                    }
                }

                if (!scanSuccess && moveUnsolvedLogs) {
                    move_unsolved_artifacts(reportLogPath, yamlRoot);
                }

                if (scanSuccess) {
                    ++successCount;
                } else {
                    ++errorCount;
                }

                emit logScanned(index, scanSuccess, resolvedPath);
            }

            emit progress(100.0f, QStringLiteral("Complete"));
            emit progressDetailed(100.0f, QStringLiteral("Complete"), total, total);
            emit finished(total, successCount, errorCount);
            return;
        }

        for (int i = 0; i < total; ++i) {
            if (m_cancelled) {
                emit error(QStringLiteral("Scan cancelled by user"));
                return;
            }

            const float percent = (static_cast<float>(i) * 100.0f) / static_cast<float>(total);
            emit progress(percent, logPaths[i]);
            emit progressDetailed(percent, logPaths[i], i, total);

            try {
                const SingleScanResult result = classic::gui::scanworker_execution::executeSingleScan(
                    config,
                    logPaths[i]
                );

                bool scanSuccess = result.success;
                const QString resolvedPath = resolve_log_path(result.logPath, logPaths[i]);
                const std::string reportLogPath = to_utf8_std_string(resolvedPath);

                if (scanSuccess && !result.reportContent.empty()) {
                    try {
                        classic::gui::scanworker_execution::writeAutoscanReport(
                            resolvedPath,
                            result.reportContent
                        );
                    } catch (const std::exception&) {
                        scanSuccess = false;
                    }
                }

                if (!scanSuccess && moveUnsolvedLogs) {
                    move_unsolved_artifacts(reportLogPath, yamlRoot);
                }

                if (scanSuccess) {
                    ++successCount;
                } else {
                    ++errorCount;
                }
                emit logScanned(i, scanSuccess, logPaths[i]);

            } catch (const std::exception&) {
                ++errorCount;
                if (moveUnsolvedLogs) {
                    move_unsolved_artifacts(std::string(logPaths[i].toUtf8().constData()), yamlRoot);
                }
                emit logScanned(i, false, logPaths[i]);
            }
        }

        emit progress(100.0f, QStringLiteral("Complete"));
        emit progressDetailed(100.0f, QStringLiteral("Complete"), total, total);
        emit finished(total, successCount, errorCount);

    } catch (const std::exception& ex) {
        emit error(QString::fromUtf8(ex.what()));
    }
}
