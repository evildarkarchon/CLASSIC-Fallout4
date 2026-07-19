#pragma once

#include "core/guiusersettings.h"

#include <QString>
#include <QStringList>

#include "classic_cxx_bridge/scanner.h"

namespace classic::gui {

/// Builds one invariant-preserving tagged Crash Log Scan Run request from accepted GUI settings.
///
/// An empty Targeted input list constructs Standard intent with Rust-owned discovery and Unsolved
/// Logs policy. A non-empty list constructs Targeted intent, whose CXX constructor cannot express
/// Unsolved Logs movement. FCX selection always uses a constructor that requires setup context.
rust::Box<classic::scanner::ScanRunRequest> buildScanRunRequest(const QString& installationRoot,
                                                                const QString& baseDirectory,
                                                                const CrashLogScanLaunchSettings& settings,
                                                                const QString& setupXseLogPath,
                                                                const QStringList& targetedInputs);

} // namespace classic::gui
