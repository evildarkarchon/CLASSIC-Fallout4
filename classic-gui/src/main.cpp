// CLASSIC C++ Qt 6 GUI — Application Entry Point
//
// Initializes the Rust runtime (ONE RUNTIME RULE), creates the Qt application,
// and shows the main window. The Rust runtime lives for the entire process lifetime.

#include <QApplication>
#include <QIcon>
#include <QDir>
#include <QMessageBox>

#include "app/mainwindow.h"

#include "rust/cxx.h"
#include "classic_cxx_bridge/runtime.h"
#include "classic_cxx_bridge/registry.h"

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#endif

/// Find the CLASSIC.ico icon by searching common locations.
static QString findIcon()
{
    // Check relative to CWD (development / distribution layout)
    QDir cwd = QDir::current();
    QString cwdIcon = cwd.filePath("CLASSIC Data/graphics/CLASSIC.ico");
    if (QFile::exists(cwdIcon)) {
        return cwdIcon;
    }

    // Check relative to executable
    QString exeDir = QCoreApplication::applicationDirPath();
    QString exeIcon = QDir(exeDir).filePath("CLASSIC Data/graphics/CLASSIC.ico");
    if (QFile::exists(exeIcon)) {
        return exeIcon;
    }

    // Check parent of executable (for build/ subdirectory layout)
    QString parentIcon = QDir(exeDir + "/..").filePath("CLASSIC Data/graphics/CLASSIC.ico");
    if (QFile::exists(parentIcon)) {
        return parentIcon;
    }

    return {};
}

int main(int argc, char* argv[])
{
    QApplication app(argc, argv);
    app.setApplicationName("CLASSIC");
    app.setApplicationVersion("1.0.0");

    // Set window icon
    QString iconPath = findIcon();
    if (!iconPath.isEmpty()) {
        app.setWindowIcon(QIcon(iconPath));
    }

    // Initialize Rust runtime (ONE RUNTIME RULE: single Tokio runtime for the process)
    try {
        classic::runtime::init_runtime();
    } catch (const rust::Error& e) {
        QMessageBox::critical(nullptr, "Fatal Error",
            QString("Failed to initialize Rust runtime:\n%1").arg(e.what()));
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
