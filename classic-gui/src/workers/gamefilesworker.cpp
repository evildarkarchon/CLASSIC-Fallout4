#include "gamefilesworker.h"
#include "core/rust_qt_bridge.h"

#include "classic_cxx_bridge/scangame.h"
#include "rust/cxx.h"

#include <QDir>

GameFilesWorker::GameFilesWorker(QObject* parent)
    : QObject(parent)
{
}

void GameFilesWorker::doScan(const QString& gameExePath, const QString& gameRoot, const QString& docsPath,
                             const QString& gameName)
{
    // Emit indeterminate progress -- the Rust side does not provide
    // granular progress callbacks for setup checks.
    emit progress(-1.0f, QStringLiteral("Running game file setup checks..."));

    try {
        // EXISTING (D-08 preserved) — combined-output text from setup orchestrator.
        auto result =
            classic::scangame::run_setup_checks(classic::toRustString(gameExePath), classic::toRustString(gameRoot),
                                                classic::toRustString(docsPath), classic::toRustString(gameName));

        // D-11 / CXXS-04 consumer migration from plan 02-05:
        // Exercise the ENB structured DTO bridge on every actual game-files scan.
        auto enb = classic::scangame::enb_checker_validate(classic::toRustString(gameRoot));

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

        // D-11 / CXXS-04 in-flow consumer #2 (plan 02-06 — Codex MEDIUM correction):
        // Exercise the new CrashgenOrchestrator bridge API on every actual scan.
        // Buffout 4 plugins live at {gameRoot}/Data/F4SE/Plugins for Fallout 4.
        QString pluginsPath = QDir(gameRoot).filePath(QStringLiteral("Data/F4SE/Plugins"));
        auto crashgen = classic::scangame::crashgen_orchestrator_check_summary(classic::toRustString(pluginsPath),
                                                                               ::rust::Str("Buffout4", 8));
        QString crashgenLine = QStringLiteral("\n[Crashgen] Buffout4 plugins detected: %1, config issues: %2")
                                   .arg(crashgen.installed_plugin_count)
                                   .arg(crashgen.issue_count);

        QString combinedText = classic::toQString(result.combined_output) + enbSummary + crashgenLine;

        // Compute combined-truth has_errors / total_checks across the three scan
        // sources stitched into combinedText. SetupCheckResults only counts
        // integrity + xse + docs (see classic-scangame-core/src/setup.rs::total_checks),
        // so forwarding result.has_errors / result.total_checks alone makes the banner
        // lie when ENB or Crashgen turn up issues.
        bool combinedHasErrors = result.has_errors;
        uint32_t combinedTotalChecks = result.total_checks;

        // ENB contributes 2 checks: binaries + config.
        combinedTotalChecks += 2;
        // Locked severity model: only Partial binaries OR Unreadable config escalate
        // to error. NotInstalled / NotFound / Present / Valid do NOT escalate
        // (the user has opted out of ENB or it is healthy).
        if (enb.binaries == classic::scangame::EnbResult::Partial) {
            combinedHasErrors = true;
        }
        if (enb.config == classic::scangame::EnbConfigResult::Unreadable) {
            combinedHasErrors = true;
        }

        // Crashgen contributes 1 check (the config audit). Any reported issue
        // is treated as an error.
        combinedTotalChecks += 1;
        if (crashgen.issue_count > 0) {
            combinedHasErrors = true;
        }

        emit progress(100.0f, QStringLiteral("Complete"));
        emit finished(combinedText, combinedHasErrors, combinedTotalChecks);

    } catch (const rust::Error& e) {
        emit error(QString::fromUtf8(e.what()));
    } catch (const std::exception& e) {
        emit error(QString::fromUtf8(e.what()));
    }
}
