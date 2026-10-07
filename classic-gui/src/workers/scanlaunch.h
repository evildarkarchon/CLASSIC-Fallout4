#pragma once

#include <QString>
#include <QStringList>

#include "classic_cxx_bridge/scanner.h"
#include "rust/cxx.h"

namespace classic::gui {

/// Launches one GUI Crash Log Scan through Rust's Crash Log Scan Launch.
///
/// This is the GUI's whole share of request building: it picks the scan intent and hands Rust the
/// Installation Root. An empty `targetedInputs` list is a Standard intent; a non-empty one is a
/// Targeted intent over exactly those inputs, in order. Rust opens User Settings read-only, applies
/// the saved values (managed game, game version, FormID rows, FCX setup context, Unsolved Logs
/// policy), and makes the Installation Root the Standard base folder. The GUI supplies no per-run
/// overrides, so nothing here can disagree with the saved settings.
///
/// The returned launch is either a typed launch error (`scan_run_launch_error(...).has_error`) or
/// a launched request plus its diagnostics. Throws `rust::Error` only for input Rust cannot
/// represent, such as an empty Installation Root.
rust::Box<classic::scanner::ScanRunLaunch> launchScanRun(const QString& installationRoot,
                                                         const QStringList& targetedInputs);

/// Renders a launched request's diagnostics as one rich-text warning, or an empty string.
///
/// The words are Rust's: each diagnostic arrives as a Display Content line rendered by the scan
/// presentation module, and this only lays them out, one per line. A clean launch says nothing.
QString formatScanRunLaunchWarning(const classic::scanner::ScanRunLaunchRequestDto& view);

} // namespace classic::gui
