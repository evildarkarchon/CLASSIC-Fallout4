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
#include "classic_cxx_bridge/settings.h"
#include "rust/cxx.h"

#include <cstdlib>
#include <string>

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#endif

/// Find the "CLASSIC Data" directory by searching common locations.
static QString findDataDir()
{
    QDir cwd = QDir::current();
    if (QDir(cwd.filePath("CLASSIC Data")).exists()) {
        return cwd.filePath("CLASSIC Data");
    }

    QString exeDir = QCoreApplication::applicationDirPath();
    if (QDir(QDir(exeDir).filePath("CLASSIC Data")).exists()) {
        return QDir(exeDir).filePath("CLASSIC Data");
    }

    if (QDir(QDir(exeDir + "/..").filePath("CLASSIC Data")).exists()) {
        return QDir(exeDir + "/..").filePath("CLASSIC Data");
    }

    return {};
}

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

    // Read application version from CLASSIC Main.yaml (single source of truth).
    QString dataDir = findDataDir();
    if (dataDir.isEmpty()) {
        classic::message::log_startup_binding_contract_failed(
            "classic-gui.startup", "CLASSIC Data directory", "config_missing",
            "Place the 'CLASSIC Data' directory next to the executable or run from the project root.",
            "Unable to locate CLASSIC Data directory", correlationId);
        QMessageBox::critical(
            nullptr, QStringLiteral("Fatal Configuration Error"),
            QStringLiteral("Unable to locate the CLASSIC Data directory.\n\n"
                           "Cannot read CLASSIC_Info.version because CLASSIC Main.yaml is unavailable.\n"
                           "CLASSIC Main.yaml is the single source of truth for the application version."));
        return 1;
    }

    QString mainYamlPath = dataDir + QStringLiteral("/databases/CLASSIC Main.yaml");
    if (!QFile::exists(mainYamlPath)) {
        classic::message::log_startup_binding_contract_failed(
            "classic-gui.startup", "CLASSIC Main.yaml", "config_missing",
            "Restore CLASSIC Main.yaml under CLASSIC Data/databases before starting the GUI.",
            mainYamlPath.toStdString(), correlationId);
        QMessageBox::critical(
            nullptr, QStringLiteral("Fatal Configuration Error"),
            QStringLiteral("Missing required file:\n%1\n\n"
                           "Cannot read CLASSIC_Info.version.\n"
                           "CLASSIC Main.yaml is the single source of truth for the application version.")
                .arg(mainYamlPath));
        return 1;
    }

    try {
        auto ops = classic::settings::yaml_ops_new();
        classic::settings::yaml_ops_load_file(*ops, std::string(mainYamlPath.toUtf8().constData()));
        auto version = classic::settings::yaml_ops_get_string(*ops, "CLASSIC_Info.version", "");
        if (version.empty()) {
            classic::message::log_startup_binding_contract_failed(
                "classic-gui.startup", "CLASSIC_Info.version", "config_invalid",
                "Add a non-empty CLASSIC_Info.version key to CLASSIC Main.yaml.", "Missing CLASSIC_Info.version key",
                correlationId);
            QMessageBox::critical(
                nullptr, QStringLiteral("Fatal Configuration Error"),
                QStringLiteral("Missing key 'CLASSIC_Info.version' in:\n%1\n\n"
                               "CLASSIC Main.yaml is the single source of truth for the application version.")
                    .arg(mainYamlPath));
            return 1;
        }

        QString qVersion = classic::toQString(version).trimmed();
        // Strip "CLASSIC v" prefix (YAML commonly stores "CLASSIC vX.Y.Z")
        if (qVersion.startsWith(QStringLiteral("CLASSIC v"))) {
            qVersion = qVersion.mid(9).trimmed();
        }

        if (qVersion.isEmpty()) {
            classic::message::log_startup_binding_contract_failed(
                "classic-gui.startup", "CLASSIC_Info.version", "config_invalid",
                "Set CLASSIC_Info.version to a non-empty value (for example: CLASSIC v9.0.0).",
                "CLASSIC_Info.version was empty after normalization", correlationId);
            QMessageBox::critical(nullptr, QStringLiteral("Fatal Configuration Error"),
                                  QStringLiteral("Invalid value for 'CLASSIC_Info.version' in:\n%1\n\n"
                                                 "Expected a non-empty version (for example: CLASSIC v9.0.0).")
                                      .arg(mainYamlPath));
            return 1;
        }

        app.setApplicationVersion(qVersion);
    } catch (const std::exception& e) {
        classic::message::log_startup_binding_contract_failed(
            "classic-gui.startup", "CLASSIC Main.yaml", "config_read",
            "Check CLASSIC Main.yaml syntax and ensure the file is readable.", e.what(), correlationId);
        QMessageBox::critical(nullptr, QStringLiteral("Fatal Configuration Error"),
                              QStringLiteral("Failed to read CLASSIC_Info.version from:\n%1\n\nDetails:\n%2")
                                  .arg(mainYamlPath, QString::fromUtf8(e.what())));
        return 1;
    } catch (...) {
        classic::message::log_startup_binding_contract_failed(
            "classic-gui.startup", "CLASSIC Main.yaml", "config_read",
            "Check CLASSIC Main.yaml syntax and file permissions, then retry startup.",
            "Unknown error while loading CLASSIC Main.yaml", correlationId);
        QMessageBox::critical(nullptr, QStringLiteral("Fatal Configuration Error"),
                              QStringLiteral("Failed to read CLASSIC_Info.version from:\n%1\n\n"
                                             "An unknown error occurred while loading CLASSIC Main.yaml.")
                                  .arg(mainYamlPath));
        return 1;
    }

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
