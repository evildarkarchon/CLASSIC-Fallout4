#include "gamefilesworker.h"
#include "core/rust_qt_bridge.h"

#include "classic_cxx_bridge/scangame.h"
#include "rust/cxx.h"

GameFilesWorker::GameFilesWorker(QObject* parent)
    : QObject(parent)
{
}

void GameFilesWorker::doScan(const QString& gameExePath, const QString& gameRoot, const QString& docsPath,
                             const QString& gameName, const QString& gameVersion)
{
    Q_UNUSED(gameExePath);

    // Emit indeterminate progress -- the Rust side does not provide
    // granular progress callbacks for Game Setup Intake.
    emit progress(-1.0f, QStringLiteral("Running game setup intake..."));

    try {
        auto result =
            classic::scangame::run_game_setup_intake(classic::toRustString(gameName), classic::toRustString(gameVersion),
                                                     classic::toRustString(gameRoot), classic::toRustString(docsPath),
                                                     ::rust::Str("", 0));

        emit progress(100.0f, QStringLiteral("Complete"));
        emit finished(classic::toQString(result.rendered_report), result.has_errors, result.total_checks);

    } catch (const rust::Error& e) {
        emit error(QString::fromUtf8(e.what()));
    } catch (const std::exception& e) {
        emit error(QString::fromUtf8(e.what()));
    }
}
