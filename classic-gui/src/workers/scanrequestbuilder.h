#pragma once

#include "core/guiusersettings.h"

#include <QString>
#include <QStringList>

#include "classic_cxx_bridge/scanner.h"

namespace classic::gui {

/// Builds the complete Rust scan-run request from one accepted typed GUI settings value object.
///
/// Runtime-only inputs such as discovered Crash Logs, the portable base directory, the XSE log
/// hint, and targeted input intent are supplied separately and never persisted as User Settings.
classic::scanner::ScanRunRequestDto buildScanRunRequest(const QStringList& logPaths, const QString& yamlRoot,
                                                        const QString& yamlData, const QString& baseDirectory,
                                                        const CrashLogScanLaunchSettings& settings,
                                                        const QString& setupXseLogPath, bool targetedMode,
                                                        const QStringList& targetedInputs);

} // namespace classic::gui
