// CLASSIC C++ Qt 6 GUI — Application Entry Point
//
// Initializes the Rust runtime (ONE RUNTIME RULE), creates the Qt application,
// and shows the main window. The Rust runtime lives for the entire process lifetime.

#include <QApplication>
#include <QDir>
#include <QFile>
#include <QIcon>
#include <QMessageBox>

#include "app/mainwindow.h"
#include "app/typography.h"

#include "core/rust_qt_bridge.h"

#include "classic_cxx_bridge/message.h"
#include "classic_cxx_bridge/registry.h"
#include "classic_cxx_bridge/runtime.h"
#include "rust/cxx.h"

#include <cstdlib>
#include <string>

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#endif

/// Find the CLASSIC.ico icon by searching common locations.
static QString findIcon()
{
    QString iconRef = QStringLiteral("@Classic Data/graphics/CLASSIC.ico");
    if (iconRef.startsWith(QLatin1Char('@'))) {
        iconRef.remove(0, 1);
    }

    QDir cwd = QDir::current();
    QString exeDir = QCoreApplication::applicationDirPath();
    const QStringList candidates = {
        cwd.filePath(iconRef),
        QDir(exeDir).filePath(iconRef),
        QDir(exeDir + "/..").filePath(iconRef),
    };

    for (const QString& iconPath : candidates) {
        if (QFile::exists(iconPath)) {
            return iconPath;
        }
    }

    return {};
}

static std::string startupCorrelationId()
{
    char* value = nullptr;
    size_t valueLen = 0;
    if (_dupenv_s(&value, &valueLen, "CLASSIC_CORRELATION_ID") != 0 || value == nullptr) {
        return {};
    }

    std::string correlationId(value);
    free(value);
    if (correlationId.empty()) {
        return {};
    }
    return correlationId;
}

int main(int argc, char* argv[])
{
    QApplication app(argc, argv);
    app.setApplicationName(QStringLiteral("CLASSIC"));
    const std::string correlationId = startupCorrelationId();

    // Bring the logging bridge online before any helper that might emit a
    // structured warning (font registration, icon lookup, etc.). The Rust
    // runtime itself is initialized below inside the rust::Error try block.
    classic::message::init_logging();

    // Register the bundled Inter font family and install it as the process-wide
    // default QFont. Non-fatal: failures log a structured warning through the
    // bridge and the QSS fallback chain ("Inter", "Segoe UI Variable",
    // "Segoe UI", sans-serif) renders the GUI for that session.
    classic::gui::registerBundledFonts(correlationId);
    classic::gui::installDefaultFont();

    // Set window icon
    QString iconPath = findIcon();
    if (!iconPath.isEmpty()) {
        app.setWindowIcon(QIcon(iconPath));
    }

    // Initialize Rust runtime (ONE RUNTIME RULE: single Tokio runtime for the process)
    try {
        classic::runtime::init_runtime();
        classic::message::log_startup_binding_contract_validated("classic-gui.startup", 3, correlationId);
        classic::message::log_startup_acceleration_status(1, 1, "MANDATORY", correlationId);
    } catch (const rust::Error& e) {
        classic::message::log_startup_binding_contract_failed(
            "classic-gui.startup", "classic::runtime::init_runtime", "runtime_init",
            "Run classic-gui/build_gui.ps1 to rebuild the C++ bridge and verify runtime dependencies.", e.what(),
            correlationId);
        QMessageBox::critical(nullptr, "Fatal Error", QString("Failed to initialize Rust runtime:\n%1").arg(e.what()));
        return 1;
    }

    // `CLASSIC_GUI_VERSION` is baked at configure time by CMake, which
    // parses `CLASSIC_Info.version` directly from
    // `CLASSIC Data/databases/CLASSIC Main.yaml` — the install-immutable
    // bundled YAML is the documented single source of truth for the
    // installed binary's version (see `classic-gui/CMakeLists.txt`).
    // Sourcing the version this way — instead of via the runtime
    // cache-preferring `classic::config::load_main_yaml_version` bridge
    // — guarantees a per-user YAML data update cannot move
    // `QApplication::applicationVersion()` ahead of the actual installed
    // executable, which would otherwise misclassify stale binaries as
    // up-to-date in the app-update notification check. Mirrors how the
    // CLI defines `CLASSIC_CLI_VERSION` and how the TUI's `build.rs`
    // emits `env!("CLASSIC_APP_VERSION")`. The runtime YAML loader stays
    // available for *data* decisions (cache promotion, schema gating)
    // but MUST NOT be the source of truth for binary identity.
#ifndef CLASSIC_GUI_VERSION
#    error "CLASSIC_GUI_VERSION must be defined by the build system (see classic-gui/CMakeLists.txt)"
#endif
    app.setApplicationVersion(QStringLiteral(CLASSIC_GUI_VERSION));

    // Register as GUI mode in the global registry
    classic::registry::registry_set_bool("is_gui_mode", true);
    classic::registry::registry_set_game("Fallout4");

    // Create and show the main window
    MainWindow window;
    window.show();

    int result = app.exec();

    // Signal shutdown intent (no-op — runtime lives for process lifetime)
    classic::runtime::shutdown_runtime();

    return result;
}
