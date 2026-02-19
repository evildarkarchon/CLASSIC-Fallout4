#include "gamefilesworker.h"
#include "core/rust_qt_bridge.h"

#include "rust/cxx.h"
#include "classic_cxx_bridge/scangame.h"

GameFilesWorker::GameFilesWorker(QObject* parent)
    : QObject(parent) {}

void GameFilesWorker::doScan(const QString& gameExePath,
                             const QString& gameRoot,
                             const QString& docsPath,
                             const QString& gameName) {
    // Emit indeterminate progress -- the Rust side does not provide
    // granular progress callbacks for setup checks.
    emit progress(-1.0f, QStringLiteral("Running game file setup checks..."));

    try {
        auto result = classic::scangame::run_setup_checks(
            classic::toRustString(gameExePath),
            classic::toRustString(gameRoot),
            classic::toRustString(docsPath),
            classic::toRustString(gameName)
        );

        emit progress(100.0f, QStringLiteral("Complete"));
        emit finished(
            classic::toQString(result.combined_output),
            result.has_errors,
            result.total_checks
        );

    } catch (const rust::Error& e) {
        emit error(QString::fromUtf8(e.what()));
    } catch (const std::exception& e) {
        emit error(QString::fromUtf8(e.what()));
    }
}
