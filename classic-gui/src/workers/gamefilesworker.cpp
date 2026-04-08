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
        // EXISTING (D-08 preserved) — combined-output text from setup orchestrator.
        auto result = classic::scangame::run_setup_checks(
            classic::toRustString(gameExePath),
            classic::toRustString(gameRoot),
            classic::toRustString(docsPath),
            classic::toRustString(gameName)
        );

        // D-11 / CXXS-04 consumer migration (Codex MEDIUM correction):
        // Exercise the new ENB structured DTO bridge as part of the existing
        // scan flow.  The result is appended to the combined output so users
        // see it in the same Results view. enb_checker_validate is now called
        // on every actual game-files scan — not a dormant helper method.
        auto enb = classic::scangame::enb_checker_validate(
            classic::toRustString(gameRoot)
        );

        QString enbSummary;
        switch (enb.binaries) {
            case classic::scangame::EnbResult::Present:
                enbSummary = QStringLiteral("\n[ENB] Binaries: PRESENT");
                break;
            case classic::scangame::EnbResult::Partial:
                enbSummary = QStringLiteral("\n[ENB] Binaries: PARTIAL (some files missing)");
                break;
            case classic::scangame::EnbResult::NotInstalled:
                enbSummary = QStringLiteral("\n[ENB] Binaries: NOT INSTALLED");
                break;
            default:
                enbSummary = QStringLiteral("\n[ENB] Binaries: UNKNOWN");
                break;
        }
        switch (enb.config) {
            case classic::scangame::EnbConfigResult::Valid:
                enbSummary += QStringLiteral(" | Config: VALID");
                break;
            case classic::scangame::EnbConfigResult::NotFound:
                enbSummary += QStringLiteral(" | Config: NOT FOUND");
                break;
            case classic::scangame::EnbConfigResult::Unreadable:
                enbSummary += QStringLiteral(" | Config: UNREADABLE");
                break;
            default:
                enbSummary += QStringLiteral(" | Config: UNKNOWN");
                break;
        }

        QString combinedText = classic::toQString(result.combined_output) + enbSummary;

        emit progress(100.0f, QStringLiteral("Complete"));
        emit finished(
            combinedText,
            result.has_errors,
            result.total_checks
        );

    } catch (const rust::Error& e) {
        emit error(QString::fromUtf8(e.what()));
    } catch (const std::exception& e) {
        emit error(QString::fromUtf8(e.what()));
    }
}
