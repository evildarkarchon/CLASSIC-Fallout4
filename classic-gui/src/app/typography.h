// CLASSIC GUI — Typography setup
//
// Registers the bundled Inter font family with Qt's font database and
// installs a process-wide default QFont with explicit antialiasing and
// hinting preferences. These helpers are called from main.cpp before
// MainWindow is constructed so every widget inherits the default font.
//
// Registration failure is non-fatal: the helper logs a structured warning
// via the existing startup bridge and lets the QSS fallback chain
// ("Inter", "Segoe UI Variable", "Segoe UI", sans-serif) render the GUI.

#pragma once

#include <string>

namespace classic::gui {

/// Register every bundled Inter face with QFontDatabase.
///
/// Emits a structured warning via classic::message::log_startup_binding_contract_failed
/// for each face that fails to load (QFontDatabase::addApplicationFont returns -1).
/// Never aborts startup.
void registerBundledFonts(const std::string& correlationId);

/// Install a process-wide QFont("Inter", 10) with PreferAntialias style strategy
/// and PreferVerticalHinting hinting preference via QApplication::setFont.
void installDefaultFont();

}  // namespace classic::gui
