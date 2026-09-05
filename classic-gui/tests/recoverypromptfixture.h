#pragma once

#include "workers/scanrunpresentation.h"

#include <QString>
#include <QStringLiteral>

namespace classic::gui::test {

/// Builds the recovery presentation a paused run hands the prompt seam.
///
/// The wording here is deliberately *not* Rust's. What the GUI tests pin is that the dialog shows,
/// offers, and returns exactly what it was handed — a fixture reusing Rust's sentences would still
/// pass if the dialog ignored its argument and printed a hard-coded copy of them. The real sentences
/// are pinned once, in `classic-scan-presentation`; that they reach this seam is pinned by
/// `test_scanrunpresentation.cpp`.
///
/// `resetAvailable` decides the one availability that varies. Proceed Without Ignore is
/// unconditionally available, exactly as Rust reports it: it needs nothing from the installation.
inline ScanRunLocalIgnoreRecoveryPresentation recoveryPresentation(bool resetAvailable = true)
{
    ScanRunLocalIgnoreRecoveryPresentation recovery;
    recovery.message = QStringLiteral("Local Ignore YAML Data is malformed.");
    recovery.prompt = resetAvailable
                          ? QStringLiteral("why the run paused")
                          // Rust states the withheld decision among the prompt lines, so a dialog
                          // that omits a button never has to explain the absence itself.
                          : QStringLiteral("why the run paused. Reset To Default is unavailable here.");

    ScanRunRecoveryDecisionPresentation proceed;
    proceed.decision = classic::scanner::ScanRunLocalIgnoreRecoveryDecision::ProceedWithoutIgnore;
    proceed.label = QStringLiteral("Proceed Without Ignore");
    proceed.description = QStringLiteral("what proceeding does");
    proceed.available = true;

    ScanRunRecoveryDecisionPresentation reset;
    reset.decision = classic::scanner::ScanRunLocalIgnoreRecoveryDecision::ResetToDefault;
    reset.label = QStringLiteral("Reset To Default");
    reset.description = QStringLiteral("what resetting does");
    reset.available = resetAvailable;

    // Both decisions are described whether or not they can be honored, which is what lets a prompt
    // explain an absence it is about to create.
    recovery.decisions.append(proceed);
    recovery.decisions.append(reset);
    return recovery;
}

} // namespace classic::gui::test
