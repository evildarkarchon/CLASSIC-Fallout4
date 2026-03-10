#pragma once

#include <QString>
#include <QStringList>
#include <QVector>

#include <cstdint>
#include <functional>
#include <string>

namespace classic::gui::scanworker_execution {
struct ScanExecutionConfig {
    QString yamlRoot;
    QString yamlData;
    QString game;
    QString gameVersion;
    bool showFormIdValues = false;
    bool fcxMode = false;
    bool simplifyLogs = false;
};

struct SingleScanResult {
    QString logPath;
    bool success = false;
    std::string reportContent;
};

struct BatchScanResult {
    std::uint32_t inputIndex = 0;
    QString logPath;
    bool success = false;
    std::string reportContent;
};

using BatchProgressCallback =
    std::function<void(float percent, const QString& status, int completed, int total)>;

SingleScanResult executeSingleScan(const ScanExecutionConfig& config, const QString& logPath);

QVector<BatchScanResult> executeBatchScan(const ScanExecutionConfig& config,
                                          const QStringList& logPaths,
                                          int maxConcurrentScans,
                                          const BatchProgressCallback& progressCallback);

void writeAutoscanReport(const QString& logPath, const std::string& reportContent);
}
