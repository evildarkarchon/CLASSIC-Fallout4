#include "gamefilesworker.h"
#include "core/rust_qt_bridge.h"

#include "classic_cxx_bridge/scangame.h"
#include "rust/cxx.h"

GameFilesWorker::GameFilesWorker(QObject* parent)
    : QObject(parent)
{
}

void GameFilesWorker::doScan(const QString& classicRoot, const QString& xseLogPath)
{
    // Emit indeterminate progress -- the Rust side does not provide
    // granular progress callbacks for Game Setup Intake.
    emit progress(-1.0f, QStringLiteral("Running game setup intake..."));

    try {
        auto result = classic::scangame::run_game_setup_intake_from_user_settings(classic::toRustString(classicRoot),
                                                                                  classic::toRustString(xseLogPath));
        const bool requiresAttention = result.has_errors ||
                                       classic::toQString(result.status) != QStringLiteral("ready") ||
                                       result.action_count > 0;

        emit progress(100.0f, QStringLiteral("Complete"));
        emit finished(classic::toQString(result.rendered_report), requiresAttention, result.total_checks);

    } catch (const rust::Error& e) {
        emit error(QString::fromUtf8(e.what()));
    } catch (const std::exception& e) {
        emit error(QString::fromUtf8(e.what()));
    } catch (...) {
        // Keep non-standard bridge exceptions from escaping the worker thread.
        emit error(QStringLiteral("unknown error"));
    }
}
